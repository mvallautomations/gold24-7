"""
Hermes Trade Coach: Post-trade feedback, performance critique, and journal debrief.
"""

from typing import Dict, Any, Optional
from core.models.trade import PaperPosition
from agents.hermes.client import HermesClient
import logging

logger = logging.getLogger(__name__)


class HermesTradeCoach:
    """
    Evaluates completed paper trades and writes journal debriefs.
    Identifies behavioral leaks (e.g. premature exits, holding losers, revenge trading).
    """

    def __init__(self, client: Optional[HermesClient] = None):
        self.client = client or HermesClient()

    def generate_trade_review(self, position: PaperPosition) -> str:
        """
        Generate qualitative post-trade feedback for OpenTraderWorld journal.
        """
        pnl_str = f"+${position.realized_pnl:.2f}" if position.realized_pnl >= 0 else f"-${abs(position.realized_pnl):.2f}"
        outcome = "WIN" if position.realized_pnl > 0 else "LOSS"

        prompt = f"""
REVIEW COMPLETED PAPER TRADE:
- Instrument: {position.symbol}
- Side: {position.side.value.upper()}
- Entry: {position.entry_price} | Exit: {position.exit_price}
- Stop Loss: {position.stop_loss} | Take Profit: {position.take_profit}
- Result: {outcome} ({pnl_str})
- Exit Reason: {position.exit_reason}
- Tags: {', '.join(position.tags)}

Provide a concise 2-sentence quantitative coach review assessing whether the execution followed the plan and what can be learned.
"""
        response = self.client.generate_response_sync(
            prompt,
            system_prompt="You are Hermes 3, a supportive yet disciplined institutional trading coach. Be direct, concise, and constructive."
        )

        feedback = response.strip()
        if not feedback:
            feedback = f"Trade exited at {position.exit_reason} resulting in {pnl_str}. Plan rules were executed systematically."

        return feedback
