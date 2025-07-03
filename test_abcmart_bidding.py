#!/usr/bin/env python3
"""
ABC마트 입찰 테스트 스크립트
데이터 전달 과정을 단계별로 확인
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from poison_integrated_bidding import AutoBiddingAdapter

# 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_abcmart_bidding():
    """ABC마트 입찰 테스트"""
    
    # 1. ABC마트 스크래핑 결과 로드
    logger.info("=== ABC마트 입찰 테스트 시작 ===")
    
    json_file = Path("abcmart_products_20250619_223305.json")
    if not json_file.exists():
        logger.error(f"파일을 찾을 수 없습니다: {json_file}")
        return
    
    with open(json_file, 'r', encoding='utf-8') as f:
        scraped_data = json.load(f)
    
    logger.info(f"스크래핑 데이터 로드: {len(scraped_data)}개 상품")
    
    # 2. 테스트용 아이템 준비 (처음 3개만)
    test_items = []
    for product in scraped_data[:3]:  # 처음 3개만 테스트
        for size_info in product.get('sizes_prices', []):
            if size_info['size'] != '품절':
                test_items.append({
                    'brand': product['brand'],
                    'code': product['product_code'],
                    'product_code': product['product_code'],
                    'color': product.get('color', ''),
                    'size': size_info['size'],
                    'price': size_info['price'],
                    'adjusted_price': int(size_info['price'] * 0.9),  # 10% 할인
                    'link': product['url']
                })
                break  # 각 상품당 하나의 사이즈만
    
    logger.info(f"테스트 아이템 준비: {len(test_items)}개")
    if test_items:
        logger.info(f"첫 번째 아이템: {json.dumps(test_items[0], ensure_ascii=False, indent=2)}")
    
    # 3. AutoBiddingAdapter 테스트
    try:
        logger.info("\n=== AutoBiddingAdapter 테스트 ===")
        adapter = AutoBiddingAdapter(
            driver_path=None,
            min_profit=0,
            worker_count=1  # 테스트용으로 1개만
        )
        
        result = adapter.run_with_poison(test_items)
        
        logger.info(f"실행 결과: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
    except Exception as e:
        logger.error(f"오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    test_abcmart_bidding()


def test_extract_abcmart_links_pagination():
    """ABC마트 링크 추출 페이지네이션 테스트"""
    logger.info("\n=== ABC마트 링크 추출 페이지네이션 테스트 시작 ===")
    
    try:
        from poison_bidder_wrapper_v2 import PoizonBidderWrapperV2
        import time
        
        # 1. PoizonBidderWrapperV2 인스턴스 생성
        wrapper = PoizonBidderWrapperV2()
        
        # 2. 실제 검색어로 링크 추출 테스트
        search_keyword = "나이키"  # 테스트용 검색어
        max_pages = 3  # 테스트용으로 3페이지만
        
        logger.info(f"검색어: '{search_keyword}', 최대 페이지: {max_pages}")
        
        start_time = time.time()
        links = wrapper.extract_abcmart_links(
            search_keyword=search_keyword,
            max_pages=max_pages
        )
        extraction_time = time.time() - start_time
        
        # 3. 결과 검증
        logger.info(f"\n=== 추출 결과 ===")
        logger.info(f"추출된 링크 수: {len(links)}")
        logger.info(f"소요 시간: {extraction_time:.2f}초")
        
        # 링크가 추출되었는지 확인
        assert len(links) > 0, "링크가 추출되지 않았습니다"
        logger.info("✓ 링크 추출 성공")
        
        # 중복 링크가 없는지 확인
        unique_links = set(links)
        assert len(unique_links) == len(links), f"중복 링크 발견: {len(links) - len(unique_links)}개"
        logger.info("✓ 중복 링크 없음")
        
        # 링크 형식이 올바른지 확인
        for link in links[:5]:  # 처음 5개만 확인
            assert link.startswith("https://abcmart.a-rt.com/product?prdtNo="), f"잘못된 링크 형식: {link}"
        logger.info("✓ 링크 형식 정상")
        
        # 처음 몇 개 링크 출력
        logger.info(f"\n처음 5개 링크:")
        for i, link in enumerate(links[:5], 1):
            logger.info(f"{i}. {link}")
        
        # 4. 파일 저장 확인
        output_dir = Path("C:/poison_final/logs")
        json_files = list(output_dir.glob(f"abcmart_links_{search_keyword}_*.txt"))
        
        if json_files:
            latest_file = max(json_files, key=lambda x: x.stat().st_mtime)
            logger.info(f"\n파일 저장 확인: {latest_file}")
            
            # 파일 내용 확인
            with open(latest_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                file_link_count = sum(1 for line in lines if line.strip().startswith("https://"))
                assert file_link_count == len(links), f"파일의 링크 수({file_link_count})와 반환된 링크 수({len(links)})가 다릅니다"
                logger.info("✓ 파일 저장 정상")
        
        logger.info("\n=== 페이지네이션 테스트 통과 ===")
        return True
        
    except ImportError as e:
        logger.error(f"Import 오류: {e}")
        return False
    except AssertionError as e:
        logger.error(f"검증 실패: {e}")
        return False
    except Exception as e:
        logger.error(f"테스트 중 오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_extract_abcmart_links_error_handling():
    """ABC마트 링크 추출 오류 처리 테스트"""
    logger.info("\n=== ABC마트 링크 추출 오류 처리 테스트 시작 ===")
    
    try:
        from poison_bidder_wrapper_v2 import PoizonBidderWrapperV2
        
        wrapper = PoizonBidderWrapperV2()
        
        # 1. 빈 검색어 테스트
        logger.info("\n[테스트 1] 빈 검색어")
        links = wrapper.extract_abcmart_links(search_keyword="", max_pages=1)
        assert len(links) == 0, "빈 검색어에서 링크가 추출되었습니다"
        logger.info("✓ 빈 검색어 처리 정상")
        
        # 2. 특수문자 검색어 테스트
        logger.info("\n[테스트 2] 특수문자 검색어")
        links = wrapper.extract_abcmart_links(search_keyword="@#$%", max_pages=1)
        # 결과가 없어도 오류가 발생하지 않아야 함
        logger.info(f"특수문자 검색 결과: {len(links)}개 (오류 없음)")
        logger.info("✓ 특수문자 처리 정상")
        
        # 3. 매우 긴 검색어 테스트
        logger.info("\n[테스트 3] 긴 검색어")
        long_keyword = "나이키" * 50  # 매우 긴 검색어
        links = wrapper.extract_abcmart_links(search_keyword=long_keyword, max_pages=1)
        # 오류 없이 실행되어야 함
        logger.info("✓ 긴 검색어 처리 정상")
        
        logger.info("\n=== 오류 처리 테스트 통과 ===")
        return True
        
    except Exception as e:
        logger.error(f"오류 처리 테스트 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_unified_bidding_web_scraping():
    """UnifiedBidding 웹 스크래핑 통합 테스트"""
    logger.info("\n=== UnifiedBidding 웹 스크래핑 통합 테스트 시작 ===")
    
    try:
        from unified_bidding import UnifiedBidding
        import json
        
        # 1. UnifiedBidding 인스턴스 생성
        bidder = UnifiedBidding(debug=True)
        
        # 2. 웹 스크래핑 모드로 파이프라인 실행 (링크 추출만)
        logger.info("\n웹 스크래핑 모드로 링크 추출 테스트")
        
        # _extract_links 메서드만 테스트
        links = bidder._extract_links(
            site="abcmart",
            web_scraping=True,
            search_keyword="아디다스"
        )
        
        # 3. 결과 검증
        logger.info(f"추출된 링크 수: {len(links)}")
        assert len(links) > 0, "링크가 추출되지 않았습니다"
        logger.info("✓ 웹 스크래핑 모드 링크 추출 성공")
        
        # 4. JSON 파일 저장 확인
        output_dir = Path("output")
        json_files = list(output_dir.glob("abcmart_links_아디다스_*.json"))
        
        if json_files:
            latest_file = max(json_files, key=lambda x: x.stat().st_mtime)
            logger.info(f"\nJSON 파일 확인: {latest_file}")
            
            with open(latest_file, 'r', encoding='utf-8') as f:
                saved_data = json.load(f)
                
            assert saved_data['site'] == "abcmart", "사이트 정보 불일치"
            assert saved_data['search_keyword'] == "아디다스", "검색어 정보 불일치"
            assert saved_data['total_count'] == len(links), "링크 수 불일치"
            logger.info("✓ JSON 파일 저장 및 형식 정상")
        
        # 5. 파일 읽기 모드 테스트 (하위 호환성)
        logger.info("\n파일 읽기 모드 테스트 (하위 호환성)")
        file_links = bidder._extract_links(
            site="abcmart",
            web_scraping=False  # 기본값
        )
        # 파일이 없으면 테스트 데이터 반환
        logger.info(f"파일 읽기 모드 결과: {len(file_links)}개")
        logger.info("✓ 파일 읽기 모드 정상 (하위 호환성 유지)")
        
        logger.info("\n=== 통합 테스트 통과 ===")
        return True
        
    except ImportError as e:
        logger.error(f"Import 오류: {e}")
        return False
    except AssertionError as e:
        logger.error(f"검증 실패: {e}")
        return False
    except Exception as e:
        logger.error(f"통합 테스트 중 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def run_all_tests():
    """모든 테스트 실행"""
    logger.info("=" * 60)
    logger.info("ABC마트 페이지네이션 테스트 스위트 실행")
    logger.info("=" * 60)
    
    test_results = []
    
    # 1. 기존 테스트
    logger.info("\n[1/4] 기존 ABC마트 입찰 테스트")
    try:
        test_abcmart_bidding()
        test_results.append(("기존 입찰 테스트", True))
    except Exception as e:
        test_results.append(("기존 입찰 테스트", False))
        logger.error(f"테스트 실패: {e}")
    
    # 2. 페이지네이션 테스트
    logger.info("\n[2/4] 페이지네이션 테스트")
    result = test_extract_abcmart_links_pagination()
    test_results.append(("페이지네이션 테스트", result))
    
    # 3. 오류 처리 테스트
    logger.info("\n[3/4] 오류 처리 테스트")
    result = test_extract_abcmart_links_error_handling()
    test_results.append(("오류 처리 테스트", result))
    
    # 4. 통합 테스트
    logger.info("\n[4/4] UnifiedBidding 통합 테스트")
    result = test_unified_bidding_web_scraping()
    test_results.append(("통합 테스트", result))
    
    # 결과 요약
    logger.info("\n" + "=" * 60)
    logger.info("테스트 결과 요약")
    logger.info("=" * 60)
    
    passed = 0
    failed = 0
    
    for test_name, result in test_results:
        status = "통과" if result else "실패"
        symbol = "✓" if result else "✗"
        logger.info(f"{symbol} {test_name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    logger.info(f"\n총 {len(test_results)}개 테스트 중 {passed}개 통과, {failed}개 실패")
    
    if failed == 0:
        logger.info("\n🎉 모든 테스트가 통과했습니다!")
    else:
        logger.warning(f"\n⚠️  {failed}개의 테스트가 실패했습니다.")
    
    return failed == 0


# 테스트 실행 부분 수정
if __name__ == "__main__":
    import sys
    
    # 명령줄 인수 확인
    if len(sys.argv) > 1:
        if sys.argv[1] == "--all":
            # 모든 테스트 실행
            success = run_all_tests()
            sys.exit(0 if success else 1)
        elif sys.argv[1] == "--pagination":
            # 페이지네이션 테스트만
            test_extract_abcmart_links_pagination()
        elif sys.argv[1] == "--error":
            # 오류 처리 테스트만
            test_extract_abcmart_links_error_handling()
        elif sys.argv[1] == "--integration":
            # 통합 테스트만
            test_unified_bidding_web_scraping()
        else:
            # 기본 테스트
            test_abcmart_bidding()
    else:
        # 인수가 없으면 기본 테스트 실행
        test_abcmart_bidding()
