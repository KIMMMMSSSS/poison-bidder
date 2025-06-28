#!/usr/bin/env python3
"""
ChromeDriver 자동 관리 설정
Chrome 버전에 관계없이 항상 작동하도록 설정
"""

import os
import logging
import undetected_chromedriver as uc
from pathlib import Path

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
    
    if disable_gpu:
        options.add_argument("--disable-gpu")
    
    if headless:
        options.add_argument("--headless")
    
    # 사용자 데이터 디렉토리 설정 (선택사항)
    # user_data_dir = Path("chrome_data/default")
    # user_data_dir.mkdir(parents=True, exist_ok=True)
    # options.add_argument(f"--user-data-dir={user_data_dir.absolute()}")
    
    try:
        # version_main=None으로 설정하면 현재 설치된 Chrome 버전을 자동 감지
        driver = uc.Chrome(
            options=options,
            version_main=None,  # 자동 버전 감지
            driver_executable_path=None,  # 자동 다운로드 경로 사용
            use_subprocess=True  # 서브프로세스로 실행 (안정성 향상)
        )
        
        logger.info(f"Chrome 드라이버 초기화 성공")
        logger.info(f"Chrome 버전: {driver.capabilities.get('browserVersion', 'Unknown')}")
        logger.info(f"ChromeDriver 버전: {driver.capabilities.get('chrome', {}).get('chromedriverVersion', 'Unknown')}")
        
        return driver
        
    except Exception as e:
        logger.error(f"Chrome 드라이버 초기화 실패: {e}")
        
        # 대체 방법: 로컬 ChromeDriver 사용 시도
        try:
            local_driver_path = Path("chromedriver.exe")
            if local_driver_path.exists():
                logger.info("로컬 ChromeDriver 사용 시도...")
                driver = uc.Chrome(
                    options=options,
                    driver_executable_path=str(local_driver_path),
                    version_main=None
                )
                return driver
        except:
            pass
            
        raise


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
                except