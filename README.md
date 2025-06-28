# K-Fashion 자동 입찰 시스템 통합

기존 GUI 기반 프로그램들을 통합하여 텔레그램 봇으로 24시간 자동화한 시스템입니다.

## 🚀 주요 기능

- 가격 전략 기반 자동 입찰
- 무신사, ABC마트 지원
- 텔레그램 봇 제어
- 24시간 스케줄링
- 실시간 진행 상황 알림
- **Chrome 138+ 자동 호환성 지원**

## 📁 프로젝트 구조

```
poison_final/
├── config/              # 설정 파일
├── db/                  # 데이터베이스
├── logs/                # 로그 파일
├── unified_bidding.py   # 메인 통합 모듈
├── telegram_bot.py      # 텔레그램 봇
├── scheduler.py         # 스케줄러
└── chrome_driver_manager.py  # ChromeDriver 자동 관리
```

## 🛠️ 설치 방법

1. 필수 패키지 설치
```bash
pip install -r requirements.txt
```

2. 환경 변수 설정
```bash
cp .env.example .env
# .env 파일을 열어서 TELEGRAM_BOT_TOKEN 설정
```

3. 데이터베이스 초기화
```bash
python db/init_db.py
```

## 🌟 ChromeDriver 자동 관리

Chrome 138 이상 버전에서 ChromeDriver 버전 불일치 문제를 자동으로 해결합니다.

### 특징
- Chrome 버전 자동 감지
- 호환되는 ChromeDriver 자동 다운로드
- 버전 불일치 시 자동 업데이트
- 멀티프로세스 환경 지원

### 사용 방법
```python
from chrome_driver_manager import initialize_chrome_driver

# 기본 사용
driver = initialize_chrome_driver()

# 헤드리스 모드
driver = initialize_chrome_driver(headless=True)

# 워커 ID 지정 (멀티프로세스)
driver = initialize_chrome_driver(worker_id=1, headless=True)
```

### 주의사항
- 프로젝트 루트에 chromedriver.exe를 직접 넣을 필요가 없습니다
- webdriver-manager가 자동으로 관리합니다
- 기존 chromedriver 파일들은 backup_chromedriver 폴더에 백업되어 있습니다

## 🤖 사용 방법

1. 텔레그램 봇 실행
```bash
python telegram_bot.py
```

2. 텔레그램에서 봇 찾아서 명령어 입력
- `/start` - 봇 시작
- `/bid <전략>` - 입찰 실행
- `/status` - 현재 상태
- `/stop` - 작업 중지

## ⚙️ 가격 전략 설정

`config/pricing_strategies.json` 파일에서 할인 전략을 수정할 수 있습니다.

## 📝 로그

모든 로그는 `logs/` 디렉토리에 저장됩니다.

## 🔧 문제 해결

### Chrome 버전 관련 오류
Chrome이 자동 업데이트되어 버전이 변경되어도 시스템이 자동으로 대응합니다.
만약 문제가 발생하면:

1. Chrome 버전 확인
```bash
python check_chrome_version.py
```

2. ChromeDriver 캐시 정리
```bash
python clean_uc_cache.py
```

3. 통합 테스트 실행
```bash
python test/test_chrome138_integration.py
```

## 📚 추가 문서

- [텔레그램 봇 가이드](TELEGRAM_BOT_GUIDE.md)
- [스케줄러 가이드](SCHEDULER_GUIDE.md)
- [자동 입찰 가이드](AUTO_BIDDING_GUIDE.md)
