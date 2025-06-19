#!/usr/bin/env python3
"""
전체 사이트 로그인 설정
포이즌, 무신사, ABC마트 순차적 로그인
"""

import time
from login_manager import LoginManager

def login_all_sites():
    """모든 사이트 로그인"""
    sites = ["poison", "musinsa", "abcmart"]
    success_count = 0
    
    print("\n" + "="*60)
    print("K-Fashion 자동 입찰 시스템 - 전체 로그인 설정")
    print("="*60)
    print("\n3개 사이트 모두 로그인이 필요합니다.")
    print("각 사이트마다 브라우저가 열립니다.")
    input("\n시작하려면 Enter를 누르세요...")
    
    for site in sites:
        print(f"\n[{sites.index(site)+1}/3] {site.upper()} 로그인")
        print("-" * 40)
        
        login_mgr = LoginManager(site)
        
        # 이미 로그인되어 있는지 확인
        if login_mgr.load_cookies() and login_mgr.is_logged_in():
            print(f"✅ {site.upper()} - 이미 로그인되어 있습니다.")
            success_count += 1
            login_mgr.close()
            continue
        
        # 로그인 필요
        print(f"🔐 {site.upper()} 로그인이 필요합니다.")
        
        if site == "poison":
            print("\n⚠️  포이즌 사이트 정보가 설정되지 않았다면:")
            print("   1. login_manager.py 파일을 열어서")
            print("   2. 'poison' 부분에 실제 URL과 선택자 입력")
            print("   3. 저장 후 다시 실행")
            print("\n설정이 완료되었다면 계속 진행하세요.")
        
        if login_mgr.manual_login():
            success_count += 1
            print(f"✅ {site.upper()} 로그인 성공!")
        else:
            print(f"❌ {site.upper()} 로그인 실패!")
        
        login_mgr.close()
        
        # 다음 사이트로 넘어가기 전 대기
        if sites.index(site) < len(sites) - 1:
            print("\n다음 사이트 로그인을 위해 3초 대기...")
            time.sleep(3)
    
    # 결과 출력
    print("\n" + "="*60)
    print("로그인 설정 완료")
    print("="*60)
    print(f"\n성공: {success_count}/{len(sites)} 사이트")
    
    if success_count == len(sites):
        print("\n✅ 모든 사이트 로그인 완료!")
        print("이제 자동 입찰을 사용할 수 있습니다.")
    else:
        print("\n⚠️  일부 사이트 로그인 실패")
        print("실패한 사이트는 개별적으로 다시 시도하세요:")
        print("python test_login.py [사이트명]")
    
    print("\n💡 팁: 쿠키는 7일간 유지되므로 일주일마다 한 번씩 로그인하면 됩니다.")


if __name__ == "__main__":
    login_all_sites()
