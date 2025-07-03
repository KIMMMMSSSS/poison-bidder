#!/usr/bin/env python3
"""
포이즌 로그인 상태 확인
저장된 쿠키로 로그인 유지되는지 테스트
"""

import pickle
import time
from pathlib import Path
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By

def test_poison_login():
    """포이즌 로그인 상태 테스트"""
    print("\n" + "="*50)
    print("POIZON 로그인 상태 확인")
    print("="*50)
    
    cookie_file = Path("cookies/poison_cookies.pkl")
    
    # 쿠키 파일 확인
    if not cookie_file.exists():
        print("❌ 쿠키 파일이 없습니다!")
        print("먼저 python simple_poison_login.py 를 실행하세요.")
        return
    
    # Chrome 옵션
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    
    # 사용자 데이터 디렉터리 (로그인 유지)
    user_data_dir = Path("chrome_data") / "poison"
    if user_data_dir.exists():
        options.add_argument(f"--user-data-dir={user_data_dir.absolute()}")
        print("✓ Chrome 사용자 데이터 사용")
    
    driver = uc.Chrome(options=options, version_main=None)
    
    try:
        print("\n1. seller.poizon.com 접속...")
        driver.get("https://seller.poizon.com")
        time.sleep(3)
        
        # 현재 상태 확인
        current_url = driver.current_url
        print(f"현재 URL: {current_url}")
        
        # 로그인 폼이 있는지 확인
        login_forms = driver.find_elements(By.CSS_SELECTOR, "input[type='password'], form[class*='login'], .login-form")
        if login_forms:
            print("\n⚠️ 로그인 페이지가 표시됩니다. 쿠키 로드를 시도합니다...")
            
            # 쿠키 로드
            print("\n2. 저장된 쿠키 로드 중...")
            with open(cookie_file, 'rb') as f:
                cookies = pickle.load(f)
            
            # 쿠키 적용
            for cookie in cookies:
                try:
                    # domain이 맞는지 확인
                    if 'poizon.com' in cookie.get('domain', ''):
                        driver.add_cookie(cookie)
                except Exception as e:
                    print(f"쿠키 추가 실패: {e}")
            
            # 페이지 새로고침
            print("\n3. 페이지 새로고침...")
            driver.refresh()
            time.sleep(3)
            
            # 다시 확인
            current_url = driver.current_url
            print(f"새로고침 후 URL: {current_url}")
            
            login_forms = driver.find_elements(By.CSS_SELECTOR, "input[type='password']")
            if not login_forms:
                print("\n✅ 로그인 성공! 쿠키가 작동합니다.")
            else:
                print("\n❌ 여전히 로그인 페이지입니다.")
                print("쿠키가 만료되었을 수 있습니다. 다시 로그인이 필요합니다.")
        else:
            print("\n✅ 이미 로그인되어 있습니다!")
            print("Chrome 사용자 데이터로 로그인이 유지되고 있습니다.")
        
        # 페이지 소스 일부 확인 (디버깅용)
        print("\n4. 페이지 상태 확인...")
        page_text = driver.find_element(By.TAG_NAME, "body").text[:200]
        print(f"페이지 텍스트 일부: {page_text}...")
        
        input("\n브라우저를 확인하고 Enter를 눌러 종료하세요...")
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()


if __name__ == "__main__":
    test_poison_login()
