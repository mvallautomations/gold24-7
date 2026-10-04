"""
Contract tests verifying canonical JSON serialization and safety guarantees of SignalContract.
"""

import json
from core.models.signal import (
    SignalContract,
    SignalDirection,
    SetupType,
    MarketRegime,
    VolatilityState,
    LLMInterpretation,
    ValidationResult
)


def test_signal_contract_schema_compliance():
    sig = SignalContract(
        symbol_requested="XAUUSD",
        symbol_resolved="GAUUSD",
        broker_name="XM",
        direction=SignalDirection.BUY,
        setup=SetupType.PULLBACK,
        market_regime=MarketRegime.TRENDING,
        entry_price=2650.50,
        stop_loss=2645.50,
        take_profit=2658.00,
        risk_reward_ratio=1.5,
        risk_points=5.0,
        volatility_state=VolatilityState.NORMAL,
        signal_candle_shift=1,
        forming_bar_price=2651.20,
        llm_interpretation=LLMInterpretation(
            confidence_score=0.75,
            reasoning="Valid pullback following M1 bullish expansion.",
            critique="Spread widening risk near rollover.",
            recommended_action="ENTER_PAPER",
            psychological_check="Maintain discipline."
        ),
        deterministic_validation=ValidationResult(
            is_valid=True,
            passed_rules=["ENVIRONMENT_SAFETY_CHECK", "GEOMETRY_VALID"],
            failed_rules=[],
            risk_reward_ratio=1.5,
            risk_percentage=1.0
        )
    )

    # Serialize to JSON and parse back
    raw_json = sig.model_dump_json()
    data = json.loads(raw_json)

    # Mandatory fields
    assert "signal_id" in data
    assert "timestamp" in data
    assert data["environment"] == "PAPER"
    assert data["is_simulation_only"] is True
    assert data["live_execution_permitted"] is False
    assert data["symbol_requested"] == "XAUUSD"
    assert data["symbol_resolved"] == "GAUUSD"
    assert data["direction"] == "BUY"
    assert data["setup"] == "PULLBACK"
    assert data["signal_candle_shift"] == 1
    assert data["llm_interpretation"]["confidence_score"] == 0.75
    assert data["deterministic_validation"]["is_valid"] is True
