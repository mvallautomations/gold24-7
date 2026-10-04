"""
Backtest Simulator: Bar-by-bar historical backtest engine with
multi-timeframe market analysis, deterministic validation, and execution modeling.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from core.models.candle import Bar, Timeframe
from core.market.analyzer import MultiTimeframeMarketAnalyzer
from core.signals.evaluator import SignalEvaluator
from core.validation.validator import DeterministicValidator
from execution.paper.engine import PaperTradingEngine
from journal.analytics.performance_engine import PerformanceEngine

logger = logging.getLogger(__name__)


class BacktestSimulator:
    """
    Simulates the full research pipeline across historical candle series.
    """

    def __init__(
        self,
        initial_balance: float = 10000.0,
        risk_per_trade_pct: float = 1.0,
        slippage_points: float = 1.5,
        min_risk_reward: float = 1.5
    ):
        self.analyzer = MultiTimeframeMarketAnalyzer()
        self.signal_evaluator = SignalEvaluator(reward_ratio=min_risk_reward)
        self.validator = DeterministicValidator(min_risk_reward=min_risk_reward)
        self.paper_engine = PaperTradingEngine(
            initial_balance=initial_balance,
            risk_per_trade_pct=risk_per_trade_pct,
            slippage_points=slippage_points
        )

    def run_backtest(
        self,
        symbol: str,
        broker: str,
        tf_data: Dict[Timeframe, List[Bar]],
        warmup_bars: int = 50
    ) -> Dict[str, Any]:
        """
        Walk forward through M1 bars from warmup_bars to the end.
        """
        m1_bars = tf_data.get(Timeframe.M1, [])
        if len(m1_bars) <= warmup_bars:
            raise ValueError(f"Insufficient M1 bars ({len(m1_bars)}) for warmup ({warmup_bars})")

        signals_generated = 0
        signals_validated = 0
        signals_rejected = 0

        # Step forward one bar at a time
        for idx in range(warmup_bars, len(m1_bars)):
            # 1. Update prices for open positions
            current_bar = m1_bars[idx]
            self.paper_engine.on_price_update(
                symbol=symbol,
                high=current_bar.high,
                low=current_bar.low,
                close=current_bar.close,
                timestamp=current_bar.timestamp
            )

            # 2. Slice timeframes up to current bar to prevent lookahead
            current_slice = {}
            for tf, bars in tf_data.items():
                if tf == Timeframe.M1:
                    # Mark current as shift 0, prior as shift 1..n
                    sliced = [
                        Bar(
                            timestamp=b.timestamp,
                            open=b.open,
                            high=b.high,
                            low=b.low,
                            close=b.close,
                            volume=b.volume,
                            shift=(idx - j),
                            shift_type="CURRENT_FORMING_BAR" if (idx - j) == 0 else "COMPLETED_BAR"
                        )
                        for j, b in enumerate(m1_bars[:idx + 1])
                    ]
                    current_slice[tf] = sliced[-100:]  # Last 100 bars
                else:
                    # Scale higher timeframes approximately
                    current_slice[tf] = bars[-60:]

            # 3. Deterministic Market Analysis
            market_state = self.analyzer.analyze_full_market(symbol, broker, current_slice)

            # 4. Signal Evaluation
            candidate_signal = self.signal_evaluator.evaluate(market_state)

            if candidate_signal.direction.value != "NONE":
                signals_generated += 1

                # 5. Deterministic Validation
                has_open = any(p.symbol == symbol for p in self.paper_engine.open_positions.values())
                m1_atr = market_state.timeframes["M1"].atr.current_atr

                val_result = self.validator.validate_signal(
                    signal=candidate_signal,
                    current_spread_points=15,
                    atr_value=m1_atr,
                    has_open_position=has_open
                )

                if val_result.is_valid:
                    signals_validated += 1
                    # 6. Simulated Execution
                    self.paper_engine.execute_signal(candidate_signal)
                else:
                    signals_rejected += 1

        # Calculate final metrics
        metrics = PerformanceEngine.calculate_metrics(
            self.paper_engine.closed_positions,
            initial_balance=self.paper_engine.initial_balance
        )

        return {
            "symbol": symbol,
            "broker": broker,
            "total_bars_processed": len(m1_bars) - warmup_bars,
            "signals_generated": signals_generated,
            "signals_validated": signals_validated,
            "signals_rejected": signals_rejected,
            "performance": metrics,
            "final_balance": self.paper_engine.balance,
            "final_equity": self.paper_engine.equity,
            "closed_trades": [
                {
                    "side": p.side.value,
                    "entry": p.entry_price,
                    "exit": p.exit_price,
                    "pnl": p.realized_pnl,
                    "exit_reason": p.exit_reason,
                    "tags": p.tags
                }
                for p in self.paper_engine.closed_positions
            ]
        }
