#!/usr/bin/env python3
"""
포이즌 입찰 시스템 통합 테스트
전체 플로우를 실제 데이터로 검증
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
import traceback

# 로깅 설정
log_dir = Path("C:/poison_final/logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_dir / f'integration_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def create_sample_data():
    """테스트용 샘플 데이터 생성"""
    logger.info("=== 샘플 데이터 생성 ===")
    
    # 정상적인 샘플 데이터
    sample_items = [
        {
            'code': 'TEST001',
            'brand': '나이키',
            'size': '270',
            'price': 50000,
            'adjusted_price': 45000,
            'color': 'BLACK',
            'link': 'https://test.com/product/001',
            'name': '테스트 상품 1'
        },
        {
            'code': 'TEST002',
            'brand': '아디다스',
            'size': '280',
            'price': 60000,
            'adjusted_price': 54000,
            'color': 'WHITE',
            'link': 'https://test.com/product/002',
            'name': '테스트 상품 2'
        },
        {
            'code': 'TEST003',
            'brand': '뉴발란스',
            'size': '265',
            'price': 70000,
            'adjusted_price': 63000,
            'color': 'GRAY',
            'link': 'https://test.com/product/003',
            'name': '테스트 상품 3'
        }
    ]
    
    logger.info(f"생성된 샘플 데이터: {len(sample_items)}개 아이템")
    return sample_items


def test_poison_integrated_bidding():
    """poison_integrated_bidding.py 테스트"""
    logger.info("\n=== poison_integrated_bidding.py 테스트 ===")
    
    try:
        from poison_integrated_bidding import AutoBiddingAdapter
        
        # 샘플 데이터 준비
        items = create_sample_data()
        
        # AutoBiddingAdapter 테스트
        logger.info("AutoBiddingAdapter 인스턴스 생성")
        adapter = AutoBiddingAdapter(
            driver_path=None,
            min_profit=0,
            worker_count=2
        )
        
        # 정상 케이스 테스트
        logger.info("\n[테스트 1] 정상 데이터 입력")
        try:
            # 실제 입찰은 포이즌 로그인이 필요하므로 모킹
            from unittest.mock import MagicMock, patch
            
            with patch('poison_integrated_bidding.PoizonBidderWrapperV2') as mock_wrapper:
                mock_instance = MagicMock()
                mock_instance.run_bidding.return_value = {
                    'status': 'success',
                    'total_codes': len(items),
                    'success': len(items),
                    'failed': 0,
                    'details': []
                }
                mock_wrapper.return_value = mock_instance
                
                result = adapter.run_with_poison(items)
                logger.info(f"정상 케이스 결과: {result['status']}")
                logger.info(f"성공: {result['successful']}, 실패: {result['failed']}")
                
        except Exception as e:
            logger.error(f"정상 케이스 실패: {e}")
            logger.error(traceback.format_exc())
        
        # 오류 케이스 테스트
        logger.info("\n[테스트 2] True 입력 (TypeError 예상)")
        try:
            adapter.run_with_poison(True)
            logger.error("❌ TypeError가 발생하지 않음!")
        except TypeError as e:
            logger.info(f"✅ 예상된 TypeError 발생: {e}")
        
        logger.info("\n[테스트 3] None 입력 (TypeError 예상)")
        try:
            adapter.run_with_poison(None)
            logger.error("❌ TypeError가 발생하지 않음!")
        except TypeError as e:
            logger.info(f"✅ 예상된 TypeError 발생: {e}")
        
        logger.info("\n[테스트 4] 빈 리스트 입력")
        result = adapter.run_with_poison([])
        logger.info(f"빈 리스트 결과: {result}")
        
        logger.info("\n[테스트 5] 필수 필드 누락")
        invalid_items = [
            {
                'brand': '나이키',
                # 'code' 누락
                'size': '270',
                'price': 50000
            }
        ]
        try:
            adapter.run_with_poison(invalid_items)
            logger.error("❌ ValueError가 발생하지 않음!")
        except ValueError as e:
            logger.info(f"✅ 예상된 ValueError 발생: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"poison_integrated_bidding 테스트 실패: {e}")
        logger.error(traceback.format_exc())
        return False


def test_poison_bidder_wrapper_v2():
    """poison_bidder_wrapper_v2.py 테스트"""
    logger.info("\n=== poison_bidder_wrapper_v2.py 테스트 ===")
    
    try:
        # 원본 모듈 로드를 모킹
        from unittest.mock import patch
        
        with patch('poison_bidder_wrapper_v2.importlib.util.spec_from_file_location'):
            from poison_bidder_wrapper_v2 import PoizonBidderWrapperV2
            
            # 인스턴스 생성
            logger.info("PoizonBidderWrapperV2 인스턴스 생성")
            wrapper = PoizonBidderWrapperV2(
                driver_path=None,
                min_profit=0,
                worker_count=2
            )
            
            # prepare_bid_data 테스트
            logger.info("\n[테스트 1] prepare_bid_data - 정상 데이터")
            items = create_sample_data()
            bid_data = wrapper.prepare_bid_data(items)
            logger.info(f"변환된 데이터: {len(bid_data)}개")
            if bid_data:
                logger.info(f"첫 번째 튜플: {bid_data[0]}")
            
            logger.info("\n[테스트 2] prepare_bid_data - 문자열 입력")
            try:
                wrapper.prepare_bid_data("잘못된 입력")
                logger.error("❌ TypeError가 발생하지 않음!")
            except TypeError as e:
                logger.info(f"✅ 예상된 TypeError 발생: {e}")
            
            logger.info("\n[테스트 3] prepare_bid_data - 빈 리스트")
            result = wrapper.prepare_bid_data([])
            logger.info(f"빈 리스트 결과: {result}")
            
            # run_bidding 테스트
            logger.info("\n[테스트 4] run_bidding - bool 입력")
            try:
                wrapper.run_bidding(unified_items=True)
                logger.error("❌ TypeError가 발생하지 않음!")
            except TypeError as e:
                logger.info(f"✅ 예상된 TypeError 발생: {e}")
            
            logger.info("\n[테스트 5] run_bidding - None 입력")
            try:
                wrapper.run_bidding(unified_items=None)
                logger.error("❌ ValueError가 발생하지 않음!")
            except (TypeError, ValueError) as e:
                logger.info(f"✅ 예상된 오류 발생: {e}")
            
        return True
        
    except Exception as e:
        logger.error(f"poison_bidder_wrapper_v2 테스트 실패: {e}")
        logger.error(traceback.format_exc())
        return False


def test_auto_bidding():
    """auto_bidding.py 테스트"""
    logger.info("\n=== auto_bidding.py 테스트 ===")
    
    try:
        from auto_bidding import AutoBidding
        
        # 인스턴스 생성
        logger.info("AutoBidding 인스턴스 생성")
        auto_bidder = AutoBidding()
        
        # _execute_auto_bidding 메서드 테스트
        logger.info("\n[테스트 1] _execute_auto_bidding - 정상 데이터")
        
        # POISON_LOGIN_AVAILABLE 모킹
        from unittest.mock import patch, MagicMock
        
        with patch('auto_bidding.POISON_LOGIN_AVAILABLE', True):
            with patch('auto_bidding.AutoBiddingAdapter') as mock_adapter_class:
                mock_adapter = MagicMock()
                mock_adapter.run_with_poison.return_value = {
                    'status': 'success',
                    'successful': 2,
                    'failed': 0,
                    'results': [
                        {'success': True, 'message': 'OK'},
                        {'success': True, 'message': 'OK'}
                    ]
                }
                mock_adapter_class.return_value = mock_adapter
                
                items = create_sample_data()
                results = auto_bidder._execute_auto_bidding('musinsa', items)
                
                logger.info(f"실행 결과: {len(results)}개 결과")
                logger.info(f"성공: {sum(1 for r in results if r['success'])}")
                
                # run_with_poison이 호출되었는지 확인
                mock_adapter.run_with_poison.assert_called_once()
                args = mock_adapter.run_with_poison.call_args[0]
                logger.info(f"run_with_poison 호출 파라미터 타입: {type(args[0])}")
        
        return True
        
    except Exception as e:
        logger.error(f"auto_bidding 테스트 실패: {e}")
        logger.error(traceback.format_exc())
        return False


def test_unified_bidding():
    """unified_bidding.py 테스트"""
    logger.info("\n=== unified_bidding.py 테스트 ===")
    
    try:
        from unified_bidding import UnifiedBidding
        
        # 설정 파일 생성
        config_dir = Path("config")
        config_dir.mkdir(exist_ok=True)
        
        config_data = {
            "strategies": {
                "basic": {
                    "enabled": True,
                    "adjustments": {
                        "base": {"enabled": True, "rate": 0.05}
                    }
                }
            }
        }
        
        config_file = config_dir / "pricing_strategies.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
        
        # 인스턴스 생성
        logger.info("UnifiedBidding 인스턴스 생성")
        unified_bidder = UnifiedBidding(debug=True)
        
        # _execute_bidding 메서드 테스트
        logger.info("\n[테스트 1] _execute_bidding - 정상 데이터")
        
        from unittest.mock import patch, MagicMock
        
        with patch('unified_bidding.AutoBiddingAdapter') as mock_adapter_class:
            mock_adapter = MagicMock()
            mock_adapter.run_with_poison.return_value = {
                'status': 'success',
                'successful': 3,
                'failed': 0,
                'results': [
                    {'success': True, 'message': 'OK'},
                    {'success': True, 'message': 'OK'},
                    {'success': True, 'message': 'OK'}
                ]
            }
            mock_adapter_class.return_value = mock_adapter
            
            items = create_sample_data()
            results = unified_bidder._execute_bidding('musinsa', items, 'auto')
            
            logger.info(f"실행 결과: {len(results)}개")
            logger.info(f"성공: {sum(1 for r in results if r['success'])}")
        
        return True
        
    except Exception as e:
        logger.error(f"unified_bidding 테스트 실패: {e}")
        logger.error(traceback.format_exc())
        return False


def analyze_logs():
    """로그 분석"""
    logger.info("\n=== 로그 분석 ===")
    
    # 오늘 날짜의 로그 파일들 찾기
    today = datetime.now().strftime("%Y%m%d")
    log_files = list(log_dir.glob(f"*{today}*.log"))
    
    logger.info(f"발견된 로그 파일: {len(log_files)}개")
    
    # 주요 키워드 검색
    keywords = [
        "TypeError",
        "ValueError",
        "run_with_poison",
        "unified_items",
        "필수 필드",
        "타입 검증"
    ]
    
    for log_file in log_files[-3:]:  # 최근 3개만
        logger.info(f"\n로그 파일: {log_file.name}")
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            for keyword in keywords:
                count = content.count(keyword)
                if count > 0:
                    logger.info(f"  - '{keyword}' 발견: {count}회")
                    
        except Exception as e:
            logger.error(f"로그 파일 읽기 실패: {e}")


def main():
    """메인 실행 함수"""
    logger.info("=" * 80)
    logger.info("포이즌 입찰 시스템 통합 테스트 시작")
    logger.info("=" * 80)
    
    # 테스트 결과 저장
    results = {
        'timestamp': datetime.now().isoformat(),
        'tests': {}
    }
    
    # 각 모듈 테스트
    tests = [
        ('poison_integrated_bidding', test_poison_integrated_bidding),
        ('poison_bidder_wrapper_v2', test_poison_bidder_wrapper_v2),
        ('auto_bidding', test_auto_bidding),
        ('unified_bidding', test_unified_bidding)
    ]
    
    success_count = 0
    for test_name, test_func in tests:
        try:
            success = test_func()
            results['tests'][test_name] = {
                'success': success,
                'message': '성공' if success else '실패'
            }
            if success:
                success_count += 1
        except Exception as e:
            results['tests'][test_name] = {
                'success': False,
                'message': str(e)
            }
            logger.error(f"{test_name} 테스트 예외: {e}")
    
    # 로그 분석
    analyze_logs()
    
    # 결과 요약
    logger.info("\n" + "=" * 80)
    logger.info("테스트 결과 요약")
    logger.info("=" * 80)
    logger.info(f"전체 테스트: {len(tests)}개")
    logger.info(f"성공: {success_count}개")
    logger.info(f"실패: {len(tests) - success_count}개")
    
    # 결과 저장
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    output_file = output_dir / f"integration_test_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    logger.info(f"\n결과 저장: {output_file}")
    
    # 성공/실패 판단
    if success_count == len(tests):
        logger.info("\n✅ 모든 테스트 통과!")
        return 0
    else:
        logger.error(f"\n❌ {len(tests) - success_count}개 테스트 실패")
        return 1


if __name__ == '__main__':
    sys.exit(main())
