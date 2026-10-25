"""
Hermes Market Interpreter: Interprets deterministic indicators and provides
qualitative critique, live open trade loss mitigation, and psychological check.
Tailored for live account XMGlobal-MT5 9 (335537672, Leverage 1:1000).
"""

import json
import logging
from typing import Optional, Any, List, Dict
from core.models.signal import (
    SignalContract,
    LLMInterpretation,
    SignalDirection,
    SetupType,
    MarketRegime,
    VolatilityState,
    TrendDirection
)
from core.market.analyzer import MultiTimeframeMarketState
from agents.hermes.client import HermesClient

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are Hermes 3, an elite quantitative trading mentor, risk manager, and loss mitigation critic for a live XM MT5 trading account (XMGlobal-MT5 9, Login: 336888981, Leverage: 1:100).
Your core directives:
1. Real money is on the line. NEVER mention "paper", "paper account", "virtual capital", or "ENTER_PAPER".
2. Prioritize capital preservation, mitigating floating drawdown on live open positions, and cutting toxic exposure.
3. If open positions exist with floating losses or without Stop Losses, prioritize explicit loss mitigation rules (emergency stops, partial trims, trailing SL) over new aggressive entries.
4. Output MUST be valid JSON adhering strictly to the requested schema:
{
  "confidence_score": 0.0 to 1.0,
  "reasoning": "brief 1-2 sentence pattern thesis",
  "critique": "brief 1-2 sentence devil's advocate risk warning",
  "recommended_action": "EXECUTE_LIVE" | "MITIGATE_LOSSES" | "PROTECT_CAPITAL" | "STAND_ASIDE" | "TRIM_EXPOSURE",
  "loss_mitigation_plan": "concrete steps to protect open trades and preserve equity",
  "psychological_check": "1 concise sentence reminding the trader of discipline"
}
"""


class HermesMarketInterpreter:
    """
    Prompts Hermes 3 to critique signals and formulate live loss mitigation directives.
    """

    def __init__(self, client: Optional[HermesClient] = None):
        self.client = client or HermesClient()

    def interpret_signal(
        self,
        signal: SignalContract,
        state: MultiTimeframeMarketState,
        open_positions: Optional[List[Dict[str, Any]]] = None,
        account_stats: Optional[Dict[str, Any]] = None
    ) -> LLMInterpretation:
        """
        Produce qualitative interpretation and critique for a candidate signal.
        """
        if signal.direction.value == "NONE":
            return LLMInterpretation(
                confidence_score=0.0,
                reasoning="No deterministic setup detected.",
                critique="Preserve live capital; market is awaiting clear impulse and confluence.",
                recommended_action="STAND_ASIDE",
                loss_mitigation_plan="Hold discipline. Do not open discretionary trades without mathematical alignment.",
                psychological_check="Patience is edge. Do not force trades in neutral conditions."
            )

        pos_context = ""
        if open_positions:
            pos_context = f"\nACTIVE OPEN TRADES IN ACCOUNT ({len(open_positions)} positions):\n"
            for p in open_positions:
                pos_context += f"- {p.get('side')} {p.get('lots', 0.01)} {p.get('symbol')} @ {p.get('entry_price')} (SL: {p.get('stop_loss', 0.0)}, Float PnL: ${p.get('unrealized_pnl', 0.0)})\n"

        acc_login = (account_stats or {}).get("account_login", "336888981")
        prompt = f"""
ANALYZE CANDIDATE SETUP FOR XM MT5 ACCOUNT {acc_login}:
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
{pos_context}
Evaluate setup quality and loss mitigation in valid JSON adhering to schema:
"""
        raw_text = self.client.generate_response_sync(prompt, system_prompt=SYSTEM_PROMPT)

        try:
            clean = raw_text.strip()
            if "```json" in clean:
                clean = clean.split("```json")[1].split("```")[0].strip()
            elif "```" in clean:
                clean = clean.split("```")[1].split("```")[0].strip()

            parsed = json.loads(clean)
            rec_action = str(parsed.get("recommended_action", "PROTECT_CAPITAL"))
            if "PAPER" in rec_action:
                rec_action = "PROTECT_CAPITAL"

            interpretation = LLMInterpretation(
                confidence_score=float(parsed.get("confidence_score", 0.65)),
                reasoning=str(parsed.get("reasoning", "")),
                critique=str(parsed.get("critique", "")),
                recommended_action=rec_action,
                loss_mitigation_plan=str(parsed.get("loss_mitigation_plan", "")),
                psychological_check=str(parsed.get("psychological_check", ""))
            )
        except Exception as e:
            logger.warning(f"Failed to parse Hermes JSON response ({e}). Using default interpretation.")
            interpretation = LLMInterpretation(
                confidence_score=0.65,
                reasoning=f"Confirmed {signal.direction.value} {signal.setup.value} with {signal.higher_tf_bias.value} macro confluence.",
                critique="Ensure stop loss is enforced immediately in MT5; protect live account equity.",
                recommended_action="PROTECT_CAPITAL",
                loss_mitigation_plan="Set hard stop-loss on all open tickets to cap adverse drawdown.",
                psychological_check="Protect your live capital first. Never risk more than predetermined limits."
            )

        signal.llm_interpretation = interpretation
        return interpretation

    def generate_hermes_signal(
        self,
        state: MultiTimeframeMarketState,
        symbol_res: Any,
        open_positions: Optional[List[Dict[str, Any]]] = None,
        account_stats: Optional[Dict[str, Any]] = None
    ) -> SignalContract:
        """
        Directly synthesize an autonomous trading signal and loss mitigation directives
        from Hermes 3:8B on GPU grounded in live multi-timeframe market state and open trades.
        """
        m1 = state.timeframes.get("M1")
        m5 = state.timeframes.get("M5")
        m15 = state.timeframes.get("M15")

        curr_price = m1.forming_bar.close if (m1 and m1.forming_bar) else (
            m1.completed_bar.close if m1 else 4140.0
        )
        atr_m1 = m1.atr.current_atr if m1 else 1.25
        rsi_m15 = round(m15.rsi, 1) if m15 else 50.0
        rsi_m1 = round(m1.rsi, 1) if m1 else 50.0
        res_zones = [round(r.high, 2) for r in m1.resistance_zones] if m1 else []
        sup_zones = [round(s.low, 2) for s in m1.support_zones] if m1 else []

        open_pos_summary = ""
        has_drawdown = False
        if open_positions:
            open_pos_lines = []
            for p in open_positions:
                pos_sym = p.get("symbol", "GOLD#")
                pos_side = p.get("side", "BUY")
                pos_lots = p.get("lots") or p.get("quantity_lots", 0.01)
                pos_entry = p.get("entry_price", 0.0)
                pos_sl = p.get("stop_loss", 0.0)
                pos_tp = p.get("take_profit", 0.0)
                pos_pnl = p.get("unrealized_pnl", 0.0)
                if pos_pnl < 0:
                    has_drawdown = True
                pos_ticket = p.get("ticket") or p.get("id", "")
                sl_str = f"SL: ${pos_sl:.2f}" if pos_sl > 0 else "NO STOP LOSS (CRITICAL RISK)"
                tp_str = f"TP: ${pos_tp:.2f}" if pos_tp > 0 else "TP: None"
                open_pos_lines.append(
                    f"  - Ticket {pos_ticket}: {pos_side} {pos_lots} {pos_sym} @ ${pos_entry:.2f} ({sl_str}, {tp_str}, Floating PnL: ${pos_pnl:.2f})"
                )
            open_pos_summary = "\nActive Live Open Positions in MT5:\n" + "\n".join(open_pos_lines)

        acc_summary = ""
        if account_stats:
            bal = account_stats.get("balance", 1874.19)
            eq = account_stats.get("equity", 1874.19)
            unrl = account_stats.get("unrealized_pnl", 0.0)
            acc_num = account_stats.get("account_login", "336888981")
            acc_summary = f"\nXM MT5 Account Metrics: Balance: ${bal:.2f}, Equity: ${eq:.2f}, Total Floating PnL: ${unrl:.2f} (Leverage 1:100)"

        acc_num = (account_stats or {}).get("account_login", "336888981")
        prompt = f"""You are Hermes 3, elite quantitative mentor and loss mitigation risk manager for XM MT5 account {acc_num}.
Analyze the live market state and open trades for {symbol_res.resolved} ({symbol_res.requested}, Broker: {symbol_res.broker}):
- Live Current Price: {curr_price}
- Macro Bias (D1/H4): {state.macro_bias.value}
- Execution Bias (M15/M5): {state.execution_bias.value}
- Confluence Score: {state.mtf_confluence_score * 100:.0f}%
- Market Regime: {state.market_regime.value}
- M1 ATR: {atr_m1:.2f} (State: {m1.atr.state.value if m1 else 'NORMAL'})
- M15 RSI: {rsi_m15}, M1 RSI: {rsi_m1}
- M1 Resistance Zones: {res_zones}
- M1 Support Zones: {sup_zones}
{acc_summary}
{open_pos_summary}

Directives:
1. Formulate a disciplined trade setup and loss mitigation plan.
2. If open trades are underwater or lack Stop Losses, focus on how to mitigate losses (e.g. set emergency stops, cut toxic legs, trim on bounce).
3. Do NOT recommend paper accounts. Real money is on the line.

Output strictly valid JSON with this exact structure:
{{
  "direction": "BUY" or "SELL",
  "setup": "PULLBACK" or "BREAKOUT" or "REVERSAL",
  "entry_price": {curr_price},
  "stop_loss": float,
  "take_profit": float,
  "confidence_score": 0.0 to 1.0,
  "reasoning": "brief 1-2 sentence pattern thesis",
  "critique": "brief 1-2 sentence risk warning on live balance",
  "recommended_action": "MITIGATE_LOSSES" or "TRIM_EXPOSURE" or "PROTECT_CAPITAL" or "EXECUTE_LIVE",
  "loss_mitigation_plan": "specific actionable loss mitigation steps for open trades",
  "psychological_check": "1 sentence discipline reminder"
}}"""

        raw_text = self.client.generate_response_sync(prompt, system_prompt=SYSTEM_PROMPT)
        parsed = {}
        try:
            clean = raw_text.strip()
            if "```json" in clean:
                clean = clean.split("```json")[1].split("```")[0].strip()
            elif "```" in clean:
                clean = clean.split("```")[1].split("```")[0].strip()
            parsed = json.loads(clean)
            if "signal" in parsed and isinstance(parsed["signal"], dict):
                parsed = parsed["signal"]
        except Exception as e:
            logger.warning(f"Error parsing Hermes raw output: {e}")

        # Parse direction
        raw_dir = str(parsed.get("direction", "")).upper()
        if "BUY" in raw_dir or "BULL" in raw_dir:
            direction_enum = SignalDirection.BUY
        elif "SELL" in raw_dir or "BEAR" in raw_dir:
            direction_enum = SignalDirection.SELL
        else:
            direction_enum = SignalDirection.BUY if state.macro_bias.value == "BULLISH" else SignalDirection.SELL

        # Parse setup
        raw_setup = str(parsed.get("setup", "")).upper()
        if "BREAK" in raw_setup:
            setup_enum = SetupType.BREAKOUT
        elif "REV" in raw_setup:
            setup_enum = SetupType.REVERSAL
        else:
            setup_enum = SetupType.PULLBACK

        # Numeric levels with mathematical fallback anchors
        entry_price = float(parsed.get("entry_price") or curr_price)
        raw_sl = parsed.get("stop_loss")
        raw_tp = parsed.get("take_profit")

        if direction_enum == SignalDirection.BUY:
            sl_price = float(raw_sl) if raw_sl and float(raw_sl) < entry_price else round(entry_price - max(2.5, 2.0 * atr_m1), 2)
            tp_price = float(raw_tp) if raw_tp and float(raw_tp) > entry_price else round(entry_price + max(4.0, 3.5 * atr_m1), 2)
        else:
            sl_price = float(raw_sl) if raw_sl and float(raw_sl) > entry_price else round(entry_price + max(2.5, 2.0 * atr_m1), 2)
            tp_price = float(raw_tp) if raw_tp and float(raw_tp) < entry_price else round(entry_price - max(4.0, 3.5 * atr_m1), 2)

        risk_pts = round(abs(entry_price - sl_price), 2)
        reward_pts = round(abs(tp_price - entry_price), 2)
        rr_ratio = round(reward_pts / risk_pts, 2) if risk_pts > 0 else 1.5

        rec_act = str(parsed.get("recommended_action") or ("MITIGATE_LOSSES" if has_drawdown else "PROTECT_CAPITAL"))
        if "PAPER" in rec_act.upper():
            rec_act = "MITIGATE_LOSSES" if has_drawdown else "PROTECT_CAPITAL"

        mitigation_text = str(parsed.get("loss_mitigation_plan") or (
            "Enforce immediate emergency stop loss on all open positions to prevent margin liquidation. Trim conflicting positions on next liquidity test."
            if has_drawdown else "Monitor positions closely with trailing stop to secure realized gains."
        ))

        interpretation = LLMInterpretation(
            confidence_score=float(parsed.get("confidence_score") or 0.78),
            reasoning=str(parsed.get("reasoning") or f"Hermes 3 evaluated {symbol_res.resolved} on XM with {direction_enum.value} momentum."),
            critique=str(parsed.get("critique") or "Maintain strict stop adherence to protect live capital against volatility spikes."),
            recommended_action=rec_act,
            loss_mitigation_plan=mitigation_text,
            psychological_check=str(parsed.get("psychological_check") or "Focus on capital preservation and process discipline over emotional attachment.")
        )

        signal = SignalContract(
            symbol_requested=symbol_res.requested,
            symbol_resolved=symbol_res.resolved,
            broker_name=symbol_res.broker,
            direction=direction_enum,
            setup=setup_enum,
            market_regime=state.market_regime,
            entry_price=entry_price,
            stop_loss=sl_price,
            take_profit=tp_price,
            risk_reward_ratio=rr_ratio,
            risk_points=risk_pts,
            volatility_state=m1.atr.state if m1 else VolatilityState.NORMAL,
            higher_tf_bias=state.macro_bias,
            mtf_confluence_score=state.mtf_confluence_score,
            forming_bar_price=curr_price,
            llm_interpretation=interpretation
        )
        return signal

    def generate_loss_mitigation_plan(
        self,
        open_positions: List[Dict[str, Any]],
        account_stats: Dict[str, Any],
        state: MultiTimeframeMarketState,
        symbol_res: Any
    ) -> Dict[str, Any]:
        """
        Specialized audit of open live positions to formulate concrete loss mitigation instructions.
        """
        acc_num = account_stats.get("account_login", "336888981") if account_stats else "336888981"
        if not open_positions:
            return {
                "risk_level": "STABLE",
                "drawdown_pct": 0.0,
                "net_exposure": "FLAT",
                "summary": f"No active open positions on XM MT5 account {acc_num}. Full capital protected.",
                "tactical_steps": ["Maintain discipline; await high-confluence mathematical setups."],
                "recommended_action": "STAND_ASIDE",
                "psychological_guardrail": "Flat is a valid and profitable position when no high-probability edge exists."
            }

        bal = account_stats.get("balance", 1874.19)
        eq = account_stats.get("equity", 1874.19)
        unrl = account_stats.get("unrealized_pnl", 0.0)
        drawdown_pct = abs(unrl / bal * 100.0) if bal > 0 and unrl < 0 else 0.0

        pos_lines = []
        for p in open_positions:
            sym = p.get("symbol", "GOLD")
            side = p.get("side", "BUY")
            lots = p.get("lots") or p.get("quantity_lots", 0.01)
            entry = p.get("entry_price", 0.0)
            cur_p = p.get("current_price", 0.0)
            sl = p.get("stop_loss", 0.0)
            tp = p.get("take_profit", 0.0)
            pnl = p.get("unrealized_pnl", 0.0)
            tkt = p.get("ticket") or p.get("id", "")
            pos_lines.append(
                f"- Ticket {tkt}: {side} {lots} {sym} @ ${entry:.2f}, Cur: ${cur_p:.2f}, SL: ${sl:.2f}, TP: ${tp:.2f}, PnL: ${pnl:.2f}"
            )

        prompt = f"""You are Hermes 3, elite quantitative risk manager and turnaround specialist for XM MT5 account (Login: {acc_num}, Leverage: 1:100).
Current live balance: ${bal:.2f}, Equity: ${eq:.2f}, Floating PnL: ${unrl:.2f} ({drawdown_pct:.1f}% drawdown).
Active open positions:
{chr(10).join(pos_lines)}

Current Market Context for {symbol_res.resolved}:
- Macro Bias (D1/H4): {state.macro_bias.value}
- Execution Bias (M15/M5): {state.execution_bias.value}
- Confluence: {state.mtf_confluence_score * 100:.0f}%
- Market Regime: {state.market_regime.value}

Task:
Formulate an urgent, concrete Loss Mitigation Plan to protect remaining live equity (${eq:.2f}) from margin call or total wipeout.
NEVER suggest paper trading.

Respond strictly in valid JSON:
{{
  "risk_level": "CRITICAL" | "ELEVATED" | "MODERATE",
  "summary": "1-2 sentence executive assessment of account danger and floating exposure",
  "recommended_action": "MITIGATE_LOSSES" | "TRIM_EXPOSURE" | "PROTECT_CAPITAL",
  "tactical_steps": [
    "Step 1: ...",
    "Step 2: ..."
  ],
  "psychological_guardrail": "1 sentence anti-panic / discipline rule"
}}"""

        raw_text = self.client.generate_response_sync(prompt, system_prompt=SYSTEM_PROMPT)
        try:
            clean = raw_text.strip()
            if "```json" in clean:
                clean = clean.split("```json")[1].split("```")[0].strip()
            elif "```" in clean:
                clean = clean.split("```")[1].split("```")[0].strip()
            parsed = json.loads(clean)
            return {
                "risk_level": parsed.get("risk_level", "CRITICAL" if drawdown_pct > 20 else "ELEVATED"),
                "drawdown_pct": round(drawdown_pct, 1),
                "summary": parsed.get("summary", f"Live account drawdown is {drawdown_pct:.1f}% with unhedged floating exposure."),
                "recommended_action": parsed.get("recommended_action", "MITIGATE_LOSSES"),
                "tactical_steps": parsed.get("tactical_steps", [
                    "Place emergency stop-loss on all open tickets immediately.",
                    "Close or reduce the oldest underwater position to free margin.",
                    "Halt any new discretionary entries until equity recovers."
                ]),
                "psychological_guardrail": parsed.get("psychological_guardrail", "Cutting a loss is an act of capital preservation, not defeat.")
            }
        except Exception as e:
            logger.warning(f"Error parsing loss mitigation JSON from Hermes ({e})")
            return {
                "risk_level": "CRITICAL" if drawdown_pct > 20 else "ELEVATED",
                "drawdown_pct": round(drawdown_pct, 1),
                "summary": f"Live account is at {drawdown_pct:.1f}% drawdown. Open tickets lack protective stop losses.",
                "recommended_action": "MITIGATE_LOSSES",
                "tactical_steps": [
                    "Immediately add emergency stop losses to tickets lacking SL.",
                    "Trim losing long positions if price breaks below M1 support.",
                    "Strictly prohibit adding to losing positions (no martingale/averaging down)."
                ],
                "psychological_guardrail": "Protect your remaining capital first. Live equity survival always precedes profit."
            }

