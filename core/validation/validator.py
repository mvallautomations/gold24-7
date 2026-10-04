"""
Deterministic Validator: Final hard mathematical gate before paper execution.
Enforces the fundamental architectural law:
"The LLM interprets. Deterministic code calculates and validates."
"""

from typing import List, Optional
from core.models.signal import SignalContract, SignalDirection, ValidationResult, VolatilityState


class DeterministicValidator:
    """
    Independent validation gate.
    Hermes (or any LLM) cannot bypass these rules or invent prices.
    """

    def __init__(
        self,
        min_risk_reward: float = 1.2,
        max_risk_reward: float = 5.0,
        max_spread_points: int = 50,
        min_atr_multiplier: float = 0.5,
        max_atr_multiplier: float = 4.0,
        max_account_risk_pct: float = 1.0,
    ):
        self.min_risk_reward = min_risk_reward
        self.max_risk_reward = max_risk_reward
        self.max_spread_points = max_spread_points
        self.min_atr_multiplier = min_atr_multiplier
        self.max_atr_multiplier = max_atr_multiplier
        self.max_account_risk_pct = max_account_risk_pct

    def validate_signal(
        self,
        signal: SignalContract,
        current_spread_points: int = 15,
        atr_value: float = 1.0,
        has_open_position: bool = False
    ) -> ValidationResult:
        """
        Run 10-point deterministic safety audit on signal contract.
        """
        passed_rules: List[str] = []
        failed_rules: List[str] = []

        # Rule 1: Hard Environment Guard (Safety Boundary)
        if signal.environment != "PAPER" or not signal.is_simulation_only or signal.live_execution_permitted:
            failed_rules.append("LIVE_EXECUTION_FORBIDDEN: Signal must be strictly PAPER / SIMULATION_ONLY")
        else:
            passed_rules.append("ENVIRONMENT_SAFETY_CHECK: Validated PAPER environment")

        # Rule 2: Active Direction Check
        if signal.direction == SignalDirection.NONE:
            failed_rules.append("NO_DIRECTION: Signal direction is NONE")
        else:
            passed_rules.append(f"DIRECTION_CHECK: Valid direction {signal.direction.value}")

        # Rule 3: Single Position Constraint (Anti-Stacking)
        if has_open_position:
            failed_rules.append("CONCURRENT_POSITION_LIMIT: An open position already exists on this instrument")
        else:
            passed_rules.append("POSITION_LIMIT_CHECK: No duplicate position open")

        # Rule 4: Spread Filter
        if current_spread_points > self.max_spread_points:
            failed_rules.append(f"SPREAD_TOO_HIGH: Current spread {current_spread_points} > max {self.max_spread_points}")
        else:
            passed_rules.append(f"SPREAD_CHECK: Spread {current_spread_points} points acceptable")

        # Rule 5: Volatility Regime Gate
        if signal.volatility_state == VolatilityState.EXTREME:
            failed_rules.append("VOLATILITY_HAZARD: Volatility state is EXTREME (news event / slippage risk)")
        elif signal.volatility_state == VolatilityState.VERY_LOW:
            failed_rules.append("VOLATILITY_CHOP: Volatility state is VERY_LOW (spread cost exceeds expected range)")
        else:
            passed_rules.append(f"VOLATILITY_CHECK: Volatility state {signal.volatility_state.value} tradable")

        # Rule 6: Mathematical Direction Symmetry & Bracket Geometry
        if signal.direction == SignalDirection.BUY:
            if signal.stop_loss >= signal.entry_price:
                failed_rules.append(f"GEOMETRY_INVALID: BUY stop loss ({signal.stop_loss}) >= entry ({signal.entry_price})")
            if signal.take_profit <= signal.entry_price:
                failed_rules.append(f"GEOMETRY_INVALID: BUY take profit ({signal.take_profit}) <= entry ({signal.entry_price})")
        elif signal.direction == SignalDirection.SELL:
            if signal.stop_loss <= signal.entry_price:
                failed_rules.append(f"GEOMETRY_INVALID: SELL stop loss ({signal.stop_loss}) <= entry ({signal.entry_price})")
            if signal.take_profit >= signal.entry_price:
                failed_rules.append(f"GEOMETRY_INVALID: SELL take profit ({signal.take_profit}) >= entry ({signal.entry_price})")

        # Rule 7: Risk-Reward Ratio Envelope
        actual_rr = signal.risk_reward_ratio
        if actual_rr < self.min_risk_reward:
            failed_rules.append(f"RISK_REWARD_SUBPAR: R:R {actual_rr:.2f} < minimum required {self.min_risk_reward}")
        elif actual_rr > self.max_risk_reward:
            failed_rules.append(f"RISK_REWARD_UNREALISTIC: R:R {actual_rr:.2f} > maximum plausible {self.max_risk_reward}")
        else:
            passed_rules.append(f"RISK_REWARD_CHECK: R:R {actual_rr:.2f} within [{self.min_risk_reward}, {self.max_risk_reward}]")

        # Rule 8: Stop Loss Distance vs ATR
        sl_dist = abs(signal.entry_price - signal.stop_loss)
        if atr_value > 0:
            atr_ratio = sl_dist / atr_value
            if atr_ratio < self.min_atr_multiplier:
                failed_rules.append(f"STOP_LOSS_TOO_TIGHT: SL distance ({sl_dist:.4f}) is {atr_ratio:.2f}x ATR < {self.min_atr_multiplier}x")
            elif atr_ratio > self.max_atr_multiplier:
                failed_rules.append(f"STOP_LOSS_TOO_LOOSE: SL distance ({sl_dist:.4f}) is {atr_ratio:.2f}x ATR > {self.max_atr_multiplier}x")
            else:
                passed_rules.append(f"STOP_DISTANCE_CHECK: Stop loss {atr_ratio:.2f}x ATR within envelope")

        # Rule 9: LLM Override Veto (Hermes Interpretation Safeguard)
        if signal.llm_interpretation:
            # If LLM recommended SKIP or confidence is low, require human / watch state
            if signal.llm_interpretation.recommended_action == "SKIP" or signal.llm_interpretation.confidence_score < 0.20:
                failed_rules.append(f"LLM_VETO: Hermes 3 flagged setup as high-risk/skip (confidence: {signal.llm_interpretation.confidence_score})")
            else:
                passed_rules.append("LLM_CONSENSUS: Hermes 3 commentary aligned with technical criteria")

        # Final verdict
        is_valid = len(failed_rules) == 0
        rejection_reason = "; ".join(failed_rules) if not is_valid else None

        result = ValidationResult(
            is_valid=is_valid,
            rejection_reason=rejection_reason,
            passed_rules=passed_rules,
            failed_rules=failed_rules,
            risk_reward_ratio=actual_rr,
            risk_percentage=self.max_account_risk_pct,
        )

        signal.deterministic_validation = result
        return result
