# Development Guidelines

## Project Overview

### 프로젝트 구조
- 루트 디렉토리: C:\poison_final
- 웹 루트: http://localhost
- 주요 시스템: K-Fashion 자동 입찰 시스템 (무신사, ABC마트 → Poizon)

### 핵심 모듈
- telegram_bot.py: 메인 제어 인터페이스
- auto_bidding.py: 자동화 파이프라인
- chrome_driver_manager.py: Chrome 드라이버 관리
- abcmart/musinsa 스크래퍼: 상품 정보 수집
- poison_bidder: Poizon 플랫폼 입찰

## Chrome Driver 관리 규칙

### 드라이버 초기화 필수 사항
- initialize_chrome_driver 함수는 절대 None을 반환하면 안됨
- 예외 발생 시 명확한 에러 메시지와 함께 Exception을 raise할 것
- 드라이버 초기화 실패 시 재시도 로직 포함 필수

### 드라이버 버전 관리
- Chrome과 ChromeDriver 메이저 버전 일치 필수
- 버전 불일치 시 자동 다운로드 시도
- chromedriver.exe는 항상 C:\poison_final에 위치

### 프로필 관리
- 각 워커는 독립적인 임시 프로필 사용
- --user-data-dir 옵션으로 격리된 프로필 지정
- Chrome 프로필 선택 화면 방지 옵션 필수 적용

## 파일 수정 규칙

### 편집 전 필수 확인
- 파일 수정 전 항상 해당 부분 근처 코드 확인
- 라인 번호는 수정할 때마다 변경되므로 재확인 필수
- 3-5개 섹션으로 나누어 순차적 수정

### Git 연동
- 모든 파일 생성/수정 후 git add와 commit 수행
- 커밋 메시지는 명확하고 구체적으로 작성
- 파일 삭제 시 git rm 사용

### 테스트 브랜치 운영
- 주요 변경사항은 test 브랜치에서 먼저 검증
- 충분한 테스트 후 master에 병합

## 로깅 및 에러 처리

### 로그 위치
- 모든 로그는 C:\poison_final\logs에 저장
- 에러 로그는 즉시 파일로 기록

### 에러 처리 원칙
- try-except 블록에서 구체적인 예외 타입 명시
- 에러 발생 시 상세한 컨텍스트 정보 포함
- 중요 작업은 재시도 로직 구현

## 데이터베이스 접근

### MySQL 연결
- 호스트: localhost
- 사용자: root
- 쿼리 실행 시 항상 따옴표로 감싸기
- 예: mysql -u root -e "SHOW DATABASES;"

## 멀티프로세싱 주의사항

### 워커 프로세스
- 각 워커는 독립적인 Chrome 인스턴스 사용
- 프로세스 종료 시 Chrome 정리 필수
- 0으로 나누기 등 예외 상황 처리

### URL 처리
- URL이 0개인 경우 처리 로직 필수
- 평균 계산 시 분모가 0인지 확인

## 텔레그램 봇 규칙

### 메시지 포맷
- 마크다운 엔티티 정확히 닫기
- 특수 문자 이스케이프 처리
- 메시지 길이 제한 고려

## 금지 사항

### 절대 하지 말 것
- Chrome 드라이버 초기화 함수에서 None 반환
- 에러 처리 없는 파일 작업
- 테스트 없는 master 브랜치 직접 수정
- 0으로 나누기 가능성 있는 계산
- git 커밋 없는 파일 수정

### 사용 금지 패턴
- driver = None 후 driver 메서드 호출
- 하드코딩된 절대 경로 (C:\poison_final 제외)
- 동기화 없는 멀티프로세스 공유 자원 접근

## AI 의사결정 기준

### 우선순위
1. 시스템 안정성 (드라이버 초기화 성공)
2. 데이터 무결성 (0개 처리 등)
3. 사용자 경험 (에러 메시지 명확성)

### 수정 시 체크리스트
- [ ] 드라이버가 None 반환 가능성 제거
- [ ] 0으로 나누기 방지 로직 추가
- [ ] 에러 메시지 구체적으로 작성
- [ ] Git 커밋 수행
- [ ] 로그 파일 경로 확인

## 프로젝트별 특수 규칙

### ABC마트 스크래퍼
- use_undetected=False 설정 필수
- 로그인 불필요
- 멀티프로세싱 시 워커별 지연 시간 적용

### Poizon 입찰
- 로그인 쿠키 유지 관리
- 입찰 실패 시 재시도 로직
- 가격 조정 로직 검증

### 파일 경로 규칙
- input/: 링크 파일 저장
- output/: 결과 파일 저장
- cookies/: 쿠키 저장
- config/: 설정 파일
