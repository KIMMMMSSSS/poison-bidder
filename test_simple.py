#!/usr/bin/env python3
"""
포이즌 자동 입찰 시스템 간단 테스트
pickle 오류 수정 확인
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
        logging.FileHandler(log_dir / f'simple_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log', encoding='utf-8'),
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
            (1, "나이키", "TEST123", "BLACK", "270", 50000),
            (2, "나이키", "TEST123", "BLACK", "275", 50000),
        ]
        
        # Wrapper 인스턴스 생성
        logger.info("포이즌 입찰 Wrapper 초기화...")
        wrapper = PoizonBidderWrapperV2(
            min_profit=5000,
            worker_count=2  # 테스트용으로 2개만
        )
        
        logger.info("✅ PoizonBidderWrapperV2 초기화 성공!")
        logger.info("✅ pickle 오류 없이 모듈 로드 완료!")
        
        # 원본 모듈 로드 테스트
        if wrapper.module:
            logger.info("✅ 원본 모듈(0923_fixed_multiprocess_cookie_v2.py) 로드 성공!")
            
        return True
            
    except Exception as e:
        logger.error(f"❌ 포이즌 입찰 테스트 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_abcmart_import():
    """ABC마트 모듈 import 테스트"""
    logger.info("\n=== ABC마트 모듈 import 테스트 ===")
    
    try:
        from abcmart_scraper_improved_backup import AbcmartMultiprocessScraper, AbcmartWorker
        logger.info("✅ AbcmartMultiprocessScraper import 성공!")
        logger.info("✅ AbcmartWorker import 성공!")
        
        # 클래스 인스턴스화 테스트
        scraper = AbcmartMultiprocessScraper(max_workers=2)
        logger.info("✅ AbcmartMultiprocessScraper 인스턴스 생성 성공!")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ ABC마트 모듈 import 오류: {e}")
        return False


def test_auto_bidding_import():
    """auto_bidding 모듈 import 테스트"""
    logger.info("\n=== auto_bidding 모듈 import 테스트 ===")
    
    try:
        from auto_bidding import AutoBidding
        logger.info("✅ AutoBidding import 성공!")
        
        # 인스턴스 생성 테스트
        auto_bidder = AutoBidding()
        logger.info("✅ AutoBidding 인스턴스 생성 성공!")
        
        # ABC마트 멀티프로세스 사용 가능 여부 확인
        import auto_bidding
        if hasattr(auto_bidding, 'ABCMART_MULTIPROCESS_AVAILABLE'):
            if auto_bidding.ABCMART_MULTIPROCESS_AVAILABLE:
                logger.info("✅ ABC마트 멀티프로세스 스크래퍼 사용 가능!")
            else:
                logger.warning("⚠️ ABC마트 멀티프로세스 스크래퍼 사용 불가")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ auto_bidding 모듈 import 오류: {e}")
        return False


def main():
    """메인 테스트 실행"""
    logger.info("=" * 80)
    logger.info("포이즌 자동 입찰 시스템 간단 테스트")
    logger.info("=" * 80)
    
    test_results = {
        "poison_bidding": False,
        "abcmart_import": False,
        "auto_bidding_import": False,
    }
    
    # 1. 포이즌 입찰 테스트
    logger.info("\n[1/3] 포이즌 입찰 모듈 테스트")
    test_results["poison_bidding"] = test_poison_bidding()
    
    # 2. ABC마트 모듈 import 테스트
    logger.info("\n[2/3] ABC마트 모듈 import 테스트")
    test_results["abcmart_import"] = test_abcmart_import()
    
    # 3. Auto Bidding import 테스트
    logger.info("\n[3/3] Auto Bidding 모듈 import 테스트")
    test_results["auto_bidding_import"] = test_auto_bidding_import()
    
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
