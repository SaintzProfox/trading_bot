"""
Combined Trading Strategy: RSI + Moving Average Crossover + ATR
"""

import numpy as np
import pandas as pd
from typing import Optional


def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    hl = df["high"] - df["low"]
    hc = (df["high"] - df["close"].shift()).abs()
    lc = (df["low"] - df["close"].shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False).mean()


class CombinedStrategy:
    """RSI + EMA crossover + ATR stop-loss / take-profit"""

    def __init__(
        self,
        rsi_period: int = 14,
        rsi_overbought: float = 70,
        rsi_oversold: float = 30,
        fast_ma: int = 20,
        slow_ma: int = 50,
        atr_period: int = 14,
        atr_multiplier_sl: float = 1.5,
        atr_multiplier_tp: float = 3.0,
    ):
        self.rsi_period = rsi_period
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        self.fast_ma = fast_ma
        self.slow_ma = slow_ma
        self.atr_period = atr_period
        self.atr_multiplier_sl = atr_multiplier_sl
        self.atr_multiplier_tp = atr_multiplier_tp

    def _compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["rsi"] = compute_rsi(df["close"], self.rsi_period)
        df["ema_fast"] = df["close"].ewm(span=self.fast_ma, adjust=False).mean()
        df["ema_slow"] = df["close"].ewm(span=self.slow_ma, adjust=False).mean()
        df["atr"] = compute_atr(df, self.atr_period)
        df["ma_diff"] = df["ema_fast"] - df["ema_slow"]
        df["ma_diff_prev"] = df["ma_diff"].shift(1)
        return df

    def generate_signal(self, df: pd.DataFrame) -> dict:
        """Return signal dict with action, atr, strategy info"""
        df = self._compute_indicators(df)
        last = df.iloc[-1]
        prev = df.iloc[-2]

        action = "NONE"
        reason = []

        # Golden cross + RSI not overbought → BUY
        if (
            prev["ma_diff"] < 0
            and last["ma_diff"] > 0
            and last["rsi"] < self.rsi_overbought
            and last["rsi"] > 40
        ):
            action = "BUY"
            reason.append("golden_cross")
            reason.append(f"rsi={last['rsi']:.1f}")

        # RSI oversold + price above slow EMA → BUY
        elif (
            last["rsi"] < self.rsi_oversold
            and last["close"] > last["ema_slow"]
            and prev["rsi"] >= self.rsi_oversold
        ):
            action = "BUY"
            reason.append("rsi_oversold_bounce")
            reason.append(f"rsi={last['rsi']:.1f}")

        # Death cross + RSI not oversold → SELL
        elif (
            prev["ma_diff"] > 0
            and last["ma_diff"] < 0
            and last["rsi"] > self.rsi_oversold
            and last["rsi"] < 60
        ):
            action = "SELL"
            reason.append("death_cross")
            reason.append(f"rsi={last['rsi']:.1f}")

        # RSI overbought + price below slow EMA → SELL
        elif (
            last["rsi"] > self.rsi_overbought
            and last["close"] < last["ema_slow"]
            and prev["rsi"] <= self.rsi_overbought
        ):
            action = "SELL"
            reason.append("rsi_overbought_reject")
            reason.append(f"rsi={last['rsi']:.1f}")

        return {
            "action": action,
            "atr": float(last["atr"]),
            "rsi": float(last["rsi"]),
            "ema_fast": float(last["ema_fast"]),
            "ema_slow": float(last["ema_slow"]),
            "strategy": "combined",
            "reason": "|".join(reason),
            "timestamp": str(last.name),
        }

    def extract_features(self, df: pd.DataFrame) -> np.ndarray:
        """Feature vector for ML classifier"""
        df = self._compute_indicators(df)
        last = df.iloc[-1]
        prev5 = df.iloc[-6:-1]

        return np.array([
            last["rsi"] / 100,
            last["ma_diff"] / last["close"],
            last["atr"] / last["close"],
            (last["close"] - last["ema_fast"]) / last["atr"],
            (last["close"] - last["ema_slow"]) / last["atr"],
            prev5["close"].pct_change().mean(),
            prev5["close"].pct_change().std(),
            (last["high"] - last["low"]) / last["atr"],
        ]).reshape(1, -1)
