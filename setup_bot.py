#!/usr/bin/env python3
"""
텔레그램 봇 설정 도우미
봇 토큰과 사용자 ID 설정을 도와줍니다
"""

import json
import os
from pathlib import Path

def setup_bot_config():
    """봇 설정 도우미"""
    print("=== K-Fashion 텔레그램 봇 설정 ===\n")
    
    config_path = Path("config/bot_config.json")
    
    # 기존 설정 로드
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # 봇 토큰 입력
    print("1. BotFather에서 받은 봇 토큰을 입력하세요:")
    print("   (예: 5123456789:ABCdefGHIjklMNOpqrsTUVwxyz1234567890)")
    token = input("봇 토큰: ").strip()
    
    if token and token != "YOUR_BOT_TOKEN_HERE":
        config['bot']['token'] = token
        print("✅ 봇 토큰이 설정되었습니다.\n")
    else:
        print("❌ 유효한 토큰을 입력하세요.\n")
        return
    
    # 사용자 ID 입력
    print("2. 텔레그램 User ID를 입력하세요:")
    print("   (@userinfobot 에서 확인 가능)")
    user_id = input("User ID: ").strip()
    
    try:
        user_id = int(user_id)
        config['bot']['admin_ids'] = [user_id]
        print("✅ 사용자 ID가 설정되었습니다.\n")
    except ValueError:
        print("❌ 유효한 숫자 ID를 입력하세요.\n")
        return
    
    # 설정 저장
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    print("✅ 설정이 저장되었습니다!")
    print("\n이제 다음 명령어로 봇을 실행할 수 있습니다:")
    print("python telegram_bot.py")
    
    # 실행 여부 확인
    run_now = input("\n지금 봇을 실행하시겠습니까? (y/n): ").lower()
    if run_now == 'y':
        print("\n봇을 시작합니다...")
        os.system("python telegram_bot.py")


if __name__ == '__main__':
    setup_bot_config()
