"""
Unit tests for deterministic indicators: Relative ATR, S&R zones, and moving averages.
"""

import pytest
from datetime import datetime, timezone, timedelta
from core.models.candle import Bar, Timeframe, BarShift
from core.models.indicators import VolatilityState, TrendDirection
from core.models.zones import ZoneType
from core.indicators.volatility import VolatilityEngine
from core.indicators.zones import SupportResistanceEngine
from core.indicators.moving_averages import compute_ema, compute_rsi, determine_trend
from backtest.datasets.data_generator import MarketDataGenerator


def test_volatility_engine_relative_atr():
    bars = MarketDataGenerator.generate_bars(symbol="GAUUSD", timeframe=Timeframe.M1, n_bars=150, base_volatility=1.0)
    engine = VolatilityEngine(period=14, lookback_window=100)

    assessment = engine.assess_volatility(bars)
    assert assessment.current_atr > 0
    assert 0.0 <= assessment.percentile <= 100.0
    assert assessment.state in [
        VolatilityState.VERY_LOW,
        VolatilityState.LOW,
        VolatilityState.NORMAL,
        VolatilityState.HIGH,
        VolatilityState.EXTREME,
    ]
    # Ratio to historical mean should be finite and positive
    assert assessment.ratio_to_mean > 0


def test_support_resistance_zones():
    bars = MarketDataGenerator.generate_bars(symbol="GAUUSD", timeframe=Timeframe.H1, n_bars=120, base_volatility=2.5)
    sr_engine = SupportResistanceEngine(swing_window=3, cluster_tolerance_pct=0.002)

    zones = sr_engine.build_zones(bars, Timeframe.H1, atr=2.5)
    assert len(zones) > 0

    for z in zones:
        assert z.low <= z.high
        assert z.strength >= 1.0
        assert z.touches >= 1
        assert z.type in [ZoneType.SUPPORT, ZoneType.RESISTANCE]


def test_moving_averages_and_trend():
    # Build clearly uptrending bars
    bars = []
    base_p = 100.0
    now = datetime.now(timezone.utc)
    for i in range(40):
        base_p += 1.5
        bars.append(Bar(
            timestamp=now + timedelta(minutes=i),
            open=base_p - 1.0,
            high=base_p + 1.0,
            low=base_p - 1.2,
            close=base_p,
            volume=500,
            shift=40 - 1 - i,
            shift_type=BarShift.COMPLETED_BAR
        ))

    trend = determine_trend(bars, fast_period=9, slow_period=21)
    assert trend == TrendDirection.BULLISH

    rsi = compute_rsi(bars, 14)
    assert rsi > 50.0  # Strong uptrend should have elevated RSI
