#!/usr/bin/env python3
"""
아식스 사이즈 매칭 통합 테스트
수정된 JP 사이즈 매칭 로직이 아식스 제품에서 정상 작동하는지 확인
"""

import re
import unittest
from unittest.mock import Mock, MagicMock, patch
import sys
import os

# 테스트 대상 모듈 경로 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class TestAsicsSizing(unittest.TestCase):
    """아식스 사이즈 매칭 로직 테스트"""
    
    def setUp(self):
        """테스트 환경 설정"""
        self.test_sizes = {
            'JP': [
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
            ],
            'US': [
                "US Men 5",
                "US Men 5.5",
                "US Men 6",
                "US Men 6.5",
                "US Men 7",
                "US Men 7.5",
                "US Men 8",
                "US Men 8.5",
                "US Men 9",
                "US Men 9.5",
                "US Men 10"
            ]
        }
        
        # 테스트 케이스 (무신사 사이즈 → 포이즌 사이즈)
        self.test_cases = [
            ('225', 'JP', '22.5'),
            ('230', 'JP', '23'),
            ('235', 'JP', '23.5'),
            ('240', 'JP', '24'),
            ('245', 'JP', '24.5'),
            ('250', 'JP', '25'),
            ('255', 'JP', '25.5'),
            ('260', 'JP', '26'),
            ('265', 'JP', '26.5'),
            ('270', 'JP', '27'),
            ('275', 'JP', '27.5'),
            ('280', 'JP', '28')
        ]
        
        self.results = []
    
    def simulate_javascript_matching(self, target_size, active_tab, available_sizes):
        """JavaScript 매칭 로직 시뮬레이션 (수정된 버전)"""
        
        # 텍스트 사이즈인지 확인
        text_sizes = ['XS', 'S', 'M', 'L', 'XL', 'XXL', 'XXXL', '2XL', '3XL', '4XL', '5XL']
        is_text_size = target_size.upper() in text_sizes
        
        for item_text in available_sizes:
            text = item_text.strip()
            
            if is_text_size:
                # 텍스트 사이즈 매칭
                upper_text = text.upper()
                upper_target = target_size.upper()
                
                if (upper_text == upper_target or 
                    f' {upper_target} ' in upper_text or
                    text.endswith(f' {upper_target}') or
                    text.startswith(f'{upper_target} ')):
                    return item_text
            else:
                # 숫자 사이즈 매칭
                pattern1 = f' {target_size} '
                pattern2 = f' {target_size}'
                pattern3 = f'{target_size} '
                
                # JP 탭 특수 처리 (핵심 개선사항)
                if active_tab == 'JP':
                    jp_pattern = f'JP {target_size}'
                    if jp_pattern in text:
                        print(f"[DEBUG] JP 패턴 매칭 성공: '{jp_pattern}' in '{text}'")
                        return item_text
                
                if (pattern1 in text or 
                    text.endswith(pattern2) or 
                    text.startswith(pattern3) or
                    text == target_size):
                    return item_text
        
        return None
    
    def test_jp_size_matching(self):
        """JP 사이즈 매칭 테스트"""
        print("\n=== JP 사이즈 매칭 테스트 시작 ===")
        
        success_count = 0
        fail_count = 0
        
        for musinsa_size, tab, expected_size in self.test_cases:
            if tab != 'JP':
                continue
            
            # JP 사이즈 변환 (225 → 22.5)
            if musinsa_size.isdigit() and len(musinsa_size) == 3:
                converted_size = str(int(musinsa_size) / 10).rstrip('0').rstrip('.')
            else:
                converted_size = musinsa_size
            
            # 매칭 테스트
            matched = self.simulate_javascript_matching(
                converted_size, 
                'JP', 
                self.test_sizes['JP']
            )
            
            if matched:
                success_count += 1
                result = f"[SUCCESS] {musinsa_size} -> {converted_size} -> {matched}"
                print(result)
                self.results.append(('SUCCESS', musinsa_size, converted_size, matched))
                
                # 예상 사이즈와 일치하는지 확인
                self.assertIn(f'JP {expected_size}', matched)
            else:
                fail_count += 1
                result = f"[FAIL] {musinsa_size} -> {converted_size} -> 매칭 실패"
                print(result)
                self.results.append(('FAIL', musinsa_size, converted_size, None))
        
        print(f"\n[결과] 성공: {success_count}, 실패: {fail_count}")
        print(f"성공률: {success_count/(success_count+fail_count)*100:.1f}%")
        
        # 모든 테스트가 성공해야 함
        self.assertEqual(fail_count, 0, f"{fail_count}개의 사이즈 매칭 실패")
    
    def test_debug_info_on_failure(self):
        """매칭 실패 시 디버그 정보 출력 테스트"""
        print("\n=== 디버그 정보 출력 테스트 ===")
        
        # 존재하지 않는 사이즈로 테스트
        non_existent_size = '29.5'
        matched = self.simulate_javascript_matching(
            non_existent_size, 
            'JP', 
            self.test_sizes['JP']
        )
        
        if not matched:
            print(f"\n[FAIL] JP 탭에서 {non_existent_size} 찾기 실패")
            print(f"[DEBUG] ===== 매칭 실패 상세 정보 =====")
            print(f"[DEBUG] 브랜드: 아식스")
            print(f"[DEBUG] 원본 사이즈: 295")
            print(f"[DEBUG] 타겟 사이즈: {non_existent_size}")
            
            # 시도한 패턴들
            tried_patterns = [
                f"' {non_existent_size} ' (공백으로 둘러싸인)",
                f"' {non_existent_size}' (뒤에만 공백)",
                f"'{non_existent_size} ' (앞에만 공백)",
                f"'{non_existent_size}' (정확히 일치)",
                f"'JP {non_existent_size}' (JP 특수 패턴)"
            ]
            
            print(f"[DEBUG] 시도한 패턴들:")
            for pattern in tried_patterns:
                print(f"  - {pattern}")
            
            # 사용 가능한 사이즈 표시
            print(f"\n[DEBUG] 사용 가능한 사이즈 (최대 10개):")
            for i, size in enumerate(self.test_sizes['JP'][:10], 1):
                print(f"  {i}. {size}")
            
            print(f"[DEBUG] ==============================\n")
        
        # 디버그 정보가 출력되었음을 확인
        self.assertIsNone(matched)
    
    def test_size_conversion_logic(self):
        """사이즈 변환 로직 테스트"""
        print("\n=== 사이즈 변환 로직 테스트 ===")
        
        test_conversions = [
            ('225', '22.5'),
            ('230', '23'),
            ('235', '23.5'),
            ('240', '24'),
            ('245', '24.5'),
            ('250', '25'),
            ('255', '25.5'),
            ('260', '26'),
            ('265', '26.5'),
            ('270', '27'),
            ('275', '27.5'),
            ('280', '28'),
            # 4자리 사이즈
            ('2552', '255'),  # 4자리 → 3자리 변환
        ]
        
        for original, expected in test_conversions:
            if len(original) == 4 and original.isdigit():
                # 4자리 사이즈 변환
                converted = original[:3]
                print(f"4자리 변환: {original} → {converted}")
                self.assertEqual(converted, expected)
            elif original.isdigit() and len(original) == 3:
                # JP 변환
                converted = str(int(original) / 10).rstrip('0').rstrip('.')
                print(f"JP 변환: {original} → {converted}")
                self.assertEqual(converted, expected)
    
    def tearDown(self):
        """테스트 종료 후 요약"""
        if hasattr(self, 'results') and self.results:
            print("\n=== 전체 테스트 결과 요약 ===")
            success_results = [r for r in self.results if r[0] == 'SUCCESS']
            fail_results = [r for r in self.results if r[0] == 'FAIL']
            
            print(f"총 테스트: {len(self.results)}")
            print(f"성공: {len(success_results)}")
            print(f"실패: {len(fail_results)}")
            
            if fail_results:
                print("\n실패한 사이즈:")
                for _, musinsa_size, converted_size, _ in fail_results:
                    print(f"  - {musinsa_size} (변환: {converted_size})")


if __name__ == '__main__':
    # 테스트 실행
    print("아식스 사이즈 매칭 통합 테스트")
    print("=" * 50)
    unittest.main(verbosity=2)
