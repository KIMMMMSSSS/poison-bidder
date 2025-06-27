#!/usr/bin/env python3
"""Chrome 138 호환성 테스트 스크립트"""

import logging
from chrome_driver_manager import ChromeDriverManager

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

print("=" * 60)
print("Chrome 138 호환성 테스트")
print("=" * 60)

# ChromeDriverManager 인스턴스 생성
manager = ChromeDriverManager()

# Chrome 버전 확인
chrome_version = manager.get_chrome_version()
print(f"\n현재 Chrome 버전: {chrome_version}")

# ChromeDriver 버전 확인
driver_version = manager.get_chromedriver_version()
print(f"현재 ChromeDriver 버전: {driver_version}")

# 호환성 확인
if chrome_version and driver_version:
    chrome_major = chrome_version.split('.')[0]
    driver_major = driver_version.split('.')[0]
    
    if chrome_major == driver_major:
        print(f"\n[OK] 버전 호환성 OK! (메이저 버전 {chrome_major} 일치)")
    else:
        print(f"\n[WARNING] 버전 불일치! Chrome: {chrome_major}, Driver: {driver_major}")
        print("새로운 ChromeDriver를 다운로드합니다...")
        
        # 드라이버 확보
        driver_path = manager.ensure_driver()
        
        if driver_path:
            print(f"\n[OK] ChromeDriver 준비 완료: {driver_path}")
            
            # 다시 버전 확인
            new_driver_version = manager.get_chromedriver_version()
            print(f"새로운 ChromeDriver 버전: {new_driver_version}")
else:
    print("\n[ERROR] 버전 정보를 가져올 수 없습니다.")

print("\nChrome 138 호환성 테스트 완료!")
