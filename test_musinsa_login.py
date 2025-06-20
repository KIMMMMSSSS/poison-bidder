#!/usr/bin/env python3
"""
무신사 로그인 기능 테스트
무신사 자동 로그인, 쿠키 관리, 최대혜택가 추출 기능을 테스트합니다.
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# 프로젝트 경로 추가
sys.path.append('C:/poison_final')

# 로깅 설정
log_dir = Path('C:/poison_final/logs')
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_dir / f'test_musinsa_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def test_environment_variables():
    """환경변수 로드 테스트"""
    logger.info("=" * 50)
    logger.info("1. 환경변수 로드 테스트")
    logger.info("=" * 50)
    
    # .env 파일 로드
    load_dotenv()
    
    # 무신사 계정 정보 확인
    musinsa_id = os.getenv('MUSINSA_ID')
    musinsa_password = os.getenv('MUSINSA_PASSWORD')
    
    if musinsa_id and musinsa_password:
        logger.info(f"✅ 무신사 ID 로드 성공: {musinsa_id[:3]}***")
        logger.info("✅ 무신사 비밀번호 로드 성공")
        return True
    else:
        logger.error("❌ 무신사 로그인 정보가 .env 파일에 없습니다")
        logger.error("MUSINSA_ID와 MUSINSA_PASSWORD를 .env 파일에 설정해주세요")
        return False


def test_login_manager():
    """LoginManager를 통한 무신사 로그인 테스트"""
    logger.info("\n" + "=" * 50)
    logger.info("2. LoginManager 무신사 로그인 테스트")
    logger.info("=" * 50)
    
    try:
        from login_manager import LoginManager
        
        # LoginManager 인스턴스 생성
        login_mgr = LoginManager('musinsa')
        logger.info("✅ LoginManager 인스턴스 생성 성공")
        
        # 환경변수에서 로그인 정보 가져오기
        musinsa_id = os.getenv('MUSINSA_ID')
        musinsa_password = os.getenv('MUSINSA_PASSWORD')
        
        if not musinsa_id or not musinsa_password:
            logger.error("❌ 환경변수에서 로그인 정보를 찾을 수 없습니다")
            return False
        
        # 자동 로그인 시도
        logger.info("자동 로그인 시도 중...")
        if login_mgr.auto_login(musinsa_id, musinsa_password):
            logger.info("✅ 무신사 자동 로그인 성공")
            
            # 쿠키 저장
            login_mgr.save_cookies()
            logger.info("✅ 쿠키 저장 완료")
            
            # 드라이버 종료
            login_mgr.quit()
            logger.info("✅ 드라이버 종료")
            return True
        else:
            logger.warning("⚠️ 자동 로그인 실패 - 수동 로그인 필요")
            
            # 수동 로그인 시도
            if login_mgr.manual_login():
                logger.info("✅ 무신사 수동 로그인 성공")
                login_mgr.save_cookies()
                login_mgr.quit()
                return True
            else:
                logger.error("❌ 무신사 수동 로그인 실패")
                login_mgr.quit()
                return False
                
    except Exception as e:
        logger.error(f"❌ LoginManager 테스트 중 오류: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_poison_wrapper_integration():
    """PoizonBidderWrapperV2 통합 테스트"""
    logger.info("\n" + "=" * 50)
    logger.info("3. PoizonBidderWrapperV2 통합 테스트")
    logger.info("=" * 50)
    
    try:
        from poison_bidder_wrapper_v2 import PoizonBidderWrapperV2
        
        # 래퍼 인스턴스 생성
        wrapper = PoizonBidderWrapperV2(min_profit=0, worker_count=1)
        logger.info("✅ PoizonBidderWrapperV2 인스턴스 생성 성공")
        
        # 무신사 로그인 확인
        if wrapper.ensure_musinsa_login():
            logger.info("✅ 무신사 로그인 확인 성공")
            
            # 쿠키 가져오기 테스트
            cookies = wrapper.get_musinsa_cookies()
            if cookies:
                logger.info(f"✅ 무신사 쿠키 가져오기 성공 (쿠키 수: {len(cookies)}개)")
            else:
                logger.warning("⚠️ 무신사 쿠키가 없습니다")
            
            return True
        else:
            logger.error("❌ 무신사 로그인 확인 실패")
            return False
            
    except Exception as e:
        logger.error(f"❌ PoizonBidderWrapperV2 테스트 중 오류: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_max_benefit_price_extraction():
    """최대혜택가 추출 테스트"""
    logger.info("\n" + "=" * 50)
    logger.info("4. 무신사 최대혜택가 추출 테스트")
    logger.info("=" * 50)
    
    # 테스트용 무신사 상품 URL (실제 상품)
    test_urls = [
        "https://www.musinsa.com/products/2545799",  # 샘플 상품 1
        "https://www.musinsa.com/products/4409450",  # 샘플 상품 2
    ]
    
    try:
        from poison_bidder_wrapper_v2 import PoizonBidderWrapperV2
        
        # 래퍼 인스턴스 생성
        wrapper = PoizonBidderWrapperV2(min_profit=0, worker_count=1)
        
        # 각 URL에 대해 테스트
        success_count = 0
        for url in test_urls:
            logger.info(f"\n테스트 URL: {url}")
            
            try:
                # 최대혜택가 추출
                max_benefit_price = wrapper.extract_musinsa_max_benefit_price(url)
                
                if max_benefit_price:
                    logger.info(f"✅ 최대혜택가 추출 성공: {max_benefit_price:,}원")
                    success_count += 1
                else:
                    logger.warning(f"⚠️ 최대혜택가를 찾을 수 없습니다")
                    
            except Exception as e:
                logger.error(f"❌ URL 처리 중 오류: {e}")
        
        logger.info(f"\n테스트 결과: {success_count}/{len(test_urls)} 성공")
        return success_count > 0
        
    except Exception as e:
        logger.error(f"❌ 최대혜택가 추출 테스트 중 오류: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """모든 테스트 실행"""
    logger.info("=" * 70)
    logger.info("무신사 로그인 기능 통합 테스트 시작")
    logger.info("=" * 70)
    
    test_results = {
        "환경변수 로드": False,
        "LoginManager 로그인": False,
        "PoizonWrapper 통합": False,
        "최대혜택가 추출": False
    }
    
    # 1. 환경변수 테스트
    test_results["환경변수 로드"] = test_environment_variables()
    
    # 환경변수가 없으면 이후 테스트 불가
    if not test_results["환경변수 로드"]:
        logger.error("\n환경변수 설정이 필요합니다. 테스트를 중단합니다.")
        return test_results
    
    # 2. LoginManager 테스트
    test_results["LoginManager 로그인"] = test_login_manager()
    
    # 3. PoizonWrapper 통합 테스트
    test_results["PoizonWrapper 통합"] = test_poison_wrapper_integration()
    
    # 4. 최대혜택가 추출 테스트
    if test_results["PoizonWrapper 통합"]:
        test_results["최대혜택가 추출"] = test_max_benefit_price_extraction()
    
    # 최종 결과 출력
    logger.info("\n" + "=" * 70)
    logger.info("테스트 결과 요약")
    logger.info("=" * 70)
    
    total_tests = len(test_results)
    passed_tests = sum(test_results.values())
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\n총 {total_tests}개 테스트 중 {passed_tests}개 성공")
    
    if passed_tests == total_tests:
        logger.info("🎉 모든 테스트 통과!")
    else:
        logger.warning(f"⚠️ {total_tests - passed_tests}개 테스트 실패")
    
    return test_results


if __name__ == "__main__":
    try:
        # 테스트 실행
        results = run_all_tests()
        
        # 테스트 완료
        logger.info("\n테스트 완료. 로그 파일을 확인하세요.")
        logger.info(f"로그 위치: {log_dir}")
        
        # 모든 테스트 통과 여부
        all_passed = all(results.values())
        sys.exit(0 if all_passed else 1)
        
    except KeyboardInterrupt:
        logger.info("\n사용자에 의해 테스트가 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n테스트 실행 중 예상치 못한 오류: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
