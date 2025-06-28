"""
ChromeDriver 없이 chrome_driver_manager 작동 테스트
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chrome_driver_manager import initialize_chrome_driver
import time

def test_chrome_driver_manager():
    """chrome_driver_manager가 ChromeDriver 없이도 정상 작동하는지 확인"""
    print("=== ChromeDriver 백업 후 테스트 ===")
    print("1. 프로젝트 루트에 chromedriver.exe 없음")
    print("2. chrome_driver_manager가 자동으로 처리해야 함\n")
    
    try:
        # Chrome 드라이버 초기화
        print("Chrome 드라이버 초기화 중...")
        driver = initialize_chrome_driver(headless=True)
        
        # Google 접속 테스트
        print("Google 접속 테스트...")
        driver.get("https://www.google.com")
        time.sleep(2)
        
        # 타이틀 확인
        title = driver.title
        print(f"페이지 타이틀: {title}")
        
        if "Google" in title:
            print("\n✅ 테스트 성공!")
            print("chrome_driver_manager가 ChromeDriver를 자동으로 관리합니다.")
        else:
            print("\n❌ 테스트 실패: 페이지 타이틀이 예상과 다릅니다.")
            
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
    finally:
        try:
            driver.quit()
            print("\n드라이버 종료 완료")
        except:
            pass

if __name__ == "__main__":
    test_chrome_driver_manager()
