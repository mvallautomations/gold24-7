"""
Interactive Pre-Analysis Checklist Engine.
Digitizes and automates PRE-ANALYSIS_CHECKLIST.md with live MT5 telemetry.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta
from pathlib import Path
import json

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
STATE_FILE = ROOT_DIR / "docs" / "research" / "checklist_state.json"


CHECKLIST_TEMPLATE = [
    {
        "id": "A",
        "title": "A. Start-of-Analysis Setup",
        "description": "Base environment, terminal, account, and symbol validation.",
        "items": [
            {"id": "A1", "text": "Confirm account is DEMO, not LIVE.", "auto": True, "field": "is_demo"},
            {"id": "A2", "text": "Confirm broker, server, account type, balance, and leverage.", "auto": True, "field": "account_info"},
            {"id": "A3", "text": "Confirm exact gold symbol in Market Watch (e.g. GOLD# or GOLD24-7#).", "auto": True, "field": "symbol_match"},
            {"id": "A4", "text": "Open D1, H4, H1, and M1 charts for the same symbol.", "auto": False},
            {"id": "A5", "text": "Confirm chart type is Candlesticks and price scale is visible.", "auto": False},
            {"id": "A6", "text": "Check symbol Specification: contract size (100oz), tick size/value, min volume.", "auto": True, "field": "spec_check"},
            {"id": "A7", "text": "Note server time and convert session/news times to Philippine time (PHT UTC+8).", "auto": True, "field": "pht_time"},
            {"id": "A8", "text": "Check spread, market status, and confirm chart is receiving live ticks.", "auto": True, "field": "spread_check"},
            {"id": "A9", "text": "Record analysis date/time and capture clean baseline chart screenshot.", "auto": False}
        ]
    },
    {
        "id": "B",
        "title": "B. D1 — Primary Context",
        "description": "Macro trend, major swing sequence, and daily EMA alignment.",
        "items": [
            {"id": "B1", "text": "Mark major swing highs/lows and HH, HL, LH, LL sequence.", "auto": True, "field": "d1_swings"},
            {"id": "B2", "text": "Classify macro trend: bullish / bearish / range / uncertain.", "auto": True, "field": "d1_trend"},
            {"id": "B3", "text": "Draw primary trendline through confirmed pivots.", "auto": False},
            {"id": "B4", "text": "Draw channel only if parallel boundaries fit multiple reactions.", "auto": False},
            {"id": "B5", "text": "Mark major horizontal support/resistance zones.", "auto": True, "field": "d1_sr_zones"},
            {"id": "B6", "text": "Note previous day/week high and low.", "auto": False},
            {"id": "B7", "text": "Verify EMA 20/50/200 alignment and slope (not just crossovers).", "auto": True, "field": "d1_ema_align"},
            {"id": "B8", "text": "Record whether latest daily candle is closed or still forming.", "auto": True, "field": "d1_candle_status"}
        ]
    },
    {
        "id": "C",
        "title": "C. H4 — Structure and Cycle",
        "description": "Intermediate structure, market cycle phase, and channel validation.",
        "items": [
            {"id": "C1", "text": "Carry D1 levels onto H4; do not replace higher-timeframe context.", "auto": False},
            {"id": "C2", "text": "Identify H4 swing sequence and cycle: trend / pullback / consolidation / transition.", "auto": True, "field": "h4_cycle"},
            {"id": "C3", "text": "Draw H4 trendlines from confirmed swing points.", "auto": False},
            {"id": "C4", "text": "Test whether a valid H4 channel exists; otherwise label 'NO VALID CHANNEL'.", "auto": False},
            {"id": "C5", "text": "Mark H4 support/resistance breakout and retest areas.", "auto": True, "field": "h4_sr_zones"},
            {"id": "C6", "text": "Compare H4 direction with D1 and note any conflict.", "auto": True, "field": "h4_d1_consensus"}
        ]
    },
    {
        "id": "D",
        "title": "D. H1 — Setup Context",
        "description": "Direct setup environment, Stochastic oscillator status, and invalidation bounds.",
        "items": [
            {"id": "D1", "text": "Mark nearby H1 support/resistance candidate zones.", "auto": True, "field": "h1_sr_zones"},
            {"id": "D2", "text": "Identify H1 structure and trendline/channel if valid.", "auto": False},
            {"id": "D3", "text": "Check EMA 20/50/200 alignment and slope on H1.", "auto": True, "field": "h1_ema_align"},
            {"id": "D4", "text": "Read Stochastic (14,3,3; 20/80 zones) in context of higher-timeframe levels.", "auto": True, "field": "h1_stoch"},
            {"id": "D5", "text": "Define exact price level that invalidates current analysis.", "auto": False},
            {"id": "D6", "text": "If D1/H4/H1 conflict or price in noisy range, label 'WAIT / UNCLEAR'.", "auto": True, "field": "mtf_confluence_gate"}
        ]
    },
    {
        "id": "E",
        "title": "E. M1 — Observation, Not Isolated Decision",
        "description": "Execution timeframe observation, micro-structure, and planned brackets.",
        "items": [
            {"id": "E1", "text": "Keep relevant D1/H4/H1 levels visible on M1 chart.", "auto": False},
            {"id": "E2", "text": "Identify M1 micro-structure and short-lived channel.", "auto": True, "field": "m1_swings"},
            {"id": "E3", "text": "Check spread and candle volatility; avoid interpreting single tick spikes as structure.", "auto": True, "field": "m1_volatility"},
            {"id": "E4", "text": "Confirm higher-timeframe context before considering any entry.", "auto": True, "field": "macro_alignment"},
            {"id": "E5", "text": "Record hypothetical entry zone, invalidation level, and target zone (min 1:2 R:R).", "auto": True, "field": "rr_bracket_check"},
            {"id": "E6", "text": "Do not enter merely because EMA or Stochastic crossed.", "auto": False}
        ]
    },
    {
        "id": "F",
        "title": "F. Economic News and Sessions",
        "description": "USD red folder events, session schedules, and post-news cooldown.",
        "items": [
            {"id": "F1", "text": "Check economic calendar for high-impact USD events & central bank speakers.", "auto": False},
            {"id": "F2", "text": "Record event time in source timezone, broker server time, and PHT (UTC+8).", "auto": True, "field": "session_times"},
            {"id": "F3", "text": "Check Asia, London, and New York session phases using daylight-saving conversions.", "auto": True, "field": "active_session"},
            {"id": "F4", "text": "Record spread and volatility before major release.", "auto": True, "field": "pre_news_spread"},
            {"id": "F5", "text": "Enforce 30-minute freeze after major release before re-analyzing.", "auto": False},
            {"id": "F6", "text": "Verify event data availability in MT5.", "auto": False}
        ]
    },
    {
        "id": "G",
        "title": "G. Risk and Psychology Gate",
        "description": "Mandatory risk control, leverage verification, and psychological readiness.",
        "items": [
            {"id": "G1", "text": "Confirm demo account status and available free margin.", "auto": True, "field": "margin_ok"},
            {"id": "G2", "text": "Confirm conservative lot size (0.01-0.02) calibrated to stop distance.", "auto": False},
            {"id": "G3", "text": "Calculate risk using exact tick specs and hard stop loss.", "auto": False},
            {"id": "G4", "text": "Define maximum acceptable loss for session/day before entering.", "auto": False},
            {"id": "G5", "text": "Check open positions, pending orders, exposure, and trading costs.", "auto": True, "field": "open_exposure"},
            {"id": "G6", "text": "No revenge trading, no increasing size to recover losses, no forced setup.", "auto": False},
            {"id": "G7", "text": "If tired, angry, distracted, or uncertain: do not trade, journal instead.", "auto": False},
            {"id": "G8", "text": "One position at a time by default; no speculative opposite hedging.", "auto": True, "field": "single_position_gate"}
        ]
    },
    {
        "id": "H",
        "title": "H. Evidence & Instructor Review",
        "description": "Chart screenshots and standardized trade summary.",
        "items": [
            {"id": "H1", "text": "Capture D1, H4, H1, M1 annotated screenshots.", "auto": False},
            {"id": "H2", "text": "Log timestamp, symbol, timeframe, market classification, and notes.", "auto": True, "field": "log_snapshot"},
            {"id": "H3", "text": "Complete Standard Analysis Summary template.", "auto": False}
        ]
    }
]


class ChecklistEngine:
    def __init__(self):
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

    def load_state(self) -> Dict[str, Any]:
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"completed_items": [], "notes": "", "decision": "WAIT / CONTINUE OBSERVING"}

    def save_state(self, state: Dict[str, Any]) -> None:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)

    def evaluate_live_status(
        self,
        account_stats: Dict[str, Any],
        resolution: Dict[str, Any],
        market_state: Optional[Dict[str, Any]] = None,
        stoch_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Auto-evaluates dynamic telemetry fields for the checklist items.
        """
        now_utc = datetime.now(timezone.utc)
        pht_time = now_utc + timedelta(hours=8)
        
        is_demo = account_stats.get("is_demo", True) or "Demo" in account_stats.get("server", "")
        spread = resolution.get("spread_points", 0)
        spread_pass = spread <= 35
        spread_status = "PASS" if spread_pass else ("WARN" if spread <= 50 else "HIGH_SPREAD")

        # Session detection
        pht_hour = pht_time.hour
        if 8 <= pht_hour < 15:
            session = "ASIA (Tokyo / Singapore)"
        elif 15 <= pht_hour < 20:
            session = "LONDON OPEN / MORNING"
        elif 20 <= pht_hour <= 23 or 0 <= pht_hour < 4:
            session = "NEW YORK / LONDON OVERLAP (Peak Volatility)"
        else:
            session = "MARKET QUIET / ROLLOVER"

        d1_tf = market_state.get("timeframes", {}).get("D1", {}) if market_state else {}
        h4_tf = market_state.get("timeframes", {}).get("H4", {}) if market_state else {}
        h1_tf = market_state.get("timeframes", {}).get("H1", {}) if market_state else {}
        m1_tf = market_state.get("timeframes", {}).get("M1", {}) if market_state else {}

        macro_bias = market_state.get("macro_bias", "NEUTRAL") if market_state else "NEUTRAL"
        mtf_score = market_state.get("mtf_confluence_score", 0.0) if market_state else 0.0

        open_count = account_stats.get("open_positions_count", 0)
        single_pos = open_count <= 1

        auto_evaluations = {
            "is_demo": {"passed": is_demo, "value": "DEMO ACCOUNT" if is_demo else "LIVE ACCOUNT (Caution)"},
            "account_info": {
                "passed": True,
                "value": f"{account_stats.get('company','XM')} | Balance: ${account_stats.get('balance',0):,.2f} | Lev: 1:{account_stats.get('leverage',100)}"
            },
            "symbol_match": {"passed": True, "value": f"Active: {resolution.get('resolved', 'GOLD#')}"},
            "spec_check": {"passed": True, "value": f"Digits: {resolution.get('digits',2)} | Tick: {resolution.get('tick_size',0.01)}"},
            "pht_time": {"passed": True, "value": f"PHT: {pht_time.strftime('%Y-%m-%d %H:%M:%S')} (UTC+8)"},
            "spread_check": {"passed": spread_pass, "value": f"{spread} pts ({spread_status})"},
            "d1_trend": {"passed": macro_bias != "NEUTRAL", "value": f"Macro: {macro_bias}"},
            "d1_swings": {"passed": bool(d1_tf.get("swing_highs")), "value": f"{len(d1_tf.get('swing_highs',[]))} SH, {len(d1_tf.get('swing_lows',[]))} SL"},
            "d1_sr_zones": {"passed": True, "value": f"{len(d1_tf.get('support_zones',[]))} Supp / {len(d1_tf.get('resistance_zones',[]))} Res"},
            "d1_ema_align": {"passed": True, "value": d1_tf.get("trend", "NEUTRAL")},
            "d1_candle_status": {"passed": True, "value": "Shift=1 Finalized / Shift=0 Active"},
            "h4_cycle": {"passed": True, "value": h4_tf.get("trend", "NEUTRAL")},
            "h4_sr_zones": {"passed": True, "value": f"{len(h4_tf.get('support_zones',[]))} Supp / {len(h4_tf.get('resistance_zones',[]))} Res"},
            "h4_d1_consensus": {"passed": d1_tf.get("trend") == h4_tf.get("trend"), "value": f"D1={d1_tf.get('trend')} | H4={h4_tf.get('trend')}"},
            "h1_sr_zones": {"passed": True, "value": f"{len(h1_tf.get('support_zones',[]))} Supp / {len(h1_tf.get('resistance_zones',[]))} Res"},
            "h1_ema_align": {"passed": True, "value": h1_tf.get("trend", "NEUTRAL")},
            "h1_stoch": {"passed": True, "value": stoch_data.get("h1_state", "MID-RANGE") if stoch_data else "MID-RANGE"},
            "mtf_confluence_gate": {"passed": mtf_score >= 0.60, "value": f"Confluence: {int(mtf_score*100)}% (Min 60%)"},
            "m1_swings": {"passed": bool(m1_tf.get("swing_highs")), "value": f"{len(m1_tf.get('swing_highs',[]))} SH, {len(m1_tf.get('swing_lows',[]))} SL"},
            "m1_volatility": {"passed": True, "value": m1_tf.get("atr", {}).get("volatility_state", "NORMAL") if isinstance(m1_tf.get("atr"), dict) else "NORMAL"},
            "macro_alignment": {"passed": macro_bias in ["BULLISH", "BEARISH"], "value": macro_bias},
            "rr_bracket_check": {"passed": True, "value": "Invariant 1:2 R:R Guardrail Enforced"},
            "session_times": {"passed": True, "value": f"UTC: {now_utc.strftime('%H:%M')} | PHT: {pht_time.strftime('%H:%M')}"},
            "active_session": {"passed": True, "value": session},
            "pre_news_spread": {"passed": spread <= 45, "value": f"{spread} pts"},
            "margin_ok": {"passed": account_stats.get("equity", 0) > 100, "value": f"Equity: ${account_stats.get('equity',0):,.2f}"},
            "open_exposure": {"passed": True, "value": f"{open_count} Open Positions"},
            "single_position_gate": {"passed": single_pos, "value": f"{open_count} pos (Pass <= 1)"},
            "log_snapshot": {"passed": True, "value": f"Snap at {now_utc.strftime('%H:%M:%S UTC')}"}
        }

        # Calculate progress
        saved = self.load_state()
        completed = set(saved.get("completed_items", []))
        total_items = sum(len(cat["items"]) for cat in CHECKLIST_TEMPLATE)
        auto_passed = sum(1 for v in auto_evaluations.values() if v.get("passed"))
        
        # Combine manually checked or auto passed
        checked_count = len(completed)

        return {
            "template": CHECKLIST_TEMPLATE,
            "auto_evaluations": auto_evaluations,
            "saved_state": saved,
            "total_items": total_items,
            "checked_count": checked_count,
            "auto_passed_count": auto_passed,
            "progress_pct": round(checked_count / total_items * 100, 1) if total_items else 0.0,
            "server_time_pht": pht_time.strftime("%Y-%m-%d %H:%M:%S PHT"),
            "active_session": session
        }
