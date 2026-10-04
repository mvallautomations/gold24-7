"""
Candle and timeframe data models with strict separation between
forming bar (shift 0) and completed bar (shift 1).
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class Timeframe(str, Enum):
    D1 = "D1"
    H4 = "H4"
    H1 = "H1"
    M15 = "M15"
    M5 = "M5"
    M1 = "M1"

    @property
    def minutes(self) -> int:
        mapping = {
            Timeframe.D1: 1440,
            Timeframe.H4: 240,
            Timeframe.H1: 60,
            Timeframe.M15: 15,
            Timeframe.M5: 5,
            Timeframe.M1: 1,
        }
        return mapping[self]


class BarShift(str, Enum):
    CURRENT_FORMING_BAR = "CURRENT_FORMING_BAR"  # Shift 0 (in-progress, incomplete)
    COMPLETED_BAR = "COMPLETED_BAR"              # Shift 1 (closed, mathematically finalized)


class Bar(BaseModel):
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    shift: int = 1
    shift_type: BarShift = BarShift.COMPLETED_BAR

    @property
    def is_bullish(self) -> bool:
        return self.close > self.open

    @property
    def is_bearish(self) -> bool:
        return self.close < self.open

    @property
    def body_range(self) -> float:
        return abs(self.close - self.open)

    @property
    def total_range(self) -> float:
        return self.high - self.low

    @property
    def upper_wick(self) -> float:
        return self.high - max(self.open, self.close)

    @property
    def lower_wick(self) -> float:
        return min(self.open, self.close) - self.low

    @property
    def mid_point(self) -> float:
        return (self.high + self.low) / 2.0


class CandleStructure(BaseModel):
    timeframe: Timeframe
    completed_bar: Bar
    forming_bar: Optional[Bar] = None
    is_impulse: bool = False
    is_pullback: bool = False
    pullback_depth: float = 0.0  # 0.0 to 1.0 of previous bar's range
