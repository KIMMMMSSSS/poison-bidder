"""
무신사 상품 링크 추출기 (통합 버전)
- URL 입력으로 자동 추출
- HTML 직접 입력
- 파일에서 불러오기
- 다양한 포맷 지원
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

class MusinsaLinkExtractorPro:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("무신사 링크 추출기 Pro")
        self.root.geometry("1000x700")
        
        # 스타일 설정
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        self.driver = None
        self.links = set()
        self.running = False
        
        self.setup_ui()
        
    def setup_ui(self):
        """UI 구성"""
        # 노트북 (탭) 위젯
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 탭 1: URL 추출
        self.url_tab = ttk.Frame(notebook)
        notebook.add(self.url_tab, text="URL에서 추출")
        self.setup_url_tab()
        
        # 탭 2: HTML 추출
        self.html_tab = ttk.Frame(notebook)
        notebook.add(self.html_tab, text="HTML에서 추출")
        self.setup_html_tab()
        
        # 탭 3: 파일 추출
        self.file_tab = ttk.Frame(notebook)
        notebook.add(self.file_tab, text="파일에서 추출")
        self.setup_file_tab()
        
        # 탭 4: 결과 및 내보내기
        self.result_tab = ttk.Frame(notebook)
        notebook.add(self.result_tab, text="결과")
        self.setup_result_tab()
        
        # 하단 상태바
        self.status_label = ttk.Label(self.root, text="준비", relief=tk.SUNKEN)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)
        
    def setup_url_tab(self):
        """URL 탭 설정"""
        # 설명
        info_frame = ttk.LabelFrame(self.url_tab, text="URL 자동 추출", padding="10")
        info_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(info_frame, text="무신사 검색 결과나 카테고리 페이지 URL을 입력하세요.").pack(anchor=tk.W)
        
        # URL 입력
        url_frame = ttk.Frame(self.url_tab)
        url_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(url_frame, text="URL:").pack(side=tk.LEFT, padx=(0, 5))
        self.url_entry = ttk.Entry(url_frame, width=60)
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.url_entry.insert(0, "https://www.musinsa.com/search/goods?keyword=")
        
        # 옵션
        option_frame = ttk.LabelFrame(self.url_tab, text="옵션", padding="10")
        option_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 스크롤 횟수
        scroll_frame = ttk.Frame(option_frame)
        scroll_frame.pack(anchor=tk.W)
        ttk.Label(scroll_frame, text="최대 스크롤 횟수:").pack(side=tk.LEFT, padx=(0, 5))
        self.scroll_var = tk.IntVar(value=10)
        ttk.Spinbox(scroll_frame, from_=1, to=50, textvariable=self.scroll_var, width=10).pack(side=tk.LEFT)
        ttk.Label(scroll_frame, text="(무한 스크롤 페이지용)").pack(side=tk.LEFT, padx=(10, 0))
        
        # 대기 시간
        wait_frame = ttk.Frame(option_frame)
        wait_frame.pack(anchor=tk.W, pady=(5, 0))
        ttk.Label(wait_frame, text="페이지 로딩 대기:").pack(side=tk.LEFT, padx=(0, 5))
        self.wait_var = tk.IntVar(value=3)
        ttk.Spinbox(wait_frame, from_=1, to=10, textvariable=self.wait_var, width=10).pack(side=tk.LEFT)
        ttk.Label(wait_frame, text="초").pack(side=tk.LEFT, padx=(5, 0))
        
        # 버튼
        button_frame = ttk.Frame(self.url_tab)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.extract_url_btn = ttk.Button(
            button_frame, 
            text="추출 시작", 
            command=self.extract_from_url,
            style="Accent.TButton"
        )
        self.extract_url_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.stop_url_btn = ttk.Button(
            button_frame, 
            text="중지", 
            command=self.stop_extraction,
            state='disabled'
        )
        self.stop_url_btn.pack(side=tk.LEFT)
        
        # 진행 상황
        self.url_progress = ttk.Progressbar(self.url_tab, mode='indeterminate')
        self.url_progress.pack(fill=tk.X, padx=10, pady=5)
        
        # 로그
        log_frame = ttk.LabelFrame(self.url_tab, text="추출 로그", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.url_log = scrolledtext.ScrolledText(log_frame, height=15)
        self.url_log.pack(fill=tk.BOTH, expand=True)
        
    def setup_html_tab(self):
        """HTML 탭 설정"""
        # 설명
        info_frame = ttk.LabelFrame(self.html_tab, text="HTML 코드에서 추출", padding="10")
        info_frame.pack(fill=tk.X, padx=10, pady=10)
        
        info_text = """1. 무신사 페이지에서 F12 (개발자 도구)
2. Elements 탭에서 상품 목록 영역 선택
3. 우클릭 → Copy → Copy outerHTML
4. 아래에 붙여넣기"""
        ttk.Label(info_frame, text=info_text).pack(anchor=tk.W)
        
        # 버튼
        button_frame = ttk.Frame(self.html_tab)
        button_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(
            button_frame, 
            text="클립보드에서 붙여넣기", 
            command=self.paste_html
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(
            button_frame, 
            text="링크 추출", 
            command=self.extract_from_html,
            style="Accent.TButton"
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(
            button_frame, 
            text="지우기", 
            command=self.clear_html
        ).pack(side=tk.LEFT)
        
        # HTML 입력
        html_frame = ttk.LabelFrame(self.html_tab, text="HTML 입력", padding="10")
        html_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.html_text = scrolledtext.ScrolledText(html_frame, wrap=tk.WORD)
        self.html_text.pack(fill=tk.BOTH, expand=True)
        
    def setup_file_tab(self):
        """파일 탭 설정"""
        # 설명
        info_frame = ttk.LabelFrame(self.file_tab, text="파일에서 추출", padding="10")
        info_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(info_frame, text="HTML 파일 또는 이전에 추출한 링크 파일을 불러올 수 있습니다.").pack(anchor=tk.W)
        
        # 파일 선택
        file_frame = ttk.Frame(self.file_tab)
        file_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.file_path_var = tk.StringVar()
        ttk.Label(file_frame, text="파일:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Entry(file_frame, textvariable=self.file_path_var, width=50).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(file_frame, text="찾아보기", command=self.browse_file).pack(side=tk.LEFT)
        
        # 추출 버튼
        ttk.Button(
            self.file_tab, 
            text="파일에서 추출", 
            command=self.extract_from_file,
            style="Accent.TButton"
        ).pack(pady=10)
        
        # 미리보기
        preview_frame = ttk.LabelFrame(self.file_tab, text="파일 미리보기", padding="10")
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.file_preview = scrolledtext.ScrolledText(preview_frame)
        self.file_preview.pack(fill=tk.BOTH, expand=True)
        
    def setup_result_tab(self):
        """결과 탭 설정"""
        # 통계
        stats_frame = ttk.LabelFrame(self.result_tab, text="추출 통계", padding="10")
        stats_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.stats_label = ttk.Label(stats_frame, text="아직 추출된 링크가 없습니다.")
        self.stats_label.pack(anchor=tk.W)
        
        # 버튼
        button_frame = ttk.Frame(self.result_tab)
        button_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(button_frame, text="TXT로 저장", command=self.save_as_txt).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="JSON으로 저장", command=self.save_as_json).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="클립보드로 복사", command=self.copy_to_clipboard).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="무신사 형식으로 변환", command=self.convert_to_musinsa_format).pack(side=tk.LEFT)
        
        # 결과 표시
        result_frame = ttk.LabelFrame(self.result_tab, text="추출된 링크", padding="10")
        result_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.result_text = scrolledtext.ScrolledText(result_frame)
        self.result_text.pack(fill=tk.BOTH, expand=True)
        
    def extract_from_url(self):
        """URL에서 추출"""
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("경고", "URL을 입력하세요.")
            return
        
        # UI 상태 변경
        self.extract_url_btn.config(state='disabled')
        self.stop_url_btn.config(state='normal')
        self.url_progress.start()
        self.url_log.delete(1.0, tk.END)
        
        # 별도 스레드에서 실행
        thread = threading.Thread(target=self._extract_url_worker, args=(url,))
        thread.daemon = True
        thread.start()
    
    def _extract_url_worker(self, url):
        """URL 추출 워커"""
        try:
            self.running = True
            self.links.clear()
            
            # 드라이버 설정
            self.log_message("크롬 드라이버 초기화 중...")
            options = uc.ChromeOptions()
            
            # 안정성을 위한 추가 옵션
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
            
            # version_main=None은 자동으로 현재 설치된 Chrome 버전을 감지
            self.driver = uc.Chrome(options=options, version_main=None)
            
            # 추가 보안 설정
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
                    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
                    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
                '''
            })
            
            # 페이지 로드
            self.log_message(f"페이지 로드 중: {url}")
            self.driver.get(url)
            time.sleep(self.wait_var.get())
            
            # 스크롤하면서 추출
            max_scrolls = self.scroll_var.get()
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            
            for i in range(max_scrolls):
                if not self.running:
                    break
                
                # 링크 추출
                self.log_message(f"스크롤 {i+1}/{max_scrolls} - 링크 추출 중...")
                links = self.extract_links_from_page()
                before = len(self.links)
                self.links.update(links)
                after = len(self.links)
                self.log_message(f"  → {after - before}개 새 링크 발견 (총 {after}개)")
                
                # 스크롤
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                
                # 높이 확인
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    self.log_message("페이지 끝 도달")
                    break
                last_height = new_height
            
            # 완료
            self.log_message(f"\n추출 완료! 총 {len(self.links)}개 링크")
            self.update_results()
            
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
        
        # 다양한 선택자로 시도
        selectors = [
            "a[href*='/products/']",
            "a.gtm-select-item",
            "a[data-item-id]",
            "[class*='goods'] a[href*='products']"
        ]
        
        for selector in selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    href = elem.get_attribute('href')
                    if href and '/products/' in href:
                        match = re.search(r'/products/(\d+)', href)
                        if match:
                            product_id = match.group(1)
                            links.add(f"https://www.musinsa.com/products/{product_id}")
            except:
                continue
        
        return links
    
    def extract_from_html(self):
        """HTML에서 추출"""
        html = self.html_text.get(1.0, tk.END).strip()
        if not html:
            messagebox.showwarning("경고", "HTML을 입력하세요.")
            return
        
        self.links.clear()
        
        # 패턴 매칭
        patterns = [
            r'href=["\']([^"\']*?/products/\d+)["\']',
            r'data-item-id=["\'](\d+)["\']',
            r'/products/(\d+)'
        ]
        
        found_ids = set()
        for pattern in patterns:
            matches = re.findall(pattern, html)
            for match in matches:
                if match.isdigit():
                    found_ids.add(match)
                else:
                    id_match = re.search(r'/products/(\d+)', match)
                    if id_match:
                        found_ids.add(id_match.group(1))
        
        # 링크 생성
        for product_id in found_ids:
            self.links.add(f"https://www.musinsa.com/products/{product_id}")
        
        self.update_results()
        self.status_label.config(text=f"{len(self.links)}개 링크 추출 완료")
        
        if not self.links:
            messagebox.showinfo("결과", "추출된 링크가 없습니다.")
    
    def extract_from_file(self):
        """파일에서 추출"""
        filepath = self.file_path_var.get()
        if not filepath or not os.path.exists(filepath):
            messagebox.showwarning("경고", "유효한 파일을 선택하세요.")
            return
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 파일 형식에 따라 처리
            if filepath.endswith('.json'):
                data = json.loads(content)
                if isinstance(data, list):
                    self.links = set(data)
                else:
                    messagebox.showerror("오류", "올바른 JSON 형식이 아닙니다.")
                    return
            else:
                # HTML 또는 텍스트로 처리
                self.html_text.delete(1.0, tk.END)
                self.html_text.insert(1.0, content)
                self.extract_from_html()
                return
            
            self.update_results()
            self.status_label.config(text=f"{len(self.links)}개 링크 불러오기 완료")
            
        except Exception as e:
            messagebox.showerror("오류", f"파일 읽기 실패: {e}")
    
    def update_results(self):
        """결과 업데이트"""
        # 통계 업데이트
        if self.links:
            stats_text = f"""총 링크 수: {len(self.links)}개
추출 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            self.stats_label.config(text=stats_text)
        else:
            self.stats_label.config(text="아직 추출된 링크가 없습니다.")
        
        # 결과 표시
        self.result_text.delete(1.0, tk.END)
        if self.links:
            for link in sorted(self.links):
                self.result_text.insert(tk.END, f"{link}\n")
    
    def save_as_txt(self):
        """TXT로 저장"""
        if not self.links:
            messagebox.showwarning("경고", "저장할 링크가 없습니다.")
            return
        
        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("텍스트 파일", "*.txt"), ("모든 파일", "*.*")],
            initialfile=f"musinsa_links_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        
        if filepath:
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(f"# 무신사 상품 링크\n")
                    f.write(f"# 추출 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"# 총 {len(self.links)}개\n")
                    f.write("=" * 50 + "\n\n")
                    for link in sorted(self.links):
                        f.write(f"{link}\n")
                
                messagebox.showinfo("성공", f"파일이 저장되었습니다:\n{filepath}")
            except Exception as e:
                messagebox.showerror("오류", f"저장 실패: {e}")
    
    def save_as_json(self):
        """JSON으로 저장"""
        if not self.links:
            messagebox.showwarning("경고", "저장할 링크가 없습니다.")
            return
        
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON 파일", "*.json"), ("모든 파일", "*.*")],
            initialfile=f"musinsa_links_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        if filepath:
            try:
                data = {
                    "extraction_time": datetime.now().isoformat(),
                    "total_count": len(self.links),
                    "links": sorted(list(self.links))
                }
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                messagebox.showinfo("성공", f"파일이 저장되었습니다:\n{filepath}")
            except Exception as e:
                messagebox.showerror("오류", f"저장 실패: {e}")
    
    def convert_to_musinsa_format(self):
        """무신사 스크래퍼 형식으로 변환"""
        if not self.links:
            messagebox.showwarning("경고", "변환할 링크가 없습니다.")
            return
        
        # urls.txt 형식으로 저장
        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("텍스트 파일", "*.txt")],
            initialfile="urls.txt"
        )
        
        if filepath:
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    for link in sorted(self.links):
                        f.write(f"{link}\n")
                
                messagebox.showinfo(
                    "성공", 
                    f"urls.txt 형식으로 저장되었습니다.\n"
                    f"이제 무신사 스크래퍼에서 사용할 수 있습니다.\n\n"
                    f"파일: {filepath}"
                )
            except Exception as e:
                messagebox.showerror("오류", f"저장 실패: {e}")
    
    def copy_to_clipboard(self):
        """클립보드로 복사"""
        if not self.links:
            messagebox.showwarning("경고", "복사할 링크가 없습니다.")
            return
        
        try:
            import pyperclip
            text = "\n".join(sorted(self.links))
            pyperclip.copy(text)
            messagebox.showinfo("성공", f"{len(self.links)}개 링크가 클립보드에 복사되었습니다.")
        except ImportError:
            # pyperclip이 없으면 기본 방법 사용
            self.root.clipboard_clear()
            self.root.clipboard_append("\n".join(sorted(self.links)))
            messagebox.showinfo("성공", f"{len(self.links)}개 링크가 클립보드에 복사되었습니다.")
    
    def paste_html(self):
        """HTML 붙여넣기"""
        try:
            import pyperclip
            text = pyperclip.paste()
        except:
            text = self.root.clipboard_get()
        
        if text:
            self.html_text.delete(1.0, tk.END)
            self.html_text.insert(1.0, text)
            self.status_label.config(text="클립보드에서 붙여넣기 완료")
    
    def clear_html(self):
        """HTML 지우기"""
        self.html_text.delete(1.0, tk.END)
    
    def browse_file(self):
        """파일 찾아보기"""
        filepath = filedialog.askopenfilename(
            filetypes=[
                ("모든 지원 파일", "*.txt;*.html;*.json"),
                ("텍스트 파일", "*.txt"),
                ("HTML 파일", "*.html"),
                ("JSON 파일", "*.json"),
                ("모든 파일", "*.*")
            ]
        )
        
        if filepath:
            self.file_path_var.set(filepath)
            
            # 미리보기
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read(1000)  # 처음 1000자만
                    if len(f.read(1)) > 0:  # 더 있으면
                        content += "\n\n... (더 많은 내용)"
                
                self.file_preview.delete(1.0, tk.END)
                self.file_preview.insert(1.0, content)
            except Exception as e:
                self.file_preview.delete(1.0, tk.END)
                self.file_preview.insert(1.0, f"파일 읽기 오류: {e}")
    
    def stop_extraction(self):
        """추출 중지"""
        self.running = False
        self.status_label.config(text="중지됨")
    
    def log_message(self, message):
        """로그 메시지 추가"""
        self.root.after(0, lambda: self._add_log(message))
    
    def _add_log(self, message):
        """로그 추가 (UI 스레드)"""
        self.url_log.insert(tk.END, f"{message}\n")
        self.url_log.see(tk.END)
    
    def _restore_ui(self):
        """UI 복원"""
        self.extract_url_btn.config(state='normal')
        self.stop_url_btn.config(state='disabled')
        self.url_progress.stop()
    
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
    app = MusinsaLinkExtractorPro()
    app.run()
