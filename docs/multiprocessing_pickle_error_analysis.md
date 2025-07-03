# Multiprocessing Pickle 오류 분석 보고서

## 1. 오류 발생 위치
- **파일**: `poison_bidder_wrapper_v2.py`
- **라인**: 318번째 줄
- **오류 메시지**: `Can't pickle <function worker_process at 0x0000018659010220>: import of module 'multiprocess_cookie' failed`

## 2. 오류 발생 코드
```python
# poison_bidder_wrapper_v2.py 318번째 줄
worker = Process(
    target=self.module.worker_process,  # 문제 발생 지점
    args=(i, task_queue, result_queue, status_dict, login_complete, 
          self.min_profit, self.driver_path, stats)
)
```

## 3. 오류 원인 분석

### 3.1 동적 모듈 로딩 구조
```python
# _load_original_module 메서드
spec = importlib.util.spec_from_file_location("multiprocess_cookie", original_file)
self.module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(self.module)
```
- `importlib.util`을 사용하여 `0923_fixed_multiprocess_cookie_v2.py`를 동적으로 로드
- 로드된 모듈은 `self.module`에 저장됨

### 3.2 Pickle 제약사항
Python의 multiprocessing은 프로세스 간 함수 전달 시 pickle을 사용합니다:
1. **pickle 가능 조건**:
   - 함수가 모듈의 최상위 레벨에 정의되어야 함
   - 함수가 `__main__` 또는 import 가능한 모듈에 속해야 함
   
2. **현재 문제**:
   - `self.module.worker_process`는 동적으로 로드된 모듈의 함수
   - pickle은 동적 로드된 모듈(`multiprocess_cookie`)을 재구성할 수 없음
   - 함수 참조가 `self.module` 속성을 통해 이루어져 직렬화 불가

## 4. 기존 코드 분석

### 4.1 정상 작동하는 코드
```python
# log_processor_worker는 모듈 레벨에 정의되어 정상 작동
def log_processor_worker(result_queue, result_list_queue):
    """로그 처리 워커 프로세스 (모듈 레벨 함수)"""
    # ...

# Process 생성 시
log_proc = Process(target=log_processor_worker, args=(result_queue, result_list_queue))
```

### 4.2 문제가 되는 코드
```python
# 동적으로 로드된 모듈의 함수 참조
worker = Process(
    target=self.module.worker_process,  # pickle 불가능
    args=(...)
)
```

## 5. 해결 방안

### 방안 1: worker_process를 모듈 레벨로 이동
- `0923_fixed_multiprocess_cookie_v2.py`의 `worker_process` 함수와 관련 클래스를
- `poison_bidder_wrapper_v2.py`의 모듈 레벨로 복사
- `log_processor_worker`처럼 직접 참조 가능하도록 수정

### 방안 2: 정상적인 import 사용
- 동적 로딩 대신 `from ... import ...` 구문 사용
- 단, 파일명이 숫자로 시작하므로 변경 필요

### 방안 3: 래퍼 함수 생성
- 모듈 레벨에 래퍼 함수를 만들어 동적 로드된 함수 호출

## 6. 권장 해결책
**방안 1**을 권장합니다. 이유:
- 가장 직접적이고 안정적인 해결책
- 기존 `log_processor_worker`와 동일한 패턴
- 코드 유지보수가 용이
- 추가적인 의존성 문제 없음
