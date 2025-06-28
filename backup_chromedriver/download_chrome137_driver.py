#!/usr/bin/env python3
"""
Chrome 137 버전용 ChromeDriver 다운로드
"""

import os
import requests
import zipfile
import shutil

def download_chromedriver_137():
    """Chrome 137용 ChromeDriver 다운로드"""
    print("Chrome 137용 ChromeDriver 다운로드 시작...")
    
    # Chrome 137 버전의 ChromeDriver URL
    driver_version = "137.0.7151.120"
    
    # 새로운 Chrome for Testing URL 구조
    driver_url = f"https://storage.googleapis.com/chrome-for-testing-public/{driver_version}/win64/chromedriver-win64.zip"
    
    print(f"다운로드 URL: {driver_url}")
    
    try:
        # 다운로드
        response = requests.get(driver_url, timeout=30)
        
        if response.status_code != 200:
            print(f"다운로드 실패. 상태 코드: {response.status_code}")
            # 대체 URL 시도
            driver_url = "https://storage.googleapis.com/chrome-for-testing-public/137.0.7151.120/win64/chromedriver-win64.zip"
            print(f"대체 URL 시도: {driver_url}")
            response = requests.get(driver_url, timeout=30)
            
        if response.status_code == 200:
            # 파일 저장
            zip_path = "C:/poison_final/chromedriver_temp.zip"
            with open(zip_path, 'wb') as f:
                f.write(response.content)
            print("다운로드 완료!")
            
            # 기존 드라이버 백업
            if os.path.exists("C:/poison_final/chromedriver.exe"):
                backup_path = "C:/poison_final/chromedriver_backup_131.exe"
                shutil.move("C:/poison_final/chromedriver.exe", backup_path)
                print(f"기존 드라이버 백업: {backup_path}")
            
            # 압축 해제
            print("압축 해제 중...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # chromedriver-win64 폴더 내의 chromedriver.exe 찾기
                for name in zip_ref.namelist():
                    if name.endswith('chromedriver.exe'):
                        # 임시 폴더에 추출
                        zip_ref.extract(name, "C:/poison_final/temp/")
                        # 루트로 이동
                        temp_path = f"C:/poison_final/temp/{name}"
                        final_path = "C:/poison_final/chromedriver.exe"
                        shutil.move(temp_path, final_path)
                        print(f"ChromeDriver 설치 완료: {final_path}")
                        break
            
            # 임시 파일 정리
            os.remove(zip_path)
            if os.path.exists("C:/poison_final/temp"):
                shutil.rmtree("C:/poison_final/temp")
                
            print("\n✅ Chrome 137용 ChromeDriver 설치 완료!")
            
            # 버전 확인
            import subprocess
            result = subprocess.run(["C:/poison_final/chromedriver.exe", "--version"], 
                                  capture_output=True, text=True)
            print(f"\n새 ChromeDriver 버전: {result.stdout.strip()}")
            
        else:
            print(f"다운로드 실패: {response.status_code}")
            
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    download_chromedriver_137()
