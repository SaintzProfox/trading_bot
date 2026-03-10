"""
XAUUSD (Gold) Trading Bot - HFM/MetaTrader5 Integration
Production-ready trading engine with RSI, MA Crossover, ATR strategies
"""

import asyncio
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Optional
import json

import MetaTrader5 as mt5
import numpy as np
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import redis
from dotenv import load_dotenv

from strategies.rsi_strategy import RSIStrategy
from strategies.ma_crossover import MACrossoverStrategy
from strategies.combined_strategy import CombinedStrategy
from ml.signal_classifier import SignalClassifier
from utils.risk_manager import RiskManager
from utils.logger import setup_logger

load_dotenv()

logger = setup_logger("TradingBot")


class TradingBot:
    """Main trading bot orchestrator for XAUUSD on HFM/MT5"""

    SYMBOL = "XAUUSD"
    MT5_TIMEFRAMES = {
        "M1": mt5.TIMEFRAME_M1,
        "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15,
        "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1,
        "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1,
    }

    def __init__(self):
        self.running = False
        self.db_conn = None
        self.redis_client = None
        self.risk_manager = None
        self.strategy = None
        self.ml_classifier = None
        self.settings = {}
        self.daily_pnl = 0.0
        self.daily_trade_count = 0
        self.last_day_reset = datetime.now().date()

    # ─── Initialisation ───────────────────────────────────────────────────────

    def initialize(self) -> bool:
        """Boot sequence: DB → Redis → MT5 → Strategy → ML"""
        try:
            self._connect_db()
            self._connect_redis()
            self.settings = self._load_settings()
            self._init_mt5()
            self._init_strategy()
            self._init_ml()
            self.risk_manager = RiskManager(self.settings)
            logger.info("Trading bot initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            return False

    def _connect_db(self):
        self.db_conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", 5432),
            database=os.getenv("DB_NAME", "tradingbot"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD"),
        )
        logger.info("Database connected")

    def _connect_redis(self):
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            decode_responses=True,
        )
        self.redis_client.ping()
        logger.info("Redis connected")

    def _init_mt5(self):
        if not mt5.initialize(
            path=os.getenv("MT5_PATH", ""),
            login=int(os.getenv("MT5_LOGIN", 0)),
            password=os.getenv("MT5_PASSWORD"),
            server=os.getenv("MT5_SERVER", "HFMarkets-Demo"),
        ):
            raise RuntimeError(f"MT5 init failed: {mt5.last_error()}")
        account = mt5.account_info()
        logger.info(f"MT5 connected | Account: {account.login} | Balance: {account.balance}")

    def _init_strategy(self):
        s = self.settings
        self.strategy = CombinedStrategy(
            rsi_period=s.get("rsi_period", 14),
            rsi_overbought=s.get("rsi_overbought", 70),
            rsi_oversold=s.get("rsi_oversold", 30),
            fast_ma=s.get("fast_ma", 20),
            slow_ma=s.get("slow_ma", 50),
            atr_period=s.get("atr_period", 14),
            atr_multiplier_sl=s.get("atr_multiplier_sl", 1.5),
            atr_multiplier_tp=s.get("atr_multiplier_tp", 3.0),
        )

    def _init_ml(self):
        model_path = os.getenv("ML_MODEL_PATH", "ml/models/signal_classifier.pkl")
        if os.path.exists(model_path):
            self.ml_classifier = SignalClassifier()
            self.ml_classifier.load(model_path)
            logger.info("ML classifier loaded")
        else:
            logger.warning("No ML model found — running without ML filter")

    def _load_settings(self) -> dict:
        with self.db_conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT key, value FROM strategy_settings WHERE active = TRUE")
            rows = cur.fetchall()
        settings = {r["key"]: self._cast(r["value"]) for r in rows}
        defaults = {
            "timeframe": "H1",
            "risk_percent": 1.0,
            "max_daily_loss": 3.0,
            "max_open_trades": 3,
            "rsi_period": 14,
            "rsi_overbought": 70,
            "rsi_oversold": 30,
            "fast_ma": 20,
            "slow_ma": 50,
            "atr_period": 14,
            "atr_multiplier_sl": 1.5,
            "atr_multiplier_tp": 3.0,
            "ml_confidence_threshold": 0.65,
            "use_ml_filter": True,
            "loop_interval_seconds": 60,
        }
        for k, v in defaults.items():
            settings.setdefault(k, v)
        return settings

    @staticmethod
    def _cast(value: str):
        try:
            if "." in value:
                return float(value)
            return int(value)
        except (ValueError, TypeError):
            if value.lower() in ("true", "false"):
                return value.lower() == "true"
            return value

    # ─── Main Loop ────────────────────────────────────────────────────────────

    def run(self):
        """Blocking main loop"""
        if not self.initialize():
            return
        self.running = True
        self._set_bot_status("running")
        logger.info("Bot started — entering main loop")
        try:
            while self.running:
                self._tick()
                interval = self.settings.get("loop_interval_seconds", 60)
                time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        finally:
            self.stop()

    def stop(self):
        self.running = False
        self._set_bot_status("stopped")
        mt5.shutdown()
        if self.db_conn:
            self.db_conn.close()
        logger.info("Bot stopped cleanly")

    def _tick(self):
        """Single strategy evaluation cycle"""
        try:
            self._reset_daily_counters_if_needed()
            self._reload_settings_if_changed()

            # Risk gate
            if not self.risk_manager.can_trade(
                daily_pnl=self.daily_pnl,
                open_trades=self._count_open_trades(),
            ):
                logger.info("Risk gate: no trading allowed this tick")
                return

            tf = self.MT5_TIMEFRAMES.get(self.settings["timeframe"], mt5.TIMEFRAME_H1)
            rates = mt5.copy_rates_from_pos(self.SYMBOL, tf, 0, 500)
            if rates is None or len(rates) < 200:
                logger.warning("Insufficient price data")
                return

            df = pd.DataFrame(rates)
            df["time"] = pd.to_datetime(df["time"], unit="s")
            df.set_index("time", inplace=True)

            signal = self.strategy.generate_signal(df)

            if signal["action"] == "NONE":
                return

            # ML filter
            if self.settings.get("use_ml_filter") and self.ml_classifier:
                features = self.strategy.extract_features(df)
                prob = self.ml_classifier.predict_proba(features)
                threshold = self.settings.get("ml_confidence_threshold", 0.65)
                if prob < threshold:
                    logger.info(f"ML rejected signal — prob={prob:.3f} < {threshold}")
                    return
                signal["ml_confidence"] = prob

            self._execute_signal(signal, df)
            self._update_dashboard_cache()

        except Exception as e:
            logger.error(f"Tick error: {e}", exc_info=True)

    # ─── Execution ────────────────────────────────────────────────────────────

    def _execute_signal(self, signal: dict, df: pd.DataFrame):
        symbol_info = mt5.symbol_info(self.SYMBOL)
        if symbol_info is None:
            return

        price = mt5.symbol_info_tick(self.SYMBOL)
        entry = price.ask if signal["action"] == "BUY" else price.bid
        atr = signal["atr"]

        sl_distance = atr * self.settings["atr_multiplier_sl"]
        tp_distance = atr * self.settings["atr_multiplier_tp"]

        if signal["action"] == "BUY":
            sl = entry - sl_distance
            tp = entry + tp_distance
            order_type = mt5.ORDER_TYPE_BUY
        else:
            sl = entry + sl_distance
            tp = entry - tp_distance
            order_type = mt5.ORDER_TYPE_SELL

        account = mt5.account_info()
        lot_size = self.risk_manager.calculate_lot_size(
            account_balance=account.balance,
            sl_pips=sl_distance / symbol_info.point,
            symbol_info=symbol_info,
        )

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.SYMBOL,
            "volume": lot_size,
            "type": order_type,
            "price": entry,
            "sl": sl,
            "tp": tp,
            "deviation": 20,
            "magic": 20240101,
            "comment": f"Bot|{signal['strategy']}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"Order failed: {result.retcode} — {result.comment}")
            return

        logger.info(f"Order placed | {signal['action']} {lot_size} lots @ {entry} | SL={sl:.2f} TP={tp:.2f}")
        self._save_trade(result, signal, entry, sl, tp, lot_size)
        self.daily_trade_count += 1

    def _save_trade(self, result, signal, entry, sl, tp, lot_size):
        with self.db_conn.cursor() as cur:
            cur.execute(
                """INSERT INTO trades
                   (ticket, symbol, action, lot_size, entry_price, stop_loss, take_profit,
                    strategy_used, ml_confidence, status, opened_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'open',NOW())""",
                (
                    result.order,
                    self.SYMBOL,
                    signal["action"],
                    lot_size,
                    entry,
                    sl,
                    tp,
                    signal.get("strategy", "combined"),
                    signal.get("ml_confidence"),
                ),
            )
        self.db_conn.commit()

    # ─── Helpers ──────────────────────────────────────────────────────────────

    def _count_open_trades(self) -> int:
        positions = mt5.positions_get(symbol=self.SYMBOL)
        return len(positions) if positions else 0

    def _reset_daily_counters_if_needed(self):
        today = datetime.now().date()
        if today != self.last_day_reset:
            self.daily_pnl = 0.0
            self.daily_trade_count = 0
            self.last_day_reset = today

    def _reload_settings_if_changed(self):
        changed = self.redis_client.get("settings_changed")
        if changed:
            self.settings = self._load_settings()
            self._init_strategy()
            self.risk_manager = RiskManager(self.settings)
            self.redis_client.delete("settings_changed")
            logger.info("Settings reloaded")

    def _set_bot_status(self, status: str):
        with self.db_conn.cursor() as cur:
            cur.execute(
                "INSERT INTO bot_status (status, updated_at) VALUES (%s, NOW()) "
                "ON CONFLICT (id) DO UPDATE SET status=%s, updated_at=NOW()",
                (status, status),
            )
        self.db_conn.commit()
        self.redis_client.set("bot_status", status)

    def _update_dashboard_cache(self):
        """Cache aggregated metrics in Redis for fast API reads"""
        account = mt5.account_info()
        if not account:
            return
        metrics = {
            "balance": account.balance,
            "equity": account.equity,
            "margin": account.margin,
            "free_margin": account.margin_free,
            "profit": account.profit,
            "daily_pnl": self.daily_pnl,
            "open_trades": self._count_open_trades(),
            "updated_at": datetime.now().isoformat(),
        }
        self.redis_client.setex("account_metrics", 30, json.dumps(metrics))


if __name__ == "__main__":
    bot = TradingBot()
    bot.run()
