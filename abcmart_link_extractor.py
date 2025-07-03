"""
ABC마트/그랜드스테이지 상품 링크 추출기
- URL 기반 상품 검색 (ABC마트, 그랜드스테이지 지원)
- 모든 페이지 순회하며 상품 링크 추출
- 10페이지 이상도 자동으로 끝까지 추출
- 결과를 파일로 저장
"""

import re
import time
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import threading
import os

class ABCMartLinkExtractor:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("ABC마트/그랜드스테이지 링크 추출기")
        self.root.geometry("900x700")
        
        # 스타일 설정
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        self.driver = None
        self.links = set()
        self.running = False
        
        self.setup_ui()
        
    def setup_ui(self):
        """UI 구성"""
        # 상단 프레임 - URL 입력
        top_frame = ttk.LabelFrame(self.root, text="URL 설정", padding="10")
        top_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # URL 입력
        url_frame = ttk.Frame(top_frame)
        url_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(url_frame, text="URL:").pack(side=tk.LEFT, padx=(0, 5))
        self.url_entry = ttk.Entry(url_frame, width=80)
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        # 예시 URL 라벨
        example_label = ttk.Label(top_frame, text="예시: https://abcmart.a-rt.com/display/search-word/result?searchWord=뉴발란스...", 
                                 foreground="gray")
        example_label.pack(anchor=tk.W, pady=(0, 5))
        
        # 대기 시간 설정
        wait_frame = ttk.Frame(top_frame)
        wait_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(wait_frame, text="페이지 로딩 대기:").pack(side=tk.LEFT, padx=(0, 5))
        self.wait_var = tk.IntVar(value=3)
        ttk.Spinbox(wait_frame, from_=1, to=10, textvariable=self.wait_var, width=10).pack(side=tk.LEFT)
        ttk.Label(wait_frame, text="초").pack(side=tk.LEFT, padx=(5, 0))
        
        # 버튼 프레임
        button_frame = ttk.Frame(self.root)
        button_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.extract_btn = ttk.Button(
            button_frame, 
            text="추출 시작", 
            command=self.start_extraction,
            style="Accent.TButton"
        )
        self.extract_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.stop_btn = ttk.Button(
            button_frame, 
            text="중지", 
            command=self.stop_extraction,
            state='disabled'
        )
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(button_frame, text="결과 저장", command=self.save_results).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="결과 지우기", command=self.clear_results).pack(side=tk.LEFT)
        
        # 진행 상황
        self.progress = ttk.Progressbar(self.root, mode='determinate')
        self.progress.pack(fill=tk.X, padx=10, pady=5)
        
        # 상태 표시
        self.status_label = ttk.Label(self.root, text="준비", relief=tk.SUNKEN)
        self.status_label.pack(fill=tk.X, padx=10, pady=5)
        
        # 로그 영역
        log_frame = ttk.LabelFrame(self.root, text="추출 로그", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 결과 통계
        stats_frame = ttk.Frame(self.root)
        stats_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.stats_label = ttk.Label(stats_frame, text="추출된 링크: 0개")
        self.stats_label.pack(side=tk.LEFT)
        
    def start_extraction(self):
        """추출 시작"""
        base_url = self.url_entry.get().strip()
        if not base_url:
            messagebox.showwarning("경고", "URL을 입력하세요.")
            return
        
        # URL 유효성 검사
        if not any(domain in base_url for domain in ['abcmart.a-rt.com', 'grandstage.a-rt.com']):
            messagebox.showwarning("경고", "ABC마트 또는 그랜드스테이지 URL을 입력하세요.")
            return
        
        # UI 상태 변경
        self.extract_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        self.links.clear()
        self.log_text.delete(1.0, tk.END)
        
        # 별도 스레드에서 실행
        thread = threading.Thread(target=self._extraction_worker, args=(base_url,))
        thread.daemon = True
        thread.start()
        
    def _extraction_worker(self, base_url):
        """추출 작업 실행"""
        try:
            self.running = True
            self.log_message(f"URL로 추출 시작...")
            
            # 드라이버 설정
            self.log_message("크롬 드라이버 초기화 중...")
            options = uc.ChromeOptions()
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
            
            self.driver = uc.Chrome(options=options, version_main=None)
            
            wait_time = self.wait_var.get()
            
            # URL에서 page 파라미터 제거
            from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
            parsed = urlparse(base_url)
            params = parse_qs(parsed.query)
            
            # page 파라미터 제거
            if 'page' in params:
                del params['page']
            
            page = 1
            
            while self.running:
                # 현재 페이지 URL 생성
                current_params = params.copy()
                current_params['page'] = [str(page)]
                
                # URL 재구성
                new_query = urlencode(current_params, doseq=True)
                current_url = urlunparse((
                    parsed.scheme,
                    parsed.netloc,
                    parsed.path,
                    parsed.params,
                    new_query,
                    parsed.fragment
                ))
                
                self.log_message(f"\n페이지 {page} 로드 중...")
                self.driver.get(current_url)
                time.sleep(wait_time)
                
                # 상품 링크 추출
                links = self.extract_links_from_page()
                before = len(self.links)
                self.links.update(links)
                after = len(self.links)
                
                self.log_message(f"페이지 {page}: {after - before}개 새 링크 발견 (총 {after}개)")
                
                # 진행률 업데이트
                self.progress['value'] = page % 100  # 100으로 나눈 나머지로 표시
                self.stats_label.config(text=f"추출된 링크: {after}개 (페이지 {page})")
                
                # 페이지가 비어있으면 즉시 종료
                if len(links) == 0:
                    self.log_message("더 이상 상품이 없습니다.")
                    break
                
                page += 1
                
            # 완료
            self.log_message(f"\n추출 완료! 총 {len(self.links)}개 링크")
            self.status_label.config(text=f"완료 - {len(self.links)}개 링크 추출됨 (총 {page-1}페이지)")
            
        except Exception as e:
            self.log_message(f"\n오류 발생: {e}")
            messagebox.showerror("오류", f"추출 중 오류 발생: {e}")
        finally:
            self.running = False
            if self.driver:
                self.driver.quit()
                self.driver = None
            
            # UI 복원
            self.root.after(0, self._restore_ui)
            
    def extract_links_from_page(self):
        """현재 페이지에서 링크 추출"""
        links = set()
        
        try:
            # 여러 선택자로 시도
            selectors = [
                'a[href*="product?prdtNo="]',
                'a[href*="prdtNo="]',
                '.item-list a[href]',
                '.search-list-wrap a[href]'
            ]
            
            for selector in selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    href = elem.get_attribute('href')
                    if href and 'prdtNo=' in href:
                        # 상품 번호 추출
                        match = re.search(r'prdtNo=(\d+)', href)
                        if match:
                            product_id = match.group(1)
                            # 표준 형식으로 저장
                            links.add(f"https://abcmart.a-rt.com/product?prdtNo={product_id}")
                            
        except Exception as e:
            self.log_message(f"링크 추출 오류: {e}")
            
        return links
        
    def stop_extraction(self):
        """추출 중지"""
        self.running = False
        self.log_message("\n사용자가 추출을 중지했습니다.")
        self.status_label.config(text="중지됨")
        
    def save_results(self):
        """결과 저장"""
        if not self.links:
            messagebox.showwarning("경고", "저장할 링크가 없습니다.")
            return
        
        # 파일 형식 선택
        file_types = [
            ("텍스트 파일", "*.txt"),
            ("JSON 파일", "*.json"),
            ("모든 파일", "*.*")
        ]
        
        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=file_types,
            initialfile=f"abcmart_links_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        
        if filepath:
            try:
                # URL에서 사이트 정보 추출
                url = self.url_entry.get()
                if 'grandstage' in url:
                    site_name = "그랜드스테이지"
                else:
                    site_name = "ABC마트"
                
                if filepath.endswith('.json'):
                    # JSON 형식으로 저장
                    data = {
                        "extraction_time": datetime.now().isoformat(),
                        "source_url": url,
                        "site": site_name,
                        "total_count": len(self.links),
                        "links": sorted(list(self.links))
                    }
                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                else:
                    # 텍스트 형식으로 저장
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(f"# {site_name} 상품 링크\n")
                        f.write(f"# URL: {url}\n")
                        f.write(f"# 추출 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                        f.write(f"# 총 {len(self.links)}개\n")
                        f.write("=" * 50 + "\n\n")
                        for link in sorted(self.links):
                            f.write(f"{link}\n")
                
                messagebox.showinfo("성공", f"파일이 저장되었습니다:\n{filepath}")
                self.log_message(f"\n결과가 저장되었습니다: {filepath}")
            except Exception as e:
                messagebox.showerror("오류", f"저장 실패: {e}")
                
    def clear_results(self):
        """결과 지우기"""
        self.links.clear()
        self.log_text.delete(1.0, tk.END)
        self.stats_label.config(text="추출된 링크: 0개")
        self.progress['value'] = 0
        self.status_label.config(text="준비")
        self.log_message("결과가 지워졌습니다.")
        
    def log_message(self, message):
        """로그 메시지 추가"""
        self.root.after(0, lambda: self._add_log(message))
        
    def _add_log(self, message):
        """로그 추가 (UI 스레드)"""
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        
    def _restore_ui(self):
        """UI 복원"""
        self.extract_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        
    def run(self):
        """프로그램 실행"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 커스텀 스타일
        self.style.configure("Accent.TButton", foreground="white", background="#007ACC")
        
        self.root.mainloop()
        
    def on_closing(self):
        """프로그램 종료"""
        if self.driver:
            self.driver.quit()
        self.root.destroy()


if __name__ == "__main__":
    app = ABCMartLinkExtractor()
    app.run()
