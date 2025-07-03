#!/usr/bin/env python3
"""
Chrome 프로필 위치 찾기 및 연동 가이드
"""

import os
from pathlib import Path
import json

def find_chrome_profiles():
    """Chrome 프로필 위치 찾기"""
    print("\n" + "="*60)
    print("Chrome 프로필 위치 찾기")
    print("="*60)
    
    # 운영체제별 Chrome 프로필 기본 위치
    possible_paths = [
        # Windows
        Path(os.environ.get('LOCALAPPDATA', '')) / "Google/Chrome/User Data",
        Path(os.environ.get('USERPROFILE', '')) / "AppData/Local/Google/Chrome/User Data",
        
        # Windows (Chrome Beta/Canary)
        Path(os.environ.get('LOCALAPPDATA', '')) / "Google/Chrome Beta/User Data",
        Path(os.environ.get('LOCALAPPDATA', '')) / "Google/Chrome SxS/User Data",
    ]
    
    found_profiles = []
    
    for path in possible_paths:
        if path.exists():
            print(f"\n✅ Chrome 프로필 폴더 발견: {path}")
            
            # 프로필 목록 확인
            profiles = []
            
            # Default 프로필
            if (path / "Default").exists():
                profiles.append("Default")
            
            # Profile 1, 2, 3...
            for item in path.iterdir():
                if item.is_dir() and item.name.startswith("Profile "):
                    profiles.append(item.name)
            
            if profiles:
                print(f"   프로필 목록: {', '.join(profiles)}")
                
                # Local State 파일에서 프로필 이름 읽기
                local_state = path / "Local State"
                if local_state.exists():
                    try:
                        with open(local_state, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            profile_info = data.get('profile', {}).get('info_cache', {})
                            
                            print("\n   프로필 상세 정보:")
                            for profile_key, profile_data in profile_info.items():
                                name = profile_data.get('name', profile_key)
                                print(f"   - {profile_key}: {name}")
                    except:
                        pass
                
                found_profiles.append(str(path))
    
    if not found_profiles:
        print("\n❌ Chrome 프로필을 찾을 수 없습니다.")
        print("Chrome이 설치되어 있는지 확인하세요.")
    
    return found_profiles


def show_profile_usage():
    """프로필 사용 방법 안내"""
    print("\n\n" + "="*60)
    print("Chrome 프로필 연동 방법")
    print("="*60)
    
    print("""
방법 1: 기존 Chrome 프로필 복사 (추천)
----------------------------------------
1. 위에서 찾은 Chrome 프로필 경로로 이동
2. 사용하려는 프로필 폴더 복사 (예: Default 또는 Profile 1)
3. 프로젝트의 chrome_profiles/poison/ 폴더에 붙여넣기

예시:
복사: C:\\Users\\사용자\\AppData\\Local\\Google\\Chrome\\User Data\\Default
붙여넣기: C:\\poison_final\\chrome_profiles\\poison\\Default


방법 2: 새 프로필 생성 후 로그인
--------------------------------
1. python poison_login_setup.py 실행
2. 새 Chrome 창에서 포이즌 로그인
3. 로그인 정보가 chrome_profiles/poison/에 저장됨


방법 3: 기존 Chrome에서 포이즌 전용 프로필 만들기
-----------------------------------------------
1. Chrome 열기
2. 오른쪽 상단 프로필 아이콘 클릭
3. "추가" 클릭하여 "포이즌" 프로필 생성
4. 해당 프로필로 포이즌 로그인
5. 프로필 폴더를 프로젝트로 복사
""")
    
    print("\n" + "="*60)
    print("주의사항")
    print("="*60)
    print("""
1. Chrome이 실행 중이면 프로필 복사가 안 될 수 있습니다
2. 프로필을 복사할 때 Chrome을 완전히 종료하세요
3. 프로필 크기가 클 수 있습니다 (수백 MB)
4. 중요한 개인정보가 포함될 수 있으니 주의하세요
""")


def create_profile_link():
    """심볼릭 링크로 프로필 연결 (고급)"""
    print("\n\n" + "="*60)
    print("고급: 심볼릭 링크로 연결")
    print("="*60)
    
    print("""
관리자 권한으로 명령 프롬프트 실행 후:

mklink /D "C:\\poison_final\\chrome_profiles\\poison" "C:\\Users\\사용자\\AppData\\Local\\Google\\Chrome\\User Data\\Profile 1"

이렇게 하면 원본 프로필을 복사하지 않고 직접 연결할 수 있습니다.
""")


if __name__ == "__main__":
    # Chrome 프로필 찾기
    profiles = find_chrome_profiles()
    
    # 사용 방법 안내
    show_profile_usage()
    
    # 고급 옵션
    create_profile_link()
    
    input("\nEnter를 눌러 종료...")
