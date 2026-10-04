"""
Unit tests for DeterministicValidator, Safety Guards, and Live Execution Blocker.
"""

import pytest
from core.models.signal import SignalContract, SignalDirection, SetupType, VolatilityState
from core.validation.validator import DeterministicValidator
from execution.live_disabled.live_blocker import LiveBrokerAdapterDisabled, LiveExecutionForbiddenError
from execution.safety.circuit_breaker import CircuitBreaker


def test_live_execution_blocker_fatal_exception():
    blocker = LiveBrokerAdapterDisabled()
    with pytest.raises(LiveExecutionForbiddenError) as exc_info:
        blocker.order_send()
    assert "Live order execution is permanently disabled" in str(exc_info.value)

    with pytest.raises(LiveExecutionForbiddenError):
        blocker.buy()

    with pytest.raises(LiveExecutionForbiddenError):
        blocker.sell()


def test_validator_rejects_live_environment():
    validator = DeterministicValidator()
    # Contract pretending to be live
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
    # Tamper with environment to test guard
    object.__setattr__(sig, "environment", "LIVE")

    result = validator.validate_signal(sig, current_spread_points=20, atr_value=5.0)
    assert not result.is_valid
    assert any("LIVE_EXECUTION_FORBIDDEN" in f for f in result.failed_rules)


def test_validator_bracket_geometry():
    validator = DeterministicValidator(min_risk_reward=1.2)

    # Inverted BUY brackets (SL higher than entry)
    sig_bad = SignalContract(
        symbol_requested="XAUUSD",
        symbol_resolved="GAUUSD",
        direction=SignalDirection.BUY,
        setup=SetupType.PULLBACK,
        entry_price=2650.0,
        stop_loss=2660.0,  # Invalid! SL > Entry
        take_profit=2670.0,
        risk_reward_ratio=1.5,
        risk_points=10.0,
        volatility_state=VolatilityState.NORMAL,
    )

    result = validator.validate_signal(sig_bad, current_spread_points=15, atr_value=5.0)
    assert not result.is_valid
    assert any("GEOMETRY_INVALID" in f for f in result.failed_rules)


def test_circuit_breaker_tripping():
    cb = CircuitBreaker(max_consecutive_losses=3, max_daily_drawdown_pct=2.0)

    assert cb.can_open_position(current_open_count=0, balance=10000.0)

    # Record 3 losses
    cb.record_closed_trade(-100.0)
    cb.record_closed_trade(-100.0)
    assert not cb.is_tripped

    cb.record_closed_trade(-100.0)
    assert cb.is_tripped
    assert not cb.can_open_position(current_open_count=0, balance=10000.0)
