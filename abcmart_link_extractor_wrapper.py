#!/usr/bin/env python3
"""
ABC마트 검색 링크 추출기 (unified_bidding 연동용)
poison_bidder_wrapper_v2.py의 extract_abcmart_links 메서드 대체
"""

import sys
import os
import json
import logging
from datetime import datetime
from pathlib import Path

# 프로젝트 경로 추가
sys.path.append('C:/poison_final')

from abcmart_search_scraper import ABCMartSearchScraper

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ABCMartLinkExtractor:
    """ABC마트 링크 추출기 (unified_bidding 연동용)"""
    
    def __init__(self):
        self.scraper = None
        
    def extract_abcmart_links(self, search_keyword, max_pages=10):
        """
        ABC마트에서 검색어로 상품 링크 추출
        
        Args:
            search_keyword: 검색 키워드
            max_pages: 최대 검색 페이지 수
            
        Returns:
            list: 추출된 상품 링크 리스트
        """
        try:
            logger.info(f"ABC마트 링크 추출 시작: '{search_keyword}'")
            
            # 스크래퍼 초기화
            self.scraper = ABCMartSearchScraper(headless=True)  # 배치 실행용 headless
            
            # 검색 실행
            links = self.scraper.run(search_keyword, max_pages)
            
            if links:
                logger.info(f"ABC마트 링크 추출 성공: {len(links)}개")
                return links
            else:
                logger.warning("ABC마트 링크 추출 결과 없음")
                return []
                
        except Exception as e:
            logger.error(f"ABC마트 링크 추출 실패: {e}")
            return []
        finally:
            # 스크래퍼 정리
            if self.scraper and self.scraper.driver:
                try:
                    self.scraper.driver.quit()
                except:
                    pass


# poison_bidder_wrapper_v2.py 호환을 위한 클래스
class PoizonBidderWrapperV2:
    """poison_bidder_wrapper_v2 호환 래퍼"""
    
    def __init__(self):
        self.extractor = ABCMartLinkExtractor()
        
    def extract_abcmart_links(self, search_keyword, max_pages=10):
        """ABC마트 링크 추출 (호환성 메서드)"""
        return self.extractor.extract_abcmart_links(search_keyword, max_pages)


def test_extraction():
    """추출 테스트"""
    print("=== ABC마트 링크 추출 테스트 ===\n")
    
    # 테스트 검색어
    test_keywords = ["아디다스신발", "나이키", "뉴발란스"]
    
    # 래퍼 생성
    wrapper = PoizonBidderWrapperV2()
    
    for keyword in test_keywords:
        print(f"\n검색어: {keyword}")
        
        # 링크 추출 (3페이지만 테스트)
        links = wrapper.extract_abcmart_links(keyword, max_pages=3)
        
        if links:
            print(f"✅ {len(links)}개 링크 추출")
            # 처음 5개만 출력
            for i, link in enumerate(links[:5], 1):
                print(f"  {i}. {link}")
            if len(links) > 5:
                print(f"  ... 외 {len(links) - 5}개")
        else:
            print("❌ 링크 추출 실패")
            
    print("\n테스트 완료!")


if __name__ == "__main__":
    test_extraction()
    input("\nEnter를 눌러 종료하세요...")
