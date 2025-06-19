#!/usr/bin/env python3
"""
포이즌 사이트 간단 로그인
쿠키만 저장하는 버전
"""

import pickle
import time
from pathlib import Path
import undetected_chromedriver as uc

def simple_poison_login():
    """간단한 포이즌 로그인"""
    print("\n" + "="*50)
    print("POIZON 간단 로그인")
    print("="*50)
    
    # 쿠키 디렉터리 생성
    cookies_dir = Path("cookies")
    cookies_dir.mkdir(exist_ok=True)
    cookie_file = cookies_dir / "poison_cookies.pkl"
    
    # Chrome 옵션
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    
    # 사용자 데이터 디렉터리 (로그인 유지)
    user_data_dir = Path("chrome_data") / "poison"
    user_data_dir.mkdir(parents=True, exist_ok=True)
    options.add_argument(f"--user-data-dir={user_data_dir.absolute()}")
    
    # 드라이버 시작
    driver = uc.Chrome(options=options, version_main=None)
    
    try:
        # 포이즌 사이트로 이동
        print("\n1. seller.poizon.com으로 이동 중...")
        driver.get("https://seller.poizon.com")
        
        print("\n2. 수동으로 로그인해주세요:")
        print("   - 아이디/비밀번호 입력")
        print("   - 로그인 버튼 클릭")
        print("   - 완전히 로그인될 때까지 대기")
        
        input("\n로그인 완료 후 Enter를 누르세요...")
        
        # 쿠키 저장
        print("\n3. 쿠키 저장 중...")
        cookies = driver.get_cookies()
        with open(cookie_file, 'wb') as f:
            pickle.dump(cookies, f)
        
        print(f"✅ 쿠키 저장 완료: {cookie_file}")
        
        # 테스트
        print("\n4. 페이지 새로고침 후 로그인 유지 테스트...")
        driver.refresh()
        time.sleep(3)
        
        print("\n✅ 로그인 설정 완료!")
        print("이제 자동 입찰을 사용할 수 있습니다.")
        
        input("\n종료하려면 Enter를 누르세요...")
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
    finally:
        driver.quit()


if __name__ == "__main__":
    simple_poison_login()
