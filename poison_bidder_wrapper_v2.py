#!/usr/bin/env python3
"""
포이즌 입찰 Wrapper V2
0923_fixed_multiprocess_cookie_v2.py의 실제 로직을 활용하는 래퍼
"""

import os
import sys
import json
import logging
import importlib.util
import time
import re
import pickle
import traceback
import functools
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from multiprocessing import Manager, Process
from typing import List, Dict, Any, Optional, Tuple

# 무신사 로그인 관련 imports
from login_manager import LoginManager
from dotenv import load_dotenv
from musinsa_scraper_improved import enhanced_close_musinsa_popup
from chrome_driver_manager import initialize_chrome_driver

# Selenium imports
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import (
    TimeoutException, 
    StaleElementReferenceException,
    NoSuchElementException,
    ElementClickInterceptedException
)
from selenium.webdriver.common.keys import Keys

# 로깅 설정
log_dir = Path('C:/poison_final/logs')
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_dir / f'poison_bidder_wrapper_{datetime.now().strftime("%Y%m%d")}.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 환경변수 로드
load_dotenv()

# 무신사 로그인 계정 정보
MUSINSA_ID = os.getenv('MUSINSA_ID')
MUSINSA_PASSWORD = os.getenv('MUSINSA_PASSWORD')

# 환경변수 누락 확인
if not MUSINSA_ID or not MUSINSA_PASSWORD:
    logger.warning("[경고] 무신사 로그인 정보가 환경변수에 설정되지 않았습니다.")
    logger.warning("MUSINSA_ID와 MUSINSA_PASSWORD를 .env 파일에 설정해주세요.")

# 설정 상수 (원본 파일에서 복사)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
LOGFILE = os.path.join(CURRENT_DIR, "poizon_bid_fail_log.txt")
COOKIE_FILE = os.path.join(CURRENT_DIR, "poizon_cookies.pkl")  # 쿠키 파일
PRICE_STEP = 1000     # 가격 조정 단위
MAX_RETRIES = 3       # 재시도 횟수
DEFAULT_WAIT_TIME = 15  # 기본 대기 시간

# 포이즌 로그인 계정 정보 (poison_direct_login.py와 동일)
PHONE_NUMBER = "1099209275"  # 포이즌 계정 전화번호
PASSWORD = "99006622kK"      # 포이즌 계정 비밀번호

# 브랜드별 검색 규칙
BRAND_SEARCH_RULES = {
    "반스": "remove_last_1",      # VN0001 → VN000
    "살로몬": "remove_L_and_00",  # L12345600 → 123456
    "SALOMON": "remove_L_and_00",  # 대문자도 지원
}

# 브랜드별 사이즈 형식 (예: 아식스의 경우 "2E-Width JP 24.5" 형식)
BRAND_SIZE_FORMATS = {
    "아식스": {
        "JP": "Width JP",  # "2E-Width JP 24.5"에서 "JP 24.5" 패턴 매칭
        "US": "Width US"   # 필요시 US 형식도 추가 가능
    },
    "ASICS": {  # 영문명도 지원
        "JP": "Width JP",
        "US": "Width US"
    }
    # 다른 브랜드의 특수 형식도 여기에 추가
    # 예: "뉴발란스": {"JP": "JPN", "US": "US Men"}
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


def log_processor_worker(result_queue, result_list_queue):
    """로그 처리 워커 프로세스 (모듈 레벨 함수)"""
    results = []
    fail_logs = []
    
    while True:
        try:
            msg_type, content = result_queue.get(timeout=1)
            
            if msg_type == "LOG":
                logger.info(content)
            elif msg_type == "FAIL_LOG":
                fail_logs.append(content)
            elif msg_type == "ERROR":
                logger.error(content)
            elif msg_type == "COMPLETE":
                logger.info(f"[완료] {content}")
            elif msg_type == "RESULT":
                results.append(content)
            elif msg_type == "TERMINATE":
                # 종료 시 결과 반환
                result_list_queue.put(('results', results))
                result_list_queue.put(('fail_logs', fail_logs))
                break
        except:
            continue


def worker_process_wrapper(worker_id, task_queue, result_queue, status_dict, login_complete, min_profit, driver_path, stats, musinsa_cookies=None, discount_rate=0):
    """워커 프로세스 래퍼 (모듈 레벨 함수)"""
    bidder = None
    try:
        # 상태 업데이트
        status_dict[worker_id] = {"status": "초기화중", "code": "", "progress": ""}
        
        # PoizonAutoBidderWorker 인스턴스 생성
        bidder = PoizonAutoBidderWorker(worker_id, result_queue, status_dict)
        bidder.min_profit = min_profit
        bidder.discount_rate = discount_rate
        
        # 무신사 어댑터 초기화 (무신사 쿠키가 있는 경우)
        musinsa_adapter = None
        if musinsa_cookies:
            result_queue.put(("LOG", f"[Worker {worker_id}] 무신사 어댑터 초기화"))
            # PoizonBidderWrapperV2 인스턴스가 필요함
            # 여기서는 간단히 None을 전달하고 나중에 수정
            musinsa_adapter = MusinsaBidderAdapter(worker_id, result_queue, None)
            musinsa_adapter.set_musinsa_cookies(musinsa_cookies)
        
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
            
            # 성능 최적화 옵션
            chrome_options.add_argument('--disable-logging')
            chrome_options.add_argument('--log-level=3')
            chrome_options.add_argument('--silent')
            
            # 메모리 최적화 옵션
            chrome_options.add_argument('--memory-pressure-off')
            chrome_options.add_argument('--disable-software-rasterizer')
            chrome_options.add_argument('--disable-background-timer-throttling')
            chrome_options.add_argument('--disable-backgrounding-occluded-windows')
            chrome_options.add_argument('--disable-renderer-backgrounding')
            chrome_options.add_argument('--disable-features=TranslateUI')
            chrome_options.add_argument('--disable-ipc-flooding-protection')
            chrome_options.add_argument('--disable-default-apps')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-hang-monitor')
            chrome_options.add_argument('--disable-sync')
            chrome_options.add_argument('--disable-web-resources')
            chrome_options.add_argument('--safebrowsing-disable-download-protection')
            chrome_options.add_argument('--disable-client-side-phishing-detection')
            chrome_options.add_argument('--disable-component-update')
            chrome_options.add_argument('--disable-domain-reliability')
            
            # JavaScript 메모리 제한 설정
            chrome_options.add_argument('--js-flags=--max-old-space-size=512')
            
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
            chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Chrome 드라이버 초기화 (chrome_driver_manager 사용)
            try:
                # chrome_driver_manager.initialize_chrome_driver() 사용
                bidder.driver = initialize_chrome_driver(options=chrome_options)
                result_queue.put(("LOG", f"[Worker {worker_id}] Chrome 드라이버 초기화 성공 (chrome_driver_manager 사용)"))
            except Exception as e:
                # fallback: webdriver-manager 직접 사용
                try:
                    from webdriver_manager.chrome import ChromeDriverManager
                    bidder.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
                    result_queue.put(("LOG", f"[Worker {worker_id}] Chrome 드라이버 초기화 성공 (webdriver-manager 직접 사용)"))
                except Exception as fallback_error:
                    # 최종 fallback: 기존 driver_path 사용
                    result_queue.put(("LOG", f"[Worker {worker_id}] chrome_driver_manager 실패, 기존 방식 시도..."))
                    bidder.driver = webdriver.Chrome(service=Service(driver_path), options=chrome_options)
            
            bidder.wait = WebDriverWait(bidder.driver, DEFAULT_WAIT_TIME)
            
            result_queue.put(("LOG", f"[Worker {worker_id}] Chrome 드라이버 초기화 성공!"))
            
        except Exception as e:
            status_dict[worker_id] = {"status": "초기화 실패", "code": "", "progress": ""}
            error_msg = f"Worker {worker_id} Chrome 드라이버 초기화 실패: {type(e).__name__} - {str(e)}"
            result_queue.put(("ERROR", error_msg))
            
            # ChromeDriver 관련 오류인 경우 추가 안내
            if "NoSuchDriverException" in type(e).__name__ or "chromedriver" in str(e).lower():
                result_queue.put(("ERROR", "======= ChromeDriver 오류 해결 방법 ======="))
                result_queue.put(("ERROR", "1. ChromeDriver가 설치되지 않았습니다."))
                result_queue.put(("ERROR", "2. 다음 명령을 실행하여 설치하세요:"))
                result_queue.put(("ERROR", "   python C:/poison_final/download_chromedriver.py"))
                result_queue.put(("ERROR", "3. 또는 프로그램을 재시작하면 자동으로 설치됩니다."))
                result_queue.put(("ERROR", "========================================="))
            
            raise
        
        # 로그인 처리
        if worker_id == 1:
            # 첫 번째 워커: 자동 로그인
            bidder.driver.get("https://seller.poizon.com/main/dataBoard")
            result_queue.put(("LOG", f"[Worker {worker_id}] 로그인 페이지 로드 중..."))
            time.sleep(5)
            
            # 로그인 페이지인지 확인
            try:
                page_text = bidder.driver.find_element(By.TAG_NAME, "body").text
                if "Log In" not in page_text:
                    result_queue.put(("LOG", f"[Worker {worker_id}] 이미 로그인되어 있습니다!"))
                    
                    # 쿠키 저장
                    save_cookies(bidder.driver)
                    result_queue.put(("LOG", f"[Worker {worker_id}] 쿠키 저장 완료"))
                    login_complete.value = True
                else:
                    # 자동 로그인 시작
                    result_queue.put(("LOG", f"[Worker {worker_id}] 자동 로그인 시작..."))
                    wait = WebDriverWait(bidder.driver, 10)
                    
                    # 1. 전화번호 입력
                    result_queue.put(("LOG", f"[Worker {worker_id}] 전화번호 입력: {PHONE_NUMBER}"))
                    phone_input = wait.until(
                        EC.presence_of_element_located((By.ID, "mobile_number"))
                    )
                    phone_input.clear()
                    phone_input.send_keys(PHONE_NUMBER)
                    time.sleep(1)
                    
                    # 2. 국가 코드 선택 (South Korea +82)
                    result_queue.put(("LOG", f"[Worker {worker_id}] 국가 코드 선택..."))
                    country_selector = wait.until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, ".countrySelect___rlSKW .ant-select-selector"))
                    )
                    country_selector.click()
                    time.sleep(1)
                    
                    # JavaScript로 South Korea 선택
                    bidder.driver.execute_script("""
                        const dropdownList = document.querySelector('.ant-select-dropdown .rc-virtual-list-holder');
                        if (!dropdownList) {
                            const dropdownList = document.querySelector('.ant-select-dropdown');
                        }
                        
                        const options = document.querySelectorAll('.ant-select-item-option');
                        
                        for (let option of options) {
                            if (option.textContent.includes('South Korea')) {
                                option.scrollIntoView({ block: 'center', behavior: 'smooth' });
                                setTimeout(() => option.click(), 500);
                                break;
                            }
                        }
                    """)
                    time.sleep(1)
                    
                    # 3. 비밀번호 입력
                    result_queue.put(("LOG", f"[Worker {worker_id}] 비밀번호 입력..."))
                    password_input = bidder.driver.find_element(By.ID, "password")
                    password_input.clear()
                    password_input.send_keys(PASSWORD)
                    time.sleep(1)
                    
                    # 4. 로그인 버튼 클릭
                    result_queue.put(("LOG", f"[Worker {worker_id}] 로그인 버튼 클릭..."))
                    login_button = bidder.driver.find_element(
                        By.XPATH, "//button[span[text()='Log In']]"
                    )
                    login_button.click()
                    
                    # 로그인 완료 대기
                    result_queue.put(("LOG", f"[Worker {worker_id}] 로그인 처리 중..."))
                    time.sleep(5)
                    
                    # 로그인 성공 확인
                    check_count = 0
                    while check_count < 30:  # 최대 30초 대기
                        check_count += 1
                        try:
                            current_url = bidder.driver.current_url
                            
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
                        
                        time.sleep(1)
                    
                    if not login_complete.value:
                        result_queue.put(("ERROR", f"[Worker {worker_id}] 자동 로그인 실패. 수동 로그인이 필요합니다."))
                        result_queue.put(("LOG", f"[Worker {worker_id}] 수동 로그인 대기 중..."))
                        
                        # 수동 로그인 대기
                        while not login_complete.value:
                            check_count += 1
                            try:
                                current_url = bidder.driver.current_url
                                result_queue.put(("LOG", f"[Worker {worker_id}] URL 확인 #{check_count}: {current_url}"))
                                
                                if "dataBoard" in current_url and "login" not in current_url.lower():
                                    # 로그인 성공 확인
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
                            
                            time.sleep(3)
                
            except Exception as e:
                result_queue.put(("ERROR", f"[Worker {worker_id}] 로그인 처리 중 오류: {str(e)}"))
                result_queue.put(("LOG", f"[Worker {worker_id}] 수동 로그인 대기 중..."))
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
                            time.sleep(worker_id * 0.3)  # 워커별 시작 시간 분산
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


# 무신사 입찰 어댑터 클래스
class MusinsaBidderAdapter:
    """무신사 상품을 포이즌 입찰 시스템에서 처리하기 위한 어댑터"""
    
    def __init__(self, worker_id, result_queue, wrapper_instance):
        self.worker_id = worker_id
        self.result_queue = result_queue
        self.wrapper = wrapper_instance
        self.musinsa_cookies = None
        
    def log_to_queue(self, message):
        """큐를 통한 로그 전송"""
        self.result_queue.put(("LOG", f"[Worker {self.worker_id}] [무신사] {message}"))
    
    def set_musinsa_cookies(self, cookies):
        """무신사 쿠키 설정"""
        self.musinsa_cookies = cookies
        self.log_to_queue("무신사 쿠키 설정 완료")
    
    def process_musinsa_item(self, item):
        """무신사 상품 처리"""
        try:
            # 무신사 URL 확인
            if 'url' not in item or 'musinsa.com' not in item['url']:
                self.log_to_queue("무신사 URL이 아닙니다")
                return None
            
            url = item['url']
            self.log_to_queue(f"무신사 상품 처리 시작: {url}")
            
            # 최대혜택가 추출
            max_benefit_price = self.wrapper.extract_musinsa_max_benefit_price(url)
            
            if max_benefit_price:
                self.log_to_queue(f"최대혜택가 추출 성공: {max_benefit_price:,}원")
                # 아이템 정보 업데이트
                item['adjusted_price'] = max_benefit_price
                item['price_source'] = 'musinsa_max_benefit'
                return item
            else:
                self.log_to_queue("최대혜택가 추출 실패")
                return None
                
        except Exception as e:
            self.log_to_queue(f"무신사 상품 처리 중 오류: {e}")
            return None


# 재시도 데코레이터 구현
def retry_on_page_load_failure(max_retries=3, base_wait=2):
    """
    페이지 로딩 실패 시 자동으로 재시도하는 데코레이터
    
    Args:
        max_retries: 최대 재시도 횟수 (기본: 3)
        base_wait: 기본 대기 시간 (기본: 2초, 재시도마다 증가)
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    # 함수 실행
                    return func(self, *args, **kwargs)
                    
                except TimeoutException as e:
                    last_exception = e
                    
                    # 마지막 시도가 아닌 경우 재시도
                    if attempt < max_retries:
                        wait_time = base_wait * (attempt + 1)  # 점진적 대기 시간 증가
                        self.log_to_queue(f"[RETRY] TimeoutException 발생 - {attempt + 1}/{max_retries} 재시도")
                        self.log_to_queue(f"[RETRY] {wait_time}초 대기 후 페이지 새로고침...")
                        
                        try:
                            # 페이지 새로고침
                            self.driver.refresh()
                            time.sleep(wait_time)
                            self.log_to_queue("[RETRY] 페이지 새로고침 완료")
                        except Exception as refresh_error:
                            self.log_to_queue(f"[ERROR] 페이지 새로고침 실패: {type(refresh_error).__name__}")
                    else:
                        # 모든 재시도 실패 시 홈으로 이동
                        self.log_to_queue(f"[ERROR] {max_retries}회 재시도 후에도 실패 - 홈으로 이동")
                        try:
                            self.driver.get("https://seller.poizon.com/main/dataBoard")
                            time.sleep(3)
                            self.log_to_queue("[INFO] 홈 페이지로 이동 완료")
                        except Exception as home_error:
                            self.log_to_queue(f"[ERROR] 홈 이동 실패: {type(home_error).__name__}")
                        
                        # 원래 예외 다시 발생
                        raise last_exception
                        
                except Exception as e:
                    # TimeoutException이 아닌 다른 예외는 그대로 전달
                    raise e
                    
            # 모든 재시도 실패
            if last_exception:
                raise last_exception
                
        return wrapper
    return decorator


# PoizonAutoBidderWorker 클래스 (모듈 레벨로 이동)
class PoizonAutoBidderWorker:
    """워커용 PoizonAutoBidder 클래스"""
    def __init__(self, worker_id, result_queue, status_dict):
        self.worker_id = worker_id
        self.result_queue = result_queue
        self.status_dict = status_dict
        self.driver = None
        self.wait = None
        self.min_profit = 0
        self.discount_rate = 0
        
    def log_to_queue(self, message):
        """큐를 통한 로그 전송"""
        self.result_queue.put(("LOG", f"[Worker {self.worker_id}] {message}"))
        
    # -- 로그 기록
    def log_fail(self, idx, brand, code, color, size, price, reason):
        log_entry = f"{idx},{brand},{code},{color},{size},{price},{reason}"
        self.result_queue.put(("FAIL_LOG", log_entry))
        self.log_to_queue(f"[FAIL] {log_entry}")

    # -- 할인율 적용 메소드
    def apply_custom_discount(self, original_price):
        """사용자 지정 할인율을 적용하여 목표 입찰가 계산"""
        if self.discount_rate > 0:
            target_price = original_price * (1 - self.discount_rate / 100)
            self.log_to_queue(f"[DISCOUNT] 원가: {original_price:,}원, 할인율: {self.discount_rate}%, 목표가: {int(target_price):,}원")
            return int(target_price)
        else:
            return original_price

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
            self.log_to_queue(f"[DEBUG] 변휈 결과: {code}")
            
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

    def check_page_health(self):
        """
        페이지가 정상적으로 로드되었는지 확인
        
        Returns:
            bool: 페이지가 완전히 로드되고 정상 상태면 True, 그렇지 않으면 False
        """
        try:
            # 1. document.readyState 확인
            ready_state = self.driver.execute_script("return document.readyState")
            if ready_state != "complete":
                self.log_to_queue(f"[WARN] 페이지 로딩 미완료: readyState={ready_state}")
                return False
            
            # 2. 주요 요소 존재 여부 확인 (JavaScript로 빠르게 체크)
            elements_check = self.driver.execute_script("""
                // 검색창 확인
                var searchBox = document.getElementById('Item Info');
                if (!searchBox) {
                    return {success: false, missing: 'search_box'};
                }
                
                // Create listings 버튼 확인
                var createBtn = document.querySelector("button[class*='ant-btn']");
                if (!createBtn) {
                    // 버튼이 없어도 검색창이 있으면 기본 페이지는 로드된 것
                    return {success: true, warning: 'no_create_button'};
                }
                
                // 테이블 존재 여부 확인 (선택적)
                var table = document.querySelector("tbody.ant-table-tbody");
                
                return {
                    success: true,
                    searchBox: searchBox ? true : false,
                    createBtn: createBtn ? true : false,
                    table: table ? true : false
                };
            """)
            
            if not elements_check['success']:
                self.log_to_queue(f"[WARN] 필수 요소 누락: {elements_check.get('missing', 'unknown')}")
                return False
            
            # 3. 페이지 에러 메시지 확인
            error_check = self.driver.execute_script("""
                // 에러 메시지나 알림 확인
                var errorElements = document.querySelectorAll('.ant-message-error, .ant-alert-error');
                if (errorElements.length > 0) {
                    return {hasError: true, count: errorElements.length};
                }
                
                // 로딩 스피너가 여전히 돌고 있는지 확인
                var spinners = document.querySelectorAll('.ant-spin-spinning');
                if (spinners.length > 0) {
                    return {loading: true, count: spinners.length};
                }
                
                return {hasError: false, loading: false};
            """)
            
            if error_check.get('hasError'):
                self.log_to_queue(f"[WARN] 페이지에 에러 메시지 발견: {error_check['count']}개")
                return False
                
            if error_check.get('loading'):
                self.log_to_queue(f"[WARN] 페이지 로딩 중: 스피너 {error_check['count']}개")
                return False
            
            # 모든 체크 통과
            self.log_to_queue("[OK] 페이지 상태 정상")
            return True
            
        except Exception as e:
            self.log_to_queue(f"[ERROR] 페이지 상태 체크 실패: {type(e).__name__} - {str(e)}")
            return False

    def wait_for_search_results(self):
        """
        검색 결과가 완전히 로드될 때까지 대기
        로딩 스피너가 사라지고 검색 결과가 나타날 때까지 대기
        """
        try:
            self.log_to_queue("[WAIT] 검색 결과 로딩 대기 중...")
            
            # 1. 로딩 스피너가 나타났다가 사라질 때까지 대기
            try:
                # 먼저 로딩 스피너가 있는지 확인 (짧은 대기)
                spinner_present = self.driver.execute_script("""
                    return document.querySelectorAll('.ant-spin-spinning, .ant-spin-container').length > 0;
                """)
                
                if spinner_present:
                    self.log_to_queue("[WAIT] 로딩 스피너 감지 - 사라질 때까지 대기")
                    # 스피너가 사라질 때까지 대기 (최대 10초)
                    WebDriverWait(self.driver, 10).until_not(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".ant-spin-spinning, .ant-spin-container"))
                    )
                    self.log_to_queue("[OK] 로딩 스피너 사라짐")
            except TimeoutException:
                self.log_to_queue("[WARN] 로딩 스피너 대기 시간 초과")
            
            # 2. 검색 결과 테이블이 나타날 때까지 대기
            try:
                # 검색 결과 컨테이너 대기
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "tbody.ant-table-tbody"))
                )
                
                # 검색 결과 행이 있는지 확인
                rows_count = self.driver.execute_script("""
                    var rows = document.querySelectorAll('tbody.ant-table-tbody tr');
                    return rows.length;
                """)
                
                if rows_count > 0:
                    self.log_to_queue(f"[OK] 검색 결과 로드 완료: {rows_count}개 항목")
                else:
                    self.log_to_queue("[INFO] 검색 결과 없음")
                    
            except TimeoutException:
                self.log_to_queue("[WARN] 검색 결과 테이블 대기 시간 초과")
            
            # 3. JavaScript 렌더링 완료를 위한 추가 대기
            self.log_to_queue("[WAIT] JavaScript 렌더링 완료 대기 (2초)")
            time.sleep(2)
            
            # 4. 최종 페이지 상태 확인
            final_check = self.driver.execute_script("""
                return {
                    hasSpinner: document.querySelectorAll('.ant-spin-spinning').length > 0,
                    hasTable: document.querySelector('tbody.ant-table-tbody') !== null,
                    hasError: document.querySelectorAll('.ant-message-error, .ant-alert-error').length > 0
                };
            """)
            
            if final_check['hasSpinner']:
                self.log_to_queue("[WARN] 아직 로딩 중인 요소가 있습니다")
            
            if final_check['hasError']:
                self.log_to_queue("[WARN] 검색 중 에러 메시지 발견")
                
            if final_check['hasTable']:
                self.log_to_queue("[OK] 검색 결과 대기 완료")
                return True
            else:
                self.log_to_queue("[WARN] 검색 결과 테이블을 찾을 수 없음")
                return False
                
        except Exception as e:
            self.log_to_queue(f"[ERROR] 검색 결과 대기 중 오류: {type(e).__name__} - {str(e)}")
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
                    
                    # 숫자 사이즈와 텍스트 사이즈(S, M, L, XL 등) 모두 처리
                    if kr_size and (kr_size.replace('.', '').isdigit() or 
                                  kr_size.upper() in ['XS', 'S', 'M', 'L', 'XL', 'XXL', 'XXXL', '2XL', '3XL', '4XL', '5XL'] or
                                  any(char.isalpha() for char in kr_size)):  # 문자가 포함된 경우도 처리
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
                                elif header == 'Foot Length Fit' or header == 'CM':
                                    size_mapping[kr_size]['CM'] = cell_text
                
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

    @retry_on_page_load_failure()
    def create_listings(self):
        self.log_to_queue("[STEP] Create listings")
        
        # 페이지 상태 체크
        if not self.check_page_health():
            self.log_to_queue("[WARN] 페이지 상태 불안정 - TimeoutException 발생")
            raise TimeoutException("페이지가 정상적으로 로드되지 않았습니다")
        
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
            # TimeoutException은 그대로 발생시켜 재시도 데코레이터가 처리하도록 함
            raise TimeoutException("Create listings 버튼을 찾을 수 없습니다")

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
                
                # CM 탭 먼저 확인
                try:
                    cm_tab = self.driver.find_element(
                        By.XPATH, 
                        "//div[@class='tabItem___vEvcb' and text()='CM']"
                    )
                    cm_tab.click()
                    active_tab = 'CM'
                    self.log_to_queue("[OK] CM 탭 사용 결정")
                except:
                    # CM 탭이 없으면 EU 탭으로 시도
                    self.log_to_queue("[INFO] CM 탭 없음 - EU 탭으로 시도")
                    try:
                        eu_tab = self.driver.find_element(
                            By.XPATH, 
                            "//div[@class='tabItem___vEvcb' and text()='EU']"
                        )
                        eu_tab.click()
                        active_tab = 'EU'
                        self.log_to_queue("[OK] EU 탭 사용 결정 - Size Chart 기반 CM 변환 예정")
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
            elif size.upper() in ['XS', 'S', 'M', 'L', 'XL', 'XXL', 'XXXL', '2XL', '3XL', '4XL', '5XL']:
                # 텍스트 사이즈는 그대로 사용
                target_size = size.upper()
                self.log_to_queue(f"[DEBUG] 텍스트 사이즈 감지: {target_size}")
                
                # Size Chart가 있고 텍스트 사이즈가 매핑되어 있으면 변환 시도
                if 'size_chart' in locals() and size_chart and size.upper() in size_chart:
                    if active_tab in size_chart[size.upper()]:
                        converted_size = size_chart[size.upper()][active_tab]
                        if converted_size and converted_size != '-':
                            self.log_to_queue(f"[DEBUG] Size Chart 기반 텍스트 사이즈 변환: {size} → {active_tab}: {converted_size}")
                            target_size = converted_size
            elif 'size_chart' in locals() and size_chart and size in size_chart:
                # Size Chart가 있을 때 변환 처리
                if active_tab == 'EU' and 'CM' in size_chart[size]:
                    # EU 탭에서 CM 변환이 필요한 경우
                    cm_value = size_chart[size].get('CM', '')
                    if cm_value and cm_value != '-':
                        self.log_to_queue(f"[INFO] EU→CM 변환: {size} → EU {size_chart[size].get('EU', size)} → CM {cm_value}")
                        # EU 사이즈를 사용하되, CM 값도 참고
                        target_size = size_chart[size].get('EU', size)
                        # CM 정보를 로그에 기록
                        self.log_to_queue(f"[DEBUG] 참고: 해당 사이즈의 CM 값은 {cm_value}입니다")
                    else:
                        target_size = size_chart[size].get(active_tab, size)
                        self.log_to_queue(f"[DEBUG] Size Chart 기반 사이즈: {size} → {active_tab}: {target_size}")
                elif active_tab in size_chart[size]:
                    target_size = size_chart[size][active_tab]
                    if target_size and target_size != '-':
                        self.log_to_queue(f"[DEBUG] Size Chart 기반 사이즈: {size} → {active_tab}: {target_size}")
                    else:
                        target_size = size
                        self.log_to_queue(f"[DEBUG] Size Chart에 정보 없음 - 원본 사용: {target_size}")
                else:
                    target_size = size
                    self.log_to_queue(f"[DEBUG] Size Chart에 {active_tab} 정보 없음 - 원본 사용: {target_size}")
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
                    var activeTab = arguments[3];  // 현재 활성 탭 추가
                    
                    console.log('[DEBUG] 찾는 사이즈: ' + targetSize);
                    console.log('[DEBUG] 현재 탭: ' + activeTab);
                    console.log('[DEBUG] 사용 가능한 아이템 수: ' + items.length);
                    
                    // 처음 5개 아이템 텍스트 표시
                    for (var j = 0; j < Math.min(5, items.length); j++) {
                        console.log('[DEBUG] 아이템 ' + j + ': ' + items[j].textContent.trim());
                    }
                    
                    // 텍스트 사이즈인지 확인
                    var isTextSize = ['XS', 'S', 'M', 'L', 'XL', 'XXL', 'XXXL', '2XL', '3XL', '4XL', '5XL'].indexOf(targetSize.toUpperCase()) !== -1;
                    
                    for (var i = 0; i < items.length; i++) {
                        var item = items[i];
                        var text = item.textContent.trim();
                        
                        // 이미 선택된 항목 스킵
                        if (item.classList.contains('selected')) continue;
                        
                        if (isTextSize) {
                            // 텍스트 사이즈 매칭 (대소문자 무시)
                            var upperText = text.toUpperCase();
                            var upperTarget = targetSize.toUpperCase();
                            
                            // 정확히 일치하거나 포함하는 경우
                            if (upperText === upperTarget || 
                                upperText.indexOf(' ' + upperTarget + ' ') !== -1 ||
                                upperText.indexOf(' ' + upperTarget) !== -1 ||
                                upperText.indexOf(upperTarget + ' ') !== -1) {
                                console.log('[DEBUG] 텍스트 사이즈 매칭 성공: ' + text);
                                
                                // 색상 체크 (필요한 경우만)
                                if (needColorMatch && targetColor) {
                                    if (!text.includes(targetColor)) {
                                        console.log('[DEBUG] 색상 불일치: ' + text + ' (필요 색상: ' + targetColor + ')');
                                        continue;
                                    }
                                }
                                console.log('[DEBUG] 최종 매칭 성공: ' + text);
                                return item;
                            }
                        } else {
                            // 숫자 사이즈 매칭 (기존 로직)
                            var pattern1 = ' ' + targetSize + ' ';  // 공백으로 둘러싸인 사이즈
                            var pattern2 = ' ' + targetSize;        // 뒤에만 공백
                            var pattern3 = targetSize + ' ';        // 앞에만 공백
                            
                            // JP 탭 특수 처리 추가
                            if (activeTab === 'JP') {
                                var jpPattern = 'JP ' + targetSize;  // 'JP 22.5' 형식
                                if (text.indexOf(jpPattern) !== -1) {
                                    console.log('[DEBUG] JP 패턴 매칭 성공: ' + text);
                                    // 색상 체크 (필요한 경우만)
                                    if (needColorMatch && targetColor) {
                                        if (!text.includes(targetColor)) {
                                            console.log('[DEBUG] 색상 불일치: ' + text + ' (필요 색상: ' + targetColor + ')');
                                            continue;
                                        }
                                    }
                                    console.log('[DEBUG] JP 패턴 최종 매칭 성공: ' + text);
                                    return item;
                                }
                            }
                            
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
                    }
                    return null;
                """, target_size, target_color, len(available['colors']) > 1, active_tab)
                
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
                            var activeTab = arguments[3];
                            
                            console.log('[DEBUG] 재시도 - 찾는 사이즈: ' + targetSize);
                            console.log('[DEBUG] 재시도 - 현재 탭: ' + activeTab);
                            
                            for (var i = 0; i < items.length; i++) {
                                var item = items[i];
                                var text = item.textContent.trim();
                                
                                if (item.classList.contains('selected')) continue;
                                
                                var pattern1 = ' ' + targetSize + ' ';
                                var pattern2 = ' ' + targetSize;
                                var pattern3 = targetSize + ' ';
                                
                                // JP 탭 특수 처리 추가 (재시도에서도)
                                if (activeTab === 'JP') {
                                    var jpPattern = 'JP ' + targetSize;
                                    if (text.indexOf(jpPattern) !== -1) {
                                        console.log('[DEBUG] 재시도 JP 패턴 매칭 성공: ' + text);
                                        if (needColorMatch && targetColor) {
                                            if (!text.includes(targetColor)) {
                                                console.log('[DEBUG] 재시도 색상 불일치: ' + text);
                                                continue;
                                            }
                                        }
                                        console.log('[DEBUG] 재시도 JP 패턴 최종 매칭 성공: ' + text);
                                        return item;
                                    }
                                }
                                
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
                        """, target_size_converted, target_color, len(available['colors']) > 1, active_tab)
                        
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
                    self.log_to_queue(f"\n[FAIL] {active_tab} 탭에서 {size} 찾기 실패")
                    
                    # 상세 디버그 정보 출력
                    self.log_to_queue(f"[DEBUG] ===== 매칭 실패 상세 정보 =====")
                    self.log_to_queue(f"[DEBUG] 브랜드: {brand}")
                    self.log_to_queue(f"[DEBUG] 원본 사이즈: {size}")
                    self.log_to_queue(f"[DEBUG] 타겟 사이즈: {target_size}")
                    
                    # 시도한 패턴들 기록
                    tried_patterns = [
                        f"' {target_size} ' (공백으로 둘러싸인)",
                        f"' {target_size}' (뒤에만 공백)",
                        f"'{target_size} ' (앞에만 공백)",
                        f"'{target_size}' (정확히 일치)"
                    ]
                    
                    # JP 탭인 경우 JP 패턴도 추가
                    if active_tab == 'JP':
                        tried_patterns.append(f"'JP {target_size}' (JP 특수 패턴)")
                        # 변환된 사이즈도 시도했다면 추가
                        if 'target_size_converted' in locals() and target_size != target_size_original:
                            tried_patterns.append(f"'{target_size_original}' (원본 사이즈)")
                            tried_patterns.append(f"'JP {target_size_original}' (JP 원본 패턴)")
                    
                    self.log_to_queue(f"[DEBUG] 시도한 패턴들:")
                    for pattern in tried_patterns:
                        self.log_to_queue(f"  - {pattern}")
                    
                    # 사용 가능한 사이즈 10개 표시
                    self.log_to_queue(f"\n[DEBUG] 사용 가능한 사이즈 (최대 10개):")
                    available_sizes = []
                    for i, item in enumerate(all_items[:10]):
                        item_text = item.text.strip()
                        self.log_to_queue(f"  {i+1}. {item_text}")
                        available_sizes.append(item_text)
                    
                    # 비슷한 사이즈 찾기 (디버깅용)
                    similar_items = []
                    for item in all_items[:20]:  # 처음 20개만 확인
                        item_text = item.text.strip()
                        # 타겟 사이즈나 원본 사이즈가 포함된 경우
                        if target_size in item_text or size in item_text:
                            similar_items.append(item_text)
                        # 4자리 사이즈의 경우 두 버전 모두 확인
                        elif len(size) == 4 and size.isdigit():
                            if size[:3] in item_text:  # 2552 -> 255
                                similar_items.append(item_text)
                    
                    if similar_items:
                        self.log_to_queue(f"\n[DEBUG] 비슷한 사이즈 포함 아이템:")
                        for item in similar_items[:5]:
                            self.log_to_queue(f"  - {item}")
                    
                    self.log_to_queue(f"[DEBUG] ==============================\n")
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
        import time as timer  # 시간 측정을 위한 import
        process_start_time = timer.time()
        
        self.log_to_queue("\n" + "="*60)
        self.log_to_queue(f"[STEP] 입찰 처리 시작 - 코드: {code}, 브랜드: {brand}")
        self.log_to_queue(f"[INFO] 처리할 사이즈: {len(matched)}개")
        self.log_to_queue("="*60)
        
        successful = []
        all_failed = True  # 모든 입찰이 실패했는지 추적
        asia_check_stats = {"success": 0, "failed": 0, "removed": 0}  # 통계 정보
        
        for match_info in matched:
            idx, brand_name, code, color, size, cost, matched_text = match_info
            item_start_time = timer.time()
            
            self.log_to_queue(f"\n[PROCESS] {matched_text} 입찰 시작 ({len(successful)+1}/{len(matched)})")
            self.log_to_queue(f"[DEBUG] 상세정보 - IDX: {idx}, 색상: {color}, 사이즈: {size}, 기준가: {cost:,}")
            
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
                    
                    # Asia 체크가 안 되어 있으면 무조건 다운 버튼 클릭 시도
                    self.log_to_queue(f"[INFO] Asia 체크 안 됨 - 다운 버튼 클릭 시도")
                    
                    # Asia 체크를 위한 다운 버튼 클릭 루프 (최대 10회)
                    max_asia_attempts = 10
                    asia_attempt = 0
                    
                    while asia_attempt < max_asia_attempts:
                        asia_attempt += 1
                        self.log_to_queue(f"[ATTEMPT] Asia 체크 시도 {asia_attempt}/{max_asia_attempts}")
                        
                        # 다운 버튼 클릭 시도
                        if not self.click_down_button(row):
                            self.log_to_queue(f"[WARN] 다운 버튼 비활성화 - Asia 체크 불가")
                            self.log_fail(idx, brand_name, code, color, size, cost, 'Asia체크불가-다운버튼비활성')
                            self.click_remove(row)
                            break
                        
                        # 다운 버튼 클릭 후 대기
                        time.sleep(0.5)
                        
                        # Asia 체크 상태 재확인
                        asia_checked = self.is_asia_checked(row)
                        
                        if asia_checked:
                            self.log_to_queue(f"[SUCCESS] Asia 체크 성공! (시도: {asia_attempt}회)")
                            asia_check_stats["success"] += 1
                            
                            # === Asia 체크 성공 - 이제 입찰 가능 상태 ===
                            # 예상수익 재계산 (가격 변경 후)
                            est_payout = self.find_est_payout(row)
                            profit = est_payout - cost
                            
                            # 수익 조건 검증 (Asia 체크가 확인된 후에만 수행)
                            self.log_to_queue(f"[VERIFY] 예상수익: {est_payout:,}, 기준가: {cost:,}, 수익: {profit:,}")
                            
                            if est_payout >= cost:  # 기본 조건: 예상수익 ≥ 기준가
                                if profit >= self.min_profit:  # 추가 조건: 수익 ≥ 최소수익
                                    # === 모든 조건 충족 - 입찰 진행 ===
                                    self.log_to_queue(f"[OK] ✓ 입찰조건 충족: {matched_text} (수익: {profit}원)")
                                    successful.append(match_info)  # 성공 목록에 추가
                                    bid_success = True
                                    all_failed = False
                                else:
                                    # 최소수익 미달
                                    self.log_to_queue(f"[INFO] ✗ 최소수익 미달 ({profit:,} < {self.min_profit:,}) - Remove")
                                    self.log_fail(idx, brand_name, code, color, size, cost, f'Asia체크후최소수익미달')
                                    self.click_remove(row)
                                    asia_check_stats["removed"] += 1
                            else:
                                # 예상수익 < 기준가
                                self.log_to_queue(f"[INFO] ✗ 예상수익 부족 ({est_payout:,} < {cost:,}) - Remove")
                                self.log_fail(idx, brand_name, code, color, size, cost, f'Asia체크후예상수익부족')
                                self.click_remove(row)
                                asia_check_stats["removed"] += 1
                            break  # Asia 체크 루프 종료
                        
                        # 현재 가격 확인 (디버깅)
                        try:
                            current_price_input = row.find_element(
                                By.CSS_SELECTOR, 
                                "td.inputNumberV2___dIR0i input[value]"
                            )
                            new_price = self.get_int(current_price_input.get_attribute("value"))
                            self.log_to_queue(f"[DEBUG] 가격 변화: {current_price} → {new_price}")
                            current_price = new_price
                        except:
                            pass
                    
                    # 최대 시도 횟수 초과
                    if asia_attempt >= max_asia_attempts and not asia_checked:
                        self.log_to_queue(f"[FAIL] ✗ Asia 체크 실패 - 최대 시도 횟수 초과")
                        self.log_fail(idx, brand_name, code, color, size, cost, 'Asia체크실패-최대시도초과')
                        self.click_remove(row)
                        asia_check_stats["failed"] += 1
                    
                    # 개별 아이템 처리 시간
                    item_elapsed = timer.time() - item_start_time
                    self.log_to_queue(f"[TIME] {matched_text} 처리 시간: {item_elapsed:.1f}초")
                    
                    break  # while 루프 종료
                        
                except StaleElementReferenceException:
                    retry_count += 1
                    self.log_to_queue(f"[RETRY] DOM 변경 감지, 재시도 {retry_count}/{MAX_RETRIES}")
                    self.log_to_queue(f"[DEBUG] 상태: Row 요소가 업데이트됨 - 재탐색 필요")
                    time.sleep(1)
                except NoSuchElementException:
                    self.log_to_queue(f"[ERROR] ✗ {matched_text} row를 찾을 수 없음")
                    self.log_to_queue(f"[DEBUG] XPath: //tr[.//div[contains(text(),'{matched_text}')]]")
                    self.log_fail(idx, brand_name, code, color, size, cost, "row 못찾음")
                    asia_check_stats["failed"] += 1
                    break
                except Exception as e:
                    self.log_to_queue(f"[ERROR] ✗ 예상치 못한 오류: {type(e).__name__}")
                    self.log_to_queue(f"[DEBUG] 오류 상세: {str(e)}")
                    self.log_to_queue(f"[DEBUG] 마지막 단계: {asia_attempt if 'asia_attempt' in locals() else 'N/A'}")
                    asia_check_stats["failed"] += 1
                    break
        
        # 모든 입찰이 실패한 경우 뒤로 가기
        if all_failed and len(matched) > 0:
            self.log_to_queue("\n[WARN] 모든 사이즈 입찰 실패 - 가격 조정 불가")
            self.go_back_and_reset()
            return []  # 빈 리스트 반환하여 Confirm 단계 스킵
        
        # 프로세스 완료 요약
        process_elapsed = timer.time() - process_start_time
        self.log_to_queue("\n" + "="*60)
        self.log_to_queue(f"[SUMMARY] 입찰 처리 완료 - 코드: {code}")
        self.log_to_queue(f"[RESULT] 성공: {len(successful)}/{len(matched)} 개")
        self.log_to_queue(f"[STATS] Asia 체크 - 성공: {asia_check_stats['success']}, 실패: {asia_check_stats['failed']}, Remove: {asia_check_stats['removed']}")
        self.log_to_queue(f"[TIME] 전체 처리 시간: {process_elapsed:.1f}초 (평균: {process_elapsed/len(matched) if matched else 0:.1f}초/개)")
        self.log_to_queue("="*60 + "\n")
                    
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


class PoizonBidderWrapperV2:
    """포이즌 입찰 래퍼 V2 - 원본 파일의 실제 로직 활용
    
    주요 기능:
    - 포이즌 자동 입찰 시스템 통합
    - ABC마트 상품 링크 추출 (페이지네이션 지원)
    - 상품 수 급감 시 자동 크롤링 종료 기능
    """
    
    # ABC마트 크롤러 설정
    MIN_PAGES_FOR_THRESHOLD = 3  # 임계값 적용을 위한 최소 페이지 수
    PRODUCT_DROP_THRESHOLD = 0.2  # 상품 수 급감 판단 임계값 (20%)
    
    def __init__(self, driver_path: str = None, min_profit: int = 0, worker_count: int = 5):
        """
        초기화
        
        Args:
            driver_path: Chrome 드라이버 경로 (None이면 자동 탐색)
            min_profit: 최소 예상 수익
            worker_count: 동시 실행 워커 수
        """
        self.driver_path = driver_path or self._find_chromedriver()
        self.min_profit = min_profit
        self.worker_count = worker_count
        self.module = None
        self.musinsa_login_mgr = None  # 무신사 로그인 매니저
        
        # 원본 모듈 로드
        self._load_original_module()
        
        logger.info(f"PoizonBidderWrapperV2 초기화 - 최소수익: {min_profit}, 워커수: {worker_count}")
    
    def _find_chromedriver(self) -> str:
        """Chrome 드라이버 자동 탐색 및 다운로드"""
        # 일반적인 위치들
        possible_paths = [
            "chromedriver.exe",
            "C:/chromedriver/chromedriver.exe",
            "C:/poison_final/chromedriver.exe",
            str(Path.home() / "Downloads" / "chromedriver.exe"),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                logger.info(f"Chrome 드라이버 발견: {path}")
                return path
        
        # ChromeDriver를 찾지 못한 경우 자동 다운로드
        logger.warning("ChromeDriver를 찾을 수 없습니다. 자동 다운로드를 시작합니다...")
        
        try:
            import subprocess
            download_script = Path("C:/poison_final/download_chromedriver.py")
            
            if download_script.exists():
                logger.info("download_chromedriver.py 스크립트 실행 중...")
                result = subprocess.run(
                    [sys.executable, str(download_script)],
                    capture_output=True,
                    text=True,
                    encoding='utf-8'
                )
                
                if result.returncode == 0:
                    logger.info("ChromeDriver 다운로드 성공!")
                    # 다운로드 후 다시 경로 확인
                    chromedriver_path = "C:/poison_final/chromedriver.exe"
                    if os.path.exists(chromedriver_path):
                        logger.info(f"ChromeDriver 경로: {chromedriver_path}")
                        return chromedriver_path
                else:
                    logger.error(f"ChromeDriver 다운로드 실패: {result.stderr}")
            else:
                logger.error(f"download_chromedriver.py 스크립트를 찾을 수 없습니다: {download_script}")
                
        except Exception as e:
            logger.error(f"ChromeDriver 자동 다운로드 중 오류: {e}")
        
        # 여전히 못 찾으면 기본값 반환
        logger.error("ChromeDriver를 찾을 수 없고 다운로드도 실패했습니다. 기본 경로 반환.")
        return "chromedriver.exe"
    
    def _load_original_module(self):
        """원본 모듈 동적 로드"""
        try:
            original_file = Path('C:/poison_final/0923_fixed_multiprocess_cookie_v2.py')
            if not original_file.exists():
                raise FileNotFoundError(f"원본 파일을 찾을 수 없습니다: {original_file}")
            
            # 모듈 동적 로드
            spec = importlib.util.spec_from_file_location("multiprocess_cookie", original_file)
            self.module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self.module)
            
            logger.info("원본 모듈 로드 성공")
            
        except Exception as e:
            logger.error(f"원본 모듈 로드 실패: {e}")
            raise
    
    def ensure_musinsa_login(self):
        """무신사 로그인 확인 및 실행"""
        try:
            # 환경변수 확인
            if not MUSINSA_ID or not MUSINSA_PASSWORD:
                logger.error("무신사 로그인 정보가 환경변수에 설정되지 않았습니다.")
                logger.error("MUSINSA_ID와 MUSINSA_PASSWORD를 .env 파일에 설정해주세요.")
                return False
            
            # 로그인 매니저 초기화
            if not self.musinsa_login_mgr:
                logger.info("무신사 로그인 매니저 초기화")
                self.musinsa_login_mgr = LoginManager('musinsa')
            
            # 자동 로그인 시도
            logger.info("무신사 자동 로그인 시도")
            if self.musinsa_login_mgr.auto_login(MUSINSA_ID, MUSINSA_PASSWORD):
                logger.info("무신사 자동 로그인 성공")
                # 쿠키 저장
                self.musinsa_login_mgr.save_cookies()
                
                # 팝업 처리 추가
                logger.info("무신사 팝업 처리 시도")
                try:
                    # enhanced_close_musinsa_popup 함수 사용
                    popup_result = enhanced_close_musinsa_popup(self.musinsa_login_mgr.driver, worker_id=None)
                    if popup_result:
                        logger.info("무신사 팝업 처리 성공")
                    else:
                        logger.warning("무신사 팝업이 없거나 처리하지 못했습니다")
                except Exception as e:
                    logger.warning(f"무신사 팝업 처리 중 오류 (무시하고 계속): {e}")
                
                return True
            else:
                logger.warning("무신사 자동 로그인 실패 - 수동 로그인 필요")
                # 수동 로그인 시도
                if self.musinsa_login_mgr.manual_login():
                    logger.info("무신사 수동 로그인 성공")
                    # 쿠키 저장
                    self.musinsa_login_mgr.save_cookies()
                    
                    # 팝업 처리 추가
                    logger.info("무신사 팝업 처리 시도")
                    try:
                        # enhanced_close_musinsa_popup 함수 사용
                        popup_result = enhanced_close_musinsa_popup(self.musinsa_login_mgr.driver, worker_id=None)
                        if popup_result:
                            logger.info("무신사 팝업 처리 성공")
                        else:
                            logger.warning("무신사 팝업이 없거나 처리하지 못했습니다")
                    except Exception as e:
                        logger.warning(f"무신사 팝업 처리 중 오류 (무시하고 계속): {e}")
                    
                    return True
                else:
                    logger.error("무신사 수동 로그인 실패")
                    return False
        except Exception as e:
            logger.error(f"무신사 로그인 중 오류 발생: {e}")
            return False
    
    def get_musinsa_cookies(self):
        """무신사 쿠키 반환"""
        try:
            if self.musinsa_login_mgr:
                return self.musinsa_login_mgr.cookies
            else:
                logger.warning("무신사 로그인 매니저가 초기화되지 않았습니다.")
                return None
        except Exception as e:
            logger.error(f"무신사 쿠키 반환 중 오류: {e}")
            return None
    
    def extract_musinsa_max_benefit_price(self, url):
        """무신사 상품 페이지에서 최대혜택가 추출"""
        driver = None
        try:
            logger.info(f"무신사 최대혜택가 추출 시작: {url}")
            
            # 로그인 상태 확인 및 로그인
            if not self.ensure_musinsa_login():
                logger.error("무신사 로그인 실패")
                return None
            
            # Chrome 드라이버 설정
            chrome_options = webdriver.ChromeOptions()
            chrome_options.add_argument('--start-maximized')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--log-level=3')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
            
            # 이미지 차단으로 속도 최적화
            chrome_options.add_experimental_option("prefs", {
                "profile.default_content_setting_values": {
                    "images": 2,  # 이미지 차단
                    "plugins": 2,  # 플러그인 차단
                    "popups": 2,  # 팝업 차단
                }
            })
            
            # 드라이버 생성
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
            except:
                driver = webdriver.Chrome(service=Service(self.driver_path), options=chrome_options)
            
            wait = WebDriverWait(driver, 10)
            
            # 쿠키 로드
            cookies = self.get_musinsa_cookies()
            if cookies:
                driver.get("https://www.musinsa.com")
                time.sleep(1)
                for cookie in cookies:
                    try:
                        driver.add_cookie(cookie)
                    except:
                        pass
                driver.refresh()
                time.sleep(1)
                logger.info("무신사 쿠키 로드 완료")
            
            # 상품 페이지 접속
            driver.get(url)
            
            # 팝업 처리 - enhanced_close_musinsa_popup 함수 사용
            time.sleep(2)  # 팝업이 나타날 시간을 줌
            try:
                popup_handled = enhanced_close_musinsa_popup(driver, worker_id=None)
                if popup_handled:
                    logger.info("무신사 팝업 처리 성공")
                else:
                    logger.info("무신사 팝업이 없거나 처리하지 못했습니다")
            except Exception as e:
                logger.warning(f"무신사 팝업 처리 중 예외 (무시하고 계속): {e}")
            
            # 페이지 로드 대기
            try:
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.sc-x9uktx-0.WoXHk")))
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "span.text-red.text-title_18px_semi")))
            except TimeoutException:
                logger.warning("최대혜택가 영역 로드 타임아웃")
            
            # 로그인 체크
            if "login" in driver.current_url.lower():
                logger.error("로그인 페이지로 리다이렉트됨")
                return None
            
            # 가격 추출
            price_text = None
            
            # 방법 1: JavaScript로 직접 추출
            try:
                price_text = driver.execute_script("""
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
                    logger.info(f"JavaScript로 가격 추출: {price_text}")
            except Exception as e:
                logger.warning(f"JavaScript 실행 실패: {e}")
            
            # 방법 2: XPath로 추출
            if not price_text:
                try:
                    max_benefit_section = wait.until(
                        EC.presence_of_element_located((By.XPATH, "//div[@class='sc-x9uktx-0 WoXHk']"))
                    )
                    price_elem = max_benefit_section.find_element(
                        By.XPATH, 
                        ".//span[contains(@class, 'text-red') and contains(@class, 'text-title_18px_semi') and contains(text(), '원') and not(contains(text(), '%'))]"
                    )
                    
                    WebDriverWait(driver, 10).until(
                        lambda d: price_elem.text.strip() != "" and "원" in price_elem.text
                    )
                    
                    price_text = price_elem.text.strip()
                    logger.info(f"XPath로 가격 추출: {price_text}")
                except Exception as e:
                    logger.warning(f"XPath 추출 실패: {e}")
            
            # 가격 텍스트 처리
            if price_text:
                # 가격에서 숫자만 추출
                current_price = int(re.sub(r'[^\d]', '', price_text))
                
                # 적립금 선할인 체크
                try:
                    buttons = driver.find_elements(By.CSS_SELECTOR, "button.sc-qexya5-0")
                    pre_discount_amount = 0
                    
                    for button in buttons:
                        try:
                            button_text = button.text
                            if "적립금 선할인" in button_text:
                                parent_div = button.find_element(By.XPATH, "./ancestor::div[contains(@class, 'flex-row')]")
                                if parent_div:
                                    checkbox_svg = parent_div.find_element(By.CSS_SELECTOR, "svg")
                                    if checkbox_svg and checkbox_svg.get_attribute("data-icon") == "square-check":
                                        logger.info("적립금 선할인이 체크되어 있음")
                                        
                                        # 버튼 클릭해서 상세 정보 보기
                                        button.click()
                                        time.sleep(0.5)
                                        
                                        # 적립금 금액 찾기
                                        amount_elems = driver.find_elements(By.XPATH, "//span[contains(text(), '적용 적립금')]/following-sibling::span")
                                        for elem in amount_elems:
                                            text = elem.text.strip()
                                            if "원" in text:
                                                amount = int(re.sub(r'[^\d]', '', text))
                                                if amount > 0:
                                                    pre_discount_amount = amount
                                                    logger.info(f"적립금 선할인 금액: {amount}원")
                                                    break
                                        
                                        # 자세히 닫기
                                        try:
                                            close_button = driver.find_element(
                                                By.XPATH,
                                                "//div[@data-button-name='혜택확인닫기']//span[text()='닫기']/.."
                                            )
                                            driver.execute_script("arguments[0].click();", close_button)
                                        except:
                                            pass
                                        
                                        break
                        except:
                            continue
                    
                    # 적립금 선할인이 적용된 경우, 원래 가격으로 복원
                    if pre_discount_amount > 0:
                        original_price = current_price + pre_discount_amount
                        logger.info(f"최대혜택가: {current_price}원 + 선할인 {pre_discount_amount}원 = {original_price}원")
                        return original_price
                        
                except Exception as e:
                    logger.warning(f"적립금 선할인 확인 실패: {e}")
                
                logger.info(f"최대혜택가: {current_price}원")
                return current_price
                
            else:
                logger.warning("최대혜택가 텍스트를 찾을 수 없음")
                
                # 대안: 정가 추출 시도
                try:
                    price_elem = driver.find_element(By.XPATH, "//span[contains(@class, 'text-title_18px_semi') and contains(text(), '원')]")
                    current_price_text = price_elem.text.strip()
                    current_price = int(re.sub(r'[^\d]', '', current_price_text))
                    logger.info(f"정가: {current_price}원")
                    return current_price
                except:
                    logger.error("가격을 찾을 수 없습니다")
                    return None
                    
        except Exception as e:
            logger.error(f"무신사 가격 추출 중 오류 발생: {e}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            if driver:
                driver.quit()
                logger.info("드라이버 종료")
    
    def prepare_bid_data(self, items: List[Dict[str, Any]]) -> List[Tuple]:
        """
        통합 시스템의 데이터를 포이즌 입찰 형식으로 변환
        
        Args:
            items: unified_bidding이나 auto_bidding에서 온 아이템 리스트
            
        Returns:
            포이즌 입찰 형식의 튜플 리스트
        """
        # 파라미터 타입 검증
        if not isinstance(items, list):
            error_msg = f"TypeError: items는 list 타입이어야 합니다. 받은 타입: {type(items).__name__}"
            logger.error(error_msg)
            raise TypeError(error_msg)
        
        if not items:
            logger.warning("prepare_bid_data: 빈 리스트가 전달되었습니다.")
            return []
        
        bid_data = []
        
        logger.info(f"데이터 변환 시작: {len(items)}개 아이템")
        if items and logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"첫 번째 아이템 샘플: {json.dumps(items[0], ensure_ascii=False)}")
        
        # 필수 필드 정의
        required_fields = ['brand', 'code', 'size']
        fields_missing_count = 0
        
        for idx, item in enumerate(items, 1):
            # 아이템 타입 검증
            if not isinstance(item, dict):
                logger.warning(f"아이템 {idx}가 dict 타입이 아닙니다: {type(item).__name__}. 건너뜁니다.")
                continue
            
            # 데이터 추출
            brand = item.get('brand', '')
            code = item.get('code', '')
            color = item.get('color', '')
            size = item.get('size', '')
            price = item.get('adjusted_price', item.get('price', 0))
            
            # 필수 필드 검증
            missing_fields = []
            for field in required_fields:
                if not item.get(field):
                    missing_fields.append(field)
            
            if missing_fields:
                fields_missing_count += 1
                logger.warning(f"아이템 {idx}(코드: {code or 'N/A'})에 필수 필드 누락: {missing_fields}")
                if fields_missing_count <= 5:  # 처음 5개만 상세 로깅
                    logger.debug(f"누락된 필드가 있는 아이템: {item}")
            
            # price 검증
            if price <= 0:
                logger.warning(f"아이템 {idx}(코드: {code})의 가격이 유효하지 않습니다: {price}")
            
            # 포이즌 형식으로 변환
            bid_data.append((
                idx,
                brand,
                code,
                color,
                size,
                price
            ))
            
        # 변환 결과 로깅
        logger.info(f"데이터 변환 완료: {len(bid_data)}개 아이템으로 변환")
        if fields_missing_count > 0:
            logger.warning(f"필수 필드 누락된 아이템 수: {fields_missing_count}개")
        
        if bid_data and logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"변환된 첫 번째 튜플: {bid_data[0]}")
            logger.debug(f"데이터 변환 상세 - 입력: {len(items)}개, 출력: {len(bid_data)}개, 누락: {fields_missing_count}개")
        return bid_data
    
    def run_bidding(self, bid_data_file: Optional[str] = None, 
                   bid_data_list: Optional[List[Tuple]] = None,
                   unified_items: Optional[List[Dict[str, Any]]] = None,
                   discount_rate: float = 0) -> Dict[str, Any]:
        """
        입찰 실행
        
        Args:
            bid_data_file: 입찰 데이터 파일 경로
            bid_data_list: 입찰 데이터 리스트 [(idx, brand, code, color, size, cost), ...]
            unified_items: unified_bidding/auto_bidding에서 온 아이템 리스트
            
        Returns:
            입찰 결과 딕셔너리
        """
        start_time = datetime.now()
        logger.info("=== 포이즌 입찰 시작 ===")
        
        # 파라미터 타입 및 입력 확인
        logger.info(f"입력 파라미터 - bid_data_file: {bid_data_file is not None}, "
                   f"bid_data_list: {bid_data_list is not None}, "
                   f"unified_items: {unified_items is not None}")
        
        # unified_items 타입 검증
        if unified_items is not None:
            logger.info(f"unified_items 타입: {type(unified_items)}")
            
            # bool 타입 검증 (True/False)
            if isinstance(unified_items, bool):
                error_msg = f"TypeError: unified_items는 bool 타입이 아니어야 합니다. 받은 값: {unified_items}"
                logger.error(error_msg)
                raise TypeError(error_msg)
            
            # list 타입 검증
            if not isinstance(unified_items, list):
                error_msg = f"TypeError: unified_items는 list 타입이어야 합니다. 받은 타입: {type(unified_items).__name__}"
                logger.error(error_msg)
                logger.error(f"unified_items 샘플: {str(unified_items)[:100]}...")  # 처음 100자만
                raise TypeError(error_msg)
            
            logger.info(f"unified_items 항목 수: {len(unified_items)}")
            
            # 빈 리스트 경고
            if len(unified_items) == 0:
                logger.warning("unified_items가 비어있습니다. 입찰할 항목이 없습니다.")
        
        # 데이터 준비
        if unified_items:
            # 통합 시스템 데이터를 변환
            logger.info(f"unified_items로부터 데이터 변환 시작: {len(unified_items)}개")
            raw_data = self.prepare_bid_data(unified_items)
        elif bid_data_file:
            # 파일에서 로드 (원본 함수 사용)
            bidder = self.module.PoizonAutoBidderMultiProcess()
            raw_data = bidder.load_bid_data(bid_data_file)
        elif bid_data_list:
            raw_data = bid_data_list
        else:
            raise ValueError("bid_data_file, bid_data_list, unified_items 중 하나는 제공되어야 합니다")
        
        if not raw_data:
            return {
                'status': 'error',
                'message': '입력 데이터가 없습니다',
                'timestamp': datetime.now().isoformat()
            }
        
        # 원본의 실행 로직을 활용하되 GUI 부분만 우회
        try:
            # 로그 파일 초기화
            if os.path.exists(LOGFILE):
                os.remove(LOGFILE)
            
            # 코드별 그룹화
            groups = defaultdict(list)
            for rec in raw_data:
                code = rec[2]  # 상품코드는 인덱스 2
                groups[code].append(rec)
            logger.info(f"그룹화 완료: {len(groups)}개 코드")
            
            # Manager 생성
            manager = Manager()
            task_queue = manager.Queue()
            result_queue = manager.Queue()
            status_dict = manager.dict()
            login_complete = manager.Value('b', False)
            
            # 통계 정보
            stats = manager.dict()
            stats['total'] = len(groups)
            stats['completed'] = 0
            stats['success'] = 0
            stats['failed'] = 0
            
            # 작업 큐에 추가
            for code, entries in groups.items():
                task_queue.put((code, entries))
            
            # 종료 신호 추가
            for _ in range(self.worker_count):
                task_queue.put(None)
            
            logger.info(f"{self.worker_count}개의 워커 프로세스로 작업 시작")
            
            # 결과 수집을 위한 큐 추가
            result_list_queue = manager.Queue()
            
            # 로그 수집 프로세스 (모듈 레벨 함수 사용)
            log_proc = Process(target=log_processor_worker, args=(result_queue, result_list_queue))
            log_proc.daemon = True
            log_proc.start()
            
            # 무신사 쿠키 가져오기
            musinsa_cookies = None
            try:
                # unified_items에 무신사 상품이 있는지 확인
                has_musinsa_items = False
                if bid_data:
                    # 무신사 관련 상품이 있는지 확인 (브랜드나 특정 패턴으로)
                    for item in bid_data:
                        if len(item) > 1 and item[1]:  # 브랜드가 있는 경우
                            # 무신사 특정 브랜드 또는 패턴 확인
                            # 일단 모든 상품에 대해 무신사 쿠키 준비
                            has_musinsa_items = True
                            break
                
                if has_musinsa_items:
                    logger.info("무신사 상품 감지 - 무신사 로그인 확인")
                    if self.ensure_musinsa_login():
                        musinsa_cookies = self.get_musinsa_cookies()
                        if musinsa_cookies:
                            logger.info("무신사 쿠키 준비 완료")
                        else:
                            logger.warning("무신사 쿠키를 가져올 수 없습니다")
                    else:
                        logger.warning("무신사 로그인 실패")
            except Exception as e:
                logger.error(f"무신사 쿠키 준비 중 오류: {e}")
            
            # 워커 프로세스들 시작 (worker_process_wrapper 사용)
            workers = []
            for i in range(1, self.worker_count + 1):
                worker = Process(
                    target=worker_process_wrapper,
                    args=(i, task_queue, result_queue, status_dict, login_complete, 
                          self.min_profit, self.driver_path, stats, musinsa_cookies, discount_rate)
                )
                workers.append(worker)
                worker.start()
                
                # 첫 번째 워커 시작 후 대기
                if i == 1:
                    logger.info("첫 번째 워커에서 로그인 진행 중...")
                    import time
                    time.sleep(5)
            
            # 모든 워커 종료 대기
            for worker in workers:
                worker.join()
            
            # 로그 수집 종료
            result_queue.put(("TERMINATE", None))
            log_proc.join()
            
            # 결과 수집
            results = []
            fail_logs = []
            while not result_list_queue.empty():
                data_type, data = result_list_queue.get()
                if data_type == 'results':
                    results = data
                elif data_type == 'fail_logs':
                    fail_logs = data
            
            # 실행 시간 계산
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # 실패 로그 저장
            if fail_logs:
                with open(self.module.LOGFILE, 'w', encoding='utf-8') as f:
                    for log in fail_logs:
                        f.write(log + "\n")
                logger.info(f"실패 로그 저장: {self.module.LOGFILE}")
            
            # 최종 결과
            return {
                'status': 'success',
                'total_codes': len(groups),
                'total_items': len(raw_data),
                'completed': stats.get('completed', 0),
                'success': stats.get('success', 0),
                'failed': stats.get('failed', 0),
                'execution_time': execution_time,
                'timestamp': datetime.now().isoformat(),
                'details': results,
                'fail_log_path': self.module.LOGFILE if fail_logs else None
            }
            
        except Exception as e:
            logger.error(f"입찰 실행 중 오류: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            return {
                'status': 'error',
                'message': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def extract_abcmart_links(self, search_keyword: str, max_pages: int = 10) -> List[str]:
        """
        ABC마트에서 검색어로 상품 링크 추출 (페이지네이션 처리)
        
        Args:
            search_keyword: 검색할 키워드 (예: "나이키", "뉴발란스")
            max_pages: 최대 검색할 페이지 수 (기본값: 10)
            
        Returns:
            추출된 상품 링크 리스트
        """
        logger.info(f"ABC마트 링크 추출 시작: 검색어='{search_keyword}', 최대 페이지={max_pages}")
        
        # Selenium 드라이버 설정
        try:
            from selenium import webdriver
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.common.exceptions import TimeoutException, NoSuchElementException
            import urllib.parse
            
            # Chrome 옵션 설정
            chrome_options = webdriver.ChromeOptions()
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # 드라이버 생성
            driver = webdriver.Chrome(
                service=Service(self.driver_path),
                options=chrome_options
            )
            
            wait = WebDriverWait(driver, 10)
            
            # 추출된 링크들을 저장할 세트 (중복 제거)
            all_links = set()
            
            # 페이지별 새로운 링크 수 기록 (크롤링 종료 판단용)
            new_links_history = []
            
            # URL 인코딩된 검색어
            encoded_keyword = urllib.parse.quote(search_keyword)
            
            # 페이지네이션 처리
            for page in range(1, max_pages + 1):
                try:
                    # ABC마트 검색 URL (페이지 포함)
                    search_url = f"https://abcmart.a-rt.com/display/search-word/result?searchWord={encoded_keyword}&page={page}"
                    logger.info(f"페이지 {page} 접속: {search_url}")
                    
                    driver.get(search_url)
                    time.sleep(3)  # 페이지 로드 대기
                    
                    # 상품 링크 추출
                    product_links = []
                    
                    # 여러 선택자로 시도
                    selectors = [
                        'a[href*="product?prdtNo="]',
                        'a[href*="prdtNo="]',
                        '.item-list a[href*="prdtNo"]',
                        '.search-list-wrap a[href*="prdtNo"]',
                        'div.item a[href*="prdtNo"]'
                    ]
                    
                    for selector in selectors:
                        try:
                            elements = driver.find_elements(By.CSS_SELECTOR, selector)
                            for elem in elements:
                                href = elem.get_attribute('href')
                                if href and 'prdtNo=' in href:
                                    # 상품 번호 추출
                                    match = re.search(r'prdtNo=(\d+)', href)
                                    if match:
                                        product_id = match.group(1)
                                        # 표준 형식으로 저장
                                        product_link = f"https://abcmart.a-rt.com/product?prdtNo={product_id}"
                                        product_links.append(product_link)
                        except Exception as e:
                            logger.debug(f"선택자 {selector} 실패: {e}")
                    
                    # 이번 페이지에서 찾은 링크 수
                    page_links = set(product_links)
                    new_links = page_links - all_links
                    all_links.update(page_links)
                    
                    logger.info(f"페이지 {page}: {len(new_links)}개 새 링크 발견 (전체: {len(all_links)}개)")
                    
                    # 페이지별 새 링크 수 기록
                    new_links_history.append(len(new_links))
                    
                    # 상품 수 급감 감지 로직
                    if page >= self.MIN_PAGES_FOR_THRESHOLD and len(new_links_history) >= 3:
                        recent_avg = sum(new_links_history[-3:]) / 3
                        if recent_avg > 0 and len(new_links) < recent_avg * self.PRODUCT_DROP_THRESHOLD:
                            logger.info(f"상품 수 급감 감지: 평균 {recent_avg:.1f}개 → 현재 {len(new_links)}개, 크롤링 종료")
                            break
                    
                    # 상품이 없으면 종료
                    if len(page_links) == 0:
                        logger.info(f"페이지 {page}에 상품이 없습니다. 검색 종료.")
                        break
                    
                    # 다음 페이지가 없는지 확인 (선택사항)
                    try:
                        # 페이지네이션 확인 - 현재 페이지가 마지막인지
                        pagination = driver.find_elements(By.CSS_SELECTOR, '.pagination a, .paging a')
                        if pagination:
                            current_page_elem = driver.find_element(By.CSS_SELECTOR, '.pagination .active, .paging .on')
                            if current_page_elem and current_page_elem.text == str(page):
                                # 다음 페이지 버튼이 비활성화되었는지 확인
                                next_disabled = driver.find_elements(By.CSS_SELECTOR, '.pagination .next.disabled, .paging .next.disabled')
                                if next_disabled:
                                    logger.info("마지막 페이지입니다.")
                                    break
                    except:
                        pass  # 페이지네이션 확인 실패해도 계속 진행
                    
                except TimeoutException:
                    logger.warning(f"페이지 {page} 로드 시간 초과")
                    break
                except Exception as e:
                    logger.error(f"페이지 {page} 처리 중 오류: {e}")
                    break
            
            # 결과 저장 (선택사항)
            if all_links:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_file = f"C:/poison_final/logs/abcmart_links_{search_keyword}_{timestamp}.txt"
                
                try:
                    os.makedirs(os.path.dirname(output_file), exist_ok=True)
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(f"# ABC마트 상품 링크 추출 결과\n")
                        f.write(f"# 검색어: {search_keyword}\n")
                        f.write(f"# 추출 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                        f.write(f"# 총 {len(all_links)}개 상품\n")
                        f.write("=" * 50 + "\n\n")
                        for link in sorted(all_links):
                            f.write(f"{link}\n")
                    
                    logger.info(f"링크 파일 저장 완료: {output_file}")
                except Exception as e:
                    logger.error(f"파일 저장 실패: {e}")
            
        except Exception as e:
            logger.error(f"ABC마트 링크 추출 실패: {e}")
            all_links = set()
        finally:
            if 'driver' in locals():
                driver.quit()
        
        logger.info(f"ABC마트 링크 추출 완료: 총 {len(all_links)}개")
        return list(all_links)


# 테스트용
if __name__ == "__main__":
    # 테스트 데이터
    test_data = [
        (1, "나이키", "ABC123", "BLACK", "270", 50000),
        (2, "나이키", "ABC123", "WHITE", "275", 50000),
        (3, "아디다스", "DEF456", "RED", "280", 60000),
    ]
    
    # Wrapper 인스턴스 생성
    wrapper = PoizonBidderWrapperV2(
        min_profit=5000,
        worker_count=2
    )
    
    # 입찰 실행
    result = wrapper.run_bidding(bid_data_list=test_data)
    
    # 결과 출력
    print("\n=== 입찰 결과 ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))
