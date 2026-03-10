-- ============================================================
-- Migration 002: Broker Credentials Table
-- Run: psql -U postgres -d tradingbot -f 002_broker_credentials.sql
-- ============================================================

CREATE TABLE IF NOT EXISTS broker_credentials (
    id                INT PRIMARY KEY DEFAULT 1,   -- singleton row
    mt5_login         VARCHAR(50),
    mt5_server        VARCHAR(100),
    mt5_password_enc  TEXT,                        -- AES-256-GCM encrypted, base64
    updated_by        INT REFERENCES users(id),
    updated_at        TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT single_row CHECK (id = 1)           -- enforce singleton
);

COMMENT ON TABLE broker_credentials IS 'Single-row table storing AES-256-GCM encrypted MT5/HFM credentials';
COMMENT ON COLUMN broker_credentials.mt5_password_enc IS 'base64(12-byte nonce || AES-GCM ciphertext). Key from CREDENTIALS_ENCRYPTION_KEY env var';
