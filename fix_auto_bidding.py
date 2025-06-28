#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
auto_bidding.py에서 _initialize_driver 메서드 수정
"""

import os

# 파일 읽기
with open('C:/poison_final/auto_bidding.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 수정할 부분 찾기
old_str = """        # 리소스 차단
        options.add_argument("--disable-images")
        options.add_argument("--disable-plugins")"""

new_str = """        # 리소스 차단 - ABC마트를 위해 이미지/플러그인 차단 제거
        # options.add_argument("--disable-images")  # ABC마트 동적 로딩을 위해 비활성화
        # options.add_argument("--disable-plugins")  # ABC마트 동적 로딩을 위해 비활성화"""

# 추가로 드라이버 초기화 부분도 수정
old_driver_init = """        try:
            self.driver = uc.Chrome(options=options)
            logger.info("Chrome 드라이버 초기화 성공")"""

new_driver_init = """        try:
            # ChromeDriver 경로 명시적 지정
            driver_path = "C:/poison_final/chromedriver.exe"
            if os.path.exists(driver_path):
                self.driver = uc.Chrome(
                    options=options,
                    driver_executable_path=driver_path,
                    version_main=None
                )
            else:
                self.driver = uc.Chrome(options=options)
            logger.info("Chrome 드라이버 초기화 성공")"""

# 페이지 대기 시간도 수정
old_wait_time = '"page_wait_time": 2, # 🚀 3 → 2로 축소'
new_wait_time = '"page_wait_time": 5, # ABC마트 동적 로딩을 위해 5초로 증가'

# 내용 치환
if old_str in content:
    content = content.replace(old_str, new_str)
    print("[OK] 이미지/플러그인 차단 옵션 주석 처리 완료")
else:
    print("[FAIL] 이미지/플러그인 차단 옵션을 찾을 수 없습니다")

if old_driver_init in content:
    content = content.replace(old_driver_init, new_driver_init)
    print("[OK] ChromeDriver 경로 명시적 지정 완료")
else:
    print("[FAIL] 드라이버 초기화 부분을 찾을 수 없습니다")

if old_wait_time in content:
    content = content.replace(old_wait_time, new_wait_time)
    print("[OK] 페이지 대기 시간 증가 완료")
else:
    print("[FAIL] 페이지 대기 시간 설정을 찾을 수 없습니다")

# 파일 저장
with open('C:/poison_final/auto_bidding.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n수정 완료!")
