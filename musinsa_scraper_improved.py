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
import pandas as pd
from datetime import datetime
from multiprocessing import Process, Queue, Manager
import pickle
from scraper_logger import ScraperLogger
import sys

def close_musinsa_popup(driver, worker_id=None):
    """
    무신사 팝업 처리 유틸리티 함수
    
    Args:
        driver: Selenium WebDriver 인스턴스
        worker_id: 워커 ID (로깅용, 선택사항)
    
    Returns:
        bool: 팝업이 닫혔으면 True, 팝업이 없었으면 False
    """
    popup_closed = False
    worker_prefix = f"[Worker {worker_id}] " if worker_id else ""
    
    # 일반적인 팝업 셀렉터들
    popup_selectors = [
        # 모달 닫기 버튼들
        "button[aria-label='Close']",
        "button[aria-label='닫기']",
        "button.close-button",
        "button.modal-close",
        "button.popup-close",
        ".close-btn",
        ".btn-close",
        "[data-dismiss='modal']",
        
        # 쿠폰/이벤트 팝업
        ".coupon-popup .close",
        ".event-popup .close",
        ".promotion-popup .close",
        
        # X 버튼 또는 아이콘
        "svg[data-icon='close']",
        "i.icon-close",
        "span.close-icon",
        
        # 무신사 특정 팝업
        ".layer-popup .btn-close",
        ".popup-container .close",
        "[data-mds='IconButton'][aria-label*='close']",
        "[data-mds='IconButton'][aria-label*='Close']"
    ]
    
    try:
        # 각 셀렉터로 팝업 찾기 시도
        for selector in popup_selectors:
            try:
                close_buttons = driver.find_elements(By.CSS_SELECTOR, selector)
                for button in close_buttons:
                    if button.is_displayed() and button.is_enabled():
                        try:
                            # JavaScript로 클릭 (더 안정적)
                            driver.execute_script("arguments[0].click();", button)
                            print(f"{worker_prefix}팝업 닫기 성공 (selector: {selector})")
                            popup_closed = True
                            time.sleep(0.1)  # 팝업 닫힘 애니메이션 최소 대기
                        except:
                            # JavaScript 실패시 일반 클릭
                            try:
                                button.click()
                                print(f"{worker_prefix}팝업 닫기 성공 (일반 클릭)")
                                popup_closed = True
                                time.sleep(0.1)
                            except:
                                continue
            except:
                continue
        
        # ESC 키로 닫기 시도 (마지막 수단)
        if not popup_closed:
            try:
                # 팝업이 있는지 먼저 확인
                popup_elements = driver.find_elements(By.CSS_SELECTOR, ".modal, .popup, .layer-popup, .modal-backdrop, .overlay")
                visible_popups = [elem for elem in popup_elements if elem.is_displayed()]
                
                if visible_popups:  # 팝업이 있는 경우에만 ESC 시도
                    from selenium.webdriver.common.keys import Keys
                    ActionChains(driver).send_keys(Keys.ESCAPE).perform()
                    time.sleep(0.1)
                    
                    # ESC 키 후 팝업이 사라졌는지 확인
                    remaining_popups = driver.find_elements(By.CSS_SELECTOR, ".modal, .popup, .layer-popup, .modal-backdrop, .overlay")
                    visible_remaining = [elem for elem in remaining_popups if elem.is_displayed()]
                    
                    if len(visible_remaining) < len(visible_popups):
                        print(f"{worker_prefix}ESC 키로 팝업 닫기 성공")
                        popup_closed = True
                        
            except Exception as e:
                print(f"{worker_prefix}ESC 키 시도 실패: {e}")
    
    except Exception as e:
        print(f"{worker_prefix}팝업 처리 중 오류: {e}")
    
    return popup_closed

class MusinsaWorker:
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
    
    def load_cookies(self, cookies):
        """쿠키 로드"""
        try:
            self.driver.get("https://www.musinsa.com")
            time.sleep(1)
            
            for cookie in cookies:
                try:
                    self.driver.add_cookie(cookie)
                except:
                    pass
                    
            self.driver.refresh()
            time.sleep(1)
            print(f"[Worker {self.worker_id}] 쿠키 로드 완료")
            return True
        except Exception as e:
            print(f"[Worker {self.worker_id}] 쿠키 로드 실패: {e}")
            return False
    
    def extract_brand(self):
        """브랜드 추출"""
        try:
            # 브랜드 링크에서 추출
            brand_elem = self.driver.find_element(By.CSS_SELECTOR, "a.gtm-click-brand span[data-mds='Typography']")
            brand_text = brand_elem.text.strip()
            
            # "브랜드숍 바로가기" 같은 잘못된 텍스트 필터링
            if "바로가기" in brand_text or "브랜드숍" in brand_text:
                # 대체 방법: href에서 브랜드 추출
                brand_link = self.driver.find_element(By.CSS_SELECTOR, "a.gtm-click-brand")
                href = brand_link.get_attribute("href")
                if "/brand/" in href:
                    brand_text = href.split("/brand/")[-1].upper()
                    
            return brand_text
        except:
            return "Unknown"
    
    def extract_product_name_and_color(self):
        """상품명 추출"""
        try:
            # 상품명 전체 추출
            name_elem = self.driver.find_element(By.CSS_SELECTOR, "span[data-mds='Typography'].text-title_18px_med")
            full_name = name_elem.text.strip()
            return full_name, ""
        except:
            return "Unknown", ""
    
    def extract_product_code(self):
        """상품 코드 추출"""
        try:
            # 품번에서 추출
            code_elem = self.driver.find_element(By.XPATH, "//dt[contains(text(), '품번')]/following-sibling::dd")
            return code_elem.text.strip()
        except:
            return "Unknown"
    
    def get_default_max_benefit_price(self):
        """기본 최대혜택가 추출 (개선된 버전)"""
        try:
            # 최대혜택가 영역 대기
            max_benefit_section = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((
                    By.XPATH, 
                    "//div[@class='sc-x9uktx-0 WoXHk']"
                ))
            )
            
            # 여러 방법으로 가격 찾기 시도
            price_text = None
            
            # 방법 1: JavaScript로 직접 추출 (가장 정확)
            try:
                price_text = self.driver.execute_script("""
                    const section = document.querySelector('.sc-x9uktx-0.WoXHk');
                    if (section) {
                        const spans = section.querySelectorAll('span.text-red.text-title_18px_semi');
                        for (let span of spans) {
                            if (span.textContent.includes('원') && !span.textContent.includes('%')) {
                                return span.textContent;
                            }
                        }
                    }
                    return null;
                """)
                
                if price_text:
                    print(f"[Worker {self.worker_id}] JavaScript로 가격 추출: {price_text}")
            except Exception as e:
                print(f"[Worker {self.worker_id}] JavaScript 실행 실패: {e}")
            
            # 방법 2: XPath로 추출
            if not price_text:
                try:
                    price_elem = max_benefit_section.find_element(
                        By.XPATH, 
                        ".//span[contains(@class, 'text-red') and contains(@class, 'text-title_18px_semi') and contains(text(), '원') and not(contains(text(), '%'))]"
                    )
                    
                    # 텍스트가 실제로 로드될 때까지 대기
                    WebDriverWait(self.driver, 10).until(
                        lambda driver: price_elem.text.strip() != "" and "원" in price_elem.text
                    )
                    
                    price_text = price_elem.text.strip()
                    print(f"[Worker {self.worker_id}] XPath로 가격 추출: {price_text}")
                except Exception as e:
                    print(f"[Worker {self.worker_id}] XPath 추출 실패: {e}")
            
            # 가격 텍스트 처리
            if price_text:
                # 가격에서 숫자만 추출
                current_price = int(re.sub(r'[^\d]', '', price_text))
                
                # 적립금 선할인 체크
                try:
                    # 모든 버튼 확인
                    buttons = self.driver.find_elements(By.CSS_SELECTOR, "button.sc-qexya5-0")
                    
                    pre_discount_amount = 0
                    for button in buttons:
                        try:
                            # 적립금 관련 버튼 찾기
                            button_text = button.text
                            if "적립금 선할인" in button_text:
                                # 체크박스 상태 확인
                                parent_div = button.find_element(By.XPATH, "./ancestor::div[contains(@class, 'flex-row')]")
                                if parent_div:
                                    checkbox_svg = parent_div.find_element(By.CSS_SELECTOR, "svg")
                                    if checkbox_svg and checkbox_svg.get_attribute("data-icon") == "square-check":
                                        print(f"[Worker {self.worker_id}] 적립금 선할인이 체크되어 있음")
                                        
                                        # 버튼 클릭해서 상세 정보 보기
                                        button.click()
                                        time.sleep(0.5)
                                        
                                        # 적립금 금액 찾기
                                        amount_elems = self.driver.find_elements(By.XPATH, "//span[contains(text(), '적용 적립금')]/following-sibling::span")
                                        for elem in amount_elems:
                                            text = elem.text.strip()
                                            if "원" in text:
                                                amount = int(re.sub(r'[^\d]', '', text))
                                                if amount > 0:
                                                    pre_discount_amount = amount
                                                    print(f"[Worker {self.worker_id}] 적립금 선할인 금액: {amount}원")
                                                    break
                                        
                                        break
                        except:
                            continue
                    
                    # 자세히 닫기
                    try:
                        close_button = self.driver.find_element(
                            By.XPATH,
                            "//div[@data-button-name='혜택확인닫기']//span[text()='닫기']/.."
                        )
                        self.driver.execute_script("arguments[0].click();", close_button)
                    except:
                        pass
                        
                    # 적립금 선할인이 적용된 경우, 원래 가격으로 복원
                    if pre_discount_amount > 0:
                        original_price = current_price + pre_discount_amount
                        print(f"[Worker {self.worker_id}] 최대혜택가: {current_price}원 + 선할인 {pre_discount_amount}원 = {original_price}원")
                        return original_price
                        
                except Exception as e:
                    print(f"[Worker {self.worker_id}] 적립금 선할인 확인 실패: {e}")
                
                print(f"[Worker {self.worker_id}] 최대혜택가: {current_price}원")
                return current_price
                
            else:
                print(f"[Worker {self.worker_id}] 최대혜택가 텍스트를 찾을 수 없음")
                return None
                
        except TimeoutException:
            print(f"[Worker {self.worker_id}] 최대혜택가 영역 로드 타임아웃")
            
            # 대안: 정가 추출 시도
            try:
                price_elem = self.driver.find_element(By.XPATH, "//span[contains(@class, 'text-title_18px_semi') and contains(text(), '원')]")
                current_price_text = price_elem.text.strip()
                current_price = int(re.sub(r'[^\d]', '', current_price_text))
                print(f"[Worker {self.worker_id}] 정가: {current_price}원")
                return current_price
            except:
                print(f"[Worker {self.worker_id}] 가격을 찾을 수 없습니다")
                return None
                    
        except Exception as e:
            print(f"[Worker {self.worker_id}] 가격 추출 실패: {e}")
            return None
    
    def extract_sizes_and_prices(self):
        """사이즈별 가격 추출 (간소화 버전 - 품절 아닌 사이즈만)"""
        size_price_list = []
        
        try:
            # 원사이즈 상품 확인
            is_one_size = self.driver.execute_script("""
                const freeElements = document.querySelectorAll("span[class*='word-break']");
                for (let elem of freeElements) {
                    if (elem.textContent.includes('FREE')) return true;
                }
                
                const hasDropdown = document.querySelector('[data-mds="DropdownTriggerBox"]');
                const hasStepper = document.querySelector('[data-mds="Stepper"]');
                
                return !hasDropdown && hasStepper;
            """)
            
            if is_one_size:
                print(f"[Worker {self.worker_id}] 원사이즈 상품 감지")
                current_price = self.get_default_max_benefit_price()
                size_price_list.append({
                    "size": "ONE SIZE",
                    "price": current_price,
                    "delivery": "무신사직배송"
                })
                return size_price_list
            
            # 기본 가격 먼저 추출 (모든 사이즈 동일)
            print(f"[Worker {self.worker_id}] 기본 가격 추출 중...")
            current_price = self.get_default_max_benefit_price()
            
            if not current_price:
                print(f"[Worker {self.worker_id}] 가격 추출 실패")
                return []
            
            # 드롭다운 처리 (색상 + 사이즈 또는 사이즈만)
            print(f"[Worker {self.worker_id}] 드롭다운 확인 중...")
            
            try:
                # 모든 드롭다운 찾기
                all_dropdowns = self.driver.find_elements(
                    By.CSS_SELECTOR, 
                    "input[data-mds='DropdownTriggerInput']"
                )
                
                print(f"[Worker {self.worker_id}] 총 {len(all_dropdowns)}개 드롭다운 발견")
                
                # 색상 드롭다운이 있는지 확인
                color_dropdown = None
                size_dropdown = None
                
                for dropdown in all_dropdowns:
                    placeholder = dropdown.get_attribute('placeholder')
                    if placeholder == '컬러':
                        color_dropdown = dropdown
                    elif placeholder == '사이즈':
                        size_dropdown = dropdown
                
                # 색상 드롭다운이 있으면 첫 번째 색상 선택
                if color_dropdown:
                    print(f"[Worker {self.worker_id}] 색상 드롭다운 발견, 첫 번째 색상 선택 중...")
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", color_dropdown)
                    time.sleep(0.5)
                    color_dropdown.click()
                    # 드롭다운 메뉴가 나타날 때까지 대기
                    try:
                        WebDriverWait(self.driver, 2).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-mds='StaticDropdownMenuItem']"))
                        )
                    except TimeoutException:
                        pass
                    
                    # 첫 번째 색상 선택
                    try:
                        first_color = self.driver.find_element(
                            By.CSS_SELECTOR,
                            "[data-mds='StaticDropdownMenuItem']:first-child"
                        )
                        first_color.click()
                        print(f"[Worker {self.worker_id}] 색상 선택 성공")
                    except Exception as e:
                        print(f"[Worker {self.worker_id}] 색상 선택 실패: {e}")
                
                # 사이즈 드롭다운 열기
                if size_dropdown:
                    print(f"[Worker {self.worker_id}] 사이즈 드롭다운 열기...")
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", size_dropdown)
                    time.sleep(0.2)  # 스크롤 최소 대기
                    size_dropdown.click()
                    # 드롭다운 메뉴가 나타날 때까지 대기
                    try:
                        WebDriverWait(self.driver, 2).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-mds='StaticDropdownMenuItem']"))
                        )
                    except TimeoutException:
                        pass
                    print(f"[Worker {self.worker_id}] 사이즈 드롭다운 열기 성공")
                elif all_dropdowns:
                    # 사이즈 드롭다운이 명시적으로 없으면 마지막 드롭다운 사용
                    print(f"[Worker {self.worker_id}] placeholder가 없는 드롭다운, 마지막 드롭다운 사용")
                    last_dropdown = all_dropdowns[-1]
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", last_dropdown)
                    time.sleep(0.2)  # 스크롤 최소 대기
                    last_dropdown.click()
                    # 드롭다운 메뉴가 나타날 때까지 대기
                    try:
                        WebDriverWait(self.driver, 2).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-mds='StaticDropdownMenuItem']"))
                        )
                    except TimeoutException:
                        pass
                    print(f"[Worker {self.worker_id}] 드롭다운 열기 성공")
                else:
                    print(f"[Worker {self.worker_id}] 드롭다운을 찾을 수 없음")
                    return []
                
                # JavaScript로 모든 사이즈 정보 한번에 가져오기
                sizes_data = self.driver.execute_script("""
                    const sizeElements = document.querySelectorAll('[data-mds="StaticDropdownMenuItem"]');
                    const sizes = [];
                    
                    sizeElements.forEach((elem) => {
                        const text = elem.textContent.trim();
                        const isOutOfStock = text.includes('(품절)');
                        
                        // 색상 항목 제외 (예: BLK0_BLACK)
                        // 사이즈는 보통 숫자로 시작하고, 색상은 영문자 포함
                        const firstChar = text.charAt(0);
                        if (/[A-Za-z]/.test(firstChar) && text.includes('_')) {
                            console.log(`색상 항목 제외: ${text}`);
                            return; // 색상 항목은 건너뛰기
                        }
                        
                        // HTML 구조에서 정보 추출
                        let sizeText = null;
                        let deliveryType = null;
                        let stockCount = null;
                        
                        try {
                            // 새로운 구조: 사이즈는 첫 번째 span에서 추출
                            const sizeSpan = elem.querySelector('span[data-mds="Typography"]:first-child');
                            if (sizeSpan) {
                                sizeText = sizeSpan.textContent.trim();
                                
                                // sizeText가 숫자인지 확인 (사이즈여야 함)
                                if (!/^\d+$/.test(sizeText)) {
                                    // 숫자가 아니면 전체 텍스트에서 추출 시도
                                    const sizeMatch = text.match(/^(\d+)/);
                                    if (sizeMatch) {
                                        sizeText = sizeMatch[1];
                                    } else {
                                        // 사이즈를 찾을 수 없으면 건너뛰기
                                        console.log(`사이즈 추출 실패: ${text}`);
                                        return;
                                    }
                                }
                            } else {
                                // span을 찾을 수 없으면 텍스트에서 첫 번째 숫자 추출
                                const sizeMatch = text.match(/^(\d+)/);
                                if (sizeMatch) {
                                    sizeText = sizeMatch[1];
                                } else {
                                    console.log(`사이즈 추출 실패: ${text}`);
                                    return;
                                }
                            }
                            
                            // 재고 정보 추출 (별도 div에서)
                            const stockDiv = elem.querySelector('.sc-12bm00o-1');
                            if (stockDiv) {
                                const stockSpan = stockDiv.querySelector('span.text-red');
                                if (stockSpan) {
                                    const stockMatch = stockSpan.textContent.match(/(\d+)개 남음/);
                                    stockCount = stockMatch ? parseInt(stockMatch[1]) : null;
                                }
                            }
                            
                            // 재고가 없으면 전체 텍스트에서 찾기 (폴백)
                            if (stockCount === null) {
                                const stockMatch = text.match(/(\d+)개 남음/);
                                if (stockMatch) {
                                    stockCount = parseInt(stockMatch[1]);
                                }
                            }
                            
                            // 배송 타입 확인
                            if (text.includes('브랜드 배송') || text.includes('브랜드배송')) {
                                console.log(`사이즈 ${sizeText}: 브랜드배송이므로 제외`);
                                return;
                            }
                            
                            if (text.includes('무신사 직배송') || text.includes('무신사직배송')) {
                                deliveryType = '무신사직배송';
                            }
                        } catch (e) {
                            console.error('사이즈 정보 추출 에러:', e);
                            // 에러 발생 시 기본 파싱
                            const sizeMatch = text.match(/^(\d+)/);
                            if (sizeMatch) {
                                sizeText = sizeMatch[1];
                            } else {
                                return;
                            }
                        }
                        
                        // 품절이 아니고, 재고가 없거나 5개 이상인 경우만 추가
                        if (!isOutOfStock && sizeText && (stockCount === null || stockCount >= 5)) {
                            sizes.push({
                                size: sizeText,
                                stock: stockCount || '충분',
                                delivery: deliveryType || '무신사직배송'
                            });
                            console.log(`사이즈 추가: ${sizeText} (재고: ${stockCount || '충분'}, 배송: ${deliveryType || '무신사직배송'})`);
                        } else if (stockCount && stockCount < 5) {
                            console.log(`사이즈 ${sizeText}: 재고 ${stockCount}개로 5개 미만이므로 제외`);
                        } else if (isOutOfStock) {
                            console.log(`사이즈 ${sizeText}: 품절`);
                        }
                    });
                    
                    console.log(`총 ${sizes.length}개 사이즈 발견 (브랜드배송 제외, 재고 5개 이상만)`);
                    return sizes;
                """)
                
                print(f"[Worker {self.worker_id}] 재고 있는 사이즈: {len(sizes_data)}개")
                
                # 각 사이즈에 대해 동일한 가격으로 추가
                for size_data in sizes_data:
                    # JavaScript에서 반환한 객체에서 size 속성 추출
                    size_text = size_data['size'] if isinstance(size_data, dict) else size_data
                    stock_info = size_data.get('stock', '충분') if isinstance(size_data, dict) else '충분'
                    
                    size_price_list.append({
                        "size": size_text,
                        "price": current_price,
                        "delivery": "무신사직배송"
                    })
                    print(f"[Worker {self.worker_id}] {size_text} - {current_price:,}원 (재고: {stock_info})")
                
                # 드롭다운 닫기
                try:
                    self.driver.execute_script("""
                        document.activeElement.blur();
                        document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape'}));
                    """)
                except:
                    pass
                    
            except Exception as e:
                print(f"[Worker {self.worker_id}] 드롭다운 처리 실패: {e}")
                # 드롭다운 실패시 기본값 반환
                size_price_list.append({
                    "size": "기본",
                    "price": current_price,
                    "delivery": "무신사직배송"
                })
            
            # 사이즈가 하나도 없는 경우
            if not size_price_list:
                print(f"[Worker {self.worker_id}] 재고 있는 사이즈 없음")
                size_price_list.append({
                    "size": "품절",
                    "price": current_price,
                    "delivery": "무신사직배송"
                })
            
        except Exception as e:
            print(f"[Worker {self.worker_id}] 사이즈/가격 추출 중 오류: {str(e)}")
            # 오류 시 기본값 반환
            try:
                default_price = self.get_default_max_benefit_price()
                size_price_list.append({
                    "size": "기본",
                    "price": default_price if default_price else 0,
                    "delivery": "무신사직배송"
                })
            except:
                pass
        
        return size_price_list
    
    def scrape_product(self, url):
        """상품 스크래핑"""
        try:
            print(f"[Worker {self.worker_id}] 스크래핑 시작: {url}")
            
            self.driver.get(url)
            
            # 페이지 로드 대기 - 가격 정보까지 완전히 로드
            try:
                # 최대혜택가 영역이 로드될 때까지 대기
                self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.sc-x9uktx-0.WoXHk")))
                # 가격 텍스트가 실제로 표시될 때까지 대기
                self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "span.text-red.text-title_18px_semi"))
                )
            except TimeoutException:
                # 타임아웃 시에도 계속 진행 (정가만 있는 경우 등)
                pass
            
            # 팝업 처리
            close_musinsa_popup(self.driver, self.worker_id)
            
            # 로그인 체크
            if "login" in self.driver.current_url.lower():
                print(f"[Worker {self.worker_id}] ❌ 로그인 필요!")
                return None
            
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
    
    def run(self, urls_queue, results_queue, cookies, progress_queue):
        """워커 실행"""
        try:
            self.setup_driver()
            
            # 쿠키 로드
            if cookies:
                self.load_cookies(cookies)
            
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


def worker_process(worker_id, urls_queue, results_queue, cookies, progress_queue, headless=True):
    """워커 프로세스 함수"""
    worker = MusinsaWorker(worker_id, headless)
    worker.run(urls_queue, results_queue, cookies, progress_queue)


class MusinsaMultiprocessScraper:
    """멀티프로세스 스크래퍼 메인 클래스"""
    def __init__(self, max_workers=4):  # CPU 코어 수에 맞춤
        self.max_workers = max_workers
        self.driver = None
        self.cookies = None
        
    def setup_main_driver(self):
        """메인 드라이버 설정 (로그인용)"""
        try:
            print("메인 Chrome 드라이버 초기화 중...")
            
            options = uc.ChromeOptions()
            options.add_argument('--start-maximized')
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--log-level=3')
            
            # User-Agent 설정
            options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
            
            self.driver = uc.Chrome(options=options, version_main=None)
            print("✅ 메인 Chrome 드라이버 설정 완료!")
            
            # 테스트로 구글 접속
            print("연결 테스트 중...")
            self.driver.get("https://www.google.com")
            time.sleep(1)
            print("브라우저 연결 성공!")
            
        except Exception as e:
            print(f"Chrome 드라이버 설정 중 오류: {e}")
            print("\n다음을 확인해주세요:")
            print("1. Chrome 브라우저가 설치되어 있는지")
            print("2. undetected-chromedriver가 설치되어 있는지")
            print("   설치: pip install undetected-chromedriver")
            raise
    
    def manual_login(self):
        """수동 로그인"""
        print("\n" + "="*50)
        print("무신사 로그인이 필요합니다!")
        print("="*50)
        
        print("무신사 로그인 페이지로 이동 중...")
        self.driver.get("https://www.musinsa.com/auth/login")
        time.sleep(2)
        
        print("\n[안내사항]")
        print("1. 브라우저에서 직접 로그인해주세요")
        print("2. 로그인 완료 후 Enter를 눌러주세요")
        print("3. 주의: 자동 로그인 체크 권장")
        print("\n로그인 대기 중...")
        
        input("로그인 완료 후 Enter를 눌러주세요...")
        
        # 로그인 확인
        if "login" in self.driver.current_url.lower():
            print("❌ 아직 로그인되지 않았습니다.")
            return False
        
        # 쿠키 저장
        self.cookies = self.driver.get_cookies()
        
        # 쿠키를 파일로 저장
        with open('musinsa_cookies.pkl', 'wb') as f:
            pickle.dump(self.cookies, f)
            
        print("✅ 로그인 성공! 쿠키가 저장되었습니다.")
        return True
    
    def generate_bid_file(self, products_data, filename="musinsa_bid.txt"):
        """입찰 파일 생성 (품번 분리 버전)"""
        try:
            print(f"\n입찰 파일 생성 중... ({filename})")
            
            with open(filename, 'w', encoding='utf-8') as f:
                # 헤더 추가
                f.write("=== 무신사 입찰 데이터 ===\n")
                f.write(f"생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"총 상품 수: {len(products_data)}개\n")
                f.write("형식: 브랜드,상품코드,색상,사이즈,가격\n")
                f.write("=" * 50 + "\n\n")
                
                # 등급 적립 안내 추가
                f.write("💡 등급 적립 안내:\n")
                f.write("- 무신사 등급에 따라 추가 할인 가능\n")
                f.write("- 계산기에서 '등급적립' 체크 시 자동 차감\n")
                f.write("- 일반적으로 2,450원 할인 (등급별 상이)\n")
                f.write("=" * 50 + "\n\n")
                
                total_items = 0
                
                for product in products_data:
                    if not product or not product.get('sizes_prices'):
                        continue
                        
                    brand = product['brand']
                    codes = product['product_code']  # 쉼표로 구분된 품번들
                    
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
                        
                        # 정상적인 사이즈 범위 확인 (신발: 200-330)
                        if size.isdigit():
                            size_num = int(size)
                            if size_num < 200 or size_num > 330:
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
            partial_filename = f"musinsa_partial_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(partial_filename, 'w', encoding='utf-8') as f:
                json.dump(products_data, f, ensure_ascii=False, indent=2)
            print(f"💾 중간 결과 저장: {partial_filename} ({len(products_data)}개)")
            return partial_filename
        except Exception as e:
            print(f"❌ 중간 저장 실패: {e}")
            return None
    
    def run_multiprocess(self, urls, output_file="musinsa_bid.txt"):
        """멀티프로세스 실행 (개선된 버전)"""
        try:
            print("\n=== 무신사 멀티프로세스 스크래퍼 시작 ===")
            
            # Chrome 프로세스 정리
            print("기존 Chrome 프로세스 정리 중...")
            os.system("taskkill /F /IM chrome.exe >nul 2>&1")
            time.sleep(1)
            
            # 메인 드라이버로 로그인
            self.setup_main_driver()
            
            if not self.manual_login():
                print("로그인 실패로 종료합니다.")
                return
            
            # 메인 드라이버 종료
            self.driver.quit()
            
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
                    args=(i+1, urls_queue, results_queue, self.cookies, progress_queue, True)
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
            json_filename = f'musinsa_products_{timestamp}.json'
            
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(products_data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 데이터 저장 완료: {json_filename}")
            
            # 입찰 파일 생성
            if products_data:
                self.generate_bid_file(products_data, output_file)
            
            # 로깅
            logger = ScraperLogger()
            summary = {
                'total_urls': len(urls),
                'success': len(products_data),
                'failed': len(urls) - len(products_data),
                'start_time': datetime.fromtimestamp(start_time).isoformat(),
                'end_time': datetime.fromtimestamp(end_time).isoformat(),
                'total_duration': str(datetime.fromtimestamp(end_time) - datetime.fromtimestamp(start_time))
            }
            logger.log_summary(summary)
            
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


# GUI 함수는 동일하게 유지
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
        input_window.title("무신사 URL 입력")
        input_window.geometry("600x400")
        
        # 안내 텍스트
        label = tk.Label(
            input_window, 
            text="무신사 상품 URL을 입력하세요 (한 줄에 하나씩):",
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
        text_area.insert(tk.END, "https://www.musinsa.com/products/2545799\n")
        text_area.insert(tk.END, "https://www.musinsa.com/products/4409450\n")
        
        urls = []
        
        def confirm_urls():
            text = text_area.get("1.0", tk.END).strip()
            if text:
                # URL 파싱
                for line in text.split('\n'):
                    line = line.strip()
                    if line and ('musinsa.com' in line):
                        # https:// 없으면 추가
                        if not line.startswith('http'):
                            line = 'https://' + line
                        urls.append(line)
                
                if urls:
                    messagebox.showinfo("확인", f"{len(urls)}개의 URL을 입력받았습니다.")
                    input_window.destroy()
                else:
                    messagebox.showwarning("경고", "유효한 무신사 URL이 없습니다.")
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
                        if line and 'musinsa.com' in line:
                            if not line.startswith('http'):
                                line = 'https://' + line
                            urls.append(line)
                
                if urls:
                    messagebox.showinfo("확인", f"{len(urls)}개의 URL을 불러왔습니다.")
                    return urls
                else:
                    messagebox.showwarning("경고", "유효한 무신사 URL이 없습니다.")
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
                initialvalue="musinsa_bid.txt"
            )
            
            if not output_file:
                output_file = "musinsa_bid.txt"
            
            # 스크래퍼 실행
            scraper = MusinsaMultiprocessScraper(max_workers=4)  # CPU에 맞춤
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
