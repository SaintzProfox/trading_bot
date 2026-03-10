"""Backtesting API route"""

from fastapi import APIRouter, Depends, Request, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from src.middleware.auth import verify_token

router = APIRouter()


class BacktestRequest(BaseModel):
    start_date: str = "2022-01-01"
    end_date: str = "2024-01-01"
    timeframe: str = "H1"
    initial_balance: float = 10000
    risk_percent: float = 1.0
    rsi_period: int = 14
    fast_ma: int = 20
    slow_ma: int = 50
    atr_sl_multiplier: float = 1.5
    atr_tp_multiplier: float = 3.0


@router.post("/run")
async def run_backtest(body: BacktestRequest, request: Request, payload: dict = Depends(verify_token)):
    """
    Runs a backtest synchronously (for demo; use background tasks in production)
    Data sourced from yfinance GC=F as XAUUSD proxy
    """
    try:
        import yfinance as yf
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../bot"))

        from backtest.backtester import Backtester
        from strategies.combined_strategy import CombinedStrategy

        ticker = yf.Ticker("GC=F")

        interval_map = {"M5": "5m", "M15": "15m", "H1": "1h", "H4": "1h", "D1": "1d"}
        yf_interval = interval_map.get(body.timeframe, "1h")

        df = ticker.history(start=body.start_date, end=body.end_date, interval=yf_interval)
        df.columns = [c.lower() for c in df.columns]
        df = df[["open", "high", "low", "close", "volume"]].dropna()

        strategy = CombinedStrategy(
            rsi_period=body.rsi_period,
            fast_ma=body.fast_ma,
            slow_ma=body.slow_ma,
            atr_sl_multiplier=body.atr_sl_multiplier,
            atr_tp_multiplier=body.atr_tp_multiplier,
        )

        backtester = Backtester(
            initial_balance=body.initial_balance,
            risk_percent=body.risk_percent,
            atr_sl_multiplier=body.atr_sl_multiplier,
            atr_tp_multiplier=body.atr_tp_multiplier,
        )

        result = backtester.run(df, strategy)

        # Store in DB
        db = request.app.state.db
        await db.execute(
            """INSERT INTO backtest_results (params, result, created_by, created_at)
               VALUES ($1::jsonb, $2::jsonb, $3, NOW())""",
            __import__("json").dumps(body.dict()),
            __import__("json").dumps({k: v for k, v in result.items() if k not in ("trades", "equity_curve")}),
            payload["sub"],
        )

        return result

    except Exception as e:
        return {"error": str(e)}


@router.get("/history")
async def backtest_history(request: Request, payload: dict = Depends(verify_token)):
    db = request.app.state.db
    rows = await db.fetch("SELECT id, params, result, created_at FROM backtest_results ORDER BY created_at DESC LIMIT 20")
    return [dict(r) for r in rows]
