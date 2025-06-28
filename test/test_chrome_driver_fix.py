#!/usr/bin/env python3
"""
Chrome 드라이버 초기화 테스트
"""

import sys
import os
import logging

# 상위 디렉토리를 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chrome_driver_manager import initialize_chrome_driver, ChromeDriverInitError, cleanup_chrome_processes

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

logger = logging.getLogger(__name__)


def test_chrome_driver_initialization():
    """Chrome 드라이버 초기화 테스트"""
    print("=" * 60)
    print("Chrome 드라이버 초기화 테스트")
    print("=" * 60)
    
    # 테스트 1: 기본 초기화 (undetected-chromedriver)
    print("\n[테스트 1] 기본 초기화 (undetected-chromedriver)")
    print("-" * 50)
    driver = None
    try:
        driver = initialize_chrome_driver(worker_id=1, headless=True)
        print("✅ 드라이버 초기화 성공!")
        print(f"드라이버 타입: {type(driver)}")
        
        # 기본 기능 테스트
        driver.get("https://www.google.com")
        print(f"✅ 페이지 로드 성공: {driver.title}")
        
    except ChromeDriverInitError as e:
        print(f"❌ ChromeDriverInitError 발생: {e}")
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {type(e).__name__}: {e}")
    finally:
        if driver:
            driver.quit()
            print("✅ 드라이버 정상 종료")
    
    # Chrome 프로세스 정리
    cleanup_chrome_processes()
    
    # 테스트 2: 일반 Selenium 모드 (ABC마트용)
    print("\n[테스트 2] 일반 Selenium 모드 (ABC마트용)")
    print("-" * 50)
    driver = None
    try:
        driver = initialize_chrome_driver(
            worker_id=2, 
            headless=True, 
            use_undetected=False,
            extra_options=['--abcmart-mode']
        )
        print("✅ 드라이버 초기화 성공!")
        print(f"드라이버 타입: {type(driver)}")
        
        # 기본 기능 테스트
        driver.get("https://abcmart.a-rt.com")
        print(f"✅ ABC마트 페이지 로드 성공!")
        
    except ChromeDriverInitError as e:
        print(f"❌ ChromeDriverInitError 발생: {e}")
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {type(e).__name__}: {e}")
    finally:
        if driver:
            driver.quit()
            print("✅ 드라이버 정상 종료")
    
    # Chrome 프로세스 정리
    cleanup_chrome_processes()
    
    # 테스트 3: None 반환 방지 테스트
    print("\n[테스트 3] None 반환 방지 테스트")
    print("-" * 50)
    print("Chrome 드라이버가 None을 반환하지 않는지 확인...")
    
    for i in range(3):
        print(f"\n시도 {i+1}/3:")
        try:
            driver = initialize_chrome_driver(worker_id=i+10, headless=True)
            if driver is None:
                print("❌ 오류: 드라이버가 None을 반환했습니다!")
            else:
                print(f"✅ 정상: 드라이버 객체 반환 ({type(driver)})")
                driver.quit()
        except ChromeDriverInitError as e:
            print(f"✅ 정상: ChromeDriverInitError 발생 (None 대신 예외 발생)")
        except Exception as e:
            print(f"⚠️  기타 예외: {type(e).__name__}: {e}")
        
        cleanup_chrome_processes()
    
    print("\n" + "=" * 60)
    print("테스트 완료!")
    print("=" * 60)


if __name__ == "__main__":
    test_chrome_driver_initialization()
