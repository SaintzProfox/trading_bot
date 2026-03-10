"""
Backtesting Engine for XAUUSD strategies
Vectorised backtester with full performance metrics reporting
"""

import numpy as np
import pandas as pd
import json
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger("Backtester")


class Backtester:
    """Vectorised backtesting with realistic spread and slippage simulation"""

    DEFAULT_SPREAD_PIPS = 3   # XAUUSD typical spread
    DEFAULT_SLIPPAGE_PIPS = 1

    def __init__(
        self,
        initial_balance: float = 10_000,
        risk_percent: float = 1.0,
        atr_sl_multiplier: float = 1.5,
        atr_tp_multiplier: float = 3.0,
        spread_pips: float = DEFAULT_SPREAD_PIPS,
        slippage_pips: float = DEFAULT_SLIPPAGE_PIPS,
        commission_per_lot: float = 7.0,
    ):
        self.initial_balance = initial_balance
        self.risk_percent = risk_percent
        self.atr_sl_mult = atr_sl_multiplier
        self.atr_tp_mult = atr_tp_multiplier
        self.spread = spread_pips * 0.01   # convert to price
        self.slippage = slippage_pips * 0.01
        self.commission = commission_per_lot

    def run(self, df: pd.DataFrame, strategy) -> dict:
        """
        Run full backtest.
        df: OHLCV DataFrame with DatetimeIndex
        strategy: CombinedStrategy instance
        Returns: performance metrics dict + equity curve
        """
        from strategies.combined_strategy import compute_rsi, compute_atr

        df = df.copy()
        df["rsi"] = compute_rsi(df["close"], strategy.rsi_period)
        df["ema_fast"] = df["close"].ewm(span=strategy.fast_ma, adjust=False).mean()
        df["ema_slow"] = df["close"].ewm(span=strategy.slow_ma, adjust=False).mean()
        df["atr"] = compute_atr(df, strategy.atr_period)
        df["ma_diff"] = df["ema_fast"] - df["ema_slow"]
        df.dropna(inplace=True)

        trades = []
        balance = self.initial_balance
        equity_curve = [balance]
        in_trade = False
        entry_price = sl = tp = action = None
        lot_size = 0.01

        for i in range(1, len(df)):
            row = df.iloc[i]
            prev = df.iloc[i - 1]

            if in_trade:
                # Check if SL/TP hit on this candle
                if action == "BUY":
                    if row["low"] <= sl:
                        pnl = (sl - entry_price) * lot_size * 100 - self.commission
                        balance += pnl
                        trades.append({"type": "BUY", "entry": entry_price, "exit": sl, "pnl": pnl, "result": "SL", "time": row.name})
                        in_trade = False
                    elif row["high"] >= tp:
                        pnl = (tp - entry_price) * lot_size * 100 - self.commission
                        balance += pnl
                        trades.append({"type": "BUY", "entry": entry_price, "exit": tp, "pnl": pnl, "result": "TP", "time": row.name})
                        in_trade = False
                else:  # SELL
                    if row["high"] >= sl:
                        pnl = (entry_price - sl) * lot_size * 100 - self.commission
                        balance += pnl
                        trades.append({"type": "SELL", "entry": entry_price, "exit": sl, "pnl": pnl, "result": "SL", "time": row.name})
                        in_trade = False
                    elif row["low"] <= tp:
                        pnl = (entry_price - tp) * lot_size * 100 - self.commission
                        balance += pnl
                        trades.append({"type": "SELL", "entry": entry_price, "exit": tp, "pnl": pnl, "result": "TP", "time": row.name})
                        in_trade = False

            if not in_trade:
                sig = self._detect_signal(row, prev)
                if sig != "NONE":
                    atr = row["atr"]
                    risk_amount = balance * (self.risk_percent / 100)
                    sl_distance = atr * self.atr_sl_mult
                    tp_distance = atr * self.atr_tp_mult

                    if sig == "BUY":
                        entry_price = row["close"] + self.spread + self.slippage
                        sl = entry_price - sl_distance
                        tp = entry_price + tp_distance
                    else:
                        entry_price = row["close"] - self.spread - self.slippage
                        sl = entry_price + sl_distance
                        tp = entry_price - tp_distance

                    lot_size = max(0.01, min(5.0, round(risk_amount / (sl_distance * 100), 2)))
                    action = sig
                    in_trade = True

            equity_curve.append(balance)

        return self._compile_metrics(trades, equity_curve, df)

    def _detect_signal(self, row, prev) -> str:
        if prev["ma_diff"] < 0 and row["ma_diff"] > 0 and 40 < row["rsi"] < 70:
            return "BUY"
        if row["rsi"] < 30 and row["close"] > row["ema_slow"]:
            return "BUY"
        if prev["ma_diff"] > 0 and row["ma_diff"] < 0 and 30 < row["rsi"] < 60:
            return "SELL"
        if row["rsi"] > 70 and row["close"] < row["ema_slow"]:
            return "SELL"
        return "NONE"

    def _compile_metrics(self, trades: list, equity: list, df: pd.DataFrame) -> dict:
        if not trades:
            return {"error": "No trades generated"}

        trade_df = pd.DataFrame(trades)
        wins = trade_df[trade_df["pnl"] > 0]
        losses = trade_df[trade_df["pnl"] <= 0]

        total_pnl = trade_df["pnl"].sum()
        win_rate = len(wins) / len(trade_df) * 100
        avg_win = wins["pnl"].mean() if len(wins) else 0
        avg_loss = losses["pnl"].mean() if len(losses) else 0
        profit_factor = (wins["pnl"].sum() / abs(losses["pnl"].sum())) if len(losses) else float("inf")

        eq = pd.Series(equity)
        rolling_max = eq.cummax()
        drawdown = (eq - rolling_max) / rolling_max * 100
        max_dd = drawdown.min()

        sharpe = 0
        if len(trade_df) > 1:
            returns = trade_df["pnl"] / self.initial_balance
            sharpe = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0

        return {
            "total_trades": len(trade_df),
            "winning_trades": len(wins),
            "losing_trades": len(losses),
            "win_rate": round(win_rate, 2),
            "total_pnl": round(total_pnl, 2),
            "final_balance": round(self.initial_balance + total_pnl, 2),
            "return_pct": round(total_pnl / self.initial_balance * 100, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "profit_factor": round(profit_factor, 3),
            "max_drawdown_pct": round(max_dd, 2),
            "sharpe_ratio": round(sharpe, 3),
            "equity_curve": [round(e, 2) for e in equity[::max(1, len(equity) // 500)]],  # downsample
            "trades": trade_df.to_dict(orient="records"),
            "start_date": str(df.index[0]),
            "end_date": str(df.index[-1]),
            "generated_at": datetime.now().isoformat(),
        }
