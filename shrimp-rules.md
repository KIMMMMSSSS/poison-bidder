# K-Fashion 자동 입찰 시스템 개발 가이드라인

## 프로젝트 개요

- **목적**: K-Fashion 쇼핑몰 자동 입찰 시스템 통합 및 24시간 자동화
- **핵심 흐름**: 가격조정 설정 → 링크 추출 → 상품 스크래핑 → 가격 적용 → 자동 입찰
- **기술 스택**: Python 3.x, SQLite, Telegram Bot API, APScheduler
- **대상 사이트**: 무신사(Musinsa), ABC마트(ABCMart)

## 프로젝트 아키텍처

### 주요 모듈 구성

- **가격 조정 모듈**: price_adjuster_gui.py 기반, GUI 제거 후 설정 파일 방식
- **링크 추출 모듈**: musinsa_link_extractor.py, abcmart_link_extractor.py
- **스크래핑 모듈**: musinsa_scraper_improved.py, abcmart_scraper_improved_backup.py  
- **입찰 실행 모듈**: 0923_fixed_multiprocess_cookie_v2.py
- **통합 컨트롤러**: 새로 생성할 unified_bidding_system.py
- **텔레그램 봇**: 새로 생성할 telegram_bot.py

### 디렉토리 구조

```
C:\poison_final\
├── config/              # 설정 파일
│   ├── pricing_strategy.json    # 가격 조정 전략
│   ├── telegram_config.json     # 텔레그램 봇 설정
│   └── schedule_config.json     # 스케줄링 설정
├── modules/             # 핵심 모듈
│   ├── pricing/         # 가격 조정 관련
│   ├── extraction/      # 링크 추출 관련
│   ├── scraping/        # 스크래핑 관련
│   └── bidding/         # 입찰 실행 관련
├── bot/                 # 텔레그램 봇
├── db/                  # SQLite 데이터베이스
├── logs/                # 로그 파일
└── data/                # 입출력 데이터
```

## 코드 표준

### 필수 준수 사항

- **GUI 제거**: tkinter, customtkinter 등 모든 GUI 관련 코드 제거
- **설정 파일 사용**: 하드코딩 금지, 모든 설정은 JSON 파일로 관리
- **클래스 구조**: 각 모듈은 BaseModule 추상 클래스 상속
- **비동기 처리**: 긴 작업은 반드시 비동기(async/await) 또는 스레드 사용
- **로깅**: 모든 로그는 C:\poison_final\logs 디렉토리에 저장

### 명명 규칙

- **클래스**: PascalCase (예: PriceAdjuster, LinkExtractor)
- **함수/메서드**: snake_case (예: extract_links, apply_discount)
- **상수**: UPPER_SNAKE_CASE (예: MAX_RETRY_COUNT, DEFAULT_TIMEOUT)
- **파일명**: snake_case (예: price_adjuster.py, telegram_bot.py)

## 기능 구현 표준

### 가격 조정 모듈 변환

- price_adjuster_gui.py의 GUI 부분 제거
- PriceAdjuster 클래스로 리팩토링
- calculate_adjusted_price() 메서드 보존
- 설정은 pricing_strategy.json에서 로드

### 통합 시스템 구현

- UnifiedBiddingSystem 클래스 생성
- 각 모듈을 순차적으로 실행하는 run_pipeline() 메서드
- 각 단계별 결과를 SQLite DB에 저장
- 실패 시 재시도 로직 (최대 3회)

### 데이터베이스 스키마

```sql
-- 작업 큐 테이블
CREATE TABLE bid_jobs (
    id INTEGER PRIMARY KEY,
    status TEXT,
    created_at TIMESTAMP,
    completed_at TIMESTAMP,
    settings TEXT,
    result TEXT
);

-- 가격 전략 테이블
CREATE TABLE pricing_strategies (
    id INTEGER PRIMARY KEY,
    name TEXT,
    coupon_rate REAL,
    points_rate REAL,
    premium_settings TEXT,
    cashback_rate REAL
);

-- 입찰 히스토리 테이블
CREATE TABLE bid_history (
    id INTEGER PRIMARY KEY,
    job_id INTEGER,
    product_code TEXT,
    original_price INTEGER,
    adjusted_price INTEGER,
    bid_result TEXT,
    timestamp TIMESTAMP
);
```

### 텔레그램 봇 명령어

- `/start` - 봇 시작 및 환영 메시지
- `/bid <설정명>` - 지정된 설정으로 입찰 시작
- `/status` - 현재 진행 상황 확인
- `/strategy` - 가격 전략 설정
- `/schedule` - 자동 실행 스케줄 설정
- `/stop` - 진행 중인 작업 중지
- `/history` - 최근 입찰 내역 조회

## 작업 흐름 표준

### 통합 파이프라인 실행 순서

1. **설정 로드**: pricing_strategy.json에서 가격 조정 설정 읽기
2. **링크 추출**: 각 사이트에서 상품 링크 수집
3. **스크래핑**: 상품 정보 스크래핑 (코드, 색상, 사이즈, 가격)
4. **가격 조정**: 설정된 할인율 적용하여 입찰가 계산
5. **입찰 실행**: 조정된 가격으로 자동 입찰
6. **결과 저장**: DB에 결과 저장 및 텔레그램 알림

### 에러 처리

- 각 단계별 try-except 블록 사용
- 실패 시 상세 에러 로그 기록
- 재시도 가능한 에러는 3회까지 재시도
- 치명적 에러는 텔레그램으로 즉시 알림

## 핵심 파일 상호작용 표준

### 설정 파일 동기화

- pricing_strategy.json 수정 시 반드시 DB의 pricing_strategies 테이블도 업데이트
- schedule_config.json 수정 시 APScheduler 재시작 필요

### 모듈 간 데이터 전달

- 각 모듈은 표준화된 딕셔너리 형식으로 데이터 반환
- 예: `{'status': 'success', 'data': [...], 'error': None}`

## AI 의사결정 표준

### 재시도 판단 기준

1. **네트워크 에러**: 3회 재시도 (간격: 5초, 10초, 20초)
2. **파싱 에러**: 1회 재시도 (다른 파싱 방법 시도)
3. **인증 에러**: 재시도 없음, 사용자에게 알림

### 가격 조정 우선순위

1. 쿠폰 할인 적용
2. 적립금/포인트 할인 적용
3. 무신사 카드 프리미엄 적용 (조건 충족 시)
4. 카드 캐시백 적용

## 금지 사항

### 절대 사용 금지

- **GUI 라이브러리**: tkinter, PyQt, customtkinter 등
- **하드코딩**: 설정값, 경로, 인증 정보 등
- **동기 blocking**: time.sleep() 대신 asyncio.sleep() 사용
- **print()**: 로깅 라이브러리 사용 (logging 모듈)

### 피해야 할 패턴

- 전역 변수 사용 (클래스 속성으로 대체)
- 중복 코드 (공통 함수로 추출)
- 긴 함수 (50줄 이상은 분리)
- 매직 넘버 (상수로 정의)

## 테스트 및 검증

### 단위 테스트 대상

- 가격 계산 로직
- 데이터 파싱 로직
- DB 연동 함수

### 통합 테스트 시나리오

- 전체 파이프라인 실행
- 에러 발생 시 복구
- 동시 실행 처리

## 배포 및 운영

### 환경 변수

- `TELEGRAM_BOT_TOKEN`: 텔레그램 봇 토큰
- `DB_PATH`: SQLite 데이터베이스 경로
- `LOG_LEVEL`: 로깅 레벨 (DEBUG, INFO, WARNING, ERROR)

### 로그 관리

- 일별 로그 파일 생성
- 30일 이상 된 로그는 자동 삭제
- 에러 로그는 별도 파일에 저장
