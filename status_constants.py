#!/usr/bin/env python3
"""
텔레그램 봇 상태 추적을 위한 상수 정의 모듈
모든 모듈에서 공통으로 사용할 상태 코드, 이모지, 가중치 등을 정의
"""

# 상태 코드 정의
STAGE_INITIALIZING = "INITIALIZING"        # 초기화
STAGE_LOGIN_CHECK = "LOGIN_CHECK"          # 로그인 확인
STAGE_SEARCHING = "SEARCHING"              # 키워드 검색
STAGE_LINK_EXTRACTING = "LINK_EXTRACTING"  # 링크 추출
STAGE_SCRAPING = "SCRAPING"                # 상품 정보 스크래핑
STAGE_PRICE_CALCULATING = "PRICE_CALCULATING"  # 가격 계산
STAGE_BIDDING = "BIDDING"                  # 입찰 진행
STAGE_COMPLETED = "COMPLETED"              # 완료
STAGE_ERROR = "ERROR"                      # 오류

# 상태별 이모지 매핑
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

# 상태별 진행률 가중치 (백분율)
STAGE_WEIGHTS = {
    STAGE_INITIALIZING: 5,       # 0-5%
    STAGE_LOGIN_CHECK: 5,        # 5-10%
    STAGE_LINK_EXTRACTING: 20,   # 10-30%
    STAGE_SCRAPING: 40,          # 30-70%
    STAGE_PRICE_CALCULATING: 10, # 70-80%
    STAGE_BIDDING: 20           # 80-100%
}

# 진행률 범위 계산을 위한 누적 가중치
STAGE_PROGRESS_RANGES = {
    STAGE_INITIALIZING: (0, 5),
    STAGE_LOGIN_CHECK: (5, 10),
    STAGE_LINK_EXTRACTING: (10, 30),
    STAGE_SCRAPING: (30, 70),
    STAGE_PRICE_CALCULATING: (70, 80),
    STAGE_BIDDING: (80, 100)
}

# 상태별 기본 메시지
STAGE_MESSAGES = {
    STAGE_INITIALIZING: "자동화 파이프라인을 시작합니다...",
    STAGE_LOGIN_CHECK: "로그인 상태를 확인하고 있습니다...",
    STAGE_SEARCHING: "키워드를 검색하고 있습니다...",
    STAGE_LINK_EXTRACTING: "상품 링크를 수집하고 있습니다...",
    STAGE_SCRAPING: "상품 정보를 스크래핑하고 있습니다...",
    STAGE_PRICE_CALCULATING: "최적 가격을 계산하고 있습니다...",
    STAGE_BIDDING: "입찰을 진행하고 있습니다...",
    STAGE_COMPLETED: "모든 작업이 완료되었습니다!",
    STAGE_ERROR: "오류가 발생했습니다."
}


def create_progress_bar(progress: int, width: int = 10) -> str:
    """
    진행률에 따른 프로그레스 바 생성
    
    Args:
        progress: 0-100 사이의 진행률
        width: 프로그레스 바 너비 (기본값: 10)
        
    Returns:
        프로그레스 바 문자열 (예: "███░░░░░░░")
    """
    if progress < 0:
        progress = 0
    elif progress > 100:
        progress = 100
    
    filled = int((progress / 100) * width)
    return "█" * filled + "░" * (width - filled)


def calculate_stage_progress(stage: str, current_item: int = 0, total_items: int = 0) -> int:
    """
    현재 단계와 세부 진행 상황을 바탕으로 전체 진행률 계산
    
    Args:
        stage: 현재 단계
        current_item: 현재 처리 중인 항목 번호 (선택사항)
        total_items: 전체 항목 수 (선택사항)
        
    Returns:
        0-100 사이의 전체 진행률
    """
    if stage not in STAGE_PROGRESS_RANGES:
        return 0
    
    start, end = STAGE_PROGRESS_RANGES[stage]
    
    # 세부 진행 상황이 없는 경우 단계의 시작 진행률 반환
    if total_items == 0 or current_item == 0:
        return start
    
    # 세부 진행률 계산
    stage_range = end - start
    item_progress = (current_item / total_items) * stage_range
    
    return int(start + item_progress)


def escape_markdown(text: str) -> str:
    """
    텔레그램 마크다운 특수 문자 이스케이프
    
    Args:
        text: 이스케이프할 텍스트
        
    Returns:
        이스케이프된 텍스트
    """
    # 텔레그램 마크다운에서 이스케이프가 필요한 문자들
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    
    if not text:
        return text
        
    text = str(text)
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    
    return text


def format_status_message(stage: str, progress: int, message: str = None, details: dict = None) -> str:
    """
    텔레그램 메시지 형식으로 상태 정보 포맷팅
    
    Args:
        stage: 현재 단계
        progress: 진행률 (0-100)
        message: 사용자 정의 메시지 (선택사항)
        details: 추가 정보 딕셔너리 (선택사항)
        
    Returns:
        포맷팅된 메시지 문자열
    """
    emoji = STAGE_EMOJIS.get(stage, "⚙️")
    progress_bar = create_progress_bar(progress)
    
    # 기본 메시지
    status_msg = f"{emoji} **진행 상황**\n\n"
    status_msg += f"[{progress_bar}] {progress}%\n\n"
    status_msg += f"🔄 현재 단계: {stage}\n"
    
    # 사용자 정의 메시지 또는 기본 메시지
    if message:
        status_msg += f"📝 {escape_markdown(message)}"
    else:
        default_msg = STAGE_MESSAGES.get(stage, "작업 진행 중...")
        status_msg += f"📝 {escape_markdown(default_msg)}"
    
    # 추가 정보
    if details:
        if 'current_item' in details and 'total_items' in details:
            status_msg += f"\n📊 진행: {details['current_item']}/{details['total_items']}"
        if 'current_keyword' in details:
            status_msg += f"\n🔍 키워드: {escape_markdown(str(details['current_keyword']))}"
        if 'error' in details:
            status_msg += f"\n❗ 오류: {escape_markdown(str(details['error']))}"
    
    return status_msg


# 텔레그램 API 제한 관련 상수
TELEGRAM_MESSAGE_RATE_LIMIT = 30  # 초당 최대 메시지 수
TELEGRAM_MESSAGE_MIN_INTERVAL = 1.0 / TELEGRAM_MESSAGE_RATE_LIMIT  # 최소 메시지 간격 (초)

# 진행률 업데이트 임계값
PROGRESS_UPDATE_THRESHOLD = 5  # 5% 이상 변경 시에만 업데이트
