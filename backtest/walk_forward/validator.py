"""
Walk-Forward Validation Engine: Implements rolling in-sample (train) and out-of-sample (test)
partitions to evaluate strategy robustness and detect parameter overfitting or performance collapse.
"""

from typing import List, Dict, Any, Optional
import numpy as np

from core.models.candle import Bar, Timeframe
from backtest.engine.simulator import BacktestSimulator, HermesAblationMode


class WalkForwardValidator:
    """
    Executes walk-forward train/test analysis across sequential historical periods.
    """

    def __init__(
        self,
        in_sample_bars: int = 150,
        out_of_sample_bars: int = 70,
        step_bars: int = 50,
        initial_balance: float = 10000.0,
        risk_per_trade_pct: float = 1.0,
        slippage_points: float = 1.5,
        min_risk_reward: float = 1.5,
    ):
        self.in_sample_bars = in_sample_bars
        self.out_of_sample_bars = out_of_sample_bars
        self.step_bars = step_bars
        self.initial_balance = initial_balance
        self.risk_per_trade_pct = risk_per_trade_pct
        self.slippage_points = slippage_points
        self.min_risk_reward = min_risk_reward

    def partition_windows(self, m1_bars: List[Bar]) -> List[Dict[str, Any]]:
        """
        Partition total M1 series into rolling [in_sample, out_of_sample] index windows.
        """
        total_bars = len(m1_bars)
        windows = []
        start_idx = 0

        while (start_idx + self.in_sample_bars + self.out_of_sample_bars) <= total_bars:
            is_start = start_idx
            is_end = is_start + self.in_sample_bars
            oos_start = is_end
            oos_end = oos_start + self.out_of_sample_bars

            windows.append({
                "window_id": len(windows) + 1,
                "in_sample_range": (is_start, is_end),
                "out_of_sample_range": (oos_start, oos_end),
            })
            start_idx += self.step_bars

        return windows

    def run_walk_forward_analysis(
        self,
        symbol: str,
        broker: str,
        tf_data: Dict[Timeframe, List[Bar]],
        warmup_bars: int = 30
    ) -> Dict[str, Any]:
        """
        Execute walk-forward partitions and compare in-sample vs out-of-sample metrics.
        """
        m1_bars = tf_data[Timeframe.M1]
        windows = self.partition_windows(m1_bars)

        if not windows:
            raise ValueError(
                f"Dataset size ({len(m1_bars)}) too small for IS={self.in_sample_bars} + OOS={self.out_of_sample_bars}"
            )

        window_results = []
        is_expectancies = []
        oos_expectancies = []
        is_win_rates = []
        oos_win_rates = []
        is_avg_rs = []
        oos_avg_rs = []

        for win in windows:
            is_s, is_e = win["in_sample_range"]
            oos_s, oos_e = win["out_of_sample_range"]

            # 1. Run In-Sample
            is_tf_data = {
                tf: bars for tf, bars in tf_data.items()
            }
            # Slice M1 for in-sample
            is_tf_data[Timeframe.M1] = m1_bars[is_s:is_e]

            sim_is = BacktestSimulator(
                initial_balance=self.initial_balance,
                risk_per_trade_pct=self.risk_per_trade_pct,
                slippage_points=self.slippage_points,
                min_risk_reward=self.min_risk_reward,
                hermes_mode=HermesAblationMode.DETERMINISTIC
            )
            res_is = sim_is.run_backtest(symbol, broker, is_tf_data, warmup_bars=warmup_bars)

            # 2. Run Out-of-Sample
            oos_tf_data = {
                tf: bars for tf, bars in tf_data.items()
            }
            # Slice M1 for out-of-sample (include warmup from end of in-sample to ensure indicator priming)
            warmup_slice_start = max(0, oos_s - warmup_bars)
            oos_tf_data[Timeframe.M1] = m1_bars[warmup_slice_start:oos_e]

            sim_oos = BacktestSimulator(
                initial_balance=self.initial_balance,
                risk_per_trade_pct=self.risk_per_trade_pct,
                slippage_points=self.slippage_points,
                min_risk_reward=self.min_risk_reward,
                hermes_mode=HermesAblationMode.DETERMINISTIC
            )
            res_oos = sim_oos.run_backtest(symbol, broker, oos_tf_data, warmup_bars=warmup_bars)

            is_r_metrics = res_is["r_multiple_analysis"]
            oos_r_metrics = res_oos["r_multiple_analysis"]

            is_exp = is_r_metrics["expectancy_r"]
            oos_exp = oos_r_metrics["expectancy_r"]
            is_wr = is_r_metrics["win_rate_pct"]
            oos_wr = oos_r_metrics["win_rate_pct"]
            is_ar = is_r_metrics["average_r"]
            oos_ar = oos_r_metrics["average_r"]

            is_expectancies.append(is_exp)
            oos_expectancies.append(oos_exp)
            is_win_rates.append(is_wr)
            oos_win_rates.append(oos_wr)
            is_avg_rs.append(is_ar)
            oos_avg_rs.append(oos_ar)

            window_results.append({
                "window_id": win["window_id"],
                "in_sample": {
                    "bars": is_e - is_s,
                    "trades": res_is["performance"]["total_trades"],
                    "win_rate_pct": is_wr,
                    "expectancy_r": is_exp,
                    "average_r": is_ar,
                    "profit_factor": is_r_metrics["profit_factor"],
                    "total_realized_r": is_r_metrics["total_realized_r"],
                },
                "out_of_sample": {
                    "bars": oos_e - oos_s,
                    "trades": res_oos["performance"]["total_trades"],
                    "win_rate_pct": oos_wr,
                    "expectancy_r": oos_exp,
                    "average_r": oos_ar,
                    "profit_factor": oos_r_metrics["profit_factor"],
                    "total_realized_r": oos_r_metrics["total_realized_r"],
                },
                "degradation_ratio": round(oos_exp / is_exp, 3) if is_exp > 0 else (0.0 if oos_exp <= 0 else 1.0)
            })

        mean_is_exp = float(np.mean(is_expectancies)) if is_expectancies else 0.0
        mean_oos_exp = float(np.mean(oos_expectancies)) if oos_expectancies else 0.0
        robustness_score = (mean_oos_exp / mean_is_exp) if mean_is_exp > 0 else 0.0

        return {
            "total_windows": len(windows),
            "summary": {
                "mean_in_sample_win_rate": round(float(np.mean(is_win_rates)), 2),
                "mean_out_of_sample_win_rate": round(float(np.mean(oos_win_rates)), 2),
                "mean_in_sample_expectancy_r": round(mean_is_exp, 4),
                "mean_out_of_sample_expectancy_r": round(mean_oos_exp, 4),
                "mean_in_sample_avg_r": round(float(np.mean(is_avg_rs)), 4),
                "mean_out_of_sample_avg_r": round(float(np.mean(oos_avg_rs)), 4),
                "robustness_score": round(robustness_score, 3),
                "is_out_of_sample_profitable": mean_oos_exp > 0.0,
            },
            "windows": window_results
        }
