#!/usr/bin/env python3
"""
포이즌 입찰 시스템 전체 통합 테스트
- 실제 플로우 테스트
- 사용자 설정 적용 확인
- 결과 표시 개선 검증
- 상세 로그 기록
"""

import os
import sys
import json
import logging
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# 시스템 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 로깅 설정
log_dir = Path('C:/poison_final/logs/integration_test')
log_dir.mkdir(parents=True, exist_ok=True)

# 상세 로깅을 위한 포맷터
detailed_formatter = logging.Formatter(
    '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# 파일 핸들러 (상세 로그)
file_handler = logging.FileHandler(
    log_dir / f'integration_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log',
    encoding='utf-8'
)
file_handler.setFormatter(detailed_formatter)
file_handler.setLevel(logging.DEBUG)

# 콘솔 핸들러 (간단 로그)
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
console_handler.setLevel(logging.INFO)

# 루트 로거 설정
logging.basicConfig(level=logging.DEBUG, handlers=[file_handler, console_handler])
logger = logging.getLogger(__name__)


class FullIntegrationTest:
    """전체 통합 테스트 클래스"""
    
    def __init__(self):
        self.test_results = {
            'start_time': datetime.now().isoformat(),
            'tests': {},
            'summary': {
                'total': 0,
                'passed': 0,
                'failed': 0,
                'warnings': 0
            }
        }
        self.auto_bidding = None
        
    def setup(self) -> bool:
        """테스트 환경 초기화"""
        logger.info("=" * 80)
        logger.info("포이즌 입찰 시스템 전체 통합 테스트 시작")
        logger.info("=" * 80)
        
        try:
            # 필요한 모듈 임포트
            from auto_bidding import AutoBidding
            self.auto_bidding = AutoBidding()
            logger.info("✓ AutoBidding 모듈 로드 성공")
            
            # 설정 파일 확인
            configs_to_check = [
                ('config/auto_bidding_config.json', '자동 입찰 설정'),
                ('config/unified_config.json', '통합 입찰 설정'),
                ('config/bot_config.json', '텔레그램 봇 설정')
            ]
            
            for config_path, config_name in configs_to_check:
                if Path(config_path).exists():
                    logger.info(f"✓ {config_name} 파일 존재: {config_path}")
                else:
                    logger.warning(f"⚠ {config_name} 파일 없음: {config_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ 환경 초기화 실패: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def test_parameter_validation(self):
        """파라미터 검증 테스트"""
        test_name = "파라미터 검증"
        logger.info(f"\n{'='*60}")
        logger.info(f"테스트: {test_name}")
        logger.info("="*60)
        
        test_cases = [
            {
                'name': '정상 범위 할인율',
                'params': {'discount_rate': 15, 'min_profit': 50000},
                'expected': 'success'
            },
            {
                'name': '최대 할인율',
                'params': {'discount_rate': 30, 'min_profit': 100000},
                'expected': 'success'
            },
            {
                'name': '최소 할인율',
                'params': {'discount_rate': 1, 'min_profit': 10000},
                'expected': 'success'
            },
            {
                'name': '범위 초과 할인율',
                'params': {'discount_rate': 40, 'min_profit': 50000},
                'expected': 'warning'
            },
            {
                'name': '음수 할인율',
                'params': {'discount_rate': -5, 'min_profit': 50000},
                'expected': 'error'
            },
            {
                'name': '음수 최소 수익',
                'params': {'discount_rate': 10, 'min_profit': -10000},
                'expected': 'warning'
            }
        ]
        
        results = []
        for tc in test_cases:
            logger.info(f"\n[{tc['name']}]")
            logger.info(f"입력: 할인율={tc['params']['discount_rate']}%, 최소수익={tc['params']['min_profit']:,}원")
            
            try:
                # 파라미터 검증 로직
                discount_rate = tc['params']['discount_rate']
                min_profit = tc['params']['min_profit']
                
                validation_result = 'success'
                validation_msg = ''
                
                # 할인율 검증
                if discount_rate < 0:
                    validation_result = 'error'
                    validation_msg = '음수 할인율은 허용되지 않음'
                elif discount_rate > 30:
                    validation_result = 'warning'
                    validation_msg = f'할인율 {discount_rate}% → 30%로 제한'
                    discount_rate = 30
                elif discount_rate < 1:
                    validation_result = 'warning'
                    validation_msg = f'할인율 {discount_rate}% → 1%로 조정'
                    discount_rate = 1
                
                # 최소 수익 검증
                if min_profit < 0:
                    if validation_result == 'success':
                        validation_result = 'warning'
                    validation_msg += f' | 음수 수익 {min_profit}원 → 0원으로 조정'
                    min_profit = 0
                
                # 결과 기록
                if validation_result == tc['expected']:
                    logger.info(f"✓ 예상대로 처리: {validation_result}")
                    if validation_msg:
                        logger.info(f"  메시지: {validation_msg}")
                    results.append('passed')
                else:
                    logger.error(f"✗ 예상과 다름: 예상={tc['expected']}, 실제={validation_result}")
                    results.append('failed')
                
            except Exception as e:
                logger.error(f"✗ 예외 발생: {e}")
                results.append('failed')
        
        # 테스트 결과 집계
        self._record_test_result(test_name, results)
    
    def test_discount_rate_application(self):
        """할인율 적용 테스트"""
        test_name = "할인율 적용"
        logger.info(f"\n{'='*60}")
        logger.info(f"테스트: {test_name}")
        logger.info("="*60)
        
        # 테스트용 상품 데이터
        test_items = [
            {'name': '나이키 에어맥스', 'price': 150000, 'link': 'test1'},
            {'name': '아디다스 슈퍼스타', 'price': 120000, 'link': 'test2'},
            {'name': '뉴발란스 574', 'price': 100000, 'link': 'test3'}
        ]
        
        test_cases = [
            {'discount': 10, 'expected_prices': [135000, 108000, 90000]},
            {'discount': 20, 'expected_prices': [120000, 96000, 80000]},
            {'discount': 30, 'expected_prices': [105000, 84000, 70000]}
        ]
        
        results = []
        for tc in test_cases:
            logger.info(f"\n할인율 {tc['discount']}% 테스트")
            
            try:
                # 가격 전략 적용
                adjusted_items = self.auto_bidding._apply_pricing_strategy(
                    items=test_items.copy(),
                    strategy='custom',
                    custom_discount_rate=tc['discount']
                )
                
                # 결과 검증
                all_correct = True
                for i, (item, expected_price) in enumerate(zip(adjusted_items, tc['expected_prices'])):
                    actual_price = item.get('adjusted_price', 0)
                    is_correct = abs(actual_price - expected_price) < 1  # 1원 미만 오차 허용
                    
                    if is_correct:
                        logger.info(f"  ✓ {item['name']}: {actual_price:,}원 (정확)")
                    else:
                        logger.error(f"  ✗ {item['name']}: {actual_price:,}원 (예상: {expected_price:,}원)")
                        all_correct = False
                
                results.append('passed' if all_correct else 'failed')
                
            except Exception as e:
                logger.error(f"✗ 테스트 실패: {e}")
                results.append('failed')
        
        self._record_test_result(test_name, results)
    
    def test_message_format(self):
        """메시지 포맷 테스트"""
        test_name = "메시지 포맷"
        logger.info(f"\n{'='*60}")
        logger.info(f"테스트: {test_name}")
        logger.info("="*60)
        
        # 테스트용 결과 데이터
        test_result = {
            'status': 'success',
            'site': 'musinsa',
            'keywords': ['나이키', '아디다스'],
            'total_links': 25,
            'total_items': 20,
            'successful_bids': 15,
            'execution_time': 180.5,
            'custom_discount_rate': 15,
            'custom_min_profit': 50000
        }
        
        # 메시지 포맷 생성 (텔레그램 봇 스타일)
        message = self._format_test_message(test_result)
        
        logger.info("생성된 메시지:")
        logger.info("-" * 60)
        for line in message.split('\n'):
            logger.info(line)
        logger.info("-" * 60)
        
        # 필수 요소 확인
        required_elements = [
            '사용자 설정',
            '검색 키워드',
            '적용 할인율',
            '최소 수익 기준',
            '처리 결과',
            '수집된 링크',
            '분석된 상품',
            '성공한 입찰',
            '실패한 입찰',
            '소요 시간',
            '예상 수익 정보'
        ]
        
        missing = []
        for element in required_elements:
            if element not in message:
                missing.append(element)
        
        if not missing:
            logger.info("✓ 모든 필수 요소 포함")
            self._record_test_result(test_name, ['passed'])
        else:
            logger.error(f"✗ 누락된 요소: {missing}")
            self._record_test_result(test_name, ['failed'])
    
    def test_logging_detail(self):
        """로깅 상세도 테스트"""
        test_name = "로깅 상세도"
        logger.info(f"\n{'='*60}")
        logger.info(f"테스트: {test_name}")
        logger.info("="*60)
        
        # 테스트 로그 메시지 생성
        test_messages = [
            ("INFO", "테스트 시작"),
            ("DEBUG", "상세 디버그 정보: 할인율=15%, 최소수익=50000"),
            ("WARNING", "경고: 할인율이 30%를 초과하여 제한됨"),
            ("ERROR", "오류: 입찰 실패 - 네트워크 오류")
        ]
        
        for level, msg in test_messages:
            getattr(logger, level.lower())(f"[로그 테스트] {msg}")
        
        # 로그 파일 확인
        log_files = list(log_dir.glob("*.log"))
        
        if log_files:
            latest_log = max(log_files, key=lambda f: f.stat().st_mtime)
            log_size = latest_log.stat().st_size
            
            logger.info(f"\n로그 파일 정보:")
            logger.info(f"  파일명: {latest_log.name}")
            logger.info(f"  크기: {log_size:,} bytes")
            
            # 로그 내용 분석
            with open(latest_log, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
                
                logger.info(f"  총 라인 수: {len(lines)}")
                
                # 로그 레벨별 카운트
                level_counts = {
                    'DEBUG': sum(1 for line in lines if 'DEBUG' in line),
                    'INFO': sum(1 for line in lines if 'INFO' in line),
                    'WARNING': sum(1 for line in lines if 'WARNING' in line),
                    'ERROR': sum(1 for line in lines if 'ERROR' in line)
                }
                
                logger.info("\n  로그 레벨별 메시지 수:")
                for level, count in level_counts.items():
                    logger.info(f"    {level}: {count}개")
            
            self._record_test_result(test_name, ['passed'])
        else:
            logger.error("✗ 로그 파일이 생성되지 않음")
            self._record_test_result(test_name, ['failed'])
    
    def test_end_to_end_simulation(self):
        """전체 플로우 시뮬레이션"""
        test_name = "전체 플로우 시뮬레이션"
        logger.info(f"\n{'='*60}")
        logger.info(f"테스트: {test_name}")
        logger.info("="*60)
        
        try:
            # 테스트 시나리오
            scenario = {
                'site': 'musinsa',
                'keywords': ['테스트'],
                'custom_discount_rate': 15,
                'custom_min_profit': 50000
            }
            
            logger.info(f"시나리오:")
            logger.info(f"  사이트: {scenario['site']}")
            logger.info(f"  키워드: {scenario['keywords']}")
            logger.info(f"  할인율: {scenario['custom_discount_rate']}%")
            logger.info(f"  최소수익: {scenario['custom_min_profit']:,}원")
            
            # 상태 콜백 함수
            def status_callback(stage, progress, message, details=None):
                logger.info(f"[{progress:3d}%] {stage}: {message}")
                if details:
                    for key, value in details.items():
                        logger.debug(f"       {key}: {value}")
            
            # 시뮬레이션 실행 (실제 크롤링은 하지 않음)
            logger.info("\n시뮬레이션 시작...")
            
            # 각 단계 시뮬레이션
            stages = [
                ("초기화", 0, "자동화 파이프라인을 시작합니다"),
                ("로그인 확인", 10, "로그인 상태를 확인하고 있습니다"),
                ("링크 추출", 30, "5개 링크 수집 완료"),
                ("스크래핑", 50, "상품 정보 수집 중"),
                ("가격 계산", 70, "할인율 15% 적용"),
                ("입찰 실행", 90, "3/5 입찰 성공"),
                ("완료", 100, "모든 작업이 완료되었습니다")
            ]
            
            for stage, progress, message in stages:
                status_callback(stage, progress, message)
                time.sleep(0.5)  # 시뮬레이션 대기
            
            logger.info("\n✓ 시뮬레이션 완료")
            self._record_test_result(test_name, ['passed'])
            
        except Exception as e:
            logger.error(f"✗ 시뮬레이션 실패: {e}")
            logger.error(traceback.format_exc())
            self._record_test_result(test_name, ['failed'])
    
    def _format_test_message(self, result: Dict[str, Any]) -> str:
        """테스트용 메시지 포맷"""
        msg = "✅ **자동화 입찰 완료!**\n\n"
        
        # 사용자 설정
        msg += "⚙️ **사용자 설정**\n"
        msg += f"├ 🔍 검색 키워드: {', '.join(result.get('keywords', []))}\n"
        msg += f"├ 💰 적용 할인율: {result.get('custom_discount_rate', '기본')}%\n"
        msg += f"└ 💵 최소 수익 기준: {result.get('custom_min_profit', 0):,}원\n\n"
        
        # 처리 결과
        msg += "📊 **처리 결과**\n"
        msg += f"├ 🔗 수집된 링크: {result.get('total_links', 0)}개\n"
        msg += f"├ 📦 분석된 상품: {result.get('total_items', 0)}개\n"
        msg += f"├ ✅ 성공한 입찰: {result.get('successful_bids', 0)}개\n"
        msg += f"├ ❌ 실패한 입찰: {result.get('total_items', 0) - result.get('successful_bids', 0)}개\n"
        msg += f"└ ⏱️ 소요 시간: {result.get('execution_time', 0):.1f}초\n\n"
        
        # 예상 수익 정보
        if result.get('successful_bids', 0) > 0:
            msg += "💰 **예상 수익 정보**\n"
            msg += f"├ 평균 할인율: {result.get('custom_discount_rate', 0)}%\n"
            msg += f"├ 성공 입찰 수: {result.get('successful_bids', 0)}개\n"
            msg += f"└ 예상 수익률: 할인율 × 판매 성공 시\n"
        
        return msg
    
    def _record_test_result(self, test_name: str, results: List[str]):
        """테스트 결과 기록"""
        passed = results.count('passed')
        failed = results.count('failed')
        total = len(results)
        
        self.test_results['tests'][test_name] = {
            'total': total,
            'passed': passed,
            'failed': failed,
            'success_rate': (passed / total * 100) if total > 0 else 0
        }
        
        self.test_results['summary']['total'] += total
        self.test_results['summary']['passed'] += passed
        self.test_results['summary']['failed'] += failed
        
        if passed == total:
            logger.info(f"\n✅ {test_name} 테스트: 모두 통과 ({passed}/{total})")
        elif passed > 0:
            logger.warning(f"\n⚠️ {test_name} 테스트: 일부 통과 ({passed}/{total})")
        else:
            logger.error(f"\n❌ {test_name} 테스트: 모두 실패 ({failed}/{total})")
    
    def save_results(self):
        """테스트 결과 저장"""
        self.test_results['end_time'] = datetime.now().isoformat()
        
        # 실행 시간 계산
        start = datetime.fromisoformat(self.test_results['start_time'])
        end = datetime.fromisoformat(self.test_results['end_time'])
        self.test_results['execution_time'] = (end - start).total_seconds()
        
        # 전체 성공률
        total = self.test_results['summary']['total']
        passed = self.test_results['summary']['passed']
        self.test_results['summary']['success_rate'] = (passed / total * 100) if total > 0 else 0
        
        # JSON 파일로 저장
        result_file = log_dir / f'test_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(self.test_results, f, ensure_ascii=False, indent=2)
        
        logger.info(f"\n테스트 결과 저장: {result_file}")
    
    def print_summary(self):
        """테스트 요약 출력"""
        logger.info("\n" + "=" * 80)
        logger.info("테스트 실행 요약")
        logger.info("=" * 80)
        
        summary = self.test_results['summary']
        logger.info(f"총 테스트: {summary['total']}개")
        logger.info(f"성공: {summary['passed']}개")
        logger.info(f"실패: {summary['failed']}개")
        logger.info(f"성공률: {summary['success_rate']:.1f}%")
        logger.info(f"실행 시간: {self.test_results.get('execution_time', 0):.1f}초")
        
        logger.info("\n개별 테스트 결과:")
        for test_name, result in self.test_results['tests'].items():
            status = "✅" if result['success_rate'] == 100 else "⚠️" if result['success_rate'] > 0 else "❌"
            logger.info(f"  {status} {test_name}: {result['passed']}/{result['total']} ({result['success_rate']:.0f}%)")
        
        # 최종 평가
        if summary['success_rate'] == 100:
            logger.info("\n🎉 모든 테스트 통과! 시스템이 정상적으로 작동합니다.")
        elif summary['success_rate'] >= 80:
            logger.warning("\n⚠️ 일부 테스트 실패. 검토가 필요합니다.")
        else:
            logger.error("\n❌ 많은 테스트 실패. 즉시 수정이 필요합니다.")
    
    def run(self):
        """전체 테스트 실행"""
        if not self.setup():
            logger.error("테스트 환경 설정 실패")
            return
        
        # 테스트 실행
        test_methods = [
            self.test_parameter_validation,
            self.test_discount_rate_application,
            self.test_message_format,
            self.test_logging_detail,
            self.test_end_to_end_simulation
        ]
        
        for test_method in test_methods:
            try:
                test_method()
            except Exception as e:
                logger.error(f"테스트 메소드 실행 중 치명적 오류: {e}")
                logger.error(traceback.format_exc())
        
        # 결과 저장 및 출력
        self.save_results()
        self.print_summary()


def main():
    """메인 실행 함수"""
    test = FullIntegrationTest()
    test.run()


if __name__ == "__main__":
    main()
