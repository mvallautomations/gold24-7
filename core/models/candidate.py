"""
Candidate Setup Journaling Models: Captures every market observation, candidate setup,
validator decision (TRADE vs NO_TRADE), reason, and eventual counterfactual outcome.
"""

from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import uuid
from pydantic import BaseModel, Field

from core.models.signal import SignalDirection, SetupType, MarketRegime, ValidationResult
from core.models.indicators import VolatilityState, TrendDirection


class DecisionType(str, Enum):
    TRADE = "TRADE"
    NO_TRADE = "NO_TRADE"


class CounterfactualOutcome(str, Enum):
    GOOD_NO_TRADE = "GOOD_NO_TRADE"          # Hypothetical setup would have hit SL (good avoidance)
    MISSED_OPPORTUNITY = "MISSED_OPPORTUNITY"  # Hypothetical setup would have hit TP (bad avoidance)
    INCONCLUSIVE_NO_TRADE = "INCONCLUSIVE_NO_TRADE"  # Neither hit before horizon expiry
    EXECUTED = "EXECUTED"                    # Trade was executed in paper engine
    PENDING = "PENDING"


class CandidateSetup(BaseModel):
    """
    Every candidate setup detected by the market evaluator, whether traded or rejected.
    Enforces complete auditability of both positive signals and filter decisions.
    """
    candidate_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    instrument: str
    broker: str = "XM"
    timeframe: str = "M1"
    
    setup_detected: bool = True
    setup_type: SetupType = SetupType.NONE
    direction: SignalDirection = SignalDirection.NONE
    decision: DecisionType = DecisionType.NO_TRADE
    rejection_reasons: List[str] = Field(default_factory=list)
    
    # Context snapshots at decision time
    market_regime: MarketRegime = MarketRegime.UNCERTAIN
    higher_timeframe_bias: TrendDirection = TrendDirection.NEUTRAL
    mtf_confluence_score: float = 0.0
    volatility_state: VolatilityState = VolatilityState.NORMAL
    
    # Candidate trade parameters
    entry_price: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    risk_points: float = 0.0
    risk_reward_ratio: float = 0.0
    signal_shift: int = 1
    
    # Counterfactual evaluation (what happened if NO_TRADE was taken)
    eventual_outcome: CounterfactualOutcome = CounterfactualOutcome.PENDING
    hypothetical_r_multiple: Optional[float] = None
    outcome_evaluated_at_bar: Optional[int] = None
    
    # Hermes commentary
    hermes_action: Optional[str] = None
    hermes_confidence: Optional[float] = None
    
    metadata: Dict[str, Any] = Field(default_factory=dict)
