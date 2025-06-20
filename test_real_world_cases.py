#!/usr/bin/env python3
"""
실제 포이즌 사이트에서 발생할 수 있는 다양한 사이즈 형식 테스트
"""

def test_real_world_cases():
    """실제 발생 가능한 다양한 사이즈 형식 테스트"""
    print("\n=== 실제 사례 기반 테스트 ===")
    print("=" * 60)
    
    # 다양한 실제 사이즈 형식들
    real_world_sizes = [
        # 아식스 형식
        "2E-Width JP 24.5",
        "4E-Width JP 27",
        # 다른 가능한 형식들
        "JP24.5",  # 공백 없는 형식
        "JP 24.5 (US 6.5)",  # 추가 정보 포함
        "24.5JP",  # 순서 바뀐 형식
        "Size: JP 24.5",  # 레이블 포함
        "24.5",  # 숫자만
        " 24.5 ",  # 양쪽 공백
    ]
    
    test_size = "24.5"
    
    print(f"찾는 사이즈: {test_size}")
    print("-" * 60)
    
    # 기존 패턴 테스트
    print("\n[기존 패턴]")
    for size in real_world_sizes:
        patterns = [
            f' {test_size} ' in size,
            size.endswith(f' {test_size}'),
            size.startswith(f'{test_size} '),
            size == test_size
        ]
        matched = any(patterns)
        print(f"'{size}': {'매칭' if matched else '실패'}")
    
    # JP 패턴 추가 테스트
    print("\n[JP 패턴 추가]")
    for size in real_world_sizes:
        # JP 패턴 우선 확인
        jp_pattern = f'JP {test_size}' in size
        
        # 기존 패턴도 확인
        patterns = [
            f' {test_size} ' in size,
            size.endswith(f' {test_size}'),
            size.startswith(f'{test_size} '),
            size == test_size
        ]
        
        matched = jp_pattern or any(patterns)
        match_type = "JP패턴" if jp_pattern else "기존패턴" if any(patterns) else None
        
        print(f"'{size}': {'매칭' if matched else '실패'} {f'({match_type})' if match_type else ''}")
    
    # 개선 효과 분석
    print("\n[개선 효과]")
    print("-" * 60)
    
    # 기존 패턴으로만 매칭
    old_matches = 0
    for size in real_world_sizes:
        patterns = [
            f' {test_size} ' in size,
            size.endswith(f' {test_size}'),
            size.startswith(f'{test_size} '),
            size == test_size
        ]
        if any(patterns):
            old_matches += 1
    
    # JP 패턴 추가 후 매칭
    new_matches = 0
    jp_pattern_matches = 0
    for size in real_world_sizes:
        jp_pattern = f'JP {test_size}' in size
        patterns = [
            f' {test_size} ' in size,
            size.endswith(f' {test_size}'),
            size.startswith(f'{test_size} '),
            size == test_size
        ]
        if jp_pattern or any(patterns):
            new_matches += 1
            if jp_pattern:
                jp_pattern_matches += 1
    
    print(f"기존 패턴 매칭: {old_matches}/{len(real_world_sizes)}개")
    print(f"JP 패턴 추가 후: {new_matches}/{len(real_world_sizes)}개 (JP패턴으로 {jp_pattern_matches}개 매칭)")
    print(f"개선율: +{((new_matches/old_matches - 1) * 100):.1f}%")
    
    # 중요 케이스 하이라이트
    print("\n[중요 개선 사례]")
    print("-" * 60)
    important_cases = [
        ("JP24.5", "공백 없는 JP 형식"),
        ("JP 24.5 (US 6.5)", "추가 정보가 있는 JP 형식"),
        ("Size: JP 24.5", "레이블이 있는 JP 형식"),
    ]
    
    for case, description in important_cases:
        jp_matched = f'JP {test_size}' in case
        print(f"- {description}: '{case}' -> {'매칭 성공' if jp_matched else '여전히 실패'}")

def test_edge_cases():
    """엣지 케이스 테스트"""
    print("\n\n=== 엣지 케이스 테스트 ===")
    print("=" * 60)
    
    edge_cases = [
        ("280", ["JP 28", "JP 280", "28", "280"], "3자리 vs 2자리 변환"),
        ("2552", ["JP 255.2", "JP 255", "255"], "4자리 사이즈"),
        ("23.5", ["JP23.5", "JP 23.5", "23.5CM"], "소수점 사이즈"),
    ]
    
    for test_size, size_list, description in edge_cases:
        print(f"\n{description} - 찾는 사이즈: {test_size}")
        print("-" * 40)
        
        # JP 탭에서 변환된 사이즈
        if test_size.isdigit() and len(test_size) == 3:
            converted = str(int(test_size) / 10).rstrip('0').rstrip('.')
        elif len(test_size) == 4 and test_size.isdigit():
            converted = test_size[:3]
        else:
            converted = test_size
        
        print(f"변환된 사이즈: {converted}")
        
        for size in size_list:
            jp_pattern = f'JP {converted}' in size
            basic_patterns = [
                f' {converted} ' in size,
                size.endswith(f' {converted}'),
                size.startswith(f'{converted} '),
                size == converted
            ]
            
            matched = jp_pattern or any(basic_patterns)
            print(f"  '{size}': {'매칭' if matched else '실패'}")

if __name__ == '__main__':
    print("실제 포이즌 사이트 사이즈 형식 매칭 테스트")
    print("=" * 60)
    
    test_real_world_cases()
    test_edge_cases()
    
    print("\n\n테스트 완료!")
