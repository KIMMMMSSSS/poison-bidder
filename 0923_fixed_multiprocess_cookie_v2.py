# 0923_fixed_multiprocess_cookie_v2.py
# 쿠키 공유 방식을 사용한 멀티프로세스 버전

import time
import re
import os
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from collections import defaultdict
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, 
    StaleElementReferenceException,
    NoSuchElementException,
    ElementClickInterceptedException
)
from selenium.webdriver.common.keys import Keys
from multiprocessing import Pool, Queue, Manager, Process
import multiprocessing
import sys
import traceback
from datetime import datetime
import pickle  # 쿠키 저장용

# 설정 상수
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
LOGFILE = os.path.join(CURRENT_DIR, "poizon_bid_fail_log.txt")
COOKIE_FILE = os.path.join(CURRENT_DIR, "poizon_cookies.pkl")  # 쿠키 파일
PRICE_STEP = 1000     # 가격 조정 단위
MAX_RETRIES = 3       # 재시도 횟수
DEFAULT_WAIT_TIME = 15  # 기본 대기 시간
WORKER_COUNT = 5      # 동시 실행 프로세스 수 (메모리 안정성 강화)

print(f"""
==================================================
Poizon Multi-Process Auto Bidder (쿠키 공유 버전)
==================================================
- 첫 번째 워커만 로그인 창이 표시됩니다.
- 로그인 후 쿠키가 저장되어 다른 워커들과 공유됩니다.
- 나머지 워커들은 headless 모드로 실행됩니다.
==================================================
""")

# 브랜드별 검색 규칙
BRAND_SEARCH_RULES = {
    "반스": "remove_last_1",      # VN0001 → VN000
    "살로몬": "remove_L_and_00",  # L12345600 → 123456
    "SALOMON": "remove_L_and_00",  # 대문자도 지원
}

# 브랜드별 사이즈 우선순위
BRAND_SIZE_PRIORITY = {
    "나이키": ["JP", "EU", "US Men", "KR"],
    "아디다스": ["JP", "EU", "US Men", "KR"],
    "반스": ["JP", "US Men", "EU", "KR"],
    "살로몬": ["JP", "EU", "US Men", "KR"],
    "SALOMON": ["JP", "EU", "US Men", "KR"],  # 대문자도 지원
    "데상트": ["EU", "JP", "KR"],
    "폴로": ["JP", "US Men", "EU", "KR"],
    "기본": ["JP", "EU", "US Men", "US Women", "UK", "KR"]
}

# 색상 매핑 테이블 (무신사 → Poizon)
COLOR_MAPPING = {
    # 한글 → 영어
    "블랙": ["BLACK", "Black", "BLK", "BK", "블랙"],
    "화이트": ["WHITE", "White", "WHT", "WT", "화이트"],
    "그레이": ["GREY", "GRAY", "Grey", "Gray", "GRY", "GR", "그레이"],
    "네이비": ["NAVY", "Navy", "NVY", "NV", "네이비"],
    "블루": ["BLUE", "Blue", "BLU", "BL", "블루"],
    "레드": ["RED", "Red", "RD", "빨강", "레드"],
    "그린": ["GREEN", "Green", "GRN", "GR", "초록", "그린"],
    "옐로우": ["YELLOW", "Yellow", "YLW", "YL", "노랑", "옐로우"],
    "오렌지": ["ORANGE", "Orange", "ORG", "OR", "주황", "오렌지"],
    "핑크": ["PINK", "Pink", "PNK", "PK", "분홍", "핑크"],
    "퍼플": ["PURPLE", "Purple", "PRP", "PP", "보라", "퍼플"],
    "브라운": ["BROWN", "Brown", "BRN", "BR", "갈색", "브라운"],
    "베이지": ["BEIGE", "Beige", "BGE", "BG", "베이지"],
    "카키": ["KHAKI", "Khaki", "KHK", "KH", "카키"],
    "실버": ["SILVER", "Silver", "SLV", "SV", "은색", "실버"],
    "골드": ["GOLD", "Gold", "GLD", "GD", "금색", "골드"],
    
    # 영어 → 영어 변형
    "BLACK": ["BLACK", "Black", "BLK", "BK", "블랙"],
    "WHITE": ["WHITE", "White", "WHT", "WT", "화이트"],
    "GREY": ["GREY", "GRAY", "Grey", "Gray", "GRY", "GR"],
    "GRAY": ["GREY", "GRAY", "Grey", "Gray", "GRY", "GR"],
    
    # 특수 색상
    "MULTI": ["MULTI", "Multi", "멀티", "다색"],
    "CAMO": ["CAMO", "Camo", "CAMOUFLAGE", "카모", "위장"],
    
    # 조합 색상 (WTBK = White/Black)
    "WTBK": ["WTBK", "White/Black", "WHITE/BLACK", "화이트/블랙"],
    "BKWT": ["BKWT", "Black/White", "BLACK/WHITE", "블랙/화이트"],
    "NVWT": ["NVWT", "Navy/White", "NAVY/WHITE", "네이비/화이트"],
    "GRBK": ["GRBK", "Grey/Black", "GREY/BLACK", "그레이/블랙"],
}

# 색상 약어 패턴 (2글자 약어)
COLOR_ABBREVIATIONS = {
    "BK": ["BLACK", "Black"],
    "WT": ["WHITE", "White"],
    "GR": ["GREY", "GRAY", "Grey", "Gray", "GREEN", "Green"],  # GR은 GREY나 GREEN일 수 있음
    "NV": ["NAVY", "Navy"],
    "BL": ["BLUE", "Blue", "BLACK", "Black"],  # BL은 BLUE나 BLACK일 수 있음
    "RD": ["RED", "Red"],
    "YL": ["YELLOW", "Yellow"],
    "OR": ["ORANGE", "Orange"],
    "PK": ["PINK", "Pink"],
    "PP": ["PURPLE", "Purple"],
    "BR": ["BROWN", "Brown"],
    "BG": ["BEIGE", "Beige"],
    "KH": ["KHAKI", "Khaki"],
    "SV": ["SILVER", "Silver"],
    "GD": ["GOLD", "Gold"],
}


def save_cookies(driver):
    """쿠키를 파일로 저장"""
    cookies = driver.get_cookies()
    with open(COOKIE_FILE, 'wb') as f:
        pickle.dump(cookies, f)
    return cookies


def load_cookies(driver):
    """저장된 쿠키를 브라우저에 로드"""
    try:
        with open(COOKIE_FILE, 'rb') as f:
            cookies = pickle.load(f)
        
        # 쿠키 추가 전에 동일 도메인으로 이동
        driver.get("https://seller.poizon.com")
        time.sleep(1)
        
        # 쿠키 추가
        for cookie in cookies:
            # 문제가 될 수 있는 키 제거
            if 'expiry' in cookie:
                cookie['expiry'] = int(cookie['expiry'])
            driver.add_cookie(cookie)
        
        return True
    except Exception as e:
        print(f"쿠키 로드 실패: {e}")
        return False


def status_monitor(status_dict, login_complete, stats):
    """상태 모니터링 프로세스"""
    last_update = time.time()
    while True:
        try:
            # 화면 클리어 (Windows)
            if time.time() - last_update > 1:  # 1초마다만 업데이트
                os.system('cls' if os.name == 'nt' else 'clear')
                
                print("=" * 80, flush=True)
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Poizon Multi-Process Status", flush=True)
                print("=" * 80, flush=True)
                
                # 진행률 표시
                if stats['total'] > 0:
                    completed = stats['completed']
                    total = stats['total']
                    progress = (completed / total) * 100
                    success_rate = (stats['success'] / completed * 100) if completed > 0 else 0
                    
                    print(f"\n진행: {completed}/{total} ({progress:.1f}%) | 성공: {stats['success']} | 실패: {stats['failed']} | 성공률: {success_rate:.1f}%", flush=True)
                    
                    # 진행률 바
                    bar_length = 50
                    filled_length = int(bar_length * completed // total)
                    bar = '█' * filled_length + '░' * (bar_length - filled_length)
                    print(f"[{bar}] {progress:.1f}%\n", flush=True)
                
                # 로그인 상태 표시 - Manager.Value 사용
                login_status = login_complete.value
                status_text = "\033[92m완료\033[0m" if login_status else "\033[93m대기중\033[0m"
                print(f"로그인 상태: {status_text}\n", flush=True)
                
                # 각 워커 상태 출력
                for i in range(1, WORKER_COUNT + 1):
                    status = status_dict.get(i, {"status": "준비중", "code": "", "progress": ""})
                    if status['status'] == '처리중':
                        print(f"[Worker {i:2d}] {status['status']}: {status['code']} {status['progress']}", flush=True)
                    elif status['status'] == '완료':
                        print(f"[Worker {i:2d}] {status['status']}: {status['code']} ✓", flush=True)
                    else:
                        print(f"[Worker {i:2d}] {status['status']}", flush=True)
                
                print("=" * 80, flush=True)
                last_update = time.time()
            
            time.sleep(0.3)  # CPU 사용률 줄이기 (최적화)
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Status monitor error: {e}")
            time.sleep(1)


def worker_process(worker_id, task_queue, result_queue, status_dict, login_complete, min_profit, driver_path, stats):
    """워커 프로세스"""
    bidder = None
    try:
        # 상태 업데이트
        status_dict[worker_id] = {"status": "초기화중", "code": "", "progress": ""}
        
        # PoizonAutoBidder 인스턴스 생성
        bidder = PoizonAutoBidderWorker(worker_id, result_queue, status_dict)
        bidder.min_profit = min_profit
        
        # Chrome 옵션 설정
        result_queue.put(("LOG", f"[Worker {worker_id}] Chrome 드라이버 초기화 시작..."))
        
        try:
            chrome_options = webdriver.ChromeOptions()
            if worker_id > 1:  # 첫 번째 워커는 보이게, 나머지는 headless
                chrome_options.add_argument('--headless')
                chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # 성능 최적화 옵션 추가
            # chrome_options.add_argument('--disable-images')  # 이미지 로딩 차단 - 버튼 아이콘을 못 찾을 수 있음
            chrome_options.add_argument('--disable-logging')  # 로깅 비활성화
            chrome_options.add_argument('--log-level=3')  # 로그 레벨 최소화
            chrome_options.add_argument('--silent')  # 조용한 모드
            
            # 메모리 최적화 옵션 추가
            chrome_options.add_argument('--memory-pressure-off')  # 메모리 압박 비활성화
            chrome_options.add_argument('--disable-software-rasterizer')  # 소프트웨어 래스터라이저 비활성화
            chrome_options.add_argument('--disable-background-timer-throttling')  # 백그라운드 타이머 제한 해제
            chrome_options.add_argument('--disable-backgrounding-occluded-windows')  # 백그라운드 윈도우 비활성화
            chrome_options.add_argument('--disable-renderer-backgrounding')  # 렌더러 백그라운딩 비활성화
            chrome_options.add_argument('--disable-features=TranslateUI')  # 번역 UI 비활성화
            chrome_options.add_argument('--disable-ipc-flooding-protection')  # IPC 픍러딩 보호 비활성화
            chrome_options.add_argument('--disable-default-apps')  # 기본 앱 비활성화
            chrome_options.add_argument('--disable-extensions')  # 확장 프로그램 비활성화
            chrome_options.add_argument('--disable-hang-monitor')  # 행 모니터 비활성화
            chrome_options.add_argument('--disable-sync')  # 동기화 비활성화
            chrome_options.add_argument('--disable-web-resources')  # 웹 리소스 비활성화
            chrome_options.add_argument('--safebrowsing-disable-download-protection')  # 다운로드 보호 비활성화
            chrome_options.add_argument('--disable-client-side-phishing-detection')  # 피싱 탐지 비활성화
            chrome_options.add_argument('--disable-component-update')  # 컴포넌트 업데이트 비활성화
            chrome_options.add_argument('--disable-domain-reliability')  # 도메인 신뢰성 비활성화
            
            # JavaScript 메모리 제한 설정
            chrome_options.add_argument('--js-flags=--max-old-space-size=512')  # JS 힙 크기 제한 (512MB)
            
            # 리소스 차단을 위한 prefs 설정
            chrome_options.add_experimental_option("prefs", {
                "profile.default_content_setting_values": {
                    "images": 2,  # 이미지 차단
                    "plugins": 2,  # 플러그인 차단
                    "popups": 2,  # 팝업 차단
                    "geolocation": 2,  # 위치정보 차단
                    "notifications": 2,  # 알림 차단
                    "media_stream": 2,  # 미디어 차단
                },
                "profile.managed_default_content_settings": {
                    "images": 2  # 이미지 차단 강화
                }
            })
            
            # 추가 experimental 옵션
            chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])  # 로깅 제거
            chrome_options.add_experimental_option('useAutomationExtension', False)  # 자동화 확장 비활성화
            
            # Chrome 드라이버 초기화
            bidder.driver = webdriver.Chrome(service=Service(driver_path), options=chrome_options)
            bidder.wait = WebDriverWait(bidder.driver, DEFAULT_WAIT_TIME)
            
            result_queue.put(("LOG", f"[Worker {worker_id}] Chrome 드라이버 초기화 성공!"))
            
        except Exception as e:
            status_dict[worker_id] = {"status": "초기화 실패", "code": "", "progress": ""}
            error_msg = f"Worker {worker_id} Chrome 드라이버 초기화 실패: {type(e).__name__} - {str(e)}"
            result_queue.put(("ERROR", error_msg))
            raise
        
        # 로그인 처리
        if worker_id == 1:
            # 첫 번째 워커: 직접 로그인
            bidder.driver.get("https://seller.poizon.com/main/dataBoard")
            result_queue.put(("LOG", f"[Worker {worker_id}] 로그인 페이지 로드 완료. 로그인해주세요..."))
            time.sleep(5)
            
            # 로그인 완료 대기
            check_count = 0
            while True:
                check_count += 1
                try:
                    current_url = bidder.driver.current_url
                    result_queue.put(("LOG", f"[Worker {worker_id}] URL 확인 #{check_count}: {current_url}"))
                    
                    if "dataBoard" in current_url and "login" not in current_url.lower():
                        try:
                            search_box = bidder.driver.find_element(By.XPATH, "//input[@id='Item Info']")
                            if search_box:
                                result_queue.put(("LOG", f"[Worker {worker_id}] 검색창 발견! 로그인 성공!"))
                                
                                # 쿠키 저장
                                save_cookies(bidder.driver)
                                result_queue.put(("LOG", f"[Worker {worker_id}] 쿠키 저장 완료"))
                                
                                login_complete.value = True
                                break
                        except:
                            tables = bidder.driver.find_elements(By.CSS_SELECTOR, "table")
                            if tables:
                                result_queue.put(("LOG", f"[Worker {worker_id}] 테이블 발견! 로그인 성공!"))
                                
                                # 쿠키 저장
                                save_cookies(bidder.driver)
                                result_queue.put(("LOG", f"[Worker {worker_id}] 쿠키 저장 완료"))
                                
                                login_complete.value = True
                                break
                except Exception as e:
                    result_queue.put(("LOG", f"[Worker {worker_id}] 로그인 체크 중 오류: {type(e).__name__}"))
                
                if check_count % 10 == 0:
                    result_queue.put(("LOG", f"[Worker {worker_id}] 로그인 대기중... (체크 횟수: {check_count})"))
                    
                time.sleep(3)
        else:
            # 다른 워커들: 쿠키 로드 방식
            result_queue.put(("LOG", f"[Worker {worker_id}] 로그인 완료 대기중..."))
            
            # 로그인 완료 대기
            wait_count = 0
            while True:
                wait_count += 1
                login_status = login_complete.value
                
                if wait_count % 10 == 0:
                    result_queue.put(("LOG", f"[Worker {worker_id}] 로그인 상태: {login_status} (대기 횟수: {wait_count})"))
                
                if login_status:
                    result_queue.put(("LOG", f"[Worker {worker_id}] 로그인 확인! 쿠키 로드 중..."))
                    
                    # 쿠키 로드
                    if load_cookies(bidder.driver):
                        result_queue.put(("LOG", f"[Worker {worker_id}] 쿠키 로드 성공!"))
                        
                        # 페이지 새로고침으로 쿠키 적용
                        bidder.driver.get("https://seller.poizon.com/main/dataBoard")
                        time.sleep(3)
                        
                        # 로그인 확인
                        try:
                            search_box = bidder.driver.find_element(By.XPATH, "//input[@id='Item Info']")
                            result_queue.put(("LOG", f"[Worker {worker_id}] 로그인 상태 확인 완료!"))
                            time.sleep(worker_id * 0.3)  # 워커별 시작 시간 분산 (기존 1초에서 0.3초로 감소)
                            break
                        except:
                            result_queue.put(("ERROR", f"[Worker {worker_id}] 쿠키 로드 후 로그인 확인 실패"))
                            raise Exception("쿠키 로드 실패")
                    else:
                        result_queue.put(("ERROR", f"[Worker {worker_id}] 쿠키 파일 로드 실패"))
                        raise Exception("쿠키 파일 없음")
                        
                time.sleep(1)
        
        # 상태 업데이트
        status_dict[worker_id] = {"status": "대기중", "code": "", "progress": ""}
        
        # 작업 처리 루프
        while True:
            try:
                # 작업 가져오기
                task = task_queue.get(timeout=1)
                
                if task is None:  # 종료 신호
                    break
                
                code, entries = task
                
                # 상태 업데이트
                status_dict[worker_id] = {
                    "status": "처리중", 
                    "code": code, 
                    "progress": f"(0/{len(entries)})"
                }
                
                # 작업 처리
                try:
                    result = bidder.process_code(code, entries)
                    # 상품번호 단위로 카운트
                    if result:  # 반환값이 있으면
                        success_count, fail_count = result
                        if success_count > 0:  # 하나라도 성공하면 성공으로 처리
                            stats['success'] += 1
                        else:  # 모두 실패하면 실패로 처리
                            stats['failed'] += 1
                    else:  # 반환값이 없으면 (호환성)
                        # 기존 방식: 성공으로 간주
                        stats['success'] += 1
                except Exception as e:
                    # 예외 발생 시 실패로 처리
                    stats['failed'] += 1
                    result_queue.put(("ERROR", f"Worker {worker_id}: {code} 처리 중 오류 - {e}"))
                
                # 완료 카운트 업데이트
                stats['completed'] += 1
                
                # 완료 상태 업데이트
                status_dict[worker_id] = {
                    "status": "완료", 
                    "code": code, 
                    "progress": f"({len(entries)}/{len(entries)})"
                }
                
                # 완료 메시지
                result_queue.put(("COMPLETE", f"Worker {worker_id}: {code} 완료"))
                
            except Exception as e:
                if "Empty" in str(type(e)):
                    continue
                else:
                    error_msg = f"Worker {worker_id} - {code if 'code' in locals() else 'N/A'} 처리 중 오류: {type(e).__name__} - {str(e)}"
                    result_queue.put(("ERROR", error_msg))
                    result_queue.put(("ERROR", traceback.format_exc()))
                    
                    if 'code' in locals():
                        status_dict[worker_id] = {"status": "오류", "code": code, "progress": ""}
        
        # 상태 업데이트
        status_dict[worker_id] = {"status": "종료", "code": "", "progress": ""}
        
    except Exception as e:
        error_msg = f"Worker {worker_id} 초기화 오류: {type(e).__name__} - {str(e)}"
        result_queue.put(("ERROR", error_msg))
        result_queue.put(("ERROR", traceback.format_exc()))
    finally:
        if bidder and bidder.driver:
            bidder.driver.quit()


class PoizonAutoBidderWorker:
    """워커용 PoizonAutoBidder 클래스"""
    def __init__(self, worker_id, result_queue, status_dict):
        self.worker_id = worker_id
        self.result_queue = result_queue
        self.status_dict = status_dict
        self.driver = None
        self.wait = None
        self.min_profit = 0
        
    def log_to_queue(self, message):
        """큐를 통한 로그 전송"""
        self.result_queue.put(("LOG", f"[Worker {self.worker_id}] {message}"))
        
    # -- 로그 기록
    def log_fail(self, idx, brand, code, color, size, price, reason):
        log_entry = f"{idx},{brand},{code},{color},{size},{price},{reason}"
        self.result_queue.put(("FAIL_LOG", log_entry))
        self.log_to_queue(f"[FAIL] {log_entry}")

    # -- 숫자 추출
    def get_int(self, txt):
        return int(re.sub(r"[^0-9]", "", txt) or 0)

    # -- 사이즈 토큰화
    def normalize_size(self, s):
        return re.findall(r"\d+|[a-zA-Z]+", s.lower())

    # -- 브랜드별 검색 코드 변환
    def apply_search_rules(self, brand, code):
        """브랜드별 검색 규칙 적용"""
        # 먼저 ** 또는 * 제거
        if code.startswith('**'):
            code = code[2:]
        elif code.startswith('*'):
            code = code[1:]
        
        # VN으로 시작하고 1로 끝나는 경우 (반스 제품) - 마지막 1 제거
        if code.startswith('VN') and code.endswith('1') and len(code) > 3:
            self.log_to_queue(f"[DEBUG] VN...1 패턴 감지: {code}")
            code = code[:-1]  # 마지막 1 제거
            self.log_to_queue(f"[DEBUG] 변환 결과: {code}")
            return code
        
        # 브랜드 대소문자 처리
        brand_upper = brand.upper()
        
        if brand in BRAND_SEARCH_RULES or brand_upper in BRAND_SEARCH_RULES:
            rule = BRAND_SEARCH_RULES.get(brand) or BRAND_SEARCH_RULES.get(brand_upper)
            if rule == "remove_last_1":
                return code[:-1] if len(code) > 1 else code
            elif rule == "remove_L_and_00":
                # L로 시작하면 제거, 00으로 끝나면 제거
                if code.startswith('L'):
                    code = code[1:]
                if code.endswith('00'):
                    code = code[:-2]
                return code
        
        # 브랜드 규칙이 없어도 L로 시작하고 00으로 끝나는 패턴 처리
        # 예: L47449600 → 474496
        if code.startswith('L') and code.endswith('00') and len(code) >= 4:
            self.log_to_queue(f"[DEBUG] L...00 패턴 감지: {code}")
            code = code[1:-2]  # L 제거, 00 제거
            self.log_to_queue(f"[DEBUG] 변환 결과: {code}")
            
        return code
    
    # -- 검색창 초기화
    def clear_search_box(self):
        """검색창 초기화 (JavaScript로 즉시 처리)"""
        try:
            # JavaScript로 검색창 즉시 초기화
            self.driver.execute_script("""
                var searchBox = document.getElementById('Item Info');
                if (searchBox) {
                    searchBox.value = '';
                    searchBox.dispatchEvent(new Event('input', { bubbles: true }));
                    searchBox.dispatchEvent(new Event('change', { bubbles: true }));
                    searchBox.focus();
                    return true;
                }
                return false;
            """)
            
            # 초기화 확인 (즉시 확인)
            search_box = self.driver.find_element(By.XPATH, "//input[@id='Item Info']")
            if search_box.get_attribute("value") == "":
                self.log_to_queue("[OK] 검색창 초기화 완료")
                return True
            else:
                # 초기화 실패 시 fallback
                search_box.clear()
                self.log_to_queue("[OK] 검색창 초기화 완료 (fallback)")
                return True
                
        except Exception as e:
            self.log_to_queue(f"[WARN] 검색창 초기화 실패: {type(e).__name__}")
            return False

    def process_code(self, code, entries):
        # 첫 번째 엔트리에서 브랜드와 기준 가격 추출
        brand = entries[0][1] if entries[0][1] else "기본"
        base_price = entries[0][5]  # 가격은 인덱스 5
        
        # 상태 업데이트
        self.status_dict[self.worker_id] = {
            "status": "처리중", 
            "code": code, 
            "progress": f"(0/{len(entries)})"
        }
        
        self.log_to_queue(f"\n=== {code} 처리 시작 === 브랜드={brand}, 원가={base_price}, 사이즈={[e[4] for e in entries]}")
        
        try:
            # 1) 검색 (브랜드별 규칙 적용)
            if not self.search_product_with_retry(code, brand):
                self.log_to_queue(f"[SKIP] 상품 검색 실패: {code}")
                for entry in entries:
                    self.log_fail(entry[0], brand, code, entry[3], entry[4], entry[5], "검색실패")
                
                # 검색 실패 시 검색창 초기화하고 다음 상품으로
                self.clear_search_box()
                return 0, len(entries)  # 검색 실패 시 모두 실패
            
            # 2) Create listings
            self.create_listings()
            
            # 3) 리전 설정
            self.setup_regions()
            
            # 4) 사이즈 매칭 (JP 우선, 필요시 Size Chart)
            matched = self.match_sizes_smart(entries, brand)
            if not matched:
                # 매칭된 사이즈가 없으면 뒤로 가기
                self.log_to_queue("[WARN] 매칭된 사이즈 없음")
                self.go_back_and_reset()
                return 0, len(entries)  # 매칭 실패 시 모두 실패
                
            # 5) 가격 설정
            self.setup_pricing(base_price)
            
            # 6) Apply
            self.click_apply()
            
            # 7) 입찰 처리
            successful = self.process_bids(matched, code, brand)
            
            # 8) 최종 확인 (성공한 항목이 있을 때만)
            if successful:
                self.confirm_bids()
                self.log_to_queue(f"[RESULT] {code} 처리 완료: 성공 {len(successful)}/{len(entries)}")
                return len(successful), len(entries) - len(successful)  # 성공 개수, 실패 개수 반환
            else:
                self.log_to_queue(f"[RESULT] {code} 처리 완료: 모두 실패 0/{len(entries)}")
                return 0, len(entries)  # 모두 실패
                
        except Exception as e:
            self.log_to_queue(f"[ERROR] {code} 처리 중 오류: {type(e).__name__} - {e}")
            # 오류 발생 시에도 검색창 초기화
            self.clear_search_box()
            return 0, len(entries)  # 오류 시 모두 실패로 처리

    # -- 색상 매칭 (매핑 테이블 활용)
    def ultra_flexible_color_match(self, input_color, available_colors):
        """초유연 색상 매칭 (매핑 테이블 활용)"""
        if not input_color:
            return None
            
        input_clean = input_color.strip()
        
        # 0. 매핑 테이블 활용
        for key, variations in COLOR_MAPPING.items():
            # 입력 색상이 매핑 테이블에 있는지 확인
            if input_clean.upper() in [v.upper() for v in variations]:
                # 사용 가능한 색상 중에서 매핑된 변형 찾기
                for available_color in available_colors:
                    if available_color.upper() in [v.upper() for v in variations]:
                        return available_color
        
        # 0-1. 2글자 약어 패턴 체크
        if len(input_clean) == 2 and input_clean.upper() in COLOR_ABBREVIATIONS:
            possible_colors = COLOR_ABBREVIATIONS[input_clean.upper()]
            for available_color in available_colors:
                for possible in possible_colors:
                    if possible.upper() in available_color.upper():
                        return available_color
        
        # 0-2. 조합 색상 처리 (WTBK, BKWT 등)
        if len(input_clean) >= 4:
            # 조합 색상 분해 (WTBK -> WT, BK)
            parts = []
            for i in range(0, len(input_clean), 2):
                if i+1 < len(input_clean):
                    parts.append(input_clean[i:i+2])
            
            # 각 부분이 모두 포함된 색상 찾기
            if len(parts) >= 2:
                for available_color in available_colors:
                    color_upper = available_color.upper()
                    all_parts_found = True
                    for part in parts:
                        if part.upper() in COLOR_ABBREVIATIONS:
                            part_found = False
                            for possible in COLOR_ABBREVIATIONS[part.upper()]:
                                if possible.upper() in color_upper:
                                    part_found = True
                                    break
                            if not part_found:
                                all_parts_found = False
                                break
                    if all_parts_found:
                        return available_color
        
        # 1. 정확히 일치
        for color in available_colors:
            if input_clean.upper() == color.upper():
                return color
        
        # 2. 포함 관계 (양방향)
        for color in available_colors:
            color_upper = color.upper()
            input_upper = input_clean.upper()
            if input_upper in color_upper or color_upper in input_upper:
                return color
        
        # 3. 단어 분리 후 매칭
        input_words = set(input_clean.upper().split())
        for color in available_colors:
            color_words = set(color.upper().split())
            # 공통 단어가 있으면 매칭
            if input_words & color_words:
                return color
        
        # 4. 유사도 체크 (첫 3글자)
        if len(input_clean) >= 3:
            for color in available_colors:
                if len(color) >= 3 and input_clean[:3].upper() == color.upper()[:3]:
                    return color
        
        # 5. 숫자/특수문자 제거 후 비교
        import re
        input_letters_only = re.sub(r'[^a-zA-Z가-힏]', '', input_clean).upper()
        if input_letters_only:
            for color in available_colors:
                color_letters_only = re.sub(r'[^a-zA-Z가-힏]', '', color).upper()
                if input_letters_only == color_letters_only:
                    return color
        
        return None

    # -- 사용 가능한 사이즈 분석
    def analyze_available_sizes(self):
        """사용 가능한 사이즈 및 색상 분석"""
        # CSS selector 수정 - 실제 DOM 구조에 맞게
        items = self.driver.find_elements(
            By.CSS_SELECTOR, 
            ".global-text-label-wrap-small[data-disabled='false']"
        )
        
        # 디버깅 로그 추가
        self.log_to_queue(f"[DEBUG] 찾은 사이즈 요소 개수: {len(items)}")
        
        colors = set()
        size_info = []
        
        for item in items:
            text = item.text.strip()
            if not text:
                continue
            
            # 디버깅: 각 아이템 텍스트 출력
            self.log_to_queue(f"[DEBUG] 사이즈 텍스트: '{text}'")
            
            # 단일 색상 제품의 경우 사이즈만 있음 (예: "22", "22.5", "23")
            # 색상이 포함된 경우 처리 (예: "Pink SIZE 85")
            parts = text.split()
            
            # 색상이 포함되어 있는지 확인
            if len(parts) > 1 and any(keyword in text.upper() for keyword in ['SIZE', 'KR', 'JP', 'US', 'EU']):
                color = parts[0]
                colors.add(color)
                size_info.append({
                    'element': item,
                    'text': text,
                    'color': color,
                    'full_text': text
                })
            else:
                # 단일 색상 - 사이즈만 있는 경우
                size_info.append({
                    'element': item,
                    'text': text,
                    'color': '',  # 색상 없음
                    'full_text': text
                })
        
        return {
            'need_color_match': False,  # 단일 색상
            'colors': [],
            'items': size_info
        }

    def read_product_size_chart(self):
        """현재 제품의 Size Chart를 읽어서 사이즈 매핑 정보 추출"""
        try:
            self.log_to_queue("[STEP] Size Chart 읽기 시작")
            
            # Size Chart 버튼 찾기
            try:
                size_chart_btn = self.driver.find_element(
                    By.CSS_SELECTOR, 
                    ".specListBtn____tiR5"
                )
            except NoSuchElementException:
                # 대체 선택자 시도
                try:
                    size_chart_btn = self.driver.find_element(
                        By.XPATH, 
                        "//span[contains(text(), 'Size Chart')]"
                    )
                except:
                    self.log_to_queue("[WARN] Size Chart 버튼을 찾을 수 없음")
                    return None
            
            # Size Chart 버튼 클릭
            self.driver.execute_script("arguments[0].click();", size_chart_btn)
            self.log_to_queue("[OK] Size Chart 버튼 클릭")
            
            # 모달이 열릴 때까지 대기
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "div.ant-table-container")
                )
            )
            time.sleep(1)  # DOM 안정화 대기
            
            # 테이블 데이터 파싱
            size_mapping = {}
            
            # 테이블 헤더 찾기 (어떤 컴럼이 있는지 확인)
            headers = self.driver.find_elements(
                By.CSS_SELECTOR, 
                "thead.ant-table-thead th"
            )
            header_texts = [h.text.strip() for h in headers]
            self.log_to_queue(f"[DEBUG] Size Chart 헤더: {header_texts}")
            
            # 테이블 행 데이터 읽기
            rows = self.driver.find_elements(
                By.CSS_SELECTOR,
                "tbody.ant-table-tbody tr"
            )
            
            self.log_to_queue(f"[INFO] Size Chart 테이블 행 수: {len(rows)}")
            
            for row in rows:
                cells = row.find_elements(By.CSS_SELECTOR, "td")
                if len(cells) >= 2:  # 최소 2개 컴럼 필요
                    # 첫 번째 컴럼이 KR 사이즈라고 가정
                    kr_size = cells[0].text.strip()
                    
                    if kr_size and kr_size.replace('.', '').isdigit():
                        size_mapping[kr_size] = {
                            'KR': kr_size
                        }
                        
                        # 헤더에 따라 매핑
                        for i, header in enumerate(header_texts[1:], 1):  # 첫 컴럼은 KR이므로 스킵
                            if i < len(cells):
                                cell_text = cells[i].text.strip()
                                if header == 'US Men' or header == 'US(M)':
                                    size_mapping[kr_size]['US Men'] = cell_text
                                elif header == 'US Women' or header == 'US(W)':
                                    size_mapping[kr_size]['US Women'] = cell_text
                                elif header == 'EU':
                                    size_mapping[kr_size]['EU'] = cell_text
                                elif header == 'JP':
                                    size_mapping[kr_size]['JP'] = cell_text
                                elif header == 'UK':
                                    size_mapping[kr_size]['UK'] = cell_text
                
                # 처음 3개 행만 샘플로 출력
                if len(size_mapping) <= 3:
                    self.log_to_queue(f"[DEBUG] Size Chart 샘플: {kr_size} = {size_mapping.get(kr_size, {})}")
            
            self.log_to_queue(f"[OK] Size Chart 읽기 완료: {len(size_mapping)}개 사이즈")
            
            # 모달 닫기
            try:
                close_btn = self.driver.find_element(
                    By.CSS_SELECTOR, 
                    "button.ant-modal-close"
                )
                close_btn.click()
                self.log_to_queue("[OK] Size Chart 모달 닫기")
                time.sleep(0.5)  # 모달 닫힘 대기
            except:
                # ESC 키로 닫기 시도
                try:
                    self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                    self.log_to_queue("[OK] ESC키로 Size Chart 모달 닫기")
                except:
                    self.log_to_queue("[WARN] Size Chart 모달 닫기 실패")
            
            return size_mapping
            
        except TimeoutException:
            self.log_to_queue("[ERROR] Size Chart 모달 로드 시간 초과")
            return None
        except Exception as e:
            self.log_to_queue(f"[ERROR] Size Chart 읽기 실패: {type(e).__name__} - {e}")
            return None

    # -- 예상수익 추출 (개선)
    def find_est_payout(self, row, retries=MAX_RETRIES):
        for _ in range(retries):
            try:
                # 방법 1: 부모 div의 형제 관계로 찾기
                text = row.find_element(
                    By.XPATH, 
                    ".//span[contains(text(),'Est. payout:')]/parent::div/following-sibling::div//span[contains(text(),'KRW')]"
                ).text
                return self.get_int(text)
            except NoSuchElementException:
                try:
                    # 방법 2: labelTitle 클래스 활용
                    payout_label = row.find_element(
                        By.XPATH,
                        ".//span[@class='labelTitle___pPygx' and contains(text(),'Est. payout:')]"
                    )
                    # 부모의 부모에서 다음 span 찾기
                    text = payout_label.find_element(
                        By.XPATH,
                        "./ancestor::div[@class='ant-space-item']/following-sibling::div//span"
                    ).text
                    return self.get_int(text)
                except:
                    pass
            except StaleElementReferenceException:
                time.sleep(0.1)  # 리전 탭 클릭 후 대기 (최적화)
                continue
        return 0

    # -- Asia 체크 여부 확인 (개선)
    def is_asia_checked(self, row):
        try:
            # Asia 라인에서 체크 아이콘 찾기 (수정된 XPath)
            asia_check = row.find_element(
                By.XPATH, 
                ".//span[text()='Asia: ']/parent::div/following-sibling::div//span[@class='anticon anticon-check']"
            )
            return True
        except NoSuchElementException:
            # 대체 방법: Asia 라인에서 녹색 체크 SVG 찾기
            try:
                asia_check = row.find_element(
                    By.XPATH,
                    ".//span[text()='Asia: ']/ancestor::div[@class='ant-space-item']/following-sibling::div//svg[@data-icon='check']"
                )
                return True
            except NoSuchElementException:
                # 또 다른 대체 방법: HTML에서 패턴 매칭
                try:
                    row_html = row.get_attribute("outerHTML")
                    # Asia: 다음에 anticon-check가 있는지 확인
                    if 'Asia:' in row_html and 'anticon-check' in row_html:
                        # Asia와 check 아이콘의 위치 확인
                        asia_pos = row_html.find('Asia:')
                        check_pos = row_html.find('anticon-check', asia_pos)
                        close_pos = row_html.find('anticon-close', asia_pos)
                        
                        # check가 Asia 다음에 있고, close보다 먼저 나오면 체크된 것
                        if check_pos > asia_pos and (close_pos == -1 or check_pos < close_pos):
                            return True
                except:
                    pass
                return False

    # -- 동적 대기 함수
    def wait_and_click(self, locator, timeout=10):
        element = WebDriverWait(self.driver, timeout).until(
            EC.element_to_be_clickable(locator)
        )
        element.click()
        return element

    # -- 가격 다운 버튼 클릭 (개선)
    def click_down_button(self, row):
        try:
            # 가격 입력 필드를 더 정확하게 찾기
            price_inputs = row.find_elements(
                By.CSS_SELECTOR, 
                "td.inputNumberV2___dIR0i input.ant-input-number-input"
            )
            
            for input_el in price_inputs:
                value_now = input_el.get_attribute("value")
                # 가격 필드인지 더 정확하게 판단
                if value_now and value_now.isdigit() and int(value_now) >= 1000:
                    # 해당 input의 부모 td에서 down 버튼 찾기
                    td = input_el.find_element(By.XPATH, "./ancestor::td")
                    down_btn = td.find_element(
                        By.CSS_SELECTOR, 
                        "span.ant-input-number-handler-down:not(.ant-input-number-handler-down-disabled)"
                    )
                    down_btn.click()
                    self.log_to_queue(f"[DEBUG] ↓ 클릭! 기존 가격: {value_now}")
                    
                    # 가격 변경이나 Asia 체크 대기
                    try:
                        # Asia 체크가 나타나거나 가격이 변경될 때까지 대기 (최대 3초)
                        WebDriverWait(self.driver, 3).until(
                            lambda d: self.is_asia_checked(row) or input_el.get_attribute("value") != value_now
                        )
                        
                        # Asia 체크 확인
                        if self.is_asia_checked(row):
                            self.log_to_queue(f"[INFO] Asia 체크 발견! 즉시 반환")
                            return True
                        
                        new_value = input_el.get_attribute("value")
                        self.log_to_queue(f"[DEBUG] 가격 변경 확인: {value_now} -> {new_value}")
                    except TimeoutException:
                        self.log_to_queue(f"[DEBUG] 가격 변경 대기 시간 초과")
                        
                    # DOM 업데이트를 위한 최소 대기 (기존 2초에서 0.5초로 감소)
                    time.sleep(0.5)
                    
                    return True
                    
        except (NoSuchElementException, TimeoutException) as e:
            self.log_to_queue(f"[DEBUG] ↓ 버튼 클릭 불가: {type(e).__name__}")
        except Exception as e:
            self.log_to_queue(f"[DEBUG] ↓ 버튼 클릭 예외: {type(e).__name__} - {e}")
        return False

    # -- Remove 클릭 (개선)
    def click_remove(self, row):
        try:
            # Python으로 먼저 Remove 링크 찾기
            rmv = row.find_element(By.XPATH, ".//a[text()='Remove']")
            # JavaScript로 클릭
            self.driver.execute_script("arguments[0].click();", rmv)
            self.log_to_queue("[OK] Remove 클릭 성공")
            
            # 최소 대기만 (3초 → 0.2초)
            time.sleep(0.2)
            
        except NoSuchElementException:
            self.log_to_queue("[ERROR] Remove 링크를 찾을 수 없음")
        except Exception as e:
            self.log_to_queue(f"[ERROR] Remove 실패: {type(e).__name__} - {str(e)}")

    # -- 뒤로 가기 및 검색 초기화
    def go_back_and_reset(self):
        """뒤로 가기 버튼 클릭하고 검색 초기화"""
        try:
            self.log_to_queue("[INFO] 입찰 가능한 가격이 없음 - 뒤로 가기")
            
            # 뒤로 가기 버튼 클릭
            back_btn = self.driver.find_element(
                By.XPATH, 
                "//div[@class='_back_52snt_15']//span[@aria-label='arrow-left']"
            )
            back_btn.click()
            time.sleep(1)
            
            # 검색창 초기화
            self.clear_search_box()
                
            return True
            
        except Exception as e:
            self.log_to_queue(f"[ERROR] 뒤로 가기 실패: {type(e).__name__}")
            return False

    def search_product_with_retry(self, code, brand):
        """브랜드별 규칙을 적용한 검색 (재시도 포함)"""
        self.log_to_queue("[STEP] 상품 검색")
        
        # 검색 전 페이지 상태 확인
        try:
            # 현재 페이지가 검색 페이지인지 확인
            current_url = self.driver.current_url
            if "dataBoard" not in current_url:
                self.log_to_queue("[INFO] 검색 페이지로 이동")
                self.driver.get("https://seller.poizon.com/main/dataBoard")
                time.sleep(2)
        except:
            pass
        
        # 1차: 원본 코드
        search_code = code
        if self.try_search(search_code):
            return True
        
        # 검색 실패 시 페이지 새로고침
        self.log_to_queue("[INFO] 페이지 새로고침 후 재시도")
        self.driver.refresh()
        time.sleep(2)
        
        # 2차: 브랜드별 변환 규칙 적용
        transformed_code = self.apply_search_rules(brand, code)
        if transformed_code != code:
            self.log_to_queue(f"[DEBUG] 브랜드 규칙 적용: {code} → {transformed_code}")
            if self.try_search(transformed_code):
                return True
        
        # 3차: 코드 일부만 검색
        if len(code) > 6:
            partial_code = code[:6]
            self.log_to_queue(f"[DEBUG] 부분 검색 시도: {partial_code}")
            if self.try_search(partial_code):
                # TODO: 검색 결과에서 정확한 상품 확인
                return True
        
        # 4차: 코드에서 브랜드 프리픽스 제거 (L로 시작하는 경우)
        if code.startswith('L') and len(code) > 1:
            no_prefix_code = code[1:]
            self.log_to_queue(f"[DEBUG] 프리픽스 제거 검색: {no_prefix_code}")
            if self.try_search(no_prefix_code):
                return True
        
        # 5차: 숫자만 추출해서 검색
        numbers_only = re.sub(r'[^0-9]', '', code)
        if numbers_only and len(numbers_only) >= 5:
            self.log_to_queue(f"[DEBUG] 숫자만 검색: {numbers_only}")
            if self.try_search(numbers_only):
                return True
                
        return False

    def try_search(self, search_code):
        """실제 검색 시도"""
        try:
            # 검색창 찾기 및 입력
            search_box = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//input[@id='Item Info']"))
            )
            
            # 검색창 완전히 초기화
            search_box.click()
            time.sleep(0.5)
            # Ctrl+A로 전체 선택 후 삭제
            search_box.send_keys(Keys.CONTROL + "a")
            search_box.send_keys(Keys.DELETE)
            time.sleep(0.5)
            
            # 새로운 검색어 입력
            search_box.send_keys(search_code)
            time.sleep(0.5)
            
            # 검색 버튼 클릭
            try:
                self.wait_and_click((By.CSS_SELECTOR, 'button.searchBtn___Fm781'))
            except:
                # 검색 버튼을 못 찾으면 Enter 키로 검색
                search_box.send_keys(Keys.RETURN)
            
            # 검색 결과 로드 대기 (WebDriverWait 사용)
            try:
                WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'tbody.ant-table-tbody tr'))
                )
            except TimeoutException:
                pass  # 검색 결과가 없을 수도 있음
            
            # 검색 결과 확인
            results = self.driver.find_elements(
                By.CSS_SELECTOR, 
                'tbody.ant-table-tbody tr'
            )
            
            if results:
                self.log_to_queue(f"[OK] 검색 성공: {search_code} ({len(results)}개 결과)")
                return True
            else:
                self.log_to_queue(f"[WARN] 검색 결과 없음: {search_code}")
                # 검색 결과가 없으면 검색창 다시 초기화
                self.clear_search_box()
                return False
                
        except Exception as e:
            self.log_to_queue(f"[ERROR] 검색 실패: {type(e).__name__} - {str(e)}")
            # 검색 실패 시 검색창 초기화
            self.clear_search_box()
            return False

    def create_listings(self):
        self.log_to_queue("[STEP] Create listings")
        try:
            # 리스트 로드 대기
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'tbody.ant-table-tbody tr')))
            
            # Create listings 버튼 클릭
            self.wait_and_click((By.XPATH, "//button[.//span[text()='Create listings']]"))
            # 리전 탭이 나타날 때까지 대기 (WebDriverWait 사용)
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//div[@class='tabItem___vEvcb']"))
            )
            self.log_to_queue("[OK] Create listings 완료")
        except TimeoutException:
            raise Exception("Create listings 버튼을 찾을 수 없습니다")

    def setup_regions(self):
        """Expand와 Select All만 처리 (탭 클릭 제거)"""
        self.log_to_queue("[STEP] 리전 초기 설정")
        
        # Expand 클릭 (모든 사이즈 표시)
        try:
            self.wait_and_click((By.XPATH, "//span[text()='Expand']"), timeout=5)
            self.log_to_queue("[OK] Expand")
            time.sleep(0.5)  # Expand 후 DOM 업데이트 대기
        except TimeoutException:
            self.log_to_queue("[WARN] Expand 없음")
            
        # Select All 해제
        try:
            sa = self.driver.find_element(
                By.XPATH, 
                "//span[text()='Select All']/ancestor::div[contains(@class,'global-text-label-wrap-small')]"
            )
            if 'selected' in sa.get_attribute('class'):
                sa.click()
                self.log_to_queue("[OK] Select All 해제")
        except NoSuchElementException:
            self.log_to_queue("[WARN] Select All 없음")

    def match_sizes_smart(self, entries, brand):
        """JP 우선 스마트 사이즈 매칭 (필요시에만 Size Chart)"""
        self.log_to_queue("[STEP] JP 우선 스마트 사이즈 매칭")
        
        # 사용 가능한 사이즈 분석
        available = self.analyze_available_sizes()
        self.log_to_queue(f"[INFO] 색상 {len(available['colors'])}개: {available['colors']}")
        self.log_to_queue(f"[INFO] 색상 매칭 필요: {available['need_color_match']}")
        
        matched = []
        active_tab = None  # 현재 활성화된 탭
        
        # JP 탭 먼저 확인
        try:
            # JavaScript로 JP 탭 즉시 클릭
            jp_clicked = self.driver.execute_script("""
                var tabs = document.querySelectorAll("div.tabItem___vEvcb");
                for (var i = 0; i < tabs.length; i++) {
                    if (tabs[i].textContent === 'JP') {
                        tabs[i].click();
                        return true;
                    }
                }
                return false;
            """)
            
            if jp_clicked:
                self.log_to_queue("[INFO] JP 탭 발견 - 빠른 매칭 모드")
                # JP 탭 활성화 확인 (대기 시간 최소화)
                time.sleep(0.2)  # DOM 업데이트를 위한 최소 대기
                active_tab = 'JP'
                self.log_to_queue("[OK] JP 탭 사용 결정 - Size Chart 스킵")
            else:
                raise NoSuchElementException("JP 탭 없음")
            
        except (NoSuchElementException, TimeoutException):
            self.log_to_queue("[WARN] JP 탭 없음 - Size Chart 모드로 전환")
            
            # JP가 없을 때만 Size Chart 읽기
            size_chart = self.read_product_size_chart()
            if size_chart:
                self.log_to_queue(f"[INFO] Size Chart 데이터 획득 ({len(size_chart)}개 사이즈)")
                # EU 탭으로 시도
                try:
                    eu_tab = self.driver.find_element(
                        By.XPATH, 
                        "//div[@class='tabItem___vEvcb' and text()='EU']"
                    )
                    eu_tab.click()
                    active_tab = 'EU'
                    self.log_to_queue("[OK] EU 탭 사용 결정")
                except:
                    # 다른 탭 찾기
                    tabs = self.driver.find_elements(By.XPATH, "//div[@class='tabItem___vEvcb']")
                    if tabs:
                        tabs[0].click()
                        active_tab = tabs[0].text
                        self.log_to_queue(f"[OK] {active_tab} 탭 사용")
            else:
                self.log_to_queue("[ERROR] Size Chart 읽기 실패")
                return matched
        
        
        if not active_tab:
            self.log_to_queue("[ERROR] 적절한 탭을 찾을 수 없음")
            return matched
        
        # 결정된 탭에서 모든 사이즈 매칭
        self.log_to_queue(f"\n[매칭 시작] {active_tab} 탭에서 모든 사이즈 처리")
        
        # 상태 업데이트
        progress = 0
        
        # 현재 탭의 모든 아이템 가져오기
        all_items = self.driver.find_elements(
            By.CSS_SELECTOR, 
            ".global-text-label-wrap-small[data-disabled='false']"
        )
        
        for idx, brand_name, code, color, size, cost in entries:
            progress += 1
            self.status_dict[self.worker_id]["progress"] = f"({progress}/{len(entries)})"
            
            # 4자리 숫자 사이즈 변환
            if len(size) == 4 and size.isdigit():
                self.log_to_queue(f"\n[WARN] 4자리 사이즈 감지: {size}")
                size = size[:3]  # 2552 → 255
                self.log_to_queue(f"[INFO] 변환된 사이즈: {size}")
            
            self.log_to_queue(f"\n[매칭] {size} (색상: {color})")
            
            # 색상 매칭 (필요한 경우)
            target_color = None
            # 색상이 2개 이상일 때만 색상 매칭
            if available['need_color_match'] and len(available['colors']) > 1 and color:
                target_color = self.ultra_flexible_color_match(color, available['colors'])
                if not target_color:
                    self.log_to_queue(f"[WARN] 색상 매칭 실패: {color}")
                    self.log_fail(idx, brand_name, code, color, size, cost, f"색상매칭실패:{color}")
                    continue
                else:
                    self.log_to_queue(f"[OK] 색상 매칭: {color} → {target_color}")
            elif available['need_color_match'] and len(available['colors']) > 1 and not color:
                # 색상이 여러 개인데 입력 색상이 없으면 첫 번째 색상 사용
                target_color = available['colors'][0]
                self.log_to_queue(f"[INFO] 색상 미입력 - 첫 번째 색상 사용: {target_color}")
            elif len(available['colors']) == 1:
                # 색상이 1개면 색상 무시
                self.log_to_queue(f"[INFO] 색상이 1개뿐 - 색상 매칭 생략")
            
            # 사이즈 변환
            if active_tab == "JP" and size.isdigit():
                # JP 탭에서는 두 가지 형식이 가능: 280 그대로 또는 28로 변환
                target_size_original = size  # 원본 사이즈 (280)
                target_size_converted = str(int(size) / 10).rstrip('0').rstrip('.')  # 변환 사이즈 (28)
                self.log_to_queue(f"[DEBUG] JP 사이즈 - 원본: {target_size_original}, 변환: {target_size_converted}")
                
                # 사용 가능한 모든 사이즈 표시 (디버깅용)
                available_sizes = [item.text.strip() for item in all_items[:10]]  # 처음 10개만
                self.log_to_queue(f"[DEBUG] 사용 가능한 사이즈들: {available_sizes}")
                
                # 먼저 원본 사이즈로 시도
                target_size = target_size_original
            elif 'size_chart' in locals() and size_chart and size in size_chart and active_tab in size_chart[size]:
                # Size Chart가 있을 때만 사용
                target_size = size_chart[size][active_tab]
                if target_size and target_size != '-':
                    self.log_to_queue(f"[DEBUG] Size Chart 기반 사이즈: {size} → {active_tab}: {target_size}")
                else:
                    target_size = size
                    self.log_to_queue(f"[DEBUG] Size Chart에 정보 없음 - 원본 사용: {target_size}")
            else:
                target_size = size
            
            # JavaScript로 빠른 매칭
            found = False
            self.log_to_queue(f"[DEBUG] 매칭 시작 - 타겟 사이즈: '{target_size}', 타겟 색상: '{target_color}'")
            
            # JavaScript로 한 번에 매칭 아이템 찾기
            try:
                matching_item = self.driver.execute_script("""
                    var items = document.querySelectorAll('.global-text-label-wrap-small[data-disabled="false"]');
                    var targetSize = arguments[0];
                    var targetColor = arguments[1];
                    var needColorMatch = arguments[2];
                    
                    console.log('[DEBUG] 찾는 사이즈: ' + targetSize);
                    console.log('[DEBUG] 사용 가능한 아이템 수: ' + items.length);
                    
                    // 처음 5개 아이템 텍스트 표시
                    for (var j = 0; j < Math.min(5, items.length); j++) {
                        console.log('[DEBUG] 아이템 ' + j + ': ' + items[j].textContent.trim());
                    }
                    
                    for (var i = 0; i < items.length; i++) {
                        var item = items[i];
                        var text = item.textContent.trim();
                        
                        // 이미 선택된 항목 스킵
                        if (item.classList.contains('selected')) continue;
                        
                        // 사이즈 체크 - 다양한 패턴 시도
                        // 패턴1: "탭명 사이즈" 형식 ("JP 260")
                        // 패턴2: 사이즈만 ("260")
                        // 패턴3: 공백 없이 붙어있는 경우 ("JP260")
                        
                        var pattern1 = ' ' + targetSize + ' ';  // 공백으로 둘러싸인 사이즈
                        var pattern2 = ' ' + targetSize;        // 뒤에만 공백
                        var pattern3 = targetSize + ' ';        // 앞에만 공백
                        
                        if (text.indexOf(pattern1) !== -1 || 
                            text.endsWith(pattern2) || 
                            text.startsWith(pattern3) ||
                            text === targetSize) {
                            console.log('[DEBUG] 매칭 성공: ' + text);
                            // 색상 체크 (필요한 경우만)
                            if (needColorMatch && targetColor) {
                                // 타겟 색상이 지정되었으면 해당 색상이 포함되어야 함
                                if (!text.includes(targetColor)) {
                                    console.log('[DEBUG] 색상 불일치: ' + text + ' (필요 색상: ' + targetColor + ')');
                                    continue;
                                }
                            }
                            console.log('[DEBUG] 최종 매칭 성공: ' + text);
                            return item;
                        }
                    }
                    return null;
                """, target_size, target_color, len(available['colors']) > 1)
                
                if matching_item:
                    # 동일 사이즈 중복 체크 (EU 다른 경우)
                    item_text = matching_item.text.strip()
                    if f"{active_tab} {target_size}" in item_text and "(EU" in item_text:
                        already_selected = False
                        for m in matched:
                            if m[4] == size:  # 같은 원본 사이즈
                                already_selected = True
                                break
                        
                        if already_selected:
                            self.log_to_queue(f"[SKIP] {size} 이미 선택됨")
                            continue
                    
                    # 클릭
                    self.driver.execute_script("arguments[0].click();", matching_item)
                    self.log_to_queue(f"[OK] 선택: {item_text}")
                    matched.append((idx, brand_name, code, color, size, cost, item_text))
                    found = True
                    
            except Exception as e:
                self.log_to_queue(f"[ERROR] JavaScript 매칭 실패: {type(e).__name__}")
            
            if not found:
                # JP 탭에서 원본 사이즈로 실패했다면 변환된 사이즈로 재시도
                if active_tab == "JP" and size.isdigit() and 'target_size_converted' in locals() and target_size == target_size_original:
                    self.log_to_queue(f"[INFO] JP 탭 - 변환된 사이즈로 재시도: {target_size_converted}")
                    try:
                        matching_item = self.driver.execute_script("""
                            var items = document.querySelectorAll('.global-text-label-wrap-small[data-disabled="false"]');
                            var targetSize = arguments[0];
                            var targetColor = arguments[1];
                            var needColorMatch = arguments[2];
                            
                            console.log('[DEBUG] 재시도 - 찾는 사이즈: ' + targetSize);
                            
                            for (var i = 0; i < items.length; i++) {
                                var item = items[i];
                                var text = item.textContent.trim();
                                
                                if (item.classList.contains('selected')) continue;
                                
                                var pattern1 = ' ' + targetSize + ' ';
                                var pattern2 = ' ' + targetSize;
                                var pattern3 = targetSize + ' ';
                                
                                if (text.indexOf(pattern1) !== -1 || 
                                    text.endsWith(pattern2) || 
                                    text.startsWith(pattern3) ||
                                    text === targetSize) {
                                    console.log('[DEBUG] 재시도 매칭 성공: ' + text);
                                    if (needColorMatch && targetColor) {
                                        if (!text.includes(targetColor)) {
                                            console.log('[DEBUG] 재시도 색상 불일치: ' + text);
                                            continue;
                                        }
                                    }
                                    console.log('[DEBUG] 재시도 최종 매칭 성공: ' + text);
                                    return item;
                                }
                            }
                            return null;
                        """, target_size_converted, target_color, len(available['colors']) > 1)
                        
                        if matching_item:
                            item_text = matching_item.text.strip()
                            if f"{active_tab} {target_size_converted}" in item_text and "(EU" in item_text:
                                already_selected = False
                                for m in matched:
                                    if m[4] == size:
                                        already_selected = True
                                        break
                                
                                if already_selected:
                                    self.log_to_queue(f"[SKIP] {size} 이미 선택됨")
                                    continue
                            
                            self.driver.execute_script("arguments[0].click();", matching_item)
                            self.log_to_queue(f"[OK] 변환 사이즈로 선택: {item_text}")
                            matched.append((idx, brand_name, code, color, size, cost, item_text))
                            found = True
                    except Exception as e:
                        self.log_to_queue(f"[ERROR] 재시도 JavaScript 매칭 실패: {type(e).__name__}")
                
                if not found:
                    self.log_to_queue(f"[FAIL] {active_tab} 탭에서 {size} 찾기 실패")
                    # 비슷한 사이즈 찾기 (디버깅용)
                    similar_items = []
                    for item in all_items[:20]:  # 처음 20개만 확인
                        item_text = item.text.strip()
                        if target_size in item_text or size in item_text:
                            similar_items.append(item_text)
                    if similar_items:
                        self.log_to_queue(f"[DEBUG] 비슷한 아이템들: {similar_items[:5]}")
                    self.log_fail(idx, brand_name, code, color, size, cost, f"{active_tab}탭매칭실패")
        
        self.log_to_queue(f"\n[완료] 매칭: {len(matched)}/{len(entries)}")
        return matched

    def setup_pricing(self, base_price):
        self.log_to_queue("[STEP] 가격 설정")
        # Specified Price 모드 선택
        try:
            self.wait_and_click((By.XPATH, "//div[contains(.,'Specified Price')]/.."), timeout=5)
            self.log_to_queue("[OK] Specified Price 선택")
        except TimeoutException:
            self.log_to_queue("[WARN] Specified Price 없음")
            
        # 필드 입력
        fields = [('Qty', 10), ('Purchase Cost', base_price), ('Operating Cost', 0)]
        for label, value in fields:
            try:
                field = self.wait.until(
                    EC.presence_of_element_located(
                        (By.XPATH, f"//span[normalize-space()='{label}']/following::input[1]")
                    )
                )
                field.clear()
                field.send_keys(str(value))
                self.log_to_queue(f"  - {label}={value}")
            except TimeoutException:
                self.log_to_queue(f"[WARN] {label} 입력 실패")
        
        # 모든 입력 완료 후 DOM 업데이트를 위한 최소 대기
        time.sleep(0.2)

    def click_apply(self):
        self.log_to_queue("[STEP] Apply 버튼 클릭")
        try:
            # Apply 버튼이 활성화될 때까지 대기 (최대 15초)
            def check_button_enabled(driver):
                try:
                    btn = driver.find_element(By.XPATH, "//button[span[text()='Apply']]")
                    return btn if (btn.is_enabled() and 'disabled' not in (btn.get_attribute("class") or "")) else False
                except NoSuchElementException:
                    return False
            
            apply_btn = WebDriverWait(self.driver, 15).until(check_button_enabled)
            
            # 버튼 클릭
            apply_btn.click()
            self.log_to_queue("[OK] Apply 클릭 완료")
            
            # 클릭 후 페이지 업데이트 대기 (최소 대기)
            time.sleep(0.3)
            
        except TimeoutException:
            self.log_to_queue("[WARN] Apply 버튼 활성화 실패 (15초 초과)")
        except Exception as e:
            self.log_to_queue(f"[ERROR] Apply 버튼 클릭 실패: {type(e).__name__}")

    def process_bids(self, matched, code, brand):
        self.log_to_queue("[STEP] 입찰 처리")
        successful = []
        all_failed = True  # 모든 입찰이 실패했는지 추적
        
        for match_info in matched:
            idx, brand_name, code, color, size, cost, matched_text = match_info
            self.log_to_queue(f"\n[PROCESS] {matched_text} 입찰 시작")
            retry_count = 0
            consecutive_fails = 0
            bid_success = False  # 개별 입찰 성공 여부
            
            while retry_count < MAX_RETRIES:
                try:
                    # Row 찾기 (매칭된 텍스트로)
                    # matched_text에는 실제 선택된 텍스트가 있음 (예: "Silver JP 26")
                    # 이를 이용해서 row를 찾아야 함
                    row = self.driver.find_element(
                        By.XPATH, 
                        f"//tr[.//div[contains(text(),'{matched_text}')]]"
                    )
                    
                    # 먼저 Asia 체크 확인
                    asia_checked = self.is_asia_checked(row)
                    
                    # 정보 추출
                    est_payout = self.find_est_payout(row)
                    profit = est_payout - cost
                    
                    self.log_to_queue(f"[CHECK] {matched_text} | 예상수익: {est_payout}, Asia: {asia_checked}, "
                          f"수익: {profit}, 기준가: {cost}")
                    
                    # 현재 가격 확인 (디버깅용)
                    try:
                        current_price_input = row.find_element(
                            By.CSS_SELECTOR, 
                            "td.inputNumberV2___dIR0i input[value]"
                        )
                        current_price = self.get_int(current_price_input.get_attribute("value"))
                        self.log_to_queue(f"[DEBUG] 현재 입찰가: {current_price}")
                    except:
                        current_price = 0
                    
                    # Asia 체크된 경우 바로 처리
                    if asia_checked:
                        self.log_to_queue(f"[INFO] Asia 체크됨 - 다운 버튼 클릭 없이 바로 처리")
                        # Asia 체크된 경우 조건 확인
                        self.log_to_queue(f"[DEBUG] Asia 체크됨 - 예상수익: {est_payout}, 기준가: {cost}, 최소수익: {self.min_profit}")
                        
                        if est_payout >= cost:
                            self.log_to_queue(f"[DEBUG] 수익: {profit}, 최소수익 기준: {self.min_profit}")
                            
                            if profit >= self.min_profit:
                                self.log_to_queue(f"[OK] 입찰조건 충족: {matched_text} (수익: {profit}원)")
                                successful.append(match_info)
                                bid_success = True
                                all_failed = False
                            else:
                                self.log_to_queue(f"[INFO] 최소수익 미달 (수익: {profit} < 최소: {self.min_profit})")
                                self.log_fail(idx, brand_name, code, color, size, cost, f'최소수익 미달 {profit}')
                                self.log_to_queue(f"[ACTION] Remove 시도: {matched_text}")
                                self.click_remove(row)
                                time.sleep(0.5)  # Remove 후 추가 대기
                        else:
                            self.log_to_queue(f"[INFO] 예상수익이 기준가보다 낮음 ({est_payout} < {cost})")
                            self.log_fail(idx, brand_name, code, color, size, cost, 'Asia 체크시 예상수익 < 기준가')
                            self.log_to_queue(f"[ACTION] Remove 시도: {matched_text}")
                            self.click_remove(row)
                            time.sleep(0.5)  # Remove 후 추가 대기
                        break  # Asia 체크 처리 후 while 루프 종료
                    
                    # Asia 체크가 안 되어 있으면 다운 버튼 클릭
                    self.log_to_queue(f"[INFO] Asia 체크 안 됨 - 다운 버튼 클릭 시도")
                    if not self.click_down_button(row):
                        consecutive_fails += 1
                        self.log_to_queue(f"[INFO] 가격 조정 실패 (연속 {consecutive_fails}회)")
                        
                        # 연속 3회 실패 시 Remove
                        if consecutive_fails >= 3:
                            self.log_to_queue(f"[INFO] 연속 실패로 인한 Remove")
                            self.log_fail(idx, brand_name, code, color, size, cost, '가격 조정 불가 Remove')
                            self.click_remove(row)
                            break
                        
                        # 잠시 대기 후 재시도
                        time.sleep(2)
                    else:
                        consecutive_fails = 0  # 성공 시 카운터 리셋
                        
                except StaleElementReferenceException:
                    retry_count += 1
                    self.log_to_queue(f"[RETRY] DOM 변경 감지, 재시도 {retry_count}/{MAX_RETRIES}")
                    time.sleep(1)
                except NoSuchElementException:
                    self.log_to_queue(f"[ERROR] {matched_text} row를 찾을 수 없음")
                    self.log_fail(idx, brand_name, code, color, size, cost, "row 못찾음")
                    break
                except Exception as e:
                    self.log_to_queue(f"[ERROR] 예상치 못한 오류: {type(e).__name__} - {e}")
                    break
        
        # 모든 입찰이 실패한 경우 뒤로 가기
        if all_failed and len(matched) > 0:
            self.log_to_queue("\n[WARN] 모든 사이즈 입찰 실패 - 가격 조정 불가")
            self.go_back_and_reset()
            return []  # 빈 리스트 반환하여 Confirm 단계 스킵
                    
        return successful

    def confirm_bids(self):
        self.log_to_queue("\n[STEP] 최종 확인")
        
        # 성공한 항목이 있는지 먼저 확인
        try:
            # 테이블에 남아있는 row가 있는지 확인
            remaining_rows = self.driver.find_elements(
                By.CSS_SELECTOR, 
                "tbody.ant-table-tbody tr"
            )
            
            if not remaining_rows:
                self.log_to_queue("[INFO] 입찰할 항목이 없습니다")
                return
                
            self.log_to_queue(f"[INFO] {len(remaining_rows)}개 항목 확인 대기 중...")
            
        except Exception as e:
            self.log_to_queue(f"[WARN] 테이블 확인 실패: {type(e).__name__}")
        
        # 페이지 스크롤 다운 (버튼이 화면 아래에 있을 수 있음)
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        
        # Confirm 버튼 클릭
        self.log_to_queue("[DEBUG] Confirm 버튼 찾기 시작...")
        
        try:
            # WebDriverWait으로 Confirm 버튼 찾기
            confirm_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Confirm') or contains(., 'confirm')]"))
            )
            
            # 버튼 텍스트 확인
            btn_text = confirm_btn.text
            self.log_to_queue(f"[DEBUG] Confirm 버튼 발견: '{btn_text}'")
            
            # JavaScript로 클릭 (더 안정적)
            self.driver.execute_script("arguments[0].click();", confirm_btn)
            self.log_to_queue("  ✓ Confirm 클릭 성공")
            
        except TimeoutException:
            self.log_to_queue("[ERROR] Confirm 버튼을 찾을 수 없습니다 (10초 초과)")
            return
        except Exception as e:
            self.log_to_queue(f"[ERROR] Confirm 버튼 클릭 실패: {type(e).__name__}")
            return
        
        # OK 버튼 대기 및 클릭
        # 모달이 나타날 때까지 대기 (WebDriverWait 사용)
        try:
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'ant-modal')]//button[span[text()='OK']]"))
            )
        except TimeoutException:
            self.log_to_queue("[WARNING] OK 버튼 모달이 나타나지 않음")
        
        ok_clicked = False
        self.log_to_queue("\n[DEBUG] OK 버튼 찾기 시작...")
        
        # OK 버튼 찾기 시도
        ok_methods = [
            # 방법 1: 모달 내부에서 찾기
            ("By.XPATH", "//div[contains(@class, 'ant-modal')]//button[span[text()='OK']]"),
            # 방법 2: 단순 텍스트
            ("By.XPATH", "//button[contains(., 'OK')]"),
            # 방법 3: span 텍스트
            ("By.XPATH", "//button[span[contains(text(), 'OK')]]"),
            # 방법 4: 모든 primary 버튼
            ("By.CSS_SELECTOR", ".ant-modal button.ant-btn-primary"),
            # 방법 5: 보이는 모든 버튼 중 OK 찾기
            ("By.TAG_NAME", "button"),
        ]
        
        for attempt in range(5):
            for method_name, selector in ok_methods:
                try:
                    if method_name == "By.TAG_NAME":
                        elements = self.driver.find_elements(By.TAG_NAME, selector)
                        for elem in elements:
                            if elem.is_displayed() and elem.text == "OK":
                                self.driver.execute_script("arguments[0].click();", elem)
                                self.log_to_queue("  ✓ OK 클릭 성공")
                                ok_clicked = True
                                break
                    else:
                        if method_name == "By.XPATH":
                            elem = self.driver.find_element(By.XPATH, selector)
                        else:
                            elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                        
                        if elem.is_displayed():
                            self.driver.execute_script("arguments[0].click();", elem)
                            self.log_to_queue("  ✓ OK 클릭 성공")
                            ok_clicked = True
                            break
                            
                except:
                    continue
                    
            if ok_clicked:
                break
            else:
                self.log_to_queue(f"[DEBUG] OK 버튼 찾기 시도 {attempt+1}/5")
                time.sleep(2)
        
        if not ok_clicked:
            self.log_to_queue("[ERROR] OK 버튼 자동 클릭 실패")
        else:
            # 입찰 처리 완료 대기 (동그라미 돌기)
            self.log_to_queue("[INFO] 입찰 처리 중... (로딩 대기)")
            try:
                # 로딩 스피너가 나타났다가 사라질 때까지 대기
                # 먼저 로딩 스피너가 나타나기를 잠시 기다림
                time.sleep(0.5)
                
                # 로딩 스피너가 사라질 때까지 대기 (최대 10초)
                WebDriverWait(self.driver, 10).until_not(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".ant-spin-spinning, .ant-spin-container, .ant-spin"))
                )
                self.log_to_queue("[OK] 입찰 처리 완료")
                
                # 추가 대기 시간 (안정성을 위해)
                time.sleep(2)
                
            except TimeoutException:
                self.log_to_queue("[WARN] 로딩 대기 시간 초과 - 계속 진행")
                time.sleep(3)  # 최소 대기
            except Exception as e:
                self.log_to_queue(f"[WARN] 로딩 확인 실패: {type(e).__name__}")
                time.sleep(3)  # 최소 대기
        
        # OK 클릭 후 모달 닫기 처리
        time.sleep(2)  # OK 후 잠시 대기
        
        # 모달 닫기(X) 버튼 처리
        self.log_to_queue("\n[DEBUG] 모달 닫기 버튼 확인 중...")
        close_clicked = False
        
        for attempt in range(3):
            try:
                # 모달 닫기 버튼 찾기
                close_methods = [
                    ("By.XPATH", "//button[@aria-label='Close' and @class='ant-modal-close']"),
                    ("By.CSS_SELECTOR", "button.ant-modal-close"),
                    ("By.XPATH", "//span[@aria-label='close' and contains(@class, 'ant-modal-close-icon')]"),
                    ("By.XPATH", "//button[contains(@class, 'ant-modal-close')]"),
                ]
                
                for method_name, selector in close_methods:
                    try:
                        if method_name == "By.XPATH":
                            close_btn = self.driver.find_element(By.XPATH, selector)
                        else:
                            close_btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                        
                        if close_btn.is_displayed():
                            # JavaScript로 클릭
                            self.driver.execute_script("arguments[0].click();", close_btn)
                            self.log_to_queue("  ✓ 모달 닫기(X) 클릭 성공")
                            close_clicked = True
                            time.sleep(1)
                            break
                    except:
                        continue
                
                if close_clicked:
                    break
                    
            except:
                pass
            
            time.sleep(1)
        
        # Dismiss 버튼 확인 (모달 닫기 후에도 나올 수 있음)
        self.log_to_queue("\n[DEBUG] Dismiss 버튼 확인 중...")
        dismiss_clicked = False
        
        for attempt in range(3):
            try:
                # Dismiss 버튼 찾기
                dismiss_methods = [
                    ("By.XPATH", "//button[span[text()='Dismiss']]"),
                    ("By.XPATH", "//button[contains(., 'Dismiss')]"),
                    ("By.XPATH", "//button[contains(@class, 'defaultButton') and span[text()='Dismiss']]"),
                    ("By.CSS_SELECTOR", "button.ant-btn-default"),
                ]
                
                for method_name, selector in dismiss_methods:
                    try:
                        if method_name == "By.XPATH":
                            dismiss_btn = self.driver.find_element(By.XPATH, selector)
                        else:
                            dismiss_btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                        
                        if dismiss_btn.is_displayed() and "dismiss" in dismiss_btn.text.lower():
                            # JavaScript로 클릭
                            self.driver.execute_script("arguments[0].click();", dismiss_btn)
                            self.log_to_queue("  ✓ Dismiss 클릭 성공")
                            dismiss_clicked = True
                            break
                    except:
                        continue
                
                if dismiss_clicked:
                    break
                    
            except:
                pass
            
            # Dismiss가 없으면 정상 (모든 경우에 나타나지 않음)
            if attempt == 0 and not dismiss_clicked:
                self.log_to_queue("[INFO] Dismiss 버튼이 없습니다 (정상)")
                break
            
            time.sleep(1)
        
        if close_clicked:
            self.log_to_queue("[INFO] 모달 닫기 처리 완료")
        if dismiss_clicked:
            self.log_to_queue("[INFO] Dismiss 처리 완료")
        
        self.log_to_queue("\n[SUCCESS] 입찰이 완료되었습니다!")


# 메인 실행 클래스
class PoizonAutoBidderMultiProcess:
    def __init__(self):
        self.min_profit = 0
        
    # -- 파일 및 설정 선택
    def select_file(self, title, filetypes):
        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo("Poizon Auto-Bid (Multi-Process)", title)
        path = filedialog.askopenfilename(filetypes=filetypes)
        if not path:
            messagebox.showwarning("취소됨", f"{title} - 취소, 종료합니다.")
            raise SystemExit("파일 선택 취소")
        print(f"[DEBUG] 파일 선택 완료: {path}")
        return path

    # -- 최소 수익 입력
    def ask_min_profit(self):
        root = tk.Tk()
        root.withdraw()
        val = simpledialog.askinteger(
            "Poizon Auto-Bid (Multi-Process)", 
            "최소 예상수익 (KRW):", 
            minvalue=0, 
            parent=root
        )
        if val is None:
            messagebox.showwarning("취소됨", "입력 취소, 종료합니다.")
            raise SystemExit("최소 수익 입력 취소")
        print(f"[DEBUG] 최소수익 입력: {val}")
        self.min_profit = val
        return val

    # -- 입찰 데이터 로드 (브랜드, 색상 추가)
    def load_bid_data(self, fp):
        data = []
        with open(fp, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.lower().startswith('total'):
                    continue
                parts = line.split(',')
                
                # 새로운 형식: 브랜드,상품코드,색상,사이즈,가격
                if len(parts) == 5:
                    try:
                        price = int(parts[4].strip())
                        if price <= 0:
                            print(f"[WARN] 라인 {i}: 비정상 가격 {price} - 스킵")
                            continue
                        
                        # 색상과 사이즈 처리
                        color_field = parts[2].strip()
                        size_field = parts[3].strip()
                        
                        # 색상 필드가 비어있고 사이즈 필드에 색상이 포함된 경우 처리
                        # 예: "","Blue 245" -> "Blue","245"
                        if not color_field and ' ' in size_field:
                            parts_size = size_field.split(' ', 1)
                            if len(parts_size) == 2 and not parts_size[1].isdigit():
                                # 순서가 바뀐 경우 (예: "245 Blue")
                                if parts_size[0].isdigit():
                                    size_field = parts_size[0]
                                    color_field = parts_size[1]
                                else:
                                    # 정상 순서 (예: "Blue 245")
                                    color_field = parts_size[0]
                                    size_field = parts_size[1]
                        
                        data.append((
                            i, 
                            parts[0].strip(),  # 브랜드
                            parts[1].strip(),  # 상품코드
                            color_field,       # 색상
                            size_field,        # 사이즈
                            price
                        ))
                    except ValueError:
                        print(f"[WARN] 라인 {i}: 파싱 실패 - 스킵")
                # 기존 형식 호환: 상품코드,사이즈,가격
                elif len(parts) == 3:
                    try:
                        price = int(parts[2].strip())
                        if price <= 0:
                            print(f"[WARN] 라인 {i}: 비정상 가격 {price} - 스킵")
                            continue
                        data.append((
                            i, 
                            "",  # 브랜드 없음
                            parts[0].strip(),  # 상품코드
                            "",  # 색상 없음
                            parts[1].strip(),  # 사이즈
                            price
                        ))
                    except ValueError:
                        print(f"[WARN] 라인 {i}: 가격 파싱 실패 - 스킵")
                        
        print(f"[DEBUG] 입찰 데이터 로드: 총 {len(data)} 건")
        return data

    def log_processor(self, result_queue):
        """로그 처리 프로세스"""
        fail_logs = []
        last_messages = {}  # 워커별 마지막 메시지 추적
        
        while True:
            try:
                msg_type, content = result_queue.get(timeout=1)
                
                if msg_type == "LOG":
                    # 워커 ID 추출
                    if "[Worker" in content:
                        try:
                            worker_id = int(content.split("[Worker ")[1].split("]")[0])
                            # 동일한 메시지 반복 방지
                            if last_messages.get(worker_id) != content:
                                print(content, flush=True)  # flush 추가
                                last_messages[worker_id] = content
                        except:
                            print(content, flush=True)  # flush 추가
                    else:
                        print(content, flush=True)  # flush 추가
                elif msg_type == "FAIL_LOG":
                    fail_logs.append(content)
                elif msg_type == "ERROR":
                    print(f"[ERROR] {content}", flush=True)  # flush 추가
                elif msg_type == "COMPLETE":
                    print(f"[COMPLETE] {content}", flush=True)  # flush 추가
                elif msg_type == "TERMINATE":
                    # 로그 파일 저장
                    if fail_logs:
                        with open(LOGFILE, 'w', encoding='utf-8') as f:
                            for log in fail_logs:
                                f.write(log + "\n")
                        print(f"\n[INFO] 실패 로그 저장 완료: {LOGFILE}")
                    break
                    
            except Exception as e:
                if "Empty" in str(type(e)):
                    continue
                else:
                    print(f"[ERROR] 로그 처리 오류: {e}")

    def run(self):
        # 로그 파일 초기화
        if os.path.exists(LOGFILE):
            os.remove(LOGFILE)
            
        # 쿠키 파일 확인
        if os.path.exists(COOKIE_FILE):
            print(f"[INFO] 기존 쿠키 파일 발견: {COOKIE_FILE}")
            answer = input("기존 쿠키를 삭제하고 새로 로그인하시겠습니까? (y/n): ")
            if answer.lower() == 'y':
                os.remove(COOKIE_FILE)
                print("[INFO] 쿠키 파일 삭제됨")
            
        try:
            # 파일 선택
            bid_file = self.select_file("입찰 데이터 TXT 선택", [("Text", "*.txt")])
            min_profit = self.ask_min_profit()
            driver_path = self.select_file("chromedriver.exe 선택", [("ChromeDriver", "chromedriver.exe")])
            
            # 데이터 로드
            raw = self.load_bid_data(bid_file)
            if not raw:
                raise ValueError("입력 데이터가 없습니다")
                
            # 코드별 그룹화 (상품코드로 그룹화)
            groups = defaultdict(list)
            for rec in raw:
                code = rec[2]  # 상품코드는 인덱스 2
                groups[code].append(rec)
            print(f"[INFO] 그룹화 완료: {len(groups)} 개 코드")
            
            # Manager 생성
            manager = Manager()
            task_queue = manager.Queue()
            result_queue = manager.Queue()
            status_dict = manager.dict()
            login_complete = manager.Value('b', False)  # 로그인 상태 공유 변수
            
            # 전체 통계 정보 추가
            total_codes = len(groups)  # 상품 코드 수
            stats = manager.dict()
            stats['total'] = total_codes  # 상품번호 단위로 카운트
            stats['completed'] = 0
            stats['success'] = 0
            stats['failed'] = 0
            
            # 작업 큐에 추가
            for code, entries in groups.items():
                task_queue.put((code, entries))
            
            # 종료 신호 추가
            for _ in range(WORKER_COUNT):
                task_queue.put(None)
            
            print(f"\n[INFO] {WORKER_COUNT}개의 워커 프로세스로 작업을 시작합니다.")
            print("[INFO] 첫 번째 Chrome 창에서 로그인해주세요.")
            print("[INFO] 나머지 워커들은 headless 모드로 실행됩니다.\n")
            
            # 상태 모니터 프로세스 시작
            monitor_proc = Process(target=status_monitor, args=(status_dict, login_complete, stats))
            monitor_proc.daemon = True
            monitor_proc.start()
            
            # 로그 처리 프로세스 시작
            log_proc = Process(target=self.log_processor, args=(result_queue,))
            log_proc.daemon = True
            log_proc.start()
            
            # 워커 프로세스들 시작
            workers = []
            for i in range(1, WORKER_COUNT + 1):
                worker = Process(
                    target=worker_process,
                    args=(i, task_queue, result_queue, status_dict, login_complete, min_profit, driver_path, stats)
                )
                workers.append(worker)
                worker.start()
                
                # 첫 번째 워커 시작 후 잠시 대기
                if i == 1:
                    time.sleep(3)  # 로그인 창이 먼저 뜨도록
            
            # 모든 워커 종료 대기
            for worker in workers:
                worker.join()
            
            # 로그 프로세스 종료
            result_queue.put(("TERMINATE", None))
            log_proc.join()
            
            # 상태 모니터 종료
            monitor_proc.terminate()
            
            print("\n[INFO] 모든 작업 완료!")
            print("[INFO] 프로그램을 종료하려면 ENTER를 누르세요...")
            input()
                
        except Exception as e:
            print(f"[ERROR] 프로그램 실행 중 오류: {type(e).__name__} - {e}")
            print("[INFO] 프로그램을 종료하려면 ENTER를 누르세요...")
            input()
            raise


# 메인 실행
if __name__ == '__main__':
    # Windows에서 multiprocessing 사용 시 필요
    multiprocessing.freeze_support()
    
    try:
        bidder = PoizonAutoBidderMultiProcess()
        bidder.run()
    except Exception as e:
        print(f"\n[FATAL] 프로그램 비정상 종료: {e}")
    finally:
        print("\n[INFO] 프로그램을 종료하려면 ENTER를 누르세요...")
        input()
