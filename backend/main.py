"""
Trading Bot Backend API — FastAPI
Handles: bot control, strategy config, trade history, metrics, WebSocket
"""

import asyncio
import json
import os
import subprocess
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional

import redis.asyncio as aioredis
import asyncpg
import uvicorn
from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.routes import auth, bot, trades, metrics, settings, backtest, credentials
from src.websocket.manager import ConnectionManager
from src.middleware.auth import verify_token
from src.config import Settings

app_settings = Settings()


# ─── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.db = await asyncpg.create_pool(app_settings.DATABASE_URL, min_size=2, max_size=10)
    app.state.redis = aioredis.from_url(app_settings.REDIS_URL, decode_responses=True)
    app.state.ws_manager = ConnectionManager()
    print("✅ DB pool and Redis connected")
    yield
    # Shutdown
    await app.state.db.close()
    await app.state.redis.close()
    print("🔴 Connections closed")


# ─── App Factory ──────────────────────────────────────────────────────────────

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="XAUUSD Trading Bot API",
    description="Production trading bot API for Gold (XAUUSD) on HFM",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter

app.add_middleware(
    CORSMiddleware,
    allow_origins=app_settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ──────────────────────────────────────────────────────────────────

app.include_router(auth.router,     prefix="/api/auth",     tags=["Authentication"])
app.include_router(bot.router,      prefix="/api/bot",      tags=["Bot Control"])
app.include_router(trades.router,   prefix="/api/trades",   tags=["Trade History"])
app.include_router(metrics.router,  prefix="/api/metrics",  tags=["Performance"])
app.include_router(settings.router, prefix="/api/settings", tags=["Strategy Settings"])
app.include_router(backtest.router,     prefix="/api/backtest",     tags=["Backtesting"])
app.include_router(credentials.router,  prefix="/api/credentials",  tags=["MT5 Credentials"])


# ─── WebSocket ────────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: Optional[str] = None):
    try:
        verify_token(token)
    except Exception:
        await websocket.close(code=4001)
        return

    manager: ConnectionManager = websocket.app.state.ws_manager
    await manager.connect(websocket)

    try:
        while True:
            # Push live metrics every 5 seconds
            redis: aioredis.Redis = websocket.app.state.redis
            metrics_raw = await redis.get("account_metrics")
            bot_status = await redis.get("bot_status") or "stopped"

            payload = {
                "type": "heartbeat",
                "bot_status": bot_status,
                "metrics": json.loads(metrics_raw) if metrics_raw else {},
                "timestamp": datetime.now().isoformat(),
            }
            await manager.send_personal_message(json.dumps(payload), websocket)
            await asyncio.sleep(5)

    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ─── Health Check ─────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "time": datetime.now().isoformat()}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False, workers=2)
