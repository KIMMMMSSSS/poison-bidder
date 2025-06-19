#!/usr/bin/env python3
"""
포이즌 직접 로그인
제공된 계정 정보로 바로 로그인
"""

import time
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
        logging.FileHandler(log_dir / 'poison_direct_login.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 계정 정보
PHONE_NUMBER = "1099209275"
PASSWORD = "99006622kK"


def login_to_poison():
    """포이즌 직접 로그인"""
    
    logger.info("포이즌 로그인 시작...")
    
    # Chrome 옵션 설정
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    
    # 프로필 디렉토리 (쿠키 유지)
    profile_dir = Path("C:/poison_final/poison_data/chrome_profile")
    profile_dir.mkdir(parents=True, exist_ok=True)
    options.add_argument(f"--user-data-dir={profile_dir}")
    
    driver = uc.Chrome(options=options, version_main=None)
    
    try:
        # 포이즌 seller 페이지 접속
        logger.info("포이즌 seller 페이지 접속...")
        driver.get("https://seller.poizon.com")
        time.sleep(3)
        
        # 로그인 페이지인지 확인
        page_text = driver.find_element(By.TAG_NAME, "body").text
        if "Log In" not in page_text:
            logger.info("✅ 이미 로그인되어 있습니다!")
            return driver
        
        logger.info("로그인 페이지 감지. 자동 로그인 시작...")
        wait = WebDriverWait(driver, 10)
        
        # 1. 전화번호 입력 (국가 코드 선택 전에)
        logger.info(f"전화번호 입력: {PHONE_NUMBER}")
        phone_input = wait.until(
            EC.presence_of_element_located((By.ID, "mobile_number"))
        )
        phone_input.clear()
        phone_input.send_keys(PHONE_NUMBER)
        time.sleep(1)
        
        # 2. 국가 코드 선택 (South Korea +82)
        logger.info("국가 코드 선택...")
        country_select = wait.until(
            EC.element_to_be_clickable((By.ID, "mobile_code"))
        )
        country_select.click()
        time.sleep(1)
        
        # South Korea 옵션 찾아서 클릭
        korea_option = driver.find_element(
            By.XPATH, "//div[contains(@title, 'South Korea +82')]"
        )
        korea_option.click()
        time.sleep(1)
        
        # 3. 비밀번호 입력
        logger.info("비밀번호 입력...")
        password_input = driver.find_element(By.ID, "password")
        password_input.clear()
        password_input.send_keys(PASSWORD)
        time.sleep(1)
        
        # 4. 로그인 버튼 클릭
        logger.info("로그인 버튼 클릭...")
        login_button = driver.find_element(
            By.XPATH, "//button[span[text()='Log In']]"
        )
        login_button.click()
        
        # 로그인 완료 대기
        logger.info("로그인 처리 중...")
        time.sleep(5)
        
        # 로그인 성공 확인
        page_text = driver.find_element(By.TAG_NAME, "body").text
        if "Log In" in page_text:
            logger.error("⚠️ 자동 로그인 실패. 수동 로그인이 필요합니다.")
            print("\n브라우저에서 직접 로그인해주세요.")
            print(f"전화번호: {PHONE_NUMBER}")
            print(f"비밀번호: {PASSWORD}")
            input("\n로그인 완료 후 Enter를 누르세요...")
        
        logger.info("✅ 포이즌 로그인 성공!")
        return driver
        
    except Exception as e:
        logger.error(f"로그인 중 오류 발생: {e}")
        print("\n오류가 발생했습니다. 수동으로 로그인해주세요.")
        input("로그인 완료 후 Enter를 누르세요...")
        return driver


if __name__ == "__main__":
    # 로그인 실행
    driver = login_to_poison()
    
    print("\n✅ 포이즌 로그인 완료!")
    print("브라우저를 열어둡니다.")
    print("다른 작업을 수행하거나 Ctrl+C로 종료하세요.")
    
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        driver.quit()
        print("\n브라우저 종료됨")
