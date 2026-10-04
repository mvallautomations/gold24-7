"""
Deterministic Multi-Regime Dataset Generator for Phase 2 Validation:
Constructs realistic multi-timeframe price series representing:
- Regime A: Strong Bullish
- Regime B: Strong Bearish
- Regime C: Sideways / Ranging Chop
- Regime D: High Volatility Expansion
- Regime E: Low Volatility Compression
- Regime F: Shock / Abnormal Volatility Discontinuity
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta, timezone
from enum import Enum
import numpy as np

from core.models.candle import Bar, BarShift, Timeframe


class MarketRegimeType(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    RANGING = "RANGING"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    LOW_VOLATILITY = "LOW_VOLATILITY"
    SHOCK = "SHOCK"


class RegimeDatasetGenerator:
    """
    Generates deterministic, mathematically reproducible multi-timeframe price series
    across distinct macroeconomic market regimes.
    """

    @staticmethod
    def generate_regime_bars(
        regime: MarketRegimeType,
        symbol: str = "GAUUSD",
        timeframe: Timeframe = Timeframe.M1,
        n_bars: int = 400,
        start_price: float = 2650.0,
        seed: int = 100
    ) -> List[Bar]:
        """
        Generate bar series tailored to specific structural regime properties.
        """
        np.random.seed(seed)
        bars: List[Bar] = []

        now = datetime.now(timezone.utc)
        current_time = now - timedelta(minutes=timeframe.minutes * n_bars)
        current_close = start_price

        for i in range(n_bars):
            shift = n_bars - 1 - i
            shift_type = BarShift.CURRENT_FORMING_BAR if shift == 0 else BarShift.COMPLETED_BAR

            # Default parameters
            drift = 0.0
            volatility = 1.0

            if regime == MarketRegimeType.BULLISH:
                # Upward trend with periodic shallow dips
                drift = 0.12 * (timeframe.minutes ** 0.5)
                volatility = 0.8 * (timeframe.minutes ** 0.5)
                # Pullback cycle every ~14 bars
                if (i % 14) in [11, 12]:
                    drift = -0.15 * (timeframe.minutes ** 0.5)

            elif regime == MarketRegimeType.BEARISH:
                # Downward trend with periodic shallow rallies
                drift = -0.12 * (timeframe.minutes ** 0.5)
                volatility = 0.8 * (timeframe.minutes ** 0.5)
                if (i % 14) in [11, 12]:
                    drift = 0.15 * (timeframe.minutes ** 0.5)

            elif regime == MarketRegimeType.RANGING:
                # Mean reverting sine wave around start_price
                cycle_pos = np.sin(i / 12.0)
                mean_pull = (start_price - current_close) * 0.1
                drift = mean_pull + (0.05 * cycle_pos)
                volatility = 0.6 * (timeframe.minutes ** 0.5)

            elif regime == MarketRegimeType.HIGH_VOLATILITY:
                # Volatility expansion: wide swings, high variance
                drift = 0.02 * np.sin(i / 20.0)
                volatility = 2.8 * (timeframe.minutes ** 0.5)

            elif regime == MarketRegimeType.LOW_VOLATILITY:
                # Volatility compression: very low ATR, tight wicks
                drift = 0.01 * np.cos(i / 30.0)
                volatility = 0.25 * (timeframe.minutes ** 0.5)

            elif regime == MarketRegimeType.SHOCK:
                # Sudden abnormal volatility discontinuity / flash crash & spike
                if i in range(150, 155):
                    drift = -3.5 * (timeframe.minutes ** 0.5)
                    volatility = 5.0 * (timeframe.minutes ** 0.5)
                elif i in range(155, 165):
                    drift = 2.0 * (timeframe.minutes ** 0.5)
                    volatility = 4.0 * (timeframe.minutes ** 0.5)
                else:
                    drift = 0.02
                    volatility = 0.9 * (timeframe.minutes ** 0.5)

            # Generate candle geometry
            open_p = current_close
            shock = np.random.normal(drift, volatility)
            close_p = open_p + shock

            wick_scale = volatility * 0.5
            upper_wick = abs(np.random.normal(0, wick_scale))
            lower_wick = abs(np.random.normal(0, wick_scale))

            high_p = max(open_p, close_p) + upper_wick
            low_p = min(open_p, close_p) - lower_wick

            # Decimal rounding according to symbol convention
            decimals = 2 if symbol == "XAUUSD" else (3 if symbol == "GAUUSD" else 2)

            bar = Bar(
                timestamp=current_time,
                open=round(open_p, decimals),
                high=round(high_p, decimals),
                low=round(low_p, decimals),
                close=round(close_p, decimals),
                volume=round(float(np.random.randint(150, 1200) * (volatility / 0.8)), 1),
                shift=shift,
                shift_type=shift_type
            )
            bars.append(bar)

            current_close = close_p
            current_time += timedelta(minutes=timeframe.minutes)

        return bars

    @classmethod
    def generate_multitimeframe_suite(
        cls,
        regime: MarketRegimeType,
        symbol: str = "GAUUSD",
        start_price: float = 2650.0,
        seed: int = 100
    ) -> Dict[Timeframe, List[Bar]]:
        """
        Generates aligned 6-timeframe suite for the specified regime.
        """
        return {
            Timeframe.D1: cls.generate_regime_bars(regime, symbol, Timeframe.D1, n_bars=80, start_price=start_price, seed=seed),
            Timeframe.H4: cls.generate_regime_bars(regime, symbol, Timeframe.H4, n_bars=100, start_price=start_price, seed=seed + 1),
            Timeframe.H1: cls.generate_regime_bars(regime, symbol, Timeframe.H1, n_bars=120, start_price=start_price, seed=seed + 2),
            Timeframe.M15: cls.generate_regime_bars(regime, symbol, Timeframe.M15, n_bars=160, start_price=start_price, seed=seed + 3),
            Timeframe.M5: cls.generate_regime_bars(regime, symbol, Timeframe.M5, n_bars=220, start_price=start_price, seed=seed + 4),
            Timeframe.M1: cls.generate_regime_bars(regime, symbol, Timeframe.M1, n_bars=350, start_price=start_price, seed=seed + 5),
        }
