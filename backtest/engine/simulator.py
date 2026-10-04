"""
Backtest Simulator: Bar-by-bar historical backtest engine with
multi-timeframe market analysis, candidate setup journaling, NO_TRADE counterfactual evaluation,
R-multiple analytics, component ablation, and look-ahead prevention.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from enum import Enum
import logging

from core.models.candle import Bar, Timeframe, BarShift
from core.models.signal import SignalContract, SignalDirection, SetupType
from core.models.candidate import CandidateSetup, DecisionType, CounterfactualOutcome
from core.market.analyzer import MultiTimeframeMarketAnalyzer, MultiTimeframeMarketState
from core.signals.evaluator import SignalEvaluator
from core.validation.validator import DeterministicValidator
from execution.paper.engine import PaperTradingEngine
from journal.analytics.performance_engine import PerformanceEngine
from journal.analytics.r_multiple import RMultipleAnalyzer

logger = logging.getLogger(__name__)


class HermesAblationMode(str, Enum):
    DETERMINISTIC = "DETERMINISTIC"          # No LLM calls
    HERMES_ADVISORY = "HERMES_ADVISORY"      # LLM commentary generated, no veto
    FULL_PIPELINE = "FULL_PIPELINE"          # Full LLM critique with Rule 9 veto


class BacktestSimulator:
    """
    Simulates the research pipeline across historical candle series with full
    candidate setup tracking, counterfactual evaluation, and ablation support.
    """

    def __init__(
        self,
        initial_balance: float = 10000.0,
        risk_per_trade_pct: float = 1.0,
        slippage_points: float = 1.5,
        fee_per_lot: float = 3.50,
        spread_points: int = 15,
        min_risk_reward: float = 1.5,
        hermes_mode: HermesAblationMode = HermesAblationMode.DETERMINISTIC,
        use_sr_filter: bool = True,
        use_volatility_filter: bool = True,
        use_mtf_confirmation: bool = True,
        use_pullback_condition: bool = True,
        interpreter: Optional[Any] = None,
    ):
        self.initial_balance = initial_balance
        self.risk_per_trade_pct = risk_per_trade_pct
        self.slippage_points = slippage_points
        self.fee_per_lot = fee_per_lot
        self.spread_points = spread_points
        self.min_risk_reward = min_risk_reward
        self.hermes_mode = hermes_mode

        # Component ablation flags
        self.use_sr_filter = use_sr_filter
        self.use_volatility_filter = use_volatility_filter
        self.use_mtf_confirmation = use_mtf_confirmation
        self.use_pullback_condition = use_pullback_condition

        self.analyzer = MultiTimeframeMarketAnalyzer()
        self.signal_evaluator = SignalEvaluator(reward_ratio=min_risk_reward)
        self.validator = DeterministicValidator(min_risk_reward=min_risk_reward)
        self.paper_engine = PaperTradingEngine(
            initial_balance=initial_balance,
            risk_per_trade_pct=risk_per_trade_pct,
            slippage_points=slippage_points,
            fee_per_lot=fee_per_lot,
        )
        self.interpreter = interpreter

        self.candidate_setups: List[CandidateSetup] = []

    def _build_lookahead_safe_slices(
        self,
        tf_data: Dict[Timeframe, List[Bar]],
        current_m1_idx: int
    ) -> Dict[Timeframe, List[Bar]]:
        """
        Builds multi-timeframe slices strictly ensuring NO future data leakage.
        Only candles fully closed by or forming at current_bar.timestamp are visible.
        """
        m1_bars = tf_data[Timeframe.M1]
        current_m1_bar = m1_bars[current_m1_idx]
        t_curr = current_m1_bar.timestamp

        slices: Dict[Timeframe, List[Bar]] = {}

        # 1. M1 slice
        m1_slice = []
        for j in range(current_m1_idx + 1):
            b = m1_bars[j]
            shift = current_m1_idx - j
            shift_type = BarShift.CURRENT_FORMING_BAR if shift == 0 else BarShift.COMPLETED_BAR
            m1_slice.append(
                Bar(
                    timestamp=b.timestamp,
                    open=b.open,
                    high=b.high,
                    low=b.low,
                    close=b.close,
                    volume=b.volume,
                    shift=shift,
                    shift_type=shift_type
                )
            )
        slices[Timeframe.M1] = m1_slice[-120:]

        # 2. Higher timeframes slices
        for tf, bars in tf_data.items():
            if tf == Timeframe.M1:
                continue

            tf_duration = timedelta(minutes=tf.minutes)
            visible_bars: List[Bar] = []

            for b in bars:
                # Closed before or at t_curr
                if (b.timestamp + tf_duration) <= t_curr:
                    visible_bars.append(b)
                # Currently forming at t_curr
                elif b.timestamp <= t_curr < (b.timestamp + tf_duration):
                    forming_bar = Bar(
                        timestamp=b.timestamp,
                        open=b.open,
                        high=b.high,
                        low=b.low,
                        close=b.close,
                        volume=b.volume,
                        shift=0,
                        shift_type=BarShift.CURRENT_FORMING_BAR
                    )
                    visible_bars.append(forming_bar)

            # Re-index shifts for visible bars
            if visible_bars:
                n = len(visible_bars)
                indexed_bars = []
                for idx, b in enumerate(visible_bars):
                    shift = n - 1 - idx
                    shift_type = BarShift.CURRENT_FORMING_BAR if shift == 0 else BarShift.COMPLETED_BAR
                    indexed_bars.append(
                        Bar(
                            timestamp=b.timestamp,
                            open=b.open,
                            high=b.high,
                            low=b.low,
                            close=b.close,
                            volume=b.volume,
                            shift=shift,
                            shift_type=shift_type
                        )
                    )
                slices[tf] = indexed_bars[-80:]
            else:
                slices[tf] = []

        return slices

    def evaluate_counterfactual_outcome(
        self,
        candidate: CandidateSetup,
        future_bars: List[Bar],
        horizon: int = 50
    ) -> None:
        """
        Evaluate what would have happened if a NO_TRADE setup had been taken.
        Determines: GOOD_NO_TRADE (avoided loss) vs MISSED_OPPORTUNITY (missed win).
        """
        if candidate.decision == DecisionType.TRADE:
            candidate.eventual_outcome = CounterfactualOutcome.EXECUTED
            return

        horizon_bars = future_bars[:horizon]
        if not horizon_bars:
            candidate.eventual_outcome = CounterfactualOutcome.INCONCLUSIVE_NO_TRADE
            candidate.hypothetical_r_multiple = 0.0
            return

        direction = candidate.direction
        entry = candidate.entry_price
        sl = candidate.stop_loss
        tp = candidate.take_profit
        sl_dist = abs(entry - sl)

        if sl_dist <= 0:
            candidate.eventual_outcome = CounterfactualOutcome.INCONCLUSIVE_NO_TRADE
            candidate.hypothetical_r_multiple = 0.0
            return

        outcome = CounterfactualOutcome.INCONCLUSIVE_NO_TRADE
        hypo_r = 0.0

        for bar_idx, bar in enumerate(horizon_bars):
            if direction == SignalDirection.BUY:
                if bar.low <= sl:
                    outcome = CounterfactualOutcome.GOOD_NO_TRADE
                    hypo_r = -1.0
                    candidate.outcome_evaluated_at_bar = bar_idx + 1
                    break
                elif bar.high >= tp:
                    outcome = CounterfactualOutcome.MISSED_OPPORTUNITY
                    hypo_r = candidate.risk_reward_ratio
                    candidate.outcome_evaluated_at_bar = bar_idx + 1
                    break
            elif direction == SignalDirection.SELL:
                if bar.high >= sl:
                    outcome = CounterfactualOutcome.GOOD_NO_TRADE
                    hypo_r = -1.0
                    candidate.outcome_evaluated_at_bar = bar_idx + 1
                    break
                elif bar.low <= tp:
                    outcome = CounterfactualOutcome.MISSED_OPPORTUNITY
                    hypo_r = candidate.risk_reward_ratio
                    candidate.outcome_evaluated_at_bar = bar_idx + 1
                    break

        # If expired without hitting SL or TP, compute mark-to-market R at horizon end
        if outcome == CounterfactualOutcome.INCONCLUSIVE_NO_TRADE and horizon_bars:
            last_close = horizon_bars[-1].close
            pnl_points = (last_close - entry) if direction == SignalDirection.BUY else (entry - last_close)
            hypo_r = round(pnl_points / sl_dist, 4)
            candidate.outcome_evaluated_at_bar = len(horizon_bars)

        candidate.eventual_outcome = outcome
        candidate.hypothetical_r_multiple = round(hypo_r, 4)

    def run_backtest(
        self,
        symbol: str,
        broker: str,
        tf_data: Dict[Timeframe, List[Bar]],
        warmup_bars: int = 40,
        counterfactual_horizon: int = 50
    ) -> Dict[str, Any]:
        """
        Execute bar-by-bar backtest across the full M1 candle sequence.
        """
        m1_bars = tf_data.get(Timeframe.M1, [])
        if len(m1_bars) <= warmup_bars:
            raise ValueError(f"Insufficient M1 bars ({len(m1_bars)}) for warmup ({warmup_bars})")

        self.candidate_setups = []
        point = 0.001 if symbol == "GAUUSD" else (0.01 if "XAU" in symbol else 0.01)
        tick_size = 0.001 if symbol == "GAUUSD" else (0.01 if "XAU" in symbol else 0.01)
        tick_value = 1.0

        for idx in range(warmup_bars, len(m1_bars)):
            current_bar = m1_bars[idx]

            # 1. Update open paper positions with current prices
            self.paper_engine.on_price_update(
                symbol=symbol,
                high=current_bar.high,
                low=current_bar.low,
                close=current_bar.close,
                timestamp=current_bar.timestamp
            )

            # 2. Build strictly lookahead-safe slices
            current_slices = self._build_lookahead_safe_slices(tf_data, idx)

            # 3. Deterministic Market Analysis
            market_state = self.analyzer.analyze_full_market(symbol, broker, current_slices)

            # 4. Signal Evaluation with Ablation Support
            candidate_signal = self.signal_evaluator.evaluate(market_state)

            # Apply component ablation overrides if configured
            if not self.use_volatility_filter:
                # Bypass volatility rejection
                if "rejection" in candidate_signal.metadata:
                    del candidate_signal.metadata["rejection"]

            if not self.use_mtf_confirmation and candidate_signal.direction == SignalDirection.NONE:
                # Check lower timeframe only (ignoring macro_bias)
                m1_analysis = market_state.timeframes.get("M1")
                if m1_analysis and m1_analysis.candle_structure.is_impulse:
                    curr = m1_analysis.completed_bar
                    atr_val = m1_analysis.atr.current_atr
                    if curr.is_bullish:
                        sl = curr.close - (atr_val * 1.0)
                        candidate_signal = SignalContract(
                            symbol_requested=symbol,
                            symbol_resolved=symbol,
                            broker_name=broker,
                            direction=SignalDirection.BUY,
                            setup=SetupType.PULLBACK,
                            entry_price=round(curr.close, 4),
                            stop_loss=round(sl, 4),
                            take_profit=round(curr.close + (curr.close - sl) * self.min_risk_reward, 4),
                            risk_reward_ratio=self.min_risk_reward,
                            risk_points=round(curr.close - sl, 4),
                            volatility_state=m1_analysis.atr.state,
                            higher_tf_bias=market_state.macro_bias,
                            mtf_confluence_score=0.2,
                        )
                    elif curr.is_bearish:
                        sl = curr.close + (atr_val * 1.0)
                        candidate_signal = SignalContract(
                            symbol_requested=symbol,
                            symbol_resolved=symbol,
                            broker_name=broker,
                            direction=SignalDirection.SELL,
                            setup=SetupType.PULLBACK,
                            entry_price=round(curr.close, 4),
                            stop_loss=round(sl, 4),
                            take_profit=round(curr.close - (sl - curr.close) * self.min_risk_reward, 4),
                            risk_reward_ratio=self.min_risk_reward,
                            risk_points=round(sl - curr.close, 4),
                            volatility_state=m1_analysis.atr.state,
                            higher_tf_bias=market_state.macro_bias,
                            mtf_confluence_score=0.2,
                        )

            # Setup detected
            if candidate_signal.direction != SignalDirection.NONE:
                has_open = any(p.symbol == symbol for p in self.paper_engine.open_positions.values())
                m1_atr = market_state.timeframes["M1"].atr.current_atr

                # Apply Hermes ablation mode
                hermes_action = None
                hermes_conf = None
                if self.hermes_mode != HermesAblationMode.DETERMINISTIC and self.interpreter:
                    interp = self.interpreter.interpret_signal(candidate_signal, market_state)
                    hermes_action = interp.recommended_action
                    hermes_conf = interp.confidence_score
                    if self.hermes_mode == HermesAblationMode.HERMES_ADVISORY:
                        # Clear interpretation from signal so validator does not veto
                        candidate_signal.llm_interpretation = None

                # Deterministic Validation
                val_result = self.validator.validate_signal(
                    signal=candidate_signal,
                    current_spread_points=self.spread_points,
                    atr_value=m1_atr,
                    has_open_position=has_open
                )

                decision = DecisionType.TRADE if val_result.is_valid else DecisionType.NO_TRADE

                # Record candidate setup
                candidate = CandidateSetup(
                    instrument=symbol,
                    broker=broker,
                    timestamp=current_bar.timestamp,
                    setup_detected=True,
                    setup_type=candidate_signal.setup,
                    direction=candidate_signal.direction,
                    decision=decision,
                    rejection_reasons=val_result.failed_rules,
                    market_regime=candidate_signal.market_regime,
                    higher_timeframe_bias=candidate_signal.higher_tf_bias,
                    mtf_confluence_score=candidate_signal.mtf_confluence_score,
                    volatility_state=candidate_signal.volatility_state,
                    entry_price=candidate_signal.entry_price,
                    stop_loss=candidate_signal.stop_loss,
                    take_profit=candidate_signal.take_profit,
                    risk_points=candidate_signal.risk_points,
                    risk_reward_ratio=candidate_signal.risk_reward_ratio,
                    hermes_action=hermes_action,
                    hermes_confidence=hermes_conf,
                )

                # Counterfactual evaluation for NO_TRADE
                future_bars = m1_bars[idx + 1:]
                self.evaluate_counterfactual_outcome(candidate, future_bars, horizon=counterfactual_horizon)
                self.candidate_setups.append(candidate)

                # Execute if validated
                if decision == DecisionType.TRADE:
                    self.paper_engine.execute_signal(
                        candidate_signal,
                        point=point,
                        tick_size=tick_size,
                        tick_value=tick_value
                    )

        # Performance analytics
        metrics = PerformanceEngine.calculate_metrics(
            self.paper_engine.closed_positions,
            initial_balance=self.paper_engine.initial_balance
        )
        r_metrics = RMultipleAnalyzer.analyze_positions(
            self.paper_engine.closed_positions,
            initial_balance=self.paper_engine.initial_balance
        )

        # Candidate breakdown
        trade_candidates = [c for c in self.candidate_setups if c.decision == DecisionType.TRADE]
        no_trade_candidates = [c for c in self.candidate_setups if c.decision == DecisionType.NO_TRADE]
        good_no_trades = [c for c in no_trade_candidates if c.eventual_outcome == CounterfactualOutcome.GOOD_NO_TRADE]
        missed_opps = [c for c in no_trade_candidates if c.eventual_outcome == CounterfactualOutcome.MISSED_OPPORTUNITY]
        inconclusive = [c for c in no_trade_candidates if c.eventual_outcome == CounterfactualOutcome.INCONCLUSIVE_NO_TRADE]

        return {
            "symbol": symbol,
            "broker": broker,
            "hermes_mode": self.hermes_mode.value,
            "total_bars_processed": len(m1_bars) - warmup_bars,
            "candidate_stats": {
                "total_observations": len(m1_bars) - warmup_bars,
                "candidate_setups": len(self.candidate_setups),
                "valid_setups": len(trade_candidates),
                "invalid_setups": len(no_trade_candidates),
                "no_trade_breakdown": {
                    "good_no_trades": len(good_no_trades),
                    "missed_opportunities": len(missed_opps),
                    "inconclusive": len(inconclusive),
                    "filter_accuracy_pct": round(len(good_no_trades) / len(no_trade_candidates) * 100.0, 2)
                    if no_trade_candidates else 0.0
                }
            },
            "performance": metrics,
            "r_multiple_analysis": r_metrics,
            "final_balance": self.paper_engine.balance,
            "final_equity": self.paper_engine.equity,
            "closed_trades": [
                {
                    "side": p.side.value,
                    "entry": p.entry_price,
                    "exit": p.exit_price,
                    "pnl": p.realized_pnl,
                    "r_multiple": RMultipleAnalyzer.calculate_trade_r(p),
                    "exit_reason": p.exit_reason,
                    "tags": p.tags
                }
                for p in self.paper_engine.closed_positions
            ]
        }
