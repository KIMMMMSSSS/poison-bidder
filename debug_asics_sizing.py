#!/usr/bin/env python3
"""아식스 사이즈 매칭 문제 디버깅 스크립트"""

import re

# 실패 로그 분석
fail_log = """1,아식스,1291A041,,품절,58900,JP탭매칭실패
9,아식스,1292A053,,225,58900,US Men탭매칭실패
10,아식스,1292A053,,230,58900,US Men탭매칭실패
11,아식스,1292A053,,235,58900,US Men탭매칭실패
40,아식스,1202A414,,270,113050,가격 조정 불가 Remove
41,아식스,1202A414,,275,113050,가격 조정 불가 Remove"""

print("=== 아식스 사이즈 매칭 실패 분석 ===\n")

# 실패 유형별 분류
failures = {
    'JP탭매칭실패': 0,
    'US Men탭매칭실패': 0,
    'US Kids탭매칭실패': 0,
    'CHN탭매칭실패': 0,
    'US탭매칭실패': 0,
    '가격 조정 불가': 0,
    '품절': 0
}

sizes_with_tabs = {}

# 로그 파싱
lines = fail_log.strip().split('\n')
for line in lines:
    parts = line.split(',')
    if len(parts) >= 7:
        size = parts[4]
        reason = parts[6]
        
        # 실패 유형 카운트
        for key in failures:
            if key in reason:
                failures[key] += 1
                break
        
        # 품절 카운트
        if size == '품절':
            failures['품절'] += 1
        else:
            # 실제 사이즈가 있는 경우 탭별로 분류
            tab_match = re.search(r'(.+)탭매칭실패', reason)
            if tab_match:
                tab = tab_match.group(1)
                if tab not in sizes_with_tabs:
                    sizes_with_tabs[tab] = []
                sizes_with_tabs[tab].append(size)

print("1. 실패 유형별 통계:")
for key, count in failures.items():
    if count > 0:
        print(f"   - {key}: {count}건")

print("\n2. 탭별 실제 사이즈:")
for tab, sizes in sizes_with_tabs.items():
    print(f"   - {tab} 탭: {', '.join(sizes)}")

print("\n3. 권장 수정 사항:")
print("   - JP 탭에서 225, 230 등의 사이즈를 22.5, 23.0 형식으로도 시도")
print("   - US Men 탭에서는 cm를 US 사이즈로 변환 필요")
print("   - 아식스의 경우 JPN, Japan 등 다른 탭 이름도 체크")
print("   - Size Chart를 우선적으로 활용하여 정확한 변환")
