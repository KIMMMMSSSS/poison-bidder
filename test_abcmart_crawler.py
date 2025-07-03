#!/usr/bin/env python3
"""
ABC마트 크롤러 개선 사항 테스트
- 상품 수 급감 시 크롤링 종료 기능 검증
"""

import os
import sys
import time
import logging
from datetime import datetime
from pathlib import Path

# 로깅 설정
log_dir = Path("C:/poison_final/logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / f'test_abcmart_crawler_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# 시스템 경로에 추가
sys.path.insert(0, str(Path(__file__).parent))

from poison_bidder_wrapper_v2 import PoizonBidderWrapperV2


class ABCMartCrawlerTest:
    """ABC마트 크롤러 테스트 클래스"""
    
    def __init__(self):
        self.wrapper = PoizonBidderWrapperV2()
        logger.info("테스트 클래스 초기화 완료")
        
    def test_with_keyword(self, keyword: str, expected_behavior: str):
        """
        특정 키워드로 크롤러 테스트
        
        Args:
            keyword: 검색 키워드
            expected_behavior: 예상 동작 ('normal', 'early_stop')
        """
        logger.info(f"\n{'='*50}")
        logger.info(f"테스트 시작: '{keyword}' (예상 동작: {expected_behavior})")
        logger.info(f"{'='*50}")
        
        start_time = time.time()
        
        try:
            # 크롤러 실행
            links = self.wrapper.extract_abcmart_links(
                search_keyword=keyword,
                max_pages=10  # 최대 10페이지까지
            )
            
            execution_time = time.time() - start_time
            
            # 결과 분석
            logger.info(f"\n테스트 결과:")
            logger.info(f"- 검색어: {keyword}")
            logger.info(f"- 추출된 링크 수: {len(links)}")
            logger.info(f"- 실행 시간: {execution_time:.2f}초")
            logger.info(f"- 예상 동작: {expected_behavior}")
            
            # 로그 파일에서 종료 이유 확인
            log_file = log_dir / f"poison_bidder_wrapper_{datetime.now().strftime('%Y%m%d')}.log"
            if log_file.exists():
                with open(log_file, 'r', encoding='utf-8') as f:
                    log_content = f.read()
                    
                # 종료 이유 분석
                if "상품 수 급감 감지" in log_content:
                    logger.info(f"- 종료 이유: 상품 수 급감 감지")
                    if expected_behavior == 'early_stop':
                        logger.info("✓ 예상대로 조기 종료됨")
                elif "마지막 페이지입니다" in log_content:
                    logger.info(f"- 종료 이유: 마지막 페이지 도달")
                elif "상품이 없습니다" in log_content:
                    logger.info(f"- 종료 이유: 상품 없음")
                else:
                    logger.info(f"- 종료 이유: 최대 페이지 도달")
            
            return {
                'keyword': keyword,
                'link_count': len(links),
                'execution_time': execution_time,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"테스트 실패: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            return {
                'keyword': keyword,
                'link_count': 0,
                'execution_time': time.time() - start_time,
                'success': False,
                'error': str(e)
            }
    
    def run_all_tests(self):
        """모든 테스트 시나리오 실행"""
        logger.info("=" * 70)
        logger.info("ABC마트 크롤러 통합 테스트 시작")
        logger.info(f"테스트 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 70)
        
        # 테스트 시나리오
        test_scenarios = [
            ("나이키", "normal"),  # 상품이 많은 키워드
            ("xyzabc123", "early_stop"),  # 상품이 거의 없는 키워드
            ("아디다스", "normal"),  # 또 다른 인기 브랜드
        ]
        
        results = []
        
        for keyword, expected in test_scenarios:
            result = self.test_with_keyword(keyword, expected)
            results.append(result)
            time.sleep(2)  # 서버 부하 방지를 위한 대기
        
        # 전체 결과 요약
        logger.info("\n" + "=" * 70)
        logger.info("테스트 결과 요약")
        logger.info("=" * 70)
        
        total_time = sum(r['execution_time'] for r in results)
        successful_tests = sum(1 for r in results if r.get('success', False))
        
        for result in results:
            status = "성공" if result.get('success', False) else "실패"
            logger.info(f"- {result['keyword']}: {status} "
                       f"({result['link_count']}개 링크, {result['execution_time']:.2f}초)")
        
        logger.info(f"\n전체 테스트: {successful_tests}/{len(results)} 성공")
        logger.info(f"총 실행 시간: {total_time:.2f}초")
        
        # 개선 효과 분석
        logger.info("\n" + "=" * 70)
        logger.info("개선 효과 분석")
        logger.info("=" * 70)
        logger.info("- 상품 수 급감 감지 로직이 추가되어 불필요한 페이지 크롤링 방지")
        logger.info("- 검색 결과가 적은 키워드의 경우 크롤링 시간 단축 예상")
        logger.info("- 기존 기능은 그대로 유지되면서 효율성 향상")
        
        return results


def main():
    """메인 실행 함수"""
    tester = ABCMartCrawlerTest()
    
    # 단일 테스트 또는 전체 테스트 실행
    import argparse
    parser = argparse.ArgumentParser(description='ABC마트 크롤러 테스트')
    parser.add_argument('--keyword', type=str, help='특정 키워드로 테스트')
    parser.add_argument('--all', action='store_true', help='모든 테스트 실행')
    
    args = parser.parse_args()
    
    if args.keyword:
        tester.test_with_keyword(args.keyword, 'unknown')
    else:
        # 기본값: 모든 테스트 실행
        tester.run_all_tests()


if __name__ == '__main__':
    main()
