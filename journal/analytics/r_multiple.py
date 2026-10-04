"""
R-Multiple Analytics Engine: Computes standardized risk-unit (R) metrics,
expectancy, drawdown in R, win/loss streaks, long/short symmetry, and regime breakdowns.
"""

from typing import List, Dict, Any, Optional
import numpy as np
from core.models.trade import PaperPosition, PositionSide


class RMultipleAnalyzer:
    """
    Standardizes performance analysis using R-multiples where 1R is the initial risk unit.
    """

    @staticmethod
    def calculate_trade_r(position: PaperPosition) -> float:
        """
        Calculate realized R for a single closed position.
        1R = abs(entry - stop_loss) * lots * contract_multiplier
        """
        multiplier = 100.0 if any(g in position.symbol for g in ["XAU", "GAU", "GOLD"]) else (
            1.0 if any(c in position.symbol for c in ["BTC", "ETH"]) else 100000.0
        )
        initial_risk_dollars = abs(position.entry_price - position.stop_loss) * position.quantity_lots * multiplier
        if initial_risk_dollars <= 0:
            return 0.0

        r_multiple = position.realized_pnl / initial_risk_dollars
        return round(float(r_multiple), 4)

    @classmethod
    def analyze_positions(
        cls,
        positions: List[PaperPosition],
        initial_balance: float = 10000.0
    ) -> Dict[str, Any]:
        """
        Comprehensive institutional R-multiple analysis across closed positions.
        """
        if not positions:
            return cls._empty_metrics(initial_balance)

        r_values: List[float] = [cls.calculate_trade_r(p) for p in positions]
        dollar_pnls: List[float] = [p.realized_pnl for p in positions]

        wins_r = [r for r in r_values if r > 0]
        losses_r = [r for r in r_values if r <= 0]

        total_trades = len(r_values)
        win_count = len(wins_r)
        loss_count = len(losses_r)
        win_rate = (win_count / total_trades) if total_trades > 0 else 0.0

        avg_r = float(np.mean(r_values)) if r_values else 0.0
        median_r = float(np.median(r_values)) if r_values else 0.0
        std_r = float(np.std(r_values)) if len(r_values) > 1 else 0.0

        avg_win_r = float(np.mean(wins_r)) if wins_r else 0.0
        avg_loss_r = float(np.mean(losses_r)) if losses_r else 0.0

        # Expectancy in R: (WinRate * AvgWinR) - (LossRate * abs(AvgLossR))
        expectancy_r = (win_rate * avg_win_r) - ((1.0 - win_rate) * abs(avg_loss_r))

        # Profit Factor
        gross_profit_r = sum(wins_r)
        gross_loss_r = abs(sum(losses_r))
        profit_factor = (gross_profit_r / gross_loss_r) if gross_loss_r > 0 else (gross_profit_r if gross_profit_r > 0 else 1.0)

        # Streaks
        max_consecutive_wins = 0
        max_consecutive_losses = 0
        curr_wins = 0
        curr_losses = 0
        for r in r_values:
            if r > 0:
                curr_wins += 1
                curr_losses = 0
                max_consecutive_wins = max(max_consecutive_wins, curr_wins)
            else:
                curr_losses += 1
                curr_wins = 0
                max_consecutive_losses = max(max_consecutive_losses, curr_losses)

        # Drawdown in R (Cumulative R curve)
        cum_r = 0.0
        peak_r = 0.0
        max_dd_r = 0.0
        r_curve = [0.0]
        for r in r_values:
            cum_r += r
            r_curve.append(cum_r)
            if cum_r > peak_r:
                peak_r = cum_r
            dd = peak_r - cum_r
            if dd > max_dd_r:
                max_dd_r = dd

        # Dollar drawdown (%)
        eq = initial_balance
        peak_dollar = initial_balance
        max_dd_dollar_pct = 0.0
        for pnl in dollar_pnls:
            eq += pnl
            if eq > peak_dollar:
                peak_dollar = eq
            dd_pct = (peak_dollar - eq) / peak_dollar * 100.0
            if dd_pct > max_dd_dollar_pct:
                max_dd_dollar_pct = dd_pct

        # R-Distribution Buckets
        distribution = {
            "<-2.0R": len([r for r in r_values if r < -2.0]),
            "[-2.0R, -1.0R)": len([r for r in r_values if -2.0 <= r < -1.0]),
            "[-1.0R, 0.0R)": len([r for r in r_values if -1.0 <= r < 0.0]),
            "[0.0R, +1.0R)": len([r for r in r_values if 0.0 <= r < 1.0]),
            "[+1.0R, +2.0R)": len([r for r in r_values if 1.0 <= r < 2.0]),
            ">= +2.0R": len([r for r in r_values if r >= 2.0]),
        }

        # Long vs Short Symmetry Breakdown
        longs = [p for p in positions if p.side == PositionSide.LONG]
        shorts = [p for p in positions if p.side == PositionSide.SHORT]

        long_metrics = cls._calculate_subset_r(longs)
        short_metrics = cls._calculate_subset_r(shorts)

        return {
            "total_trades": total_trades,
            "win_rate_pct": round(win_rate * 100.0, 2),
            "total_realized_r": round(float(np.sum(r_values)), 2),
            "average_r": round(avg_r, 4),
            "median_r": round(median_r, 4),
            "std_r": round(std_r, 4),
            "average_win_r": round(avg_win_r, 4),
            "average_loss_r": round(avg_loss_r, 4),
            "expectancy_r": round(expectancy_r, 4),
            "profit_factor": round(profit_factor, 2),
            "max_drawdown_r": round(max_dd_r, 2),
            "max_drawdown_pct": round(max_dd_dollar_pct, 2),
            "max_consecutive_wins": max_consecutive_wins,
            "max_consecutive_losses": max_consecutive_losses,
            "r_distribution": distribution,
            "symmetry": {
                "long": long_metrics,
                "short": short_metrics,
                "directional_bias_detected": abs(long_metrics["win_rate_pct"] - short_metrics["win_rate_pct"]) > 25.0
                if (longs and shorts) else False,
            }
        }

    @classmethod
    def _calculate_subset_r(cls, positions: List[PaperPosition]) -> Dict[str, Any]:
        if not positions:
            return {
                "trades": 0,
                "win_rate_pct": 0.0,
                "average_r": 0.0,
                "expectancy_r": 0.0,
                "profit_factor": 1.0,
                "total_r": 0.0,
            }

        r_vals = [cls.calculate_trade_r(p) for p in positions]
        wins = [r for r in r_vals if r > 0]
        losses = [r for r in r_vals if r <= 0]
        win_rate = len(wins) / len(r_vals) if r_vals else 0.0
        avg_win_r = float(np.mean(wins)) if wins else 0.0
        avg_loss_r = float(np.mean(losses)) if losses else 0.0
        expectancy_r = (win_rate * avg_win_r) - ((1.0 - win_rate) * abs(avg_loss_r))
        gross_p = sum(wins)
        gross_l = abs(sum(losses))
        pf = (gross_p / gross_l) if gross_l > 0 else (gross_p if gross_p > 0 else 1.0)

        return {
            "trades": len(positions),
            "win_rate_pct": round(win_rate * 100.0, 2),
            "average_r": round(float(np.mean(r_vals)), 4),
            "expectancy_r": round(expectancy_r, 4),
            "profit_factor": round(pf, 2),
            "total_r": round(float(np.sum(r_vals)), 2),
        }

    @staticmethod
    def _empty_metrics(initial_balance: float) -> Dict[str, Any]:
        return {
            "total_trades": 0,
            "win_rate_pct": 0.0,
            "total_realized_r": 0.0,
            "average_r": 0.0,
            "median_r": 0.0,
            "std_r": 0.0,
            "average_win_r": 0.0,
            "average_loss_r": 0.0,
            "expectancy_r": 0.0,
            "profit_factor": 1.0,
            "max_drawdown_r": 0.0,
            "max_drawdown_pct": 0.0,
            "max_consecutive_wins": 0,
            "max_consecutive_losses": 0,
            "r_distribution": {},
            "symmetry": {
                "long": {"trades": 0, "win_rate_pct": 0.0, "average_r": 0.0, "expectancy_r": 0.0, "profit_factor": 1.0, "total_r": 0.0},
                "short": {"trades": 0, "win_rate_pct": 0.0, "average_r": 0.0, "expectancy_r": 0.0, "profit_factor": 1.0, "total_r": 0.0},
                "directional_bias_detected": False,
            }
        }
