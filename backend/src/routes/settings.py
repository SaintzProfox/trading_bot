"""Strategy settings routes"""

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from typing import Any, Dict
from src.middleware.auth import require_admin, verify_token

router = APIRouter()


class SettingUpdate(BaseModel):
    key: str
    value: Any


class BulkSettingsUpdate(BaseModel):
    settings: Dict[str, Any]


@router.get("/")
async def get_settings(request: Request, payload: dict = Depends(verify_token)):
    db = request.app.state.db
    rows = await db.fetch("SELECT key, value, description FROM strategy_settings WHERE active = TRUE ORDER BY key")
    return {r["key"]: {"value": r["value"], "description": r["description"]} for r in rows}


@router.put("/")
async def update_settings(body: BulkSettingsUpdate, request: Request, payload: dict = Depends(require_admin)):
    db = request.app.state.db
    redis = request.app.state.redis

    async with db.transaction():
        for key, value in body.settings.items():
            await db.execute(
                """INSERT INTO strategy_settings (key, value, updated_at, active)
                   VALUES ($1, $2, NOW(), TRUE)
                   ON CONFLICT (key) DO UPDATE SET value=$2, updated_at=NOW()""",
                key, str(value)
            )

    await redis.set("settings_changed", "1")
    return {"message": "Settings updated", "count": len(body.settings)}


@router.get("/defaults")
async def get_defaults(payload: dict = Depends(verify_token)):
    return {
        "timeframe": {"value": "H1", "options": ["M5", "M15", "M30", "H1", "H4", "D1"], "description": "Trading timeframe"},
        "risk_percent": {"value": 1.0, "min": 0.1, "max": 5.0, "description": "Risk per trade (% of balance)"},
        "max_daily_loss": {"value": 3.0, "min": 1.0, "max": 10.0, "description": "Max daily loss (%)"},
        "max_open_trades": {"value": 3, "min": 1, "max": 10, "description": "Max concurrent open trades"},
        "rsi_period": {"value": 14, "min": 5, "max": 50},
        "rsi_overbought": {"value": 70, "min": 60, "max": 90},
        "rsi_oversold": {"value": 30, "min": 10, "max": 40},
        "fast_ma": {"value": 20, "min": 5, "max": 100},
        "slow_ma": {"value": 50, "min": 20, "max": 200},
        "atr_period": {"value": 14, "min": 7, "max": 50},
        "atr_multiplier_sl": {"value": 1.5, "min": 0.5, "max": 5.0, "description": "ATR multiplier for stop loss"},
        "atr_multiplier_tp": {"value": 3.0, "min": 1.0, "max": 10.0, "description": "ATR multiplier for take profit"},
        "use_ml_filter": {"value": True, "description": "Enable ML signal filtering"},
        "ml_confidence_threshold": {"value": 0.65, "min": 0.5, "max": 0.95},
    }
