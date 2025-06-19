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
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# python-telegram-bot 라이브러리
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

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
        """자동화 링크 추출 + 입찰 명령어"""
        if not self.is_authorized(update.effective_user.id):
            await update.message.reply_text(self.config['messages']['unauthorized'])
            return
        
        # 이미 실행 중인지 확인
        if self.is_running:
            await update.message.reply_text(self.config['messages']['task_running'])
            return
        
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
                return
        
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
            return
        
        # 확인 메시지
        keyboard = [
            [
                InlineKeyboardButton("✅ 시작", callback_data=f"auto_start_{site}_{'|'.join(keywords)}"),
                InlineKeyboardButton("❌ 취소", callback_data="auto_cancel")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"🤖 **자동화 입찰 설정**\n\n"
            f"사이트: {site}\n"
            f"키워드: {', '.join(keywords)}\n\n"
            f"링크 추출부터 입찰까지 자동으로 진행합니다.\n"
            f"예상 시간: 10-15분\n\n"
            f"계속하시겠습니까?",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
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
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """버튼 콜백 처리"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data.startswith("bid_start_"):
            # 입찰 시작
            _, _, site, strategy = data.split("_")
            await query.edit_message_text("🚀 입찰을 시작합니다...")
            
            # 비동기로 입찰 실행
            asyncio.create_task(self._run_bidding(query, site, strategy))
            
        elif data.startswith("auto_start_"):
            # 자동화 입찰 시작
            parts = data.split("_", 3)
            site = parts[2]
            keywords = parts[3].split("|") if len(parts) > 3 else []
            
            await query.edit_message_text("🤖 자동화 입찰을 시작합니다...")
            
            # 비동기로 자동 입찰 실행
            asyncio.create_task(self._run_auto_bidding(query, site, keywords))
            
        elif data == "bid_cancel" or data == "auto_cancel":
            await query.edit_message_text("❌ 취소되었습니다.")
            
        elif data == "stop_confirm":
            self.is_running = False
            await query.edit_message_text("⛔ 작업이 중지되었습니다.")
            
        elif data == "stop_cancel":
            await query.edit_message_text("↩️ 작업을 계속 진행합니다.")
    
    async def _run_auto_bidding(self, query, site: str, keywords: list):
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
            
            # 시작 메시지
            await query.message.chat.send_message(
                f"🚀 **자동화 입찰 시작**\n\n"
                f"🎯 사이트: {site.upper()}\n"
                f"🔍 키워드: {', '.join(keywords)}\n"
                f"⏰ 예상 시간: 10-15분\n\n"
                f"진행 상황을 알려드리겠습니다...",
                parse_mode='Markdown'
            )
            
            # 진행 상황 업데이트
            stages = [
                ('로그인 확인', '🔐 로그인 상태 확인 중...', 5),
                ('키워드 검색', '🔍 검색 페이지 접속 중...', 10),
                ('링크 추출', '🔗 상품 링크 수집 중...', 20),
                ('정보 수집', '📦 상품 정보 스크래핑 중...', 40),
                ('가격 계산', '💰 최적 가격 계산 중...', 10),
                ('입찰 실행', '🎯 입찰 진행 중...', 15)
            ]
            
            total_weight = sum(s[2] for s in stages)
            current_progress = 0
            
            for i, (stage, description, weight) in enumerate(stages):
                if not self.is_running:
                    break
                
                self.current_task['stage'] = stage
                current_progress += weight
                
                # 진행률 계산
                percentage = int((current_progress / total_weight) * 100)
                
                # 프로그레스 바 생성
                filled = int(percentage / 10)
                progress_bar = "█" * filled + "░" * (10 - filled)
                
                # 메시지 업데이트
                await query.message.chat.send_message(
                    f"⚙️ **진행 상황**\n\n"
                    f"[{progress_bar}] {percentage}%\n\n"
                    f"🔄 현재 단계: {stage}\n"
                    f"📝 {description}",
                    parse_mode='Markdown'
                )
                
                # 실제 작업 시뮬레이션 (나중에 실제 작업으로 교체)
                await asyncio.sleep(weight / 5)  # 가중치에 따른 대기 시간
            
            # 실제 자동 입찰 실행
            if self.is_running:
                result = await asyncio.to_thread(
                    self.auto_bidder.run_auto_pipeline,
                    site=site,
                    keywords=keywords,
                    strategy='basic'
                )
                
                # 결과 메시지
                if result['status'] == 'success':
                    # 성공 메시지
                    success_msg = (
                        f"✅ **자동화 입찰 완료!**\n\n"
                        f"📊 **결과 요약**\n"
                        f"├ 🔍 검색 키워드: {', '.join(keywords)}\n"
                        f"├ 🔗 수집된 링크: {result.get('total_links', 0)}개\n"
                        f"├ 📦 처리된 상품: {result.get('total_items', 0)}개\n"
                        f"├ ✅ 성공한 입찰: {result.get('successful_bids', 0)}개\n"
                        f"└ ⏱️ 소요 시간: {result.get('execution_time', 0):.1f}초\n\n"
                        f"💾 결과는 `output` 폴더에 저장되었습니다."
                    )
                    
                    await query.message.chat.send_message(
                        success_msg,
                        parse_mode='Markdown'
                    )
                    
                    # 입찰 성공률 계산
                    if result.get('total_items', 0) > 0:
                        success_rate = (result.get('successful_bids', 0) / result.get('total_items', 0)) * 100
                        
                        # 성공률에 따른 이모지
                        if success_rate >= 80:
                            emoji = "🎯"
                        elif success_rate >= 50:
                            emoji = "👍"
                        else:
                            emoji = "⚠️"
                        
                        await query.message.chat.send_message(
                            f"{emoji} 입찰 성공률: {success_rate:.1f}%",
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
        
        # 핸들러 등록
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("auto", self.auto_command))  # 자동화 명령어 추가
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
