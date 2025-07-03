#!/usr/bin/env python3
"""
포이즌 로그인 매니저
하나의 브라우저 세션을 유지하면서 사용
"""

import time
from pathlib import Path
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import logging

logger = logging.getLogger(__name__)


class PoisonLoginManager:
    """포이즌 전용 로그인 매니저"""
    
    _instance = None
    _driver = None
    
    def __new__(cls):
        """싱글톤 패턴"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_driver(self):
        """로그인된 드라이버 반환"""
        if self._driver is None:
            self._init_driver()
        return self._driver
    
    def _init_driver(self):
        """드라이버 초기화 및 로그인"""
        print("\n포이즌 로그인 중...")
        
        options = uc.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        # options.add_argument("--headless")  # 필요시 헤드리스 모드
        
        self._driver = uc.Chrome(options=options, version_main=None)
        
        # 포이즌 접속
        self._driver.get("https://seller.poizon.com")
        time.sleep(3)
        
        # 로그인 확인 - 간단한 방법
        page_text = self._driver.find_element(By.TAG_NAME, "body").text
        
        # "Log In" 버튼이 보이면 로그인 필요
        if "Log In" in page_text and "Phone number" in page_text:
            print("\n포이즌 로그인이 필요합니다.")
            print("브라우저에서 로그인해주세요.")
            input("\n로그인 완료 후 Enter를 누르세요...")
            print("✅ 포이즌 로그인 완료!")
        else:
            # 명확하지 않으면 사용자에게 확인
            print("\n현재 페이지를 확인해주세요.")
            confirm = input("로그인이 필요하면 Y, 이미 로그인되어 있으면 N: ")
            if confirm.upper() == 'Y':
                input("\n브라우저에서 로그인 후 Enter를 누르세요...")
            print("✅ 포이즌 로그인 완료!")
    
    def execute_bidding(self, product_url: str, price: int):
        """입찰 실행"""
        if self._driver is None:
            self.get_driver()
        
        try:
            # 상품 페이지로 이동
            self._driver.get(product_url)
            time.sleep(2)
            
            # TODO: 실제 입찰 로직 구현
            # 예: 가격 입력, 입찰 버튼 클릭 등
            
            logger.info(f"입찰 실행: {product_url} - {price}원")
            return True
            
        except Exception as e:
            logger.error(f"입찰 실패: {e}")
            return False
    
    def close(self):
        """드라이버 종료"""
        if self._driver:
            self._driver.quit()
            self._driver = None


# 전역 인스턴스
poison_login = PoisonLoginManager()


# 사용 예시
if __name__ == "__main__":
    # 로그인
    driver = poison_login.get_driver()
    
    # 입찰 테스트
    poison_login.execute_bidding("https://seller.poizon.com/product/123", 50000)
    
    # 종료하지 않고 유지
    print("\n브라우저를 열어둡니다. Ctrl+C로 종료하세요.")
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        poison_login.close()
