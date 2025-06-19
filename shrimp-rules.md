# Development Guidelines

## 프로젝트 개요
- **목적**: 무신사/ABC마트 상품 스크래핑 → 포이즌 플랫폼 자동 입찰 시스템
- **기술 스택**: Python 3.11+, Selenium, undetected_chromedriver, multiprocessing
- **핵심 모듈**: 스크래퍼(musinsa/abcmart) → 통합 입찰(poison_integrated_bidding) → 포이즌 API
- **주요 데이터 흐름**: 스크래퍼 → JSON 파일 → auto_bidding/unified_bidding → poison_integrated_bidding → poison_bidder_wrapper_v2

## 필수 준수 규칙

### 파라미터 타입 검증 ⚠️ CRITICAL
- **모든 함수 시작 부분에 타입 검증 필수**
- **특히 run_with_poison, run_bidding 함수에서 필수**
- **예시**:
  ```python
  def run_with_poison(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
      # 필수: 타입 검증
      if not isinstance(items, list):
          logger.error(f"items 파라미터가 list가 아님: {type(items)}")
          raise TypeError(f"items는 list여야 합니다. 현재 타입: {type(items)}")
      
      # 필수: 빈 데이터 체크
      if not items:
          logger.warning("처리할 아이템이 없습니다")
          return {'status': 'error', 'message': '빈 아이템 리스트'}
      
      # 필수: 디버깅을 위한 로깅
      logger.info(f"입력 아이템 수: {len(items)}")
      logger.debug(f"첫 번째 아이템 예시: {items[0] if items else 'None'}")
  ```

### Path 객체 처리
- **금지**: `Path.replace()` 직접 사용
- **필수**: `str(path_obj).replace()` 또는 `path_obj.as_posix().replace()`
- **예시**:
  ```python
  # 잘못된 예
  log_path = Path("logs/test.log")
  new_path = log_path.replace("test", "prod")  # ❌
  
  # 올바른 예
  log_path = Path("logs/test.log")
  new_path = Path(str(log_path).replace("test", "prod"))  # ✅
  ```

### 로깅 시스템
- **로그 디렉토리**: 반드시 `C:\poison_final\logs` 사용
- **파일명 형식**: `{module}_{timestamp}.log` (예: `abcmart_20250619_223300.log`)
- **멀티프로세싱 로깅**: 워커별 고유 로그 파일 생성
- **오류 로깅 시 필수 포함**:
  ```python
  except Exception as e:
      logger.error(f"오류 발생: {e}")
      logger.error(f"Traceback: {traceback.format_exc()}")
  ```

### 데이터 전달 규칙
- **스크래퍼 → 입찰 모듈 데이터 전달**:
  1. 스크래퍼는 반드시 JSON 파일로 저장
  2. 파일명: `{site}_products_{timestamp}.json`
  3. 입찰 모듈은 JSON 파일 읽어서 처리
- **빈 데이터 체크 필수**:
  ```python
  if not items:
      logger.warning("처리할 아이템이 없습니다")
      return
  ```

### JSON 파일 처리
- **저장 시 필수 파라미터**:
  ```python
  with open(filename, 'w', encoding='utf-8') as f:
      json.dump(data, f, ensure_ascii=False, indent=2)
  ```
- **읽기 시 오류 처리**:
  ```python
  try:
      with open(filename, 'r', encoding='utf-8') as f:
          data = json.load(f)
  except (FileNotFoundError, json.JSONDecodeError) as e:
      logger.error(f"JSON 파일 읽기 실패: {e}")
      return []
  ```

### unified_items 형식
- **필수 필드**: code (product_code가 아님!), brand, size, price
- **선택 필드**: color, adjusted_price, link
- **형식 예시**:
  ```python
  unified_item = {
      'code': 'DZ2628-001',  # product_code가 아닌 code 사용!
      'brand': 'NIKE',
      'size': '270',
      'price': 139000,
      'color': '',  # 빈 문자열 허용
      'adjusted_price': 145000,  # price보다 우선 사용
      'link': 'https://...'  # 선택사항
  }
  ```

### 모듈 간 데이터 전달 체인
1. **스크래퍼 → auto_bidding/unified_bidding**:
   - JSON 파일로 전달
   - 필드명: product_code, brand, product_name 등
   
2. **auto_bidding/unified_bidding → poison_integrated_bidding**:
   - List[Dict] 형태로 전달
   - 필드명 변환: product_code → code
   
3. **poison_integrated_bidding → poison_bidder_wrapper_v2**:
   - unified_items 파라미터로 전달
   - **절대 bool 타입이면 안됨!**

## 멀티프로세싱 규칙

### Chrome 드라이버
- **포트 충돌 방지**: `port = 9222 + worker_id`
- **워커별 임시 디렉토리**: `f'chrome_worker_{worker_id}_{os.getpid()}'`
- **종료 시 정리 필수**:
  ```python
  finally:
      if driver:
          driver.quit()
      os.system(f"taskkill /F /PID {os.getpid()} >nul 2>&1")
  ```

### 파일 동시 접근
- **워커별 고유 파일명 사용**
- **공유 파일 접근 시 lock 사용**:
  ```python
  from multiprocessing import Lock
  lock = Lock()
  with lock:
      # 파일 읽기/쓰기
  ```

## 오류 처리 규칙

### 스크래핑 실패
- **부분 결과 저장**: 실패 전까지의 결과라도 저장
- **재시도 로직**: 최대 3회 재시도
- **실패 로깅**: URL, 오류 메시지, traceback 포함

### 입찰 실패
- **실패 아이템 기록**: `failed_items.json`에 저장
- **재시도 가능하도록 데이터 보존**
- **상세 오류 메시지 로깅**

## 스크래핑 규칙

### ABC마트 페이지네이션 처리
- **필수**: 검색 결과의 모든 페이지 순회
- **URL 파라미터**: `page` 파라미터 사용 (예: `&page=1`, `&page=2`)
- **종료 조건**: 상품이 없는 페이지 도달 시 중지
- **구현 예시**:
  ```python
  from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
  
  # URL에서 page 파라미터 제거
  parsed = urlparse(base_url)
  params = parse_qs(parsed.query)
  if 'page' in params:
      del params['page']
  
  page = 1
  while True:
      # 현재 페이지 URL 생성
      current_params = params.copy()
      current_params['page'] = [str(page)]
      new_query = urlencode(current_params, doseq=True)
      current_url = urlunparse((
          parsed.scheme, parsed.netloc, parsed.path,
          parsed.params, new_query, parsed.fragment
      ))
      
      # 페이지 로드 및 상품 추출
      links = extract_links_from_page(current_url)
      if not links:  # 상품이 없으면 종료
          break
      
      page += 1
  ```

### 무신사 페이지네이션 처리
- **필수**: 스크롤 또는 "더보기" 버튼 클릭으로 추가 상품 로드
- **대기 시간**: 새 상품 로드 시 충분한 대기 (2-3초)
- **중복 제거**: Set 자료구조 사용하여 중복 링크 제거

## 파일 간 의존성

### 수정 시 함께 확인해야 할 파일
- `scraper_improved.py` 수정 시 → `unified_bidding.py` 데이터 형식 확인
- `auto_bidding.py` 수정 시 → `poison_integrated_bidding.py` 호출 부분 확인
- `poison_integrated_bidding.py` 수정 시 → `poison_bidder_wrapper_v2.py` 파라미터 확인
- `unified_bidding.py` 수정 시 → 전체 데이터 흐름 테스트 필수
- `abcmart_link_extractor.py` 수정 시 → `poison_bidder_wrapper_v2.py` 링크 추출 로직 동기화

## 테스트 및 디버깅 규칙

### 코드 수정 후 필수 테스트
1. **단위 테스트**: `python test_*.py` 실행
2. **통합 테스트**: `python test_integration.py` 실행
3. **실제 데이터 테스트**: 작은 샘플로 전체 플로우 테스트

### 디버깅 시 필수 로깅
- **함수 진입 시**:
  ```python
  logger.info(f"함수명 시작 - 파라미터: {param_name}={param_value}")
  logger.debug(f"파라미터 타입: {type(param_name)}")
  ```
- **오류 발생 시**:
  ```python
  logger.error(f"오류 발생: {e}")
  logger.error(f"파라미터 상태: items={items}, type={type(items)}")
  logger.error(traceback.format_exc())
  ```

### 일반적인 오류 체크리스트
- [ ] items가 list인지 확인
- [ ] items가 비어있지 않은지 확인
- [ ] 각 item이 dict인지 확인
- [ ] 필수 필드(code, brand, size, price)가 있는지 확인
- [ ] None 값 처리
- [ ] 빈 문자열 처리

## 텔레그램 봇 상태 추적 규칙 ⚠️ CRITICAL

### 상태 코드 정의
- **필수 사용 상태 코드**:
  ```python
  STAGE_INITIALIZING = "INITIALIZING"        # 초기화
  STAGE_LOGIN_CHECK = "LOGIN_CHECK"          # 로그인 확인
  STAGE_SEARCHING = "SEARCHING"              # 키워드 검색
  STAGE_LINK_EXTRACTING = "LINK_EXTRACTING"  # 링크 추출
  STAGE_SCRAPING = "SCRAPING"                # 상품 정보 스크래핑
  STAGE_PRICE_CALCULATING = "PRICE_CALCULATING"  # 가격 계산
  STAGE_BIDDING = "BIDDING"                  # 입찰 진행
  STAGE_COMPLETED = "COMPLETED"              # 완료
  STAGE_ERROR = "ERROR"                      # 오류
  ```

### 콜백 인터페이스
- **필수 파라미터 형식**:
  ```python
  def status_callback(stage: str, progress: int, message: str, details: dict = None):
      """
      stage: 위의 상태 코드 중 하나
      progress: 0-100 사이의 정수 (전체 진행률)
      message: 사용자에게 표시할 메시지
      details: 추가 정보 (선택사항)
          - current_item: 현재 처리 중인 항목
          - total_items: 전체 항목 수
          - error: 오류 정보 (ERROR 상태일 때)
      """
  ```

### 콜백 구현 규칙
- **auto_bidding.py의 run_auto_pipeline 수정**:
  ```python
  def run_auto_pipeline(self, site: str, keywords: List[str], 
                       strategy: str, status_callback=None):
      if status_callback:
          status_callback(STAGE_INITIALIZING, 0, "자동화 파이프라인 시작")
  ```

- **각 단계별 콜백 호출 필수**:
  ```python
  # 링크 추출 시작
  if status_callback:
      status_callback(STAGE_LINK_EXTRACTING, 10, 
                     f"'{keyword}' 검색 중...", 
                     {"current_keyword": keyword})
  
  # 스크래핑 진행
  if status_callback:
      status_callback(STAGE_SCRAPING, 40,
                     f"상품 정보 수집 중... ({i+1}/{total})",
                     {"current_item": i+1, "total_items": total})
  ```

### 진행률 계산 규칙
- **단계별 가중치**:
  - 초기화: 0-5%
  - 로그인 확인: 5-10%
  - 링크 추출: 10-30%
  - 스크래핑: 30-70%
  - 가격 계산: 70-80%
  - 입찰: 80-100%

- **세부 진행률 계산**:
  ```python
  # 스크래핑 단계 예시 (30-70% 구간)
  base_progress = 30
  stage_weight = 40  # 70 - 30
  item_progress = (current_item / total_items) * stage_weight
  total_progress = int(base_progress + item_progress)
  ```

### 텔레그램 메시지 형식
- **상태별 이모지 매핑**:
  ```python
  STAGE_EMOJIS = {
      STAGE_INITIALIZING: "🚀",
      STAGE_LOGIN_CHECK: "🔐",
      STAGE_SEARCHING: "🔍",
      STAGE_LINK_EXTRACTING: "🔗",
      STAGE_SCRAPING: "📦",
      STAGE_PRICE_CALCULATING: "💰",
      STAGE_BIDDING: "🎯",
      STAGE_COMPLETED: "✅",
      STAGE_ERROR: "❌"
  }
  ```

- **프로그레스 바 형식**:
  ```python
  def create_progress_bar(progress: int) -> str:
      filled = int(progress / 10)
      return "█" * filled + "░" * (10 - filled)
  ```

### 오류 처리 및 상태 보고
- **오류 발생 시 콜백**:
  ```python
  except Exception as e:
      if status_callback:
          status_callback(STAGE_ERROR, progress,
                         f"오류 발생: {str(e)}",
                         {"error": str(e), "traceback": traceback.format_exc()})
      raise
  ```

### 텔레그램 봇 수정 규칙
- **_run_auto_bidding 메서드 수정**:
  - 시간 기반 시뮬레이션 제거
  - 실제 콜백 처리 함수 구현
  - asyncio와 threading 간 통신 처리

- **콜백 처리 예시**:
  ```python
  async def handle_status_callback(self, stage, progress, message, details):
      # 상태 정보 업데이트
      self.current_task['stage'] = stage
      self.current_task['progress'] = progress
      
      # 메시지 생성
      emoji = STAGE_EMOJIS.get(stage, "⚙️")
      progress_bar = create_progress_bar(progress)
      
      # 텔레그램 메시지 전송
      await self.send_status_message(
          f"{emoji} **진행 상황**\n\n"
          f"[{progress_bar}] {progress}%\n\n"
          f"🔄 현재 단계: {stage}\n"
          f"📝 {message}"
      )
  ```

## 금지 사항

### 절대 하지 말아야 할 것들
- **금지**: 타입 검증 없이 파라미터 사용
- **금지**: 빈 데이터 체크 없이 처리 진행
- **금지**: 오류 발생 시 traceback 없이 로깅
- **금지**: unified_items에 bool 값 전달
- **금지**: 테스트 없이 프로덕션 배포
- **금지**: status_callback 없이 시간 기반 진행률 표시
- **금지**: 콜백 호출 시 상태 코드 하드코딩 (정의된 상수 사용)