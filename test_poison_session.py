#!/usr/bin/env python3
"""
포이즌 세션 유지 테스트
동일 세션에서 작동하는지 확인
"""

import time
from pathlib import Path
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By

class PoisonSession:
    def __init__(self):
        self.driver = None
        
    def login(self):
        """로그인"""
        print("\n" + "="*50)
        print("POIZON 세션 테스트")
        print("="*50)
        
        # Chrome 옵션
        options = uc.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        
        self.driver = uc.Chrome(options=options, version_main=None)
        
        print("\n1. seller.poizon.com 접속...")
        self.driver.get("https://seller.poizon.com")
        time.sleep(3)
        
        print("\n2. 로그인해주세요:")
        input("\n로그인 완료 후 Enter를 누르세요...")
        
        # 로그인 확인
        page_text = self.driver.find_element(By.TAG_NAME, "body").text
        if "Log In" not in page_text:
            print("✅ 로그인 성공!")
            return True
        else:
            print("❌ 로그인 실패!")
            return False
    
    def test_navigation(self):
        """다른 페이지로 이동해도 로그인 유지되는지 테스트"""
        if not self.driver:
            return
        
        print("\n3. 로그인 유지 테스트...")
        
        # 메인 페이지로 다시 이동
        print("- 메인 페이지 재접속...")
        self.driver.get("https://seller.poizon.com")
        time.sleep(2)
        
        page_text = self.driver.find_element(By.TAG_NAME, "body").text
        if "Log In" not in page_text:
            print("✅ 로그인 유지됨!")
        else:
            print("❌ 로그인 풀림!")
            
    def open_new_tab(self):
        """새 탭에서도 로그인 유지되는지 테스트"""
        if not self.driver:
            return
        
        print("\n4. 새 탭 테스트...")
        
        # 새 탭 열기
        self.driver.execute_script("window.open('');")
        self.driver.switch_to.window(self.driver.window_handles[-1])
        
        # 포이즌 접속
        self.driver.get("https://seller.poizon.com")
        time.sleep(2)
        
        page_text = self.driver.find_element(By.TAG_NAME, "body").text
        if "Log In" not in page_text:
            print("✅ 새 탭에서도 로그인 유지!")
        else:
            print("❌ 새 탭에서는 로그인 필요!")
            
        # 원래 탭으로 돌아가기
        self.driver.switch_to.window(self.driver.window_handles[0])
    
    def minimize_and_restore(self):
        """최소화 후 복원 테스트"""
        print("\n5. 브라우저 최소화/복원 테스트...")
        
        # 최소화
        self.driver.minimize_window()
        time.sleep(2)
        
        # 복원
        self.driver.maximize_window()
        time.sleep(1)
        
        # 새로고침
        self.driver.refresh()
        time.sleep(2)
        
        page_text = self.driver.find_element(By.TAG_NAME, "body").text
        if "Log In" not in page_text:
            print("✅ 최소화 후에도 로그인 유지!")
        else:
            print("❌ 로그인 풀림!")
    
    def keep_alive(self):
        """세션 유지를 위한 대기"""
        print("\n6. 세션 유지 모드...")
        print("이 브라우저를 열어두면 로그인이 유지됩니다.")
        print("다른 프로그램에서 이 세션을 사용할 수 있습니다.")
        print("\nCtrl+C로 종료하세요.")
        
        try:
            while True:
                time.sleep(60)
                # 1분마다 페이지 새로고침으로 세션 유지
                self.driver.refresh()
                print(f"세션 유지 중... {time.strftime('%H:%M:%S')}")
        except KeyboardInterrupt:
            print("\n종료합니다.")
    
    def close(self):
        """종료"""
        if self.driver:
            self.driver.quit()


def main():
    session = PoisonSession()
    
    try:
        # 로그인
        if session.login():
            # 각종 테스트
            session.test_navigation()
            session.open_new_tab()
            session.minimize_and_restore()
            
            print("\n" + "="*50)
            print("테스트 결과")
            print("="*50)
            print("포이즌은 동일 브라우저 세션에서만 로그인이 유지됩니다.")
            print("해결 방법:")
            print("1. 입찰 프로그램 실행 시 로그인된 브라우저를 계속 열어둠")
            print("2. 또는 각 브라우저마다 로그인")
            print("="*50)
            
            # 세션 유지 모드
            keep = input("\n세션을 유지하시겠습니까? (y/n): ")
            if keep.lower() == 'y':
                session.keep_alive()
        
    except Exception as e:
        print(f"오류: {e}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
