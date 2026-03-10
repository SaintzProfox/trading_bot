"""
Risk Management Engine
- Max risk per trade (% of balance)
- Daily loss limit
- Maximum concurrent open trades
- Position sizing via ATR
"""

import logging

logger = logging.getLogger("RiskManager")

XAUUSD_TICK_VALUE_PER_LOT = 1.0   # $1 per pip per 0.01 lot for XAUUSD on most brokers
XAUUSD_POINT = 0.01


class RiskManager:
    def __init__(self, settings: dict):
        self.risk_percent = float(settings.get("risk_percent", 1.0))
        self.max_daily_loss_percent = float(settings.get("max_daily_loss", 3.0))
        self.max_open_trades = int(settings.get("max_open_trades", 3))
        self.min_lot = 0.01
        self.max_lot = 5.0

    def can_trade(self, daily_pnl: float, open_trades: int, account_balance: float = None) -> bool:
        if open_trades >= self.max_open_trades:
            logger.info(f"Max open trades reached ({open_trades}/{self.max_open_trades})")
            return False

        if account_balance and daily_pnl < 0:
            daily_loss_pct = abs(daily_pnl) / account_balance * 100
            if daily_loss_pct >= self.max_daily_loss_percent:
                logger.warning(f"Daily loss limit hit: {daily_loss_pct:.2f}% >= {self.max_daily_loss_percent}%")
                return False

        return True

    def calculate_lot_size(
        self,
        account_balance: float,
        sl_pips: float,
        symbol_info=None,
    ) -> float:
        """Kelly-inspired fixed-fractional position sizing"""
        risk_amount = account_balance * (self.risk_percent / 100)

        # For XAUUSD: 1 lot = 100oz, pip value ≈ $1 per 0.01 pip
        # Tick value from symbol_info is most accurate
        if symbol_info:
            tick_value = symbol_info.trade_tick_value
            tick_size = symbol_info.trade_tick_size
            if tick_value and tick_size and sl_pips > 0:
                sl_in_ticks = sl_pips / tick_size
                lot = risk_amount / (sl_in_ticks * tick_value)
            else:
                lot = self.min_lot
        else:
            # Fallback heuristic for XAUUSD
            lot = risk_amount / (sl_pips * 10)

        lot = round(lot, 2)
        lot = max(self.min_lot, min(self.max_lot, lot))
        logger.debug(f"Lot size: {lot} (risk=${risk_amount:.2f}, sl_pips={sl_pips:.1f})")
        return lot
