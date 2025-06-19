-- K-Fashion 자동 입찰 시스템 데이터베이스 스키마
-- 단순한 구조로 입찰 이력만 저장

-- 입찰 이력 테이블
CREATE TABLE IF NOT EXISTS bid_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    strategy TEXT NOT NULL,              -- 사용된 가격 전략 (basic, standard, premium 등)
    site TEXT NOT NULL,                  -- 사이트 (musinsa, abcmart)
    product_code TEXT NOT NULL,          -- 상품 코드
    product_name TEXT,                   -- 상품명 (선택사항)
    size TEXT,                           -- 사이즈
    color TEXT,                          -- 색상
    original_price INTEGER NOT NULL,     -- 원가
    final_price INTEGER NOT NULL,        -- 최종 입찰가 (할인 적용 후)
    discount_details TEXT,               -- 할인 상세 (JSON 형식)
    status TEXT NOT NULL,                -- 상태 (success, failed, pending)
    error_message TEXT,                  -- 오류 메시지 (실패 시)
    execution_time REAL,                 -- 실행 시간 (초)
    job_id TEXT                          -- 작업 그룹 ID (같은 배치 작업 구분용)
);

-- 인덱스 생성 (검색 성능 향상)
CREATE INDEX IF NOT EXISTS idx_timestamp ON bid_history(timestamp);
CREATE INDEX IF NOT EXISTS idx_product_code ON bid_history(product_code);
CREATE INDEX IF NOT EXISTS idx_status ON bid_history(status);
CREATE INDEX IF NOT EXISTS idx_job_id ON bid_history(job_id);
CREATE INDEX IF NOT EXISTS idx_site ON bid_history(site);

-- 가격 전략 설정 이력 (선택사항)
CREATE TABLE IF NOT EXISTS pricing_strategies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,           -- 전략 이름
    config TEXT NOT NULL,                -- JSON 형식의 설정
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1          -- 활성화 여부
);

-- 스케줄 실행 이력 (선택사항)
CREATE TABLE IF NOT EXISTS schedule_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scheduled_time DATETIME NOT NULL,    -- 예정된 실행 시간
    actual_time DATETIME,                -- 실제 실행 시간
    strategy TEXT NOT NULL,              -- 사용된 전략
    status TEXT NOT NULL,                -- 상태 (completed, failed, skipped)
    total_items INTEGER DEFAULT 0,       -- 총 아이템 수
    success_count INTEGER DEFAULT 0,     -- 성공 개수
    fail_count INTEGER DEFAULT 0,        -- 실패 개수
    duration REAL,                       -- 전체 소요 시간 (초)
    notes TEXT                           -- 비고
);

-- 뷰 생성: 일별 통계
CREATE VIEW IF NOT EXISTS daily_stats AS
SELECT 
    DATE(timestamp) as date,
    site,
    strategy,
    COUNT(*) as total_bids,
    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_count,
    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as fail_count,
    AVG(original_price) as avg_original_price,
    AVG(final_price) as avg_final_price,
    AVG(original_price - final_price) as avg_discount,
    SUM(original_price - final_price) as total_saved
FROM bid_history
GROUP BY DATE(timestamp), site, strategy;

-- 뷰 생성: 최근 입찰 요약
CREATE VIEW IF NOT EXISTS recent_bids AS
SELECT 
    timestamp,
    site,
    product_code,
    product_name,
    size,
    original_price,
    final_price,
    ROUND((original_price - final_price) * 100.0 / original_price, 2) as discount_rate,
    status
FROM bid_history
ORDER BY timestamp DESC
LIMIT 100;
