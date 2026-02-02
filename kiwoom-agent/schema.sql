-- PostgreSQL: trades 테이블 (Spring Backend와 동일 스키마)
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
