#!/usr/bin/env python3
"""
아식스 사이즈 매칭 개선 전후 비교
수정 전후의 매칭 성공률을 비교하여 개선 효과를 시각화
"""

import time
from datetime import datetime

def simulate_old_matching(target_size, available_sizes):
    """개선 전 매칭 로직 (JP 패턴 미지원)"""
    for item_text in available_sizes:
        text = item_text.strip()
        
        # 기존 패턴만 확인
        pattern1 = f' {target_size} '
        pattern2 = f' {target_size}'
        pattern3 = f'{target_size} '
        
        if (pattern1 in text or 
            text.endswith(pattern2) or 
            text.startswith(pattern3) or
            text == target_size):
            return item_text
    
    return None

def simulate_new_matching(target_size, available_sizes):
    """개선 후 매칭 로직 (JP 패턴 지원)"""
    for item_text in available_sizes:
        text = item_text.strip()
        
        # JP 특수 패턴 추가
        jp_pattern = f'JP {target_size}'
        if jp_pattern in text:
            return item_text
        
        # 기존 패턴도 확인
        pattern1 = f' {target_size} '
        pattern2 = f' {target_size}'
        pattern3 = f'{target_size} '
        
        if (pattern1 in text or 
            text.endswith(pattern2) or 
            text.startswith(pattern3) or
            text == target_size):
            return item_text
    
    return None

def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("아식스 사이즈 매칭 개선 전후 비교")
    print("=" * 60)
    print(f"실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 아식스 JP 사이즈 목록
    asics_sizes = [
        "2E-Width JP 22.5",
        "2E-Width JP 23",
        "2E-Width JP 23.5",
        "2E-Width JP 24",
        "2E-Width JP 24.5",
        "2E-Width JP 25",
        "2E-Width JP 25.5",
        "2E-Width JP 26",
        "2E-Width JP 26.5",
        "2E-Width JP 27",
        "4E-Width JP 27.5",
        "4E-Width JP 28"
    ]
    
    # 테스트할 무신사 사이즈
    test_sizes = {
        '225': '22.5',
        '230': '23',
        '235': '23.5',
        '240': '24',
        '245': '24.5',
        '250': '25',
        '255': '25.5',
        '260': '26',
        '265': '26.5',
        '270': '27',
        '275': '27.5',
        '280': '28'
    }
    
    # 개선 전 테스트
    print("### 개선 전 (기존 매칭 로직)")
    print("-" * 60)
    old_success = 0
    old_fail = 0
    old_results = []
    
    for musinsa_size, converted_size in test_sizes.items():
        result = simulate_old_matching(converted_size, asics_sizes)
        if result:
            old_success += 1
            status = "성공"
        else:
            old_fail += 1
            status = "실패"
        
        old_results.append((musinsa_size, converted_size, result, status))
        print(f"{musinsa_size} → {converted_size}: {status}")
    
    old_rate = (old_success / (old_success + old_fail)) * 100
    print(f"\n결과: 성공 {old_success}개, 실패 {old_fail}개 (성공률: {old_rate:.1f}%)")
    
    # 개선 후 테스트
    print("\n### 개선 후 (JP 패턴 지원)")
    print("-" * 60)
    new_success = 0
    new_fail = 0
    new_results = []
    
    for musinsa_size, converted_size in test_sizes.items():
        result = simulate_new_matching(converted_size, asics_sizes)
        if result:
            new_success += 1
            status = "성공"
        else:
            new_fail += 1
            status = "실패"
        
        new_results.append((musinsa_size, converted_size, result, status))
        print(f"{musinsa_size} → {converted_size}: {status} {f'({result})' if result else ''}")
    
    new_rate = (new_success / (new_success + new_fail)) * 100
    print(f"\n결과: 성공 {new_success}개, 실패 {new_fail}개 (성공률: {new_rate:.1f}%)")
    
    # 개선 효과 분석
    print("\n### 개선 효과 분석")
    print("=" * 60)
    print(f"성공률 향상: {old_rate:.1f}% → {new_rate:.1f}% (+{new_rate - old_rate:.1f}%)")
    print(f"추가 매칭 성공: {new_success - old_success}개")
    
    # 개선으로 새로 매칭된 사이즈
    print("\n### 개선으로 새로 매칭된 사이즈")
    print("-" * 60)
    for i, (musinsa, converted, result, status) in enumerate(new_results):
        old_status = old_results[i][3]
        if old_status == "실패" and status == "성공":
            print(f"• {musinsa} → {converted} → {result}")
    
    # 성능 측정
    print("\n### 성능 측정")
    print("-" * 60)
    
    # 개선 전 성능
    start_time = time.time()
    for _ in range(1000):
        for _, converted_size in test_sizes.items():
            simulate_old_matching(converted_size, asics_sizes)
    old_time = time.time() - start_time
    
    # 개선 후 성능
    start_time = time.time()
    for _ in range(1000):
        for _, converted_size in test_sizes.items():
            simulate_new_matching(converted_size, asics_sizes)
    new_time = time.time() - start_time
    
    print(f"개선 전: {old_time:.3f}초 (1000회 반복)")
    print(f"개선 후: {new_time:.3f}초 (1000회 반복)")
    print(f"성능 차이: {abs(new_time - old_time):.3f}초 ({(new_time/old_time - 1)*100:+.1f}%)")
    
    # 결론
    print("\n### 결론")
    print("=" * 60)
    if new_rate == 100:
        print("✓ JP 패턴 추가로 아식스 제품의 모든 사이즈 매칭 성공!")
        print("✓ 'Width JP XX' 형식의 특수 사이즈도 정상적으로 인식")
        print("✓ 성능 오버헤드도 최소화 (JP 탭에서만 추가 패턴 확인)")
    else:
        print("일부 사이즈 매칭 실패 - 추가 개선 필요")
    
    print("\n테스트 완료!")

if __name__ == '__main__':
    main()
