# K-Fashion 자동 입찰 시스템 - 주요 파일 가이드

## 📁 프로젝트 개요
이 프로젝트는 무신사와 ABC마트에서 상품을 검색하고, 해당 상품들을 Poizon(포이즌) 플랫폼에서 자동으로 입찰하는 시스템입니다.

## 🔍 핵심 파일 구조

### 1. 메인 제어 시스템

#### 📱 **telegram_bot.py**
- **용도**: 텔레그램 봇을 통한 원격 제어 인터페이스
- **주요 기능**:
  - `/auto` 명령어로 자동화 입찰 실행
  - 적립금 선할인, 카드 할인 설정
  - 작업 상태 모니터링
  - 입찰 결과 리포팅
- **사용법**: `python telegram_bot.py`

#### 🤖 **auto_bidding.py**
- **용도**: 자동화 파이프라인 실행
- **주요 기능**:
  - 링크 추출 → 스크래핑 → 가격 조정 → 입찰의 전체 프로세스 자동화
  - 진행 상태 실시간 리포팅
  - 오류 처리 및 재시도 로직

#### 🎯 **unified_bidding.py**
- **용도**: 통합 입찰 시스템 (수동 모드)
- **주요 기능**:
  - 링크 파일 기반 입찰
  - 다양한 입찰 전략 적용
  - 배치 처리

### 2. 링크 추출 시스템

#### 🔗 **musinsa_link_extractor.py**
- **용도**: 무신사에서 상품 링크 추출
- **주요 기능**:
  - 키워드 검색
  - 페이지네이션 처리
  - 필터링 옵션 (신상품, 세일 등)
- **출력**: `input/musinsa_links.txt`

#### 🔗 **abcmart_link_extractor.py**
- **용도**: ABC마트에서 상품 링크 추출
- **주요 기능**:
  - 브랜드별 검색
  - 상품 수 급감 시 조기 종료
  - 멀티프로세싱 지원
- **출력**: `input/abcmart_links.txt`

### 3. 스크래핑 시스템

#### 📦 **musinsa_scraper_improved.py**
- **용도**: 무신사 상품 정보 스크래핑
- **주요 기능**:
  - 상품명, 가격, 이미지 추출
  - 팝업 처리
  - 재고 상태 확인

#### 📦 **abcmart_scraper_improved_backup.py**
- **용도**: ABC마트 상품 정보 스크래핑
- **주요 기능**:
  - 동적 콘텐츠 로딩 대기
  - 이미지 URL 추출
  - 브랜드/상품명 파싱

### 4. Poizon 입찰 시스템

#### 💰 **poison_bidder_wrapper_v2.py**
- **용도**: Poizon 플랫폼 입찰 래퍼
- **주요 기능**:
  - 자동 로그인
  - 상품 검색 및 매칭
  - 가격 입찰
  - 오류 재시도

#### 🔐 **login_manager.py**
- **용도**: 통합 로그인 관리
- **주요 기능**:
  - 무신사, ABC마트, Poizon 로그인
  - 쿠키 저장 및 재사용
  - 세션 유지

### 5. 유틸리티 파일

#### 📊 **status_constants.py**
- **용도**: 상태 메시지 상수 정의
- **내용**:
  - 진행 단계별 메시지 템플릿
  - 이모지 정의
  - 진행률 임계값

#### 💸 **price_adjuster_gui.py**
- **용도**: 가격 조정 GUI (독립 실행)
- **주요 기능**:
  - 시각적 가격 조정
  - 할인율 적용
  - 수익 계산

### 6. 설정 파일

#### ⚙️ **config/bot_config.json**
- **용도**: 텔레그램 봇 설정
- **내용**:
  - 봇 토큰
  - 관리자 ID
  - 기본 설정값

#### ⚙️ **config/config.json**
- **용도**: 전체 시스템 설정
- **내용**:
  - 사이트별 설정
  - 입찰 전략
  - 할인 정책

#### 🔑 **.env**
- **용도**: 환경 변수 (민감한 정보)
- **내용**:
  - 텔레그램 봇 토큰
  - API 키
  - 로그인 정보

### 7. 배치 실행 파일

#### 🚀 **start_bot.bat**
- **용도**: 텔레그램 봇 시작
- **내용**: `python telegram_bot.py`

#### 🔄 **restart_bot.bat**
- **용도**: 봇 재시작
- **기능**: 기존 프로세스 종료 후 재시작

#### ⏰ **start_scheduler.bat**
- **용도**: 스케줄러 시작
- **내용**: `python scheduler.py`

## 📂 디렉토리 구조

```
C:\poison_final\
├── config/          # 설정 파일
├── input/          # 링크 파일 저장
├── output/         # 결과 파일 저장
├── logs/           # 로그 파일
├── cookies/        # 쿠키 저장
├── data/           # 임시 데이터
├── test/           # 테스트 코드
└── docs/           # 문서
```

## 🔧 주요 의존성 파일

- **requirements.txt**: 기본 의존성
- **requirements_auto.txt**: 자동화 추가 의존성

## 📝 문서 파일

- **README.md**: 프로젝트 전체 가이드
- **TELEGRAM_BOT_GUIDE.md**: 텔레그램 봇 사용법
- **AUTO_BIDDING_GUIDE.md**: 자동 입찰 가이드
- **SCHEDULER_GUIDE.md**: 스케줄러 설정
- **POISON_LOGIN_SETUP.md**: Poizon 로그인 설정

## 🎯 사용 시나리오

### 1. 자동화 입찰 (추천)
1. `start_bot.bat` 실행
2. 텔레그램에서 `/auto 나이키` 입력
3. 할인 설정 후 자동 실행

### 2. 수동 입찰
1. 링크 추출기로 `input/musinsa_links.txt` 생성
2. `python unified_bidding.py musinsa basic` 실행

### 3. 스케줄 실행
1. `config/scheduler_config.json` 설정
2. `start_scheduler.bat` 실행
3. 지정 시간에 자동 실행

## ⚠️ 주의사항

1. **로그인 정보**: `.env` 파일에 로그인 정보 설정 필요
2. **Chrome 버전**: ChromeDriver 버전과 Chrome 브라우저 버전 일치 필요
3. **쿠키 유효성**: 주기적으로 로그인 갱신 필요
4. **API 제한**: 너무 빠른 요청 시 차단 가능

## 🐛 디버깅 파일

- **test_telegram.py**: 텔레그램 봇 테스트
- **test_auto_bidding.py**: 자동 입찰 테스트
- **test_poison_login_status.py**: Poizon 로그인 테스트
- **debug_poison_login.py**: 로그인 디버깅

이 가이드는 프로젝트의 주요 파일들을 설명합니다. 각 파일의 상세 사용법은 개별 문서를 참조하세요.
