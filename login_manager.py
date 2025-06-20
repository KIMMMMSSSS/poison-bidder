#!/usr/bin/env python3
"""
로그인 관리 모듈
브라우저 쿠키를 저장하고 재사용하여 로그인 상태 유지
"""

import os
import json
import pickle
import time
from pathlib import Path
from typing import Dict, Optional
import logging

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    import undetected_chromedriver as uc
except ImportError:
    print("Selenium이 설치되지 않았습니다.")
    print("pip install selenium undetected-chromedriver")
    exit(1)

logger = logging.getLogger(__name__)


class LoginManager:
    """로그인 관리 클래스"""
    
    def __init__(self, site: str = "musinsa"):
        """
        초기화
        
        Args:
            site: 사이트 이름 (musinsa, abcmart)
        """
        self.site = site
        self.cookies_dir = Path("cookies")
        self.cookies_dir.mkdir(exist_ok=True)
        self.cookie_file = self.cookies_dir / f"{site}_cookies.pkl"
        self.driver = None
        self.cookies = None  # 쿠키 저장용 속성 추가
        
        # 사이트별 설정
        self.sites_config = {
            "musinsa": {
                "login_url": "https://www.musinsa.com/auth/login",
                "home_url": "https://www.musinsa.com",
                "login_check_selector": "div.mypage-cont, a.header-member__link",
                "id_selector": "input[placeholder='아이디']",
                "pw_selector": "input[placeholder='비밀번호']", 
                "login_button": "button[type='submit'].login-v2-button__item--black",
                "auto_login_checkbox": "input#login-v2-member__util__login-auto"
            },
            "abcmart": {
                "login_url": "https://abcmart.a-rt.com/login",
                "home_url": "https://abcmart.a-rt.com",
                "login_check_selector": ".member-info",
                "id_field": "loginId",
                "pw_field": "loginPw",
                "login_button": ".login-btn"
            },
            "poison": {
                "login_url": "https://seller.poizon.com",  # 로그인 페이지가 메인 페이지
                "home_url": "https://seller.poizon.com",
                "login_check_selector": ".user-name, .user-info, .avatar, span[class*='user'], div[class*='user']",
                "id_field": "username",
                "pw_field": "password",
                "login_button": "button[type='submit'], .login-btn, .submit-btn"
            }
        }
        
        self.config = self.sites_config.get(site, self.sites_config["musinsa"])
    
    def init_driver(self, headless: bool = False) -> webdriver.Chrome:
        """드라이버 초기화"""
        options = uc.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        
        # Chrome 바이너리 경로 명시적 설정
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        ]
        
        chrome_binary = None
        for path in chrome_paths:
            if os.path.exists(path):
                chrome_binary = path
                break
        
        if chrome_binary:
            options.binary_location = chrome_binary
        
        if headless:
            options.add_argument("--headless")
        
        self.driver = uc.Chrome(options=options, version_main=None)
        return self.driver
    
    def save_cookies(self):
        """현재 쿠키 저장"""
        if not self.driver:
            logger.error("드라이버가 초기화되지 않았습니다.")
            return False
        
        try:
            cookies = self.driver.get_cookies()
            self.cookies = cookies  # 메모리에도 저장
            with open(self.cookie_file, 'wb') as f:
                pickle.dump(cookies, f)
            logger.info(f"쿠키 저장 완료: {self.cookie_file}")
            return True
        except Exception as e:
            logger.error(f"쿠키 저장 실패: {e}")
            return False
    
    def load_cookies(self) -> bool:
        """저장된 쿠키 로드"""
        if not self.cookie_file.exists():
            logger.warning(f"쿠키 파일이 없습니다: {self.cookie_file}")
            return False
        
        if not self.driver:
            logger.error("드라이버가 초기화되지 않았습니다.")
            return False
        
        try:
            # 먼저 사이트에 접속
            self.driver.get(self.config['home_url'])
            time.sleep(2)
            
            # 쿠키 로드
            with open(self.cookie_file, 'rb') as f:
                cookies = pickle.load(f)
            
            self.cookies = cookies  # 메모리에도 저장
            
            # 쿠키 적용
            for cookie in cookies:
                try:
                    self.driver.add_cookie(cookie)
                except Exception as e:
                    logger.warning(f"쿠키 추가 실패: {e}")
            
            # 페이지 새로고침
            self.driver.refresh()
            time.sleep(2)
            
            # 무신사 팝업 처리 추가
            if self.site == "musinsa":
                try:
                    from musinsa_scraper_improved import enhanced_close_musinsa_popup
                    popup_handled = enhanced_close_musinsa_popup(self.driver, worker_id=None)
                    if popup_handled:
                        logger.info("무신사 팝업 처리 성공 (쿠키 로드 후)")
                        time.sleep(1)  # 팝업 처리 후 잠시 대기
                except Exception as e:
                    logger.debug(f"무신사 팝업 처리 시도 중 예외 (무시): {e}")
            
            logger.info("쿠키 로드 완료")
            return True
            
        except Exception as e:
            logger.error(f"쿠키 로드 실패: {e}")
            return False
    
    def is_logged_in(self) -> bool:
        """로그인 상태 확인"""
        # ABC마트는 로그인 불필요
        if self.site == "abcmart":
            return True
        
        if not self.driver:
            return False
        
        try:
            # 무신사는 URL로도 확인
            if self.site == "musinsa":
                current_url = self.driver.current_url
                # 로그인 페이지에 있으면 로그인 안됨
                if "/auth/login" in current_url:
                    return False
                
                # 무신사 팝업 처리 추가
                try:
                    from musinsa_scraper_improved import enhanced_close_musinsa_popup
                    popup_handled = enhanced_close_musinsa_popup(self.driver, worker_id=None)
                    if popup_handled:
                        logger.info("무신사 팝업 처리 성공 (로그인 확인 중)")
                        time.sleep(1)  # 팝업 처리 후 잠시 대기
                except Exception as e:
                    logger.debug(f"무신사 팝업 처리 시도 중 예외 (무시): {e}")
                
                # 마이페이지나 회원 링크 찾기
                try:
                    # 여러 선택자 시도
                    selectors = [
                        "a.header-member__link",  # 헤더의 회원 링크
                        "div.mypage-cont",  # 마이페이지 컨텐츠
                        "span[class*='member']",  # 회원 관련 span
                        "a[href*='/member/']"  # 회원 관련 링크
                    ]
                    
                    for selector in selectors:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements:
                            return True
                    
                    # 페이지 텍스트로도 확인
                    page_text = self.driver.find_element(By.TAG_NAME, "body").text
                    if "로그아웃" in page_text or "마이페이지" in page_text:
                        return True
                        
                except:
                    pass
                
                return False
            
            # 포이즌은 특별 처리 - 로그인 페이지 텍스트로 확인
            elif self.site == "poison":
                time.sleep(2)  # 페이지 로드 대기
                page_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
                
                # 로그인 페이지 키워드가 있으면 로그인 안됨
                login_keywords = ["log in", "login", "phone number", "email address", "password"]
                
                # 로그인된 상태 키워드
                logged_in_keywords = ["dashboard", "seller", "product", "order", "inventory"]
                
                # 로그인 페이지 키워드가 있고, 로그인된 상태 키워드가 없으면 로그인 필요
                has_login_form = any(keyword in page_text for keyword in login_keywords)
                has_dashboard = any(keyword in page_text for keyword in logged_in_keywords)
                
                # 디버깅용 로그
                logger.info(f"포이즌 페이지 텍스트 일부: {page_text[:100]}...")
                logger.info(f"로그인 폼 발견: {has_login_form}, 대시보드 발견: {has_dashboard}")
                
                # 대시보드가 있으면 로그인됨, 로그인 폼만 있으면 로그인 안됨
                return has_dashboard or (not has_login_form)
            
            # 다른 사이트는 기존 방식
            selectors = self.config['login_check_selector'].split(', ')
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.warning(f"로그인 확인 중 오류: {e}")
            return False
    
    def manual_login(self) -> bool:
        """수동 로그인 (사용자가 직접 로그인)"""
        # ABC마트는 로그인 불필요
        if self.site == "abcmart":
            logger.info("ABC마트는 로그인이 필요하지 않습니다")
            return True
        
        if not self.driver:
            self.init_driver(headless=False)
        
        try:
            # 로그인 페이지로 이동
            self.driver.get(self.config['login_url'])
            
            print("\n" + "="*50)
            print(f"[{self.site.upper()}] 수동 로그인 필요")
            print("="*50)
            print("1. 브라우저에서 직접 로그인해주세요.")
            print("2. 로그인 완료 후 Enter를 누르세요.")
            print("="*50)
            
            input("\n로그인 완료 후 Enter를 누르세요...")
            
            # 로그인 확인
            if self.is_logged_in():
                print("✅ 로그인 성공!")
                self.save_cookies()
                return True
            else:
                print("❌ 로그인 실패 또는 확인 불가")
                return False
                
        except Exception as e:
            logger.error(f"수동 로그인 중 오류: {e}")
            return False
    
    def auto_login(self, username: str, password: str) -> bool:
        """자동 로그인 (계정 정보 필요)"""
        if not self.driver:
            self.init_driver(headless=False)
        
        try:
            # 로그인 페이지로 이동
            self.driver.get(self.config['login_url'])
            time.sleep(3)
            
            # 무신사는 CSS 선택자 사용
            if self.site == "musinsa":
                # ID 입력
                id_field = self.driver.find_element(By.CSS_SELECTOR, self.config['id_selector'])
                id_field.clear()
                id_field.send_keys(username)
                time.sleep(0.5)
                
                # 비밀번호 입력
                pw_field = self.driver.find_element(By.CSS_SELECTOR, self.config['pw_selector'])
                pw_field.clear()
                pw_field.send_keys(password)
                time.sleep(0.5)
                
                # 자동 로그인 체크박스 체크
                try:
                    auto_login_checkbox = self.driver.find_element(By.CSS_SELECTOR, self.config['auto_login_checkbox'])
                    if not auto_login_checkbox.is_selected():
                        # 라벨 클릭 (체크박스가 blind 클래스로 숨겨져 있음)
                        label = self.driver.find_element(By.CSS_SELECTOR, "label[for='login-v2-member__util__login-auto']")
                        label.click()
                        logger.info("자동 로그인 체크")
                except:
                    logger.warning("자동 로그인 체크박스를 찾을 수 없습니다")
                
                # 로그인 버튼 클릭
                login_btn = self.driver.find_element(By.CSS_SELECTOR, self.config['login_button'])
                login_btn.click()
            else:
                # 다른 사이트는 기존 방식
                # ID 입력
                id_field = self.driver.find_element(By.NAME, self.config['id_field'])
                id_field.clear()
                id_field.send_keys(username)
                
                # 비밀번호 입력
                pw_field = self.driver.find_element(By.NAME, self.config['pw_field'])
                pw_field.clear()
                pw_field.send_keys(password)
                
                # 로그인 버튼 클릭
                login_btn = self.driver.find_element(By.CSS_SELECTOR, self.config['login_button'])
                login_btn.click()
            
            # 로그인 완료 대기
            time.sleep(5)
            
            # 로그인 확인
            if self.is_logged_in():
                logger.info("자동 로그인 성공")
                
                # 무신사인 경우 팝업 처리
                if self.site == "musinsa":
                    logger.info("무신사 로그인 후 팝업 처리 시작")
                    self.handle_musinsa_popup()
                    # 팝업 처리 실패해도 로그인은 성공으로 처리
                
                self.save_cookies()
                return True
            else:
                logger.error("자동 로그인 실패")
                return False
                
        except Exception as e:
            logger.error(f"자동 로그인 중 오류: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def handle_musinsa_popup(self, timeout: int = 10, max_attempts: int = 3) -> bool:
        """무신사 팝업 처리
        
        Args:
            timeout: 팝업 감지 대기 시간 (초)
            max_attempts: 최대 시도 횟수
            
        Returns:
            bool: 팝업 처리 성공 여부 (팝업이 없는 경우도 True)
        """
        # 무신사가 아니면 바로 성공 반환
        if self.site != "musinsa":
            return True
            
        if not self.driver:
            logger.error("드라이버가 초기화되지 않았습니다.")
            return False
            
        logger.info("무신사 팝업 확인 중...")
        
        for attempt in range(max_attempts):
            try:
                # JavaScript로 팝업 감지 및 처리
                popup_handled = self.driver.execute_script("""
                    // 입장하기 버튼 처리
                    var enterBtns = document.querySelectorAll('[data-button-name="입장하기"]');
                    if (enterBtns.length > 0) {
                        console.log('입장하기 버튼 발견');
                        enterBtns[0].click();
                        return 'enter_clicked';
                    }
                    
                    // 오늘 그만 보기 버튼 처리
                    var dismissBtns = document.querySelectorAll('[data-button-name="오늘 그만 보기"]');
                    if (dismissBtns.length > 0) {
                        console.log('오늘 그만 보기 버튼 발견');
                        dismissBtns[0].click();
                        return 'dismiss_clicked';
                    }
                    
                    // 기타 팝업 닫기 버튼 처리
                    var closeBtns = document.querySelectorAll('.popup-close, .modal-close, button[class*="close"], [aria-label="close"]');
                    for (var i = 0; i < closeBtns.length; i++) {
                        var btn = closeBtns[i];
                        // 보이는 버튼만 클릭
                        if (btn.offsetParent !== null && btn.offsetWidth > 0 && btn.offsetHeight > 0) {
                            console.log('팝업 닫기 버튼 발견');
                            btn.click();
                            return 'close_clicked';
                        }
                    }
                    
                    // 팝업이 없음
                    return null;
                """)
                
                if popup_handled:
                    logger.info(f"팝업 처리 성공: {popup_handled} (시도 {attempt+1}/{max_attempts})")
                    time.sleep(0.5)  # DOM 업데이트 대기
                    # 추가 팝업이 있을 수 있으므로 계속 진행
                    continue
                else:
                    # 더 이상 팝업이 없음
                    logger.info("팝업이 없거나 모두 처리됨")
                    return True
                    
            except Exception as e:
                logger.warning(f"팝업 처리 시도 {attempt+1}/{max_attempts} 실패: {e}")
                time.sleep(1)
        
        # 모든 시도 후에도 팝업이 있으면 실패로 처리하지 않고 True 반환
        # (팝업이 있어도 계속 진행 가능)
        logger.info(f"팝업 처리 완료 (총 {max_attempts}회 시도)")
        return True
    
    def ensure_login(self) -> bool:
        """로그인 상태 확인 및 필요시 로그인"""
        # ABC마트는 로그인 불필요
        if self.site == "abcmart":
            logger.info("ABC마트는 로그인 불필요")
            if not self.driver:
                self.init_driver()
            return True
        
        if not self.driver:
            self.init_driver()
        
        # 1. 저장된 쿠키로 시도
        if self.load_cookies() and self.is_logged_in():
            logger.info("쿠키로 로그인 성공")
            return True
        
        # 2. 수동 로그인 필요
        logger.info("로그인이 필요합니다.")
        return self.manual_login()
    
    def close(self):
        """드라이버 종료"""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def quit(self):
        """드라이버 종료 (close와 동일)"""
        self.close()


# 사용 예시
if __name__ == "__main__":
    # 무신사 로그인 테스트
    login_mgr = LoginManager("musinsa")
    
    if login_mgr.ensure_login():
        print("로그인 완료! 이제 작업을 시작할 수 있습니다.")
        
        # 여기서 원하는 작업 수행
        # 예: 상품 페이지로 이동
        login_mgr.driver.get("https://www.musinsa.com/app/goods/1234567")
        time.sleep(3)
        
        # 작업 완료 후 종료
        login_mgr.close()
    else:
        print("로그인 실패")
