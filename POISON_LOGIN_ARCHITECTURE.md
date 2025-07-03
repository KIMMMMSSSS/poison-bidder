# 포이즌 로그인 아키텍처 문서

## 📋 개요

이 문서는 포이즌(POIZON) 자동 입찰 시스템의 로그인 관련 코드 구조를 분석하고, 현재의 문제점과 향후 통합 방안을 제시합니다.

## 🗂️ 현재 로그인 관련 파일들

### 1. **poison_bidder_wrapper_v2.py** (메인 파일)
- **용도**: 멀티워커 자동 입찰 시스템의 핵심 파일
- **특징**:
  - 멀티프로세싱 기반 워커 관리
  - `check_poison_login_status()` 함수로 통합된 로그인 체크
  - 쿠키 저장/로드 메커니즘
  - Worker 1이 로그인 후 쿠키를 공유하는 구조
- **로그인 확인 방식**: 
  - 1차: `id="Item Info"` 검색창
  - 2차: "Seller Dashboard" 텍스트
  - 3차: `id="mobile_number"` 로그인 폼

### 2. **poison_login_manager.py**
- **용도**: 싱글톤 패턴의 포이즌 전용 로그인 매니저
- **특징**:
  - 하나의 브라우저 세션을 유지
  - `undetected_chromedriver` 사용
  - 수동 로그인 유도 방식
- **문제점**:
  - 구식 로그인 체크 방식 ("Log In" 텍스트)
  - `check_poison_login_status()` 미사용

### 3. **login_manager.py** 
- **용도**: 멀티사이트 로그인 지원 (무신사, ABC마트, 포이즌)
- **특징**:
  - 사이트별 설정 관리
  - 쿠키 파일 관리 (`{site}_cookies.pkl`)
  - 환경 변수 기반 계정 정보
- **문제점**:
  - 포이즌 설정이 최신화되지 않음
  - selector 기반 체크가 정확하지 않음

### 4. **poison_direct_login.py**
- **용도**: 단독 실행용 포이즌 로그인 스크립트
- **특징**:
  - Chrome 프로필 사용으로 로그인 유지
  - 자동 로그인 로직 포함
  - 쿠키 저장 기능
- **문제점**:
  - `poison_bidder_wrapper_v2.py`와 중복 코드

### 5. **poison_auto_login.py**
- **용도**: 계정 정보 저장 및 자동 로그인
- **특징**:
  - 프로필별 계정 정보 관리
  - credentials.json에 계정 정보 저장
  - 쿠키 자동 저장/로드

### 6. **poison_login_setup.py**
- **용도**: Chrome 프로필 기반 로그인 유지 설정
- **특징**:
  - Chrome 프로필 디렉토리 사용
  - 일회성 로그인 설정용

### 7. **poison_integrated_bidding.py**
- **용도**: 통합 입찰 시스템
- **특징**:
  - 여러 로그인 방식 시도
  - 복잡한 로그인 로직

## 🔍 현재 문제점

### 1. **코드 중복**
- 로그인 체크 로직이 여러 파일에 분산
- 쿠키 저장/로드 코드 중복
- 동일한 계정 정보가 여러 곳에 하드코딩

### 2. **일관성 부족**
- 파일마다 다른 로그인 체크 방식
  - "Log In" 텍스트 체크
  - selector 기반 체크
  - 검색창 ID 체크
- Chrome 옵션 설정 불일치

### 3. **유지보수 어려움**
- 로그인 로직 변경 시 여러 파일 수정 필요
- 디버깅 시 어떤 파일이 사용되는지 혼란

### 4. **기능 중복**
- 싱글톤 패턴과 멀티워커 패턴 혼재
- 프로필 기반과 쿠키 기반 로그인 혼재

## 🛠️ 통합 방안

### 1단계: 공통 모듈 생성
```python
# poison_login_common.py
class PoisonLoginChecker:
    @staticmethod
    def check_login_status(driver):
        """통합 로그인 체크 함수"""
        return check_poison_login_status(driver)
    
    @staticmethod
    def save_cookies(driver, filepath):
        """쿠키 저장"""
        # 통합된 쿠키 저장 로직
    
    @staticmethod
    def load_cookies(driver, filepath):
        """쿠키 로드"""
        # 통합된 쿠키 로드 로직
```

### 2단계: 로그인 전략 패턴 적용
```python
# poison_login_strategies.py
class LoginStrategy(ABC):
    @abstractmethod
    def login(self, driver, credentials):
        pass

class AutoLoginStrategy(LoginStrategy):
    """자동 로그인 전략"""
    
class ManualLoginStrategy(LoginStrategy):
    """수동 로그인 전략"""
    
class ProfileLoginStrategy(LoginStrategy):
    """Chrome 프로필 기반 로그인"""
```

### 3단계: 통합 로그인 매니저
```python
# poison_login_unified.py
class UnifiedPoisonLoginManager:
    def __init__(self, strategy: LoginStrategy):
        self.strategy = strategy
        self.checker = PoisonLoginChecker()
    
    def ensure_login(self, driver):
        """로그인 보장"""
        if not self.checker.check_login_status(driver):
            return self.strategy.login(driver, self.credentials)
        return True
```

### 4단계: 기존 파일 리팩토링
1. `poison_bidder_wrapper_v2.py`: UnifiedPoisonLoginManager 사용
2. 기타 파일들: Deprecated 표시 및 통합 매니저로 리다이렉트

## 📈 예상 효과

1. **코드 중복 90% 감소**
2. **유지보수성 향상**: 로그인 로직 변경 시 한 곳만 수정
3. **일관성 확보**: 모든 모듈이 동일한 로그인 체크 사용
4. **확장성**: 새로운 로그인 방식 추가 용이
5. **테스트 가능성**: 전략 패턴으로 단위 테스트 용이

## 🗓️ 마이그레이션 로드맵

### Phase 1 (1주)
- [ ] `poison_login_common.py` 생성
- [ ] `check_poison_login_status()` 함수 이동
- [ ] 쿠키 관리 함수 통합

### Phase 2 (1주)
- [ ] 로그인 전략 패턴 구현
- [ ] 기존 로그인 방식을 전략으로 변환

### Phase 3 (2주)
- [ ] `UnifiedPoisonLoginManager` 구현
- [ ] `poison_bidder_wrapper_v2.py` 적용
- [ ] 테스트 및 검증

### Phase 4 (1주)
- [ ] 기존 파일 Deprecated 처리
- [ ] 문서 업데이트
- [ ] 최종 정리

## 📝 권장사항

1. **즉시 적용 가능한 개선**
   - 환경 변수로 계정 정보 관리
   - 로그인 타임아웃 설정 통일
   - 로그 레벨 표준화

2. **중기 개선 (1-2개월)**
   - 위 통합 방안 실행
   - CI/CD 파이프라인에 로그인 테스트 추가

3. **장기 개선 (3-6개월)**
   - OAuth 또는 API 키 기반 인증 검토
   - 로그인 상태 모니터링 대시보드
   - 멀티 계정 관리 시스템

## 🔚 결론

현재 포이즌 로그인 시스템은 여러 파일에 분산되어 있어 유지보수가 어렵습니다. 
제안된 통합 방안을 통해 코드 중복을 제거하고, 일관성 있는 로그인 메커니즘을 구축할 수 있습니다.
단계별 마이그레이션을 통해 리스크를 최소화하면서 시스템을 개선할 수 있을 것입니다.

---
*작성일: 2025년 1월*  
*작성자: Claude AI Assistant*  
*버전: 1.0*
