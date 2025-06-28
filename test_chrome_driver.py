#!/usr/bin/env python3
"""
Chrome 드라이버 간단 테스트
"""

import sys
import logging
from chrome_driver_manager import ChromeDriverManager, initialize_chrome_driver

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('C:/poison_final/logs/chrome_test_20250627.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def test_chrome_driver():
    """Chrome 드라이버 테스트"""
    logger.info("=" * 60)
    logger.info("Chrome 드라이버 테스트 시작")
    logger.info("=" * 60)
    
    try:
        # ChromeDriverManager로 테스트
        manager = ChromeDriverManager()
        
        # 1. 버전 확인
        chrome_version = manager.get_chrome_version()
        logger.info(f"Chrome 브라우저 버전: {chrome_version}")
        
        driver_version = manager.get_chromedriver_version()
        logger.info(f"ChromeDriver 버전: {driver_version}")
        
        # 2. 드라이버 확보
        driver_path = manager.ensure_driver()
        if driver_path:
            logger.info(f"ChromeDriver 경로: {driver_path}")
        else:
            logger.error("ChromeDriver 경로를 찾을 수 없습니다.")
            return False
            
        # 3. 실제 테스트
        logger.info("\n브라우저 실행 테스트...")
        
        # initialize_chrome_driver 함수 사용
        driver = initialize_chrome_driver(worker_id=0, headless=False)
        
        # 테스트 페이지 방문
        logger.info("ABC마트 페이지 접속 시도...")
        driver.get("https://abcmart.a-rt.com")
        
        import time
        time.sleep(3)
        
        title = driver.title
        logger.info(f"페이지 타이틀: {title}")
        
        # 검색 페이지 테스트
        logger.info("\n검색 페이지 테스트...")
        driver.get("https://abcmart.a-rt.com/display/search-word/result?searchWord=아디다스")
        time.sleep(3)
        
        # 상품 링크 찾기
        from selenium.webdriver.common.by import By
        links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="prdtNo="]')
        logger.info(f"찾은 상품 링크 수: {len(links)}")
        
        if links:
            # 첫 번째 링크 정보 출력
            first_link = links[0].get_attribute('href')
            logger.info(f"첫 번째 링크: {first_link}")
            
        driver.quit()
        logger.info("\n✅ Chrome 드라이버 테스트 성공!")
        return True
        
    except Exception as e:
        logger.error(f"\n❌ Chrome 드라이버 테스트 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    success = test_chrome_driver()
    sys.exit(0 if success else 1)
