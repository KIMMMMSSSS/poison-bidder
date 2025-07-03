#!/usr/bin/env python3
"""
ChromeDriver 작동 테스트
"""

import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

print("ChromeDriver 테스트 시작...")

try:
    # Chrome 옵션 설정
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1280,720')
    
    # webdriver-manager를 사용하여 드라이버 초기화
    print("ChromeDriver 초기화 중...")
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), 
        options=chrome_options
    )
    
    print("ChromeDriver 초기화 성공!")
    
    # 테스트 페이지 열기
    print("테스트 페이지 열기...")
    driver.get("https://www.google.com")
    
    print(f"페이지 타이틀: {driver.title}")
    
    # 3초 대기
    time.sleep(3)
    
    # 브라우저 종료
    driver.quit()
    print("테스트 완료! ChromeDriver가 정상적으로 작동합니다.")
    
except Exception as e:
    print(f"오류 발생: {type(e).__name__}")
    print(f"상세: {str(e)}")
