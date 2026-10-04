"""
Ablation Testing Orchestrator:
Executes:
1. Hermes Ablation (Deterministic vs. Advisory Commentary vs. Full Pipeline with Veto)
2. Component Ablation (Full vs. -S/R vs. -Volatility vs. -MTF vs. -Pullback)
"""

from typing import Dict, Any, List, Optional
from core.models.candle import Bar, Timeframe
from agents.analyzer.interpreter import HermesMarketInterpreter
from backtest.engine.simulator import BacktestSimulator, HermesAblationMode


class AblationExperimentRunner:
    """
    Runs systematic ablation experiments to isolate the value of AI and individual technical components.
    """

    @staticmethod
    def run_hermes_ablation(
        symbol: str,
        broker: str,
        tf_data: Dict[Timeframe, List[Bar]],
        interpreter: Optional[HermesMarketInterpreter] = None,
        warmup_bars: int = 40
    ) -> Dict[str, Any]:
        """
        Experiment A: Deterministic baseline (no LLM)
        Experiment B: Deterministic + Hermes commentary (advisory)
        Experiment C: Full current pipeline (Hermes veto active)
        """
        active_interp = interpreter or HermesMarketInterpreter()

        # Experiment A: Deterministic Baseline
        sim_a = BacktestSimulator(
            hermes_mode=HermesAblationMode.DETERMINISTIC
        )
        res_a = sim_a.run_backtest(symbol, broker, tf_data, warmup_bars=warmup_bars)

        # Experiment B: Deterministic + Hermes Commentary (Advisory)
        sim_b = BacktestSimulator(
            hermes_mode=HermesAblationMode.HERMES_ADVISORY,
            interpreter=active_interp
        )
        res_b = sim_b.run_backtest(symbol, broker, tf_data, warmup_bars=warmup_bars)

        # Experiment C: Full Pipeline (Hermes Veto Active)
        sim_c = BacktestSimulator(
            hermes_mode=HermesAblationMode.FULL_PIPELINE,
            interpreter=active_interp
        )
        res_c = sim_c.run_backtest(symbol, broker, tf_data, warmup_bars=warmup_bars)

        return {
            "experiment_a_deterministic": {
                "trades": res_a["performance"]["total_trades"],
                "win_rate_pct": res_a["r_multiple_analysis"]["win_rate_pct"],
                "expectancy_r": res_a["r_multiple_analysis"]["expectancy_r"],
                "profit_factor": res_a["r_multiple_analysis"]["profit_factor"],
                "total_r": res_a["r_multiple_analysis"]["total_realized_r"],
                "max_drawdown_pct": res_a["r_multiple_analysis"]["max_drawdown_pct"],
                "avg_r": res_a["r_multiple_analysis"]["average_r"],
            },
            "experiment_b_advisory": {
                "trades": res_b["performance"]["total_trades"],
                "win_rate_pct": res_b["r_multiple_analysis"]["win_rate_pct"],
                "expectancy_r": res_b["r_multiple_analysis"]["expectancy_r"],
                "profit_factor": res_b["r_multiple_analysis"]["profit_factor"],
                "total_r": res_b["r_multiple_analysis"]["total_realized_r"],
                "max_drawdown_pct": res_b["r_multiple_analysis"]["max_drawdown_pct"],
                "avg_r": res_b["r_multiple_analysis"]["average_r"],
            },
            "experiment_c_full_pipeline": {
                "trades": res_c["performance"]["total_trades"],
                "win_rate_pct": res_c["r_multiple_analysis"]["win_rate_pct"],
                "expectancy_r": res_c["r_multiple_analysis"]["expectancy_r"],
                "profit_factor": res_c["r_multiple_analysis"]["profit_factor"],
                "total_r": res_c["r_multiple_analysis"]["total_realized_r"],
                "max_drawdown_pct": res_c["r_multiple_analysis"]["max_drawdown_pct"],
                "avg_r": res_c["r_multiple_analysis"]["average_r"],
            },
            "hermes_measurable_alpha": {
                "win_rate_delta": round(
                    res_c["r_multiple_analysis"]["win_rate_pct"] - res_a["r_multiple_analysis"]["win_rate_pct"], 2
                ),
                "expectancy_r_delta": round(
                    res_c["r_multiple_analysis"]["expectancy_r"] - res_a["r_multiple_analysis"]["expectancy_r"], 4
                ),
                "conclusion": "HERMES_IMPROVES_COACHING_EXPLANATION_NOT_NUMERICAL_ALPHA"
                if abs(res_c["r_multiple_analysis"]["expectancy_r"] - res_a["r_multiple_analysis"]["expectancy_r"]) < 0.10
                else ("HERMES_ADDS_ALPHA" if res_c["r_multiple_analysis"]["expectancy_r"] > res_a["r_multiple_analysis"]["expectancy_r"] else "HERMES_REDUCES_ALPHA")
            }
        }

    @staticmethod
    def run_component_ablation(
        symbol: str,
        broker: str,
        tf_data: Dict[Timeframe, List[Bar]],
        warmup_bars: int = 40
    ) -> Dict[str, Any]:
        """
        Runs component ablation to test the marginal predictive or risk-filtering
        value of each technical component.
        """
        variations = [
            ("full_system", {}),
            ("minus_sr", {"use_sr_filter": False}),
            ("minus_volatility", {"use_volatility_filter": False}),
            ("minus_mtf", {"use_mtf_confirmation": False}),
            ("minus_pullback", {"use_pullback_condition": False}),
        ]

        results = {}
        for name, kwargs in variations:
            sim = BacktestSimulator(**kwargs)
            res = sim.run_backtest(symbol, broker, tf_data, warmup_bars=warmup_bars)
            r_m = res["r_multiple_analysis"]
            results[name] = {
                "trades": res["performance"]["total_trades"],
                "win_rate_pct": r_m["win_rate_pct"],
                "expectancy_r": r_m["expectancy_r"],
                "profit_factor": r_m["profit_factor"],
                "total_realized_r": r_m["total_realized_r"],
                "max_drawdown_pct": r_m["max_drawdown_pct"],
                "candidate_setups": res["candidate_stats"]["candidate_setups"],
                "rejected_setups": res["candidate_stats"]["invalid_setups"],
            }

        return results
