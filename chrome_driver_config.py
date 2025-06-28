#!/usr/bin/env python3
"""
ChromeDriver 자동 관리 설정
Chrome 버전에 관계없이 항상 작동하도록 설정
"""

import os
import logging
import undetected_chromedriver as uc
from pathlib import Path
import tempfile
import time

logger = logging.getLogger(__name__)

def get_chrome_driver(headless=False, disable_gpu=True):
    """
    Chrome 버전에 맞는 드라이버를 자동으로 가져오는 함수
    
    Args:
        headless: 헤드리스 모드 사용 여부
        disable_gpu: GPU 비활성화 여부
        
    Returns:
        uc.Chrome: 설정된 Chrome 드라이버 인스턴스
    """
    options = uc.ChromeOptions()
    
    # 기본 옵션 설정
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-infobars")
    options.add_argument("--window-size=1920,1080")
    
    # Chrome 프로필 선택 화면 우회 옵션 추가
    options.add_argument("--no-first-run")  # 첫 실행 화면 비활성화
    options.add_argument("--no-default-browser-check")  # 기본 브라우저 확인 비활성화
    options.add_argument("--disable-features=ChromeWhatsNewUI")  # Chrome 새 기능 UI 비활성화
    options.add_argument("--disable-search-engine-choice-screen")  # 검색엔진 선택 화면 비활성화
    
    if disable_gpu:
        options.add_argument("--disable-gpu")
    
    if headless:
        options.add_argument("--headless")
    
    # 임시 사용자 데이터 디렉토리 설정 (격리된 프로필 사용)
    temp_dir = tempfile.mkdtemp(prefix="chrome_profile_")
    options.add_argument(f"--user-data-dir={temp_dir}")
    logger.info(f"임시 Chrome 프로필 디렉토리 생성: {temp_dir}")
    
    # 재시도 로직 추가
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            # version_main=None으로 설정하면 현재 설치된 Chrome 버전을 자동 감지
            driver = uc.Chrome(
                options=options,
                version_main=None,  # 자동 버전 감지
                driver_executable_path=None,  # 자동 다운로드 경로 사용
                use_subprocess=True,  # 서브프로세스로 실행 (안정성 향상)
                suppress_welcome=True  # 환영 화면 억제 (프로필 선택 화면 포함)
            )
            
            # 드라이버가 None이 아닌지 확인
            if driver is None:
                raise Exception("Chrome 드라이버가 None을 반환했습니다.")
            
            # 드라이버가 정상적으로 작동하는지 확인
            try:
                driver.set_page_load_timeout(30)  # 페이지 로드 타임아웃 설정으로 검증
            except AttributeError:
                raise Exception("Chrome 드라이버 객체가 유효하지 않습니다.")
            
            logger.info(f"Chrome 드라이버 초기화 성공 (시도 {attempt + 1}/{max_retries})")
            logger.info(f"Chrome 버전: {driver.capabilities.get('browserVersion', 'Unknown')}")
            logger.info(f"ChromeDriver 버전: {driver.capabilities.get('chrome', {}).get('chromedriverVersion', 'Unknown')}")
            
            return driver
            
        except Exception as e:
            logger.warning(f"Chrome 드라이버 초기화 실패 (시도 {attempt + 1}/{max_retries}): {e}")
            
            if attempt < max_retries - 1:
                logger.info(f"{retry_delay}초 후 재시도...")
                time.sleep(retry_delay)
                continue
            
            # 모든 재시도가 실패한 경우
            logger.error(f"Chrome 드라이버 초기화 최종 실패: {e}")
            
            # 대체 방법: 로컬 ChromeDriver 사용 시도
            try:
                local_driver_path = Path("chromedriver.exe")
                if local_driver_path.exists():
                    logger.info("로컬 ChromeDriver 사용 시도...")
                    driver = uc.Chrome(
                        options=options,
                        driver_executable_path=str(local_driver_path),
                        version_main=None,
                        suppress_welcome=True
                    )
                    
                    # 드라이버 유효성 검증
                    if driver and hasattr(driver, 'set_page_load_timeout'):
                        driver.set_page_load_timeout(30)
                        return driver
                    else:
                        raise Exception("로컬 ChromeDriver도 유효하지 않습니다.")
            except Exception as local_e:
                logger.error(f"로컬 ChromeDriver 사용 실패: {local_e}")
            
            raise Exception(f"Chrome 드라이버를 초기화할 수 없습니다: {e}")


def cleanup_chrome_processes():
    """
    남아있는 Chrome 프로세스 정리
    """
    try:
        import psutil
        
        for proc in psutil.process_iter(['pid', 'name']):
            if 'chrome' in proc.info['name'].lower():
                try:
                    proc.kill()
                except Exception as e:
                    logger.debug(f"Chrome 프로세스 종료 실패: {e}")
    except ImportError:
        logger.warning("psutil이 설치되지 않아 Chrome 프로세스 정리를 건너뜁니다.")
    except Exception as e:
        logger.error(f"Chrome 프로세스 정리 중 오류: {e}")