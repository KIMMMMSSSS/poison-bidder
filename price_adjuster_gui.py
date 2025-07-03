import tkinter as tk
from tkinter import ttk, filedialog, messagebox, font
import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFilter
import json
import os
from datetime import datetime
import threading
import queue
from typing import List, Dict, Tuple
import pandas as pd
import platform

# CustomTkinter 설정 - 밝은 테마
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

class PriceAdjusterGUI:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("K-Fashion Price Adjuster ✨")
        self.root.geometry("1200x900")  # 높이를 800에서 900으로 증가
        
        # 변수 초기화
        self.input_file = None
        self.output_data = []
        self.processing = False
        self.log_queue = queue.Queue()
        
        # 색상 팔레트 (통합 프로그램과 동일)
        self.colors = {
            'bg': '#FFFFFF',
            'card': '#F8FAFB',
            'card_hover': '#F3F4F6',
            'border': '#E5E7EB',
            'accent': '#3B82F6',
            'accent_hover': '#2563EB',
            'success': '#10B981',
            'success_hover': '#059669',
            'error': '#EF4444',
            'warning': '#F59E0B',
            'text': '#111827',
            'text_secondary': '#6B7280'
        }
        
        # 한국어 폰트 설정
        self.setup_fonts()
        
        # UI 구성
        self.setup_ui()
        
        # 로그 업데이트 시작
        self.update_logs()
        
    def setup_fonts(self):
        """한국어 폰트 설정"""
        system = platform.system()
        
        # 시스템별 한국어 폰트
        if system == "Windows":
            korean_fonts = ["맑은 고딕", "나눔고딕", "Malgun Gothic", "NanumGothic"]
        elif system == "Darwin":  # macOS
            korean_fonts = ["Apple SD Gothic Neo", "나눔고딕", "NanumGothic"]
        else:  # Linux
            korean_fonts = ["NanumGothic", "나눔고딕", "Noto Sans CJK KR"]
        
        # 사용 가능한 첫 번째 폰트 찾기
        available_fonts = list(font.families())
        self.korean_font = None
        
        for f in korean_fonts:
            if f in available_fonts:
                self.korean_font = f
                break
        
        # 기본값
        if not self.korean_font:
            self.korean_font = "Arial"
            
    def setup_ui(self):
        """메인 UI 구성"""
        # 배경색
        self.root.configure(fg_color=self.colors['bg'])
        
        # 메인 컨테이너
        self.main_container = ctk.CTkFrame(
            self.root,
            fg_color='transparent',
            corner_radius=0
        )
        self.main_container.pack(fill='both', expand=True, padx=20, pady=20)
        
        # 헤더
        self.create_header()
        
        # 컨텐츠 영역
        self.content_frame = ctk.CTkFrame(
            self.main_container,
            fg_color=self.colors['card'],
            corner_radius=20,
            border_width=1,
            border_color=self.colors['border']
        )
        self.content_frame.pack(fill='both', expand=True, pady=(20, 0))
        
        # 왼쪽: 설정 패널 (스크롤 가능)
        self.left_scroll = ctk.CTkScrollableFrame(
            self.content_frame,
            fg_color='transparent',
            width=380,
            corner_radius=0
        )
        self.left_scroll.pack(side='left', fill='y', padx=20, pady=20)
        
        # 스크롤 프레임 내부에 패널 생성
        self.left_panel = ctk.CTkFrame(
            self.left_scroll,
            fg_color='transparent'
        )
        self.left_panel.pack(fill='both', expand=True)
        
        # 오른쪽: 진행상황 & 로그
        self.right_panel = ctk.CTkFrame(
            self.content_frame,
            fg_color='transparent'
        )
        self.right_panel.pack(side='right', fill='both', expand=True, padx=(0, 20), pady=20)
        
        # 설정 섹션들
        self.create_file_section()
        self.create_adjustment_section()
        self.create_action_section()
        
        # 진행상황 섹션
        self.create_progress_section()
        
    def create_header(self):
        """헤더 섹션"""
        header_frame = ctk.CTkFrame(
            self.main_container,
            fg_color='transparent',
            height=80
        )
        header_frame.pack(fill='x')
        header_frame.pack_propagate(False)
        
        # 타이틀
        title_label = ctk.CTkLabel(
            header_frame,
            text="K-Fashion Price Adjuster",
            font=ctk.CTkFont(family=self.korean_font, size=32, weight="bold"),
            text_color=self.colors['accent']
        )
        title_label.pack(side='left', padx=10)
        
        # 서브타이틀
        subtitle_label = ctk.CTkLabel(
            header_frame,
            text="스마트 가격 조정 시스템",
            font=ctk.CTkFont(family=self.korean_font, size=14),
            text_color=self.colors['text_secondary']
        )
        subtitle_label.pack(side='left', padx=(0, 20))
        
        # 실행 모드
        mode_frame = ctk.CTkFrame(header_frame, fg_color='transparent')
        mode_frame.pack(side='right', padx=10)
        
        mode_label = ctk.CTkLabel(
            mode_frame,
            text="실행 모드:",
            font=ctk.CTkFont(family=self.korean_font, size=13),
            text_color=self.colors['text_secondary']
        )
        mode_label.pack(side='left', padx=(0, 10))
        
        self.exec_mode = ctk.StringVar(value="auto")
        
        auto_radio = ctk.CTkRadioButton(
            mode_frame,
            text="🚀 자동",
            font=ctk.CTkFont(family=self.korean_font, size=13),
            variable=self.exec_mode,
            value="auto"
        )
        auto_radio.pack(side='left', padx=5)
        
        manual_radio = ctk.CTkRadioButton(
            mode_frame,
            text="👀 확인",
            font=ctk.CTkFont(family=self.korean_font, size=13),
            variable=self.exec_mode,
            value="manual"
        )
        manual_radio.pack(side='left', padx=5)
        
    def create_file_section(self):
        """파일 선택 섹션"""
        # 카드 프레임
        file_card = self.create_card(self.left_panel, "📁 파일 선택")
        
        # 파일 선택 버튼
        self.file_button = ctk.CTkButton(
            file_card,
            text="입찰 파일 선택...",
            font=ctk.CTkFont(family=self.korean_font, size=14),
            command=self.select_file,
            height=40,
            corner_radius=10,
            fg_color=self.colors['accent'],
            hover_color=self.colors['accent_hover']
        )
        self.file_button.pack(fill='x', pady=(0, 10))
        
        # 선택된 파일 표시
        self.file_label = ctk.CTkLabel(
            file_card,
            text="파일을 선택해주세요",
            text_color=self.colors['text_secondary'],
            font=ctk.CTkFont(family=self.korean_font, size=12)
        )
        self.file_label.pack()
        
    def create_adjustment_section(self):
        """가격 조정 설정 섹션"""
        # 카드 프레임
        adjust_card = self.create_card(self.left_panel, "💰 할인 설정")
        
        # 1. 쿠폰 할인
        self.create_discount_option(
            adjust_card,
            "쿠폰 할인",
            "coupon",
            ["없음", "5%", "10%", "15%", "20%"]
        )
        
        # 2. 적립금/포인트
        self.create_discount_option(
            adjust_card,
            "적립금/포인트",
            "points",
            ["없음", "1%", "2%", "3%", "4%"],
            "* 브론즈 2%, 골드/플래티넘 3%, 다이아 4%"
        )
        
        # 3. 무신사 카드 프리미엄
        self.create_premium_section(adjust_card)
        
        # 4. 카드 캐시백
        self.create_discount_option(
            adjust_card,
            "카드 캐시백 (최종)",
            "cashback",
            ["없음", "1%", "2%", "3%", "4%", "5%"]
        )
        
    def create_discount_option(self, parent, label, var_name, options, hint=None):
        """할인 옵션 생성"""
        frame = ctk.CTkFrame(parent, fg_color='transparent')
        frame.pack(fill='x', pady=(0, 15))
        
        # 라벨
        label_widget = ctk.CTkLabel(
            frame,
            text=label,
            font=ctk.CTkFont(family=self.korean_font, size=14, weight="bold"),
            text_color=self.colors['text']
        )
        label_widget.pack(anchor='w')
        
        # 힌트
        if hint:
            hint_label = ctk.CTkLabel(
                frame,
                text=hint,
                font=ctk.CTkFont(family=self.korean_font, size=11),
                text_color=self.colors['text_secondary']
            )
            hint_label.pack(anchor='w', pady=(2, 5))
        
        # 라디오 버튼 프레임
        radio_frame = ctk.CTkFrame(frame, fg_color='transparent')
        radio_frame.pack(fill='x', pady=(5, 0))
        
        # 변수 생성
        setattr(self, f"{var_name}_var", ctk.StringVar(value=options[0]))
        
        # 라디오 버튼들
        for i, option in enumerate(options):
            radio = ctk.CTkRadioButton(
                radio_frame,
                text=option,
                font=ctk.CTkFont(family=self.korean_font, size=12),
                variable=getattr(self, f"{var_name}_var"),
                value=option,
                radiobutton_width=20,
                radiobutton_height=20
            )
            radio.grid(row=i//3, column=i%3, padx=5, pady=2, sticky='w')
            
    def create_premium_section(self, parent):
        """무신사 카드 프리미엄 섹션"""
        frame = ctk.CTkFrame(parent, fg_color='transparent')
        frame.pack(fill='x', pady=(0, 15))
        
        # 라벨
        label = ctk.CTkLabel(
            frame,
            text="무신사 카드 프리미엄",
            font=ctk.CTkFont(family=self.korean_font, size=14, weight="bold"),
            text_color=self.colors['text']
        )
        label.pack(anchor='w')
        
        # 체크박스
        self.premium_var = ctk.BooleanVar(value=False)
        self.premium_check = ctk.CTkCheckBox(
            frame,
            text="사용",
            font=ctk.CTkFont(family=self.korean_font, size=12),
            variable=self.premium_var,
            command=self.toggle_premium
        )
        self.premium_check.pack(anchor='w', pady=(5, 5))
        
        # 입력 필드들
        self.premium_frame = ctk.CTkFrame(frame, fg_color='transparent')
        
        input_frame = ctk.CTkFrame(self.premium_frame, fg_color='transparent')
        input_frame.pack(fill='x')
        
        # 최소 금액
        min_label = ctk.CTkLabel(
            input_frame, 
            text="최소 금액:",
            font=ctk.CTkFont(family=self.korean_font, size=12)
        )
        min_label.pack(side='left', padx=(0, 5))
        
        self.premium_min = ctk.CTkEntry(
            input_frame,
            width=100,
            placeholder_text="70000"
        )
        self.premium_min.pack(side='left', padx=(0, 5))
        
        won_label1 = ctk.CTkLabel(
            input_frame, 
            text="원 이상",
            font=ctk.CTkFont(family=self.korean_font, size=12)
        )
        won_label1.pack(side='left', padx=(0, 10))
        
        # 할인 금액
        discount_label = ctk.CTkLabel(
            input_frame, 
            text="할인:",
            font=ctk.CTkFont(family=self.korean_font, size=12)
        )
        discount_label.pack(side='left', padx=(0, 5))
        
        self.premium_discount = ctk.CTkEntry(
            input_frame,
            width=80,
            placeholder_text="5000"
        )
        self.premium_discount.pack(side='left', padx=(0, 5))
        
        won_label2 = ctk.CTkLabel(
            input_frame, 
            text="원",
            font=ctk.CTkFont(family=self.korean_font, size=12)
        )
        won_label2.pack(side='left')
        
    def toggle_premium(self):
        """프리미엄 할인 토글"""
        if self.premium_var.get():
            self.premium_frame.pack(fill='x', pady=(5, 0))
        else:
            self.premium_frame.pack_forget()
            
    def create_action_section(self):
        """실행 버튼 섹션"""
        # 처리 방식 선택
        process_card = self.create_card(self.left_panel, "⚙️ 처리 방식")
        
        self.process_mode = ctk.StringVar(value="sequential")
        
        seq_radio = ctk.CTkRadioButton(
            process_card,
            text="🐌 순차 처리 (안전)",
            font=ctk.CTkFont(family=self.korean_font, size=13),
            variable=self.process_mode,
            value="sequential"
        )
        seq_radio.pack(anchor='w', pady=2)
        
        para_radio = ctk.CTkRadioButton(
            process_card,
            text="⚡ 동시 처리 (빠름)",
            font=ctk.CTkFont(family=self.korean_font, size=13),
            variable=self.process_mode,
            value="parallel"
        )
        para_radio.pack(anchor='w', pady=2)
        
        # 실행 버튼
        self.start_button = ctk.CTkButton(
            self.left_panel,
            text="🚀 가격 조정 시작",
            font=ctk.CTkFont(family=self.korean_font, size=16, weight="bold"),
            command=self.start_processing,
            height=50,
            corner_radius=15,
            fg_color=self.colors['success'],
            hover_color=self.colors['success_hover']
        )
        self.start_button.pack(fill='x', pady=(20, 20))  # bottom 대신 일반 pack 사용
        
    def create_progress_section(self):
        """진행상황 섹션"""
        # 진행 상황 카드
        progress_card = self.create_card(self.right_panel, "📊 진행 상황")
        
        # 진행률 바
        self.progress = ctk.CTkProgressBar(
            progress_card,
            height=20,
            corner_radius=10,
            progress_color=self.colors['accent']
        )
        self.progress.pack(fill='x', pady=(0, 10))
        self.progress.set(0)
        
        # 진행 정보
        self.progress_label = ctk.CTkLabel(
            progress_card,
            text="대기 중...",
            font=ctk.CTkFont(family=self.korean_font, size=14)
        )
        self.progress_label.pack()
        
        # 통계
        stats_frame = ctk.CTkFrame(progress_card, fg_color='transparent')
        stats_frame.pack(fill='x', pady=(10, 0))
        
        # 통계 박스들
        self.create_stat_box(stats_frame, "✅ 성공", "0", self.colors['success'])
        self.create_stat_box(stats_frame, "❌ 실패", "0", self.colors['error'])
        self.create_stat_box(stats_frame, "⏳ 대기", "0", self.colors['warning'])
        
        # 로그 카드
        log_card = self.create_card(self.right_panel, "📋 실행 로그", expand=True)
        
        # 로그 텍스트
        self.log_text = ctk.CTkTextbox(
            log_card,
            height=300,
            corner_radius=10,
            fg_color='white',
            text_color=self.colors['text'],
            font=ctk.CTkFont(family="Consolas", size=12)
        )
        self.log_text.pack(fill='both', expand=True)
        
    def create_card(self, parent, title, expand=False):
        """카드 생성"""
        # 카드 프레임
        card = ctk.CTkFrame(
            parent,
            corner_radius=15,
            fg_color='white',
            border_width=1,
            border_color=self.colors['border']
        )
        
        if expand:
            card.pack(fill='both', expand=True, pady=(0, 10))
        else:
            card.pack(fill='x', pady=(0, 10))
        
        # 타이틀
        title_label = ctk.CTkLabel(
            card,
            text=title,
            font=ctk.CTkFont(family=self.korean_font, size=16, weight="bold"),
            text_color=self.colors['text']
        )
        title_label.pack(anchor='w', padx=20, pady=(15, 10))
        
        # 컨텐츠 프레임
        content = ctk.CTkFrame(
            card,
            fg_color='transparent'
        )
        content.pack(fill='both', expand=True, padx=20, pady=(0, 20))
        
        return content
        
    def create_stat_box(self, parent, label, value, color):
        """통계 박스 생성"""
        box = ctk.CTkFrame(
            parent,
            corner_radius=10,
            fg_color='transparent',
            border_width=1,
            border_color=color
        )
        box.pack(side='left', fill='x', expand=True, padx=5)
        
        # 라벨
        label_widget = ctk.CTkLabel(
            box,
            text=label,
            font=ctk.CTkFont(family=self.korean_font, size=12),
            text_color=color
        )
        label_widget.pack(pady=(10, 5))
        
        # 값
        value_widget = ctk.CTkLabel(
            box,
            text=value,
            font=ctk.CTkFont(family=self.korean_font, size=20, weight="bold"),
            text_color=self.colors['text']
        )
        value_widget.pack(pady=(0, 10))
        
        # 위젯 저장
        setattr(self, f"{label.split()[1]}_stat", value_widget)
        
    def select_file(self):
        """파일 선택"""
        filename = filedialog.askopenfilename(
            title="입찰 파일 선택",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filename:
            self.input_file = filename
            self.file_label.configure(text=os.path.basename(filename))
            self.file_button.configure(text="✓ 파일 선택됨")
            self.log(f"파일 로드: {os.path.basename(filename)}", "INFO")
            
    def start_processing(self):
        """가격 조정 시작"""
        if not self.input_file:
            messagebox.showwarning("경고", "파일을 먼저 선택해주세요!")
            return
            
        # UI 상태 변경
        self.processing = True
        self.start_button.configure(state='disabled', text="처리 중...")
        
        # 별도 스레드에서 처리
        thread = threading.Thread(target=self.process_file, daemon=True)
        thread.start()
        
    def process_file(self):
        """파일 처리 (별도 스레드)"""
        try:
            # 파일 읽기
            self.log("파일 처리 시작...", "INFO")
            
            with open(self.input_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            # 헤더와 데이터 분리
            data_lines = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith('=') and not line.startswith('💡') and not line.startswith('Total'):
                    if ',' in line:
                        data_lines.append(line)
                        
            total_items = len(data_lines)
            self.log(f"총 {total_items}개 항목 발견", "INFO")
            
            # 통계 초기화
            success_count = 0
            fail_count = 0
            
            # 각 항목 처리
            for i, line in enumerate(data_lines):
                try:
                    # 진행률 업데이트
                    progress = (i + 1) / total_items
                    self.root.after(0, self.update_progress, progress, i+1, total_items)
                    
                    # 데이터 파싱
                    parts = line.split(',')
                    if len(parts) >= 5:
                        brand = parts[0].strip()
                        code = parts[1].strip()
                        color = parts[2].strip()
                        size = parts[3].strip()
                        price = int(parts[4].strip())
                        
                        # 가격 조정
                        adjusted_price = self.calculate_adjusted_price(price)
                        
                        if adjusted_price > 0:
                            # 성공
                            self.output_data.append({
                                'brand': brand,
                                'code': code,
                                'color': color,
                                'size': size,
                                'original': price,
                                'adjusted': adjusted_price
                            })
                            success_count += 1
                            self.log(f"✓ #{i+1} {code} - {size}: {price}원 → {adjusted_price}원", "SUCCESS")
                        else:
                            # 실패 (음수 가격)
                            fail_count += 1
                            self.log(f"✗ #{i+1} {code} - {size}: 음수 가격 발생 ({adjusted_price}원)", "ERROR")
                            
                except Exception as e:
                    fail_count += 1
                    self.log(f"✗ #{i+1} 처리 오류: {str(e)}", "ERROR")
                    
                # 통계 업데이트
                self.root.after(0, self.update_stats, success_count, fail_count, total_items - i - 1)
                
            # 완료
            self.log(f"\n처리 완료! 성공: {success_count}, 실패: {fail_count}", "INFO")
            
            # 결과 저장
            if self.output_data:
                self.save_results()
                
        except Exception as e:
            self.log(f"치명적 오류: {str(e)}", "ERROR")
            
        finally:
            # UI 복원
            self.root.after(0, self.processing_complete)
            
    def calculate_adjusted_price(self, original_price):
        """가격 조정 계산"""
        price = original_price
        
        # 1. 쿠폰 할인
        coupon = self.coupon_var.get()
        if coupon != "없음":
            discount_rate = int(coupon.replace('%', '')) / 100
            price = price * (1 - discount_rate)
            
        # 2. 적립금/포인트
        points = self.points_var.get()
        if points != "없음":
            discount_rate = int(points.replace('%', '')) / 100
            price = price * (1 - discount_rate)
            
        # 3. 무신사 카드 프리미엄
        if self.premium_var.get():
            try:
                min_amount = int(self.premium_min.get() or 0)
                discount_amount = int(self.premium_discount.get() or 0)
                
                if price >= min_amount:
                    price = price - discount_amount
                else:
                    # 비례 배분
                    discount_ratio = price / min_amount
                    price = price - (discount_amount * discount_ratio)
            except:
                pass
                
        # 4. 카드 캐시백
        cashback = self.cashback_var.get()
        if cashback != "없음":
            discount_rate = int(cashback.replace('%', '')) / 100
            price = price * (1 - discount_rate)
            
        return int(price)
        
    def save_results(self):
        """결과 저장"""
        # 출력 파일명
        base_name = os.path.splitext(self.input_file)[0]
        output_file = f"{base_name}_adjusted.txt"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            # 헤더
            f.write("=== 가격 조정 완료 ===\n")
            f.write(f"조정 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"쿠폰: {self.coupon_var.get()}, 적립금: {self.points_var.get()}, ")
            f.write(f"캐시백: {self.cashback_var.get()}\n")
            f.write("=" * 50 + "\n\n")
            
            # 데이터
            for item in self.output_data:
                f.write(f"{item['brand']},{item['code']},{item['color']},{item['size']},{item['adjusted']}\n")
                
            # 총 개수
            f.write(f"\nTotal: {len(self.output_data)} items")
            
        self.log(f"결과 저장: {output_file}", "SUCCESS")
        
    def update_progress(self, value, current, total):
        """진행률 업데이트"""
        self.progress.set(value)
        self.progress_label.configure(text=f"처리 중: {current}/{total} ({int(value*100)}%)")
        
    def update_stats(self, success, fail, remain):
        """통계 업데이트"""
        self.성공_stat.configure(text=str(success))
        self.실패_stat.configure(text=str(fail))
        self.대기_stat.configure(text=str(remain))
        
    def processing_complete(self):
        """처리 완료"""
        self.processing = False
        self.start_button.configure(state='normal', text="🚀 가격 조정 시작")
        self.progress_label.configure(text="처리 완료!")
        
        # 완료 메시지
        if self.output_data:
            messagebox.showinfo("완료", f"가격 조정이 완료되었습니다!\n\n성공: {len(self.output_data)}개 항목")
            
    def log(self, message, level="INFO"):
        """로그 추가"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_queue.put((timestamp, message, level))
        
    def update_logs(self):
        """로그 업데이트"""
        try:
            while True:
                timestamp, message, level = self.log_queue.get_nowait()
                
                # 색상 설정
                if level == "SUCCESS":
                    color = self.colors['success']
                elif level == "ERROR":
                    color = self.colors['error']
                elif level == "WARNING":
                    color = self.colors['warning']
                else:
                    color = self.colors['text']
                    
                # 로그 추가
                self.log_text.insert('end', f"[{timestamp}] {message}\n")
                self.log_text.see('end')
                
        except queue.Empty:
            pass
            
        # 100ms 후 다시 실행
        self.root.after(100, self.update_logs)
        
    def run(self):
        """프로그램 실행"""
        self.root.mainloop()


if __name__ == "__main__":
    app = PriceAdjusterGUI()
    app.run()
