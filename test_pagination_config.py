#!/usr/bin/env python3
"""
페이지네이션 설정 테스트
"""

import json
from pathlib import Path


def test_config_loading():
    """설정 파일 로드 테스트"""
    print("=== 페이지네이션 설정 테스트 ===\n")
    
    # 1. 설정 파일 존재 확인
    config_path = Path("config/auto_bidding_config.json")
    if config_path.exists():
        print("[OK] 설정 파일 존재 확인")
    else:
        print("[FAIL] 설정 파일을 찾을 수 없습니다")
        return
    
    # 2. 설정 파일 로드
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print("[OK] 설정 파일 로드 성공")
    except Exception as e:
        print(f"[FAIL] 설정 파일 로드 실패: {e}")
        return
    
    # 3. 페이지네이션 설정 확인
    print("\n[extraction 섹션 확인]")
    extraction = config.get('extraction', {})
    
    # 기존 설정
    print(f"  max_scrolls: {extraction.get('max_scrolls', 'N/A')}")
    print(f"  wait_time: {extraction.get('wait_time', 'N/A')}")
    print(f"  max_links: {extraction.get('max_links', 'N/A')}")
    print(f"  timeout: {extraction.get('timeout', 'N/A')}")
    
    # 새로운 페이지네이션 설정
    print("\n[새로운 페이지네이션 설정]")
    print(f"  max_pages: {extraction.get('max_pages', 'N/A')}")
    print(f"  page_wait_time: {extraction.get('page_wait_time', 'N/A')}")
    print(f"  empty_page_threshold: {extraction.get('empty_page_threshold', 'N/A')}")
    
    # 4. 기본값 테스트 (설정 파일이 없는 경우를 시뮬레이션)
    print("\n[기본값 테스트]")
    default_config = {
        "extraction": {
            "max_scrolls": 10,
            "wait_time": 3,
            "max_links": 50,
            "max_pages": 100,
            "page_wait_time": 3,
            "empty_page_threshold": 2
        }
    }
    
    print("기본 설정값:")
    for key, value in default_config["extraction"].items():
        print(f"  {key}: {value}")
    
    # 5. 검증 결과
    print("\n[검증 결과]")
    required_fields = ["max_pages", "page_wait_time", "empty_page_threshold"]
    missing_fields = []
    
    for field in required_fields:
        if field not in extraction:
            missing_fields.append(field)
    
    if not missing_fields:
        print("[OK] 모든 페이지네이션 설정이 정상적으로 추가되었습니다.")
    else:
        print(f"[FAIL] 누락된 설정: {', '.join(missing_fields)}")
    
    print("\n=== 테스트 완료 ===")


if __name__ == "__main__":
    test_config_loading()
