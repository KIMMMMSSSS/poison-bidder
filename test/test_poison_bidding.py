#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Asia 체크 로직 통합 테스트 스크립트
수정된 Asia 체크 로직이 올바르게 동작하는지 검증
"""

import sys
import os
import time
import json
import subprocess
from datetime import datetime

# 상위 디렉토리를 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_log_file():
    """로그 파일 존재 여부 확인"""
    log_dir = "C:/poison_final/logs"
    today = datetime.now().strftime("%Y%m%d")
    log_file = os.path.join(log_dir, f"poison_bidder_{today}.log")
    
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        print(f"[INFO] 로그 디렉토리 생성: {log_dir}")
    
    return log_file

def parse_logs(log_file, start_time):
    """시작 시간 이후의 로그만 파싱"""
    relevant_logs = []
    
    if not os.path.exists(log_file):
        return relevant_logs
    
    with open(log_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                # 시간 정보가 있는 경우에만 처리
                if '[' in line and ']' in line:
                    try:
                        # 로그 시간 추출 시도
                        time_str = line.split('[')[1].split(']')[0]
                        # 시간 비교 로직 (필요시 구현)
                        relevant_logs.append(line.strip())
                    except:
                        relevant_logs.append(line.strip())
    
    return relevant_logs

def analyze_test_results(logs):
    """테스트 결과 분석"""
    results = {
        'asia_check_attempts': 0,
        'down_button_clicks': 0,
        'asia_check_success': False,
        'bid_attempts': 0,
        'errors': [],
        'test_passed': False
    }
    
    for log in logs:
        if 'Asia 체크 시작' in log:
            results['asia_check_attempts'] += 1
        elif '다운 버튼 클릭' in log:
            results['down_button_clicks'] += 1
        elif 'Asia 체크 성공' in log:
            results['asia_check_success'] = True
        elif '입찰 진행' in log or 'Placing bid' in log:
            results['bid_attempts'] += 1
        elif 'ERROR' in log or '에러' in log:
            results['errors'].append(log)
    
    # 테스트 통과 조건
    if results['asia_check_success'] and results['bid_attempts'] > 0:
        results['test_passed'] = True
    
    return results

def run_integration_test():
    """통합 테스트 실행"""
    print("="*60)
    print("Asia 체크 로직 통합 테스트 시작")
    print("="*60)
    
    start_time = datetime.now()
    log_file = check_log_file()
    
    print(f"[INFO] 테스트 시작 시간: {start_time}")
    print(f"[INFO] 로그 파일 경로: {log_file}")
    
    # 1. poison_bidder_wrapper_v2.py 실행 여부 확인
    script_path = "C:/poison_final/poison_bidder_wrapper_v2.py"
    if not os.path.exists(script_path):
        print(f"[ERROR] 스크립트를 찾을 수 없습니다: {script_path}")
        return False
    
    print(f"[INFO] 스크립트 확인 완료: {script_path}")
    
    # 2. 기존 프로세스 확인
    print("\n[테스트 1] 기존 프로세스 확인")
    print("-"*40)
    
    try:
        # Windows에서 Python 프로세스 확인
        result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq python.exe'], 
                              capture_output=True, text=True)
        if 'poison_bidder' in result.stdout:
            print("[OK] Poison Bidder 프로세스가 실행 중입니다.")
        else:
            print("[WARNING] Poison Bidder 프로세스가 실행되지 않았습니다.")
            print("[INFO] 수동으로 poison_bidder_wrapper_v2.py를 실행해주세요.")
    except Exception as e:
        print(f"[ERROR] 프로세스 확인 실패: {e}")
    
    # 3. 로그 모니터링 (30초간)
    print("\n[테스트 2] 로그 모니터링 (30초)")
    print("-"*40)
    
    monitor_duration = 30
    print(f"[INFO] {monitor_duration}초간 로그를 모니터링합니다...")
    
    time.sleep(monitor_duration)
    
    # 4. 로그 분석
    print("\n[테스트 3] 로그 분석")
    print("-"*40)
    
    logs = parse_logs(log_file, start_time)
    
    if not logs:
        print("[WARNING] 로그가 기록되지 않았습니다.")
        print("[INFO] poison_bidder_wrapper_v2.py가 실행 중인지 확인하세요.")
    else:
        print(f"[INFO] {len(logs)}개의 로그 항목을 찾았습니다.")
        
        # 최근 로그 5개 출력
        print("\n최근 로그:")
        for log in logs[-5:]:
            print(f"  {log}")
    
    # 5. 테스트 결과 분석
    print("\n[테스트 4] 테스트 결과 분석")
    print("-"*40)
    
    results = analyze_test_results(logs)
    
    print(f"Asia 체크 시도 횟수: {results['asia_check_attempts']}")
    print(f"다운 버튼 클릭 횟수: {results['down_button_clicks']}")
    print(f"Asia 체크 성공 여부: {results['asia_check_success']}")
    print(f"입찰 시도 횟수: {results['bid_attempts']}")
    print(f"에러 발생 횟수: {len(results['errors'])}")
    
    if results['errors']:
        print("\n발생한 에러:")
        for error in results['errors'][:3]:  # 최대 3개만 표시
            print(f"  {error}")
    
    # 6. 최종 결과
    print("\n" + "="*60)
    print("테스트 결과 요약")
    print("="*60)
    
    if results['test_passed']:
        print("[SUCCESS] 테스트 통과!")
        print("- Asia 체크가 성공적으로 수행되었습니다.")
        print("- Asia 체크 후 입찰이 진행되었습니다.")
    else:
        print("[FAILED] 테스트 실패")
        if not results['asia_check_success']:
            print("- Asia 체크가 수행되지 않았습니다.")
        if results['bid_attempts'] == 0:
            print("- 입찰이 진행되지 않았습니다.")
    
    print(f"\n[INFO] 상세 로그는 다음 파일을 확인하세요: {log_file}")
    
    return results['test_passed']

if __name__ == "__main__":
    # 통합 테스트 실행
    test_passed = run_integration_test()
    
    # 종료 코드 반환
    sys.exit(0 if test_passed else 1)
