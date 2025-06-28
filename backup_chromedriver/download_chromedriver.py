#!/usr/bin/env python3
"""
Chrome 드라이버 자동 다운로드 및 설정
"""

import os
import sys
import zipfile
import requests
import platform
from pathlib import Path

def get_chrome_version():
    """Chrome 버전 확인"""
    if platform.system() == "Windows":
        import winreg
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\BLBeacon")
            version, _ = winreg.QueryValueEx(key, "version")
            return version
        except:
            return None
    return None

def download_chromedriver():
    """Chrome 드라이버 다운로드"""
    print("Chrome 드라이버 다운로드 중...")
    
    # Chrome 버전 확인
    chrome_version = get_chrome_version()
    if chrome_version:
        print(f"Chrome 버전: {chrome_version}")
        major_version = chrome_version.split('.')[0]
    else:
        print("Chrome 버전을 확인할 수 없습니다. 최신 버전으로 다운로드합니다.")
        major_version = "131"  # 최신 버전
    
    # 다운로드 URL
    if platform.system() == "Windows":
        # Chrome 137은 특별 처리
        if major_version == "137":
            print(f"Chrome {major_version}은 특별 처리가 필요합니다. 대체 방법 사용...")
            # Chrome 137용 ChromeDriver는 새로운 URL 구조 사용
            driver_url = "https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/131.0.6778.33/win32/chromedriver-win32.zip"
        else:
            download_url = f"https://chromedriver.storage.googleapis.com/LATEST_RELEASE_{major_version}"
            try:
                response = requests.get(download_url)
                driver_version = response.text.strip()
            except:
                # 대체 URL
                driver_version = "131.0.6778.33"  # 최신 안정 버전
            
            driver_url = f"https://chromedriver.storage.googleapis.com/{driver_version}/chromedriver_win32.zip"
        
        # 다운로드
        print(f"다운로드 중: {driver_url}")
        response = requests.get(driver_url)
        
        if response.status_code != 200:
            print(f"다운로드 실패. 상태 코드: {response.status_code}")
            print("대체 다운로드 URL 시도 중...")
            # 대체 URL (Chrome for Testing)
            driver_url = "https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/131.0.6778.33/win32/chromedriver-win32.zip"
            response = requests.get(driver_url)
        
        # 저장
        zip_path = Path("C:/poison_final/chromedriver.zip")
        with open(zip_path, 'wb') as f:
            f.write(response.content)
        
        # 압축 해제
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # 새로운 ChromeDriver 구조 확인
                for name in zip_ref.namelist():
                    if name.endswith('chromedriver.exe'):
                        # chromedriver.exe만 추출
                        zip_ref.extract(name, "C:/poison_final/temp")
                        # 파일 이동
                        import shutil
                        shutil.move(f"C:/poison_final/temp/{name}", "C:/poison_final/chromedriver.exe")
                        # 임시 폴더 정리
                        shutil.rmtree("C:/poison_final/temp", ignore_errors=True)
                        break
                else:
                    # 기존 방식
                    zip_ref.extractall("C:/poison_final")
        except Exception as e:
            print(f"압축 해제 오류: {e}")
            return None
        
        # zip 파일 삭제
        zip_path.unlink()
        
        print("Chrome 드라이버 다운로드 완료!")
        print("경로: C:/poison_final/chromedriver.exe")
        
        return "C:/poison_final/chromedriver.exe"
    
    else:
        print("Windows가 아닌 시스템은 지원하지 않습니다.")
        return None

if __name__ == "__main__":
    # Chrome 드라이버가 없으면 다운로드
    driver_path = Path("C:/poison_final/chromedriver.exe")
    if not driver_path.exists():
        download_chromedriver()
    else:
        print("Chrome 드라이버가 이미 존재합니다.")
