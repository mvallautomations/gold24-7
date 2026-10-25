"""Snapshot validator defaults before intentional risk-rule changes."""

import pytest

from core.models.signal import SignalContract, SignalDirection, SetupType
from core.validation.validator import DeterministicValidator


@pytest.mark.parametrize(
    ("risk_reward_ratio", "expected_valid"),
    [
        (1.0, False),
        (1.2, True),
        (1.5, True),
        (2.0, True),
        (3.0, True),
        (5.5, False),
    ],
)
def test_current_risk_reward_acceptance(risk_reward_ratio, expected_valid):
    signal = SignalContract(
        symbol_requested="XAUUSD",
        symbol_resolved="GOLD#",
        direction=SignalDirection.BUY,
        setup=SetupType.PULLBACK,
        entry_price=100.0,
        stop_loss=99.0,
        take_profit=100.0 + risk_reward_ratio,
        risk_reward_ratio=risk_reward_ratio,
    )

    result = DeterministicValidator().validate_signal(signal, atr_value=1.0)

    assert result.is_valid is expected_valid
    if risk_reward_ratio == 1.0:
        assert any("RISK_REWARD_SUBPAR" in rule for rule in result.failed_rules)
    elif risk_reward_ratio == 5.5:
        assert any("RISK_REWARD_UNREALISTIC" in rule for rule in result.failed_rules)
    else:
        assert any("RISK_REWARD_CHECK" in rule for rule in result.passed_rules)


@pytest.mark.parametrize(
    ("spread_points", "expected_valid"),
    [(30, True), (60, False)],
)
def test_current_spread_acceptance(spread_points, expected_valid):
    signal = SignalContract(
        symbol_requested="XAUUSD",
        symbol_resolved="GOLD#",
        direction=SignalDirection.BUY,
        setup=SetupType.PULLBACK,
        entry_price=100.0,
        stop_loss=99.0,
        take_profit=101.5,
        risk_reward_ratio=1.5,
    )

    result = DeterministicValidator().validate_signal(
        signal,
        current_spread_points=spread_points,
        atr_value=1.0,
    )

    assert result.is_valid is expected_valid
    if spread_points == 60:
        assert any("SPREAD_TOO_HIGH" in rule for rule in result.failed_rules)
    else:
        assert any("SPREAD_CHECK" in rule for rule in result.passed_rules)
