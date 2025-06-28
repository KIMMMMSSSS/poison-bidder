#!/usr/bin/env python3
"""
Chrome 드라이버 자동 관리 시스템 통합 테스트
"""

import os
import sys
import time
import logging
import subprocess
from pathlib import Path

# 프로젝트 경로 추가
sys.path.append('C:/poison_final')

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

def test_chrome_driver_manager():
    """Chrome 드라이버 관리자 테스트"""
    print("=" * 60)
    print("Chrome 드라이버 자동 관리 시스템 테스트")
    print("=" * 60)
    
    try:
        # 1. ChromeDriverManager import 테스트
        print("\n[1/5] ChromeDriverManager import 테스트...")
        from chrome_driver_manager import ChromeDriverManager, initialize_chrome_driver
        print("✅ import 성공!")
        
        # 2. Chrome 버전 확인 테스트
        print("\n[2/5] Chrome 버전 확인 테스트...")
        manager = ChromeDriverManager()
        chrome_version = manager.get_chrome_version()
        
        if chrome_version:
            print(f"✅ Chrome 버전: {chrome_version}")
        else:
            print("❌ Chrome 버전 확인 실패")
            return False
            
        # 3. ChromeDriver 버전 확인 테스트
        print("\n[3/5] ChromeDriver 버전 확인 테스트...")
        driver_version = manager.get_chromedriver_version()
        
        if driver_version:
            print(f"✅ 기존 ChromeDriver 버전: {driver_version}")
        else:
            print("⚠️ ChromeDriver가 설치되지 않음")
            
        # 4. 자동 드라이버 확보 테스트
        print("\n[4/5] 자동 드라이버 확보 테스트...")
        driver_path = manager.ensure_driver()
        
        if driver_path and os.path.exists(driver_path):
            print(f"✅ ChromeDriver 준비 완료: {driver_path}")
            
            # 새 버전 확인
            new_version = manager.get_chromedriver_version()
            if new_version:
                print(f"✅ ChromeDriver 버전: {new_version}")
                
                # 버전 호환성 확인
                chrome_major = chrome_version.split('.')[0]
                driver_major = new_version.split('.')[0]
                
                if chrome_major == driver_major:
                    print(f"✅ 버전 호환성 확인: 메이저 버전 {chrome_major} 일치")
                else:
                    print(f"❌ 버전 불일치: Chrome {chrome_major} vs Driver {driver_major}")
                    return False
        else:
            print("❌ ChromeDriver 확보 실패")
            return False
            
        # 5. 드라이버 초기화 테스트
        print("\n[5/5] 드라이버 초기화 테스트...")
        try:
            driver = initialize_chrome_driver(worker_id=1, headless=True)
            print("✅ Chrome 드라이버 초기화 성공!")
            
            # 간단한 페이지 로드 테스트
            driver.get("https://www.google.com")
            title = driver.title
            print(f"✅ 페이지 로드 테스트 성공: {title}")
            
            # 드라이버 종료
            driver.quit()
            print("✅ 드라이버 정상 종료")
            
        except Exception as e:
            print(f"❌ 드라이버 초기화 실패: {type(e).__name__} - {str(e)}")
            return False
            
        print("\n" + "=" * 60)
        print("✅ 모든 테스트 통과!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {type(e).__name__} - {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_webdriver_manager_fallback():
    """webdriver-manager fallback 테스트"""
    print("\n" + "=" * 60)
    print("webdriver-manager Fallback 테스트")
    print("=" * 60)
    
    try:
        # ChromeDriver 임시 이름 변경으로 fallback 테스트
        print("\n[1/3] ChromeDriver 백업...")
        driver_path = Path("C:/poison_final/chromedriver.exe")
        backup_path = Path("C:/poison_final/chromedriver_test_backup.exe")
        
        if driver_path.exists():
            driver_path.rename(backup_path)
            print("✅ ChromeDriver 백업 완료")
        
        # webdriver-manager 캐시 삭제
        print("\n[2/3] webdriver-manager 캐시 삭제...")
        from chrome_driver_manager import ChromeDriverManager
        manager = ChromeDriverManager()
        manager.clear_cache()
        print("✅ 캐시 삭제 완료")
        
        # fallback 동작 테스트
        print("\n[3/3] Fallback 동작 테스트...")
        driver_path = manager.ensure_driver()
        
        if driver_path:
            print(f"✅ Fallback 성공: {driver_path}")
        else:
            print("❌ Fallback 실패")
            
        # 백업 복원
        if backup_path.exists():
            backup_path.rename(driver_path)
            print("✅ ChromeDriver 복원 완료")
            
        return True
        
    except Exception as e:
        print(f"❌ Fallback 테스트 실패: {e}")
        # 백업 복원 시도
        if 'backup_path' in locals() and backup_path.exists():
            backup_path.rename(Path("C:/poison_final/chromedriver.exe"))
        return False


def main():
    """메인 테스트 실행"""
    print("\n🚀 Chrome 드라이버 자동 관리 시스템 통합 테스트 시작\n")
    
    # 1. 기본 테스트
    basic_test_passed = test_chrome_driver_manager()
    
    # 2. Fallback 테스트 (선택적)
    if basic_test_passed:
        response = input("\nFallback 테스트도 실행하시겠습니까? (y/n): ")
        if response.lower() == 'y':
            test_webdriver_manager_fallback()
    
    # 3. 결과 요약
    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)
    
    if basic_test_passed:
        print("✅ Chrome 드라이버 자동 관리 시스템: 정상 작동")
        print("✅ 버전 호환성 검사: 통과")
        print("✅ 자동 설치 기능: 정상")
        print("\n💡 이제 poison_bidder_wrapper_v2.py를 실행할 수 있습니다!")
    else:
        print("❌ 테스트 실패")
        print("\n💡 다음을 확인하세요:")
        print("1. Chrome 브라우저가 설치되어 있는지 확인")
        print("2. 인터넷 연결 상태 확인")
        print("3. python -m pip install --upgrade webdriver-manager 실행")


if __name__ == "__main__":
    main()
    input("\n테스트 완료. Enter를 눌러 종료하세요...")
