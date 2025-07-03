#!/usr/bin/env python3
"""
텔레그램 봇 문제 진단
"""

import sys
import os

print("텔레그램 봇 진단 시작...")
print(f"Python 버전: {sys.version}")
print(f"현재 디렉토리: {os.getcwd()}")

# 1. 필요한 모듈 import 테스트
print("\n1. 모듈 import 테스트...")
try:
    from telegram import Update
    print("[OK] telegram 모듈 import 성공")
except Exception as e:
    print(f"[ERROR] telegram 모듈 import 실패: {e}")
    sys.exit(1)

try:
    from telegram.ext import Application
    print("[OK] telegram.ext 모듈 import 성공")
except Exception as e:
    print(f"[ERROR] telegram.ext 모듈 import 실패: {e}")
    sys.exit(1)

# 2. 설정 파일 확인
print("\n2. 설정 파일 확인...")
config_path = "config/bot_config.json"
if os.path.exists(config_path):
    print(f"[OK] 설정 파일 존재: {config_path}")
    try:
        import json
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print(f"[OK] 설정 파일 로드 성공")
        print(f"   - 토큰 길이: {len(config['bot']['token'])} 문자")
        print(f"   - 관리자 ID: {config['bot']['admin_ids']}")
    except Exception as e:
        print(f"[ERROR] 설정 파일 로드 실패: {e}")
else:
    print(f"[ERROR] 설정 파일 없음: {config_path}")

# 3. 통합 모듈 확인
print("\n3. 의존 모듈 확인...")
modules_to_check = [
    "unified_bidding",
    "auto_bidding"
]

for module_name in modules_to_check:
    try:
        __import__(module_name)
        print(f"[OK] {module_name} 모듈 import 성공")
    except Exception as e:
        print(f"[ERROR] {module_name} 모듈 import 실패: {e}")

# 4. 간단한 봇 테스트
print("\n4. 간단한 봇 생성 테스트...")
try:
    from telegram.ext import Application
    
    # 테스트용 토큰 (실제 토큰 사용)
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    token = config['bot']['token']
    
    # Application 생성 시도
    print("Application 생성 시도...")
    app = Application.builder().token(token).build()
    print("[OK] Application 생성 성공!")
    
    # 봇 정보 가져오기
    print("\n봇 정보 가져오는 중...")
    import asyncio
    
    async def get_bot_info():
        bot = app.bot
        me = await bot.get_me()
        print(f"[OK] 봇 정보 획득 성공!")
        print(f"   - 봇 이름: {me.first_name}")
        print(f"   - 봇 username: @{me.username}")
        print(f"   - 봇 ID: {me.id}")
        return True
    
    # 비동기 실행
    try:
        asyncio.run(get_bot_info())
    except Exception as e:
        print(f"[ERROR] 봇 정보 가져오기 실패: {e}")
        print("   가능한 원인:")
        print("   1. 인터넷 연결 문제")
        print("   2. 토큰이 잘못됨")
        print("   3. 텔레그램 API 접속 차단")
        
except Exception as e:
    print(f"[ERROR] 봇 테스트 실패: {e}")
    import traceback
    traceback.print_exc()

print("\n진단 완료!")
