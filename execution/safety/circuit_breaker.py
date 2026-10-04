"""
Safety Circuit Breaker: Tracks daily drawdowns, consecutive losses,
and enforces automated trading halt for the paper engine.
"""

from typing import List, Optional
from datetime import datetime, timezone, date
import logging

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """
    Enforces risk circuit breakers even during simulated/paper trading.
    Prevents unrealistic catastrophic martingale or runaway paper loss loops.
    """

    def __init__(
        self,
        max_daily_drawdown_pct: float = 3.0,
        max_consecutive_losses: int = 4,
        max_open_positions: int = 2
    ):
        self.max_daily_drawdown_pct = max_daily_drawdown_pct
        self.max_consecutive_losses = max_consecutive_losses
        self.max_open_positions = max_open_positions

        self.current_consecutive_losses: int = 0
        self.daily_pnl: float = 0.0
        self.is_tripped: bool = False
        self.trip_reason: Optional[str] = None
        self.last_reset_date: date = datetime.now(timezone.utc).date()

    def check_reset(self) -> None:
        today = datetime.now(timezone.utc).date()
        if today > self.last_reset_date:
            self.daily_pnl = 0.0
            self.current_consecutive_losses = 0
            self.is_tripped = False
            self.trip_reason = None
            self.last_reset_date = today
            logger.info("Circuit breaker daily metrics reset for new session.")

    def record_closed_trade(self, pnl: float) -> None:
        self.check_reset()
        self.daily_pnl += pnl

        if pnl < 0:
            self.current_consecutive_losses += 1
            if self.current_consecutive_losses >= self.max_consecutive_losses:
                self.is_tripped = True
                self.trip_reason = f"Max consecutive losses reached ({self.current_consecutive_losses})"
                logger.warning(f"CIRCUIT BREAKER TRIPPED: {self.trip_reason}")
        else:
            self.current_consecutive_losses = 0

    def can_open_position(self, current_open_count: int, balance: float) -> bool:
        self.check_reset()

        if self.is_tripped:
            return False

        if current_open_count >= self.max_open_positions:
            return False

        # Check daily drawdown limit
        if balance > 0:
            drawdown_pct = abs(min(0.0, self.daily_pnl)) / balance * 100.0
            if drawdown_pct >= self.max_daily_drawdown_pct:
                self.is_tripped = True
                self.trip_reason = f"Daily drawdown limit hit ({drawdown_pct:.2f}% >= {self.max_daily_drawdown_pct}%)"
                logger.warning(f"CIRCUIT BREAKER TRIPPED: {self.trip_reason}")
                return False

        return True
