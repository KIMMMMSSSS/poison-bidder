# 자동화 입찰 설치 가이드

## 필수 패키지 설치

자동화 기능을 사용하려면 추가 패키지가 필요합니다:

```bash
# Selenium과 webdriver-manager 설치
pip install selenium webdriver-manager

# 또는 requirements에서 설치
pip install -r requirements_auto.txt
```

## Chrome 브라우저 설치

1. Google Chrome이 설치되어 있어야 합니다
2. 최신 버전(138+)으로 업데이트하세요
3. **ChromeDriver는 자동으로 관리됩니다**

## Chrome 자동 관리 시스템

### 특징
- Chrome 버전 자동 감지
- 호환되는 ChromeDriver 자동 다운로드
- 버전 불일치 시 자동 업데이트
- 수동 ChromeDriver 설치 불필요

### 동작 원리
```python
# chrome_driver_manager.py가 모든 것을 처리
from chrome_driver_manager import initialize_chrome_driver

# Chrome 138에서도 자동으로 작동
driver = initialize_chrome_driver()
```

## 사용 방법

### 1. 텔레그램 봇 실행
```bash
python telegram_bot.py
```

### 2. 텔레그램에서 명령어 사용

**자동화 입찰 (링크 추출 + 입찰)**
```
/auto 나이키
/auto musinsa 아디다스 에어포스
/auto abcmart 운동화
```

**수동 입찰 (링크 파일 필요)**
```
/bid musinsa basic
```

### 3. 자동화 설정 변경

`config/auto_bidding_config.json` 파일에서:
- 검색 키워드 기본값
- 최대 링크 수
- 스크롤 횟수
- 대기 시간

## 문제 해결

### Chrome 버전 관련 오류
시스템이 자동으로 처리하지만, 문제 발생 시:

```bash
# Chrome 버전 확인
python check_chrome_version.py

# ChromeDriver 캐시 정리
python clean_uc_cache.py

# 통합 테스트
python test/test_chrome138_integration.py
```

### "Chrome이 자동화된 테스트 소프트웨어에 의해 제어되고 있습니다" 메시지
정상적인 메시지입니다. Selenium이 작동 중입니다.

### 링크를 찾을 수 없음
- 검색 키워드가 너무 구체적이지 않은지 확인
- 사이트가 변경되었을 수 있으니 로그 확인

### 느린 속도
- `max_links`를 줄여서 처리할 상품 수 제한
- `max_scrolls`를 줄여서 페이지 스크롤 횟수 제한

## 추천 사용법

1. 먼저 적은 수의 상품으로 테스트
   ```
   /auto 나이키 (기본 30개 상품)
   ```

2. 잘 작동하면 설정 파일에서 max_links 증가

3. 특정 상품을 찾으려면 구체적인 키워드 사용
   ```
   /auto musinsa 나이키 에어포스 화이트
   ```

## Chrome 업데이트 대응

Chrome이 자동으로 업데이트되어도:
- 시스템이 자동으로 새 버전 감지
- 호환되는 ChromeDriver 자동 다운로드
- 재시작 없이 계속 작동

더 이상 Chrome 버전 때문에 걱정할 필요가 없습니다!
