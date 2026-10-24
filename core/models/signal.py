"""
Canonical Signal Contract with hard safety boundaries.
Enforces that every signal is explicitly labeled SIMULATION_ONLY / PAPER.
"""

from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import uuid
from pydantic import BaseModel, Field
from core.models.indicators import VolatilityState, TrendDirection


class SignalDirection(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    NONE = "NONE"


class SetupType(str, Enum):
    PULLBACK = "PULLBACK"
    BREAKOUT = "BREAKOUT"
    REVERSAL = "REVERSAL"
    NONE = "NONE"


class MarketRegime(str, Enum):
    TRENDING = "TRENDING"
    RANGING = "RANGING"
    VOLATILE = "VOLATILE"
    UNCERTAIN = "UNCERTAIN"


class ValidationResult(BaseModel):
    is_valid: bool
    rejection_reason: Optional[str] = None
    passed_rules: List[str] = Field(default_factory=list)
    failed_rules: List[str] = Field(default_factory=list)
    risk_reward_ratio: float = 0.0
    risk_percentage: float = 1.0


class LLMInterpretation(BaseModel):
    confidence_score: float = Field(default=0.0, description="Confidence 0.0 to 1.0")
    reasoning: str = Field(default="", description="Hermes 3 contextual analysis")
    critique: str = Field(default="", description="Hermes 3 risk warnings and trade counter-arguments")
    recommended_action: str = Field(default="STAND_ASIDE", description="EXECUTE_LIVE | MITIGATE_LOSSES | PROTECT_CAPITAL | STAND_ASIDE | TRIM_EXPOSURE")
    loss_mitigation_plan: Optional[str] = Field(default=None, description="Tactical loss mitigation directives for open trades")
    psychological_check: str = Field(default="", description="ADHD/Emotional guardrail prompt")


class SignalContract(BaseModel):
    signal_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    environment: str = Field(default="PAPER", frozen=True)
    is_simulation_only: bool = Field(default=True, frozen=True)
    live_execution_permitted: bool = Field(default=False, frozen=True)

    symbol_requested: str
    symbol_resolved: str
    broker_name: str = "XM"

    direction: SignalDirection = SignalDirection.NONE
    setup: SetupType = SetupType.NONE
    market_regime: MarketRegime = MarketRegime.UNCERTAIN

    entry_price: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    risk_reward_ratio: float = 0.0
    risk_points: float = 0.0

    volatility_state: VolatilityState = VolatilityState.NORMAL
    higher_tf_bias: TrendDirection = TrendDirection.NEUTRAL
    mtf_confluence_score: float = 0.0  # 0.0 to 1.0 alignment

    # Shift clarity
    signal_candle_shift: int = 1  # Always shift 1 (closed bar)
    forming_bar_price: float = 0.0

    llm_interpretation: Optional[LLMInterpretation] = None
    deterministic_validation: Optional[ValidationResult] = None

    metadata: Dict[str, Any] = Field(default_factory=dict)
