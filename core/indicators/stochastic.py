"""
Deterministic Stochastic Oscillator and EMA Alignment Engine.
Mirrors MetaTrader 5 iStochastic (14,3,3) and iMA (20, 50, 200).
"""

from typing import List, Dict, Any, Tuple
import numpy as np
from core.models.candle import Bar


def compute_stochastic(
    bars: List[Bar],
    k_period: int = 14,
    d_period: int = 3,
    slowing: int = 3
) -> Dict[str, Any]:
    """
    Calculate Stochastic Oscillator (%K and %D) on completed bars (shift >= 1).
    Matches MT5 iStochastic(Symbol, Period, 14, 3, 3, MODE_SMA, STO_LOWHIGH).
    """
    completed = [b for b in bars if b.shift >= 1]
    if len(completed) < k_period + slowing + d_period:
        return {
            "k": 50.0,
            "d": 50.0,
            "state": "MID-RANGE",
            "is_extreme_oversold": False,
            "is_extreme_overbought": False
        }

    highs = np.array([b.high for b in completed])
    lows = np.array([b.low for b in completed])
    closes = np.array([b.close for b in completed])

    # 1. Fast %K raw = 100 * (Close - LowestLow) / (HighestHigh - LowestLow)
    raw_k = []
    for i in range(k_period - 1, len(completed)):
        window_high = np.max(highs[i - k_period + 1 : i + 1])
        window_low = np.min(lows[i - k_period + 1 : i + 1])
        denom = window_high - window_low
        if denom == 0:
            raw_k.append(50.0)
        else:
            raw_k.append(100.0 * (closes[i] - window_low) / denom)

    if len(raw_k) < slowing:
        k_val = raw_k[-1] if raw_k else 50.0
        d_val = k_val
    else:
        # 2. Slowed %K = SMA of raw_k over slowing
        slowed_k = []
        for i in range(slowing - 1, len(raw_k)):
            slowed_k.append(float(np.mean(raw_k[i - slowing + 1 : i + 1])))

        k_val = slowed_k[-1] if slowed_k else 50.0

        # 3. %D = SMA of slowed_k over d_period
        if len(slowed_k) < d_period:
            d_val = k_val
        else:
            d_val = float(np.mean(slowed_k[-d_period:]))

    k_round = round(k_val, 2)
    d_round = round(d_val, 2)

    is_oversold = k_round <= 20.0
    is_overbought = k_round >= 80.0

    if is_overbought:
        state = "ABOVE 80 (Overbought Extreme)"
    elif is_oversold:
        state = "BELOW 20 (Oversold Extreme)"
    else:
        state = "MID-RANGE (20-80 Neutral)"

    return {
        "k": k_round,
        "d": d_round,
        "state": state,
        "is_extreme_oversold": is_oversold,
        "is_extreme_overbought": is_overbought
    }


def compute_ema_alignment(
    bars: List[Bar],
    fast_period: int = 20,
    slow_period: int = 50,
    trend_period: int = 200
) -> Dict[str, Any]:
    """
    Computes EMA 20, 50, 200 and matches GOLD_TrainingMonitorEA logic:
    BULLISH: Close > EMA20 > EMA50 > EMA200
    BEARISH: Close < EMA20 < EMA50 < EMA200
    MIXED: Otherwise
    """
    completed = [b for b in bars if b.shift >= 1]
    if not completed:
        return {
            "ema20": 0.0,
            "ema50": 0.0,
            "ema200": 0.0,
            "alignment": "INSUFFICIENT_DATA",
            "is_bullish": False,
            "is_bearish": False
        }

    closes = [b.close for b in completed]
    c = closes[-1]

    def ema(prices: List[float], period: int) -> float:
        if len(prices) < period:
            return float(np.mean(prices)) if prices else 0.0
        multiplier = 2.0 / (period + 1)
        val = float(np.mean(prices[:period]))
        for p in prices[period:]:
            val = (p - val) * multiplier + val
        return val

    e20 = round(ema(closes, fast_period), 2)
    e50 = round(ema(closes, slow_period), 2)
    e200 = round(ema(closes, trend_period), 2)

    if c > e20 and e20 > e50 and e50 > e200:
        alignment = "BULLISH EMA ALIGNMENT"
        is_bullish = True
        is_bearish = False
    elif c < e20 and e20 < e50 and e50 < e200:
        alignment = "BEARISH EMA ALIGNMENT"
        is_bullish = False
        is_bearish = True
    else:
        alignment = "MIXED / NO ALIGNMENT"
        is_bullish = False
        is_bearish = False

    return {
        "current_close": round(c, 2),
        "ema20": e20,
        "ema50": e50,
        "ema200": e200,
        "alignment": alignment,
        "is_bullish": is_bullish,
        "is_bearish": is_bearish
    }


def compute_swing_channels(
    bars: List[Bar],
    lookback: int = 180,
    left_bars: int = 3,
    right_bars: int = 3
) -> Dict[str, Any]:
    """
    Matches GOLD_AutoTrendChannel.mq5 swing point detection.
    Identifies confirmed Swing Highs (SH) and Swing Lows (SL).
    """
    completed = [b for b in bars if b.shift >= 1][-lookback:]
    if len(completed) < left_bars + right_bars + 2:
        return {"swing_highs": [], "swing_lows": []}

    swing_highs = []
    swing_lows = []

    for i in range(left_bars, len(completed) - right_bars):
        curr = completed[i]
        # Check swing high
        is_high = True
        for k in range(1, left_bars + 1):
            if curr.high <= completed[i - k].high:
                is_high = False
                break
        if is_high:
            for k in range(1, right_bars + 1):
                if curr.high < completed[i + k].high:
                    is_high = False
                    break
        if is_high:
            swing_highs.append({
                "time": curr.timestamp.isoformat(),
                "price": round(curr.high, 2),
                "label": "SH"
            })

        # Check swing low
        is_low = True
        for k in range(1, left_bars + 1):
            if curr.low >= completed[i - k].low:
                is_low = False
                break
        if is_low:
            for k in range(1, right_bars + 1):
                if curr.low > completed[i + k].low:
                    is_low = False
                    break
        if is_low:
            swing_lows.append({
                "time": curr.timestamp.isoformat(),
                "price": round(curr.low, 2),
                "label": "SL"
            })

    return {
        "swing_highs": swing_highs[-10:],
        "swing_lows": swing_lows[-10:],
        "last_swing_high": swing_highs[-1]["price"] if swing_highs else None,
        "last_swing_low": swing_lows[-1]["price"] if swing_lows else None,
    }
