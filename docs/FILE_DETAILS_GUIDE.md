# K-Fashion 자동 입찰 시스템 - 파일별 상세 설명

## 📱 텔레그램 봇 시스템

### telegram_bot.py
**역할**: 메인 제어 인터페이스
```python
# 주요 명령어
/start      # 봇 시작
/auto       # 자동화 입찰 (대화형)
/bid        # 수동 입찰
/status     # 현재 작업 상태
/stop       # 작업 중지
/help       # 도움말

# 사용 예시
/auto musinsa 나이키
/auto abcmart 운동화
/bid musinsa standard
```

**특징**:
- 대화형 인터페이스로 할인 설정
- 실시간 진행 상황 알림
- 오류 처리 및 재시도

### auto_bidding.py
**역할**: 자동화 파이프라인 실행기
```python
# 메인 함수
run_auto_pipeline(
    site='musinsa',
    keywords=['나이키'],
    strategy='basic',
    status_callback=None,
    custom_discount_rate=10.0,
    custom_min_profit=5000,
    points_rate=3.0,
    card_discount={...}
)
```

**프로세스**:
1. 링크 추출 (키워드 검색)
2. 상품 정보 스크래핑
3. 가격 조정 (할인 적용)
4. Poizon 입찰

## 🔗 링크 추출 시스템

### musinsa_link_extractor.py
**역할**: 무신사 상품 링크 수집
```python
# 사용법
python musinsa_link_extractor.py [키워드] [옵션]

# 옵션
--pages N        # 최대 페이지 수
--category CAT   # 카테고리 필터
--min-price N    # 최소 가격
--max-price N    # 최대 가격

# 예시
python musinsa_link_extractor.py "나이키 에어포스" --pages 5
```

**출력 형식**:
```
https://www.musinsa.com/app/goods/1234567
https://www.musinsa.com/app/goods/1234568
```

### abcmart_link_extractor.py
**역할**: ABC마트 상품 링크 수집
```python
# 내부 구조
extract_links_multiprocess(
    search_keyword="나이키",
    max_pages=10,
    max_workers=5
)
```

**특징**:
- 멀티프로세싱으로 빠른 수집
- 상품 수 급감 시 자동 종료
- 브랜드별 검색 지원

## 📦 스크래핑 시스템

### musinsa_scraper_improved.py
**데이터 추출**:
```python
{
    "url": "상품 URL",
    "name": "상품명",
    "brand": "브랜드",
    "price": 가격,
    "image_url": "이미지 URL",
    "category": "카테고리",
    "availability": true/false
}
```

**팝업 처리**:
- 자동 쿠폰 팝업 닫기
- 회원가입 유도 팝업 처리
- 동적 로딩 대기

### abcmart_scraper_improved_backup.py
**특별 기능**:
- JavaScript 렌더링 대기
- 이미지 지연 로딩 처리
- 재시도 로직 (3회)

## 💰 Poizon 입찰 시스템

### poison_bidder_wrapper_v2.py
**주요 메소드**:
```python
# 로그인
login()

# 상품 검색
search_product(keyword, image_url)

# 입찰
submit_bid(product_id, size, price)

# 파이프라인 실행
run_pipeline(
    site='musinsa',
    strategy_id='basic',
    exec_mode='full'
)
```

**입찰 전략**:
- basic: 기본 할인율 적용
- standard: 중간 할인율
- premium: 높은 할인율
- aggressive: 공격적 할인

### login_manager.py
**통합 로그인 관리**:
```python
# 사이트별 로그인
login_musinsa()
login_abcmart()
login_poizon()

# 쿠키 관리
save_cookies(site, cookies)
load_cookies(site)
```

## 📊 유틸리티

### status_constants.py
**상태 메시지 정의**:
```python
# 진행 단계
STAGE_INIT = "초기화"
STAGE_LINK = "링크 추출"
STAGE_SCRAPE = "스크래핑"
STAGE_PRICE = "가격 조정"
STAGE_BID = "입찰"

# 이모지
EMOJI_SEARCH = "🔍"
EMOJI_SUCCESS = "✅"
EMOJI_ERROR = "❌"
```

### price_adjuster_gui.py
**GUI 가격 조정기**:
- 시각적 인터페이스
- 실시간 수익 계산
- 배치 처리 지원

## ⚙️ 설정 파일 구조

### config/bot_config.json
```json
{
    "bot": {
        "token": "YOUR_BOT_TOKEN",
        "admin_ids": [123456789]
    },
    "bidding": {
        "default_site": "musinsa",
        "default_strategy": "standard"
    }
}
```

### config/config.json
```json
{
    "sites": {
        "musinsa": {
            "base_url": "https://www.musinsa.com",
            "search_url": "..."
        }
    },
    "strategies": {
        "basic": {
            "discount_rate": 0.05,
            "min_profit": 5000
        }
    }
}
```

### .env
```
# 텔레그램
TELEGRAM_BOT_TOKEN=your_token_here

# 로그인 정보
MUSINSA_ID=your_id
MUSINSA_PW=your_password
POIZON_ID=your_id
POIZON_PW=your_password
```

## 🧪 테스트 파일

### test_telegram.py
```bash
# 봇 연결 테스트
python test_telegram.py
```

### test_auto_bidding.py
```bash
# 자동 입찰 테스트
python test_auto_bidding.py --site musinsa --keyword 나이키
```

### test_poison_login_status.py
```bash
# 로그인 상태 확인
python test_poison_login_status.py
```

## 📈 로그 분석

### logs/ 디렉토리 구조
```
telegram_bot_YYYYMMDD.log      # 봇 실행 로그
auto_bidding_YYYYMMDD.log      # 자동 입찰 로그
poison_bidder_YYYYMMDD.log     # Poizon 입찰 로그
scraper_YYYYMMDD.log           # 스크래핑 로그
```

**로그 레벨**:
- INFO: 정상 동작
- WARNING: 경고 (재시도 등)
- ERROR: 오류 발생
- DEBUG: 상세 디버깅

## 🚀 실행 순서 이해하기

### 자동화 플로우
1. **telegram_bot.py** 시작
2. `/auto` 명령 입력
3. **auto_bidding.py** 호출
4. **musinsa_link_extractor.py** 실행
5. **musinsa_scraper_improved.py** 실행
6. 가격 조정 로직 적용
7. **poison_bidder_wrapper_v2.py** 입찰
8. 결과 텔레그램 전송

### 수동 플로우
1. 링크 파일 준비 (`input/musinsa_links.txt`)
2. **unified_bidding.py** 실행
3. 스크래핑 → 가격 조정 → 입찰
4. 결과 파일 생성 (`output/`)

이 문서는 각 파일의 구체적인 역할과 사용법을 설명합니다. 실제 사용 시 이 가이드를 참조하여 필요한 파일을 선택하고 활용하세요.
