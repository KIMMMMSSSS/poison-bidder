#!/usr/bin/env python3
"""
ChromeDriver 작동 테스트 - chrome_driver_manager 사용
"""

import time
from selenium import webdriver
from chrome_driver_manager import initialize_chrome_driver

print("ChromeDriver 테스트 시작...")

try:
    # chrome_driver_manager를 사용하여 드라이버 초기화
    print("ChromeDriver 초기화 중...")
    driver = initialize_chrome_driver(
        headless=False,  # 테스트이므로 화면 표시
        use_undetected=False,  # 일반 모드로 테스트
        extra_options=['--window-size=1280,720']
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
