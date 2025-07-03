#!/usr/bin/env python3
"""
ABC마트 페이지네이션 통합 테스트
"""

import sys
import json
from datetime import datetime
from pathlib import Path

# auto_bidding 모듈 import
from auto_bidding import AutoBidding


def test_abcmart_pagination():
    """ABC마트 페이지네이션 테스트"""
    print("=" * 60)
    print("ABC마트 페이지네이션 통합 테스트 시작")
    print(f"시작 시간: {datetime.now()}")
    print("=" * 60)
    
    # 테스트 설정
    test_keywords = ["운동화"]  # 테스트용 키워드 1개로 제한
    
    # AutoBidding 인스턴스 생성
    bidding = AutoBidding()
    
    # 테스트 결과 저장
    test_results = {
        "test_time": datetime.now().isoformat(),
        "results": []
    }
    
    for keyword in test_keywords:
        print(f"\n키워드 '{keyword}' 테스트 시작...")
        
        try:
            # 링크 추출 테스트
            links = bidding._extract_links_auto("abcmart", keyword)
            
            result = {
                "keyword": keyword,
                "status": "success",
                "link_count": len(links),
                "unique_links": len(set(links)),
                "sample_links": links[:5] if links else []
            }
            
            print(f"✓ 성공: {len(links)}개 링크 추출")
            print(f"  - 고유 링크 수: {len(set(links))}")
            print(f"  - 샘플 링크:")
            for i, link in enumerate(links[:3]):
                print(f"    {i+1}. {link}")
            
        except Exception as e:
            result = {
                "keyword": keyword,
                "status": "error",
                "error": str(e)
            }
            print(f"✗ 오류 발생: {e}")
        
        test_results["results"].append(result)
    
    # 드라이버 정리
    if bidding.driver:
        bidding.driver.quit()
    
    # 결과 저장
    result_file = Path("C:/poison_final/logs/test_abcmart_pagination_result.json")
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(test_results, f, ensure_ascii=False, indent=2)
    
    print(f"\n테스트 결과가 저장되었습니다: {result_file}")
    
    # 요약
    print("\n" + "=" * 60)
    print("테스트 요약:")
    for result in test_results["results"]:
        if result["status"] == "success":
            print(f"✓ {result['keyword']}: {result['link_count']}개 링크 추출")
        else:
            print(f"✗ {result['keyword']}: 오류 - {result.get('error', 'Unknown error')}")
    print("=" * 60)
    
    return test_results


def test_musinsa_regression():
    """무신사 회귀 테스트"""
    print("\n" + "=" * 60)
    print("무신사 회귀 테스트 시작")
    print("=" * 60)
    
    bidding = AutoBidding()
    
    try:
        # 무신사 링크 추출 테스트
        links = bidding._extract_links_auto("musinsa", "나이키")
        print(f"✓ 무신사 링크 추출 정상: {len(links)}개 링크")
        print(f"  샘플: {links[0] if links else 'No links'}")
        
        if bidding.driver:
            bidding.driver.quit()
            
        return True
        
    except Exception as e:
        print(f"✗ 무신사 테스트 실패: {e}")
        if bidding.driver:
            bidding.driver.quit()
        return False


if __name__ == "__main__":
    # ABC마트 페이지네이션 테스트
    abc_results = test_abcmart_pagination()
    
    # 무신사 회귀 테스트
    musinsa_ok = test_musinsa_regression()
    
    # 최종 결과
    print("\n" + "=" * 60)
    print("최종 테스트 결과:")
    print(f"- ABC마트 페이지네이션: {'✓ 성공' if abc_results['results'][0]['status'] == 'success' else '✗ 실패'}")
    print(f"- 무신사 회귀 테스트: {'✓ 성공' if musinsa_ok else '✗ 실패'}")
    print("=" * 60)
