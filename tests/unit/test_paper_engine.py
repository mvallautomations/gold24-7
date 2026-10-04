"""
Unit tests for PaperTradingEngine: lot sizing, simulated execution,
and bracket TP/SL hit handling.
"""

import pytest
from core.models.signal import SignalContract, SignalDirection, SetupType, VolatilityState
from core.models.trade import PositionSide, TradeStatus
from execution.paper.engine import PaperTradingEngine


def test_lot_size_calculation():
    engine = PaperTradingEngine(initial_balance=10000.0, risk_per_trade_pct=1.0)
    # $10,000 * 1% = $100 risk
    # Stop distance = $10 (1000 ticks on $0.01 tick)
    # 1000 * $1.0 tick value = $1000 loss per 1.0 lot
    # lots = $100 / $1000 = 0.10 lots
    lots = engine.calculate_lots(stop_distance=10.0, tick_size=0.01, tick_value=1.0)
    assert lots == 0.10


def test_paper_execution_and_tp_hit():
    engine = PaperTradingEngine(initial_balance=10000.0, risk_per_trade_pct=1.0, slippage_points=1.0)

    sig = SignalContract(
        symbol_requested="XAUUSD",
        symbol_resolved="GAUUSD",
        direction=SignalDirection.BUY,
        setup=SetupType.PULLBACK,
        entry_price=2650.0,
        stop_loss=2640.0,
        take_profit=2665.0,
        risk_reward_ratio=1.5,
        risk_points=10.0,
        volatility_state=VolatilityState.NORMAL,
    )

    pos = engine.execute_signal(sig, point=0.01, tick_size=0.01, tick_value=1.0)
    assert pos is not None
    assert pos.status == TradeStatus.OPEN
    assert pos.side == PositionSide.LONG
    assert len(engine.open_positions) == 1

    # Simulate price moving up and hitting TP (high hits 2666.0)
    closed = engine.on_price_update(
        symbol="GAUUSD",
        high=2666.0,
        low=2651.0,
        close=2665.0
    )

    assert len(closed) == 1
    assert closed[0].exit_reason == "TP_HIT"
    assert closed[0].realized_pnl > 0
    assert engine.balance > 10000.0
    assert len(engine.open_positions) == 0
