"""
Deterministic indicator data models with relative ATR volatility assessment.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class VolatilityState(str, Enum):
    VERY_LOW = "VERY_LOW"
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    EXTREME = "EXTREME"


class TrendDirection(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class ATRAssessment(BaseModel):
    current_atr: float = Field(..., description="Current ATR value in points/price units")
    historical_mean: float = Field(..., description="Rolling historical mean ATR")
    historical_std: float = Field(default=0.0, description="Standard deviation of ATR")
    percentile: float = Field(..., description="Current ATR rank (0.0 to 100.0) relative to history")
    ratio_to_mean: float = Field(..., description="current_atr / historical_mean")
    state: VolatilityState = Field(..., description="Categorical volatility assessment")
    is_tradable: bool = Field(default=True, description="Whether volatility is within safe trading envelope")


class IndicatorSummary(BaseModel):
    ema_fast: Optional[float] = None
    ema_slow: Optional[float] = None
    rsi: Optional[float] = None
    atr: ATRAssessment
    trend: TrendDirection
    swing_high: Optional[float] = None
    swing_low: Optional[float] = None
