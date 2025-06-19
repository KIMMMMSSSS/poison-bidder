# 텔레그램 봇 설정 가이드

## 1. 봇 생성
1. 텔레그램에서 @BotFather 검색
2. `/newbot` 명령어 입력
3. 봇 이름과 username 설정
4. 생성된 토큰 복사

## 2. 설정 파일 수정
`config/bot_config.json` 파일을 열어서:
- `YOUR_BOT_TOKEN_HERE`를 실제 봇 토큰으로 교체
- `admin_ids`에 자신의 텔레그램 User ID 추가

텔레그램 User ID 확인 방법:
1. @userinfobot 검색 후 시작
2. 표시되는 ID 복사

## 3. 봇 실행
```bash
python telegram_bot.py
```

## 4. 사용 가능한 명령어
- `/start` - 봇 시작
- `/bid [site] [strategy]` - 입찰 시작
- `/status` - 현재 상태 확인
- `/stop` - 작업 중지
- `/strategies` - 전략 목록
- `/help` - 도움말

## 5. 입찰 예시
- `/bid` - 기본 설정(무신사, basic 전략)
- `/bid abcmart` - ABC마트 입찰
- `/bid musinsa standard` - 무신사 standard 전략

## 주의사항
- admin_ids에 등록된 사용자만 봇 사용 가능
- 한 번에 하나의 작업만 실행 가능
- 입찰 전 input 폴더에 링크 파일 필요
