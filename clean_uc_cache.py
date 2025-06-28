#!/usr/bin/env python3
"""
undetected_chromedriver 캐시 정리 및 재설정
"""

import os
import shutil
import subprocess
import sys

def clean_uc_cache():
    """undetected_chromedriver 캐시 정리"""
    print("=" * 60)
    print("undetected_chromedriver 캐시 정리")
    print("=" * 60)
    
    # 캐시 디렉토리 목록
    cache_dirs = [
        os.path.join(os.environ.get('APPDATA', ''), 'undetected_chromedriver'),
        os.path.join(os.environ.get('LOCALAPPDATA', ''), 'undetected_chromedriver'),
        os.path.join(os.path.expanduser('~'), '.undetected_chromedriver'),
        os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming', 'undetected_chromedriver'),
        os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'undetected_chromedriver'),
    ]
    
    print("\n1. 캐시 디렉토리 검색 및 삭제:")
    for cache_dir in cache_dirs:
        if os.path.exists(cache_dir):
            try:
                print(f"   [삭제] {cache_dir}")
                shutil.rmtree(cache_dir)
            except Exception as e:
                print(f"   [실패] {cache_dir} - {e}")
        else:
            print(f"   [없음] {cache_dir}")
    
    print("\n2. pip 캐시 정리:")
    try:
        subprocess.run([sys.executable, "-m", "pip", "cache", "purge"], check=True)
        print("   [OK] pip 캐시 정리 완료")
    except Exception as e:
        print(f"   [실패] pip 캐시 정리 - {e}")
    
    print("\n3. undetected_chromedriver 재설치:")
    try:
        # 제거
        print("   - 기존 패키지 제거 중...")
        subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", "undetected-chromedriver"], check=True)
        
        # 재설치
        print("   - 최신 버전 설치 중...")
        subprocess.run([sys.executable, "-m", "pip", "install", "undetected-chromedriver", "--no-cache-dir"], check=True)
        print("   [OK] 재설치 완료")
    except Exception as e:
        print(f"   [실패] 재설치 - {e}")
    
    print("\n4. 간단한 테스트:")
    try:
        import undetected_chromedriver as uc
        print(f"   - 버전: {uc.__version__ if hasattr(uc, '__version__') else '알 수 없음'}")
        
        # 옵션 설정
        options = uc.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        
        # Chrome 137 버전 명시
        print("   - Chrome 137로 초기화 시도...")
        driver = uc.Chrome(options=options, version_main=137)
        driver.get("https://www.google.com")
        print(f"   - 페이지 타이틀: {driver.title}")
        driver.quit()
        print("   [OK] 테스트 성공!")
        
    except Exception as e:
        print(f"   [실패] 테스트 - {e}")
        print("\n   대안: Selenium WebDriver 사용을 권장합니다.")
    
    print("\n" + "=" * 60)
    print("완료!")


if __name__ == "__main__":
    clean_uc_cache()
