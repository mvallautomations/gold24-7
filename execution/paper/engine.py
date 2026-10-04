"""
Simulated Paper Trading Engine: Realistic virtual execution, slippage modeling,
lot sizing, position tracking, and bracket order fulfillment.
"""

from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
import math
import logging

from core.models.signal import SignalContract, SignalDirection
from core.models.trade import PaperOrder, PaperPosition, PositionSide, TradeStatus
from execution.safety.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)


class PaperTradingEngine:
    """
    Simulated order book and position manager.
    Operates completely decoupled from live MT5 order pipelines.
    """

    def __init__(
        self,
        initial_balance: float = 10000.0,
        risk_per_trade_pct: float = 1.0,
        slippage_points: float = 1.5,
        fee_per_lot: float = 3.50  # $3.50 per standard lot turn
    ):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.equity = initial_balance
        self.risk_per_trade_pct = risk_per_trade_pct
        self.slippage_points = slippage_points
        self.fee_per_lot = fee_per_lot

        self.open_positions: Dict[str, PaperPosition] = {}
        self.closed_positions: List[PaperPosition] = []
        self.circuit_breaker = CircuitBreaker()

    def calculate_lots(
        self,
        stop_distance: float,
        tick_size: float = 0.01,
        tick_value: float = 1.0,
        min_lot: float = 0.01,
        max_lot: float = 50.0,
        lot_step: float = 0.01
    ) -> float:
        """
        Calculate precise position size based on balance and stop loss distance.
        """
        risk_money = self.balance * (self.risk_per_trade_pct / 100.0)
        ticks_at_risk = stop_distance / (tick_size or 0.01)
        loss_per_lot = ticks_at_risk * (tick_value or 1.0)

        if loss_per_lot <= 0:
            return min_lot

        raw_lots = risk_money / loss_per_lot
        stepped_lots = math.floor(raw_lots / lot_step) * lot_step
        clipped_lots = max(min_lot, min(stepped_lots, max_lot))
        return round(clipped_lots, 2)

    def execute_signal(
        self,
        signal: SignalContract,
        point: float = 0.01,
        tick_size: float = 0.01,
        tick_value: float = 1.0
    ) -> Optional[PaperPosition]:
        """
        Submit a validated paper trade signal for execution.
        """
        # Safety gate
        if not self.circuit_breaker.can_open_position(len(self.open_positions), self.balance):
            logger.warning("Paper execution rejected by Circuit Breaker.")
            return None

        # Anti-stacking: check if symbol already open
        for pos in self.open_positions.values():
            if pos.symbol == signal.symbol_resolved and pos.status == TradeStatus.OPEN:
                logger.warning(f"Position already open for {signal.symbol_resolved}. Skipping.")
                return None

        side = PositionSide.LONG if signal.direction == SignalDirection.BUY else PositionSide.SHORT
        stop_dist = abs(signal.entry_price - signal.stop_loss)
        lots = self.calculate_lots(stop_dist, tick_size, tick_value)

        # Apply slippage modeling
        slippage_delta = self.slippage_points * point
        if side == PositionSide.LONG:
            fill_price = signal.entry_price + slippage_delta
        else:
            fill_price = signal.entry_price - slippage_delta

        fees = round(lots * self.fee_per_lot, 2)

        position = PaperPosition(
            order_id=signal.signal_id,
            signal_id=signal.signal_id,
            symbol=signal.symbol_resolved,
            side=side,
            entry_price=round(fill_price, 4),
            current_price=round(fill_price, 4),
            quantity_lots=lots,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            fees=fees,
            slippage_points=self.slippage_points,
            tags=[signal.setup.value, "PAPER", "GOLD24-7"]
        )

        self.open_positions[position.position_id] = position
        logger.info(f"Opened PAPER {side.value.upper()} {lots} lots on {position.symbol} at {position.entry_price}")
        return position

    def on_price_update(
        self,
        symbol: str,
        high: float,
        low: float,
        close: float,
        timestamp: Optional[datetime] = None
    ) -> List[PaperPosition]:
        """
        Process incoming candle/tick price update to check for TP/SL fills.
        """
        closed_this_tick: List[PaperPosition] = []

        for pos_id, pos in list(self.open_positions.items()):
            if pos.symbol != symbol:
                continue

            pos.current_price = close
            now_ts = timestamp or datetime.now(timezone.utc)

            # Check LONG fills
            if pos.side == PositionSide.LONG:
                # Did low hit SL?
                if low <= pos.stop_loss:
                    pos.exit_price = pos.stop_loss
                    pos.exit_reason = "SL_HIT"
                    pos.status = TradeStatus.CLOSED
                    pos.closed_at = now_ts
                # Did high hit TP?
                elif high >= pos.take_profit:
                    pos.exit_price = pos.take_profit
                    pos.exit_reason = "TP_HIT"
                    pos.status = TradeStatus.CLOSED
                    pos.closed_at = now_ts

            # Check SHORT fills
            elif pos.side == PositionSide.SHORT:
                # Did high hit SL?
                if high >= pos.stop_loss:
                    pos.exit_price = pos.stop_loss
                    pos.exit_reason = "SL_HIT"
                    pos.status = TradeStatus.CLOSED
                    pos.closed_at = now_ts
                # Did low hit TP?
                elif low <= pos.take_profit:
                    pos.exit_price = pos.take_profit
                    pos.exit_reason = "TP_HIT"
                    pos.status = TradeStatus.CLOSED
                    pos.closed_at = now_ts

            if pos.status == TradeStatus.CLOSED:
                # Compute Realized PnL ($)
                price_diff = (pos.exit_price - pos.entry_price) if pos.side == PositionSide.LONG else (pos.entry_price - pos.exit_price)
                # Standard contract: 1 lot Gold = 100 oz ($1 move = $100 per lot). Forex = 100,000.
                multiplier = 100.0 if "XAU" in symbol or "GAU" in symbol or "GOLD" in symbol else (
                    1.0 if "BTC" in symbol or "ETH" in symbol else 100000.0
                )
                gross_pnl = price_diff * pos.quantity_lots * multiplier
                net_pnl = round(gross_pnl - pos.fees, 2)
                pos.realized_pnl = net_pnl

                self.balance = round(self.balance + net_pnl, 2)
                self.circuit_breaker.record_closed_trade(net_pnl)

                del self.open_positions[pos_id]
                self.closed_positions.append(pos)
                closed_this_tick.append(pos)
                logger.info(f"Closed PAPER position {pos_id} [{pos.exit_reason}]: Net PnL: ${net_pnl} | New Balance: ${self.balance}")

        # Update equity
        unrealized = 0.0
        for pos in self.open_positions.values():
            price_diff = (pos.current_price - pos.entry_price) if pos.side == PositionSide.LONG else (pos.entry_price - pos.current_price)
            multiplier = 100.0 if "XAU" in symbol or "GAU" in symbol or "GOLD" in symbol else (
                1.0 if "BTC" in symbol or "ETH" in symbol else 100000.0
            )
            unrealized += (price_diff * pos.quantity_lots * multiplier) - pos.fees
        self.equity = round(self.balance + unrealized, 2)

        return closed_this_tick

    def get_summary(self) -> Dict[str, Any]:
        """Performance summary metrics."""
        wins = [p for p in self.closed_positions if p.realized_pnl > 0]
        losses = [p for p in self.closed_positions if p.realized_pnl <= 0]
        total_pnl = sum(p.realized_pnl for p in self.closed_positions)
        win_rate = (len(wins) / len(self.closed_positions) * 100.0) if self.closed_positions else 0.0

        gross_profit = sum(p.realized_pnl for p in wins)
        gross_loss = abs(sum(p.realized_pnl for p in losses))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (gross_profit if gross_profit > 0 else 1.0)

        return {
            "initial_balance": self.initial_balance,
            "current_balance": self.balance,
            "equity": self.equity,
            "total_trades": len(self.closed_positions),
            "open_positions": len(self.open_positions),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate_pct": round(win_rate, 2),
            "total_realized_pnl": round(total_pnl, 2),
            "profit_factor": round(profit_factor, 2),
            "circuit_breaker_tripped": self.circuit_breaker.is_tripped,
        }
