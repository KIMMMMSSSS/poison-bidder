#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
브라우저 크래시 테스트
브라우저가 바로 꺼지는 원인을 찾기 위한 스크립트
"""

import os
import sys
import time
import traceback

# 콘솔 인코딩 설정
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

print("브라우저 크래시 테스트 시작...")

# 1. 일반 Selenium 테스트
print("\n1. 일반 Selenium Chrome 테스트")
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    # 디버그 로그 활성화
    options.add_argument("--enable-logging")
    options.add_argument("--v=1")
    
    # ChromeDriver 경로
    driver_path = "C:/poison_final/chromedriver.exe"
    service = Service(driver_path)
    
    print(f"   ChromeDriver 경로: {driver_path}")
    print(f"   파일 존재: {os.path.exists(driver_path)}")
    
    print("   드라이버 생성 중...")
    driver = webdriver.Chrome(service=service, options=options)
    print("   [OK] 일반 Selenium 드라이버 생성 성공!")
    
    print("   구글 접속 시도...")
    driver.get("https://www.google.com")
    time.sleep(2)
    print("   [OK] 페이지 로드 성공!")
    
    print("   타이틀:", driver.title)
    driver.quit()
    print("   [OK] 드라이버 정상 종료")
    
except Exception as e:
    print(f"   [ERROR] 일반 Selenium 실패: {e}")
    traceback.print_exc()

# 2. undetected_chromedriver 테스트
print("\n2. undetected_chromedriver 테스트")
try:
    import undetected_chromedriver as uc
    
    # 버전 확인
    print(f"   undetected_chromedriver 버전: {uc.__version__ if hasattr(uc, '__version__') else 'Unknown'}")
    
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    
    # Chrome 바이너리 경로 명시적 설정
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")
    ]
    
    chrome_found = False
    for chrome_path in chrome_paths:
        if os.path.exists(chrome_path):
            options.binary_location = chrome_path
            chrome_found = True
            print(f"   Chrome 경로: {chrome_path}")
            break
    
    if not chrome_found:
        print("   [WARNING] Chrome 실행 파일을 찾을 수 없습니다!")
    
    print("   드라이버 생성 중...")
    # version_main을 명시적으로 지정
    driver = uc.Chrome(options=options, version_main=137)
    print("   [OK] undetected_chromedriver 생성 성공!")
    
    print("   구글 접속 시도...")
    driver.get("https://www.google.com")
    time.sleep(2)
    print("   [OK] 페이지 로드 성공!")
    
    print("   타이틀:", driver.title)
    
    # ABC마트 접속 테스트
    print("\n   ABC마트 접속 시도...")
    driver.get("https://abcmart.a-rt.com")
    time.sleep(3)
    print("   [OK] ABC마트 로드 성공!")
    print("   타이틀:", driver.title)
    
    driver.quit()
    print("   [OK] 드라이버 정상 종료")
    
except Exception as e:
    print(f"   [ERROR] undetected_chromedriver 실패: {e}")
    traceback.print_exc()

# 3. 프로세스 확인
print("\n3. Chrome 프로세스 확인")
try:
    import psutil
    chrome_processes = []
    for proc in psutil.process_iter(['pid', 'name']):
        if 'chrome' in proc.info['name'].lower():
            chrome_processes.append(proc.info)
    
    if chrome_processes:
        print(f"   실행 중인 Chrome 프로세스: {len(chrome_processes)}개")
        for proc in chrome_processes[:5]:  # 처음 5개만
            print(f"   - PID: {proc['pid']}, Name: {proc['name']}")
    else:
        print("   실행 중인 Chrome 프로세스 없음")
except:
    print("   psutil을 사용할 수 없습니다.")

print("\n테스트 완료!")
