#!/usr/bin/env python3
"""
K-Fashion 자동 입찰 텔레그램 봇 (자동화 기능 포함)
시스템을 원격으로 제어하고 모니터링
"""

import os
import sys
import json
import logging
import asyncio
import queue
import threading
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# 상태 추적을 위한 상수 import
import status_constants

# python-telegram-bot 라이브러리
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes,
    ConversationHandler, MessageHandler, filters
)

# 통합 모듈 import
from unified_bidding import UnifiedBidding
from auto_bidding import AutoBidding

# 로깅 설정
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / f'telegram_bot_{datetime.now().strftime("%Y%m%d")}.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# ConversationHandler 상태 정의
# 순서: 적립금선할인 → 카드할인 → 기본할인율 → 최소수익
(WAITING_POINTS_USE, WAITING_POINTS_RATE, 
 WAITING_CARD_USE, WAITING_CARD_INPUT,
 WAITING_DISCOUNT, WAITING_PROFIT) = range(6)


def parse_card_discount(input_text: str) -> Optional[Dict[str, Any]]:
    """카드 할인 문자열을 파싱하여 구조화된 데이터로 변환
    
    Args:
        input_text: 사용자가 입력한 카드 할인 조건 문자열
        
    Returns:
        파싱된 할인 정보 딕셔너리 또는 None
        - type: 'threshold' (임계값 기반) 또는 'proportional' (비례 할인)
        - base_amount: 기준 금액 (원 단위)
        - discount_amount: 할인 금액 (원 단위)
        - condition: 'gte' (이상) 또는 'gt' (초과)
    
    Examples:
        "3만원 이상 3천원" -> {type: 'threshold', base_amount: 30000, discount_amount: 3000, condition: 'gte'}
        "5만원 초과 5천원" -> {type: 'threshold', base_amount: 50000, discount_amount: 5000, condition: 'gt'}
        "10만원당 1만원" -> {type: 'proportional', base_amount: 100000, discount_amount: 10000}
    """
    if not input_text:
        return None
        
    # 입력 텍스트 정규화 (공백 제거, 소문자 변환)
    text = input_text.strip().replace(' ', '')
    
    # 금액 단위 변환 함수
    def parse_amount(amount_str: str, unit: str) -> int:
        """금액 문자열과 단위를 받아 원 단위로 변환"""
        try:
            amount = float(amount_str)
            if unit == '천' or unit == '천원':
                return int(amount * 1000)
            elif unit == '만' or unit == '만원':
                return int(amount * 10000)
            elif unit == '원':
                return int(amount)
            else:
                return 0
        except ValueError:
            return 0
    
    # 패턴 1: 임계값 기반 할인 (예: "3만원 이상 3천원", "5만원 초과 5천원")
    threshold_pattern = r'(\d+\.?\d*)(천|만|천원|만원|원)\s*(이상|초과)\s*(\d+\.?\d*)(천|만|천원|만원|원)'
    threshold_match = re.search(threshold_pattern, text)
    
    if threshold_match:
        base_amount = parse_amount(threshold_match.group(1), threshold_match.group(2))
        condition = 'gte' if threshold_match.group(3) == '이상' else 'gt'
        discount_amount = parse_amount(threshold_match.group(4), threshold_match.group(5))
        
        return {
            'type': 'threshold',
            'base_amount': base_amount,
            'discount_amount': discount_amount,
            'condition': condition
        }
    
    # 패턴 2: 비례 할인 (예: "10만원당 1만원", "5만원마다 5천원")
    proportional_pattern = r'(\d+\.?\d*)(천|만|천원|만원|원)\s*(당|마다)\s*(\d+\.?\d*)(천|만|천원|만원|원)'
    proportional_match = re.search(proportional_pattern, text)
    
    if proportional_match:
        base_amount = parse_amount(proportional_match.group(1), proportional_match.group(2))
        discount_amount = parse_amount(proportional_match.group(4), proportional_match.group(5))
        
        return {
            'type': 'proportional',
            'base_amount': base_amount,
            'discount_amount': discount_amount
        }
    
    # 패턴 3: 간단한 형식 (예: "3만3천", "5만5천" - 기본적으로 "이상" 조건으로 처리)
    simple_pattern = r'(\d+)만\s*(\d+)?천'
    simple_match = re.search(simple_pattern, text)
    
    if simple_match:
        base_amount = int(simple_match.group(1)) * 10000
        discount_amount = int(simple_match.group(2) or 0) * 1000
        
        # 기본 금액과 할인 금액이 비슷하면 "만원당" 형식으로 간주
        if base_amount > 0 and discount_amount > 0:
            return {
                'type': 'threshold',
                'base_amount': base_amount,
                'discount_amount': discount_amount,
                'condition': 'gte'
            }
    
    # 파싱 실패
    return None


class BiddingBot:
    """입찰 텔레그램 봇"""
    
    def __init__(self, config_path: str = "config/bot_config.json"):
        """초기화"""
        self.config = self._load_config(config_path)
        self.bidder = UnifiedBidding()
        self.auto_bidder = AutoBidding()
        self.current_task = None
        self.is_running = False
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """설정 파일 로드"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"설정 파일 로드 실패: {e}")
            raise
    
    def is_authorized(self, user_id: int) -> bool:
        """사용자 권한 확인"""
        admin_ids = self.config['bot'].get('admin_ids', [])
        return user_id in admin_ids
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """시작 명령어 처리"""
        user = update.effective_user
        logger.info(f"Start command from user {user.id}: {user.first_name}")
        
        if not self.is_authorized(user.id):
            await update.message.reply_text(self.config['messages']['unauthorized'])
            return
        
        # 환영 메시지 업데이트
        welcome_text = """
🤖 **K-Fashion 자동 입찰 봇**

이제 링크 추출부터 입찰까지 자동으로!

**주요 명령어:**
• `/auto musinsa 나이키` - 자동화 입찰
• `/help` - 전체 명령어 보기

시작하려면 `/auto` 명령어를 사용하세요!
        """
        await update.message.reply_text(welcome_text, parse_mode='Markdown')
    
    async def auto_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """자동화 링크 추출 + 입찰 명령어 (대화형)"""
        if not self.is_authorized(update.effective_user.id):
            await update.message.reply_text(self.config['messages']['unauthorized'])
            return ConversationHandler.END
        
        # 이미 실행 중인지 확인
        if self.is_running:
            await update.message.reply_text(self.config['messages']['task_running'])
            return ConversationHandler.END
        
        # 파라미터 파싱
        args = context.args
        site = args[0] if len(args) > 0 else 'musinsa'
        keywords = args[1:] if len(args) > 1 else None
        
        # 유효한 사이트인지 확인
        valid_sites = ['musinsa', 'abcmart']
        if site not in valid_sites:
            # site가 키워드일 수도 있음
            if site and not keywords:
                keywords = [site]
                site = 'musinsa'
            else:
                await update.message.reply_text(f"❌ 유효하지 않은 사이트: {site}\n사용 가능: {', '.join(valid_sites)}")
                return ConversationHandler.END
        
        if not keywords:
            await update.message.reply_text(
                "🤖 **자동화 입찰**\n\n"
                "사용법: /auto [site] [keywords...]\n\n"
                "예시:\n"
                "`/auto musinsa 나이키 에어포스`\n"
                "`/auto abcmart 운동화`\n"
                "`/auto 나이키` (무신사 기본)\n\n"
                "키워드를 공백으로 구분하여 입력하세요.",
                parse_mode='Markdown'
            )
            return ConversationHandler.END
        
        # context.user_data에 기본 정보 저장
        context.user_data['site'] = site
        context.user_data['keywords'] = keywords
        
        # 적립금 선할인 사용 여부 질문
        keyboard = [
            [
                InlineKeyboardButton("✅ 사용", callback_data="points_use_yes"),
                InlineKeyboardButton("❌ 미사용", callback_data="points_use_no")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "💳 **무신사 적립금 선할인**\n\n"
            "무신사 적립금 선할인을 사용하시겠습니까?\n\n"
            "📄 멤버십 등급별 적립률:\n"
            "• 브론즈: 2%\n"
            "• 실버: 3%\n"
            "• 골드: 4%\n"
            "• 플래티넘: 5%\n"
            "• 다이아: 6-8%",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        return WAITING_POINTS_USE
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """도움말 명령어"""
        if not self.is_authorized(update.effective_user.id):
            await update.message.reply_text(self.config['messages']['unauthorized'])
            return
        
        help_text = """
📚 **명령어 도움말**

**🤖 자동화 입찰 (추천!)**
/auto [site] [keywords...] - 링크 추출부터 입찰까지 자동
  • 예: `/auto 나이키 에어포스`
  • 예: `/auto musinsa 아디다스`
  • 예: `/auto abcmart 운동화`

**📁 수동 입찰**
/bid [site] [strategy] - 링크 파일 필요
  • site: musinsa, abcmart
  • strategy: basic, standard, premium
  • 예: `/bid musinsa standard`

**🔧 기타 명령어**
/status - 현재 작업 상태
/stop - 작업 중지
/strategies - 전략 목록
/help - 이 도움말

💡 **팁**: 대부분의 경우 `/auto` 명령어만 사용하면 됩니다!
        """
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def bid_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """입찰 시작 명령어"""
        if not self.is_authorized(update.effective_user.id):
            await update.message.reply_text(self.config['messages']['unauthorized'])
            return
        
        # 이미 실행 중인지 확인
        if self.is_running:
            await update.message.reply_text(self.config['messages']['task_running'])
            return
        
        # 파라미터 파싱
        args = context.args
        site = args[0] if len(args) > 0 else self.config['bidding']['default_site']
        strategy = args[1] if len(args) > 1 else self.config['bidding']['default_strategy']
        
        # 유효성 검사
        valid_sites = ['musinsa', 'abcmart']
        if site not in valid_sites:
            await update.message.reply_text(f"❌ 유효하지 않은 사이트: {site}\n사용 가능: {', '.join(valid_sites)}")
            return
        
        # 전략 확인
        available_strategies = list(self.bidder.config['strategies'].keys())
        if strategy not in available_strategies:
            await update.message.reply_text(
                f"❌ 유효하지 않은 전략: {strategy}\n"
                f"사용 가능: {', '.join(available_strategies)}"
            )
            return
        
        # 확인 메시지
        keyboard = [
            [
                InlineKeyboardButton("✅ 시작", callback_data=f"bid_start_{site}_{strategy}"),
                InlineKeyboardButton("❌ 취소", callback_data="bid_cancel")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"🎯 **입찰 설정**\n\n"
            f"사이트: {site}\n"
            f"전략: {strategy}\n\n"
            f"⚠️ 주의: input/{site}_links.txt 파일이 필요합니다.\n\n"
            f"이대로 진행하시겠습니까?",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """상태 확인 명령어"""
        if not self.is_authorized(update.effective_user.id):
            await update.message.reply_text(self.config['messages']['unauthorized'])
            return
        
        if not self.is_running:
            await update.message.reply_text(self.config['messages']['no_task'])
            return
        
        # 현재 작업 상태
        if self.current_task:
            status_text = f"""
📊 **현재 작업 상태**

작업 ID: {self.current_task.get('id', 'N/A')}
작업 유형: {self.current_task.get('type', 'N/A')}
사이트: {self.current_task.get('site', 'N/A')}
시작 시간: {self.current_task.get('start_time', 'N/A')}
진행 단계: {self.current_task.get('stage', 'N/A')}
            """
            
            # 자동화 작업인 경우 추가 정보
            if self.current_task.get('type') == 'auto':
                status_text += f"\n키워드: {self.current_task.get('keywords', 'N/A')}"
            else:
                status_text += f"\n전략: {self.current_task.get('strategy', 'N/A')}"
                
            await update.message.reply_text(status_text, parse_mode='Markdown')
        else:
            await update.message.reply_text("작업 정보를 가져올 수 없습니다.")
    
    async def stop_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """작업 중지 명령어"""
        if not self.is_authorized(update.effective_user.id):
            await update.message.reply_text(self.config['messages']['unauthorized'])
            return
        
        if not self.is_running:
            await update.message.reply_text(self.config['messages']['no_task'])
            return
        
        # 중지 확인
        keyboard = [
            [
                InlineKeyboardButton("⛔ 중지", callback_data="stop_confirm"),
                InlineKeyboardButton("↩️ 계속", callback_data="stop_cancel")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "⚠️ 정말로 작업을 중지하시겠습니까?",
            reply_markup=reply_markup
        )
    
    async def strategies_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """전략 목록 명령어"""
        if not self.is_authorized(update.effective_user.id):
            await update.message.reply_text(self.config['messages']['unauthorized'])
            return
        
        strategies = self.bidder.config['strategies']
        
        text = "📋 **사용 가능한 전략**\n\n"
        for strategy_id, strategy_data in strategies.items():
            enabled = "✅" if strategy_data.get('enabled', False) else "❌"
            text += f"{enabled} **{strategy_id}** - {strategy_data.get('name', 'N/A')}\n"
            text += f"   {strategy_data.get('description', 'N/A')}\n\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def discount_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """할인율 입력 처리"""
        try:
            # 입력값 파싱
            text = update.message.text.strip()
            discount = float(text.replace('%', ''))
            
            # 유효성 검사 (1-30%)
            if not 1 <= discount <= 30:
                await update.message.reply_text(
                    "⚠️ 할인율은 1-30% 범위여야 합니다.\n"
                    "다시 입력해주세요.",
                    parse_mode='Markdown'
                )
                return WAITING_DISCOUNT
            
            # 저장
            context.user_data['discount_rate'] = discount
            
            # 최소 수익 입력 요청
            await update.message.reply_text(
                "💵 **최소 예상 수익 설정**\n\n"
                "최소 예상 수익을 입력하세요 (0원 이상)\n"
                "예: 5000, 10000, 20000\n\n"
                "숫자만 입력하면 됩니다.",
                parse_mode='Markdown'
            )
            
            return WAITING_PROFIT
            
        except ValueError:
            await update.message.reply_text(
                "⚠️ 숫자만 입력해주세요.\n"
                "예: 5, 10, 15, 20",
                parse_mode='Markdown'
            )
            return WAITING_DISCOUNT
    
    async def profit_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """최소 수익 입력 처리"""
        try:
            # 입력값 파싱
            text = update.message.text.strip()
            min_profit = int(text.replace(',', '').replace('원', ''))
            
            # 유효성 검사 (0원 이상)
            if min_profit < 0:
                await update.message.reply_text(
                    "⚠️ 최소 예상 수익은 0원 이상이어야 합니다.\n"
                    "다시 입력해주세요.",
                    parse_mode='Markdown'
                )
                return WAITING_PROFIT
            
            # 저장
            context.user_data['min_profit'] = min_profit
            
            # 최종 확인 메시지
            site = context.user_data.get('site', 'musinsa')
            keywords = context.user_data.get('keywords', [])
            discount_rate = context.user_data.get('discount_rate', 5)
            
            # 설정 정보 구성
            settings_msg = f"🤖 **자동화 입찰 설정 확인**\n\n"
            settings_msg += f"🏪 사이트: {site.upper()}\n"
            settings_msg += f"🔍 키워드: {', '.join(keywords)}\n\n"
            
            # 적립금 선할인 정보
            if context.user_data.get('use_points_discount', False):
                points_rate = context.user_data.get('points_rate', 0)
                settings_msg += f"💳 무신사 적립금 선할인: {points_rate}%\n"
            else:
                settings_msg += f"💳 무신사 적립금 선할인: 미사용\n"
            
            # 카드 할인 정보
            if context.user_data.get('use_card_discount', False):
                card_discount = context.user_data.get('card_discount')
                if card_discount:
                    if card_discount['type'] == 'threshold':
                        condition = "이상" if card_discount['condition'] == 'gte' else "초과"
                        settings_msg += f"💳 카드 할인: {card_discount['base_amount']:,}원 {condition} {card_discount['discount_amount']:,}원 할인\n"
                    else:
                        settings_msg += f"💳 카드 할인: {card_discount['base_amount']:,}원당 {card_discount['discount_amount']:,}원 할인\n"
            else:
                settings_msg += f"💳 카드 할인: 미사용\n"
            
            settings_msg += f"\n💰 기본 할인율: {discount_rate}%\n"
            settings_msg += f"💵 최소 수익: {min_profit:,}원\n\n"
            settings_msg += f"이대로 진행하시겠습니까?"
            
            # callback_data에 설정값 포함 (적립금과 카드 할인 정보 추가)
            callback_data_parts = [
                "auto_start_with_discounts",
                site,
                '|'.join(keywords),
                str(discount_rate),
                str(min_profit),
                str(context.user_data.get('points_rate', 0)),
                '1' if context.user_data.get('use_card_discount', False) else '0'
            ]
            callback_data = "_".join(callback_data_parts)
            
            keyboard = [
                [
                    InlineKeyboardButton("✅ 시작", callback_data=callback_data),
                    InlineKeyboardButton("❌ 취소", callback_data="auto_cancel")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                settings_msg,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            return ConversationHandler.END
            
        except ValueError:
            await update.message.reply_text(
                "⚠️ 숫자만 입력해주세요.\n"
                "예: 5000, 10000, 20000",
                parse_mode='Markdown'
            )
            return WAITING_PROFIT
    
    async def cancel_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """대화 취소 처리"""
        await update.message.reply_text(
            "❌ 설정이 취소되었습니다.",
            parse_mode='Markdown'
        )
        # user_data 초기화
        context.user_data.clear()
        return ConversationHandler.END
    
    async def card_input_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """카드 할인 조건 입력 처리"""
        try:
            # 입력값 파싱
            text = update.message.text.strip()
            card_discount = parse_card_discount(text)
            
            if not card_discount:
                await update.message.reply_text(
                    "⚠️ 올바른 형식으로 입력해주세요.\n\n"
                    "예시:\n"
                    "• `3만원 이상 3천원`\n"
                    "• `5만원당 5천원`\n"
                    "• `10만원 초과 1만원`",
                    parse_mode='Markdown'
                )
                return WAITING_CARD_INPUT
            
            # 저장
            context.user_data['card_discount'] = card_discount
            
            # 카드 할인 정보 표시
            discount_info = f"카드 할인: "
            if card_discount['type'] == 'threshold':
                condition_text = "이상" if card_discount['condition'] == 'gte' else "초과"
                discount_info += f"{card_discount['base_amount']:,}원 {condition_text} {card_discount['discount_amount']:,}원 할인"
            else:  # proportional
                discount_info += f"{card_discount['base_amount']:,}원당 {card_discount['discount_amount']:,}원 할인"
            
            # 기본 할인율 입력 요청
            await update.message.reply_text(
                f"✅ {discount_info}\n\n"
                "💰 **기본 할인율 설정**\n\n"
                "기본 할인율을 입력하세요 (1-30%)\n"
                "예: 5, 10, 15, 20\n\n"
                "숫자만 입력하면 됩니다.",
                parse_mode='Markdown'
            )
            
            return WAITING_DISCOUNT
            
        except Exception as e:
            logger.error(f"카드 할인 입력 처리 중 오류: {e}")
            await update.message.reply_text(
                "⚠️ 처리 중 오류가 발생했습니다.\n"
                "다시 입력해주세요.",
                parse_mode='Markdown'
            )
            return WAITING_CARD_INPUT
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """버튼 콜백 처리"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        # 적립금 선할인 사용 여부 처리
        if data == "points_use_yes":
            # 적립금 선할인 사용 선택
            context.user_data['use_points_discount'] = True
            
            # 퍼센트 선택 버튼 표시
            keyboard = []
            # 2x4 그리드로 1-8% 버튼 배치
            for i in range(0, 8, 2):
                row = []
                for j in range(2):
                    percent = i + j + 1
                    row.append(InlineKeyboardButton(f"{percent}%", callback_data=f"points_rate_{percent}"))
                keyboard.append(row)
            
            # 취소 버튼 추가
            keyboard.append([InlineKeyboardButton("❌ 취소", callback_data="auto_cancel")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "💳 **적립금 선할인 비율 선택**\n\n"
                "귀하의 멤버십 등급에 맞는 적립률을 선택하세요:\n\n"
                "📊 **멤버십별 적립률**\n"
                "• 브론즈: 2%\n"
                "• 실버: 3%\n"
                "• 골드: 4%\n"
                "• 플래티넘: 5%\n"
                "• 다이아: 6-8%",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            return  # ConversationHandler에서 상태 관리
            
        elif data == "points_use_no":
            # 적립금 선할인 미사용
            context.user_data['use_points_discount'] = False
            context.user_data['points_rate'] = 0
            
            # 카드 할인 사용 여부 질문으로 이동
            keyboard = [
                [
                    InlineKeyboardButton("✅ 사용", callback_data="card_use_yes"),
                    InlineKeyboardButton("❌ 미사용", callback_data="card_use_no")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "💳 **카드 할인 사용**\n\n"
                "카드 할인을 사용하시겠습니까?\n\n"
                "예시:\n"
                "• 3만원 이상 3천원 할인\n"
                "• 5만원당 5천원 할인\n"
                "• 10만원 이상 1만원 할인",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            return
            
        elif data.startswith("points_rate_"):
            # 적립금 퍼센트 선택
            rate = int(data.replace("points_rate_", ""))
            context.user_data['points_rate'] = rate
            
            # 카드 할인 사용 여부 질문으로 이동
            keyboard = [
                [
                    InlineKeyboardButton("✅ 사용", callback_data="card_use_yes"),
                    InlineKeyboardButton("❌ 미사용", callback_data="card_use_no")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"✅ 적립금 선할인 {rate}% 선택됨\n\n"
                "💳 **카드 할인 사용**\n\n"
                "카드 할인을 사용하시겠습니까?\n\n"
                "예시:\n"
                "• 3만원 이상 3천원 할인\n"
                "• 5만원당 5천원 할인\n"
                "• 10만원 이상 1만원 할인",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            return
        
        elif data.startswith("bid_start_"):
            # 입찰 시작
            _, _, site, strategy = data.split("_")
            await query.edit_message_text("🚀 입찰을 시작합니다...")
            
            # 비동기로 입찰 실행
            asyncio.create_task(self._run_bidding(query, site, strategy))
            
        elif data.startswith("auto_start_"):
            # 자동화 입찰 시작
            custom_discount_rate = None
            custom_min_profit = None
            points_rate = None
            card_discount = None
            
            if data.startswith("auto_start_with_discounts_"):
                # 새로운 형식: auto_start_with_discounts_{site}_{keywords}_{discount}_{profit}_{points_rate}_{use_card}
                parts = data.replace("auto_start_with_discounts_", "").split("_")
                
                if len(parts) >= 6:
                    site = parts[0]
                    
                    try:
                        # 설정값 파싱
                        use_card = parts[-1] == '1'
                        points_rate_value = float(parts[-2])
                        custom_min_profit = int(parts[-3])
                        custom_discount_rate = float(parts[-4])
                        
                        # 키워드 파싱
                        keywords_part = "_".join(parts[1:-4])
                        keywords = keywords_part.split("|") if keywords_part else []
                        
                        # 적립금 선할인 설정
                        if points_rate_value > 0:
                            points_rate = points_rate_value
                        
                        # 카드 할인 정보 가져오기
                        if use_card and context.user_data.get('card_discount'):
                            card_discount = context.user_data['card_discount']
                            
                    except (ValueError, IndexError):
                        # 파싱 실패 시 기본값 사용
                        keywords = parts[1].split("|") if len(parts) > 1 else []
                else:
                    site = parts[0] if parts else 'musinsa'
                    keywords = parts[1].split("|") if len(parts) > 1 else []
                    
            elif data.startswith("auto_start_custom_"):
                # 커스텀 설정이 있는 경우
                # 형식: auto_start_custom_{site}_{keywords}_{discount}_{profit}
                parts = data.replace("auto_start_custom_", "").split("_")
                
                if len(parts) >= 4:
                    site = parts[0]
                    # 마지막 두 부분은 설정값
                    try:
                        custom_min_profit = int(parts[-1])
                        custom_discount_rate = float(parts[-2])
                        # 나머지는 키워드
                        keywords_part = "_".join(parts[1:-2])
                        keywords = keywords_part.split("|") if keywords_part else []
                    except (ValueError, IndexError):
                        # 파싱 실패 시 기본값 사용
                        keywords = parts[1].split("|") if len(parts) > 1 else []
                else:
                    site = parts[0] if parts else 'musinsa'
                    keywords = parts[1].split("|") if len(parts) > 1 else []
            else:
                # 기본 설정
                parts = data.split("_", 3)
                site = parts[2]
                keywords = parts[3].split("|") if len(parts) > 3 else []
            
            await query.edit_message_text("🤖 자동화 입찰을 시작합니다...")
            
            # 비동기로 자동 입찰 실행 (커스텀 설정 포함)
            asyncio.create_task(self._run_auto_bidding(
                query, site, keywords, 
                custom_discount_rate, custom_min_profit,
                points_rate, card_discount
            ))
            
        elif data == "bid_cancel" or data == "auto_cancel":
            await query.edit_message_text("❌ 취소되었습니다.")
            # user_data 초기화
            context.user_data.clear()
            
        elif data == "card_use_yes":
            # 카드 할인 사용 선택
            context.user_data['use_card_discount'] = True
            
            await query.edit_message_text(
                "💳 **카드 할인 조건 입력**\n\n"
                "카드 할인 조건을 입력해주세요.\n\n"
                "📝 **입력 예시:**\n"
                "• `3만원 이상 3천원`\n"
                "• `5만원 초과 5천원`\n"
                "• `10만원당 1만원`\n"
                "• `5만원마다 5천원`\n"
                "• `3만3천` (3만원 이상 3천원으로 해석)\n\n"
                "숫자와 단위를 정확히 입력해주세요.",
                parse_mode='Markdown'
            )
            return WAITING_CARD_INPUT
            
        elif data == "card_use_no":
            # 카드 할인 미사용
            context.user_data['use_card_discount'] = False
            context.user_data['card_discount'] = None
            
            # 기본 할인율 입력으로 이동
            await query.edit_message_text(
                "💰 **기본 할인율 설정**\n\n"
                "기본 할인율을 입력하세요 (1-30%)\n"
                "예: 5, 10, 15, 20\n\n"
                "숫자만 입력하면 됩니다.",
                parse_mode='Markdown'
            )
            return WAITING_DISCOUNT
            
        elif data == "stop_confirm":
            self.is_running = False
            await query.edit_message_text("⛔ 작업이 중지되었습니다.")
            
        elif data == "stop_cancel":
            await query.edit_message_text("↩️ 작업을 계속 진행합니다.")
    
    async def _run_auto_bidding(self, query, site: str, keywords: list,
                                custom_discount_rate: float = None,
                                custom_min_profit: int = None,
                                points_rate: float = None,
                                card_discount: dict = None):
        """자동화 입찰 실행 (비동기)"""
        chat_id = query.message.chat_id
        
        try:
            self.is_running = True
            self.current_task = {
                'id': f"AUTO_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'type': 'auto',
                'site': site,
                'keywords': ', '.join(keywords),
                'start_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'stage': '초기화'
            }
            
            # 시작 메시지 구성
            start_message = (
                f"🚀 **자동화 입찰 시작**\n\n"
                f"🎯 사이트: {site.upper()}\n"
                f"🔍 키워드: {', '.join(keywords)}\n"
            )
            
            # 커스텀 설정이 있으면 표시
            if custom_discount_rate is not None:
                start_message += f"💰 할인율: {custom_discount_rate}%\n"
            if custom_min_profit is not None:
                start_message += f"💵 최소 수익: {custom_min_profit:,}원\n"
            if points_rate is not None and points_rate > 0:
                start_message += f"💳 적립금 선할인: {points_rate}%\n"
            if card_discount is not None:
                if card_discount['type'] == 'threshold':
                    condition = "이상" if card_discount['condition'] == 'gte' else "초과"
                    start_message += f"💳 카드 할인: {card_discount['base_amount']:,}원 {condition} {card_discount['discount_amount']:,}원\n"
                else:
                    start_message += f"💳 카드 할인: {card_discount['base_amount']:,}원당 {card_discount['discount_amount']:,}원\n"
            
            start_message += (
                f"\n⏰ 예상 시간: 10-15분\n\n"
                f"진행 상황을 알려드리겠습니다..."
            )
            
            await query.message.chat.send_message(
                start_message,
                parse_mode='Markdown'
            )
            
            # 큐 생성 (threading과 asyncio 간 통신)
            status_queue = queue.Queue()
            last_progress = 0
            
            # 콜백 함수 정의
            def status_callback(stage: str, progress: int, message: str, details: dict = None):
                """상태 업데이트 콜백"""
                nonlocal last_progress
                
                # 진행률이 일정 이상 변경되었을 때만 업데이트
                if progress - last_progress >= status_constants.PROGRESS_UPDATE_THRESHOLD or stage == status_constants.STAGE_ERROR:
                    status_queue.put({
                        'stage': stage,
                        'progress': progress,
                        'message': message,
                        'details': details or {}
                    })
                    last_progress = progress
            
            # 큐 모니터링 태스크
            async def monitor_queue():
                """큐를 모니터링하고 텔레그램 메시지 전송"""
                while self.is_running:
                    try:
                        # 큐에서 상태 가져오기 (0.1초 타임아웃)
                        status = status_queue.get(timeout=0.1)
                        
                        # 현재 작업 상태 업데이트
                        self.current_task['stage'] = status['stage']
                        self.current_task['progress'] = status['progress']
                        
                        # 메시지 포맷팅
                        formatted_msg = status_constants.format_status_message(
                            status['stage'],
                            status['progress'],
                            status['message'],
                            status['details']
                        )
                        
                        # 텔레그램 메시지 전송
                        await query.message.chat.send_message(
                            formatted_msg,
                            parse_mode='Markdown'
                        )
                        
                        # API 제한 고려하여 대기
                        await asyncio.sleep(status_constants.TELEGRAM_MESSAGE_MIN_INTERVAL)
                        
                    except queue.Empty:
                        # 큐가 비어있으면 짧게 대기
                        await asyncio.sleep(0.1)
                    except Exception as e:
                        logger.error(f"큐 모니터링 중 오류: {e}")
            
            # 큐 모니터링 시작
            monitor_task = asyncio.create_task(monitor_queue())
            
            # 실제 자동 입찰 실행 (별도 스레드에서)
            try:
                result = await asyncio.to_thread(
                    self.auto_bidder.run_auto_pipeline,
                    site=site,
                    keywords=keywords,
                    strategy='basic',
                    status_callback=status_callback,
                    custom_discount_rate=custom_discount_rate,
                    custom_min_profit=custom_min_profit
                )
                
                # 작업 완료 후 잠시 대기 (마지막 메시지 처리)
                await asyncio.sleep(0.5)
                
                # 결과 메시지
                if result['status'] == 'success':
                    # 성공 메시지 개선
                    success_msg = (
                        f"✅ **자동화 입찰 완료!**\n\n"
                        f"⚙️ **사용자 설정**\n"
                        f"├ 🔍 검색 키워드: {', '.join(keywords)}\n"
                    )
                    
                    # 커스텀 설정이 있으면 표시
                    if points_rate is not None and points_rate > 0:
                        success_msg += f"├ 💳 적립금 선할인: {points_rate}%\n"
                    else:
                        success_msg += f"├ 💳 적립금 선할인: 미사용\n"
                        
                    if card_discount is not None:
                        if card_discount['type'] == 'threshold':
                            condition = "이상" if card_discount['condition'] == 'gte' else "초과"
                            success_msg += f"├ 💳 카드 할인: {card_discount['base_amount']:,}원 {condition} {card_discount['discount_amount']:,}원\n"
                        else:
                            success_msg += f"├ 💳 카드 할인: {card_discount['base_amount']:,}원당 {card_discount['discount_amount']:,}원\n"
                    else:
                        success_msg += f"├ 💳 카드 할인: 미사용\n"
                        
                    if custom_discount_rate is not None:
                        success_msg += f"├ 💰 기본 할인율: {custom_discount_rate}%\n"
                    else:
                        success_msg += f"├ 💰 기본 할인율: 기본 전략\n"
                        
                    if custom_min_profit is not None:
                        success_msg += f"└ 💵 최소 수익 기준: {custom_min_profit:,}원\n\n"
                    else:
                        success_msg += f"└ 💵 최소 수익 기준: 설정 없음\n\n"
                    
                    # 수집 및 처리 결과
                    success_msg += (
                        f"📊 **처리 결과**\n"
                        f"├ 🔗 수집된 링크: {result.get('total_links', 0)}개\n"
                        f"├ 📦 분석된 상품: {result.get('total_items', 0)}개\n"
                        f"├ ✅ 성공한 입찰: {result.get('successful_bids', 0)}개\n"
                        f"├ ❌ 실패한 입찰: {result.get('total_items', 0) - result.get('successful_bids', 0)}개\n"
                        f"└ ⏱️ 소요 시간: {result.get('execution_time', 0):.1f}초\n\n"
                    )
                    
                    # 재무 정보 추가 (예상)
                    successful_bids = result.get('successful_bids', 0)
                    if successful_bids > 0:
                        success_msg += (
                            f"💰 **예상 수익 정보**\n"
                            f"├ 평균 할인율: {custom_discount_rate if custom_discount_rate else '전략별 상이'}%\n"
                            f"├ 성공 입찰 수: {successful_bids}개\n"
                            f"└ 예상 수익률: 할인율 × 판매 성공 시\n\n"
                        )
                    
                    success_msg += f"💾 상세 결과는 `output` 폴더에 저장되었습니다."
                    
                    await query.message.chat.send_message(
                        success_msg,
                        parse_mode='Markdown'
                    )
                    
                    # 입찰 성공률 계산 및 평가
                    if result.get('total_items', 0) > 0:
                        success_rate = (result.get('successful_bids', 0) / result.get('total_items', 0)) * 100
                        
                        # 성공률에 따른 평가 메시지
                        if success_rate >= 80:
                            rate_msg = f"🎯 **우수한 성공률**: {success_rate:.1f}%\n"
                            rate_msg += "대부분의 상품에서 입찰에 성공했습니다!"
                        elif success_rate >= 50:
                            rate_msg = f"👍 **양호한 성공률**: {success_rate:.1f}%\n"
                            rate_msg += "절반 이상의 상품에서 입찰에 성공했습니다."
                        else:
                            rate_msg = f"⚠️ **개선 필요**: {success_rate:.1f}%\n"
                            rate_msg += "할인율이나 최소 수익 설정을 조정해보세요."
                        
                        await query.message.chat.send_message(
                            rate_msg,
                            parse_mode='Markdown'
                        )
                else:
                    # 실패 메시지
                    error_msg = (
                        f"❌ **자동화 입찰 실패**\n\n"
                        f"⚠️ 오류 내용:\n"
                        f"```\n{result.get('error', '알 수 없는 오류')}\n```\n\n"
                        f"💡 **해결 방법**\n"
                        f"1. 인터넷 연결 확인\n"
                        f"2. 사이트 접속 가능 여부 확인\n"
                        f"3. 로그 파일 확인 (`logs` 폴더)"
                    )
                    
                    await query.message.chat.send_message(
                        error_msg,
                        parse_mode='Markdown'
                    )
                    
            finally:
                # 큐 모니터링 종료
                self.is_running = False
                monitor_task.cancel()
                try:
                    await monitor_task
                except asyncio.CancelledError:
                    pass
            
        except Exception as e:
            logger.error(f"자동화 입찰 실행 중 오류: {e}")
            await query.message.chat.send_message(
                self.config['messages']['error'].format(error=str(e))
            )
        finally:
            self.is_running = False
            self.current_task = None
    
    async def _run_bidding(self, query, site: str, strategy: str):
        """입찰 실행 (비동기)"""
        chat_id = query.message.chat_id
        
        try:
            self.is_running = True
            self.current_task = {
                'id': f"TG_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'type': 'manual',
                'site': site,
                'strategy': strategy,
                'start_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'stage': '초기화'
            }
            
            # 진행 상황 업데이트
            stages = ['링크 읽기', '스크래핑', '가격 조정', '입찰 실행']
            
            for i, stage in enumerate(stages):
                if not self.is_running:
                    break
                
                self.current_task['stage'] = stage
                
                # 메시지 업데이트
                progress = "▓" * (i + 1) + "░" * (len(stages) - i - 1)
                await query.message.chat.send_message(
                    f"⏳ **진행 중**\n\n"
                    f"[{progress}] {(i+1)*25}%\n"
                    f"현재 단계: {stage}",
                    parse_mode='Markdown'
                )
                
                # 실제로는 여기서 해당 단계 실행
                await asyncio.sleep(2)  # 임시 대기
            
            # 실제 입찰 실행
            if self.is_running:
                result = await asyncio.to_thread(
                    self.bidder.run_pipeline,
                    site=site,
                    strategy_id=strategy,
                    exec_mode=self.config['bidding']['default_mode']
                )
                
                # 결과 메시지
                if result['status'] == 'success':
                    await query.message.chat.send_message(
                        f"✅ **입찰 완료**\n\n"
                        f"처리 항목: {result['total_items']}개\n"
                        f"성공: {result['successful_bids']}개\n"
                        f"실패: {result['failed_bids']}개\n"
                        f"실행 시간: {result['execution_time']:.2f}초",
                        parse_mode='Markdown'
                    )
                else:
                    await query.message.chat.send_message(
                        f"❌ **입찰 실패**\n\n"
                        f"오류: {result.get('error', '알 수 없는 오류')}",
                        parse_mode='Markdown'
                    )
            
        except Exception as e:
            logger.error(f"입찰 실행 중 오류: {e}")
            await query.message.chat.send_message(
                self.config['messages']['error'].format(error=str(e))
            )
        finally:
            self.is_running = False
            self.current_task = None
    
    def run(self):
        """봇 실행"""
        # 토큰 확인
        token = self.config['bot']['token']
        if token == "YOUR_BOT_TOKEN_HERE":
            logger.error("봇 토큰이 설정되지 않았습니다. config/bot_config.json 파일을 수정하세요.")
            return
        
        # Application 생성
        application = Application.builder().token(token).build()
        
        # ConversationHandler 생성 (auto 명령어용)
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("auto", self.auto_command)],
            states={
                WAITING_POINTS_USE: [CallbackQueryHandler(self.button_callback)],
                WAITING_POINTS_RATE: [CallbackQueryHandler(self.button_callback)],
                WAITING_CARD_USE: [CallbackQueryHandler(self.button_callback)],
                WAITING_CARD_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.card_input_handler)],
                WAITING_DISCOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.discount_handler)],
                WAITING_PROFIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.profit_handler)]
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel_handler),
                CallbackQueryHandler(self.button_callback, pattern="^auto_cancel$")
            ],
            per_message=False
        )
        
        # 핸들러 등록
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(conv_handler)  # ConversationHandler 등록
        application.add_handler(CommandHandler("bid", self.bid_command))
        application.add_handler(CommandHandler("status", self.status_command))
        application.add_handler(CommandHandler("stop", self.stop_command))
        application.add_handler(CommandHandler("strategies", self.strategies_command))
        application.add_handler(CallbackQueryHandler(self.button_callback))
        
        # 봇 시작
        logger.info("텔레그램 봇 시작... (자동화 기능 활성화)")
        application.run_polling()


def main():
    """메인 함수"""
    bot = BiddingBot()
    bot.run()


if __name__ == '__main__':
    main()
