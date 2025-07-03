# K-Fashion 자동 입찰 시스템 - 실제 사용 파일 리스트

## 🔥 현재 활발히 사용되는 핵심 파일

### 1. 메인 실행 파일
```
telegram_bot.py          # 텔레그램 봇 메인
auto_bidding.py         # 자동화 파이프라인
unified_bidding.py      # 통합 입찰 시스템
scheduler.py            # 스케줄 실행
```

### 2. 링크 추출기
```
musinsa_link_extractor.py    # 무신사 링크 추출
abcmart_link_extractor.py    # ABC마트 링크 추출
```

### 3. 스크래퍼
```
musinsa_scraper_improved.py      # 무신사 스크래핑
abcmart_scraper_improved_backup.py   # ABC마트 스크래핑
```

### 4. Poizon 입찰
```
poison_bidder_wrapper_v2.py      # Poizon 입찰 래퍼 (최신)
login_manager.py                 # 통합 로그인 관리
poison_login_manager.py          # Poizon 전용 로그인
```

### 5. 유틸리티
```
status_constants.py              # 상태 메시지 상수
price_adjuster_gui.py           # 가격 조정 GUI
```

### 6. 설정 파일
```
config/bot_config.json          # 텔레그램 봇 설정
config/config.json              # 시스템 전체 설정
config/scheduler_config.json    # 스케줄러 설정
.env                           # 환경 변수
```

### 7. 실행 스크립트
```
start_bot.bat                   # 봇 시작
restart_bot.bat                 # 봇 재시작
start_scheduler.bat             # 스케줄러 시작
```

## 📝 문서 파일
```
README.md
TELEGRAM_BOT_GUIDE.md
AUTO_BIDDING_GUIDE.md
SCHEDULER_GUIDE.md
POISON_LOGIN_SETUP.md
docs/PROJECT_FILES_GUIDE.md     # 이 문서
```

## 🧪 유용한 테스트 파일
```
test_telegram.py                # 텔레그램 봇 테스트
test_auto_bidding.py           # 자동 입찰 테스트
test_poison_login_status.py    # 로그인 상태 확인
test_full_integration.py       # 전체 통합 테스트
```

## 📊 로그 및 데이터 디렉토리
```
logs/                          # 실행 로그
input/                         # 링크 파일
output/                        # 결과 파일
cookies/                       # 로그인 쿠키
```

## ⚠️ 사용하지 않거나 백업 파일
```
# 백업 파일
telegram_bot_backup.py
poison_bidder_wrapper_v2_backup.py
poison_bidder_wrapper.py        # 구버전

# 테스트/개발용
0923_fixed_multiprocess_cookie_v2.py
worker_process_module.py
debug_*.py

# 구버전 파일
musinsa_poison_bid_example.py
poison_integrated_bidding.py
```

## 🚀 빠른 시작 가이드

### 1. 텔레그램 봇으로 시작 (추천)
```bash
# 1. 설정
- config/bot_config.json에 봇 토큰 설정
- .env 파일에 로그인 정보 설정

# 2. 실행
start_bot.bat

# 3. 텔레그램에서 사용
/auto 나이키
```

### 2. 직접 실행
```bash
# 링크 추출
python musinsa_link_extractor.py 나이키

# 자동 입찰
python auto_bidding.py musinsa 나이키
```

### 3. 스케줄 실행
```bash
# 설정 후 실행
start_scheduler.bat
```

## 💡 개발 팁

1. **로그 확인**: `logs/` 폴더에서 오류 추적
2. **쿠키 갱신**: 로그인 실패 시 `cookies/` 폴더 정리
3. **테스트**: `test_*.py` 파일로 기능별 테스트

## 📌 중요 참고사항

- **ChromeDriver**: Chrome 버전과 일치 필요
- **Python 버전**: 3.8 이상 권장
- **의존성 설치**: `pip install -r requirements.txt`
