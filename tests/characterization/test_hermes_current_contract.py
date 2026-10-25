"""Snapshot the current Hermes system prompt and interpreter response keys."""

import hashlib
import json

from agents.analyzer.interpreter import HermesMarketInterpreter, SYSTEM_PROMPT
from core.models.signal import (
    LLMInterpretation,
    MarketRegime,
    SetupType,
    SignalContract,
    SignalDirection,
    VolatilityState,
)


class StubHermesClient:
    def __init__(self, response):
        self.response = response
        self.system_prompt = None

    def generate_response_sync(self, prompt, system_prompt=None):
        self.system_prompt = system_prompt
        return self.response


def test_current_prompt_hash_and_interpreter_response_schema():
    assert hashlib.sha256(SYSTEM_PROMPT.encode("utf-8")).hexdigest() == (
        "229cf019a6b064f9911cf73cc327568a944c8f09cf585c531f3410ee38d29d43"
    )

    expected_keys = {
        "confidence_score",
        "reasoning",
        "critique",
        "recommended_action",
        "loss_mitigation_plan",
        "psychological_check",
    }
    client = StubHermesClient(
        json.dumps(
            {
                "confidence_score": 0.8,
                "reasoning": "Aligned trend and pullback.",
                "critique": "Volatility may expand.",
                "recommended_action": "PROTECT_CAPITAL",
                "loss_mitigation_plan": "Honor the predefined stop.",
                "psychological_check": "Follow the plan.",
            }
        )
    )
    interpreter = HermesMarketInterpreter(client=client)
    signal = SignalContract(
        symbol_requested="XAUUSD",
        symbol_resolved="GOLD#",
        direction=SignalDirection.BUY,
        setup=SetupType.PULLBACK,
        market_regime=MarketRegime.TRENDING,
        entry_price=2650.0,
        stop_loss=2649.0,
        take_profit=2651.5,
        risk_reward_ratio=1.5,
        volatility_state=VolatilityState.NORMAL,
    )

    result = interpreter.interpret_signal(signal, state=None)

    assert isinstance(result, LLMInterpretation)
    assert set(result.model_dump()) == expected_keys
    assert result.recommended_action == "PROTECT_CAPITAL"
    assert client.system_prompt == SYSTEM_PROMPT
