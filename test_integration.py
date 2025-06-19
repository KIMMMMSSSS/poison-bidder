#!/usr/bin/env python3
"""
포이즌 자동 입찰 시스템 통합 테스트
pickle 오류 수정 및 ABC마트 병렬 스크래핑 검증
"""

import os
import sys
import time
import json
import logging
from datetime import datetime
from pathlib import Path

# 로깅 설정
log_dir = Path("C:/poison_final/logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / f'integration_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def test_poison_bidding():
    """포이즌 입찰 테스트 (pickle 오류 수정 확인)"""
    logger.info("=== 포이즌 입찰 테스트 시작 ===")
    
    try:
        from poison_bidder_wrapper_v2 import PoizonBidderWrapperV2
        
        # 테스트 데이터
        test_data = [
            (1, "나이키", "DV3853-002", "BLACK", "270", 50000),
            (2, "나이키", "DV3853-002", "BLACK", "275", 50000),
            (3, "아디다스", "GY9425", "WHITE", "280", 60000),
        ]
        
        # Wrapper 인스턴스 생성
        logger.info("포이즌 입찰 Wrapper 초기화...")
        wrapper = PoizonBidderWrapperV2(
            min_profit=5000,
            worker_count=2  # 테스트용으로 2개만
        )
        
        # 입찰 실행
        logger.info(f"입찰 실행 중... (테스트 데이터 {len(test_data)}개)")
        start_time = time.time()
        
        result = wrapper.run_bidding(bid_data_list=test_data)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # 결과 검증
        if result['status'] == 'success':
            logger.info(f"✅ 포이즌 입찰 테스트 성공!")
            logger.info(f"   - 실행 시간: {execution_time:.2f}초")
            logger.info(f"   - 완료: {result['completed']}/{result['total_items']}")
            logger.info(f"   - 성공: {result['success']}, 실패: {result['failed']}")
            return True
        else:
            logger.error(f"❌ 포이즌 입찰 테스트 실패: {result.get('message')}")
            return False
            
    except Exception as e:
        logger.error(f"❌ 포이즌 입찰 테스트 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_abcmart_scraping():
    """ABC마트 병렬 스크래핑 테스트"""
    logger.info("\n=== ABC마트 병렬 스크래핑 테스트 시작 ===")
    
    try:
        from abcmart_scraper_improved_backup import AbcmartMultiprocessScraper
        
        # 테스트 URL (실제 상품 5개)
        test_urls = [
            "https://abcmart.a-rt.com/product?prdtNo=1010070311",
            "https://abcmart.a-rt.com/product?prdtNo=1010070312",
            "https://abcmart.a-rt.com/product?prdtNo=1010070313",
            "https://abcmart.a-rt.com/product?prdtNo=1010070314",
            "https://abcmart.a-rt.com/product?prdtNo=1010070315",
        ]
        
        # 멀티프로세스 스크래퍼 초기화
        logger.info("ABC마트 멀티프로세스 스크래퍼 초기화...")
        scraper = AbcmartMultiprocessScraper(max_workers=3)  # 테스트용으로 3개
        
        # 스크래핑 실행
        logger.info(f"스크래핑 실행 중... (URL {len(test_urls)}개)")
        start_time = time.time()
        
        products_data = scraper.run_multiprocess(test_urls, output_file=None)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # 결과 검증
        if products_data and len(products_data) > 0:
            logger.info(f"✅ ABC마트 스크래핑 테스트 성공!")
            logger.info(f"   - 실행 시간: {execution_time:.2f}초")
            logger.info(f"   - 평균 처리 시간: {execution_time/len(test_urls):.2f}초/URL")
            logger.info(f"   - 스크래핑 성공: {len(products_data)}/{len(test_urls)}")
            
            # 샘플 데이터 출력
            if products_data:
                sample = products_data[0]
                logger.info(f"   - 샘플 데이터: {sample['brand']} - {sample['product_code']}")
                
            return True
        else:
            logger.error(f"❌ ABC마트 스크래핑 테스트 실패: 데이터 없음")
            return False
            
    except Exception as e:
        logger.error(f"❌ ABC마트 스크래핑 테스트 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_auto_bidding_integration():
    """auto_bidding 통합 테스트"""
    logger.info("\n=== Auto Bidding 통합 테스트 시작 ===")
    
    try:
        from auto_bidding import AutoBidding
        
        # AutoBidding 인스턴스 생성
        logger.info("AutoBidding 인스턴스 생성...")
        auto_bidder = AutoBidding()
        
        # ABC마트 테스트 (링크 추출은 스킵하고 직접 URL 제공)
        test_urls = [
            "https://abcmart.a-rt.com/product?prdtNo=1010070311",
            "https://abcmart.a-rt.com/product?prdtNo=1010070312",
        ]
        
        logger.info("ABC마트 스크래핑 메서드 테스트...")
        start_time = time.time()
        
        # _scrape_items_auto 메서드 직접 테스트
        items = auto_bidder._scrape_items_auto("abcmart", test_urls)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        if items and len(items) > 0:
            logger.info(f"✅ Auto Bidding 통합 테스트 성공!")
            logger.info(f"   - 실행 시간: {execution_time:.2f}초")
            logger.info(f"   - 아이템 수: {len(items)}개")
            
            # 샘플 아이템 출력
            if items:
                sample = items[0]
                logger.info(f"   - 샘플 아이템: {sample.get('brand')} - {sample.get('size')} - {sample.get('price')}원")
                
            return True
        else:
            logger.error(f"❌ Auto Bidding 통합 테스트 실패: 아이템 없음")
            return False
            
    except Exception as e:
        logger.error(f"❌ Auto Bidding 통합 테스트 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def check_log_files():
    """로그 파일 생성 확인"""
    logger.info("\n=== 로그 파일 확인 ===")
    
    log_files = list(log_dir.glob("*.log"))
    
    logger.info(f"로그 디렉토리: {log_dir}")
    logger.info(f"로그 파일 수: {len(log_files)}개")
    
    # 최근 로그 파일 5개 표시
    recent_logs = sorted(log_files, key=lambda x: x.stat().st_mtime, reverse=True)[:5]
    for log_file in recent_logs:
        size_kb = log_file.stat().st_size / 1024
        logger.info(f"   - {log_file.name} ({size_kb:.2f} KB)")
    
    return len(log_files) > 0


def main():
    """메인 테스트 실행"""
    logger.info("=" * 80)
    logger.info("포이즌 자동 입찰 시스템 통합 테스트")
    logger.info("=" * 80)
    
    test_results = {
        "poison_bidding": False,
        "abcmart_scraping": False,
        "auto_bidding_integration": False,
        "log_files": False
    }
    
    # 1. 포이즌 입찰 테스트
    logger.info("\n[1/4] 포이즌 입찰 테스트")
    test_results["poison_bidding"] = test_poison_bidding()
    
    # 2. ABC마트 병렬 스크래핑 테스트
    logger.info("\n[2/4] ABC마트 병렬 스크래핑 테스트")
    test_results["abcmart_scraping"] = test_abcmart_scraping()
    
    # 3. Auto Bidding 통합 테스트
    logger.info("\n[3/4] Auto Bidding 통합 테스트")
    test_results["auto_bidding_integration"] = test_auto_bidding_integration()
    
    # 4. 로그 파일 확인
    logger.info("\n[4/4] 로그 파일 확인")
    test_results["log_files"] = check_log_files()
    
    # 최종 결과
    logger.info("\n" + "=" * 80)
    logger.info("테스트 결과 요약")
    logger.info("=" * 80)
    
    total_tests = len(test_results)
    passed_tests = sum(test_results.values())
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\n총 {total_tests}개 테스트 중 {passed_tests}개 성공")
    
    if passed_tests == total_tests:
        logger.info("\n🎉 모든 테스트 통과! 시스템이 정상적으로 작동합니다.")
        return 0
    else:
        logger.error(f"\n⚠️ {total_tests - passed_tests}개 테스트 실패")
        return 1


if __name__ == "__main__":
    sys.exit(main())
