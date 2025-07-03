#!/usr/bin/env python3
"""
unified_items 파라미터 오류 재현 테스트
"""

import os
import sys
import logging
from datetime import datetime

# 경로 설정
sys.path.append('C:/poison_final')

# 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

def test_direct_call():
    """직접 호출로 오류 재현"""
    try:
        logger.info("=== 직접 호출 테스트 시작 ===")
        from poison_integrated_bidding import AutoBiddingAdapter
        
        # 문제: True를 전달
        adapter = AutoBiddingAdapter()
        logger.info("AutoBiddingAdapter 인스턴스 생성 완료")
        
        # 오류를 재현하기 위해 True 전달
        logger.info("run_with_poison에 True 전달 시도...")
        result = adapter.run_with_poison(True)  # 이것이 오류 원인!
        
    except Exception as e:
        logger.error(f"예상된 오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())

def test_empty_call():
    """빈 호출로 오류 재현"""
    try:
        logger.info("\n=== 빈 호출 테스트 시작 ===")
        from poison_integrated_bidding import AutoBiddingAdapter
        
        adapter = AutoBiddingAdapter()
        
        # 빈 리스트 전달
        logger.info("run_with_poison에 빈 리스트 전달...")
        result = adapter.run_with_poison([])
        logger.info(f"결과: {result}")
        
    except Exception as e:
        logger.error(f"오류 발생: {e}")

def test_correct_call():
    """올바른 호출 테스트"""
    try:
        logger.info("\n=== 올바른 호출 테스트 시작 ===")
        from poison_integrated_bidding import AutoBiddingAdapter
        
        adapter = AutoBiddingAdapter()
        
        # 올바른 형식의 데이터
        test_items = [
            {
                'code': 'TEST001',
                'brand': 'NIKE',
                'size': '270',
                'price': 100000,
                'color': 'BLACK'
            }
        ]
        
        logger.info(f"run_with_poison에 올바른 데이터 전달: {test_items}")
        result = adapter.run_with_poison(test_items)
        logger.info(f"결과: {result}")
        
    except Exception as e:
        logger.error(f"오류 발생: {e}")

def find_error_source():
    """오류 발생 지점 추적"""
    logger.info("\n=== 오류 발생 지점 추적 ===")
    
    # poison_integrated_bidding.py의 main() 함수 확인
    try:
        import poison_integrated_bidding
        logger.info("poison_integrated_bidding 모듈의 main() 함수 확인")
        
        # main 함수가 어떻게 호출되는지 확인
        # 이 부분에서 True가 전달될 가능성이 있음
        
    except Exception as e:
        logger.error(f"모듈 import 오류: {e}")

if __name__ == '__main__':
    # 각 테스트 실행
    test_direct_call()
    test_empty_call()
    test_correct_call()
    find_error_source()
    
    logger.info("\n=== 테스트 완료 ===")
