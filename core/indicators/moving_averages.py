"""
Deterministic Moving Averages and Momentum indicators.
"""

from typing import List, Optional
import numpy as np
from core.models.candle import Bar
from core.models.indicators import TrendDirection


def compute_ema(prices: List[float], period: int) -> List[float]:
    """Calculate Exponential Moving Average."""
    if len(prices) < period:
        return [prices[-1]] if prices else [0.0]

    multiplier = 2.0 / (period + 1)
    ema_series = [float(np.mean(prices[:period]))]

    for price in prices[period:]:
        next_ema = (price - ema_series[-1]) * multiplier + ema_series[-1]
        ema_series.append(next_ema)

    return ema_series


def compute_rsi(bars: List[Bar], period: int = 14) -> float:
    """Calculate Relative Strength Index on completed bars."""
    completed = [b for b in bars if b.shift >= 1]
    if len(completed) < period + 1:
        return 50.0

    closes = [b.close for b in completed]
    deltas = np.diff(closes)

    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    avg_gain = float(np.mean(gains[:period]))
    avg_loss = float(np.mean(losses[:period]))

    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0.0:
        return 100.0
    rs = avg_gain / avg_loss
    return float(100.0 - (100.0 / (1.0 + rs)))


def determine_trend(bars: List[Bar], fast_period: int = 9, slow_period: int = 21) -> TrendDirection:
    """Determine trend direction using EMA crossover and price location on completed bars."""
    completed = [b for b in bars if b.shift >= 1]
    if len(completed) < slow_period:
        return TrendDirection.NEUTRAL

    closes = [b.close for b in completed]
    fast_ema = compute_ema(closes, fast_period)[-1]
    slow_ema = compute_ema(closes, slow_period)[-1]
    last_close = completed[-1].close

    if last_close > fast_ema and fast_ema > slow_ema:
        return TrendDirection.BULLISH
    elif last_close < fast_ema and fast_ema < slow_ema:
        return TrendDirection.BEARISH
    return TrendDirection.NEUTRAL
