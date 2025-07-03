#!/usr/bin/env python3
"""
통합 모듈 테스트 스크립트
"""

from unified_bidding import UnifiedBidding
import json

def test_unified_bidding():
    """통합 모듈 테스트"""
    print("=== K-Fashion 통합 입찰 시스템 테스트 ===\n")
    
    # 1. 초기화 테스트
    print("[1] 시스템 초기화...")
    try:
        bidder = UnifiedBidding()
        print("✓ 초기화 성공")
    except Exception as e:
        print(f"✗ 초기화 실패: {e}")
        return
    
    # 2. 설정 확인
    print("\n[2] 설정 파일 확인...")
    strategies = bidder.config.get('strategies', {})
    print(f"✓ 발견된 전략: {list(strategies.keys())}")
    
    # 3. 파이프라인 실행 테스트
    print("\n[3] 파이프라인 실행 (테스트 모드)...")
    result = bidder.run_pipeline(
        site="musinsa",
        strategy_id="basic",
        exec_mode="manual",
        process_mode="sequential"
    )
    
    # 4. 결과 출력
    print("\n[4] 실행 결과:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    # 5. 상태 확인
    if result['status'] == 'success':
        print("\n✓ 테스트 성공!")
        print(f"  - 처리된 상품: {result['total_items']}개")
        print(f"  - 조정된 상품: {result['adjusted_items']}개")
        print(f"  - 실행 시간: {result['execution_time']:.2f}초")
    else:
        print("\n✗ 테스트 실패")
        print(f"  - 오류: {result.get('error', '알 수 없음')}")


if __name__ == '__main__':
    test_unified_bidding()
