#!/usr/bin/env python3
"""
포이즌 자동 로그인 매니저
계정 정보를 저장하고 자동으로 로그인
"""

import time
import json
import pickle
import getpass
from pathlib import Path
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import logging

# 로그 설정
log_dir = Path('C:/poison_final/logs')
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'poison_auto_login.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class PoisonAutoLogin:
    """포이즌 자동 로그인 클래스"""
    
    def __init__(self, profile_name="default"):
        self.profile_name = profile_name
        self.data_dir = Path("C:/poison_final/poison_data")
        self.data_dir.mkdir(exist_ok=True)
        
        self.profile_dir = self.data_dir / f"profile_{profile_name}"
        self.profile_dir.mkdir(exist_ok=True)
        
        self.cookies_file = self.profile_dir / "cookies.pkl"
        self.credentials_file = self.profile_dir / "credentials.json"
        
        self.driver = None
    
    def save_credentials(self, country_code, phone, password):
        """계정 정보 저장 (보안 주의!)"""
        credentials = {
            'country_code': country_code,
            'phone': phone,
            'password': password
        }
        
        # 실제 운영에서는 암호화 필요!
        with open(self.credentials_file, 'w') as f:
            json.dump(credentials, f)
        
        logger.info(f"계정 정보 저장됨: {self.profile_name}")
    
    def load_credentials(self):
        """저장된 계정 정보 로드"""
        if not self.credentials_file.exists():
            return None
        
        with open(self.credentials_file, 'r') as f:
            return json.load(f)
    
    def init_driver(self):
        """드라이버 초기화"""
        options = uc.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        
        # 프로필 디렉토리 사용 (쿠키 유지)
        options.add_argument(f"--user-data-dir={self.profile_dir}/chrome_profile")
        
        self.driver = uc.Chrome(options=options, version_main=None)
        logger.info("크롬 드라이버 초기화 완료")
    
    def auto_login(self):
        """자동 로그인 수행"""
        if self.driver is None:
            self.init_driver()
        
        try:
            # 포이즌 접속
            logger.info("포이즌 seller 페이지 접속...")
            self.driver.get("https://seller.poizon.com")
            time.sleep(3)
            
            # 이미 로그인되어 있는지 확인
            page_text = self.driver.find_element(By.TAG_NAME, "body").text
            if "Log In" not in page_text:
                logger.info("이미 로그인되어 있습니다.")
                return True
            
            # 저장된 계정 정보 로드
            creds = self.load_credentials()
            if not creds:
                logger.warning("저장된 계정 정보가 없습니다.")
                return self.manual_login()
            
            logger.info("자동 로그인 시작...")
            wait = WebDriverWait(self.driver, 10)
            
            # 1. 국가 코드 선택 (South Korea +82)
            country_select = wait.until(
                EC.element_to_be_clickable((By.ID, "mobile_code"))
            )
            country_select.click()
            time.sleep(1)
            
            # South Korea 옵션 찾아서 클릭
            korea_option = self.driver.find_element(
                By.XPATH, "//div[contains(@title, 'South Korea +82')]"
            )
            korea_option.click()
            time.sleep(0.5)
            
            # 2. 전화번호 입력
            phone_input = wait.until(
                EC.presence_of_element_located((By.ID, "mobile_number"))
            )
            phone_input.clear()
            phone_input.send_keys(creds['phone'])
            time.sleep(0.5)
            
            # 3. 비밀번호 입력
            password_input = self.driver.find_element(By.ID, "password")
            password_input.clear()
            password_input.send_keys(creds['password'])
            time.sleep(0.5)
            
            # 4. 로그인 버튼 클릭
            login_button = self.driver.find_element(
                By.XPATH, "//button[span[text()='Log In']]"
            )
            login_button.click()
            
            # 로그인 완료 대기
            time.sleep(5)
            
            # 로그인 성공 확인
            page_text = self.driver.find_element(By.TAG_NAME, "body").text
            if "Log In" in page_text:
                logger.error("자동 로그인 실패")
                return self.manual_login()
            
            # 쿠키 저장
            self.save_cookies()
            logger.info("✅ 자동 로그인 성공!")
            return True
            
        except Exception as e:
            logger.error(f"자동 로그인 중 오류: {e}")
            return self.manual_login()
    
    def manual_login(self):
        """수동 로그인"""
        logger.info("수동 로그인이 필요합니다.")
        logger.info("브라우저에서 로그인해주세요.")
        
        # 로그인 대기
        input("\n로그인 완료 후 Enter를 누르세요...")
        
        # 쿠키 저장
        self.save_cookies()
        
        # 계정 정보 저장 여부 확인
        save_creds = input("\n계정 정보를 저장하시겠습니까? (y/n): ")
        if save_creds.lower() == 'y':
            phone = input("전화번호 (0 제외): ")
            password = getpass.getpass("비밀번호: ")
            self.save_credentials("82", phone, password)
        
        logger.info("✅ 수동 로그인 완료!")
        return True
    
    def save_cookies(self):
        """쿠키 저장"""
        cookies = self.driver.get_cookies()
        with open(self.cookies_file, 'wb') as f:
            pickle.dump(cookies, f)
        logger.info("쿠키 저장 완료")
    
    def load_cookies(self):
        """쿠키 로드"""
        if not self.cookies_file.exists():
            return False
        
        try:
            with open(self.cookies_file, 'rb') as f:
                cookies = pickle.load(f)
            
            for cookie in cookies:
                self.driver.add_cookie(cookie)
            
            logger.info("쿠키 로드 완료")
            return True
        except Exception as e:
            logger.error(f"쿠키 로드 실패: {e}")
            return False
    
    def get_driver(self):
        """로그인된 드라이버 반환"""
        if self.driver is None:
            self.init_driver()
            self.auto_login()
        return self.driver
    
    def close(self):
        """드라이버 종료"""
        if self.driver:
            self.driver.quit()
            self.driver = None


# 사용 예시
if __name__ == "__main__":
    # 프로필 이름으로 구분 (여러 계정 관리 가능)
    poison = PoisonAutoLogin("account1")
    
    # 드라이버 가져오기 (자동 로그인됨)
    driver = poison.get_driver()
    
    print("\n✅ 포이즌 로그인 완료!")
    print("브라우저를 열어둡니다. Ctrl+C로 종료하세요.")
    
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        poison.close()
        print("\n종료됨")