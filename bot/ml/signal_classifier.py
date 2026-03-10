"""
ML Signal Classifier for XAUUSD
Uses Random Forest trained on historical XAUUSD data to filter trade signals.
"""

import os
import pickle
import logging
import numpy as np
import pandas as pd
from typing import Optional

logger = logging.getLogger("SignalClassifier")


class SignalClassifier:
    """Random Forest classifier to label signals as high/low probability"""

    def __init__(self):
        self.model = None
        self.scaler = None
        self.feature_names = [
            "rsi_norm",
            "ma_diff_norm",
            "atr_norm",
            "price_vs_fast_ema",
            "price_vs_slow_ema",
            "mean_return_5",
            "std_return_5",
            "candle_range_norm",
        ]

    def train(self, df: pd.DataFrame, forward_periods: int = 10, profit_threshold: float = 0.003):
        """
        Train on historical OHLCV data.
        Label = 1 if future return > profit_threshold else 0.
        """
        from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
        from sklearn.preprocessing import StandardScaler
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import classification_report

        from strategies.combined_strategy import CombinedStrategy, compute_rsi, compute_atr

        strategy = CombinedStrategy()

        df = df.copy()
        df["rsi"] = compute_rsi(df["close"], 14)
        df["ema_fast"] = df["close"].ewm(span=20, adjust=False).mean()
        df["ema_slow"] = df["close"].ewm(span=50, adjust=False).mean()
        df["atr"] = compute_atr(df, 14)
        df["ma_diff"] = df["ema_fast"] - df["ema_slow"]
        df["future_return"] = df["close"].pct_change(forward_periods).shift(-forward_periods)
        df["label"] = (df["future_return"] > profit_threshold).astype(int)
        df.dropna(inplace=True)

        X = np.column_stack([
            df["rsi"] / 100,
            df["ma_diff"] / df["close"],
            df["atr"] / df["close"],
            (df["close"] - df["ema_fast"]) / df["atr"],
            (df["close"] - df["ema_slow"]) / df["atr"],
            df["close"].pct_change(5).rolling(5).mean(),
            df["close"].pct_change(5).rolling(5).std(),
            (df["high"] - df["low"]) / df["atr"],
        ])
        y = df["label"].values

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)

        self.scaler = StandardScaler()
        X_train_s = self.scaler.fit_transform(X_train)
        X_test_s = self.scaler.transform(X_test)

        self.model = GradientBoostingClassifier(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.05,
            random_state=42,
        )
        self.model.fit(X_train_s, y_train)

        preds = self.model.predict(X_test_s)
        report = classification_report(y_test, preds)
        logger.info(f"Training complete:\n{report}")
        return report

    def predict_proba(self, features: np.ndarray) -> float:
        """Return probability of signal being profitable"""
        if self.model is None:
            return 0.5
        scaled = self.scaler.transform(features)
        proba = self.model.predict_proba(scaled)[0][1]
        return float(proba)

    def save(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump({"model": self.model, "scaler": self.scaler}, f)
        logger.info(f"Model saved to {path}")

    def load(self, path: str):
        with open(path, "rb") as f:
            data = pickle.load(f)
        self.model = data["model"]
        self.scaler = data["scaler"]
        logger.info(f"Model loaded from {path}")


# ─── Training Script ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    """Run: python ml/signal_classifier.py to train the model"""
    import yfinance as yf
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

    logging.basicConfig(level=logging.INFO)
    logger.info("Downloading XAUUSD historical data...")

    ticker = yf.Ticker("GC=F")  # Gold Futures as proxy
    df = ticker.history(period="5y", interval="1h")
    df.columns = [c.lower() for c in df.columns]
    df = df[["open", "high", "low", "close", "volume"]].dropna()

    logger.info(f"Training on {len(df)} candles")
    clf = SignalClassifier()
    clf.train(df)
    clf.save("ml/models/signal_classifier.pkl")
    logger.info("Done — model saved to ml/models/signal_classifier.pkl")
