#!/usr/bin/env python3
"""Chrome driver manager 종합 테스트"""

import logging
from chrome_driver_manager import ChromeDriverManager, initialize_chrome_driver

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

print("=" * 60)
print("Chrome Driver Manager 종합 테스트")
print("=" * 60)

# 1. ensure_driver() 테스트
print("\n[TEST 1] ensure_driver() 테스트")
manager = ChromeDriverManager()
driver_path = manager.ensure_driver()

if driver_path:
    print(f"[OK] ChromeDriver 경로: {driver_path}")
else:
    print("[ERROR] ensure_driver() 실패")

# 2. 버전 확인
print("\n[TEST 2] 버전 확인")
chrome_version = manager.get_chrome_version()
driver_version = manager.get_chromedriver_version()
print(f"Chrome 버전: {chrome_version}")
print(f"ChromeDriver 버전: {driver_version}")

if chrome_version and driver_version:
    chrome_major = chrome_version.split('.')[0]
    driver_major = driver_version.split('.')[0]
    if chrome_major == driver_major:
        print(f"[OK] 메이저 버전 일치: {chrome_major}")
    else:
        print(f"[ERROR] 메이저 버전 불일치: Chrome {chrome_major} vs Driver {driver_major}")

# 3. initialize_chrome_driver() 테스트
print("\n[TEST 3] initialize_chrome_driver() 테스트")
try:
    driver = initialize_chrome_driver(worker_id=1, headless=True)
    print("[OK] Chrome driver 초기화 성공")
    
    # 간단한 페이지 로드 테스트
    driver.get("https://www.google.com")
    title = driver.title
    print(f"[OK] 페이지 로드 성공: {title}")
    
    driver.quit()
    print("[OK] Chrome driver 종료 성공")
    
except Exception as e:
    print(f"[ERROR] Chrome driver 테스트 실패: {e}")

print("\n[RESULT] 모든 테스트 완료!")
