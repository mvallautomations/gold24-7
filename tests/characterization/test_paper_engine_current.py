"""Snapshot current paper-engine defaults and bracket P&L."""

import pytest

from core.models.signal import SignalContract, SignalDirection, SetupType
from core.models.trade import TradeStatus
from execution.paper.engine import PaperTradingEngine


def test_default_initial_balance_is_10000():
    assert PaperTradingEngine().initial_balance == 10000.0


def test_explicit_initial_balance_10000():
    assert PaperTradingEngine(initial_balance=10000.0).initial_balance == 10000.0


def test_explicit_initial_balance_500():
    assert PaperTradingEngine(initial_balance=500.0).initial_balance == 500.0


@pytest.mark.parametrize(
    ("exit_reason", "high", "low", "expected_pnl"),
    [
        ("SL_HIT", 2650.5, 2640.0, -100.45),
        ("TP_HIT", 2665.0, 2650.5, 149.55),
    ],
)
def test_current_bracket_exit_pnl(exit_reason, high, low, expected_pnl):
    engine = PaperTradingEngine(slippage_points=1.0)
    signal = SignalContract(
        symbol_requested="XAUUSD",
        symbol_resolved="GAUUSD",
        direction=SignalDirection.BUY,
        setup=SetupType.PULLBACK,
        entry_price=2650.0,
        stop_loss=2640.0,
        take_profit=2665.0,
        risk_reward_ratio=1.5,
        risk_points=10.0,
    )

    position = engine.execute_signal(signal, point=0.01, tick_size=0.01, tick_value=1.0)
    assert position is not None

    closed = engine.on_price_update(
        symbol="GAUUSD",
        high=high,
        low=low,
        close=2650.0,
    )

    assert len(closed) == 1
    assert closed[0].status == TradeStatus.CLOSED
    assert closed[0].exit_reason == exit_reason
    assert closed[0].realized_pnl == expected_pnl
