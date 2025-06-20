#!/usr/bin/env python3
"""간단한 디버그 테스트"""

import sys
import os

# 로그 디렉토리 확인
log_dir = "C:/poison_final/logs"
print(f"로그 디렉토리 존재: {os.path.exists(log_dir)}")

# 원본 파일 확인
original_file = "0923_fixed_multiprocess_cookie_v2.py"
print(f"원본 파일 존재: {os.path.exists(original_file)}")

# 모듈 import 테스트
try:
    from poison_integrated_bidding import AutoBiddingAdapter
    print("AutoBiddingAdapter import 성공")
    
    # 인스턴스 생성 테스트
    adapter = AutoBiddingAdapter()
    print("AutoBiddingAdapter 인스턴스 생성 성공")
    
    # 테스트 데이터
    test_item = [{
        'brand': '나이키',
        'code': 'TEST001',
        'size': '270',
        'price': 50000
    }]
    
    print(f"테스트 데이터: {test_item}")
    
    # run_with_poison 호출 전까지만 테스트
    print("준비 완료")
    
except Exception as e:
    print(f"오류 발생: {e}")
    import traceback
    traceback.print_exc()
