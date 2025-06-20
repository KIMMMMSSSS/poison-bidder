# Development Guidelines

## 프로젝트 개요
- **목적**: 무신사/ABC마트 상품 스크래핑 → 포이즌 플랫폼 자동 입찰 시스템
- **기술 스택**: Python 3.11+, Selenium, undetected_chromedriver, multiprocessing
- **핵심 모듈**: 스크래퍼(musinsa/abcmart) → 통합 입찰(poison_integrated_bidding) → 포이즌 API
- **주요 데이터 흐름**: 스크래퍼 → JSON 파일 → auto_bidding/unified_bidding → poison_integrated_bidding → poison_bidder_wrapper_v2
- **프로젝트 루트**: `C:\poison_final`
- **웹사이트 루트**: `http://localhost` (C:\poison_final을 가리킴)

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

## 웹 스크래핑 팝업 처리 규칙 ⚠️ CRITICAL

### 무신사 팝업 처리
- **필수**: 페이지 로드 후 팝업 체크 및 제거
- **구현 위치**: `musinsa_scraper_improved.py`의 `close_musinsa_popup` 함수
- **팝업 처리 순서**:
  1. JavaScript로 즉시 팝업 감지/제거 시도
  2. CSS 셀렉터로 다양한 팝업 유형 확인
  3. ESC 키로 팝업 닫기 (마지막 수단)
- **특수 팝업 처리**:
  - **무진장 팝업**: `[data-section-name="mujinjang_index_popup"]`
    - "오늘 그만 보기" 버튼 클릭 우선
    - 버튼 못 찾으면 팝업 전체 제거
- **팝업 셀렉터 목록**:
  ```python
  popup_selectors = [
      # 무진장 팝업 - 우선순위 높음
      "button[data-button-name='오늘 그만 보기']",
      "[data-button-id='dismisstoday']",
      
      # 모달 닫기 버튼들
      "button[aria-label='Close']",
      "button[aria-label='닫기']",
      "button.close-button",
      "button.modal-close",
      "button.popup-close",
      ".close-btn",
      ".btn-close",
      "[data-dismiss='modal']",
      
      # 쿠폰/이벤트 팝업
      ".coupon-popup .close",
      ".event-popup .close",
      ".promotion-popup .close",
      
      # 무신사 특정 팝업
      ".layer-popup .btn-close",
      ".popup-container .close",
      "[data-mds='IconButton'][aria-label*='close']"
  ]
  ```
- **JavaScript 우선 처리**:
  ```python
  # JavaScript로 팝업 즉시 제거
  driver.execute_script("""
      // 모든 모달 찾기
      var modals = document.querySelectorAll('.modal, .popup, .layer-popup');
      modals.forEach(function(modal) {
          if (modal.style.display !== 'none') {
              modal.style.display = 'none';
              modal.remove();
          }
      });
      
      // 모달 백드롭 제거
      var backdrops = document.querySelectorAll('.modal-backdrop, .overlay');
      backdrops.forEach(function(backdrop) {
          backdrop.remove();
      });
  """)
  ```

### 팝업 처리 모범 사례
- **재시도 로직**: 팝업이 동적으로 나타날 수 있으므로 재시도 필요
- **워커별 로깅**: `[Worker {worker_id}] 팝업 처리 성공/실패` 형식
- **성능 최적화**: 팝업 체크는 페이지 로드 직후 1회만 수행
- **예외 처리**: 팝업 처리 실패가 전체 프로세스를 중단시키지 않도록 함

## 로그인 관리 규칙 ⚠️ CRITICAL

### 로그인 정보 관리
- **금지**: 로그인 정보 하드코딩
- **필수**: 환경변수 또는 config 파일 사용
- **예시**:
  ```python
  # .env 파일
  MUSINSA_ID=your_id
  MUSINSA_PASSWORD=your_password
  POISON_PHONE=your_phone
  POISON_PASSWORD=your_password
  
  # 코드에서 사용
  import os
  from dotenv import load_dotenv
  load_dotenv()
  
  musinsa_id = os.getenv('MUSINSA_ID')
  musinsa_password = os.getenv('MUSINSA_PASSWORD')
  ```

### 무신사 자동 로그인 구현
- **필수 처리 필드**:
  - `cipherKey`: 암호화 키
  - `csrfToken`: CSRF 토큰
  - `encryptMemberId`: 암호화된 ID
  - `encryptPassword`: 암호화된 비밀번호
- **구현 예시**:
  ```python
  # 폼 데이터 추출
  cipher_key = driver.find_element(By.ID, "cipherKey").get_attribute("value")
  csrf_token = driver.find_element(By.ID, "csrfToken").get_attribute("value")
  
  # JavaScript로 암호화 처리
  driver.execute_script("""
      // 무신사 암호화 함수 호출
      document.getElementById('encryptMemberId').value = encrypt(arguments[0]);
      document.getElementById('encryptPassword').value = encrypt(arguments[1]);
  """, username, password)
  
  # 자동 로그인 체크
  auto_login_checkbox = driver.find_element(By.ID, "login-v2-member__util__login-auto")
  if not auto_login_checkbox.is_selected():
      auto_login_checkbox.click()
  ```

### 쿠키 관리
- **저장 경로**: `cookies/{site}_cookies.pkl`
- **쿠키 저장**:
  ```python
  cookies = driver.get_cookies()
  with open('cookies/musinsa_cookies.pkl', 'wb') as f:
      pickle.dump(cookies, f)
  ```
- **쿠키 로드**:
  ```python
  if os.path.exists('cookies/musinsa_cookies.pkl'):
      with open('cookies/musinsa_cookies.pkl', 'rb') as f:
          cookies = pickle.load(f)
      for cookie in cookies:
          driver.add_cookie(cookie)
  ```

### LoginManager 통합
- **필수**: `login_manager.py`의 LoginManager 클래스 활용
- **사용 예시**:
  ```python
  from login_manager import LoginManager
  
  login_mgr = LoginManager("musinsa")
  if login_mgr.ensure_login():
      # 로그인 성공, 작업 진행
      driver = login_mgr.driver
  else:
      # 로그인 실패 처리
      raise Exception("로그인 실패")
  ```

### 멀티프로세싱 로그인 상태 공유
- **필수**: 메인 프로세스에서 로그인 후 쿠키 공유
- **구현 예시**:
  ```python
  # 메인 프로세스
  login_mgr = LoginManager("musinsa")
  login_mgr.ensure_login()
  cookies = login_mgr.driver.get_cookies()
  
  # 워커 프로세스
  def worker_process(cookies):
      driver = setup_driver()
      driver.get("https://www.musinsa.com")
      for cookie in cookies:
          driver.add_cookie(cookie)
      driver.refresh()
  ```

### 보안 규칙
- **금지**: 로그에 비밀번호 출력
- **필수**: 비밀번호 마스킹
  ```python
  logger.info(f"로그인 시도: {username}")  # 비밀번호는 로그하지 않음
  ```
- **금지**: Git에 로그인 정보 커밋
- **필수**: `.gitignore`에 추가
  ```
  .env
  cookies/
  *_cookies.pkl
  config/credentials.json
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
- **undetected_chromedriver 사용 필수**:
  ```python
  import undetected_chromedriver as uc
  
  options = uc.ChromeOptions()
  options.add_argument('--no-sandbox')
  options.add_argument('--disable-dev-shm-usage')
  
  # 워커별 헤드리스 설정
  if worker_id > 1:  # 첫 번째 워커만 GUI 표시
      options.add_argument('--headless')
  
  driver = uc.Chrome(options=options, version_main=None)
  ```
- **포트 충돌 방지**: `port = 9222 + worker_id`
- **워커별 임시 디렉토리**: `f'chrome_worker_{worker_id}_{os.getpid()}'`
- **워커별 chromedriver 복사본 생성**:
  ```python
  # undetected_chromedriver 경로에서 복사
  driver_dir = os.path.join(tempfile.gettempdir(), f'chromedriver_worker_{worker_id}_{os.getpid()}')
  os.makedirs(driver_dir, exist_ok=True)
  driver_path = os.path.join(driver_dir, 'chromedriver.exe')
  shutil.copy2(existing_driver, driver_path)
  ```
- **종료 시 정리 필수**:
  ```python
  finally:
      if driver:
          driver.quit()
      # 임시 디렉토리 정리
      if os.path.exists(user_data_dir):
          shutil.rmtree(user_data_dir, ignore_errors=True)
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

### Selenium WebDriverWait 사용 규칙
- **명시적 대기 우선 사용**:
  ```python
  from selenium.webdriver.support.ui import WebDriverWait
  from selenium.webdriver.support import expected_conditions as EC
  
  # 요소가 나타날 때까지 대기
  element = WebDriverWait(driver, 10).until(
      EC.presence_of_element_located((By.CSS_SELECTOR, "selector"))
  )
  
  # 클릭 가능할 때까지 대기
  button = WebDriverWait(driver, 10).until(
      EC.element_to_be_clickable((By.XPATH, "//button[@id='submit']"))
  )
  ```

- **JavaScript executor 활용**:
  ```python
  # 요소가 가려져 있을 때
  driver.execute_script("arguments[0].click();", element)
  
  # 스크롤
  driver.execute_script("arguments[0].scrollIntoView(true);", element)
  
  # 값 직접 설정
  driver.execute_script("arguments[0].value = arguments[1];", input_element, value)
  ```

- **StaleElementReferenceException 처리**:
  ```python
  for retry in range(3):
      try:
          element.click()
          break
      except StaleElementReferenceException:
          element = driver.find_element(By.ID, "element_id")
          time.sleep(0.5)
  ```

## 파일 간 의존성

### 수정 시 함께 확인해야 할 파일
- `scraper_improved.py` 수정 시 → `unified_bidding.py` 데이터 형식 확인
- `auto_bidding.py` 수정 시 → `poison_integrated_bidding.py` 호출 부분 확인
- `poison_integrated_bidding.py` 수정 시 → `poison_bidder_wrapper_v2.py` 파라미터 확인
- `unified_bidding.py` 수정 시 → 전체 데이터 흐름 테스트 필수
- `abcmart_link_extractor.py` 수정 시 → `poison_bidder_wrapper_v2.py` 링크 추출 로직 동기화
- `poison_bidder_wrapper_v2.py` 수정 시 → 다음 사항 확인:
  - 포이즌 로그인 정보 변경 시 환경변수 업데이트
  - 무신사 로그인 기능 추가 시 `LoginManager` 클래스 사용
  - 멀티프로세싱 워커 수정 시 쿠키 공유 로직 확인

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

## 데이터베이스 규칙

### MySQL 접속 정보
- **필수**: 환경변수로 관리
  ```python
  DB_HOST = os.getenv('DB_HOST', 'localhost')
  DB_USER = os.getenv('DB_USER', 'root')
  DB_PASSWORD = os.getenv('DB_PASSWORD', '')
  DB_NAME = os.getenv('DB_NAME', '')
  ```

### MySQL 명령 실행
- **필수 형식**:
  ```bash
  mysql -u root -p -e "SQL명령어" 데이터베이스명
  ```
- **중요**: SQL 명령어는 반드시 따옴표로 감싸야 함
  ```python
  command = ['mysql', '-u', 'root', '-e', '"SHOW DATABASES;"']
  ```

### 데이터베이스 경로
- **SQLite**: `db/bidding_history.db`
- **로그 DB**: `db/logs.db`

## 환경변수 관리

### .env 파일 구조
```env
# 텔레그램 봇
TELEGRAM_BOT_TOKEN=your_token

# 무신사 로그인
MUSINSA_ID=your_id
MUSINSA_PASSWORD=your_password

# 포이즌 로그인
POISON_PHONE=your_phone
POISON_PASSWORD=your_password

# 데이터베이스
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=your_database

# 로그 설정
LOG_LEVEL=INFO
```

### 환경변수 사용
- **필수**: python-dotenv 사용
  ```python
  from dotenv import load_dotenv
  load_dotenv()
  
  value = os.getenv('KEY', 'default_value')
  ```

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

## Shrimp Task Manager 사용 규칙 ⚠️ CRITICAL

### 작업 계획 및 실행 모드
- **TaskPlanner 모드**: 새 기능 개발이나 버그 수정 시 작업 계획 수립
  ```python
  # plan_task 사용 예시
  { "tool": "shrimp-task:plan_task", 
    "parameters": { 
      "description": "무신사 팝업 처리 기능 개선",
      "requirements": "다양한 팝업 유형 대응, JavaScript 활용"
    }
  }
  ```

- **TaskExecutor 모드**: 계획된 작업 실행
  ```python
  # execute_task 사용 예시
  { "tool": "shrimp-task:execute_task", 
    "parameters": { 
      "taskId": "TASK-2025-0001" 
    }
  }
  ```

### 작업 관리 워크플로우
1. **프로젝트 초기화** (선택사항):
   ```python
   { "tool": "shrimp-task:init_project_rules" }
   ```

2. **작업 계획 수립**:
   - 작업 분석: `analyze_task`
   - 사고 프로세스: `process_thought`  
   - 계획 반영: `reflect_task`
   - 작업 분할: `split_tasks` (clearAllTasks 모드 사용)

3. **작업 실행**:
   - 작업 목록 확인: `list_tasks`
   - 작업 실행: `execute_task`
   - 작업 검증: `verify_task` (80점 이상 시 자동 완료)

### split_tasks 모드 선택
- **clearAllTasks** (기본값): 새로운 계획 수립 시
- **append**: 기존 작업에 추가
- **overwrite**: 미완료 작업만 교체
- **selective**: 특정 작업만 업데이트

### 작업 단위 규칙
- **크기**: 1-2일 내 완료 가능한 단위로 분할
- **개수**: 최대 10개 이하로 제한
- **의존성**: 작업 간 dependencies 명시
- **검증 기준**: 각 작업에 verificationCriteria 포함

### 연속 실행 모드
- **사용 시기**: 여러 작업을 자동으로 처리할 때
- **활성화**: 사용자에게 "continuous mode" 사용 여부 확인
- **진행**: execute_task → verify_task → 다음 작업 자동 진행

### 파일 작업 시 Shrimp 통합
1. **작업 전**: 관련 작업이 있는지 `query_task`로 확인
2. **파일 수정**: `text-editor` 또는 `filesystem` 도구 사용
3. **작업 업데이트**: `update_task`로 진행 상황 기록
4. **완료 후**: `verify_task`로 검증

### Shrimp 데이터 관리
- **작업 파일 위치**: `shrimp_data/tasks.json`
- **삭제 금지**: 작업은 함부로 삭제하지 않고 동의 필요
- **초기화 금지**: clearAllTasks는 사용자 동의 필수

## 금지 사항

### 절대 하지 말아야 할 것들
- **금지**: 타입 검증 없이 파라미터 사용
- **금지**: 빈 데이터 체크 없이 처리 진행
- **금지**: 오류 발생 시 traceback 없이 로깅
- **금지**: unified_items에 bool 값 전달
- **금지**: 테스트 없이 프로덕션 배포
- **금지**: status_callback 없이 시간 기반 진행률 표시
- **금지**: 콜백 호출 시 상태 코드 하드코딩 (정의된 상수 사용)
- **금지**: 로그인 정보 하드코딩 또는 Git 커밋
- **금지**: 쿠키 파일을 Git에 커밋
- **금지**: Shrimp 작업을 사용자 동의 없이 삭제
- **금지**: clearAllTasks를 사용자 동의 없이 실행
- **금지**: analyze_task 도구를 프로젝트 규칙 작성 시 호출
- **금지**: 작업 진행 전 동의 없이 자동 실행

## AI Agent 작업 지침

### 작업 시작 전 확인 사항
1. **현재 작업 확인**: `shrimp-task:list_tasks`로 진행 중인 작업 확인
2. **관련 파일 확인**: 수정할 파일과 연관된 파일들 미리 확인
3. **테스트 파일 확인**: `test/` 디렉토리에 관련 테스트 존재 여부

### 작업 진행 순서
1. **계획 수립**: TaskPlanner 모드로 작업 계획
2. **사용자 동의**: 작업 진행 전 반드시 동의 받기
3. **작업 실행**: TaskExecutor 모드로 순차 실행
4. **검증**: 각 작업 완료 후 verify_task로 검증

### 파일 수정 시 주의사항
- **섹션별 수정**: 큰 파일은 3-5개 섹션으로 나누어 수정
- **라인 번호 재확인**: 각 edit 전에 반드시 소스 위치 재확인
- **dry-run 우선**: edit_file_lines 사용 시 항상 dryRun: true로 먼저 테스트

### 작업 완료 후
- **Git 커밋**: 파일 수정 후 즉시 add와 commit
- **테스트 실행**: 관련 테스트 파일 실행하여 검증
- **문서 업데이트**: 필요시 README.md나 가이드 문서 업데이트

## Git 작업 규칙

### 브랜치 전략
- **master**: 안정된 프로덕션 코드
- **test**: 테스트 및 검증용 브랜치
- **feature/***: 새 기능 개발용 브랜치

### 커밋 규칙
- **커밋 메시지 형식**:
  ```
  type: 간단한 설명
  
  - 상세 변경사항 1
  - 상세 변경사항 2
  ```
- **타입 종류**:
  - `feat`: 새로운 기능
  - `fix`: 버그 수정
  - `docs`: 문서 수정
  - `style`: 코드 포맷팅
  - `refactor`: 리팩토링
  - `test`: 테스트 코드
  - `chore`: 빌드, 패키지 매니저 등

### 파일 작업 후 Git 처리
- **필수**: 파일 생성/수정 후 즉시 git add와 commit
  ```bash
  git add <파일명>
  git commit -m "type: 설명"
  ```
- **필수**: 작업 완료 후 pull request
- **필수**: test 브랜치에서 충분히 검증 후 master 병합