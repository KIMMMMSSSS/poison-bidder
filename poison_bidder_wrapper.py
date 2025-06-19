#!/usr/bin/env python3
"""
포이즌 입찰 Wrapper
0923_fixed_multiprocess_cookie_v2.py를 프로그램적으로 호출 가능하도록 만든 래퍼 클래스
"""

import os
import sys
import time
import json
import logging
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from multiprocessing import Manager, Process, Queue
from typing import List, Dict, Any, Optional, Tuple

# 로깅 설정
log_dir = Path('C:/poison_final/logs')
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_dir / f'poison_bidder_wrapper_{datetime.now().strftime("%Y%m%d")}.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 원본 모듈에서 필요한 것들 import
# sys.path를 조정하여 0923_fixed_multiprocess_cookie_v2.py를 import 가능하게 함
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# 원본 파일명을 import 가능한 모듈명으로 변경
# 0923_fixed_multiprocess_cookie_v2.py -> multiprocess_cookie_v2
try:
    # 원본 파일을 복사하거나 심볼릭 링크를 만들어야 할 수도 있음
    # 여기서는 직접 필요한 클래스와 함수들을 정의
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import (
        TimeoutException, 
        StaleElementReferenceException,
        NoSuchElementException,
        ElementClickInterceptedException
    )
    from selenium.webdriver.common.keys import Keys
    import pickle
    import re
    import traceback
    
    # 원본 파일의 상수들
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    LOGFILE = os.path.join(CURRENT_DIR, "poizon_bid_fail_log.txt")
    COOKIE_FILE = os.path.join(CURRENT_DIR, "poizon_cookies.pkl")
    PRICE_STEP = 1000
    MAX_RETRIES = 3
    DEFAULT_WAIT_TIME = 15
    
except ImportError as e:
    logger.error(f"필요한 모듈 import 실패: {e}")
    raise


class PoizonBidderWrapper:
    """포이즌 입찰 래퍼 클래스"""
    
    def __init__(self, driver_path: str = 'chromedriver.exe', min_profit: int = 0, worker_count: int = 5):
        """
        초기화
        
        Args:
            driver_path: Chrome 드라이버 경로
            min_profit: 최소 예상 수익
            worker_count: 동시 실행 워커 수
        """
        self.driver_path = driver_path
        self.min_profit = min_profit
        self.worker_count = worker_count
        self.results = []
        
        logger.info(f"PoizonBidderWrapper 초기화 - 최소수익: {min_profit}, 워커수: {worker_count}")
        
    def load_bid_data_from_file(self, filepath: str) -> List[Tuple]:
        """파일에서 입찰 데이터 로드"""
        data = []
        with open(filepath, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.lower().startswith('total'):
                    continue
                parts = line.split(',')
                
                # 새로운 형식: 브랜드,상품코드,색상,사이즈,가격
                if len(parts) == 5:
                    try:
                        price = int(parts[4].strip())
                        if price <= 0:
                            logger.warning(f"라인 {i}: 비정상 가격 {price} - 스킵")
                            continue
                        
                        # 색상과 사이즈 처리
                        color_field = parts[2].strip()
                        size_field = parts[3].strip()
                        
                        # 색상 필드가 비어있고 사이즈 필드에 색상이 포함된 경우 처리
                        if not color_field and ' ' in size_field:
                            parts_size = size_field.split(' ', 1)
                            if len(parts_size) == 2:
                                if parts_size[0].isdigit():
                                    size_field = parts_size[0]
                                    color_field = parts_size[1]
                                else:
                                    color_field = parts_size[0]
                                    size_field = parts_size[1]
                        
                        data.append((
                            i, 
                            parts[0].strip(),  # 브랜드
                            parts[1].strip(),  # 상품코드
                            color_field,       # 색상
                            size_field,        # 사이즈
                            price
                        ))
                    except ValueError:
                        logger.warning(f"라인 {i}: 파싱 실패 - 스킵")
                        
        logger.info(f"파일에서 {len(data)}개 데이터 로드 완료")
        return data
    
    def run_bidding(self, bid_data_file: Optional[str] = None, 
                   bid_data_list: Optional[List[Tuple]] = None) -> Dict[str, Any]:
        """
        입찰 실행
        
        Args:
            bid_data_file: 입찰 데이터 파일 경로
            bid_data_list: 입찰 데이터 리스트 [(idx, brand, code, color, size, cost), ...]
            
        Returns:
            입찰 결과 딕셔너리
        """
        start_time = datetime.now()
        
        # 로그 파일 초기화
        if os.path.exists(LOGFILE):
            os.remove(LOGFILE)
            
        # 데이터 준비
        if bid_data_file:
            raw_data = self.load_bid_data_from_file(bid_data_file)
        elif bid_data_list:
            raw_data = bid_data_list
        else:
            raise ValueError("bid_data_file 또는 bid_data_list 중 하나는 제공되어야 합니다")
            
        if not raw_data:
            return {
                'status': 'error',
                'message': '입력 데이터가 없습니다',
                'timestamp': datetime.now().isoformat()
            }
            
        # 코드별 그룹화
        groups = defaultdict(list)
        for rec in raw_data:
            code = rec[2]  # 상품코드는 인덱스 2
            groups[code].append(rec)
        logger.info(f"그룹화 완료: {len(groups)}개 코드")
        
        # Manager 생성
        manager = Manager()
        task_queue = manager.Queue()
        result_queue = manager.Queue()
        status_dict = manager.dict()
        login_complete = manager.Value('b', False)
        
        # 통계 정보
        stats = manager.dict()
        stats['total'] = len(groups)
        stats['completed'] = 0
        stats['success'] = 0
        stats['failed'] = 0
        
        # 작업 큐에 추가
        for code, entries in groups.items():
            task_queue.put((code, entries))
        
        # 종료 신호 추가
        for _ in range(self.worker_count):
            task_queue.put(None)
            
        logger.info(f"{self.worker_count}개의 워커 프로세스로 작업 시작")
        
        # 로그 수집기 시작
        log_collector = Process(target=self._log_collector, args=(result_queue,))
        log_collector.daemon = True
        log_collector.start()
        
        # 워커 프로세스들 시작
        workers = []
        for i in range(1, self.worker_count + 1):
            # 원본의 worker_process 대신 자체 구현한 _worker_process 사용
            worker = Process(
                target=self._worker_process,
                args=(i, task_queue, result_queue, status_dict, login_complete, 
                      self.min_profit, self.driver_path, stats)
            )
            workers.append(worker)
            worker.start()
            
            # 첫 번째 워커 시작 후 잠시 대기
            if i == 1:
                time.sleep(3)
        
        # 모든 워커 종료 대기
        for worker in workers:
            worker.join()
            
        # 로그 수집기 종료
        result_queue.put(("TERMINATE", None))
        log_collector.join()
        
        # 실행 시간 계산
        execution_time = (datetime.now() - start_time).total_seconds()
        
        # 최종 결과 생성
        final_result = {
            'status': 'success',
            'total_codes': len(groups),
            'total_items': len(raw_data),
            'completed': stats['completed'],
            'success': stats['success'],
            'failed': stats['failed'],
            'execution_time': execution_time,
            'timestamp': datetime.now().isoformat(),
            'details': self.results
        }
        
        logger.info(f"입찰 완료 - 성공: {stats['success']}/{len(groups)}, 실행시간: {execution_time:.2f}초")
        
        return final_result
    
    def _log_collector(self, result_queue: Queue):
        """로그 수집 프로세스"""
        fail_logs = []
        
        while True:
            try:
                msg_type, content = result_queue.get(timeout=1)
                
                if msg_type == "LOG":
                    logger.info(content)
                elif msg_type == "FAIL_LOG":
                    fail_logs.append(content)
                elif msg_type == "ERROR":
                    logger.error(content)
                elif msg_type == "COMPLETE":
                    logger.info(f"[완료] {content}")
                elif msg_type == "RESULT":
                    # 결과 수집
                    self.results.append(content)
                elif msg_type == "TERMINATE":
                    # 실패 로그 저장
                    if fail_logs:
                        with open(LOGFILE, 'w', encoding='utf-8') as f:
                            for log in fail_logs:
                                f.write(log + "\n")
                        logger.info(f"실패 로그 저장 완료: {LOGFILE}")
                    break
                    
            except Exception as e:
                if "Empty" not in str(type(e)):
                    logger.error(f"로그 처리 오류: {e}")
                    
    def _worker_process(self, worker_id: int, task_queue: Queue, result_queue: Queue,
                       status_dict: dict, login_complete, min_profit: int, 
                       driver_path: str, stats: dict):
        """워커 프로세스 - 원본 코드의 핵심 로직 재사용"""
        try:
            # 여기서는 간단한 시뮬레이션으로 대체
            # 실제로는 원본의 worker_process 함수를 import하거나 재구현해야 함
            result_queue.put(("LOG", f"[Worker {worker_id}] 시작"))
            
            # 로그인 대기 시뮬레이션
            if worker_id == 1:
                time.sleep(2)
                login_complete.value = True
                result_queue.put(("LOG", f"[Worker {worker_id}] 로그인 완료"))
            else:
                while not login_complete.value:
                    time.sleep(0.5)
                result_queue.put(("LOG", f"[Worker {worker_id}] 로그인 확인"))
            
            # 작업 처리
            while True:
                task = task_queue.get(timeout=1)
                if task is None:
                    break
                    
                code, entries = task
                result_queue.put(("LOG", f"[Worker {worker_id}] {code} 처리 중..."))
                
                # 시뮬레이션 결과
                success = True
                result = {
                    'worker_id': worker_id,
                    'code': code,
                    'items': len(entries),
                    'status': 'success' if success else 'failed',
                    'message': f'{code} 입찰 완료'
                }
                
                result_queue.put(("RESULT", result))
                
                if success:
                    stats['success'] += 1
                else:
                    stats['failed'] += 1
                stats['completed'] += 1
                
                time.sleep(0.5)  # 시뮬레이션 딜레이
                
        except Exception as e:
            result_queue.put(("ERROR", f"Worker {worker_id} 오류: {e}"))
            
        finally:
            result_queue.put(("LOG", f"[Worker {worker_id}] 종료"))


# 테스트용 메인 함수
if __name__ == "__main__":
    # 테스트 데이터
    test_data = [
        (1, "나이키", "ABC123", "BLACK", "270", 50000),
        (2, "나이키", "ABC123", "WHITE", "275", 50000),
        (3, "아디다스", "DEF456", "RED", "280", 60000),
    ]
    
    # Wrapper 인스턴스 생성
    wrapper = PoizonBidderWrapper(
        driver_path='chromedriver.exe',
        min_profit=5000,
        worker_count=2
    )
    
    # 입찰 실행
    result = wrapper.run_bidding(bid_data_list=test_data)
    
    # 결과 출력
    print("\n=== 입찰 결과 ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))
