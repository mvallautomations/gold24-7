"""
Unit tests for Stochastic, Checklist Engine, and Experts Catalog.
"""

from datetime import datetime, timezone
import pytest
from core.models.candle import Bar, Timeframe
from core.indicators.stochastic import compute_stochastic, compute_ema_alignment, compute_swing_channels
from core.checklist.engine import ChecklistEngine
from core.experts.catalog import get_experts_catalog, get_indicators_catalog, get_strategy_setups_to_test


def test_stochastic_calculation():
    bars = []
    base_time = datetime(2026, 10, 21, 12, 0, tzinfo=timezone.utc)
    for i in range(30):
        price = 4100.0 + (i % 5) * 2.0
        bars.append(Bar(
            timestamp=base_time,
            open=price,
            high=price + 2.0,
            low=price - 1.0,
            close=price + 1.0,
            volume=100.0,
            timeframe=Timeframe.M1,
            shift=1
        ))

    stoch = compute_stochastic(bars, k_period=14, d_period=3, slowing=3)
    assert "k" in stoch
    assert "d" in stoch
    assert 0.0 <= stoch["k"] <= 100.0
    assert 0.0 <= stoch["d"] <= 100.0


def test_ema_alignment():
    bars = []
    base_time = datetime(2026, 10, 21, 12, 0, tzinfo=timezone.utc)
    # Strongly upward trending bars
    for i in range(250):
        price = 4000.0 + i * 2.0
        bars.append(Bar(
            timestamp=base_time,
            open=price,
            high=price + 3.0,
            low=price - 1.0,
            close=price + 2.0,
            volume=100.0,
            timeframe=Timeframe.M1,
            shift=1
        ))

    align = compute_ema_alignment(bars, 20, 50, 200)
    assert align["is_bullish"] is True
    assert align["alignment"] == "BULLISH EMA ALIGNMENT"


def test_checklist_engine():
    engine = ChecklistEngine()
    account_stats = {
        "company": "XM Global Limited",
        "balance": 1874.19,
        "equity": 1874.19,
        "leverage": 100,
        "is_demo": True,
        "server": "XMGlobal-MT5 9",
        "open_positions_count": 0
    }
    resolution = {
        "resolved": "GOLD#",
        "broker": "XM",
        "spread_points": 30,
        "digits": 2,
        "tick_size": 0.01
    }

    eval_result = engine.evaluate_live_status(account_stats, resolution)
    assert len(eval_result["template"]) == 8
    assert eval_result["auto_evaluations"]["is_demo"]["passed"] is True
    assert eval_result["auto_evaluations"]["spread_check"]["passed"] is True


def test_catalog_retrieval():
    experts = get_experts_catalog()
    assert len(experts) == 4
    indicators = get_indicators_catalog()
    assert len(indicators) == 2
    setups = get_strategy_setups_to_test()
    assert len(setups) == 4
