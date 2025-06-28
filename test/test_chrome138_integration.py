"""
Chrome 138 통합 테스트
chrome_driver_manager를 사용하여 모든 주요 기능이 정상 작동하는지 확인
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chrome_driver_manager import initialize_chrome_driver, get_chrome_version
import time
from datetime import datetime

def print_section(title):
    """섹션 구분선 출력"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)

def test_chrome_driver_initialization():
    """ChromeDriver 초기화 테스트"""
    print_section("1. ChromeDriver 초기화 테스트")
    
    try:
        # Chrome 버전 확인
        chrome_version = get_chrome_version()
        print(f"Chrome 버전: {chrome_version}")
        
        # 헤드리스 모드로 드라이버 초기화
        print("헤드리스 모드로 드라이버 초기화 중...")
        driver = initialize_chrome_driver(headless=True)
        
        print("[PASS] ChromeDriver 초기화 성공")
        driver.quit()
        return True
        
    except Exception as e:
        print(f"[FAIL] ChromeDriver 초기화 실패: {e}")
        return False

def test_musinsa_connection():
    """무신사 접속 테스트"""
    print_section("2. 무신사 접속 테스트")
    
    try:
        driver = initialize_chrome_driver(headless=True)
        
        print("무신사 메인 페이지 접속 중...")
        driver.get("https://www.musinsa.com")
        time.sleep(2)
        
        if "무신사" in driver.title:
            print("[PASS] 무신사 접속 성공")
            result = True
        else:
            print(f"[FAIL] 무신사 접속 실패: 예상과 다른 타이틀 - {driver.title}")
            result = False
            
        driver.quit()
        return result
        
    except Exception as e:
        print(f"[FAIL] 무신사 접속 테스트 실패: {e}")
        return False

def test_abcmart_connection():
    """ABC마트 접속 테스트"""
    print_section("3. ABC마트 접속 테스트")
    
    try:
        driver = initialize_chrome_driver(headless=True)
        
        print("ABC마트 메인 페이지 접속 중...")
        driver.get("https://abcmart.a-rt.com")
        time.sleep(2)
        
        if "ABC" in driver.title.upper():
            print("[PASS] ABC마트 접속 성공")
            result = True
        else:
            print(f"[FAIL] ABC마트 접속 실패: 예상과 다른 타이틀 - {driver.title}")
            result = False
            
        driver.quit()
        return result
        
    except Exception as e:
        print(f"[FAIL] ABC마트 접속 테스트 실패: {e}")
        return False

def test_poizon_connection():
    """Poizon 접속 테스트 (로그인 페이지까지)"""
    print_section("4. Poizon 접속 테스트")
    
    try:
        driver = initialize_chrome_driver(headless=True)
        
        print("Poizon 로그인 페이지 접속 중...")
        driver.get("https://www.dewuapp.com")
        time.sleep(3)
        
        # 페이지가 로드되었는지 확인
        if driver.current_url:
            print(f"현재 URL: {driver.current_url}")
            print("[PASS] Poizon 사이트 접속 성공")
            result = True
        else:
            print("[FAIL] Poizon 사이트 접속 실패")
            result = False
            
        driver.quit()
        return result
        
    except Exception as e:
        print(f"[FAIL] Poizon 접속 테스트 실패: {e}")
        return False

def test_multiple_workers():
    """멀티 워커 테스트"""
    print_section("5. 멀티 워커 동시 실행 테스트")
    
    try:
        print("3개의 워커를 동시에 실행합니다...")
        drivers = []
        
        # 3개의 드라이버 동시 생성
        for i in range(3):
            print(f"워커 {i+1} 초기화 중...")
            driver = initialize_chrome_driver(worker_id=i+1, headless=True)
            drivers.append(driver)
            
        # 각 드라이버로 다른 사이트 접속
        sites = [
            ("https://www.google.com", "Google"),
            ("https://www.naver.com", "NAVER"),
            ("https://www.daum.net", "Daum")
        ]
        
        for i, (driver, (url, name)) in enumerate(zip(drivers, sites)):
            print(f"워커 {i+1}: {name} 접속 중...")
            driver.get(url)
            
        time.sleep(2)
        
        # 모든 드라이버 종료
        for i, driver in enumerate(drivers):
            print(f"워커 {i+1} 종료 중...")
            driver.quit()
            
        print("[PASS] 멀티 워커 테스트 성공")
        return True
        
    except Exception as e:
        print(f"[FAIL] 멀티 워커 테스트 실패: {e}")
        # 남은 드라이버 정리
        for driver in drivers:
            try:
                driver.quit()
            except:
                pass
        return False

def run_all_tests():
    """모든 테스트 실행"""
    print(f"\n{'#'*60}")
    print(f"  Chrome 138 통합 테스트 시작")
    print(f"  실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*60}")
    
    # 테스트 목록
    tests = [
        ("ChromeDriver 초기화", test_chrome_driver_initialization),
        ("무신사 접속", test_musinsa_connection),
        ("ABC마트 접속", test_abcmart_connection),
        ("Poizon 접속", test_poizon_connection),
        ("멀티 워커", test_multiple_workers)
    ]
    
    results = []
    
    # 각 테스트 실행
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n테스트 중 예외 발생: {e}")
            results.append((test_name, False))
    
    # 결과 요약
    print_section("테스트 결과 요약")
    
    passed = 0
    failed = 0
    
    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{test_name:20} : {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\n총 {len(results)}개 테스트 중:")
    print(f"  - 성공: {passed}개")
    print(f"  - 실패: {failed}개")
    
    if failed == 0:
        print("\n[SUCCESS] 모든 테스트가 성공했습니다!")
        print("Chrome 138과 chrome_driver_manager가 정상적으로 작동합니다.")
    else:
        print(f"\n[WARNING] {failed}개의 테스트가 실패했습니다.")
        print("실패한 테스트를 확인해주세요.")
    
    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
