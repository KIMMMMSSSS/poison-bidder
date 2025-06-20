#!/usr/bin/env python3
"""
자동 입찰 시스템 통합 테스트
ABC마트와 그랜드스테이지 모두에서 링크가 수집되는지 확인
"""

import sys
import logging
from pathlib import Path
from datetime import datetime

# 로깅 설정
log_dir = Path("C:/poison_final/logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / f'test_auto_bidding_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def test_abcmart_link_extraction():
    """ABC마트 계열 링크 추출 테스트"""
    logger.info("=== ABC마트 계열 링크 추출 테스트 시작 ===")
    
    try:
        from auto_bidding import AutoBidding
        
        # AutoBidding 인스턴스 생성
        auto_bidder = AutoBidding()
        
        # 테스트 키워드 설정
        test_keywords = ["운동화"]  # 간단한 테스트를 위해 하나의 키워드만 사용
        
        # 설정 업데이트 (테스트를 위해 적은 페이지만 크롤링)
        auto_bidder.config['extraction']['max_pages'] = 3  # 3페이지만 테스트
        auto_bidder.config['extraction']['page_wait_time'] = 2
        auto_bidder.config['extraction']['empty_page_threshold'] = 2
        
        logger.info(f"테스트 설정:")
        logger.info(f"- 키워드: {test_keywords}")
        logger.info(f"- 최대 페이지: {auto_bidder.config['extraction']['max_pages']}")
        logger.info(f"- 빈 페이지 임계값: {auto_bidder.config['extraction']['empty_page_threshold']}")
        
        # 링크 추출 실행
        all_links = []
        for keyword in test_keywords:
            logger.info(f"\n키워드 '{keyword}' 테스트 시작...")
            links = auto_bidder._extract_links_auto('abcmart', keyword)
            all_links.extend(links)
            
            # 결과 분석
            logger.info(f"\n=== 테스트 결과 분석 ===")
            logger.info(f"총 수집된 링크 수: {len(links)}")
            
            # 채널별로 링크 분류
            abcmart_links = [link for link in links if 'abcmart.a-rt.com' in link]
            grandstage_links = [link for link in links if 'grandstage.a-rt.com' in link]
            
            logger.info(f"\n채널별 링크 분포:")
            logger.info(f"- ABC마트 링크: {len(abcmart_links)}개")
            logger.info(f"- 그랜드스테이지 링크: {len(grandstage_links)}개")
            
            # 샘플 링크 출력
            if abcmart_links:
                logger.info(f"\nABC마트 샘플 링크 (최대 3개):")
                for i, link in enumerate(abcmart_links[:3]):
                    logger.info(f"  {i+1}. {link}")
            
            if grandstage_links:
                logger.info(f"\n그랜드스테이지 샘플 링크 (최대 3개):")
                for i, link in enumerate(grandstage_links[:3]):
                    logger.info(f"  {i+1}. {link}")
            
            # 테스트 성공 여부 판단
            if len(abcmart_links) > 0 and len(grandstage_links) > 0:
                logger.info("\n✓ 테스트 성공: 두 채널 모두에서 링크가 수집되었습니다!")
                return True
            elif len(abcmart_links) > 0:
                logger.warning("\n△ 부분 성공: ABC마트에서만 링크가 수집되었습니다.")
                return False
            elif len(grandstage_links) > 0:
                logger.warning("\n△ 부분 성공: 그랜드스테이지에서만 링크가 수집되었습니다.")
                return False
            else:
                logger.error("\n✗ 테스트 실패: 어떤 채널에서도 링크가 수집되지 않았습니다.")
                return False
                
    except Exception as e:
        logger.error(f"테스트 중 오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
    finally:
        # 드라이버 정리
        if hasattr(auto_bidder, 'driver') and auto_bidder.driver:
            auto_bidder.driver.quit()


def main():
    """메인 테스트 실행"""
    logger.info("자동 입찰 시스템 통합 테스트 시작\n")
    
    # ABC마트 계열 테스트
    success = test_abcmart_link_extraction()
    
    if success:
        logger.info("\n=== 전체 테스트 성공 ===")
        logger.info("ABC마트와 그랜드스테이지 모두에서 링크 수집이 정상적으로 작동합니다.")
    else:
        logger.warning("\n=== 테스트 부분 성공 또는 실패 ===")
        logger.warning("일부 채널에서 링크 수집이 제대로 작동하지 않을 수 있습니다.")
        logger.warning("로그를 확인하여 문제를 진단해주세요.")


if __name__ == '__main__':
    main()
