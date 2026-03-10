"""
MT5 / HFM Credentials API
- AES-256-GCM encryption at rest (via cryptography library)
- Password is write-only — never returned to the client
- Saving triggers a bot restart via Redis signal
"""

import base64
import json
import os
from datetime import datetime

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional

from src.middleware.auth import require_admin, verify_token

router = APIRouter()

# AES-256 key: 32 bytes, base64-encoded in env
def _get_key() -> bytes:
    raw = os.getenv("CREDENTIALS_ENCRYPTION_KEY", "")
    if len(raw) >= 32:
        return raw[:32].encode()
    # Derive a deterministic fallback from JWT_SECRET (not ideal — set CREDENTIALS_ENCRYPTION_KEY in prod)
    secret = os.getenv("JWT_SECRET", "fallback-secret-change-me")
    return (secret * 4)[:32].encode()


def _encrypt(plaintext: str) -> str:
    """AES-256-GCM encrypt → base64(nonce + ciphertext)"""
    key = _get_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ct = aesgcm.encrypt(nonce, plaintext.encode(), None)
    return base64.b64encode(nonce + ct).decode()


def _decrypt(token: str) -> str:
    """Reverse of _encrypt"""
    key = _get_key()
    aesgcm = AESGCM(key)
    raw = base64.b64decode(token)
    nonce, ct = raw[:12], raw[12:]
    return aesgcm.decrypt(nonce, ct, None).decode()


# ─── Schemas ──────────────────────────────────────────────────────────────────

class CredentialsUpdate(BaseModel):
    mt5_login: str
    mt5_server: str
    mt5_password: Optional[str] = None   # optional: omit to keep existing


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.get("/")
async def get_credentials(request: Request, payload: dict = Depends(require_admin)):
    """Return non-sensitive credential info (login + server only, never password)"""
    db = request.app.state.db
    row = await db.fetchrow("SELECT * FROM broker_credentials WHERE id = 1")
    if not row:
        return {"mt5_login": None, "mt5_server": None, "has_password": False, "updated_at": None}

    return {
        "mt5_login": row["mt5_login"],
        "mt5_server": row["mt5_server"],
        "has_password": bool(row["mt5_password_enc"]),
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
    }


@router.put("/")
async def update_credentials(
    body: CredentialsUpdate,
    request: Request,
    payload: dict = Depends(require_admin),
):
    """Upsert encrypted credentials, then signal bot to restart"""
    db = request.app.state.db
    redis = request.app.state.redis

    # Fetch existing to preserve password if not provided
    existing = await db.fetchrow("SELECT mt5_password_enc FROM broker_credentials WHERE id = 1")
    if body.mt5_password:
        encrypted_pw = _encrypt(body.mt5_password)
    elif existing and existing["mt5_password_enc"]:
        encrypted_pw = existing["mt5_password_enc"]
    else:
        raise HTTPException(400, detail="Password is required for first-time setup.")

    await db.execute(
        """INSERT INTO broker_credentials (id, mt5_login, mt5_server, mt5_password_enc, updated_by, updated_at)
           VALUES (1, $1, $2, $3, $4, NOW())
           ON CONFLICT (id) DO UPDATE SET
             mt5_login = EXCLUDED.mt5_login,
             mt5_server = EXCLUDED.mt5_server,
             mt5_password_enc = EXCLUDED.mt5_password_enc,
             updated_by = EXCLUDED.updated_by,
             updated_at = NOW()""",
        body.mt5_login,
        body.mt5_server,
        encrypted_pw,
        int(payload["sub"]),
    )

    # Signal bot to reload credentials and restart MT5 connection
    await redis.set("credentials_changed", "1")
    await redis.set("bot_status", "restarting")

    return {
        "message": "Credentials saved. Bot is restarting to apply changes.",
        "mt5_login": body.mt5_login,
        "mt5_server": body.mt5_server,
    }


# ─── Helper used by trading bot ───────────────────────────────────────────────

async def load_decrypted_credentials(db) -> dict:
    """Called by the trading bot to get plaintext MT5 credentials"""
    row = await db.fetchrow("SELECT * FROM broker_credentials WHERE id = 1")
    if not row:
        return {}
    password = _decrypt(row["mt5_password_enc"]) if row["mt5_password_enc"] else ""
    return {
        "login": int(row["mt5_login"]),
        "password": password,
        "server": row["mt5_server"],
    }
