"""
Deterministic Relative ATR & Volatility Assessment Engine.
Replaces naive 'ATR > 0' check with percentile-based historical distribution analysis.
"""

from typing import List, Optional
import numpy as np
from core.models.candle import Bar
from core.models.indicators import VolatilityState, ATRAssessment


class VolatilityEngine:
    """
    Computes instrument-agnostic relative ATR volatility.
    Works seamlessly across XAUUSD, BTCUSD, and FX pairs without hardcoded point thresholds.
    """

    def __init__(self, period: int = 14, lookback_window: int = 100):
        self.period = period
        self.lookback_window = lookback_window

    def compute_true_ranges(self, bars: List[Bar]) -> List[float]:
        """Compute True Range sequence across historical completed bars."""
        if not bars:
            return []

        tr_list = []
        for i in range(len(bars)):
            curr = bars[i]
            if i == 0:
                tr = curr.high - curr.low
            else:
                prev = bars[i - 1]
                tr = max(
                    curr.high - curr.low,
                    abs(curr.high - prev.close),
                    abs(curr.low - prev.close)
                )
            tr_list.append(tr)
        return tr_list

    def compute_atr_series(self, bars: List[Bar]) -> List[float]:
        """Compute Wilder's smoothed ATR series."""
        tr_list = self.compute_true_ranges(bars)
        if len(tr_list) < self.period:
            return [tr_list[-1]] if tr_list else [0.0]

        atr_series = []
        # Initial ATR is simple moving average of first N true ranges
        first_atr = float(np.mean(tr_list[:self.period]))
        atr_series.append(first_atr)

        running_atr = first_atr
        for tr in tr_list[self.period:]:
            running_atr = (running_atr * (self.period - 1) + tr) / self.period
            atr_series.append(running_atr)

        return atr_series

    def assess_volatility(self, bars: List[Bar]) -> ATRAssessment:
        """
        Evaluate current ATR against historical percentile distribution.
        Strictly analyzes COMPLETED bars (shift >= 1).
        """
        completed_bars = [b for b in bars if b.shift >= 1]
        if not completed_bars:
            completed_bars = bars

        atr_series = self.compute_atr_series(completed_bars)
        current_atr = atr_series[-1] if atr_series else 1.0

        # Take lookback slice for distribution
        dist_slice = atr_series[-self.lookback_window:] if len(atr_series) >= self.lookback_window else atr_series
        hist_mean = float(np.mean(dist_slice)) if dist_slice else current_atr
        hist_std = float(np.std(dist_slice)) if len(dist_slice) > 1 else 0.0

        # Percentile rank of current ATR within window
        if len(dist_slice) > 1:
            percentile = float(np.sum(np.array(dist_slice) <= current_atr) / len(dist_slice) * 100.0)
        else:
            percentile = 50.0

        ratio_to_mean = (current_atr / hist_mean) if hist_mean > 0 else 1.0

        # Map percentile to categorical volatility state
        if percentile < 15.0:
            state = VolatilityState.VERY_LOW
            is_tradable = False  # Spread compression risk / dead market
        elif percentile < 35.0:
            state = VolatilityState.LOW
            is_tradable = True
        elif percentile <= 75.0:
            state = VolatilityState.NORMAL
            is_tradable = True
        elif percentile <= 90.0:
            state = VolatilityState.HIGH
            is_tradable = True
        else:
            state = VolatilityState.EXTREME
            is_tradable = False  # Slippage / gap risk (breaking news, economic release)

        return ATRAssessment(
            current_atr=round(current_atr, 5),
            historical_mean=round(hist_mean, 5),
            historical_std=round(hist_std, 5),
            percentile=round(percentile, 2),
            ratio_to_mean=round(ratio_to_mean, 3),
            state=state,
            is_tradable=is_tradable
        )
