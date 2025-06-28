#!/usr/bin/env python3
"""
텔레그램 봇 안전 실행 래퍼
- 기존 인스턴스 확인 및 종료
- 단일 인스턴스만 실행 보장
"""

import os
import sys
import time
import psutil
import subprocess
import signal

def kill_existing_bot():
    """기존 텔레그램 봇 프로세스 종료"""
    killed = False
    
    # 현재 프로세스 제외하고 telegram_bot 관련 프로세스 찾기
    current_pid = os.getpid()
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # Python 프로세스이고 telegram_bot을 실행 중인지 확인
            if proc.info['name'] and 'python' in proc.info['name'].lower():
                cmdline = proc.info.get('cmdline', [])
                if cmdline and any('telegram_bot' in arg for arg in cmdline):
                    if proc.pid != current_pid:
                        print(f"기존 봇 프로세스 발견 (PID: {proc.pid}), 종료 중...")
                        proc.terminate()
                        killed = True
                        time.sleep(2)  # 프로세스 종료 대기
                        
                        # 강제 종료 필요시
                        if proc.is_running():
                            proc.kill()
                            time.sleep(1)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    return killed

def main():
    """메인 함수"""
    print("=" * 60)
    print("텔레그램 봇 안전 실행기")
    print("=" * 60)
    
    # 1. 기존 봇 프로세스 종료
    if kill_existing_bot():
        print("기존 봇 프로세스를 종료했습니다.")
        print("잠시 대기 중...")
        time.sleep(3)
    else:
        print("실행 중인 봇 프로세스가 없습니다.")
    
    # 2. 봇 실행
    print("\n새 봇 인스턴스를 시작합니다...")
    bot_path = os.path.join(os.path.dirname(__file__), "telegram_bot.py")
    
    if not os.path.exists(bot_path):
        print(f"오류: {bot_path} 파일을 찾을 수 없습니다.")
        return
    
    try:
        # 봇 실행 (현재 프로세스 대체)
        if sys.platform == "win32":
            # Windows에서는 새 프로세스로 실행
            subprocess.run([sys.executable, bot_path])
        else:
            # Unix 계열에서는 exec로 현재 프로세스 대체
            os.execv(sys.executable, [sys.executable, bot_path])
    except KeyboardInterrupt:
        print("\n봇이 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"봇 실행 중 오류 발생: {e}")

if __name__ == "__main__":
    main()
