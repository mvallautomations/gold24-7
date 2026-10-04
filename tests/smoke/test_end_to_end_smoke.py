"""
Smoke tests for complete end-to-end pipeline.
"""

import pytest
import asyncio
from core.models.candle import Timeframe
from core.market.analyzer import MultiTimeframeMarketAnalyzer
from core.signals.evaluator import SignalEvaluator
from core.validation.validator import DeterministicValidator
from adapters.broker.symbol_resolver import BrokerSymbolResolver
from backtest.datasets.data_generator import MarketDataGenerator
from execution.paper.engine import PaperTradingEngine
from backtest.engine.simulator import BacktestSimulator


def test_full_pipeline_smoke():
    # 1. Resolve Symbol
    resolver = BrokerSymbolResolver(broker="XM")
    res = resolver.resolve("XAUUSD")
    assert res.resolved in ["GAUUSD", "XAUUSD"]

    # 2. Generate Market Data
    tf_data = MarketDataGenerator.generate_multitimeframe_suite(symbol=res.resolved, start_price=2650.0)
    assert len(tf_data) == 6

    # 3. Analyze Market
    analyzer = MultiTimeframeMarketAnalyzer()
    market_state = analyzer.analyze_full_market(res.resolved, res.broker, tf_data)
    assert market_state.symbol == res.resolved
    assert market_state.macro_bias is not None

    # 4. Evaluate Signals
    evaluator = SignalEvaluator(reward_ratio=1.5)
    candidate_signal = evaluator.evaluate(market_state)
    assert candidate_signal.environment == "PAPER"
    assert candidate_signal.is_simulation_only is True

    # 5. Deterministic Validation
    validator = DeterministicValidator()
    val_result = validator.validate_signal(
        candidate_signal,
        current_spread_points=res.spread_points,
        atr_value=market_state.timeframes["M1"].atr.current_atr
    )
    assert val_result is not None


def test_backtest_simulator_smoke():
    resolver = BrokerSymbolResolver(broker="XM")
    res = resolver.resolve("GAUUSD")
    tf_data = MarketDataGenerator.generate_multitimeframe_suite(symbol="GAUUSD", start_price=2650.0)

    sim = BacktestSimulator(initial_balance=10000.0)
    report = sim.run_backtest(res.resolved, res.broker, tf_data, warmup_bars=50)

    assert "performance" in report
    assert report["total_bars_processed"] > 0
    assert report["final_balance"] > 0
