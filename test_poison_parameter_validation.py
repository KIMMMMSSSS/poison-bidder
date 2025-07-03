#!/usr/bin/env python3
"""
포이즌 입찰 시스템 파라미터 검증 단위 테스트
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
import logging

# 현재 디렉토리를 sys.path에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 테스트 대상 모듈 import
from poison_integrated_bidding import AutoBiddingAdapter
from poison_bidder_wrapper_v2 import PoizonBidderWrapperV2


class TestPoisonParameterValidation(unittest.TestCase):
    """파라미터 검증 테스트 클래스"""
    
    def setUp(self):
        """테스트 초기화"""
        # 로깅 설정
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def test_autobidding_adapter_valid_items(self):
        """AutoBiddingAdapter - 정상 리스트 입력"""
        adapter = AutoBiddingAdapter()
        
        # 정상 데이터
        valid_items = [
            {
                'code': 'ABC123',
                'brand': '나이키',
                'size': '270',
                'price': 50000,
                'adjusted_price': 45000,
                'color': 'BLACK'
            },
            {
                'code': 'DEF456',
                'brand': '아디다스',
                'size': '280',
                'price': 60000,
                'adjusted_price': 54000,
                'color': 'WHITE'
            }
        ]
        
        # PoizonBidderWrapperV2 모킹
        with patch('poison_integrated_bidding.PoizonBidderWrapperV2') as mock_wrapper:
            mock_instance = MagicMock()
            mock_instance.run_bidding.return_value = {
                'status': 'success',
                'total_codes': 2,
                'success': 2,
                'failed': 0,
                'details': []
            }
            mock_wrapper.return_value = mock_instance
            
            # 실행
            result = adapter.run_with_poison(valid_items)
            
            # 검증
            self.assertEqual(result['status'], 'success')
            self.assertEqual(result['total'], 2)
            mock_instance.run_bidding.assert_called_once()
    
    def test_autobidding_adapter_bool_input(self):
        """AutoBiddingAdapter - bool 타입 입력 (True)"""
        adapter = AutoBiddingAdapter()
        
        # TypeError가 발생해야 함
        with self.assertRaises(TypeError) as context:
            adapter.run_with_poison(True)
        
        self.assertIn("items는 list 타입이어야 합니다", str(context.exception))
        self.assertIn("bool", str(context.exception))
    
    def test_autobidding_adapter_none_input(self):
        """AutoBiddingAdapter - None 입력"""
        adapter = AutoBiddingAdapter()
        
        # TypeError가 발생해야 함
        with self.assertRaises(TypeError) as context:
            adapter.run_with_poison(None)
        
        self.assertIn("items는 list 타입이어야 합니다", str(context.exception))
        self.assertIn("NoneType", str(context.exception))
    
    def test_autobidding_adapter_empty_list(self):
        """AutoBiddingAdapter - 빈 리스트 입력"""
        adapter = AutoBiddingAdapter()
        
        # 빈 리스트는 정상 처리되어야 함
        result = adapter.run_with_poison([])
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['total'], 0)
        self.assertEqual(result['successful'], 0)
        self.assertEqual(result['failed'], 0)
        self.assertEqual(result['message'], '입찰할 항목이 없습니다')
    
    def test_autobidding_adapter_invalid_item_structure(self):
        """AutoBiddingAdapter - 잘못된 아이템 구조"""
        adapter = AutoBiddingAdapter()
        
        # dict가 아닌 아이템
        invalid_items = [
            "문자열 아이템",  # 잘못된 타입
            123,              # 숫자
            True              # bool
        ]
        
        # TypeError가 발생해야 함
        with self.assertRaises(TypeError) as context:
            adapter.run_with_poison(invalid_items)
        
        self.assertIn("items[0]는 dict 타입이어야 합니다", str(context.exception))
    
    def test_autobidding_adapter_missing_required_fields(self):
        """AutoBiddingAdapter - 필수 필드 누락"""
        adapter = AutoBiddingAdapter()
        
        # 필수 필드가 누락된 아이템
        items_missing_fields = [
            {
                'brand': '나이키',
                # 'code' 누락
                'size': '270',
                'price': 50000
            }
        ]
        
        # ValueError가 발생해야 함
        with self.assertRaises(ValueError) as context:
            adapter.run_with_poison(items_missing_fields)
        
        self.assertIn("필수 필드가 누락되었습니다", str(context.exception))
        self.assertIn("code", str(context.exception))
    
    def test_bidder_wrapper_prepare_valid_items(self):
        """PoizonBidderWrapperV2 - prepare_bid_data 정상 입력"""
        # 원본 모듈 로드를 모킹
        with patch('poison_bidder_wrapper_v2.importlib.util.spec_from_file_location'):
            wrapper = PoizonBidderWrapperV2()
            
            valid_items = [
                {
                    'code': 'ABC123',
                    'brand': '나이키',
                    'size': '270',
                    'price': 50000,
                    'adjusted_price': 45000,
                    'color': 'BLACK'
                }
            ]
            
            # 실행
            result = wrapper.prepare_bid_data(valid_items)
            
            # 검증
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0][1], '나이키')  # brand
            self.assertEqual(result[0][2], 'ABC123')  # code
            self.assertEqual(result[0][5], 45000)     # price
    
    def test_bidder_wrapper_prepare_invalid_type(self):
        """PoizonBidderWrapperV2 - prepare_bid_data 잘못된 타입"""
        with patch('poison_bidder_wrapper_v2.importlib.util.spec_from_file_location'):
            wrapper = PoizonBidderWrapperV2()
            
            # TypeError가 발생해야 함
            with self.assertRaises(TypeError) as context:
                wrapper.prepare_bid_data("문자열")
            
            self.assertIn("items는 list 타입이어야 합니다", str(context.exception))
    
    def test_bidder_wrapper_prepare_empty_list(self):
        """PoizonBidderWrapperV2 - prepare_bid_data 빈 리스트"""
        with patch('poison_bidder_wrapper_v2.importlib.util.spec_from_file_location'):
            wrapper = PoizonBidderWrapperV2()
            
            # 빈 리스트는 빈 결과 반환
            result = wrapper.prepare_bid_data([])
            self.assertEqual(result, [])
    
    @patch('poison_bidder_wrapper_v2.Manager')
    @patch('poison_bidder_wrapper_v2.Process')
    def test_bidder_wrapper_run_bidding_bool_input(self, mock_process, mock_manager):
        """PoizonBidderWrapperV2 - run_bidding bool 입력"""
        with patch('poison_bidder_wrapper_v2.importlib.util.spec_from_file_location'):
            wrapper = PoizonBidderWrapperV2()
            
            # TypeError가 발생해야 함
            with self.assertRaises(TypeError) as context:
                wrapper.run_bidding(unified_items=True)
            
            self.assertIn("unified_items는 bool 타입이 아니어야 합니다", str(context.exception))
    
    @patch('poison_bidder_wrapper_v2.Manager')
    @patch('poison_bidder_wrapper_v2.Process')
    def test_bidder_wrapper_run_bidding_string_input(self, mock_process, mock_manager):
        """PoizonBidderWrapperV2 - run_bidding 문자열 입력"""
        with patch('poison_bidder_wrapper_v2.importlib.util.spec_from_file_location'):
            wrapper = PoizonBidderWrapperV2()
            
            # TypeError가 발생해야 함
            with self.assertRaises(TypeError) as context:
                wrapper.run_bidding(unified_items="잘못된 입력")
            
            self.assertIn("unified_items는 list 타입이어야 합니다", str(context.exception))
            self.assertIn("str", str(context.exception))
    
    def test_edge_cases_mixed_valid_invalid_items(self):
        """엣지 케이스 - 유효한 아이템과 무효한 아이템 혼재"""
        adapter = AutoBiddingAdapter()
        
        mixed_items = [
            {
                'code': 'ABC123',
                'brand': '나이키',
                'size': '270',
                'price': 50000
            },
            "잘못된 아이템",  # 이것 때문에 실패해야 함
            {
                'code': 'DEF456',
                'brand': '아디다스',
                'size': '280',
                'price': 60000
            }
        ]
        
        # TypeError가 발생해야 함
        with self.assertRaises(TypeError) as context:
            adapter.run_with_poison(mixed_items)
        
        self.assertIn("items[1]는 dict 타입이어야 합니다", str(context.exception))
    
    def test_logging_output(self):
        """로깅 출력 테스트"""
        adapter = AutoBiddingAdapter()
        
        # 로깅 캡처
        with self.assertLogs(level='INFO') as log:
            with patch('poison_integrated_bidding.PoizonBidderWrapperV2'):
                # 빈 리스트로 테스트
                adapter.run_with_poison([])
        
        # 로그 메시지 확인
        log_output = '\n'.join(log.output)
        self.assertIn("run_with_poison 호출 - items 타입", log_output)
        self.assertIn("입력된 items가 비어있습니다", log_output)


class TestIntegrationScenarios(unittest.TestCase):
    """통합 시나리오 테스트"""
    
    def test_complete_flow_with_validation(self):
        """전체 플로우 테스트 - 검증 포함"""
        # auto_bidding.py의 _execute_auto_bidding 메서드 테스트
        from auto_bidding import AutoBidding
        
        auto_bidder = AutoBidding()
        
        # 모킹
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
                
                # 정상 아이템으로 테스트
                items = [
                    {'name': 'Item1', 'adjusted_price': 50000, 'sizes': ['270']},
                    {'name': 'Item2', 'adjusted_price': 60000, 'sizes': ['280']}
                ]
                
                results = auto_bidder._execute_auto_bidding('musinsa', items)
                
                # 검증
                self.assertEqual(len(results), 2)
                self.assertTrue(all(r['success'] for r in results))
                mock_adapter.run_with_poison.assert_called_once_with(items)
    
    def test_error_propagation(self):
        """에러 전파 테스트"""
        adapter = AutoBiddingAdapter()
        
        # 다양한 잘못된 입력에 대한 에러 확인
        invalid_inputs = [
            (True, "bool"),
            (False, "bool"),
            (None, "NoneType"),
            ("string", "str"),
            (123, "int"),
            ({"dict": "value"}, "dict"),
            (set([1, 2, 3]), "set")
        ]
        
        for invalid_input, expected_type in invalid_inputs:
            with self.subTest(input=invalid_input):
                with self.assertRaises(TypeError) as context:
                    adapter.run_with_poison(invalid_input)
                
                self.assertIn(expected_type, str(context.exception))


if __name__ == '__main__':
    # 테스트 실행
    unittest.main(verbosity=2)
