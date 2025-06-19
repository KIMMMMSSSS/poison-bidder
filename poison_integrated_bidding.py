#!/usr/bin/env python3
"""
포이즌 통합 입찰 시스템
poison_direct_login.py를 활용한 완전 자동화
"""

import os
import sys
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

# 포이즌 직접 로그인 import
from poison_direct_login import login_to_poison

# 포이즌 입찰 Wrapper import
from poison_bidder_wrapper_v2 import PoizonBidderWrapperV2

# 로깅 설정
log_dir = Path('C:/poison_final/logs')
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_dir / f'poison_integrated_{datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class PoisonIntegratedBidding:
    """포이즌 통합 입찰 클래스"""
    
    def __init__(self):
        self.driver = None
        self.is_logged_in = False
        
    def initialize(self):
        """포이즌 로그인 초기화"""
        logger.info("포이즌 입찰 시스템 초기화...")
        
        try:
            # poison_direct_login.py의 함수 사용
            self.driver = login_to_poison()
            self.is_logged_in = True
            logger.info("✅ 포이즌 로그인 성공!")
            return True
            
        except Exception as e:
            logger.error(f"로그인 실패: {e}")
            return False
    
    def execute_bid(self, product_url: str, bid_price: int, size: str = None) -> Dict[str, Any]:
        """
        입찰 실행
        
        Args:
            product_url: 포이즌 상품 URL
            bid_price: 입찰 가격
            size: 사이즈 (옵션)
            
        Returns:
            입찰 결과
        """
        if not self.is_logged_in:
            return {
                'success': False,
                'message': '로그인이 필요합니다',
                'timestamp': datetime.now().isoformat()
            }
        
        try:
            logger.info(f"입찰 시작: {product_url}")
            logger.info(f"입찰가: {bid_price:,}원")
            
            # 상품 페이지로 이동
            self.driver.get(product_url)
            time.sleep(3)
            
            # TODO: 실제 입찰 로직 구현
            # 1. 사이즈 선택
            # 2. 가격 입력
            # 3. 입찰 버튼 클릭
            # 4. 확인
            
            # 현재는 시뮬레이션
            result = {
                'success': True,
                'product_url': product_url,
                'bid_price': bid_price,
                'size': size,
                'message': '입찰 성공 (시뮬레이션)',
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"✅ 입찰 완료: {result['message']}")
            return result
            
        except Exception as e:
            logger.error(f"입찰 중 오류: {e}")
            return {
                'success': False,
                'product_url': product_url,
                'message': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def batch_bidding(self, bid_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        배치 입찰 실행
        
        Args:
            bid_list: 입찰 목록 [{url, price, size}, ...]
            
        Returns:
            입찰 결과 목록
        """
        results = []
        
        for i, bid_item in enumerate(bid_list):
            logger.info(f"\n입찰 진행 중... {i+1}/{len(bid_list)}")
            
            result = self.execute_bid(
                product_url=bid_item.get('url'),
                bid_price=bid_item.get('price'),
                size=bid_item.get('size')
            )
            
            results.append(result)
            
            # 입찰 간 대기
            if i < len(bid_list) - 1:
                time.sleep(2)
        
        return results
    
    def close(self):
        """드라이버 종료"""
        if self.driver:
            self.driver.quit()
            logger.info("브라우저 종료")


# 기존 auto_bidding.py와 통합하는 어댑터
class AutoBiddingAdapter:
    """기존 auto_bidding.py와 통합 - 실제 포이즌 입찰 수행"""
    
    def __init__(self, driver_path: str = None, min_profit: int = 0, worker_count: int = 5):
        self.driver_path = driver_path
        self.min_profit = min_profit
        self.worker_count = worker_count
        self.poison_bidder = None
        
    def run_with_poison(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        포이즌으로 입찰 실행 - 실제 0923_fixed_multiprocess_cookie_v2.py 사용
        
        Args:
            items: auto_bidding.py에서 조정된 상품 목록
        """
        try:
            logger.info("포이즌 입찰 시작 (PoizonBidderWrapperV2 사용)")
            
            # PoizonBidderWrapper 인스턴스 생성
            self.poison_bidder = PoizonBidderWrapperV2(
                driver_path=self.driver_path,
                min_profit=self.min_profit,
                worker_count=self.worker_count
            )
            
            # 입찰 실행 (unified_items 파라미터 사용)
            result = self.poison_bidder.run_bidding(unified_items=items)
            
            # 결과 로깅
            logger.info(f"포이즌 입찰 완료 - 성공: {result.get('success', 0)}/{result.get('total_codes', 0)}")
            
            # 결과 형식 통일
            return {
                'status': result.get('status', 'error'),
                'total': result.get('total_codes', 0),
                'successful': result.get('success', 0),
                'failed': result.get('failed', 0),
                'results': self._convert_results(items, result.get('details', [])),
                'execution_time': result.get('execution_time', 0),
                'fail_log_path': result.get('fail_log_path')
            }
            
        except Exception as e:
            logger.error(f"포이즌 입찰 실행 중 오류: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            return {
                'status': 'error',
                'message': str(e),
                'total': 0,
                'successful': 0,
                'failed': len(items),
                'results': []
            }
    
    def _convert_results(self, items: List[Dict[str, Any]], bid_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        포이즌 입찰 결과를 통합 시스템 형식으로 변환
        """
        converted_results = []
        
        # 코드별로 결과 매핑
        code_results = {}
        for result in bid_results:
            code = result.get('code')
            if code:
                code_results[code] = result
        
        # 아이템별 결과 생성
        for item in items:
            code = item.get('code', '')
            result = code_results.get(code, {})
            
            # 각 아이템의 입찰 결과
            item_result = {
                'product_url': item.get('link', ''),
                'item_code': code,
                'brand': item.get('brand', ''),
                'size': item.get('size', ''),
                'color': item.get('color', ''),
                'bid_price': item.get('adjusted_price', item.get('price', 0)),
                'success': result.get('status') == 'success' if result else False,
                'message': result.get('message', '입찰 결과 없음'),
                'worker_id': result.get('worker_id'),
                'timestamp': datetime.now().isoformat()
            }
            
            converted_results.append(item_result)
        
        return converted_results


# unified_bidding.py와 통합
def integrate_with_unified_bidding():
    """unified_bidding.py의 _execute_bidding 메서드 대체"""
    
    def _execute_bidding_with_poison(self, site: str, items: List[Dict[str, Any]], exec_mode: str) -> List[Dict[str, Any]]:
        """포이즌 입찰 실행"""
        
        adapter = AutoBiddingAdapter()
        result = adapter.run_with_poison(items)
        
        # 결과 형식 변환
        bid_results = []
        for item, res in zip(items, result.get('results', [])):
            bid_results.append({
                'item_code': item.get('code'),
                'success': res.get('success', False),
                'message': res.get('message', ''),
                'timestamp': res.get('timestamp')
            })
        
        return bid_results
    
    # UnifiedBidding 클래스의 메서드 교체
    # UnifiedBidding._execute_bidding = _execute_bidding_with_poison


def main():
    """테스트 실행"""
    # 테스트 데이터
    test_items = [
        {
            'url': 'https://seller.poizon.com/product/12345',
            'price': 55000,
            'size': '95'
        },
        {
            'url': 'https://seller.poizon.com/product/67890',
            'price': 68000,
            'size': '100'
        }
    ]
    
    # 통합 입찰 실행
    bidder = PoisonIntegratedBidding()
    
    if bidder.initialize():
        results = bidder.batch_bidding(test_items)
        
        print("\n=== 입찰 결과 ===")
        for result in results:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        
        # 브라우저 유지
        input("\n브라우저를 유지하려면 Enter를 누르세요...")
        bidder.close()
    else:
        print("로그인 실패")


if __name__ == "__main__":
    main()
