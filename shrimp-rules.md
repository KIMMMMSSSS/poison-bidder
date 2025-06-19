# Development Guidelines

## Project Overview
- 포이즌(Poizon) 플랫폼 자동 입찰 시스템
- 텔레그램 봇을 통한 제어 및 모니터링
- 무신사, ABC마트 등 쇼핑몰에서 상품 정보 수집 후 포이즌에 자동 입찰

## Project Architecture

### Main Directories
- `/` - 프로젝트 루트 (C:\poison_final)
- `/config` - 설정 파일들 (pricing_strategies.json 등)
- `/cookies` - 사이트별 쿠키 파일 저장
- `/logs` - 모든 로그 파일 저장 (필수 경로: C:\poison_final\logs)
- `/output` - 실행 결과 파일 저장
- `/db` - SQLite 데이터베이스
- `/input` - 입력 데이터 파일

### Core Modules
- `telegram_bot.py` - 메인 텔레그램 봇 제어
- `auto_bidding.py` - 자동 입찰 파이프라인
- `unified_bidding.py` - 통합 입찰 실행
- `poison_integrated_bidding.py` - 포이즌 입찰 어댑터
- `abcmart_scraper_improved_backup.py` - ABC마트 스크래퍼
- `musinsa_scraper_improved.py` - 무신사 스크래퍼

## Code Standards

### Import Order
1. 표준 라이브러리
2. 서드파티 라이브러리
3. 로컬 모듈

### Error Handling
- 모든 예외는 logs 디렉토리에 기록
- 사용자에게는 간단한 메시지만 표시
- traceback은 로그 파일에만 저장

### Database
- MySQL 접속 정보는 .env 파일에서 관리
- 접속 형식: `mysql -u root -e "QUERY;" DB_NAME`
- 쿼리는 반드시 따옴표로 감싸야 함

## Functionality Implementation Standards

### 로그인 처리
- **무신사**: 로그인 필수 (LoginManager 사용)
- **ABC마트**: 로그인 불필요 - 로그인 체크 로직 건너뛰기
- **포이즌**: 로그인 필수 (쿠키 기반)

### 스크래핑 규칙
- 4자리 사이즈는 제외 (예: 1000)
- 신발 사이즈 범위: 220-310
- 재고 5개 미만 상품 제외
- ABC마트는 회원 최대혜택가 우선 적용

### 파일 작업
- 파일 생성/수정 후 반드시 git add 및 commit
- 대용량 파일은 3-5개 섹션으로 나누어 처리
- 파일 편집 전 항상 해당 부분 재확인

## Framework/Plugin/Third-party Library Usage Standards

### Selenium/Undetected ChromeDriver
- 워커별 고유 포트 사용 (9222 + worker_id)
- 워커별 임시 디렉토리 생성
- headless 모드 기본 사용
- Chrome 프로세스는 작업 완료 후 강제 종료

### 텔레그램 봇
- python-telegram-bot 라이브러리 사용
- 콜백 쿼리는 항상 응답 필요
- 긴 작업은 비동기 처리

## Workflow Standards

### 자동 입찰 워크플로우
1. 키워드로 상품 검색
2. 링크 추출 (사이트별 로그인 체크)
3. 상품 정보 스크래핑
4. 가격 조정 (전략 적용)
5. 포이즌 입찰 실행
6. 결과 저장 및 알림

### Git 워크플로우
1. 변경사항은 test 브랜치에서 작업
2. 충분한 테스트 후 master에 병합
3. 파일 작업마다 의미있는 커밋 메시지

## Key File Interaction Standards

### 동시 수정 필요 파일
- `auto_bidding.py` 수정 시 → `telegram_bot.py` 확인
- 가격 전략 변경 시 → `config/pricing_strategies.json` 수정
- 로그 경로 변경 금지 → 항상 `C:\poison_final\logs` 사용

### 데이터 흐름
- 텔레그램 봇 → auto_bidding → scraper → poison_integrated_bidding
- 결과는 항상 output 디렉토리에 JSON 형식으로 저장
- 로그는 항상 logs 디렉토리에 날짜별로 저장

## AI Decision-making Standards

### 오류 처리 우선순위
1. 로그인 실패 → 사이트별 로그인 요구사항 확인
2. 스크래핑 실패 → 셀렉터 변경 확인
3. 입찰 실패 → 데이터 형식 및 로그인 상태 확인

### 코드 수정 시
1. 항상 현재 코드 상태 확인 후 수정
2. dryRun: true로 먼저 테스트
3. 한 번에 하나의 기능만 수정

## Prohibited Actions

### 절대 금지
- `C:\poison_final\logs` 이외의 경로에 로그 저장
- 로그인이 필요없는 사이트에 로그인 강제
- 사용자 동의 없이 shrimp 작업 삭제 또는 초기화
- 한 번에 전체 파일 재작성 (섹션별로 나누어 처리)

### 주의 사항
- ABC마트는 로그인 체크 로직 실행 금지
- 4자리 사이즈 코드는 항상 필터링
- edit_file_lines 사용 시 항상 dryRun: true 먼저
- 파일 수정 전 해당 부분 라인 번호 재확인
