#!/usr/bin/env python3
"""
Chrome 드라이버 버전 문제 자동 해결 스크립트
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

print("=" * 60)
print("Chrome 드라이버 버전 문제 자동 해결")
print("=" * 60)

# 1. 기존 ChromeDriver 파일들 삭제
print("\n1. 기존 ChromeDriver 파일 정리 중...")
chromedriver_files = [
    "chromedriver.exe",
    "chromedriver_backup.exe",
    "chromedriver_old.zip"
]

for file in chromedriver_files:
    if os.path.exists(file):
        try:
            os.remove(file)
            print(f"   ✅ {file} 삭제 완료")
        except Exception as e:
            print(f"   ⚠️ {file} 삭제 실패: {e}")

# 2. undetected-chromedriver 캐시 정리
print("\n2. undetected-chromedriver 캐시 정리 중...")
uc_dirs = [
    os.path.join(os.environ.get('APPDATA', ''), 'undetected_chromedriver'),
    os.path.join(os.environ.get('LOCALAPPDATA', ''), 'undetected_chromedriver'),
    os.path.join(os.path.expanduser('~'), '.undetected_chromedriver'),
]

for uc_dir in uc_dirs:
    if os.path.exists(uc_dir):
        try:
            shutil.rmtree(uc_dir)
            print(f"   ✅ {uc_dir} 삭제 완료")
        except Exception as e:
            print(f"   ⚠️ {uc_dir} 삭제 실패: {e}")

# 3. 패키지 업데이트
print("\n3. 필수 패키지 업데이트 중...")
packages = [
    "selenium",
    "undetected-chromedriver",
    "webdriver-manager"
]

for package in packages:
    print(f"\n   📦 {package} 업데이트 중...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", package])
        print(f"   ✅ {package} 업데이트 완료")
    except subprocess.CalledProcessError:
        print(f"   ❌ {package} 업데이트 실패")

# 4. Chrome 드라이버 테스트
print("\n4. Chrome 드라이버 테스트...")
try:
    import undetected_chromedriver as uc
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    
    print("   🔄 Chrome 드라이버 초기화 중...")
    
    # undetected-chromedriver로 테스트
    options = uc.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    # version_main=None으로 자동 버전 매칭
    driver = uc.Chrome(options=options, version_main=None)
    driver.get("https://www.google.com")
    title = driver.title
    driver.quit()
    
    print(f"   ✅ Chrome 드라이버 테스트 성공!")
    print(f"   ✅ 테스트 페이지: {title}")
    
except Exception as e:
    print(f"   ❌ Chrome 드라이버 테스트 실패: {e}")
    print("\n   💡 Chrome 브라우저가 최신 버전인지 확인하세요.")
    print("   💡 Chrome 업데이트: chrome://settings/help")

print("\n" + "=" * 60)
print("✅ Chrome 드라이버 문제 해결 완료!")
print("=" * 60)

# 5. ABC마트 스크래핑 테스트
print("\n5. ABC마트 스크래핑 다시 실행하시겠습니까?")
response = input("   실행하려면 'y'를 입력하세요: ")

if response.lower() == 'y':
    print("\n   🚀 ABC마트 스크래핑 실행 중...")
    try:
        # unified_bidding.py 실행
        subprocess.call([
            sys.executable, 
            "unified_bidding.py",
            "--site", "abcmart",
            "--web-scraping",
            "--search-keyword", "아디다스신발"
        ])
    except Exception as e:
        print(f"   ❌ 실행 실패: {e}")
        print("\n   다음 명령을 직접 실행하세요:")
        print('   python unified_bidding.py --site abcmart --web-scraping --search-keyword "아디다스신발"')
