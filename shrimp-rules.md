# Development Guidelines

## 프로젝트 개요
- **목적**: 무신사/ABC마트 상품 스크래핑 → 포이즌 플랫폼 자동 입찰 시스템
- **기술 스택**: Python 3.11+, Selenium, undetected_chromedriver, multiprocessing
- **핵심 모듈**: 스크래퍼(musinsa/abcmart) → 통합 입찰(poison_integrated_bidding) → 포이즌 API

## 필수 준수 규칙

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
- **필수 필드**: brand, product_code, color, size, price
- **형식 예시**:
  ```python
  unified_item = {
      'brand': 'NIKE',
      'product_code': 'DZ2628-001',
      'color': '',  # 빈 문자열 허용
      'size': '270',
      'price': 139000
  }
  ```

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

## 파일 간 의존성

### 수정 시 함께 확인해야 할 파일
- `scraper_