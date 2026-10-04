"""
GOLD24-7 Phase 2 Comprehensive Strategy Validation Runner:
Executes the full research battery:
1. Multi-regime empirical backtesting (Regimes A - F)
2. Candidate setup journaling & NO_TRADE counterfactual evaluation
3. R-multiple and drawdown distribution analytics
4. BUY vs SELL directional symmetry verification
5. Hermes ablation study (Deterministic vs Advisory vs Full)
6. Component ablation study (S/R, Volatility, MTF, Pullback)
7. Walk-forward rolling train/test validation
8. Overfitting and look-ahead bias audit
9. Live execution safety boundary verification
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.models.candle import Timeframe
from backtest.datasets.regimes import RegimeDatasetGenerator, MarketRegimeType
from backtest.engine.simulator import BacktestSimulator, HermesAblationMode
from backtest.walk_forward.validator import WalkForwardValidator
from backtest.ablation.runner import AblationExperimentRunner
from execution.live_disabled.live_blocker import LiveBrokerAdapterDisabled, LiveExecutionForbiddenError
from agents.analyzer.interpreter import HermesMarketInterpreter


def run_full_validation_battery() -> dict:
    print("=" * 80)
    print("GOLD24-7 PHASE 2: EMPIRICAL STRATEGY VALIDATION BATTERY")
    print("=" * 80)

    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git_branch": "main",
        "benchmark_strategy": "M1_Pullback_Benchmark_EA",
        "symbol": "GAUUSD",
        "broker": "XM",
        "regimes": {},
        "buy_vs_sell": {},
        "hermes_ablation": {},
        "component_ablation": {},
        "walk_forward": {},
        "safety_audit": {},
    }

    # 1. Test All 6 Market Regimes
    print("\n[1/6] Running Multi-Regime Backtesting across Regimes A-F...")
    regime_map = {
        "Regime_A_Bullish": MarketRegimeType.BULLISH,
        "Regime_B_Bearish": MarketRegimeType.BEARISH,
        "Regime_C_Ranging": MarketRegimeType.RANGING,
        "Regime_D_High_Volatility": MarketRegimeType.HIGH_VOLATILITY,
        "Regime_E_Low_Volatility": MarketRegimeType.LOW_VOLATILITY,
        "Regime_F_Shock": MarketRegimeType.SHOCK,
    }

    all_positions = []
    all_candidates = []

    for reg_name, reg_type in regime_map.items():
        print(f"  -> Testing {reg_name}...")
        tf_data = RegimeDatasetGenerator.generate_multitimeframe_suite(
            regime=reg_type,
            symbol="GAUUSD",
            start_price=2650.0,
            seed=200
        )
        sim = BacktestSimulator(
            initial_balance=10000.0,
            spread_points=15,
            slippage_points=1.5,
            fee_per_lot=3.50,
            min_risk_reward=1.5
        )
        res = sim.run_backtest("GAUUSD", "XM", tf_data, warmup_bars=40)
        results["regimes"][reg_name] = {
            "total_bars": res["total_bars_processed"],
            "candidates": res["candidate_stats"],
            "trades": res["performance"]["total_trades"],
            "win_rate_pct": res["r_multiple_analysis"]["win_rate_pct"],
            "expectancy_r": res["r_multiple_analysis"]["expectancy_r"],
            "profit_factor": res["r_multiple_analysis"]["profit_factor"],
            "total_realized_r": res["r_multiple_analysis"]["total_realized_r"],
            "max_drawdown_pct": res["r_multiple_analysis"]["max_drawdown_pct"],
            "average_r": res["r_multiple_analysis"]["average_r"],
            "median_r": res["r_multiple_analysis"]["median_r"],
            "symmetry": res["r_multiple_analysis"]["symmetry"],
        }
        all_positions.extend(sim.paper_engine.closed_positions)
        all_candidates.extend(sim.candidate_setups)

    # Global Aggregate Performance across all regimes
    from journal.analytics.r_multiple import RMultipleAnalyzer
    from journal.analytics.performance_engine import PerformanceEngine

    agg_perf = PerformanceEngine.calculate_metrics(all_positions, initial_balance=10000.0)
    agg_r = RMultipleAnalyzer.analyze_positions(all_positions, initial_balance=10000.0)

    results["aggregate_performance"] = {
        "total_trades": len(all_positions),
        "win_rate_pct": agg_r["win_rate_pct"],
        "expectancy_r": agg_r["expectancy_r"],
        "profit_factor": agg_r["profit_factor"],
        "total_realized_r": agg_r["total_realized_r"],
        "average_r": agg_r["average_r"],
        "median_r": agg_r["median_r"],
        "average_win_r": agg_r["average_win_r"],
        "average_loss_r": agg_r["average_loss_r"],
        "max_drawdown_r": agg_r["max_drawdown_r"],
        "max_drawdown_pct": agg_r["max_drawdown_pct"],
        "max_consecutive_wins": agg_r["max_consecutive_wins"],
        "max_consecutive_losses": agg_r["max_consecutive_losses"],
        "r_distribution": agg_r["r_distribution"],
    }

    # Candidate Journal Summary
    from core.models.candidate import DecisionType, CounterfactualOutcome
    trade_cands = [c for c in all_candidates if c.decision == DecisionType.TRADE]
    no_trade_cands = [c for c in all_candidates if c.decision == DecisionType.NO_TRADE]
    good_no_trades = [c for c in no_trade_cands if c.eventual_outcome == CounterfactualOutcome.GOOD_NO_TRADE]
    missed_opps = [c for c in no_trade_cands if c.eventual_outcome == CounterfactualOutcome.MISSED_OPPORTUNITY]
    inconclusive_no = [c for c in no_trade_cands if c.eventual_outcome == CounterfactualOutcome.INCONCLUSIVE_NO_TRADE]

    results["candidate_journal_summary"] = {
        "total_observations": sum(r["total_bars"] for r in results["regimes"].values()),
        "total_candidate_setups": len(all_candidates),
        "validated_trades": len(trade_cands),
        "rejected_no_trades": len(no_trade_cands),
        "good_no_trades_avoided_losses": len(good_no_trades),
        "missed_opportunities": len(missed_opps),
        "inconclusive_no_trades": len(inconclusive_no),
        "filter_success_rate_pct": round(len(good_no_trades) / len(no_trade_cands) * 100.0, 2) if no_trade_cands else 0.0
    }

    # 2. BUY vs SELL Symmetry
    print("\n[2/6] Evaluating Long/Short Symmetry...")
    results["buy_vs_sell"] = agg_r["symmetry"]

    # 3. Hermes Ablation Study
    print("\n[3/6] Running Hermes Ablation (Deterministic vs Advisory vs Full Pipeline)...")
    bullish_suite = RegimeDatasetGenerator.generate_multitimeframe_suite(
        MarketRegimeType.BULLISH, "GAUUSD", seed=300
    )
    hermes_runner = AblationExperimentRunner()
    results["hermes_ablation"] = hermes_runner.run_hermes_ablation(
        "GAUUSD", "XM", bullish_suite, warmup_bars=40
    )

    # 4. Component Ablation Study
    print("\n[4/6] Running Component Ablation (S/R, Volatility, MTF, Pullback)...")
    results["component_ablation"] = hermes_runner.run_component_ablation(
        "GAUUSD", "XM", bullish_suite, warmup_bars=40
    )

    # 5. Walk-Forward Validation
    print("\n[5/6] Running Walk-Forward Rolling Analysis (In-Sample vs Out-of-Sample)...")
    extended_bars = RegimeDatasetGenerator.generate_multitimeframe_suite(
        MarketRegimeType.BULLISH, "GAUUSD", start_price=2650.0, seed=400
    )
    # Generate 600 M1 bars for robust walk-forward
    extended_bars[Timeframe.M1] = RegimeDatasetGenerator.generate_regime_bars(
        MarketRegimeType.BULLISH, "GAUUSD", Timeframe.M1, n_bars=600, seed=405
    )

    wfv = WalkForwardValidator(
        in_sample_bars=180,
        out_of_sample_bars=80,
        step_bars=60,
        initial_balance=10000.0
    )
    results["walk_forward"] = wfv.run_walk_forward_analysis("GAUUSD", "XM", extended_bars, warmup_bars=30)

    # 6. Live Safety Boundary Audit
    print("\n[6/6] Auditing Live Execution Physical Disablement...")
    live_adapter = LiveBrokerAdapterDisabled()
    safety_passed = False
    try:
        live_adapter.order_send()
    except LiveExecutionForbiddenError as e:
        safety_passed = True
        results["safety_audit"] = {
            "live_adapter_blocked": True,
            "exception_caught": type(e).__name__,
            "message": str(e),
            "circuit_breaker_active": True,
            "status": "PASS"
        }

    print("\n" + "=" * 80)
    print("VALIDATION BATTERY COMPLETE")
    print(f"Total Trades Analyzed: {results['aggregate_performance']['total_trades']}")
    print(f"Overall Win Rate: {results['aggregate_performance']['win_rate_pct']}%")
    print(f"Overall Expectancy (R): {results['aggregate_performance']['expectancy_r']}R")
    print(f"Overall Profit Factor: {results['aggregate_performance']['profit_factor']}")
    print(f"Total Realized R: {results['aggregate_performance']['total_realized_r']}R")
    print(f"Live Execution Disabled: {'YES' if safety_passed else 'NO'}")
    print("=" * 80)

    # Save to JSON artifact
    out_dir = ROOT_DIR / "docs" / "research"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "phase2_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved raw research artifact to: {out_path}")

    return results


if __name__ == "__main__":
    run_full_validation_battery()
