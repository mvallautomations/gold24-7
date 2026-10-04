"""
Hermes Market Interpreter: Interprets deterministic indicators and provides
qualitative critique, devil's advocate risks, and psychological check.
"""

import json
import logging
from typing import Optional
from core.models.signal import SignalContract, LLMInterpretation
from core.market.analyzer import MultiTimeframeMarketState
from agents.hermes.client import HermesClient

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are Hermes 3, an expert quantitative trading mentor and risk critic.
Your role is to strictly INTERPRET deterministic market indicators and CRITIQUE trading setups.
Rules:
1. You do NOT compute numerical prices or indicators; they are provided by deterministic math.
2. Provide a skeptical critique: What could go wrong with this trade?
3. Provide an emotional/cognitive sanity check (anti-FOMO, ADHD discipline).
4. Output MUST be valid JSON adhering strictly to this schema:
{
  "confidence_score": 0.0 to 1.0,
  "reasoning": "brief 1-2 sentence pattern explanation",
  "critique": "brief 1-2 sentence devil's advocate risk warning",
  "recommended_action": "ENTER_PAPER" | "WATCH" | "SKIP",
  "psychological_check": "1 concise sentence reminding the trader of discipline"
}
"""


class HermesMarketInterpreter:
    """
    Prompts Hermes 3 to critique deterministic signals.
    """

    def __init__(self, client: Optional[HermesClient] = None):
        self.client = client or HermesClient()

    def interpret_signal(
        self,
        signal: SignalContract,
        state: MultiTimeframeMarketState
    ) -> LLMInterpretation:
        """
        Produce qualitative interpretation and critique for a candidate signal.
        """
        # If no active direction, no need for deep LLM evaluation
        if signal.direction.value == "NONE":
            return LLMInterpretation(
                confidence_score=0.0,
                reasoning="No deterministic setup detected.",
                critique="Market is awaiting clear impulse and confluence.",
                recommended_action="WATCH",
                psychological_check="Patience is edge. Do not force trades in neutral conditions."
            )

        prompt = f"""
ANALYZE CANDIDATE SETUP:
- Symbol: {signal.symbol_resolved} (Broker: {signal.broker_name})
- Direction: {signal.direction.value}
- Setup: {signal.setup.value}
- Market Regime: {signal.market_regime.value}
- Macro Bias: {signal.higher_tf_bias.value}
- MTF Confluence: {signal.mtf_confluence_score * 100:.0f}%
- Volatility: {signal.volatility_state.value}
- Entry Price: {signal.entry_price}
- Stop Loss: {signal.stop_loss} (Risk Points: {signal.risk_points})
- Take Profit: {signal.take_profit} (R:R Ratio: {signal.risk_reward_ratio:.2f})

Evaluate the quality of this setup and provide your critique in valid JSON:
"""
        raw_text = self.client.generate_response_sync(prompt, system_prompt=SYSTEM_PROMPT)

        try:
            # Clean possible markdown fence
            clean = raw_text.strip()
            if "```json" in clean:
                clean = clean.split("```json")[1].split("```")[0].strip()
            elif "```" in clean:
                clean = clean.split("```")[1].split("```")[0].strip()

            parsed = json.loads(clean)
            interpretation = LLMInterpretation(
                confidence_score=float(parsed.get("confidence_score", 0.65)),
                reasoning=str(parsed.get("reasoning", "")),
                critique=str(parsed.get("critique", "")),
                recommended_action=str(parsed.get("recommended_action", "WATCH")),
                psychological_check=str(parsed.get("psychological_check", ""))
            )
        except Exception as e:
            logger.warning(f"Failed to parse Hermes JSON response ({e}). Using default interpretation.")
            interpretation = LLMInterpretation(
                confidence_score=0.65,
                reasoning=f"Confirmed {signal.direction.value} {signal.setup.value} with {signal.higher_tf_bias.value} macro confluence.",
                critique="Ensure stop loss is respected at all times; watch for volatility expansion.",
                recommended_action="ENTER_PAPER",
                psychological_check="Execute without hesitation; let the statistical edge play out."
            )

        signal.llm_interpretation = interpretation
        return interpretation
