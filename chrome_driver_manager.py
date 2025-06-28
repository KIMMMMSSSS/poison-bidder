#!/usr/bin/env python3
"""
통합 Chrome 드라이버 관리 시스템
기존 check_chrome_version.py, download_chromedriver.py, fix_chromedriver_issue.py의 기능을 통합
"""

import os
import sys
import subprocess
import re
import requests
import zipfile
import shutil
import platform
import logging
from pathlib import Path
from typing import Optional, Tuple

# 로깅 설정
logger = logging.getLogger(__name__)


class ChromeDriverManager:
    """Chrome 브라우저와 ChromeDriver 버전을 자동으로 관리하는 통합 클래스"""
    
    def __init__(self, driver_dir: str = "C:/poison_final"):
        """
        Args:
            driver_dir: ChromeDriver를 저장할 디렉토리
        """
        self.driver_dir = Path(driver_dir)
        self.driver_path = self.driver_dir / "chromedriver.exe"
        self.chrome_version = None
        self.driver_version = None
        
    def get_chrome_version(self) -> Optional[str]:
        """설치된 Chrome 브라우저 버전 확인"""
        if platform.system() != "Windows":
            logger.error("Windows가 아닌 시스템은 현재 지원하지 않습니다.")
            return None
            
        # Windows에서 Chrome 버전 확인
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")
        ]
        
        for chrome_path in chrome_paths:
            if os.path.exists(chrome_path):
                try:
                    # Chrome 버전 가져오기
                    result = subprocess.run(
                        [chrome_path, '--version'],
                        capture_output=True,
                        text=True,
                        creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
                    )
                    version_match = re.search(r'(\d+\.\d+\.\d+\.\d+)', result.stdout)
                    if version_match:
                        self.chrome_version = version_match.group(1)
                        logger.info(f"Chrome 브라우저 버전: {self.chrome_version}")
                        return self.chrome_version
                except Exception as e:
                    logger.error(f"Chrome 버전 확인 실패: {e}")
                    
        # Registry에서 버전 확인 (대체 방법)
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\BLBeacon")
            version, _ = winreg.QueryValueEx(key, "version")
            winreg.CloseKey(key)
            self.chrome_version = version
            logger.info(f"Chrome 브라우저 버전 (Registry): {self.chrome_version}")
            return self.chrome_version
        except Exception:
            pass
            
        logger.warning("Chrome 브라우저를 찾을 수 없습니다.")
        return None
        
    def get_chromedriver_version(self) -> Optional[str]:
        """현재 ChromeDriver 버전 확인"""
        if self.driver_path.exists():
            try:
                result = subprocess.run(
                    [str(self.driver_path), '--version'],
                    capture_output=True,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
                )
                version_match = re.search(r'(\d+\.\d+\.\d+\.\d+)', result.stdout)
                if version_match:
                    self.driver_version = version_match.group(1)
                    logger.info(f"ChromeDriver 버전: {self.driver_version}")
                    return self.driver_version
            except Exception as e:
                logger.error(f"ChromeDriver 버전 확인 실패: {e}")
                
        return None
        
    def clear_cache(self):
        """undetected-chromedriver 캐시 정리"""
        logger.info("undetected-chromedriver 캐시 정리 중...")
        
        uc_dirs = [
            os.path.join(os.environ.get('APPDATA', ''), 'undetected_chromedriver'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'undetected_chromedriver'),
            os.path.join(os.path.expanduser('~'), '.undetected_chromedriver'),
        ]
        
        for uc_dir in uc_dirs:
            if os.path.exists(uc_dir):
                try:
                    shutil.rmtree(uc_dir)
                    logger.info(f"캐시 삭제 완료: {uc_dir}")
                except Exception as e:
                    logger.warning(f"캐시 삭제 실패: {uc_dir} - {e}")
                    
    def download_chromedriver_manually(self, chrome_version: str) -> bool:
        """Chrome 버전에 맞는 ChromeDriver 수동 다운로드"""
        logger.info(f"ChromeDriver 수동 다운로드 시작 (Chrome {chrome_version})")
        
        major_version = chrome_version.split('.')[0]
        
        # Chrome 137 이상의 경우 새로운 URL 구조 사용
        if int(major_version) >= 137:
            # Chrome for Testing 엔드포인트 사용
            try:
                # 버전별 다운로드 URL 확인
                endpoint_url = f"https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_{major_version}"
                response = requests.get(endpoint_url, timeout=10)
                if response.status_code == 200:
                    driver_version = response.text.strip()
                else:
                    # 대체 버전 사용
                    driver_version = "131.0.6778.33"
                    
                # 새로운 URL 구조
                driver_url = f"https://storage.googleapis.com/chrome-for-testing-public/{driver_version}/win64/chromedriver-win64.zip"
                
            except Exception as e:
                logger.warning(f"버전 정보 가져오기 실패: {e}")
                # 최신 안정 버전 사용
                driver_version = "131.0.6778.33"
                driver_url = f"https://storage.googleapis.com/chrome-for-testing-public/{driver_version}/win64/chromedriver-win64.zip"
        else:
            # Chrome 136 이하의 경우 기존 URL 구조 사용
            try:
                download_url = f"https://chromedriver.storage.googleapis.com/LATEST_RELEASE_{major_version}"
                response = requests.get(download_url, timeout=10)
                driver_version = response.text.strip()
                driver_url = f"https://chromedriver.storage.googleapis.com/{driver_version}/chromedriver_win32.zip"
            except:
                logger.error("구 버전 ChromeDriver URL 접근 실패")
                return False
                
        # 다운로드
        try:
            logger.info(f"다운로드 URL: {driver_url}")
            response = requests.get(driver_url, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"다운로드 실패. 상태 코드: {response.status_code}")
                return False
                
            # 임시 파일로 저장
            zip_path = self.driver_dir / "chromedriver_temp.zip"
            with open(zip_path, 'wb') as f:
                f.write(response.content)
                
            # 기존 드라이버 백업
            if self.driver_path.exists():
                backup_path = self.driver_dir / "chromedriver_backup.exe"
                shutil.move(str(self.driver_path), str(backup_path))
                logger.info("기존 ChromeDriver 백업 완료")
                
            # 압축 해제
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # 새로운 ChromeDriver 구조 확인
                for name in zip_ref.namelist():
                    if name.endswith('chromedriver.exe'):
                        # chromedriver.exe만 추출
                        zip_ref.extract(name, str(self.driver_dir / "temp"))
                        # 파일 이동
                        temp_driver = self.driver_dir / "temp" / name
                        shutil.move(str(temp_driver), str(self.driver_path))
                        # 임시 폴더 정리
                        shutil.rmtree(str(self.driver_dir / "temp"), ignore_errors=True)
                        break
                else:
                    # 기존 방식 (chromedriver.exe가 루트에 있는 경우)
                    zip_ref.extractall(str(self.driver_dir))
                    
            # zip 파일 삭제
            zip_path.unlink()
            
            logger.info(f"ChromeDriver {driver_version} 다운로드 완료!")
            return True
            
        except Exception as e:
            logger.error(f"ChromeDriver 다운로드 중 오류: {e}")
            return False
            
    def ensure_driver(self) -> Optional[str]:
        """Chrome 드라이버 확보 (자동 관리)"""
        try:
            # 1. Chrome 버전 확인
            chrome_version = self.get_chrome_version()
            if not chrome_version:
                logger.error("Chrome 브라우저가 설치되지 않았습니다.")
                return None
                
            # 2. 현재 ChromeDriver 버전 확인
            driver_version = self.get_chromedriver_version()
            
            # 3. 버전 호환성 확인
            if chrome_version and driver_version:
                chrome_major = chrome_version.split('.')[0]
                driver_major = driver_version.split('.')[0]
                
                if chrome_major == driver_major:
                    logger.info(f"버전 호환성 OK! (메이저 버전 {chrome_major} 일치)")
                    return str(self.driver_path)
                else:
                    logger.warning(f"버전 불일치! Chrome: {chrome_major}, Driver: {driver_major}")
                    
            # 4. webdriver-manager로 시도
            try:
                logger.info("webdriver-manager를 사용하여 ChromeDriver 다운로드 시도...")
                from webdriver_manager.chrome import ChromeDriverManager as WDM
                
                # 캐시 정리
                self.clear_cache()
                
                # webdriver-manager로 다운로드
                wdm_path = WDM().install()
                
                # 현재 디렉토리로 복사
                if os.path.exists(wdm_path) and wdm_path != str(self.driver_path):
                    shutil.copy2(wdm_path, str(self.driver_path))
                    logger.info(f"ChromeDriver 복사 완료: {self.driver_path}")
                    
                return str(self.driver_path)
                
            except Exception as e:
                logger.warning(f"webdriver-manager 실패: {e}")
                
                # 5. 수동 다운로드 시도
                if self.download_chromedriver_manually(chrome_version):
                    return str(self.driver_path)
                else:
                    logger.error("ChromeDriver 자동 설치 실패")
                    return None
                    
        except Exception as e:
            logger.error(f"ChromeDriver 관리 중 오류: {e}")
            return None
            
    def test_driver(self) -> bool:
        """Chrome 드라이버 테스트"""
        logger.info("Chrome 드라이버 테스트 시작...")
        
        try:
            # undetected-chromedriver 우선 시도
            import undetected_chromedriver as uc
            
            options = uc.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            
            # version_main에 Chrome 메이저 버전 전달
            chrome_version = self.get_chrome_version()
            if chrome_version:
                major_version = int(chrome_version.split('.')[0])
                logger.info(f"Chrome {major_version} 감지, 해당 버전용 드라이버 사용")
                driver = uc.Chrome(options=options, version_main=major_version)
            else:
                driver = uc.Chrome(options=options, version_main=None)
            driver.get("https://www.google.com")
            title = driver.title
            driver.quit()
            
            logger.info(f"undetected-chromedriver 테스트 성공! (페이지: {title})")
            return True
            
        except Exception as e:
            logger.warning(f"undetected-chromedriver 테스트 실패: {e}")
            
            # selenium webdriver로 재시도
            try:
                from selenium import webdriver
                from selenium.webdriver.chrome.service import Service
                
                options = webdriver.ChromeOptions()
                options.add_argument('--headless')
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                
                service = Service(str(self.driver_path))
                driver = webdriver.Chrome(service=service, options=options)
                driver.get("https://www.google.com")
                title = driver.title
                driver.quit()
                
                logger.info(f"selenium webdriver 테스트 성공! (페이지: {title})")
                return True
                
            except Exception as e2:
                logger.error(f"selenium webdriver 테스트도 실패: {e2}")
                return False
                

def get_chrome_version() -> Optional[str]:
    """설치된 Chrome 브라우저 버전 확인 (헬퍼 함수)"""
    manager = ChromeDriverManager()
    return manager.get_chrome_version()


def initialize_chrome_driver(worker_id: int = 1, headless: bool = True, use_undetected: bool = True, extra_options: list = None):
    """
    Chrome 드라이버 초기화 헬퍼 함수
    poison_bidder_wrapper_v2.py에서 쉽게 사용할 수 있도록 제공
    
    Args:
        worker_id: 워커 ID (로깅용)
        headless: 헤드리스 모드 여부
        use_undetected: undetected-chromedriver 사용 여부 (기본값: True)
        extra_options: 추가 Chrome 옵션 리스트 (선택사항)
        
    Returns:
        driver: 초기화된 Chrome 드라이버 객체
    """
    manager = ChromeDriverManager()
    driver_path = manager.ensure_driver()
    
    if not driver_path:
        raise Exception("ChromeDriver 초기화 실패")
        
    # undetected-chromedriver 우선 사용
    if use_undetected:
        try:
            import undetected_chromedriver as uc
            
            options = uc.ChromeOptions()
            if headless:
                options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--window-size=1920,1080')
            
            # 메모리 최적화 옵션들
            options.add_argument('--disable-logging')
            options.add_argument('--log-level=3')
            options.add_argument('--silent')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-software-rasterizer')
            options.add_argument('--disable-background-timer-throttling')
            options.add_argument('--disable-backgrounding-occluded-windows')
            options.add_argument('--disable-renderer-backgrounding')
            options.add_argument('--disable-features=TranslateUI')
            options.add_argument('--disable-ipc-flooding-protection')
            
            # 추가 옵션 적용
            if extra_options:
                for option in extra_options:
                    options.add_argument(option)
            
            # Chrome 버전 확인하여 메이저 버전 전달
            chrome_version = manager.get_chrome_version()
            if chrome_version:
                major_version = int(chrome_version.split('.')[0])
                logger.info(f"[Worker {worker_id}] Chrome {major_version} 감지, 해당 버전용 드라이버 사용")
                driver = uc.Chrome(options=options, version_main=major_version)
            else:
                driver = uc.Chrome(options=options, version_main=None)
            
            logger.info(f"[Worker {worker_id}] undetected-chromedriver 초기화 성공")
            return driver
            
        except Exception as e:
            logger.warning(f"[Worker {worker_id}] undetected-chromedriver 실패: {e}")
        
        # fallback to selenium
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        
        # 동일한 메모리 최적화 옵션
        options.add_argument('--disable-logging')
        options.add_argument('--log-level=3')
        options.add_argument('--disable-gpu')
        
        # 추가 옵션 적용
        if extra_options:
            for option in extra_options:
                options.add_argument(option)
        
        service = Service(driver_path)
        driver = webdriver.Chrome(service=service, options=options)
        logger.info(f"[Worker {worker_id}] selenium webdriver 초기화 성공")
        return driver


# 메인 실행 시 테스트
if __name__ == "__main__":
    print("=" * 60)
    print("Chrome 드라이버 통합 관리 시스템 테스트")
    print("=" * 60)
    
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )
    
    # ChromeDriverManager 인스턴스 생성
    manager = ChromeDriverManager()
    
    # 드라이버 확보
    driver_path = manager.ensure_driver()
    
    if driver_path:
        print(f"\n✅ ChromeDriver 준비 완료: {driver_path}")
        
        # 테스트 실행
        if manager.test_driver():
            print("\n✅ Chrome 드라이버 테스트 성공!")
        else:
            print("\n❌ Chrome 드라이버 테스트 실패")
    else:
        print("\n❌ ChromeDriver 준비 실패")
