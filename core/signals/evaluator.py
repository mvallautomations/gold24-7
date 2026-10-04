"""
Deterministic Signal Evaluator: Applies explicit technical rules to classify setups
(PULLBACK, BREAKOUT, REVERSAL) with full BUY/SELL symmetry on closed candles.
"""

from typing import Optional, Dict, Any, List
from core.models.candle import Bar, Timeframe
from core.models.indicators import TrendDirection, VolatilityState
from core.models.signal import (
    SignalContract,
    SignalDirection,
    SetupType,
    MarketRegime,
)
from core.market.analyzer import MultiTimeframeMarketState, TimeframeAnalysis


class SignalEvaluator:
    """
    Evaluates market state for high-probability deterministic setups.
    Enforces completed-bar (shift 1) evaluation and symmetrical long/short rules.
    """

    def __init__(self, reward_ratio: float = 1.5, min_confluence: float = 0.5):
        self.reward_ratio = reward_ratio
        self.min_confluence = min_confluence

    def evaluate(self, state: MultiTimeframeMarketState) -> SignalContract:
        """
        Evaluate multi-timeframe state and produce a canonical SignalContract.
        """
        # Base contract initialized to NONE (safe default)
        contract = SignalContract(
            symbol_requested=state.symbol,
            symbol_resolved=state.symbol,
            broker_name=state.broker,
            direction=SignalDirection.NONE,
            setup=SetupType.NONE,
            market_regime=state.market_regime,
            higher_tf_bias=state.macro_bias,
            mtf_confluence_score=state.mtf_confluence_score,
            environment="PAPER",
            is_simulation_only=True,
            live_execution_permitted=False,
        )

        # 1. Volatility Envelope Check
        m1_analysis = state.timeframes.get("M1") or state.timeframes.get("M5")
        if not m1_analysis:
            return contract

        atr = m1_analysis.atr
        contract.volatility_state = atr.state

        if not atr.is_tradable:
            contract.metadata["rejection"] = f"Volatility {atr.state.value} is outside safe trading envelope"
            return contract

        # 2. Check Setups
        # Priority 1: M1/M5 Symmetrical Pullback (Benchmark strategy)
        pullback_sig = self._evaluate_symmetrical_pullback(state, m1_analysis)
        if pullback_sig:
            return pullback_sig

        # Priority 2: Key Level Breakout
        breakout_sig = self._evaluate_breakout(state, m1_analysis)
        if breakout_sig:
            return breakout_sig

        # Priority 3: S/R Zone Reversal
        reversal_sig = self._evaluate_reversal(state, m1_analysis)
        if reversal_sig:
            return reversal_sig

        return contract

    def _evaluate_symmetrical_pullback(
        self,
        state: MultiTimeframeMarketState,
        m1: Any
    ) -> Optional[SignalContract]:
        """
        Evaluates M1 pullback with full BUY and SELL symmetry on closed candle (shift 1).
        """
        curr = m1.completed_bar
        cs = m1.candle_structure
        atr_val = m1.atr.current_atr

        # Forming bar price for context
        forming_price = m1.forming_bar.close if m1.forming_bar else curr.close

        # A. Bullish Pullback Setup
        # Requires: Execution trend is BULLISH or macro is BULLISH, impulse up + shallow pullback
        if (state.macro_bias in [TrendDirection.BULLISH, TrendDirection.NEUTRAL]) and \
           (m1.trend in [TrendDirection.BULLISH, TrendDirection.NEUTRAL]):
            if cs.is_impulse and cs.is_pullback and curr.is_bullish:
                entry = curr.close
                # Stop loss: below current bar low or 1.2 * ATR
                sl_distance = max(curr.close - curr.low + (atr_val * 0.2), atr_val * 1.0)
                sl = entry - sl_distance
                tp = entry + (sl_distance * self.reward_ratio)

                return SignalContract(
                    symbol_requested=state.symbol,
                    symbol_resolved=state.symbol,
                    broker_name=state.broker,
                    direction=SignalDirection.BUY,
                    setup=SetupType.PULLBACK,
                    market_regime=state.market_regime,
                    entry_price=round(entry, 4),
                    stop_loss=round(sl, 4),
                    take_profit=round(tp, 4),
                    risk_reward_ratio=self.reward_ratio,
                    risk_points=round(sl_distance, 4),
                    volatility_state=m1.atr.state,
                    higher_tf_bias=state.macro_bias,
                    mtf_confluence_score=state.mtf_confluence_score,
                    signal_candle_shift=1,
                    forming_bar_price=round(forming_price, 4),
                    environment="PAPER",
                    is_simulation_only=True,
                    live_execution_permitted=False,
                    metadata={"pattern": "bullish_impulse_shallow_pullback"}
                )

        # B. Bearish Pullback Setup (SYMMETRICAL)
        # Requires: Execution trend is BEARISH or macro is BEARISH, impulse down + shallow pullback
        if (state.macro_bias in [TrendDirection.BEARISH, TrendDirection.NEUTRAL]) and \
           (m1.trend in [TrendDirection.BEARISH, TrendDirection.NEUTRAL]):
            if cs.is_impulse and cs.is_pullback and curr.is_bearish:
                entry = curr.close
                sl_distance = max(curr.high - curr.close + (atr_val * 0.2), atr_val * 1.0)
                sl = entry + sl_distance
                tp = entry - (sl_distance * self.reward_ratio)

                return SignalContract(
                    symbol_requested=state.symbol,
                    symbol_resolved=state.symbol,
                    broker_name=state.broker,
                    direction=SignalDirection.SELL,
                    setup=SetupType.PULLBACK,
                    market_regime=state.market_regime,
                    entry_price=round(entry, 4),
                    stop_loss=round(sl, 4),
                    take_profit=round(tp, 4),
                    risk_reward_ratio=self.reward_ratio,
                    risk_points=round(sl_distance, 4),
                    volatility_state=m1.atr.state,
                    higher_tf_bias=state.macro_bias,
                    mtf_confluence_score=state.mtf_confluence_score,
                    signal_candle_shift=1,
                    forming_bar_price=round(forming_price, 4),
                    environment="PAPER",
                    is_simulation_only=True,
                    live_execution_permitted=False,
                    metadata={"pattern": "bearish_impulse_shallow_pullback"}
                )

        return None

    def _evaluate_breakout(self, state: MultiTimeframeMarketState, m1: Any) -> Optional[SignalContract]:
        curr = m1.completed_bar
        atr_val = m1.atr.current_atr

        # Bullish Breakout above Resistance
        for r_zone in m1.resistance_zones:
            if curr.close > r_zone.high and curr.open <= r_zone.high:
                entry = curr.close
                sl = r_zone.low - (atr_val * 0.2)
                sl_distance = entry - sl
                tp = entry + (sl_distance * self.reward_ratio)

                return SignalContract(
                    symbol_requested=state.symbol,
                    symbol_resolved=state.symbol,
                    broker_name=state.broker,
                    direction=SignalDirection.BUY,
                    setup=SetupType.BREAKOUT,
                    market_regime=state.market_regime,
                    entry_price=round(entry, 4),
                    stop_loss=round(sl, 4),
                    take_profit=round(tp, 4),
                    risk_reward_ratio=self.reward_ratio,
                    risk_points=round(sl_distance, 4),
                    volatility_state=m1.atr.state,
                    higher_tf_bias=state.macro_bias,
                    mtf_confluence_score=state.mtf_confluence_score,
                    environment="PAPER",
                    is_simulation_only=True,
                    live_execution_permitted=False,
                    metadata={"broken_zone_low": r_zone.low, "broken_zone_high": r_zone.high}
                )

        return None

    def _evaluate_reversal(self, state: MultiTimeframeMarketState, m1: Any) -> Optional[SignalContract]:
        curr = m1.completed_bar
        atr_val = m1.atr.current_atr

        # Bullish Reversal at Strong Support (pin bar or lower rejection wick)
        for s_zone in m1.support_zones:
            if s_zone.contains(curr.low) and curr.lower_wick > (curr.body_range * 1.5) and curr.is_bullish:
                entry = curr.close
                sl = s_zone.low - (atr_val * 0.3)
                sl_distance = entry - sl
                tp = entry + (sl_distance * self.reward_ratio)

                return SignalContract(
                    symbol_requested=state.symbol,
                    symbol_resolved=state.symbol,
                    broker_name=state.broker,
                    direction=SignalDirection.BUY,
                    setup=SetupType.REVERSAL,
                    market_regime=state.market_regime,
                    entry_price=round(entry, 4),
                    stop_loss=round(sl, 4),
                    take_profit=round(tp, 4),
                    risk_reward_ratio=self.reward_ratio,
                    risk_points=round(sl_distance, 4),
                    volatility_state=m1.atr.state,
                    higher_tf_bias=state.macro_bias,
                    mtf_confluence_score=state.mtf_confluence_score,
                    environment="PAPER",
                    is_simulation_only=True,
                    live_execution_permitted=False,
                    metadata={"bounced_zone_strength": s_zone.strength}
                )

        return None
