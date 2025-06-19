# 포이즌 사이트 로그인 설정

## 1. login_manager.py 수정 필요

`login_manager.py` 파일의 "poison" 부분을 실제 정보로 수정해주세요:

```python
"poison": {
    "login_url": "실제_포이즌_로그인_URL",
    "home_url": "실제_포이즌_홈페이지_URL",
    "login_check_selector": "로그인_확인_요소_선택자",
    "id_field": "아이디_입력_필드_name",
    "pw_field": "비밀번호_입력_필드_name",
    "login_button": "로그인_버튼_선택자"
}
```

## 2. 필요한 정보 확인 방법

1. 포이즌 사이트 로그인 페이지에서 F12 (개발자 도구) 열기
2. Elements 탭에서 각 요소 확인:
   - ID 입력창의 `name` 속성
   - 비밀번호 입력창의 `name` 속성
   - 로그인 버튼의 선택자
   - 로그인 후 나타나는 사용자 정보 요소

## 3. 통합 로그인 순서

입찰 시스템이 작동하려면 3개 사이트 모두 로그인이 필요합니다:

1. **포이즌 사이트** - 입찰 실행
2. **무신사** - 상품 정보 수집
3. **ABC마트** - 상품 정보 수집 (선택사항)

## 4. 로그인 설정 명령어

```bash
# 포이즌 로그인
python test_login.py poison

# 무신사 로그인
python test_login.py musinsa

# ABC마트 로그인
python test_login.py abcmart
```

## 5. 자동 입찰 시 로그인 체크

자동 입찰 실행 시 자동으로:
1. 포이즌 사이트 로그인 확인
2. 대상 사이트(무신사/ABC마트) 로그인 확인
3. 모두 로그인되어 있으면 작업 진행

쿠키는 7일간 유지되므로, 일주일에 한 번만 로그인하면 됩니다.
