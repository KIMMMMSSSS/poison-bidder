#!/usr/bin/env python3
"""
포이즌 쿠키 로그인
순수 쿠키 방식으로 로그인 유지
"""

import pickle
import time
from pathlib import Path
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By

def setup_poison_cookies():
    """포이즌 쿠키 설정"""
    print("\n" + "="*50)
    print("POIZON 쿠키 로그인 설정")
    print("="*50)
    
    cookies_dir = Path("cookies")
    cookies_dir.mkdir(exist_ok=True)
    cookie_file = cookies_dir / "poison_cookies.pkl"
    
    # Chrome 옵션 (프로필 없이)
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    
    driver = uc.Chrome(options=options, version_main=None)
    
    try:
        # 1. 포이즌 사이트 접속
        print("\n1. seller.poizon.com 접속...")
        driver.get("https://seller.poizon.com")
        time.sleep(3)
        
        # 2. 기존 쿠키 로드 시도
        if cookie_file.exists():
            print("\n2. 기존 쿠키 로드 시도...")
            with open(cookie_file, 'rb') as f:
                cookies = pickle.load(f)
            
            for cookie in cookies:
                try:
                    driver.add_cookie(cookie)
                except:
                    pass
            
            driver.refresh()
            time.sleep(3)
        
        # 3. 로그인 상태 확인
        page_text = driver.find_element(By.TAG_NAME, "body").text
        
        if "Log In" in page_text or "Phone number" in page_text:
            print("\n3. 로그인이 필요합니다.")
            print("\n수동으로 로그인해주세요:")
            print("- 아이디/비밀번호 입력")
            print("- 로그인 버튼 클릭")
            print("- 2차 인증이 있다면 완료")
            
            input("\n로그인 완료 후 Enter를 누르세요...")
            
            # 쿠키 저장
            print("\n4. 쿠키 저장 중...")
            cookies = driver.get_cookies()
            with open(cookie_file, 'wb') as f:
                pickle.dump(cookies, f)
            
            print("✅ 쿠키 저장 완료!")
            
            # 테스트
            print("\n5. 쿠키 테스트...")
            driver.delete_all_cookies()
            driver.get("https://seller.poizon.com")
            time.sleep(2)
            
            # 쿠키 다시 로드
            for cookie in cookies:
                try:
                    driver.add_cookie(cookie)
                except:
                    pass
            
            driver.refresh()
            time.sleep(3)
            
            page_text = driver.find_element(By.TAG_NAME, "body").text
            if "Log In" not in page_text:
                print("✅ 쿠키가 정상 작동합니다!")
            else:
                print("⚠️ 쿠키가 작동하지 않습니다.")
                print("포이즌은 쿠키 외에 추가 인증이 필요할 수 있습니다.")
        else:
            print("\n✅ 이미 로그인되어 있습니다!")
            
            # 쿠키 업데이트
            cookies = driver.get_cookies()
            with open(cookie_file, 'wb') as f:
                pickle.dump(cookies, f)
            print("✅ 쿠키 업데이트 완료!")
        
        input("\n종료하려면 Enter를 누르세요...")
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()


if __name__ == "__main__":
    setup_poison_cookies()
