# 스케줄러 사용 가이드

## 1. 스케줄러 실행
```bash
python scheduler.py
```

## 2. 스케줄 설정
`config/schedules.json` 파일에서 스케줄을 관리합니다.

### 스케줄 구조
- **id**: 고유 식별자
- **name**: 스케줄 이름
- **enabled**: 활성화 여부 (true/false)
- **trigger**: 실행 시간 설정
  - type: "cron" (현재 지원)
  - hour: 시간 (0-23)
  - minute: 분 (0-59)
  - day_of_week: 요일 (mon, tue, wed, thu, fri, sat, sun)
- **job**: 실행할 작업 설정
  - site: "musinsa" 또는 "abcmart"
  - strategy: 가격 전략 ID
  - mode: "auto" 또는 "manual"

### 예시
```json
{
  "id": "morning_bid",
  "name": "아침 입찰",
  "enabled": true,
  "trigger": {
    "type": "cron",
    "hour": 9,
    "minute": 30
  },
  "job": {
    "site": "musinsa",
    "strategy": "basic",
    "mode": "auto"
  }
}
```

## 3. 스케줄 관리
현재는 설정 파일을 직접 수정하여 관리합니다.
- 스케줄 추가: schedules 배열에 새 항목 추가
- 스케줄 수정: 해당 항목 수정
- 스케줄 비활성화: enabled를 false로 변경
- 스케줄 삭제: 배열에서 항목 제거

## 4. 로그 확인
`logs/scheduler_YYYYMMDD.log` 파일에서 실행 내역을 확인할 수 있습니다.

## 5. 주의사항
- 스케줄러 실행 중 설정 파일을 수정하면 재시작이 필요합니다
- 타임존은 기본적으로 Asia/Seoul로 설정되어 있습니다
- 동시에 실행되는 작업은 1개로 제한됩니다
