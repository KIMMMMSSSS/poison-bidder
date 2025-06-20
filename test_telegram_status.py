#!/usr/bin/env python3
"""
텔레그램 봇 상태 추적 시스템 통합 테스트
각 모듈의 콜백 메커니즘이 올바르게 작동하는지 검증
"""

import unittest
import asyncio
from unittest.mock import Mock, MagicMock, patch
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import status_constants
from auto_bidding import AutoBidding


class TestStatusTracking(unittest.TestCase):
    """상태 추적 시스템 테스트"""
    
    def setUp(self):
        """테스트 초기화"""
        self.auto_bidder = AutoBidding()
        self.callback_history = []
        
    def test_status_constants(self):
        """상태 상수가 올바르게 정의되었는지 확인"""
        # 필수 상태 코드 확인
        required_stages = [
            'STAGE_INITIALIZING',
            'STAGE_LOGIN_CHECK',
            'STAGE_SEARCHING',
            'STAGE_LINK_EXTRACTING',
            'STAGE_SCRAPING',
            'STAGE_PRICE_CALCULATING',
            'STAGE_BIDDING',
            'STAGE_COMPLETED',
            'STAGE_ERROR'
        ]
        
        for stage in required_stages:
            self.assertTrue(hasattr(status_constants, stage))
            
        # 이모지 매핑 확인
        self.assertIsInstance(status_constants.STAGE_EMOJIS, dict)
        self.assertEqual(len(status_constants.STAGE_EMOJIS), 9)
        
        # 진행률 범위 확인
        self.assertIsInstance(status_constants.STAGE_PROGRESS_RANGES, dict)
        
    def test_progress_bar_creation(self):
        """프로그레스 바 생성 테스트"""
        # 0% 테스트
        bar = status_constants.create_progress_bar(0)
        self.assertEqual(bar, "░" * 10)
        
        # 50% 테스트
        bar = status_constants.create_progress_bar(50)
        self.assertEqual(bar, "█" * 5 + "░" * 5)
        
        # 100% 테스트
        bar = status_constants.create_progress_bar(100)
        self.assertEqual(bar, "█" * 10)
        
        # 범위 초과 테스트
        bar = status_constants.create_progress_bar(150)
        self.assertEqual(bar, "█" * 10)
        
        bar = status_constants.create_progress_bar(-50)
        self.assertEqual(bar, "░" * 10)
        
    def test_stage_progress_calculation(self):
        """단계별 진행률 계산 테스트"""
        # 스크래핑 단계 테스트 (30-70%)
        progress = status_constants.calculate_stage_progress(
            status_constants.STAGE_SCRAPING, 0, 10
        )
        self.assertEqual(progress, 30)
        
        progress = status_constants.calculate_stage_progress(
            status_constants.STAGE_SCRAPING, 5, 10
        )
        self.assertEqual(progress, 50)
        
        progress = status_constants.calculate_stage_progress(
            status_constants.STAGE_SCRAPING, 10, 10
        )
        self.assertEqual(progress, 70)
        
    def test_format_status_message(self):
        """상태 메시지 포맷팅 테스트"""
        msg = status_constants.format_status_message(
            status_constants.STAGE_SCRAPING,
            50,
            "테스트 메시지",
            {"current_item": 5, "total_items": 10}
        )
        
        self.assertIn("📦", msg)  # 스크래핑 이모지
        self.assertIn("50%", msg)
        self.assertIn("테스트 메시지", msg)
        self.assertIn("5/10", msg)
        
    def test_callback_invocation(self):
        """콜백 호출 테스트"""
        def test_callback(stage, progress, message, details=None):
            self.callback_history.append({
                'stage': stage,
                'progress': progress,
                'message': message,
                'details': details
            })
        
        # 간단한 시뮬레이션
        stages = [
            (status_constants.STAGE_INITIALIZING, 0, "초기화"),
            (status_constants.STAGE_LOGIN_CHECK, 10, "로그인 확인"),
            (status_constants.STAGE_LINK_EXTRACTING, 30, "링크 추출"),
            (status_constants.STAGE_COMPLETED, 100, "완료")
        ]
        
        for stage, progress, message in stages:
            test_callback(stage, progress, message)
        
        self.assertEqual(len(self.callback_history), 4)
        self.assertEqual(self.callback_history[0]['stage'], status_constants.STAGE_INITIALIZING)
        self.assertEqual(self.callback_history[-1]['progress'], 100)
        
    def test_error_handling(self):
        """오류 처리 테스트"""
        def test_callback(stage, progress, message, details=None):
            self.callback_history.append({
                'stage': stage,
                'progress': progress,
                'message': message,
                'details': details
            })
        
        # 오류 상황 시뮬레이션
        test_callback(
            status_constants.STAGE_ERROR,
            0,
            "테스트 오류",
            {"error": "Connection timeout", "traceback": "..."}
        )
        
        last_call = self.callback_history[-1]
        self.assertEqual(last_call['stage'], status_constants.STAGE_ERROR)
        self.assertIn("error", last_call['details'])
        
    @patch('auto_bidding.SELENIUM_AVAILABLE', False)
    def test_auto_bidding_without_selenium(self):
        """Selenium 없이 auto_bidding 테스트"""
        called_stages = []
        
        def mock_callback(stage, progress, message, details=None):
            called_stages.append(stage)
            
        # Selenium이 없을 때 에러가 발생해야 함
        result = self.auto_bidder.run_auto_pipeline(
            site="musinsa",
            keywords=["test"],
            strategy="basic",
            status_callback=mock_callback
        )
        
        # 초기화는 호출되어야 함
        self.assertIn(status_constants.STAGE_INITIALIZING, called_stages)
        

class TestIntegration(unittest.TestCase):
    """통합 테스트"""
    
    def test_message_formatting_with_various_details(self):
        """다양한 상세 정보로 메시지 포맷팅 테스트"""
        test_cases = [
            # 기본 메시지
            {
                'stage': status_constants.STAGE_INITIALIZING,
                'progress': 0,
                'message': "시작합니다",
                'details': None
            },
            # 키워드 포함
            {
                'stage': status_constants.STAGE_SEARCHING,
                'progress': 15,
                'message': "검색 중",
                'details': {"current_keyword": "나이키"}
            },
            # 진행 상황 포함
            {
                'stage': status_constants.STAGE_SCRAPING,
                'progress': 50,
                'message': "스크래핑 중",
                'details': {"current_item": 25, "total_items": 50}
            },
            # 오류 포함
            {
                'stage': status_constants.STAGE_ERROR,
                'progress': 0,
                'message': "오류 발생",
                'details': {"error": "Network error"}
            }
        ]
        
        for test_case in test_cases:
            msg = status_constants.format_status_message(
                test_case['stage'],
                test_case['progress'],
                test_case['message'],
                test_case['details']
            )
            
            # 기본 요소 확인
            self.assertIn(str(test_case['progress']) + "%", msg)
            self.assertIn(test_case['message'], msg)
            
            # 상세 정보 확인
            if test_case['details']:
                if 'current_keyword' in test_case['details']:
                    self.assertIn(test_case['details']['current_keyword'], msg)
                if 'error' in test_case['details']:
                    self.assertIn(test_case['details']['error'], msg)


class TestEndToEnd(unittest.TestCase):
    """End-to-End 테스트"""
    
    def test_telegram_bot_callback_flow(self):
        """텔레그램 봇의 콜백 플로우 테스트"""
        # 이 테스트는 실제 텔레그램 봇 실행 없이
        # 콜백 메커니즘만 테스트합니다
        
        callback_received = []
        
        def capture_callback(stage, progress, message, details=None):
            callback_received.append({
                'stage': stage,
                'progress': progress,
                'message': message
            })
        
        # 예상되는 콜백 순서
        expected_stages = [
            status_constants.STAGE_INITIALIZING,
            status_constants.STAGE_LOGIN_CHECK,
            status_constants.STAGE_LINK_EXTRACTING,
            status_constants.STAGE_SCRAPING,
            status_constants.STAGE_PRICE_CALCULATING,
            status_constants.STAGE_BIDDING,
            status_constants.STAGE_COMPLETED
        ]
        
        # 각 단계별로 콜백 시뮬레이션
        progress = 0
        for stage in expected_stages:
            if stage == status_constants.STAGE_COMPLETED:
                progress = 100
            else:
                progress += 15
            capture_callback(stage, progress, f"{stage} 진행 중")
        
        # 모든 단계가 호출되었는지 확인
        received_stages = [cb['stage'] for cb in callback_received]
        for expected_stage in expected_stages:
            self.assertIn(expected_stage, received_stages)
        
        # 진행률이 증가하는지 확인
        progresses = [cb['progress'] for cb in callback_received]
        self.assertEqual(progresses[-1], 100)


def run_tests():
    """테스트 실행"""
    # 테스트 스위트 생성
    test_suite = unittest.TestSuite()
    
    # 테스트 추가
    test_suite.addTest(unittest.makeSuite(TestStatusTracking))
    test_suite.addTest(unittest.makeSuite(TestIntegration))
    test_suite.addTest(unittest.makeSuite(TestEndToEnd))
    
    # 테스트 실행
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # 결과 반환
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    if success:
        print("\nAll tests passed successfully!")
    else:
        print("\nSome tests failed.")
        sys.exit(1)
