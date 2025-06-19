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
        
        # 사이트별 설정
        self.sites_config = {
            "musinsa": {
                "login_url": "https://www.musinsa.com/auth/login",
                "home_url": "https://www.musinsa.com",
                "login_check_selector": "div.mypage-cont",
                "id_field": "searchId",
                "pw_field": "searchPw",
                "login_button": "button.login-button"
            },
            "abcmart": {
                "login_url": "https://abcmart.a-rt.com/login",
                "home_url": "https://abcmart.a-rt.com",
                "login_check_selector": ".member-info",
                "id_field": "loginId",
                "pw_field": "loginPw",
                "login_button": ".login-btn"
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
        
        if headless:
            options.add_argument("--headless")
        
        # 사용자 데이터 디렉터리 설정 (로그인 유지)
        user_data_dir = Path("chrome_data") / self.site
        user_data_dir.mkdir(parents=True, exist_ok=True)
        options.add_argument(f"--user-data-dir={user_data_dir.absolute()}")
        
        self.driver = uc.Chrome(options=options, version_main=None)
        return self.driver
    
    def save_cookies(self):
        """현재 쿠키 저장"""
        if not self.driver:
            logger.error("드라이버가 초기화되지 않았습니다.")
            return False
        
        try:
            cookies = self.driver.get_cookies()
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
            
            # 쿠키 적용
            for cookie in cookies:
                try:
                    self.driver.add_cookie(cookie)
                except Exception as e:
                    logger.warning(f"쿠키 추가 실패: {e}")
            
            # 페이지 새로고침
            self.driver.refresh()
            time.sleep(2)
            
            logger.info("쿠키 로드 완료")
            return True
            
        except Exception as e:
            logger.error(f"쿠키 로드 실패: {e}")
            return False
    
    def is_logged_in(self) -> bool:
        """로그인 상태 확인"""
        if not self.driver:
            return False
        
        try:
            # 마이페이지나 로그인 확인 요소 찾기
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.config['login_check_selector']))
            )
            return True
        except:
            return False
    
    def manual_login(self) -> bool:
        """수동 로그인 (사용자가 직접 로그인)"""
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
                self.save_cookies()
                return True
            else:
                logger.error("자동 로그인 실패")
                return False
                
        except Exception as e:
            logger.error(f"자동 로그인 중 오류: {e}")
            return False
    
    def ensure_login(self) -> bool:
        """로그인 상태 확인 및 필요시 로그인"""
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
