import time
import re
import json
import os
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from datetime import datetime
from multiprocessing import Process, Queue, Manager
from scraper_logger import ScraperLogger
from pathlib import Path
import sys

def close_abcmart_popup(driver, worker_id=None):
    """
    ABC마트 팝업 처리 유틸리티 함수 (현재는 사용하지 않음)
    
    Args:
        driver: Selenium WebDriver 인스턴스
        worker_id: 워커 ID (로깅용, 선택사항)
    
    Returns:
        bool: 팝업이 닫혔으면 True, 팝업이 없었으면 False
    """
    # ABC마트는 팝업 처리가 필요 없음
    return False

class AbcmartWorker:
    """개별 워커 프로세스"""
    def __init__(self, worker_id, headless=True):
        self.worker_id = worker_id
        self.headless = headless
        self.driver = None
        self.wait = None
        
    def setup_driver(self):
        """Chrome 드라이버 설정 (개선된 충돌 방지)"""
        max_retries = 3  # 재시도 횟수 줄임
        retry_delay = 0.2  # 재시도 지연 더 단축
        
        for attempt in range(max_retries):
            try:
                print(f"[Worker {self.worker_id}] Chrome 드라이버 초기화 중... (시도 {attempt + 1}/{max_retries})")
                
                options = uc.ChromeOptions()
                
                # 기본 설정
                if self.headless:  # 모든 워커 헤드리스로
                    options.add_argument('--headless')
                
                options.add_argument('--start-maximized')
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                options.add_argument('--disable-gpu')
                options.add_argument('--log-level=3')
                options.add_argument('--disable-blink-features=AutomationControlled')
                
                # User-Agent 설정
                options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
                
                # 리소스 차단 설정 (속도 최적화)
                options.add_argument('--blink-settings=imagesEnabled=false')  # 이미지 차단
                options.add_experimental_option("prefs", {
                    "profile.default_content_setting_values": {
                        "images": 2,  # 이미지 차단
                        "plugins": 2,  # 플러그인 차단
                        "popups": 2,  # 팝업 차단
                        "geolocation": 2,  # 위치 차단
                        "notifications": 2,  # 알림 차단
                        "media_stream": 2,  # 미디어 차단
                        "javascript": 1  # JS는 켜두기 (필수)
                    },
                    "profile.managed_default_content_settings": {
                        "images": 2,
                        # "stylesheet": 2  # CSS는 레이아웃 문제로 주석 처리
                    }
                })
                
                # 추가 성능 최적화 옵션
                options.add_argument('--disable-web-security')
                options.add_argument('--disable-features=VizDisplayCompositor')
                options.add_argument('--disable-dev-tools')
                options.add_argument('--disable-extensions')
                options.add_argument('--disable-default-apps')
                options.add_argument('--disable-sync')
                options.add_argument('--disable-translate')
                options.add_argument('--metrics-recording-only')
                options.add_argument('--no-first-run')
                options.add_argument('--safebrowsing-disable-auto-update')
                options.add_argument('--disable-background-networking')
                
                # 페이지 로드 전략 설정 (DOM 로드 완료시 즉시 진행)
                options.page_load_strategy = 'eager'
                
                # 각 워커별로 고유한 설정
                import tempfile
                import os
                import shutil
                import glob
                
                # 워커별 고유 사용자 데이터 디렉토리
                user_data_dir = os.path.join(tempfile.gettempdir(), f'chrome_worker_{self.worker_id}_{os.getpid()}')
                if os.path.exists(user_data_dir):
                    shutil.rmtree(user_data_dir, ignore_errors=True)
                os.makedirs(user_data_dir, exist_ok=True)
                options.add_argument(f'--user-data-dir={user_data_dir}')
                
                # 워커별 고유 포트 설정 (충돌 방지)
                port = 9222 + self.worker_id
                options.add_argument(f'--remote-debugging-port={port}')
                
                # undetected_chromedriver의 chromedriver 경로 찾기
                uc_paths = [
                    os.path.join(os.environ.get('APPDATA', ''), 'undetected_chromedriver', 'undetected_chromedriver.exe'),
                    os.path.join(os.environ.get('LOCALAPPDATA', ''), 'undetected_chromedriver', 'chromedriver.exe'),
                    os.path.join(os.path.expanduser('~'), '.undetected_chromedriver', 'chromedriver.exe'),
                ]
                
                # 가능한 모든 경로에서 chromedriver 찾기
                existing_driver = None
                for path in uc_paths:
                    if os.path.exists(path):
                        existing_driver = path
                        break
                
                # 기존 chromedriver를 찾았으면 워커별 복사본 생성
                if existing_driver:
                    driver_dir = os.path.join(tempfile.gettempdir(), f'chromedriver_worker_{self.worker_id}_{os.getpid()}')
                    os.makedirs(driver_dir, exist_ok=True)
                    driver_path = os.path.join(driver_dir, 'chromedriver.exe')
                    
                    try:
                        shutil.copy2(existing_driver, driver_path)
                        print(f"[Worker {self.worker_id}] chromedriver 복사 완료")
                        
                        # 워커별 개별 chromedriver로 실행
                        self.driver = uc.Chrome(
                            options=options, 
                            driver_executable_path=driver_path,
                            version_main=None,
                            use_subprocess=False  # 서브프로세스 사용 안함
                        )
                    except:
                        # 복사 실패시 기본 방식 사용
                        self.driver = uc.Chrome(options=options, version_main=None)
                else:
                    # chromedriver를 찾지 못했으면 기본 방식 사용
                    print(f"[Worker {self.worker_id}] 기존 chromedriver 없음, 자동 다운로드...")
                    self.driver = uc.Chrome(options=options, version_main=None)
                
                self.wait = WebDriverWait(self.driver, 10)
                
                print(f"[Worker {self.worker_id}] ✅ Chrome 드라이버 설정 완료!")
                return  # 성공시 함수 종료
                
            except (FileExistsError, PermissionError, OSError) as e:
                print(f"[Worker {self.worker_id}] Chrome 드라이버 초기화 충돌 발생: {e}")
                if attempt < max_retries - 1:
                    print(f"[Worker {self.worker_id}] {retry_delay}초 후 재시도...")
                    time.sleep(retry_delay + (self.worker_id * 0.1))  # 워커별 미세한 차이
                else:
                    print(f"[Worker {self.worker_id}] Chrome 드라이버 설정 최종 실패")
                    raise
            except Exception as e:
                print(f"[Worker {self.worker_id}] Chrome 드라이버 설정 실패: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    raise
    
    def extract_brand(self):
        """브랜드 추출"""
        try:
            # ABC마트 브랜드 링크에서 추출
            brand_elem = self.driver.find_element(By.CSS_SELECTOR, 'a[data-product-brand="link"]')
            brand_text = brand_elem.text.strip()
            
            # 브랜드명이 비어있으면 href에서 추출 시도
            if not brand_text:
                href = brand_elem.get_attribute("href")
                if "/brand/" in href:
                    brand_text = href.split("/brand/")[-1].upper()
                    
            return brand_text
        except:
            return "Unknown"
    
    def extract_product_name_and_color(self):
        """상품명 추출"""
        try:
            # ABC마트 상품명 추출 - 페이지 제목이나 h1 태그에서 찾기
            # 먼저 h1 태그 시도
            try:
                name_elem = self.driver.find_element(By.CSS_SELECTOR, "h1")
                full_name = name_elem.text.strip()
            except:
                # h1이 없으면 제목에서 추출
                full_name = self.driver.title.split(" - ")[0].strip()
            
            return full_name, ""
        except:
            return "Unknown", ""
    
    def extract_product_code(self):
        """상품 코드 추출"""
        try:
            # 스타일코드 추출
            style_elem = self.driver.find_element(By.CSS_SELECTOR, 'li[data-product="style-code"]')
            style_text = style_elem.text.strip()
            
            # "스타일코드 : " 부분 제거
            if ":" in style_text:
                style_code = style_text.split(":")[-1].strip()
            else:
                style_code = style_text.replace("스타일코드", "").strip()
            
            # 브랜드 확인 (나이키인 경우만 색상코드 추가)
            brand = self.extract_brand()
            if brand.upper() in ["NIKE", "나이키"]:
                # 색상코드 추출 - tr 태그 내부에서 찾기
                try:
                    # 방법 1: tr 태그의 data-product-area 속성으로 찾기
                    color_tr = self.driver.find_element(By.CSS_SELECTOR, 'tr[data-product-area="color-code"]')
                    color_elem = color_tr.find_element(By.CSS_SELECTOR, 'span[data-product="color-code"]')
                    color_code = color_elem.text.strip()
                    
                    # 나이키 색상코드는 숫자 형태 (예: 105, 001)
                    # 슬래시(/)가 포함된 경우 다른 브랜드의 색상코드일 가능성
                    if color_code and '/' not in color_code:
                        # 숫자만 있는 경우 색상코드로 인식
                        if re.match(r'^\d{3}$', color_code):
                            return f"{style_code}-{color_code}"
                except:
                    pass
            
            return style_code
        except:
            return "Unknown"
    
    def get_member_price(self):
        """회원 최대혜택가 추출 (tooltip-trigger 클릭 후 추출)"""
        try:
            # tooltip-trigger 찾기 (다양한 선택자 시도)
            tooltip_trigger = None
            selectors = [
                "span.tooltip-trigger.product-discount-info",
                "span.tooltip-trigger",
                ".tooltip-trigger",
                "[class*='tooltip-trigger']",
                "span[data-tooltip]",
                "[data-bs-toggle='tooltip']",
                "[data-toggle='tooltip']"
            ]
            
            for selector in selectors:
                try:
                    tooltip_trigger = self.driver.find_element(By.CSS_SELECTOR, selector)
                    print(f"[Worker {self.worker_id}] 툴팁 트리거 발견: {selector}")
                    # 트리거의 속성들 출력
                    attrs = self.driver.execute_script("""
                        var attrs = {};
                        for (var i = 0; i < arguments[0].attributes.length; i++) {
                            var attr = arguments[0].attributes[i];
                            attrs[attr.name] = attr.value;
                        }
                        return attrs;
                    """, tooltip_trigger)
                    print(f"[Worker {self.worker_id}] 트리거 속성: {attrs}")
                    break
                except:
                    continue
            
            if not tooltip_trigger:
                print(f"[Worker {self.worker_id}] 회원 혜택가 트리거를 찾을 수 없음")
                return None
            
            # 스크롤하여 요소가 보이게 함
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", tooltip_trigger)
            time.sleep(0.5)
            
            # 클릭 전에 마우스 오버 시도
            try:
                ActionChains(self.driver).move_to_element(tooltip_trigger).perform()
                time.sleep(0.5)
            except:
                pass
            
            # 클릭 (여러 방법 시도)
            try:
                tooltip_trigger.click()
            except:
                try:
                    self.driver.execute_script("arguments[0].click();", tooltip_trigger)
                except:
                    # 강제 클릭
                    self.driver.execute_script("""
                        var event = new MouseEvent('click', {
                            view: window,
                            bubbles: true,
                            cancelable: true
                        });
                        arguments[0].dispatchEvent(event);
                    """, tooltip_trigger)
            
            time.sleep(2.5)  # 툴팁이 나타날 때까지 충분히 대기
            
            # 툴팁 컨텐츠 찾기
            price_text = None
            
            # 공통 패턴 정의
            patterns = [
                r'회원\s*최대\s*혜택가\s*([\d,]+)\s*원',  # 한 줄에 있는 경우
                r'회원\s*최대\s*혜택가[^\d]*([\d,]+)\s*원',  # 중간에 뭔가 있는 경우
                r'([\d,]+)\s*원.*회원\s*최대\s*혜택가',  # 가격이 먼저 나오는 경우
                r'회원\s*최대\s*혜택가[\s\S]*?([\d,]+)\s*원',  # 멀티라인
                r'회원최대혜택가\s*([\d,]+)\s*원',  # 띄어쓰기 없는 경우
            ]
            
            # 방법 1: aria-describedby로 연결된 툴팁 찾기 (개선)
            try:
                tooltip_id = tooltip_trigger.get_attribute("aria-describedby")
                if tooltip_id:
                    # 툴팁이 렌더링될 때까지 대기 (더 정교한 대기)
                    try:
                        tooltip = WebDriverWait(self.driver, 5).until(
                            lambda driver: driver.find_element(By.ID, tooltip_id) if driver.find_element(By.ID, tooltip_id).text.strip() else None
                        )
                    except:
                        # 타임아웃 시 그냥 요소 찾기
                        tooltip = self.driver.find_element(By.ID, tooltip_id)
                    
                    # 툴팁 내 모든 텍스트 가져오기 (여러 방법 시도)
                    all_text = tooltip.text
                    if not all_text:
                        # text가 비어있으면 innerHTML 시도
                        all_text = self.driver.execute_script("return arguments[0].innerText || arguments[0].textContent", tooltip)
                    
                    print(f"[Worker {self.worker_id}] 툴팁 전체 내용:\n{all_text}\n")
                    
                    # "회원 최대혜택가" 패턴으로 찾기
                    # 줄바꿈이 없을 수도 있으므로 정규식으로 처리
                    import re
                    
                    # 여러 가지 패턴 시도
                    for pattern in patterns:
                        match = re.search(pattern, all_text, re.DOTALL | re.MULTILINE)
                        if match:
                            price_text = match.group(1) + "원"
                            print(f"[Worker {self.worker_id}] 회원 최대혜택가 발견 (패턴): {price_text}")
                            break
                    
                    # 패턴이 안 맞으면 수동으로 찾기
                    if not price_text:
                        lines = all_text.split('\n')
                        for i, line in enumerate(lines):
                            if "회원" in line and ("최대" in line or "혜택" in line):
                                print(f"[Worker {self.worker_id}] 관련 라인 발견: {line}")
                                # 같은 줄에서 가격 찾기
                                price_match = re.search(r'([\d,]+)\s*원', line)
                                if price_match:
                                    price_text = price_match.group(1) + "원"
                                    print(f"[Worker {self.worker_id}] 회원 최대혜택가 발견 (같은 줄): {price_text}")
                                    break
                                # 다음 줄에서 가격 찾기
                                elif i + 1 < len(lines):
                                    next_line = lines[i + 1].strip()
                                    price_match = re.search(r'([\d,]+)\s*원', next_line)
                                    if price_match:
                                        price_text = price_match.group(1) + "원"
                                        print(f"[Worker {self.worker_id}] 회원 최대혜택가 발견 (다음 줄): {price_text}")
                                        break
            except Exception as e:
                print(f"[Worker {self.worker_id}] 툴팁 ID로 찾기 실패: {e}")
            
            # 방법 2: JavaScript로 툴팁 내용 직접 가져오기
            if not price_text:
                try:
                    # JavaScript로 모든 보이는 툴팁 찾기 (개선된 버전)
                    js_code = """
                    let tooltips = [];
                    
                    // 모든 가능한 툴팁 요소 찾기 (더 많은 선택자 추가)
                    let selectors = [
                        '.tooltip-content', 
                        '.tooltip', 
                        '[role="tooltip"]', 
                        '.tooltip-inner', 
                        '.popover-content',
                        '.tooltip-body',
                        '.tooltip-box',
                        '.tooltip-wrap',
                        '[class*="tooltip"]',
                        '[id*="tooltip"]',
                        '.popover',
                        '.popover-body',
                        '[data-popper-placement]',
                        '[data-tippy-root]',
                        '.tippy-box',
                        '.floating',
                        '.floating-content'
                    ];
                    
                    // 1. 선택자로 찾기
                    for (let selector of selectors) {
                        let elements = document.querySelectorAll(selector);
                        for (let elem of elements) {
                            let style = window.getComputedStyle(elem);
                            // 보이고 있고, 크기가 있는 요소만
                            if (style.display !== 'none' && 
                                style.visibility !== 'hidden' && 
                                elem.offsetHeight > 0 && 
                                elem.textContent && 
                                (elem.textContent.includes('회원') || elem.textContent.includes('혜택'))) {
                                tooltips.push(elem.textContent);
                            }
                        }
                    }
                    
                    // 2. body의 마지막 부분에 동적으로 추가된 요소들 확인
                    let bodyChildren = document.body.children;
                    for (let i = bodyChildren.length - 1; i >= Math.max(0, bodyChildren.length - 10); i--) {
                        let elem = bodyChildren[i];
                        if (elem && elem.textContent && 
                            (elem.textContent.includes('회원') || elem.textContent.includes('혜택'))) {
                            tooltips.push(elem.textContent);
                        }
                    }
                    
                    // 3. aria-labelledby나 aria-describedby가 있는 요소들
                    let ariaElements = document.querySelectorAll('[aria-labelledby], [aria-describedby]');
                    for (let elem of ariaElements) {
                        let style = window.getComputedStyle(elem);
                        if (style.display !== 'none' && 
                            style.visibility !== 'hidden' && 
                            elem.textContent && 
                            (elem.textContent.includes('회원') || elem.textContent.includes('혜택'))) {
                            tooltips.push(elem.textContent);
                        }
                    }
                    
                    return tooltips;
                    """
                    
                    tooltip_texts = self.driver.execute_script(js_code)
                    
                    for tooltip_text in tooltip_texts:
                        print(f"[Worker {self.worker_id}] JS로 찾은 툴팁: {tooltip_text[:100]}...")
                        
                        # 패턴 매칭
                        for pattern in patterns:
                            match = re.search(pattern, tooltip_text, re.DOTALL | re.MULTILINE)
                            if match:
                                price_text = match.group(1) + "원"
                                print(f"[Worker {self.worker_id}] 회원 최대혜택가 발견 (JS): {price_text}")
                                break
                        
                        if price_text:
                            break
                            
                except Exception as e:
                    print(f"[Worker {self.worker_id}] JS 툴팁 검색 실패: {e}")
            
            # 방법 3: visible tooltip 요소들 확인
            if not price_text:
                try:
                    # 모든 툴팁 관련 요소 찾기
                    tooltips = self.driver.find_elements(By.CSS_SELECTOR, ".tooltip-content, .tooltip, [role='tooltip']")
                    
                    for tooltip in tooltips:
                        # 보이는 툴팁만 확인
                        if tooltip.is_displayed() and tooltip.size['height'] > 0:
                            tooltip_text = tooltip.text
                            if "회원 최대혜택가" in tooltip_text:
                                # 같은 패턴으로 가격 추출
                                pattern = r'회원\s*최대\s*혜택가\s*([\d,]+)\s*원'
                                match = re.search(pattern, tooltip_text)
                                if match:
                                    price_text = match.group(1) + "원"
                                    print(f"[Worker {self.worker_id}] 회원 최대혜택가 발견 (방법3): {price_text}")
                                    break
                except Exception as e:
                    print(f"[Worker {self.worker_id}] 툴팁 요소 확인 실패: {e}")
            
            # ESC 키로 툴팁 닫기
            try:
                self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            except:
                pass
            
            # 가격 텍스트에서 숫자만 추출
            if price_text:
                price = int(re.sub(r'[^\d]', '', price_text))
                print(f"[Worker {self.worker_id}] 회원 최대혜택가: {price:,}원")
                return price
            else:
                # 툴팁에서 가격을 못 찾으면 페이지에서 직접 회원가 찾기 시도
                print(f"[Worker {self.worker_id}] 툴팁에서 회원 혜택가를 찾을 수 없음, 페이지에서 직접 찾기 시도...")
                
                # 페이지에서 회원가 텍스트 찾기
                try:
                    # 회원가 표시 영역 찾기
                    price_elements = self.driver.find_elements(By.CSS_SELECTOR, "[class*='price'], [class*='member'], [class*='discount']")
                    for elem in price_elements:
                        elem_text = elem.text
                        if '회원' in elem_text and '원' in elem_text:
                            # 회원가 패턴으로 추출
                            match = re.search(r'([\d,]+)\s*원', elem_text)
                            if match:
                                price = int(match.group(1).replace(',', ''))
                                print(f"[Worker {self.worker_id}] 페이지에서 회원가 발견: {price:,}원")
                                return price
                except Exception as e:
                    print(f"[Worker {self.worker_id}] 페이지 회원가 찾기 실패: {e}")
                
                print(f"[Worker {self.worker_id}] 회원 혜택가를 찾을 수 없습니다")
                return None
                
        except Exception as e:
            print(f"[Worker {self.worker_id}] 회원가 추출 실패: {e}")
            return None
    
    def extract_sizes_and_prices(self):
        """사이즈별 가격 추출 (회원 최대혜택가 우선 적용)"""
        size_price_list = []
        
        # 먼저 회원 최대혜택가 확인
        member_price = self.get_member_price()
        
        try:
            # 사이즈 리스트 찾기
            size_list = self.driver.find_element(By.CSS_SELECTOR, "ul.size-list[data-product='option-list']")
            size_items = size_list.find_elements(By.CSS_SELECTOR, "li[data-product-type='option']")
            
            print(f"[Worker {self.worker_id}] 총 {len(size_items)}개 사이즈 발견")
            if member_price:
                print(f"[Worker {self.worker_id}] 회원 최대혜택가 적용: {member_price:,}원")
            
            for item in size_items:
                try:
                    # 사이즈 추출
                    size = item.get_attribute("data-product-option-name")
                    
                    # 220-310 범위 확인
                    if size.isdigit():
                        size_num = int(size)
                        if size_num < 220 or size_num > 310:
                            print(f"[Worker {self.worker_id}] 사이즈 {size} 범위 벗어남 (220-310)")
                            continue
                    
                    # 4자리 사이즈 제외
                    if len(size) == 4 and size.isdigit():
                        print(f"[Worker {self.worker_id}] 4자리 사이즈 {size} 제외")
                        continue
                    
                    # 재고 확인
                    quantity = int(item.get_attribute("data-product-option-quantity") or "0")
                    if quantity < 5:
                        print(f"[Worker {self.worker_id}] 사이즈 {size}: 재고 {quantity}개로 5개 미만이므로 제외")
                        continue
                    
                    # 품절 확인
                    button = item.find_element(By.CSS_SELECTOR, "button")
                    if "sold-out" in button.get_attribute("class"):
                        print(f"[Worker {self.worker_id}] 사이즈 {size}: 품절")
                        continue
                    
                    # 가격 결정 (회원 최대혜택가가 있으면 우선 사용)
                    if member_price:
                        price = member_price
                    else:
                        # 회원 혜택가가 없으면 기본 가격 사용
                        price = int(item.get_attribute("data-product-price") or "0")
                    
                    size_price_list.append({
                        "size": size,
                        "price": price,
                        "delivery": "ABC마트배송"  # ABC마트는 배송 구분 없음
                    })
                    
                    price_type = "(회원가)" if member_price else ""
                    print(f"[Worker {self.worker_id}] {size} - {price:,}원 {price_type} (재고: {quantity}개)")
                    
                except Exception as e:
                    print(f"[Worker {self.worker_id}] 사이즈 정보 추출 실패: {e}")
                    continue
            
            # 사이즈가 하나도 없는 경우
            if not size_price_list:
                print(f"[Worker {self.worker_id}] 재고 있는 사이즈 없음")
                # 회원 혜택가가 있으면 사용, 없으면 기본 가격 시도
                final_price = member_price
                if not final_price:
                    # 기본 가격 추출 시도 (툴팁 클릭 없이)
                    try:
                        size_item = self.driver.find_element(By.CSS_SELECTOR, "li[data-product-price]")
                        final_price = int(size_item.get_attribute("data-product-price") or "0")
                    except:
                        final_price = None
                
                if final_price:
                    size_price_list.append({
                        "size": "품절",
                        "price": final_price,
                        "delivery": "ABC마트배송"
                    })
            
        except Exception as e:
            print(f"[Worker {self.worker_id}] 사이즈/가격 추출 중 오류: {str(e)}")
            # 오류 시 기본값 반환
            final_price = member_price
            if not final_price:
                try:
                    size_item = self.driver.find_element(By.CSS_SELECTOR, "li[data-product-price]")
                    final_price = int(size_item.get_attribute("data-product-price") or "0")
                except:
                    final_price = None
            
            if final_price:
                size_price_list.append({
                    "size": "기본",
                    "price": final_price,
                    "delivery": "ABC마트배송"
                })
        
        return size_price_list
    
    def scrape_product(self, url):
        """상품 스크래핑"""
        try:
            print(f"[Worker {self.worker_id}] 스크래핑 시작: {url}")
            
            self.driver.get(url)
            
            # 페이지 로드 대기
            try:
                # 사이즈 리스트가 로드될 때까지 대기
                self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "ul.size-list")))
            except TimeoutException:
                # 타임아웃 시에도 계속 진행
                pass
            
            # ABC마트는 팝업 처리 불필요
            
            # 정보 추출
            brand = self.extract_brand()
            product_name, color = self.extract_product_name_and_color()
            product_code = self.extract_product_code()
            
            print(f"[Worker {self.worker_id}] 브랜드: {brand}")
            print(f"[Worker {self.worker_id}] 상품명: {product_name}")
            print(f"[Worker {self.worker_id}] 품번: {product_code}")
            
            # 사이즈별 가격 추출
            sizes_prices = self.extract_sizes_and_prices()
            
            if not sizes_prices:
                print(f"[Worker {self.worker_id}] ⚠️ 사이즈/가격 정보 없음")
                return None
                
            # 결과 저장
            product_data = {
                'url': url,
                'brand': brand,
                'product_name': product_name,
                'color': color,
                'product_code': product_code,
                'sizes_prices': sizes_prices,
                'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'worker_id': self.worker_id
            }
            
            print(f"[Worker {self.worker_id}] ✅ 완료: {brand} - {product_code} (사이즈: {len(sizes_prices)}개)")
            return product_data
            
        except Exception as e:
            print(f"[Worker {self.worker_id}] ❌ 스크래핑 오류: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def run(self, urls_queue, results_queue, progress_queue):
        """워커 실행"""
        try:
            self.setup_driver()
            
            # ABC마트는 로그인 불필요
            
            # URL 처리
            while True:
                try:
                    url = urls_queue.get(timeout=1)
                    if url is None:
                        break
                        
                    result = self.scrape_product(url)
                    if result:
                        results_queue.put(result)
                        progress_queue.put(('success', self.worker_id))
                    else:
                        progress_queue.put(('failed', self.worker_id))
                        
                except:
                    break
                    
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
            # Chrome 프로세스 강제 종료
            try:
                os.system(f"taskkill /F /PID {os.getpid()} >nul 2>&1")
            except:
                pass


def worker_process(worker_id, urls_queue, results_queue, progress_queue, headless=True):
    """워커 프로세스 함수"""
    worker = AbcmartWorker(worker_id, headless)
    worker.run(urls_queue, results_queue, progress_queue)


class AbcmartMultiprocessScraper:
    """멀티프로세스 스크래퍼 메인 클래스"""
    def __init__(self, max_workers=4):  # CPU 코어 수에 맞춤
        self.max_workers = max_workers
        self.driver = None
        
    def generate_bid_file(self, products_data, filename="abcmart_bid.txt"):
        """입찰 파일 생성 (품번 분리 버전)"""
        try:
            print(f"\n입찰 파일 생성 중... ({filename})")
            
            with open(filename, 'w', encoding='utf-8') as f:
                # 헤더 추가
                f.write("=== ABC마트 입찰 데이터 ===\n")
                f.write(f"생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"총 상품 수: {len(products_data)}개\n")
                f.write("형식: 브랜드,상품코드,색상,사이즈,가격\n")
                f.write("=" * 50 + "\n\n")
                
                total_items = 0
                
                for product in products_data:
                    if not product or not product.get('sizes_prices'):
                        continue
                        
                    brand = product['brand']
                    codes = product['product_code']  # 나이키의 경우 색상코드 포함된 형태
                    
                    # 품번을 쉼표로 분리하고 공백 제거
                    code_list = [code.strip() for code in codes.split(',')]
                    
                    # 각 사이즈별로
                    for size_info in product['sizes_prices']:
                        size_str = size_info['size']
                        # 재고 정보 제거 (예: "220 (4개 남음)" -> "220")
                        size = re.match(r'^(\d+(?:\.\d+)?)', size_str)
                        if size:
                            size = size.group(1)
                        else:
                            size = size_str.split()[0] if size_str else size_str
                        
                        # 4자리 숫자 검증 및 스킵
                        if len(size) == 4 and size.isdigit():
                            print(f"⚠️ 잘못된 사이즈 스킵: {brand} {codes} - {size} (4자리)")
                            continue
                        
                        # 정상적인 사이즈 범위 확인 (신발: 220-310)
                        if size.isdigit():
                            size_num = int(size)
                            if size_num < 220 or size_num > 310:
                                print(f"⚠️ 비정상 사이즈 스킵: {brand} {codes} - {size}")
                                continue
                        
                        price = size_info['price']
                        
                        # 각 품번에 대해 따로 작성
                        for code in code_list:
                            # 입찰 형식: 브랜드,상품코드,,사이즈,가격 (색상은 빈칸)
                            line = f"{brand},{code},,{size},{price}\n"
                            f.write(line)
                            total_items += 1
                
                # 총 개수 추가
                f.write(f"\nTotal: {total_items} items")
            
            print(f"✅ 입찰 파일 생성 완료! (총 {total_items}개 항목)")
            return filename
            
        except Exception as e:
            print(f"❌ 입찰 파일 생성 실패: {e}")
            return None
    
    def save_partial_results(self, products_data, partial_filename=None):
        """중간 결과 저장"""
        if not partial_filename:
            partial_filename = f"abcmart_partial_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(partial_filename, 'w', encoding='utf-8') as f:
                json.dump(products_data, f, ensure_ascii=False, indent=2)
            print(f"💾 중간 결과 저장: {partial_filename} ({len(products_data)}개)")
            return partial_filename
        except Exception as e:
            print(f"❌ 중간 저장 실패: {e}")
            return None
    
    def run_multiprocess(self, urls, output_file="abcmart_bid.txt"):
        """멀티프로세스 실행 (로그인 제거 버전)"""
        try:
            print("\n=== ABC마트 멀티프로세스 스크래퍼 시작 ===")
            
            # Chrome 프로세스 정리
            print("기존 Chrome 프로세스 정리 중...")
            os.system("taskkill /F /IM chrome.exe >nul 2>&1")
            time.sleep(1)
            
            # ABC마트는 로그인 불필요
            
            # 멀티프로세스 매니저
            manager = Manager()
            urls_queue = manager.Queue()
            results_queue = manager.Queue()
            progress_queue = manager.Queue()
            
            # URL 큐에 추가
            for url in urls:
                urls_queue.put(url)
            
            # 종료 신호
            for _ in range(self.max_workers):
                urls_queue.put(None)
            
            print(f"\n총 {len(urls)}개 URL을 {self.max_workers}개 프로세스로 처리합니다...")
            start_time = time.time()
            
            # 워커 프로세스 시작
            processes = []
            for i in range(self.max_workers):
                # 모든 워커 헤드리스 모드
                p = Process(
                    target=worker_process,
                    args=(i+1, urls_queue, results_queue, progress_queue, True)
                )
                p.start()
                processes.append(p)
                time.sleep(0.5)  # 프로세스 시작 간격 단축
            
            # 결과 수집 및 진행률 표시
            products_data = []
            completed = 0
            failed = 0
            
            print("\n진행 상황:")
            print("-" * 50)
            
            while completed + failed < len(urls):
                try:
                    # 진행률 업데이트
                    status, worker_id = progress_queue.get(timeout=1)
                    if status == 'success':
                        completed += 1
                    else:
                        failed += 1
                    
                    # 진행률 표시
                    progress = (completed + failed) / len(urls) * 100
                    success_rate = (completed / (completed + failed) * 100) if (completed + failed) > 0 else 0
                    
                    print(f"\r진행: {completed + failed}/{len(urls)} ({progress:.1f}%) | "
                          f"성공: {completed} | 실패: {failed} | "
                          f"성공률: {success_rate:.1f}%", end='', flush=True)
                    
                    # 50개마다 중간 저장
                    if (completed + failed) % 50 == 0:
                        # 결과 큐에서 데이터 수집
                        temp_data = []
                        while not results_queue.empty():
                            temp_data.append(results_queue.get())
                        products_data.extend(temp_data)
                        
                        if products_data:
                            self.save_partial_results(products_data)
                    
                except:
                    # 타임아웃 시 결과 큐 확인
                    while not results_queue.empty():
                        products_data.append(results_queue.get())
            
            print("\n")
            
            # 남은 결과 수집
            while not results_queue.empty():
                products_data.append(results_queue.get())
            
            # 모든 프로세스 종료 대기
            for p in processes:
                p.join(timeout=10)
                if p.is_alive():
                    p.terminate()
            
            # 처리 시간 계산
            end_time = time.time()
            total_duration = end_time - start_time
            
            # 최종 결과 저장
            print(f"\n총 {len(products_data)}개 상품 스크래핑 완료!")
            print(f"소요 시간: {total_duration/60:.1f}분")
            print(f"평균 처리 시간: {total_duration/len(urls):.1f}초/URL")
            
            # JSON 파일로 저장
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            json_filename = f'abcmart_products_{timestamp}.json'
            
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(products_data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 데이터 저장 완료: {json_filename}")
            
            # 입찰 파일 생성 (output_file이 지정된 경우만)
            if products_data and output_file:
                self.generate_bid_file(products_data, output_file)
            
            # 로깅
            logger = ScraperLogger(log_dir="C:/poison_final/logs")
            logger.log_file = Path(str(logger.log_file).replace("musinsa", "abcmart"))
            logger.summary_file = Path(str(logger.summary_file).replace("musinsa", "abcmart"))
            
            # 로깅 통계 업데이트
            logger.stats['total_urls'] = len(urls)
            logger.stats['success'] = len(products_data)
            logger.stats['failed'] = len(urls) - len(products_data)
            logger.stats['end_time'] = datetime.now().isoformat()
            
            # 요약 저장
            logger.save_summary()
            
            return products_data
            
        except Exception as e:
            print(f"\n오류 발생: {e}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            # Chrome 프로세스 정리
            time.sleep(2)
            os.system("taskkill /F /IM chrome.exe >nul 2>&1")


# GUI 함수는 동일하게 유지 (URL 검증만 변경)
def get_urls_from_user():
    """사용자로부터 URL 입력받기"""
    import tkinter as tk
    from tkinter import messagebox, filedialog, scrolledtext
    
    # GUI 창 생성
    root = tk.Tk()
    root.withdraw()  # 메인 창 숨기기
    
    # URL 입력 방식 선택
    choice = messagebox.askyesno(
        "URL 입력 방식", 
        "직접 URL을 입력하시겠습니까?\n\n" +
        "Yes: 직접 입력\n" +
        "No: 파일에서 불러오기"
    )
    
    if choice:  # Yes - 직접 입력
        # 입력 창 생성
        input_window = tk.Toplevel()
        input_window.title("ABC마트/그랜드스테이지 URL 입력")
        input_window.geometry("600x400")
        
        # 안내 텍스트
        label = tk.Label(
            input_window, 
            text="ABC마트/그랜드스테이지 상품 URL을 입력하세요 (한 줄에 하나씩):",
            font=("Arial", 12)
        )
        label.pack(pady=10)
        
        # 텍스트 영역
        text_area = scrolledtext.ScrolledText(
            input_window, 
            wrap=tk.WORD, 
            width=70, 
            height=15
        )
        text_area.pack(padx=10, pady=5)
        
        # 예시 텍스트
        text_area.insert(tk.END, "https://abcmart.a-rt.com/product/detail/view?prdtCode=\nhttps://grandstage.a-rt.com/product/new?prdtNo=\n")
        
        urls = []
        
        def confirm_urls():
            text = text_area.get("1.0", tk.END).strip()
            if text:
                # URL 파싱
                for line in text.split('\n'):
                    line = line.strip()
                    if line and ('abcmart.a-rt.com' in line or 'grandstage.a-rt.com' in line):
                        # https:// 없으면 추가
                        if not line.startswith('http'):
                            line = 'https://' + line
                        urls.append(line)
                
                if urls:
                    messagebox.showinfo("확인", f"{len(urls)}개의 URL을 입력받았습니다.")
                    input_window.destroy()
                else:
                    messagebox.showwarning("경고", "유효한 ABC마트/그랜드스테이지 URL이 없습니다.")
            else:
                messagebox.showwarning("경고", "URL을 입력해주세요.")
        
        # 확인 버튼
        confirm_btn = tk.Button(
            input_window, 
            text="확인", 
            command=confirm_urls,
            width=20,
            height=2
        )
        confirm_btn.pack(pady=10)
        
        # 창이 닫힐 때까지 대기
        input_window.wait_window()
        return urls if urls else None
        
    else:  # No - 파일에서 불러오기
        file_path = filedialog.askopenfilename(
            title="URL 목록 파일 선택",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if file_path:
            urls = []
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and ('abcmart.a-rt.com' in line or 'grandstage.a-rt.com' in line):
                            if not line.startswith('http'):
                                line = 'https://' + line
                            urls.append(line)
                
                if urls:
                    messagebox.showinfo("확인", f"{len(urls)}개의 URL을 불러왔습니다.")
                    return urls
                else:
                    messagebox.showwarning("경고", "유효한 ABC마트/그랜드스테이지 URL이 없습니다.")
                    return None
                    
            except Exception as e:
                messagebox.showerror("오류", f"파일 읽기 실패: {e}")
                return None
        else:
            return None


if __name__ == "__main__":
    try:
        # URL 입력받기
        urls = get_urls_from_user()
        
        if urls:
            print(f"\n입력받은 URL 목록 ({len(urls)}개):")
            for i, url in enumerate(urls[:5], 1):  # 처음 5개만 표시
                print(f"{i}. {url}")
            if len(urls) > 5:
                print(f"... 외 {len(urls)-5}개")
            
            # 출력 파일명 입력
            import tkinter as tk
            from tkinter import simpledialog
            
            root = tk.Tk()
            root.withdraw()
            
            output_file = simpledialog.askstring(
                "출력 파일명",
                "입찰 파일명을 입력하세요:",
                initialvalue="abcmart_bid.txt"
            )
            
            if not output_file:
                output_file = "abcmart_bid.txt"
            
            # 스크래퍼 실행
            scraper = AbcmartMultiprocessScraper(max_workers=4)  # CPU에 맞춤
            scraper.run_multiprocess(urls, output_file)
            
            print("\n✅ 모든 작업이 완료되었습니다!")
            input("\nEnter를 눌러 종료하세요...")
            
        else:
            print("URL을 입력하지 않아 종료합니다.")
            
    except KeyboardInterrupt:
        print("\n\n사용자에 의해 중단되었습니다.")
        os.system("taskkill /F /IM chrome.exe >nul 2>&1")
        sys.exit(0)
    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback
        traceback.print_exc()
        input("\n오류가 발생했습니다. Enter를 눌러 종료하세요...")
        sys.exit(1)
