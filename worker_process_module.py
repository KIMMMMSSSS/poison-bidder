"""
worker_process 함수와 PoizonAutoBidderWorker 클래스를 포함한 모듈
pickle 문제를 해결하기 위해 별도 모듈로 분리
"""

import time
import re
import os
import traceback
from datetime import datetime
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
from .poison_bidder_wrapper_v2 import (
    save_cookies, load_cookies,
    BRAND_SEARCH_RULES, COLOR_MAPPING, COLOR_ABBREVIATIONS,
    MAX_RETRIES, DEFAULT_WAIT_TIME
)


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
            chrome_options.add_argument('--disable-logging')
            chrome_options.add_argument('--log-level=3')
            chrome_options.add_argument('--silent')
            
            # 메모리 최적화 옵션 추가
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
                    "images": 2,
                    "plugins": 2,
                    "popups": 2,
                    "geolocation": 2,
                    "notifications": 2,
                    "media_stream": 2,
                },
                "profile.managed_default_content_settings": {
                    "images": 2
                }
            })
            
            # 추가 experimental 옵션
            chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
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
                            time.sleep(worker_id * 0.3)
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
    
    # 여기에 나머지 메서드들을 추가해야 함...
