# unified_items 파라미터 오류 분석 보고서

## 오류 발생 경로

1. **호출 체인**:
   ```
   실행 스크립트 → auto_bidding.py 또는 unified_bidding.py
   → AutoBiddingAdapter.run_with_poison(items)
   → poison_integrated_bidding.py (188번째 줄)
   → poison_bidder_wrapper_v2.py.run_bidding(unified_items=items)
   ```

2. **오류 로그 분석**:
   ```
   [INFO] 입력 파라미터 - bid_data_file: False, bid_data_list: False, unified_items: True
   [ERROR] bid_data_file, bid_data_list, unified_items 중 하나는 제공되어야 합니다
   ```

## 문제 원인

`unified_items` 파라미터에 리스트가 아닌 `True` 불린 값이 전달됨

## 가능한 시나리오

1. **시나리오 1**: 조건문 오류
   ```python
   # 잘못된 코드 예시
   if items:  # items가 있으면
       adapter.run_with_poison(True)  # 실수로 True 전달
   ```

2. **시나리오 2**: 변수명 혼동
   ```python
   # 잘못된 코드 예시
   items = True  # 어딘가에서 items가 True로 덮어씌워짐
   adapter.run_with_poison(items)
   ```

3. **시나리오 3**: 빈 리스트 처리 오류
   ```python
   # 잘못된 코드 예시
   items = get_items() or True  # get_items()가 빈 리스트 반환 시 True가 됨
   ```

## 재현 가능한 테스트 케이스

```python
# 오류 재현
from poison_integrated_bidding import AutoBiddingAdapter
adapter = AutoBiddingAdapter()
result = adapter.run_with_poison(True)  # TypeError 발생!

# 올바른 사용법
items = [
    {
        'code': 'ABC123',
        'brand': 'NIKE',
        'size': '270',
        'price': 100000,
        'color': 'BLACK'
    }
]
result = adapter.run_with_poison(items)  # 정상 작동
```

## 결론

- 오류는 `run_with_poison` 메서드 호출 시 리스트 대신 `True` 값이 전달되어 발생
- 호출하는 코드에서 items 변수가 올바르게 설정되지 않았을 가능성이 높음
- 파라미터 타입 검증이 없어서 오류가 늦게 발견됨
