# 자동화 입찰 설치 가이드

## 필수 패키지 설치

자동화 기능을 사용하려면 추가 패키지가 필요합니다:

```bash
# Selenium과 undetected-chromedriver 설치
pip install selenium undetected-chromedriver

# 또는 requirements에서 설치
pip install -r requirements_auto.txt
```

## Chrome 브라우저 설치

1. Google Chrome이 설치되어 있어야 합니다
2. 최신 버전으로 업데이트하세요

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

### "Chrome이 자동화된 테스트 소프트웨어에 의해 제어되고 있습니다" 메시지
정상적인 메시지입니다. undetected-chromedriver가 작동 중입니다.

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
