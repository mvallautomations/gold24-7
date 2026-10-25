"""Unit tests for the multi-timeframe channel mapping engine."""

import math
from datetime import datetime, timedelta, timezone

from core.indicators.channels import (
    fit_channel,
    manual_channel,
    map_multi_timeframe_channels,
)
from core.models.candle import Bar, BarShift


def _channel_bars(n=100, slope=-6.0, start=4700.0, half_width=90.0, step=timedelta(days=1), wave=10):
    """Bars oscillating between two parallel rails (sine wave with period `wave`)."""
    t0 = datetime(2026, 6, 1, tzinfo=timezone.utc)
    bars = []
    for i in range(n):
        centre = start + slope * i
        swing = math.sin(2 * math.pi * i / wave) * half_width * 0.8
        close = centre + swing
        bars.append(
            Bar(
                timestamp=t0 + step * i,
                open=close - 3,
                high=close + 12,
                low=close - 12,
                close=close,
                shift=n - 1 - i,
                shift_type=BarShift.CURRENT_FORMING_BAR if i == n - 1 else BarShift.COMPLETED_BAR,
            )
        )
    return bars


def test_fit_descending_channel():
    ch = fit_channel("D1", _channel_bars())
    assert ch is not None
    assert ch["direction"] == "DESCENDING"
    assert ch["slope_per_bar"] < 0
    now = ch["now"]
    assert now["lower"] < now["mid"] < now["upper"]
    assert ch["touches"]["upper"] >= 2 and ch["touches"]["lower"] >= 1
    # rails are parallel in every exported projection point
    up, lo = ch["lines"]["upper"], ch["lines"]["lower"]
    gaps = [round(u["price"] - l["price"], 1) for u, l in zip(up, lo)]
    assert len(set(gaps)) == 1


def test_fit_ascending_channel():
    ch = fit_channel("H4", _channel_bars(slope=5.0, start=3000.0, step=timedelta(hours=4)))
    assert ch is not None
    assert ch["direction"] == "ASCENDING"


def test_flat_data_without_swings_returns_none():
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    bars = [
        Bar(timestamp=t0 + timedelta(days=i), open=100, high=101, low=99, close=100, shift=29 - i)
        for i in range(30)
    ]
    assert fit_channel("D1", bars) is None


def test_manual_channel_clones_parallel_rail():
    bars = _channel_bars()
    t = [int(b.timestamp.timestamp()) for b in bars]
    override = {
        "a1": {"time": t[10], "price": 4700 - 60 + 140},
        "a2": {"time": t[50], "price": 4700 - 300 + 140},
        "opposite": {"time": t[30], "price": 4700 - 180 - 60},
    }
    ch = manual_channel("D1", bars, override)
    assert ch is not None
    assert ch["source"] == "MANUAL"
    assert ch["primary_side"] == "upper"
    assert ch["now"]["upper"] > ch["now"]["lower"]


def test_multi_timeframe_map_has_alignment_zones_and_guide():
    tf_bars = {
        "D1": _channel_bars(),
        "H4": _channel_bars(slope=-1.5, half_width=30, step=timedelta(hours=4)),
        "H1": _channel_bars(slope=1.0, half_width=12, step=timedelta(hours=1)),
    }
    result = map_multi_timeframe_channels(tf_bars)
    assert set(result["channels"]) == {"D1", "H4", "H1"}
    assert result["alignment"]["macro_direction"] == "DESCENDING"
    relations = {(r["parent"], r["child"]): r["relation"] for r in result["alignment"]["relations"]}
    assert relations[("H4", "H1")] == "COUNTER_TREND_PULLBACK"
    assert result["guide"]["steps"] and result["guide"]["scenarios"]
    for z in result["confluence_zones"]:
        assert z["low"] <= z["center"] <= z["high"]
        assert len(z["sources"]) >= 2


def test_overrides_are_used_per_timeframe():
    bars = _channel_bars()
    t = [int(b.timestamp.timestamp()) for b in bars]
    override = {
        "D1": {
            "a1": {"time": t[10], "price": 4780.0},
            "a2": {"time": t[50], "price": 4540.0},
            "opposite": {"time": t[30], "price": 4460.0},
        }
    }
    result = map_multi_timeframe_channels({"D1": bars}, overrides=override)
    assert result["channels"]["D1"]["source"] == "MANUAL"
