-- ============================================================
-- XAUUSD Trading Bot — PostgreSQL Schema
-- Run: psql -U postgres -d tradingbot -f 001_initial_schema.sql
-- ============================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ─── Users ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id            SERIAL PRIMARY KEY,
    email         VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    name          VARCHAR(100),
    role          VARCHAR(20) DEFAULT 'user' CHECK (role IN ('user','admin')),
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW(),
    last_login    TIMESTAMPTZ
);

CREATE INDEX idx_users_email ON users(email);

-- ─── Bot Status ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS bot_status (
    id          SERIAL PRIMARY KEY,
    singleton   BOOLEAN UNIQUE DEFAULT TRUE,
    status      VARCHAR(20) DEFAULT 'stopped' CHECK (status IN ('running','stopped','error','paused')),
    pid         INT,
    started_at  TIMESTAMPTZ,
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);
INSERT INTO bot_status (singleton, status) VALUES (TRUE, 'stopped') ON CONFLICT DO NOTHING;

-- ─── Strategy Settings ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS strategy_settings (
    id          SERIAL PRIMARY KEY,
    key         VARCHAR(100) UNIQUE NOT NULL,
    value       TEXT NOT NULL,
    description TEXT,
    active      BOOLEAN DEFAULT TRUE,
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Default settings
INSERT INTO strategy_settings (key, value, description) VALUES
  ('timeframe',             'H1',   'Chart timeframe'),
  ('risk_percent',          '1.0',  'Risk per trade as % of balance'),
  ('max_daily_loss',        '3.0',  'Max daily drawdown % before halt'),
  ('max_open_trades',       '3',    'Maximum concurrent positions'),
  ('rsi_period',            '14',   'RSI lookback period'),
  ('rsi_overbought',        '70',   'RSI overbought threshold'),
  ('rsi_oversold',          '30',   'RSI oversold threshold'),
  ('fast_ma',               '20',   'Fast EMA period'),
  ('slow_ma',               '50',   'Slow EMA period'),
  ('atr_period',            '14',   'ATR lookback period'),
  ('atr_multiplier_sl',     '1.5',  'ATR multiplier for stop loss'),
  ('atr_multiplier_tp',     '3.0',  'ATR multiplier for take profit'),
  ('use_ml_filter',         'true', 'Enable ML signal filter'),
  ('ml_confidence_threshold','0.65','ML minimum confidence to trade'),
  ('loop_interval_seconds', '60',   'Strategy evaluation interval (seconds)')
ON CONFLICT (key) DO NOTHING;

-- ─── Trades ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS trades (
    id              SERIAL PRIMARY KEY,
    ticket          BIGINT UNIQUE,
    symbol          VARCHAR(20) DEFAULT 'XAUUSD',
    action          VARCHAR(10) NOT NULL CHECK (action IN ('BUY','SELL')),
    lot_size        NUMERIC(8,2),
    entry_price     NUMERIC(12,5),
    exit_price      NUMERIC(12,5),
    stop_loss       NUMERIC(12,5),
    take_profit     NUMERIC(12,5),
    pnl             NUMERIC(12,2),
    commission      NUMERIC(8,2) DEFAULT 0,
    swap            NUMERIC(8,2) DEFAULT 0,
    strategy_used   VARCHAR(50) DEFAULT 'combined',
    ml_confidence   NUMERIC(5,4),
    status          VARCHAR(20) DEFAULT 'open' CHECK (status IN ('open','closed','cancelled')),
    close_reason    VARCHAR(50),  -- 'tp','sl','manual','bot_stop'
    opened_at       TIMESTAMPTZ DEFAULT NOW(),
    closed_at       TIMESTAMPTZ,
    duration_minutes INT GENERATED ALWAYS AS (
        EXTRACT(EPOCH FROM (closed_at - opened_at)) / 60
    ) STORED
);

CREATE INDEX idx_trades_status ON trades(status);
CREATE INDEX idx_trades_opened_at ON trades(opened_at DESC);
CREATE INDEX idx_trades_symbol ON trades(symbol);

-- ─── Performance Metrics (time-series snapshots) ─────────────
CREATE TABLE IF NOT EXISTS performance_metrics (
    id          SERIAL PRIMARY KEY,
    recorded_at TIMESTAMPTZ DEFAULT NOW(),
    balance     NUMERIC(12,2),
    equity      NUMERIC(12,2),
    margin      NUMERIC(12,2),
    free_margin NUMERIC(12,2),
    daily_pnl   NUMERIC(12,2),
    weekly_pnl  NUMERIC(12,2),
    monthly_pnl NUMERIC(12,2),
    win_rate    NUMERIC(5,2),
    profit_factor NUMERIC(8,3),
    drawdown    NUMERIC(8,4),
    open_trades INT DEFAULT 0
);

CREATE INDEX idx_perf_recorded_at ON performance_metrics(recorded_at DESC);

-- ─── Backtest Results ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS backtest_results (
    id          SERIAL PRIMARY KEY,
    params      JSONB,
    result      JSONB,
    created_by  INT REFERENCES users(id),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ─── Refresh updated_at automatically ──────────────────────
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated_at BEFORE UPDATE ON users
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();
