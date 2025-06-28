#!/usr/bin/env python3
"""
Chrome 브라우저와 ChromeDriver 버전 확인 및 자동 업데이트
"""

import os
import sys
import subprocess
import re
import requests
from pathlib import Path

def get_chrome_version():
    """설치된 Chrome 브라우저 버전 확인"""
    try:
        # Windows에서 Chrome 버전 확인
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")
        ]
        
        for chrome_path in chrome_paths:
            if os.path.exists(chrome_path):
                # Chrome 버전 가져오기
                result = subprocess.run(
                    [chrome_path, '--version'],
                    capture_output=True,
                    text=True
                )
                version_match = re.search(r'(\d+\.\d+\.\d+\.\d+)', result.stdout)
                if version_match:
                    version = version_match.group(1)
                    print(f"✅ Chrome 브라우저 버전: {version}")
                    return version
        
        print("❌ Chrome 브라우저를 찾을 수 없습니다.")
        return None
        
    except Exception as e:
        print(f"❌ Chrome 버전 확인 실패: {e}")
        return None

def get_chromedriver_version():
    """현재 ChromeDriver 버전 확인"""
    try:
        # 현재 디렉토리의 chromedriver 확인
        chromedriver_path = "chromedriver.exe"
        if os.path.exists(chromedriver_path):
            result = subprocess.run(
                [chromedriver_path, '--version'],
                capture_output=True,
                text=True
            )
            version_match = re.search(r'(\d+\.\d+\.\d+\.\d+)', result.stdout)
            if version_match:
                version = version_match.group(1)
                print(f"✅ ChromeDriver 버전: {version}")
                return version
        
        print("❌ ChromeDriver를 찾을 수 없습니다.")
        return None
        
    except Exception as e:
        print(f"❌ ChromeDriver 버전 확인 실패: {e}")
        return None

def download_chromedriver():
    """webdriver-manager를 사용하여 ChromeDriver 자동 다운로드"""
    try:
        print("\n🔄 ChromeDriver 자동 다운로드 중...")
        
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        
        # webdriver-manager로 자동 다운로드
        driver_path = ChromeDriverManager().install()
        print(f"✅ ChromeDriver 다운로드 완료: {driver_path}")
        
        # 현재 디렉토리로 복사
        import shutil
        local_path = "chromedriver.exe"
        if os.path.exists(driver_path):
            shutil.copy2(driver_path, local_path)
            print(f"✅ ChromeDriver 복사 완료: {local_path}")
            
        return True
        
    except Exception as e:
        print(f"❌ ChromeDriver 다운로드 실패: {e}")
        return False

def test_chrome_driver():
    """Chrome 드라이버 테스트"""
    try:
        print("\n🧪 Chrome 드라이버 테스트 중...")
        
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        import undetected_chromedriver as uc
        
        # undetected-chromedriver로 테스트
        options = uc.ChromeOptions()
        options.add_argument('--headless')
        
        driver = uc.Chrome(options=options, version_main=None)
        driver.get("https://www.google.com")
        title = driver.title
        driver.quit()
        
        print(f"✅ Chrome 드라이버 테스트 성공! (페이지 타이틀: {title})")
        return True
        
    except Exception as e:
        print(f"❌ Chrome 드라이버 테스트 실패: {e}")
        return False

def main():
    print("="*60)
    print("Chrome 브라우저 및 ChromeDriver 버전 확인")
    print("="*60)
    
    # 1. Chrome 브라우저 버전 확인
    chrome_version = get_chrome_version()
    
    # 2. ChromeDriver 버전 확인
    chromedriver_version = get_chromedriver_version()
    
    # 3. 버전 비교
    if chrome_version and chromedriver_version:
        chrome_major = chrome_version.split('.')[0]
        driver_major = chromedriver_version.split('.')[0]
        
        if chrome_major == driver_major:
            print(f"\n✅ 버전 호환성 OK! (메이저 버전 {chrome_major} 일치)")
        else:
            print(f"\n⚠️ 버전 불일치! Chrome: {chrome_major}, Driver: {driver_major}")
            print("ChromeDriver 업데이트가 필요합니다.")
    
    # 4. ChromeDriver 다운로드 제안
    if not chromedriver_version or (chrome_version and chromedriver_version and 
                                   chrome_version.split('.')[0] != chromedriver_version.split('.')[0]):
        response = input("\nChromeDriver를 자동으로 다운로드하시겠습니까? (y/n): ")
        if response.lower() == 'y':
            if download_chromedriver():
                # 다시 버전 확인
                new_version = get_chromedriver_version()
                if new_version:
                    print(f"\n✅ 새 ChromeDriver 버전: {new_version}")
    
    # 5. 테스트 실행
    print("\n" + "="*60)
    response = input("Chrome 드라이버를 테스트하시겠습니까? (y/n): ")
    if response.lower() == 'y':
        test_chrome_driver()
    
    print("\n완료!")

if __name__ == "__main__":
    main()
    input("\nEnter를 눌러 종료하세요...")
