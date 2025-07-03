#!/usr/bin/env python3
"""
로그인 테스트 스크립트
무신사/ABC마트 로그인 테스트
"""

import sys
from pathlib import Path
from login_manager import LoginManager

def test_login(site: str = "musinsa"):
    """로그인 테스트"""
    print(f"\n{'='*50}")
    print(f"{site.upper()} 로그인 테스트")
    print('='*50)
    
    # 로그인 관리자 생성
    login_mgr = LoginManager(site)
    
    # 로그인 시도
    if login_mgr.ensure_login():
        print("\n✅ 로그인 성공!")
        print("쿠키가 저장되었습니다.")
        print(f"쿠키 파일: cookies/{site}_cookies.pkl")
        
        # 테스트로 메인 페이지 이동
        if site == "musinsa":
            login_mgr.driver.get("https://www.musinsa.com/app/")
        else:
            login_mgr.driver.get("https://abcmart.a-rt.com/")
        
        input("\n테스트 완료. Enter를 눌러 종료하세요...")
        
        login_mgr.close()
        return True
    else:
        print("\n❌ 로그인 실패!")
        return False


def main():
    """메인 함수"""
    if len(sys.argv) > 1:
        site = sys.argv[1]
    else:
        print("\n사이트를 선택하세요:")
        print("1. 무신사 (musinsa)")
        print("2. ABC마트 (abcmart)")
        print("3. 포이즌 (poison) - 입찰 사이트")
        choice = input("\n선택 (1, 2 또는 3): ")
        
        if choice == "1":
            site = "musinsa"
        elif choice == "2":
            site = "abcmart"
        elif choice == "3":
            site = "poison"
        else:
            print("잘못된 선택입니다.")
            return
    
    test_login(site)


if __name__ == "__main__":
    main()
