"""
Performance Engine: Quantitative analytics, win/loss attribution,
and error classification for research trades.
"""

from typing import List, Dict, Any, Optional
import numpy as np
from core.models.trade import PaperPosition


from journal.analytics.r_multiple import RMultipleAnalyzer


class PerformanceEngine:
    """
    Computes institutional performance metrics across closed paper trades.
    """

    @staticmethod
    def calculate_metrics(positions: List[PaperPosition], initial_balance: float = 10000.0) -> Dict[str, Any]:
        if not positions:
            base_metrics = {
                "total_trades": 0,
                "win_rate_pct": 0.0,
                "profit_factor": 1.0,
                "sharpe_ratio": 0.0,
                "max_drawdown_pct": 0.0,
                "total_net_pnl": 0.0,
                "average_trade_pnl": 0.0,
                "expectancy": 0.0,
                "error_analysis": {},
            }
            r_metrics = RMultipleAnalyzer.analyze_positions(positions, initial_balance)
            base_metrics["r_metrics"] = r_metrics
            return base_metrics

        pnls = [p.realized_pnl for p in positions]
        wins = [p for p in positions if p.realized_pnl > 0]
        losses = [p for p in positions if p.realized_pnl <= 0]

        total_net_pnl = sum(pnls)
        win_rate = (len(wins) / len(positions)) * 100.0
        avg_trade = float(np.mean(pnls))

        gross_profit = sum(p.realized_pnl for p in wins)
        gross_loss = abs(sum(p.realized_pnl for p in losses))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (gross_profit if gross_profit > 0 else 1.0)

        # Sharpe Ratio (annualized approximation assuming 252 trading days)
        pnl_std = float(np.std(pnls)) if len(pnls) > 1 else 0.0
        sharpe = (avg_trade / pnl_std * np.sqrt(252)) if pnl_std > 0 else 0.0

        # Maximum Drawdown
        equity_curve = [initial_balance]
        for p in pnls:
            equity_curve.append(equity_curve[-1] + p)

        peak = equity_curve[0]
        max_dd = 0.0
        for eq in equity_curve:
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak * 100.0
            if dd > max_dd:
                max_dd = dd

        # Expectancy: (Win% * AvgWin) - (Loss% * AvgLoss)
        avg_win = float(np.mean([p.realized_pnl for p in wins])) if wins else 0.0
        avg_loss = abs(float(np.mean([p.realized_pnl for p in losses]))) if losses else 0.0
        win_pct = len(wins) / len(positions)
        loss_pct = len(losses) / len(positions)
        expectancy = (win_pct * avg_win) - (loss_pct * avg_loss)

        # Error analysis / exit reason attribution
        error_counts: Dict[str, int] = {}
        for p in positions:
            reason = p.exit_reason or "UNKNOWN"
            error_counts[reason] = error_counts.get(reason, 0) + 1

        r_analysis = RMultipleAnalyzer.analyze_positions(positions, initial_balance)

        return {
            "total_trades": len(positions),
            "win_rate_pct": round(win_rate, 2),
            "profit_factor": round(profit_factor, 2),
            "sharpe_ratio": round(sharpe, 2),
            "max_drawdown_pct": round(max_dd, 2),
            "total_net_pnl": round(total_net_pnl, 2),
            "average_trade_pnl": round(avg_trade, 2),
            "expectancy": round(expectancy, 2),
            "error_analysis": error_counts,
            "r_metrics": r_analysis,
        }
