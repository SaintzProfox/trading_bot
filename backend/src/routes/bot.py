"""Bot control routes — start, stop, status"""

import asyncio
import subprocess
import sys
import os
import signal as os_signal
from fastapi import APIRouter, Depends, HTTPException, Request
from src.middleware.auth import verify_token, require_admin

router = APIRouter()
_bot_process = None


@router.post("/start")
async def start_bot(request: Request, payload: dict = Depends(require_admin)):
    global _bot_process
    redis = request.app.state.redis
    status = await redis.get("bot_status") or "stopped"

    if status == "running":
        raise HTTPException(status_code=409, detail="Bot is already running")

    _bot_process = subprocess.Popen(
        [sys.executable, "trading_bot.py"],
        cwd=os.path.join(os.path.dirname(__file__), "../../../bot"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    await redis.set("bot_status", "running")
    db = request.app.state.db
    await db.execute("INSERT INTO bot_status (status) VALUES ('running') ON CONFLICT (singleton) DO UPDATE SET status='running', updated_at=NOW()")
    return {"message": "Bot started", "pid": _bot_process.pid}


@router.post("/stop")
async def stop_bot(request: Request, payload: dict = Depends(require_admin)):
    global _bot_process
    redis = request.app.state.redis

    if _bot_process:
        _bot_process.terminate()
        _bot_process = None

    await redis.set("bot_status", "stopped")
    db = request.app.state.db
    await db.execute("UPDATE bot_status SET status='stopped', updated_at=NOW() WHERE singleton=true")
    return {"message": "Bot stopped"}


@router.get("/status")
async def bot_status(request: Request, payload: dict = Depends(verify_token)):
    redis = request.app.state.redis
    db = request.app.state.db

    status = await redis.get("bot_status") or "stopped"
    metrics_raw = await redis.get("account_metrics")

    import json
    metrics = json.loads(metrics_raw) if metrics_raw else {}

    # Active positions from DB
    open_trades = await db.fetch("SELECT * FROM trades WHERE status = 'open' ORDER BY opened_at DESC")

    return {
        "status": status,
        "metrics": metrics,
        "open_trades": [dict(t) for t in open_trades],
    }
