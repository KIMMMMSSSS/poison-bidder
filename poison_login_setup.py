#!/usr/bin/env python3
"""
포이즌 로그인 유지 설정
Chrome 프로필을 사용해서 로그인 상태 유지
"""

import time
from pathlib import Path
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import pickle
import os

def setup_poison_login():
    """포이즌 로그인 설정"""
    print("\n" + "="*50)
    print("POIZON 로그인 유지 설정")
    print("="*50)
    
    # Chrome 프로필 경로 설정
    profile_dir = Path("chrome_profiles/poison")
    profile_dir.mkdir(parents=True, exist_ok=True)
    
    # Chrome 옵션
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    
    # 중요: 프로필 디렉토리 설정
    options.add_argument(f"--user-data-dir={profile_dir.absolute()}")
    options.add_argument("--profile-directory=Default")
    
    print(f"Chrome 프로필 경로: {profile_dir.absolute()}")
    
    driver = uc.Chrome(options=options, version_main=None)
    
    try:
        print("\n1. seller.poizon.com 접속...")
        driver.get("https://seller.poizon.com")
        time.sleep(3)
        
        # 로그인 필요 여부 확인
        print("\n2. 로그인 상태 확인...")
        
        # 페이지 텍스트로 로그인 여부 확인
        page_text = driver.find_element(By.TAG_NAME, "body").text
        
        if "Log In" in page_text or "Phone number" in page_text:
            print("\n📌 로그인이 필요합니다.")
            print("\n다음 단계를 따라주세요:")
            print("1. 브라우저에서 아이디/비밀번호 입력")
            print("2. 로그인 버튼 클릭")
            print("3. 2단계 인증이 있다면 완료")
            print("4. 완전히 로그인될 때까지 대기")
            print("5. 'Remember me' 또는 '로그인 유지' 옵션이 있다면 체크")
            
            input("\n로그인 완료 후 Enter를 누르세요...")
            
            # 로그인 후 URL 확인
            time.sleep(2)
            current_url = driver.current_url
            page_text = driver.find_element(By.TAG_NAME, "body").text
            
            if "Log In" not in page_text:
                print(f"\n✅ 로그인 성공!")
                print(f"현재 URL: {current_url}")
                
                # 쿠키도 저장
                cookies_dir = Path("cookies")
                cookies_dir.mkdir(exist_ok=True)
                cookies = driver.get_cookies()
                with open(cookies_dir / "poison_cookies.pkl", 'wb') as f:
                    pickle.dump(cookies, f)
                print("✅ 쿠키도 저장했습니다.")
            else:
                print("\n❌ 아직 로그인되지 않았습니다.")
                return False
        else:
            print("\n✅ 이미 로그인되어 있습니다!")
            print("Chrome 프로필에 로그인이 저장되어 있습니다.")
        
        # 로그인 유지 테스트
        print("\n3. 로그인 유지 테스트...")
        print("브라우저를 닫고 다시 열어도 로그인이 유지되는지 확인합니다.")
        
        driver.quit()
        time.sleep(2)
        
        # 다시 열기
        print("\n4. 브라우저 재시작...")
        driver = uc.Chrome(options=options, version_main=None)
        driver.get("https://seller.poizon.com")
        time.sleep(3)
        
        page_text = driver.find_element(By.TAG_NAME, "body").text
        if "Log In" not in page_text:
            print("\n✅ 완벽! 로그인이 유지됩니다.")
            print("이제 자동 입찰 시스템을 사용할 수 있습니다.")
            return True
        else:
            print("\n⚠️ 로그인이 유지되지 않습니다.")
            print("브라우저 설정이나 사이트 정책 때문일 수 있습니다.")
            return False
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if driver:
            driver.quit()


def check_poison_login():
    """로그인 상태만 빠르게 확인"""
    profile_dir = Path("chrome_profiles/poison")
    
    if not profile_dir.exists():
        print("❌ Chrome 프로필이 없습니다. setup_poison_login()을 먼저 실행하세요.")
        return False
    
    options = uc.ChromeOptions()
    options.add_argument("--headless")  # 백그라운드 실행
    options.add_argument(f"--user-data-dir={profile_dir.absolute()}")
    options.add_argument("--profile-directory=Default")
    
    driver = uc.Chrome(options=options, version_main=None)
    
    try:
        driver.get("https://seller.poizon.com")
        time.sleep(3)
        
        page_text = driver.find_element(By.TAG_NAME, "body").text
        return "Log In" not in page_text
        
    except:
        return False
    finally:
        driver.quit()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        # 빠른 확인 모드
        if check_poison_login():
            print("✅ 포이즌 로그인 상태: OK")
        else:
            print("❌ 포이즌 로그인 필요")
    else:
        # 설정 모드
        setup_poison_login()
