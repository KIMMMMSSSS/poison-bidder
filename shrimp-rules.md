# K-Fashion 자동 입찰 시스템 개발 가이드라인

## 프로젝트 개요
- **목적**: 무신사/ABC마트에서 상품을 검색하고 Poizon 플랫폼에서 자동 입찰
- **기술 스택**: Python 3.x, Selenium WebDriver, Chrome Browser
- **루트 디렉토리**: C:\poison_final

## 프로젝트 아키텍처

### 디렉토리 구조 관리 규칙
- **config/**: 설정 파일만 저장, 민감한 정보는 .env 파일 사용
- **input/**: 링크 파일 저장 (예: musinsa_links.txt, abcmart_links.txt)
- **output/**: 스크래핑 결과 및 입찰 결과 저장
- **logs/**: 모든 로그 파일은 반드시 이곳에 저장
- **cookies/**: 사이트별 쿠키 파일 저장
- **test/**: 테스트 코드만 포함

## 코드 표준

### ChromeDriver 관리 - 매우 중요
- **절대 사용 금지**: 직접 ChromeDriver 경로 지정 또는 수동 다운로드
- **반드시 사용**: `from chrome_driver_manager import initialize_chrome_driver`
- **모든 Selenium 파일에서 다음 패턴 사용**:
```python
from chrome_driver_manager import initialize_chrome_driver

# Worker ID가 있는 경우
driver = initialize_chrome_driver(worker_id=1, headless=True)

# Worker ID가 없는 경우
driver = initialize_chrome_driver(headless=False)
```

### 파일별 ChromeDriver 초기화 규칙
- **poison_bidder_wrapper_v2.py**: worker_process_wrapper 함수에서 chrome_driver_manager 사용
- **musinsa_scraper_improved.py**: get_driver 함수를 chrome_driver_manager로 대체
- **abcmart_scraper_improved_backup.py**: webdriver 초기화 부분을 chrome_driver_manager로 대체
- **auto_bidding.py**: 모든 Chrome 초기화를 chrome_driver_manager로 통일
- **login_manager.py**: 각 사이트별 로그인에서 chrome_driver_manager 사용

### 로그 작성 규칙
- **로그 경로**: 모든 로그는 `C:\poison_final\logs` 디렉토리에 저장
- **파일명 형식**: `{모듈명}_{YYYYMMDD}.log` 또는 `{모듈명}_{YYYYMMDD_HHMMSS}.log`
- **인코딩**: UTF-8 필수
- **로그 레벨**: INFO, WARNING, ERROR, DEBUG 사용

### 오류 처리 규칙
- **ChromeDriver 오류**: chrome_driver_manager가 자동으로 처리하므로 별도 처리 불필요
- **Selenium TimeoutException**: 3회 재시도 후 실패 처리
- **로그인 실패**: 쿠키 삭제 후 재로그인 시도

## 기능 구현 표준

### 링크 추출 구현 규칙
- **파일 저장 위치**: `input/{사이트명}_links.txt`
- **중복 제거**: set() 사용하여 중복 링크 제거
- **진행 상황**: tqdm 또는 커스텀 프로그레스 표시

### 스크래핑 구현 규칙
- **팝업 처리**: enhanced_close_musinsa_popup 함수 사용 (무신사)
- **동적 로딩 대기**: WebDriverWait 사용, 최대 15초
- **이미지 추출**: data-original 속성 우선, src 속성 차선

### 입찰 시스템 구현 규칙
- **가격 계산**: 원가 + 최소수익 이상일 때만 입찰
- **Asia 체크**: 반드시 Asia 체크 확인 후 입찰
- **재시도**: 실패 시 3회까지 재시도

## 워크플로우 표준

### 자동 입찰 프로세스
1. 링크 추출 (link_extractor)
2. 상품 정보 스크래핑 (scraper)
3. 가격 조정 (할인 적용)
4. Poizon 입찰 (bidder_wrapper)

### 수동 입찰 프로세스
1. input 폴더에 링크 파일 준비
2. unified_bidding.py 실행
3. 입찰 전략 선택
4. 결과 확인

## 키 파일 상호작용 표준

### 동시 수정 필요 파일
- **ChromeDriver 관련 수정 시**: 
  - poison_bidder_wrapper_v2.py
  - musinsa_scraper_improved.py
  - abcmart_scraper_improved_backup.py
  - auto_bidding.py
  - login_manager.py
  - 모든 test 파일들

### 의존성 관계
- **telegram_bot.py** → auto_bidding.py → 각 scraper/bidder 모듈
- **unified_bidding.py** → poison_bidder_wrapper_v2.py
- **모든 Selenium 파일** → chrome_driver_manager.py

## AI 의사결정 표준

### ChromeDriver 오류 발생 시
1. chrome_driver_manager.ensure_driver() 호출
2. 실패 시 webdriver-manager 패키지 설치 확인
3. 그래도 실패 시 사용자에게 알림

### 입찰 실패 시
1. 검색 코드 변환 규칙 적용 (브랜드별)
2. 부분 검색 시도
3. Size Chart 확인
4. 실패 로그 기록

### 가격 결정 시
1. 원가 확인
2. 할인율 적용
3. 최소수익 확인
4. Asia 체크 여부 확인

## 금지 사항

### 절대 하지 말아야 할 것
- **ChromeDriver 수동 다운로드 코드 작성 금지**
- **chromedriver.exe 직접 경로 지정 금지**
- **Service('chromedriver.exe') 형태 사용 금지**
- **undetected_chromedriver 직접 사용 금지** (chrome_driver_manager가 처리)
- **로그 파일을 logs 폴더 외부에 저장 금지**
- **환경변수 없이 로그인 정보 하드코딩 금지**

### 반드시 해야 할 것
- **모든 Selenium 파일에서 chrome_driver_manager 사용**
- **webdriver-manager 패키지 의존성 확인**
- **로그는 반드시 logs 폴더에 저장**
- **민감한 정보는 .env 파일 사용**

## 패키지 의존성

### 필수 패키지
```
selenium>=4.0.0
webdriver-manager>=4.0.0
python-dotenv
requests
tqdm
```

### ChromeDriver 관련 패키지
- **webdriver-manager**: 자동 ChromeDriver 관리 (필수)
- **undetected-chromedriver**: chrome_driver_manager가 내부적으로 사용

## 테스트 및 디버깅

### ChromeDriver 테스트
```python
# 올바른 방법
from chrome_driver_manager import ChromeDriverManager
manager = ChromeDriverManager()
if manager.test_driver():
    print("ChromeDriver 정상 작동")
```

### 디버그 모드
- headless=False로 브라우저 표시
- 로그 레벨을 DEBUG로 설정
- Chrome DevTools 활용

이 문서는 AI Agent가 코드를 수정할 때 반드시 따라야 하는 규칙입니다.
특히 ChromeDriver 관련 규칙은 매우 중요하며, 반드시 chrome_driver_manager를 사용해야 합니다.
