# K-Fashion 자동 입찰 시스템 통합

기존 GUI 기반 프로그램들을 통합하여 텔레그램 봇으로 24시간 자동화한 시스템입니다.

## 🚀 주요 기능

- 가격 전략 기반 자동 입찰
- 무신사, ABC마트 지원
- 텔레그램 봇 제어
- 24시간 스케줄링
- 실시간 진행 상황 알림

## 📁 프로젝트 구조

```
poison_final/
├── config/              # 설정 파일
├── db/                  # 데이터베이스
├── logs/                # 로그 파일
├── unified_bidding.py   # 메인 통합 모듈
├── telegram_bot.py      # 텔레그램 봇
└── scheduler.py         # 스케줄러
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
