#!/usr/bin/env python3
"""
포이즌 입찰 Wrapper V2
0923_fixed_multiprocess_cookie_v2.py의 실제 로직을 활용하는 래퍼
"""

import os
import sys
import json
import logging
import importlib.util
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from multiprocessing import Manager, Process
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


def log_processor_worker(result_queue, result_list_queue):
    """로그 처리 워커 프로세스 (모듈 레벨 함수)"""
    results = []
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
                results.append(content)
            elif msg_type == "TERMINATE":
                # 종료 시 결과 반환
                result_list_queue.put(('results', results))
                result_list_queue.put(('fail_logs', fail_logs))
                break
        except:
            continue


class PoizonBidderWrapperV2:
    """포이즌 입찰 래퍼 V2 - 원본 파일의 실제 로직 활용"""
    
    def __init__(self, driver_path: str = None, min_profit: int = 0, worker_count: int = 5):
        """
        초기화
        
        Args:
            driver_path: Chrome 드라이버 경로 (None이면 자동 탐색)
            min_profit: 최소 예상 수익
            worker_count: 동시 실행 워커 수
        """
        self.driver_path = driver_path or self._find_chromedriver()
        self.min_profit = min_profit
        self.worker_count = worker_count
        self.module = None
        
        # 원본 모듈 로드
        self._load_original_module()
        
        logger.info(f"PoizonBidderWrapperV2 초기화 - 최소수익: {min_profit}, 워커수: {worker_count}")
    
    def _find_chromedriver(self) -> str:
        """Chrome 드라이버 자동 탐색"""
        # 일반적인 위치들
        possible_paths = [
            "chromedriver.exe",
            "C:/chromedriver/chromedriver.exe",
            "C:/poison_final/chromedriver.exe",
            str(Path.home() / "Downloads" / "chromedriver.exe"),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                logger.info(f"Chrome 드라이버 발견: {path}")
                return path
                
        # 못 찾으면 기본값
        return "chromedriver.exe"
    
    def _load_original_module(self):
        """원본 모듈 동적 로드"""
        try:
            original_file = Path('C:/poison_final/0923_fixed_multiprocess_cookie_v2.py')
            if not original_file.exists():
                raise FileNotFoundError(f"원본 파일을 찾을 수 없습니다: {original_file}")
            
            # 모듈 동적 로드
            spec = importlib.util.spec_from_file_location("multiprocess_cookie", original_file)
            self.module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self.module)
            
            logger.info("원본 모듈 로드 성공")
            
        except Exception as e:
            logger.error(f"원본 모듈 로드 실패: {e}")
            raise
    
    def prepare_bid_data(self, items: List[Dict[str, Any]]) -> List[Tuple]:
        """
        통합 시스템의 데이터를 포이즌 입찰 형식으로 변환
        
        Args:
            items: unified_bidding이나 auto_bidding에서 온 아이템 리스트
            
        Returns:
            포이즌 입찰 형식의 튜플 리스트
        """
        bid_data = []
        
        logger.debug(f"데이터 변환 시작: {len(items)}개 아이템")
        if items and logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"첫 번째 아이템 샘플: {json.dumps(items[0], ensure_ascii=False)}")
        
        for idx, item in enumerate(items, 1):
            # 데이터 추출
            brand = item.get('brand', '')
            code = item.get('code', '')
            color = item.get('color', '')
            size = item.get('size', '')
            price = item.get('adjusted_price', item.get('price', 0))
            
            # 포이즌 형식으로 변환
            bid_data.append((
                idx,
                brand,
                code,
                color,
                size,
                price
            ))
            
        logger.info(f"데이터 변환 완료: {len(bid_data)}개 아이템")
        if bid_data and logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"변환된 첫 번째 튜플: {bid_data[0]}")
        return bid_data
    
    def run_bidding(self, bid_data_file: Optional[str] = None, 
                   bid_data_list: Optional[List[Tuple]] = None,
                   unified_items: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        입찰 실행
        
        Args:
            bid_data_file: 입찰 데이터 파일 경로
            bid_data_list: 입찰 데이터 리스트 [(idx, brand, code, color, size, cost), ...]
            unified_items: unified_bidding/auto_bidding에서 온 아이템 리스트
            
        Returns:
            입찰 결과 딕셔너리
        """
        start_time = datetime.now()
        logger.info("=== 포이즌 입찰 시작 ===")
        
        # 입력 확인
        logger.info(f"입력 파라미터 - bid_data_file: {bid_data_file is not None}, "
                   f"bid_data_list: {bid_data_list is not None}, "
                   f"unified_items: {unified_items is not None}")
        
        # 데이터 준비
        if unified_items:
            # 통합 시스템 데이터를 변환
            logger.info(f"unified_items로부터 데이터 변환 시작: {len(unified_items)}개")
            raw_data = self.prepare_bid_data(unified_items)
        elif bid_data_file:
            # 파일에서 로드 (원본 함수 사용)
            bidder = self.module.PoizonAutoBidderMultiProcess()
            raw_data = bidder.load_bid_data(bid_data_file)
        elif bid_data_list:
            raw_data = bid_data_list
        else:
            raise ValueError("bid_data_file, bid_data_list, unified_items 중 하나는 제공되어야 합니다")
        
        if not raw_data:
            return {
                'status': 'error',
                'message': '입력 데이터가 없습니다',
                'timestamp': datetime.now().isoformat()
            }
        
        # 원본의 실행 로직을 활용하되 GUI 부분만 우회
        try:
            # 로그 파일 초기화
            if os.path.exists(self.module.LOGFILE):
                os.remove(self.module.LOGFILE)
            
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
            
            # 결과 수집을 위한 큐 추가
            result_list_queue = manager.Queue()
            
            # 로그 수집 프로세스 (모듈 레벨 함수 사용)
            log_proc = Process(target=log_processor_worker, args=(result_queue, result_list_queue))
            log_proc.daemon = True
            log_proc.start()
            
            # 워커 프로세스들 시작 (원본의 worker_process 사용)
            workers = []
            for i in range(1, self.worker_count + 1):
                worker = Process(
                    target=self.module.worker_process,
                    args=(i, task_queue, result_queue, status_dict, login_complete, 
                          self.min_profit, self.driver_path, stats)
                )
                workers.append(worker)
                worker.start()
                
                # 첫 번째 워커 시작 후 대기
                if i == 1:
                    logger.info("첫 번째 워커에서 로그인 진행 중...")
                    import time
                    time.sleep(5)
            
            # 모든 워커 종료 대기
            for worker in workers:
                worker.join()
            
            # 로그 수집 종료
            result_queue.put(("TERMINATE", None))
            log_proc.join()
            
            # 결과 수집
            results = []
            fail_logs = []
            while not result_list_queue.empty():
                data_type, data = result_list_queue.get()
                if data_type == 'results':
                    results = data
                elif data_type == 'fail_logs':
                    fail_logs = data
            
            # 실행 시간 계산
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # 실패 로그 저장
            if fail_logs:
                with open(self.module.LOGFILE, 'w', encoding='utf-8') as f:
                    for log in fail_logs:
                        f.write(log + "\n")
                logger.info(f"실패 로그 저장: {self.module.LOGFILE}")
            
            # 최종 결과
            return {
                'status': 'success',
                'total_codes': len(groups),
                'total_items': len(raw_data),
                'completed': stats.get('completed', 0),
                'success': stats.get('success', 0),
                'failed': stats.get('failed', 0),
                'execution_time': execution_time,
                'timestamp': datetime.now().isoformat(),
                'details': results,
                'fail_log_path': self.module.LOGFILE if fail_logs else None
            }
            
        except Exception as e:
            logger.error(f"입찰 실행 중 오류: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            return {
                'status': 'error',
                'message': str(e),
                'timestamp': datetime.now().isoformat()
            }


# 테스트용
if __name__ == "__main__":
    # 테스트 데이터
    test_data = [
        (1, "나이키", "ABC123", "BLACK", "270", 50000),
        (2, "나이키", "ABC123", "WHITE", "275", 50000),
        (3, "아디다스", "DEF456", "RED", "280", 60000),
    ]
    
    # Wrapper 인스턴스 생성
    wrapper = PoizonBidderWrapperV2(
        min_profit=5000,
        worker_count=2
    )
    
    # 입찰 실행
    result = wrapper.run_bidding(bid_data_list=test_data)
    
    # 결과 출력
    print("\n=== 입찰 결과 ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))
