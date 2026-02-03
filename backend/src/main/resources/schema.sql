-- PostgreSQL: trades 테이블 (Spring Backend + Kiwoom 에이전트 공용)
CREATE TABLE IF NOT EXISTS trades (
    id BIGSERIAL PRIMARY KEY,
    account_id VARCHAR(32) NOT NULL,
    trade_date TIMESTAMP NOT NULL,
    symbol VARCHAR(32) NOT NULL,
    side VARCHAR(8) NOT NULL,
    qty DECIMAL(20, 8) NOT NULL,
    price DECIMAL(20, 8) NOT NULL,
    fee DECIMAL(20, 8) DEFAULT 0,
    order_id VARCHAR(64),
    exec_id VARCHAR(64),
    strategy_tag VARCHAR(64)
);

CREATE INDEX IF NOT EXISTS idx_trades_account_date ON trades(account_id, trade_date);

-- 커밋 기록 (목록 API용)
CREATE TABLE IF NOT EXISTS performance_commits (
    id BIGSERIAL PRIMARY KEY,
    account_id VARCHAR(32) NOT NULL,
    strategy_tag VARCHAR(64),
    period_start_epoch BIGINT NOT NULL,
    period_end_epoch BIGINT NOT NULL,
    total_pnl DECIMAL(20, 8) NOT NULL,
    max_drawdown DECIMAL(20, 8) NOT NULL,
    sharpe_ratio DECIMAL(20, 8) NOT NULL,
    win_rate DECIMAL(10, 4) NOT NULL,
    trade_count INT NOT NULL,
    hash_hex VARCHAR(64) NOT NULL,
    tx_hash VARCHAR(66),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_performance_commits_account ON performance_commits(account_id);
CREATE INDEX IF NOT EXISTS idx_performance_commits_created ON performance_commits(created_at DESC);

-- 키움 계좌 연동 (사용자별 연동 계좌)
CREATE TABLE IF NOT EXISTS kiwoom_account_links (
    id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(128) NOT NULL,
    kiwoom_account_no VARCHAR(32) NOT NULL,
    our_account_id VARCHAR(64) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, kiwoom_account_no)
);
CREATE INDEX IF NOT EXISTS idx_kiwoom_links_user ON kiwoom_account_links(user_id);
