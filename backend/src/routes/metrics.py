"""Performance metrics routes"""

from fastapi import APIRouter, Depends, Request
from src.middleware.auth import verify_token
from datetime import datetime, timedelta

router = APIRouter()


@router.get("/summary")
async def get_summary(request: Request, payload: dict = Depends(verify_token)):
    db = request.app.state.db

    today = datetime.now().date()
    month_start = today.replace(day=1)

    total = await db.fetchrow("""
        SELECT
            COUNT(*) AS total_trades,
            COUNT(*) FILTER (WHERE pnl > 0) AS wins,
            COUNT(*) FILTER (WHERE pnl <= 0) AS losses,
            COALESCE(SUM(pnl), 0) AS total_pnl,
            COALESCE(AVG(pnl) FILTER (WHERE pnl > 0), 0) AS avg_win,
            COALESCE(AVG(ABS(pnl)) FILTER (WHERE pnl <= 0), 0) AS avg_loss
        FROM trades WHERE status = 'closed'
    """)

    daily = await db.fetchrow("""
        SELECT COALESCE(SUM(pnl), 0) AS pnl, COUNT(*) AS trades
        FROM trades WHERE status='closed' AND DATE(closed_at) = $1
    """, today)

    monthly = await db.fetchrow("""
        SELECT COALESCE(SUM(pnl), 0) AS pnl, COUNT(*) AS trades
        FROM trades WHERE status='closed' AND DATE(closed_at) >= $1
    """, month_start)

    equity = await db.fetch("""
        SELECT DATE(closed_at) AS date, SUM(pnl) AS daily_pnl
        FROM trades WHERE status='closed'
        GROUP BY DATE(closed_at) ORDER BY date ASC
    """)

    t = dict(total)
    win_rate = (t["wins"] / t["total_trades"] * 100) if t["total_trades"] > 0 else 0
    profit_factor = (t["avg_win"] * t["wins"]) / (t["avg_loss"] * t["losses"]) if t["losses"] > 0 else 0

    # Compute max drawdown from equity curve
    running = 0
    peak = 0
    max_dd = 0
    for row in equity:
        running += float(row["daily_pnl"])
        if running > peak:
            peak = running
        dd = (peak - running) / max(peak, 1) * 100
        if dd > max_dd:
            max_dd = dd

    return {
        "total_trades": t["total_trades"],
        "wins": t["wins"],
        "losses": t["losses"],
        "win_rate": round(win_rate, 2),
        "total_pnl": round(float(t["total_pnl"]), 2),
        "avg_win": round(float(t["avg_win"]), 2),
        "avg_loss": round(float(t["avg_loss"]), 2),
        "profit_factor": round(profit_factor, 3),
        "max_drawdown_pct": round(max_dd, 2),
        "daily_pnl": round(float(daily["pnl"]), 2),
        "daily_trades": daily["trades"],
        "monthly_pnl": round(float(monthly["pnl"]), 2),
        "monthly_trades": monthly["trades"],
        "equity_curve": [{"date": str(r["date"]), "pnl": round(float(r["daily_pnl"]), 2)} for r in equity],
    }


@router.get("/performance-history")
async def performance_history(request: Request, payload: dict = Depends(verify_token)):
    db = request.app.state.db
    rows = await db.fetch("""
        SELECT recorded_at, balance, equity, daily_pnl, win_rate, drawdown
        FROM performance_metrics ORDER BY recorded_at DESC LIMIT 720
    """)
    return [dict(r) for r in rows]
