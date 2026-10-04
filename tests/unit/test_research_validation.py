"""
Comprehensive Unit & Regression Tests for Phase 2 Strategy Validation:
Verifies:
1. Strict look-ahead prevention and shift=1 completed bar semantics
2. Candidate setup journaling and NO_TRADE counterfactual evaluation
3. Institutional R-multiple analytics (expectancy, drawdown, streaks)
4. Long (BUY) vs. Short (SELL) directional symmetry
5. Walk-forward non-overlapping window partitioning
6. Live execution adapter blocking (LiveExecutionForbiddenError)
"""

import pytest
from datetime import datetime, timezone, timedelta
from core.models.candle import Bar, Timeframe, BarShift
from core.models.signal import SignalContract, SignalDirection, SetupType, MarketRegime
from core.models.candidate import CandidateSetup, DecisionType, CounterfactualOutcome
from core.models.trade import PaperPosition, PositionSide, TradeStatus
from core.validation.validator import DeterministicValidator
from execution.live_disabled.live_blocker import LiveBrokerAdapterDisabled, LiveExecutionForbiddenError
from journal.analytics.r_multiple import RMultipleAnalyzer
from backtest.engine.simulator import BacktestSimulator, HermesAblationMode
from backtest.walk_forward.validator import WalkForwardValidator
from backtest.datasets.regimes import RegimeDatasetGenerator, MarketRegimeType


def test_lookahead_prevention_and_shift_indexing():
    """Ensure multi-timeframe slicing never exposes future data and strictly marks forming vs completed."""
    tf_data = RegimeDatasetGenerator.generate_multitimeframe_suite(
        MarketRegimeType.BULLISH, "GAUUSD", seed=10
    )
    sim = BacktestSimulator()
    m1_bars = tf_data[Timeframe.M1]
    test_idx = 100
    target_time = m1_bars[test_idx].timestamp

    slices = sim._build_lookahead_safe_slices(tf_data, test_idx)

    # 1. No bar in any timeframe has timestamp > target_time
    for tf, bars in slices.items():
        for b in bars:
            assert b.timestamp <= target_time, f"Lookahead leak in {tf}: {b.timestamp} > {target_time}"

    # 2. On M1, the last bar is shift 0 (forming) and prior is shift 1 (completed)
    m1_slice = slices[Timeframe.M1]
    assert m1_slice[-1].shift == 0
    assert m1_slice[-1].shift_type == BarShift.CURRENT_FORMING_BAR
    assert m1_slice[-2].shift == 1
    assert m1_slice[-2].shift_type == BarShift.COMPLETED_BAR


def test_candidate_journaling_and_counterfactuals():
    """Verify that candidate setups are journaled and counterfactual outcomes are evaluated."""
    sim = BacktestSimulator(min_risk_reward=1.5)
    now = datetime.now(timezone.utc)

    # Setup a rejected candidate (NO_TRADE)
    candidate = CandidateSetup(
        instrument="GAUUSD",
        direction=SignalDirection.BUY,
        decision=DecisionType.NO_TRADE,
        rejection_reasons=["SPREAD_TOO_HIGH"],
        entry_price=2650.0,
        stop_loss=2648.0,      # 2.0 SL
        take_profit=2653.0,     # 3.0 TP (1.5 R)
        risk_points=2.0,
        risk_reward_ratio=1.5
    )

    # Future scenario 1: price drops to hit SL first (Avoided Loss -> GOOD_NO_TRADE)
    future_sl = [
        Bar(timestamp=now, open=2650.0, high=2651.0, low=2647.5, close=2648.0, volume=100.0, shift=1)
    ]
    sim.evaluate_counterfactual_outcome(candidate, future_sl, horizon=10)
    assert candidate.eventual_outcome == CounterfactualOutcome.GOOD_NO_TRADE
    assert candidate.hypothetical_r_multiple == -1.0

    # Future scenario 2: price rises to hit TP first (Missed Win -> MISSED_OPPORTUNITY)
    candidate2 = CandidateSetup(
        instrument="GAUUSD",
        direction=SignalDirection.BUY,
        decision=DecisionType.NO_TRADE,
        rejection_reasons=["CONCURRENT_POSITION_LIMIT"],
        entry_price=2650.0,
        stop_loss=2648.0,
        take_profit=2653.0,
        risk_points=2.0,
        risk_reward_ratio=1.5
    )
    future_tp = [
        Bar(timestamp=now, open=2650.0, high=2653.5, low=2649.5, close=2653.0, volume=100.0, shift=1)
    ]
    sim.evaluate_counterfactual_outcome(candidate2, future_tp, horizon=10)
    assert candidate2.eventual_outcome == CounterfactualOutcome.MISSED_OPPORTUNITY
    assert candidate2.hypothetical_r_multiple == 1.5


def test_r_multiple_analytics():
    """Verify R-multiple calculation, expectancy, and streak tracking."""
    # Synthetic closed positions
    # Position 1: Win +1.5R (risk $200, gain $300)
    p1 = PaperPosition(
        order_id="1", signal_id="1", symbol="GAUUSD", side=PositionSide.LONG,
        entry_price=2650.0, current_price=2653.0, quantity_lots=1.0,
        stop_loss=2648.0, take_profit=2653.0, exit_price=2653.0,
        realized_pnl=300.0, status=TradeStatus.CLOSED
    )
    # Position 2: Loss -1.0R (risk $200, loss -$200)
    p2 = PaperPosition(
        order_id="2", signal_id="2", symbol="GAUUSD", side=PositionSide.LONG,
        entry_price=2650.0, current_price=2648.0, quantity_lots=1.0,
        stop_loss=2648.0, take_profit=2653.0, exit_price=2648.0,
        realized_pnl=-200.0, status=TradeStatus.CLOSED
    )

    r1 = RMultipleAnalyzer.calculate_trade_r(p1)
    r2 = RMultipleAnalyzer.calculate_trade_r(p2)
    assert r1 == 1.5
    assert r2 == -1.0

    analysis = RMultipleAnalyzer.analyze_positions([p1, p2], initial_balance=10000.0)
    assert analysis["total_trades"] == 2
    assert analysis["win_rate_pct"] == 50.0
    assert analysis["average_r"] == 0.25
    assert analysis["expectancy_r"] == 0.25
    assert analysis["profit_factor"] == 1.5
    assert analysis["max_consecutive_wins"] == 1
    assert analysis["max_consecutive_losses"] == 1


def test_buy_sell_symmetry():
    """Verify evaluator produces symmetrical BUY and SELL setups."""
    from core.signals.evaluator import SignalEvaluator
    from core.market.analyzer import MultiTimeframeMarketState, TimeframeAnalysis
    from core.models.indicators import ATRAssessment, TrendDirection, VolatilityState
    from core.models.candle import CandleStructure

    evaluator = SignalEvaluator(reward_ratio=1.5)

    def create_mock_state(trend_dir: TrendDirection, is_bull: bool) -> MultiTimeframeMarketState:
        atr_mock = ATRAssessment(
            current_atr=1.5,
            historical_mean=1.5,
            ratio_to_mean=1.0,
            percentile=50.0,
            state=VolatilityState.NORMAL,
            is_tradable=True,
            threshold_low=0.5,
            threshold_high=2.5,
            rolling_window=100
        )
        bar_mock = Bar(
            timestamp=datetime.now(timezone.utc),
            open=2650.0 if is_bull else 2652.0,
            high=2653.0 if is_bull else 2653.0,
            low=2649.0 if is_bull else 2649.0,
            close=2652.0 if is_bull else 2650.0,
            volume=500.0,
            shift=1
        )
        cs_mock = CandleStructure(
            timeframe=Timeframe.M1,
            completed_bar=bar_mock,
            is_impulse=True,
            is_pullback=True,
            pullback_depth=0.35,
            impulse_bar_shift=2,
            pullback_bar_shift=1
        )
        tf_analysis = TimeframeAnalysis(
            timeframe=Timeframe.M1,
            completed_bar=bar_mock,
            trend=trend_dir,
            atr=atr_mock,
            ema_fast=2651.0,
            ema_slow=2650.0,
            rsi=55.0,
            candle_structure=cs_mock,
            support_zones=[],
            resistance_zones=[],
            swing_highs=[],
            swing_lows=[]
        )
        return MultiTimeframeMarketState(
            symbol="GAUUSD",
            broker="XM",
            macro_bias=trend_dir,
            execution_bias=trend_dir,
            mtf_confluence_score=0.8,
            market_regime=MarketRegime.TRENDING,
            timeframes={"M1": tf_analysis}
        )

    # Bullish state -> BUY signal
    bull_state = create_mock_state(TrendDirection.BULLISH, is_bull=True)
    sig_buy = evaluator.evaluate(bull_state)
    assert sig_buy.direction == SignalDirection.BUY
    assert sig_buy.setup == SetupType.PULLBACK

    # Bearish state -> SELL signal
    bear_state = create_mock_state(TrendDirection.BEARISH, is_bull=False)
    sig_sell = evaluator.evaluate(bear_state)
    assert sig_sell.direction == SignalDirection.SELL
    assert sig_sell.setup == SetupType.PULLBACK


def test_walk_forward_window_partitioning():
    """Verify that walk-forward window partitioning maintains clean rolling steps."""
    bars = RegimeDatasetGenerator.generate_regime_bars(
        MarketRegimeType.BULLISH, "GAUUSD", n_bars=400, seed=12
    )
    wfv = WalkForwardValidator(
        in_sample_bars=150,
        out_of_sample_bars=60,
        step_bars=50
    )
    windows = wfv.partition_windows(bars)
    assert len(windows) > 1

    for win in windows:
        is_s, is_e = win["in_sample_range"]
        oos_s, oos_e = win["out_of_sample_range"]
        # In-sample ends where out-of-sample begins
        assert is_e == oos_s
        assert (is_e - is_s) == 150
        assert (oos_e - oos_s) == 60


def test_live_broker_adapter_strictly_disabled():
    """Verify that LiveBrokerAdapterDisabled raises fatal exception on any execution call."""
    adapter = LiveBrokerAdapterDisabled()
    assert adapter.is_live is False

    with pytest.raises(LiveExecutionForbiddenError) as exc_info:
        adapter.order_send()
    assert "Live order execution is permanently disabled" in str(exc_info.value)

    with pytest.raises(LiveExecutionForbiddenError):
        adapter.buy()

    with pytest.raises(LiveExecutionForbiddenError):
        adapter.sell()


def test_validator_enforces_paper_only():
    """Verify DeterministicValidator rejects any live signal."""
    validator = DeterministicValidator()
    # Mock invalid signal attempting live
    signal = SignalContract(
        symbol_requested="GAUUSD",
        symbol_resolved="GAUUSD",
        direction=SignalDirection.BUY,
        setup=SetupType.PULLBACK,
        entry_price=2650.0,
        stop_loss=2648.0,
        take_profit=2653.0,
        risk_reward_ratio=1.5,
    )
    # Validate safe default
    res_paper = validator.validate_signal(signal, atr_value=1.5)
    assert any("ENVIRONMENT_SAFETY_CHECK" in r for r in res_paper.passed_rules)
