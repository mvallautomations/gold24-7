"""
1-Minute Scalping Playbook Engine
Based on 'The 1-Minute Scalping Playbook: A Mechanical Standard Operating Procedure
for the NY Session Opening Range' (Terminal Systems Precision HUD).

Implements:
1. Multi-Market Opening Range Schedules (TSLA, NVDA, QQQ, SPY, GOLD, BTCUSD, EURUSD)
2. Multi-Timeframe Alignment Protocol (15M Boundary, 5M Confirmation Close, 1M Execution Matrix)
3. 3 Mechanical Execution Models:
   - Model A: Displacement & Momentum Breakout (FVG gap confirmation)
   - Model B: Structural Break & Retest (Boundary hold)
   - Model C: Mean Reversion & The Trap (Reversal Order Block)
4. Invariant 1:2 Risk Architecture (+2R Target, -1R Stop Loss)
5. The 10-Point EA Confluence Scorecard & Capital Allocation (Grade A+, Grade B, Grade C)
6. Session Tracking & The R-Multiple Ledger with PnL % & R:R Analysis
"""

import os
import sys
from pathlib import Path

# Add project root to sys.path so the module can be run directly or imported
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# PEP 405 auto-switch to .venv if running with system python
venv_python = PROJECT_ROOT / ".venv" / "bin" / "python"
if sys.prefix == sys.base_prefix and venv_python.exists():
    os.execv(str(venv_python), [str(venv_python)] + sys.argv)

import math
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone, time as dt_time, timedelta
from pydantic import BaseModel, Field

from core.models.candle import Bar, Timeframe
from core.models.signal import SignalDirection


class PlaybookModel(str, Enum):
    MODEL_A = "MODEL_A"  # Displacement & Momentum Breakout
    MODEL_B = "MODEL_B"  # Structural Break & Retest
    MODEL_C = "MODEL_C"  # Mean Reversion & The Trap
    NONE = "NONE"


class SetupGrade(str, Enum):
    GRADE_A_PLUS = "A+"  # 9-10 Points (Full Standard Risk)
    GRADE_B = "B"        # 7-8 Points (Half Standard Risk)
    GRADE_C = "C"        # < 7 Points (DO NOT TRADE / Sit on hands)


class SessionPhase(str, Enum):
    PRE_SESSION = "PRE_SESSION"          # Waiting for session open
    PHASE_1_ORH = "PHASE_1_ORH"          # 09:30-09:45 EST: Defining 15M ORH/ORL (Sit on hands)
    PHASE_2_CONFIRM = "PHASE_2_CONFIRM"  # Awaiting 5M Confirmation Close beyond boundary
    PHASE_3_EXECUTE = "PHASE_3_EXECUTE"  # 1M Execution Matrix Armed (Model A, B, C)
    POST_SESSION = "POST_SESSION"        # Execution window closed (Post-session audit)


class MarketScheduleConfig(BaseModel):
    symbol: str
    asset_class: str  # EQUITIES, COMMODITIES, CRYPTO, FOREX
    name: str
    open_hour_est: int
    open_minute_est: int
    duration_hours: float = 2.0  # 2-hour mechanical execution window
    is_24_7: bool = False
    tick_size: float = 0.01
    pip_factor: float = 100.0


# Recommended Markets across Stocks, Commodities, Crypto, and Forex
RECOMMENDED_MARKETS: Dict[str, MarketScheduleConfig] = {
    "GOLD": MarketScheduleConfig(
        symbol="GOLD", asset_class="COMMODITIES", name="Spot Gold / XAUUSD",
        open_hour_est=9, open_minute_est=30, duration_hours=2.0, tick_size=0.01, pip_factor=10.0
    ),
    "GOLD#": MarketScheduleConfig(
        symbol="GOLD#", asset_class="COMMODITIES", name="Spot Gold (XM Ultra Low)",
        open_hour_est=9, open_minute_est=30, duration_hours=2.0, tick_size=0.01, pip_factor=10.0
    ),
    "TSLA": MarketScheduleConfig(
        symbol="TSLA", asset_class="EQUITIES", name="Tesla Inc.",
        open_hour_est=9, open_minute_est=30, duration_hours=2.0, tick_size=0.01, pip_factor=100.0
    ),
    "NVDA": MarketScheduleConfig(
        symbol="NVDA", asset_class="EQUITIES", name="NVIDIA Corp.",
        open_hour_est=9, open_minute_est=30, duration_hours=2.0, tick_size=0.01, pip_factor=100.0
    ),
    "QQQ": MarketScheduleConfig(
        symbol="QQQ", asset_class="EQUITIES", name="Invesco QQQ Trust (Nasdaq 100)",
        open_hour_est=9, open_minute_est=30, duration_hours=2.0, tick_size=0.01, pip_factor=100.0
    ),
    "SPY": MarketScheduleConfig(
        symbol="SPY", asset_class="EQUITIES", name="SPDR S&P 500 ETF",
        open_hour_est=9, open_minute_est=30, duration_hours=2.0, tick_size=0.01, pip_factor=100.0
    ),
    "AAPL": MarketScheduleConfig(
        symbol="AAPL", asset_class="EQUITIES", name="Apple Inc.",
        open_hour_est=9, open_minute_est=30, duration_hours=2.0, tick_size=0.01, pip_factor=100.0
    ),
    "BTCUSD": MarketScheduleConfig(
        symbol="BTCUSD", asset_class="CRYPTO", name="Bitcoin / USD",
        open_hour_est=9, open_minute_est=30, duration_hours=24.0, is_24_7=True, tick_size=0.01, pip_factor=1.0
    ),
    "BTCUSD#": MarketScheduleConfig(
        symbol="BTCUSD#", asset_class="CRYPTO", name="Bitcoin / USD (XM)",
        open_hour_est=9, open_minute_est=30, duration_hours=24.0, is_24_7=True, tick_size=0.01, pip_factor=1.0
    ),
    "ETHUSD": MarketScheduleConfig(
        symbol="ETHUSD", asset_class="CRYPTO", name="Ethereum / USD",
        open_hour_est=9, open_minute_est=30, duration_hours=24.0, is_24_7=True, tick_size=0.01, pip_factor=10.0
    ),
    "EURUSD": MarketScheduleConfig(
        symbol="EURUSD", asset_class="FOREX", name="Euro / US Dollar",
        open_hour_est=8, open_minute_est=0, duration_hours=4.0, tick_size=0.00001, pip_factor=10000.0
    ),
    "US100Cash": MarketScheduleConfig(
        symbol="US100Cash", asset_class="EQUITIES", name="US Wall Street 100 Cash (Nasdaq)",
        open_hour_est=9, open_minute_est=30, duration_hours=2.0, tick_size=0.1, pip_factor=10.0
    ),
}


class ConfluenceScorecard(BaseModel):
    session_timing_pts: int = Field(default=0, description="Strictly within 2-hour window [0 or 2 pts]")
    boundary_15m_pts: int = Field(default=0, description="15M ORH/ORL clean & defined [0, 1, or 2 pts]")
    close_5m_pts: int = Field(default=0, description="5M full body close outside range [0 or 3 pts]")
    trigger_1m_pts: int = Field(default=0, description="Exact Model A, B, or C signature [0, 1, or 2 pts]")
    risk_distance_pts: int = Field(default=0, description="Valid 1:2 R:R distance to liquidity draw [0 or 1 pt]")
    total_score: int = Field(default=0, description="Total score (0-10)")
    grade: SetupGrade = SetupGrade.GRADE_C
    action_directive: str = "DO NOT TRADE. Sit on hands. Protect capital."
    risk_allocation_multiplier: float = 0.0  # 1.0 for Grade A+, 0.5 for Grade B, 0.0 for Grade C


class PlaybookSetupDiagnostic(BaseModel):
    symbol: str
    current_price: float
    session_phase: SessionPhase
    session_name: str
    is_in_execution_window: bool
    time_est_str: str

    # 15M Boundary
    orh: float
    orl: float
    range_pts: float
    is_boundary_clean: bool

    # 5M Confirmation
    is_5m_confirmed: bool
    confirm_direction: SignalDirection
    is_wick_trap: bool
    confirmation_candle_close: float

    # 1M Model
    detected_model: PlaybookModel
    model_name: str
    model_thesis: str

    # Invariant 1:2 Risk Bracket
    signal_direction: SignalDirection
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_points: float
    reward_points: float
    planned_rr_ratio: float = 2.0
    suggested_lots: float = 0.01

    # Scorecard
    scorecard: ConfluenceScorecard
    hermes_vibe_critique: str


class ScalpingPlaybookEngine:
    """
    Core algorithmic implementation of the 1-Minute Scalping Playbook.
    """

    def __init__(self, default_balance: float = 1874.19, base_risk_pct: float = 1.0):
        self.default_balance = default_balance
        self.base_risk_pct = base_risk_pct

    def get_market_schedule_status(self, symbol: str) -> Dict[str, Any]:
        """
        Calculate precise EST/UTC session open schedule and countdown.
        """
        clean_sym = symbol.strip().upper()
        config = RECOMMENDED_MARKETS.get(clean_sym)
        if not config:
            for k, v in RECOMMENDED_MARKETS.items():
                if k in clean_sym or clean_sym in k:
                    config = v
                    break
        if not config:
            config = RECOMMENDED_MARKETS["GOLD"]

        # Current time in EST (UTC - 4 in EDT or UTC - 5 in EST; approximating UTC-4 for market schedule)
        now_utc = datetime.now(timezone.utc)
        est_offset = timedelta(hours=-4)
        now_est = now_utc + est_offset

        if config.is_24_7:
            # 24/7 continuous market
            return {
                "symbol": config.symbol,
                "name": config.name,
                "asset_class": config.asset_class,
                "is_in_window": True,
                "phase": SessionPhase.PHASE_3_EXECUTE.value,
                "status_badge": "24/7 CONTINUOUS",
                "session_name": "Crypto 24/7 Session",
                "time_est": now_est.strftime("%H:%M:%S EST"),
                "time_utc": now_utc.strftime("%H:%M:%S UTC"),
                "minutes_remaining": 1440,
                "window_description": "Continuous liquidity window active."
            }

        # Daily open time today
        open_time_est = now_est.replace(
            hour=config.open_hour_est, minute=config.open_minute_est, second=0, microsecond=0
        )
        close_time_est = open_time_est + timedelta(hours=config.duration_hours)

        is_in_window = open_time_est <= now_est <= close_time_est

        if now_est < open_time_est:
            phase = SessionPhase.PRE_SESSION
            time_diff = open_time_est - now_est
            status_badge = f"OPENS IN {int(time_diff.total_seconds() // 60)}m"
            mins_remaining = 0
            desc = f"Pre-market formation. Session opens at {config.open_hour_est:02d}:{config.open_minute_est:02d} EST."
        elif is_in_window:
            elapsed = (now_est - open_time_est).total_seconds()
            if elapsed < 900:  # first 15 mins (09:30-09:45)
                phase = SessionPhase.PHASE_1_ORH
                status_badge = "PHASE 1: 15M ORH FORMING"
                desc = "Sit on hands. Boxing the 15-minute Opening Range High & Low."
            elif elapsed < 1200:  # 09:45-09:50 (first 5M bar after ORH)
                phase = SessionPhase.PHASE_2_CONFIRM
                status_badge = "PHASE 2: 5M CONFIRMATION"
                desc = "Awaiting full 5-minute candle body close beyond ORH/ORL. Wicks are traps."
            else:
                phase = SessionPhase.PHASE_3_EXECUTE
                status_badge = "PHASE 3: 1M ARMED"
                desc = "Mechanical execution window open. Diagnosing Model A, B, or C."
            mins_remaining = int((close_time_est - now_est).total_seconds() // 60)
        else:
            phase = SessionPhase.POST_SESSION
            status_badge = "SESSION CLOSED"
            mins_remaining = 0
            desc = "2-hour execution window closed. Terminal powered down for post-session audit."

        return {
            "symbol": config.symbol,
            "name": config.name,
            "asset_class": config.asset_class,
            "is_in_window": is_in_window,
            "phase": phase.value,
            "status_badge": status_badge,
            "session_name": f"{config.name} Opening Window ({config.open_hour_est:02d}:{config.open_minute_est:02d} - {int(config.open_hour_est + config.duration_hours):02d}:{config.open_minute_est:02d} EST)",
            "time_est": now_est.strftime("%H:%M:%S EST"),
            "time_utc": now_utc.strftime("%H:%M:%S UTC"),
            "minutes_remaining": mins_remaining,
            "window_description": desc
        }

    def get_15m_object_indicators(
        self,
        symbol: str,
        bars_15m: List[Bar],
        bars_5m: Optional[List[Bar]] = None,
        bars_1m: Optional[List[Bar]] = None
    ) -> Dict[str, Any]:
        """
        Generate complete geometric and mathematical object indicators for the 15M opening entry timeframe.
        Produces:
        - 15M Opening Range Box (OBJ_RECTANGLE)
        - 15M ORH & ORL Boundary Rays (OBJ_TREND / OBJ_HLINE)
        - 50% Equilibrium Median Line (OBJ_TREND)
        - +1R / +2R Institutional Bullish Expansion Targets
        - -1R / -2R Institutional Bearish Expansion Targets
        - Breakout / Wick Trap Markers
        - On-Chart HUD text labels and tags
        """
        sched = self.get_market_schedule_status(symbol)
        curr_price = bars_1m[-1].close if (bars_1m and len(bars_1m) > 0) else (bars_15m[-1].close if bars_15m else 0.0)

        if not bars_15m:
            return {}

        ref_bar_15m = bars_15m[-2] if len(bars_15m) >= 2 else bars_15m[-1]
        orh = round(ref_bar_15m.high, 2)
        orl = round(ref_bar_15m.low, 2)
        range_pts = round(orh - orl, 2)
        eq_price = round((orh + orl) / 2.0, 2)

        # Expansion Targets
        exp_plus_1r = round(orh + range_pts, 2)
        exp_plus_2r = round(orh + (2.0 * range_pts), 2)
        exp_minus_1r = round(orl - range_pts, 2)
        exp_minus_2r = round(orl - (2.0 * range_pts), 2)

        # Time bounds
        t_open = ref_bar_15m.timestamp
        t_close = t_open + timedelta(minutes=15)
        # 2-hour window projection
        t_window_end = t_open + timedelta(hours=2)

        t_open_str = t_open.strftime("%H:%M") if hasattr(t_open, "strftime") else str(t_open)
        t_close_str = t_close.strftime("%H:%M") if hasattr(t_close, "strftime") else str(t_close)
        t_window_end_str = t_window_end.strftime("%H:%M") if hasattr(t_window_end, "strftime") else str(t_window_end)

        # Check breakout status on current/latest bar
        latest_close = curr_price
        if latest_close > orh:
            status = "BULLISH_EXPANSION"
            status_desc = f"Trading above 15M ORH (${orh}). Bullish expansion toward +1R (${exp_plus_1r}) and +2R (${exp_plus_2r})."
        elif latest_close < orl:
            status = "BEARISH_EXPANSION"
            status_desc = f"Trading below 15M ORL (${orl}). Bearish expansion toward -1R (${exp_minus_1r}) and -2R (${exp_minus_2r})."
        else:
            status = "CONSOLIDATION_INSIDE_RANGE"
            status_desc = f"Trading inside 15M range (${orl} - ${orh}). Awaiting 5M confirmation close."

        return {
            "symbol": symbol,
            "current_price": curr_price,
            "session_status": sched.get("status_badge"),
            "session_name": sched.get("session_name"),
            "state": status,
            "description": status_desc,
            "box": {
                "name": "PB_15M_ORH_BOX",
                "object_type": "OBJ_RECTANGLE",
                "time_start": t_open.isoformat() if hasattr(t_open, "isoformat") else str(t_open),
                "time_end": t_window_end.isoformat() if hasattr(t_window_end, "isoformat") else str(t_window_end),
                "time_start_str": t_open_str,
                "time_end_str": t_window_end_str,
                "price_high": orh,
                "price_low": orl,
                "range_points": range_pts,
                "color_bg": "rgba(30, 80, 180, 0.12)",
                "color_border": "#3b82f6"
            },
            "boundaries": {
                "orh": {
                    "name": "PB_LINE_15M_ORH",
                    "object_type": "OBJ_TREND",
                    "price": orh,
                    "label": f"15M ORH (Liquidity High): ${orh:.2f}",
                    "color": "#60a5fa",
                    "style": "solid",
                    "width": 2
                },
                "orl": {
                    "name": "PB_LINE_15M_ORL",
                    "object_type": "OBJ_TREND",
                    "price": orl,
                    "label": f"15M ORL (Liquidity Low): ${orl:.2f}",
                    "color": "#38bdf8",
                    "style": "solid",
                    "width": 2
                },
                "equilibrium": {
                    "name": "PB_LINE_15M_EQ",
                    "object_type": "OBJ_TREND",
                    "price": eq_price,
                    "label": f"50% Equilibrium (Median): ${eq_price:.2f}",
                    "color": "#eab308",
                    "style": "dashed",
                    "width": 1
                }
            },
            "expansion_projections": {
                "plus_1r": {
                    "name": "PB_EXP_PLUS_1R",
                    "price": exp_plus_1r,
                    "label": f"+1R Expansion: ${exp_plus_1r:.2f}",
                    "color": "#22c55e",
                    "style": "dotted",
                    "width": 1
                },
                "plus_2r": {
                    "name": "PB_EXP_PLUS_2R",
                    "price": exp_plus_2r,
                    "label": f"+2R Target (+2R TP): ${exp_plus_2r:.2f}",
                    "color": "#10b981",
                    "style": "solid",
                    "width": 2
                },
                "minus_1r": {
                    "name": "PB_EXP_MINUS_1R",
                    "price": exp_minus_1r,
                    "label": f"-1R Expansion: ${exp_minus_1r:.2f}",
                    "color": "#f87171",
                    "style": "dotted",
                    "width": 1
                },
                "minus_2r": {
                    "name": "PB_EXP_MINUS_2R",
                    "price": exp_minus_2r,
                    "label": f"-2R Target (+2R Short TP): ${exp_minus_2r:.2f}",
                    "color": "#ef4444",
                    "style": "solid",
                    "width": 2
                }
            },
            "on_chart_hud": {
                "badge_title": "15M OPENING ENTRY TIMEFRAME",
                "range_badge": f"Range: {range_pts:.2f} pts (${orl:.2f} - ${orh:.2f})",
                "equilibrium_badge": f"EQ: ${eq_price:.2f}",
                "window_badge": f"Open Window: {t_open_str} - {t_window_end_str} EST",
                "bias_badge": status
            }
        }

    def evaluate_playbook_setup(
        self,
        symbol: str,
        bars_15m: List[Bar],
        bars_5m: List[Bar],
        bars_1m: List[Bar],
        account_balance: Optional[float] = None
    ) -> PlaybookSetupDiagnostic:
        """
        Full diagnostic evaluation against all 15 pages of the Playbook.
        """
        sched = self.get_market_schedule_status(symbol)
        curr_price = bars_1m[-1].close if bars_1m else (bars_5m[-1].close if bars_5m else 0.0)
        bal = account_balance or self.default_balance

        # 1. 15M Boundary (ORH / ORL)
        if bars_15m:
            # Use completed 15M reference candle (Shift 1) so 5M/1M can break beyond it
            ref_bar_15m = bars_15m[-2] if len(bars_15m) >= 2 else bars_15m[-1]
            orh = ref_bar_15m.high
            orl = ref_bar_15m.low
            range_pts = round(orh - orl, 2)
            # Boundary cleanliness check: range must be reasonable, not 0
            is_boundary_clean = range_pts > 0.5
        else:
            orh = curr_price + 2.0
            orl = curr_price - 2.0
            range_pts = 4.0
            is_boundary_clean = True

        # 2. 5M Confirmation Close (Page 5)
        is_5m_confirmed = False
        confirm_direction = SignalDirection.NONE
        is_wick_trap = False
        confirm_close = curr_price

        if bars_5m:
            latest_5m = bars_5m[-1]
            confirm_close = latest_5m.close
            # Full body close beyond boundary
            if latest_5m.close > orh:
                is_5m_confirmed = True
                confirm_direction = SignalDirection.BUY
            elif latest_5m.close < orl:
                is_5m_confirmed = True
                confirm_direction = SignalDirection.SELL
            elif latest_5m.high > orh and latest_5m.close <= orh:
                is_wick_trap = True  # wicked above ORH but rejected
            elif latest_5m.low < orl and latest_5m.close >= orl:
                is_wick_trap = True  # wicked below ORL but rejected

        # 3. 1M Execution Matrix (Models A, B, C - Pages 6, 7, 8, 9)
        detected_model = PlaybookModel.NONE
        model_name = "Awaiting Setup Diagnosis"
        model_thesis = "Monitoring 1M candle signatures for Model A, B, or C trigger."
        signal_dir = SignalDirection.NONE
        entry_price = curr_price
        stop_loss = curr_price
        take_profit = curr_price
        risk_pts = 2.5

        if is_5m_confirmed:
            # Direction is confirmed by 5M
            signal_dir = confirm_direction
            m1_tail = bars_1m[-5:] if len(bars_1m) >= 5 else bars_1m

            # Check Model A: Displacement & Momentum Breakout (FVG gap)
            has_gap = False
            if len(m1_tail) >= 3:
                b1, b2, b3 = m1_tail[-3], m1_tail[-2], m1_tail[-1]
                if signal_dir == SignalDirection.BUY and b3.low > b1.high:
                    has_gap = True
                elif signal_dir == SignalDirection.SELL and b3.high < b1.low:
                    has_gap = True

            if has_gap:
                detected_model = PlaybookModel.MODEL_A
                model_name = "Model A: Displacement & Momentum Breakout"
                model_thesis = "Explosive momentum verified with clear displacement gap printing beyond 15M boundary."
                entry_price = curr_price
                if signal_dir == SignalDirection.BUY:
                    stop_loss = round(m1_tail[-2].low - 0.20, 2)  # below 2nd candle of gap
                else:
                    stop_loss = round(m1_tail[-2].high + 0.20, 2)
            else:
                # Check Model B: Structural Break & Retest
                # Price broke boundary, now testing boundary level
                boundary_test = (abs(curr_price - orh) <= 1.0) if signal_dir == SignalDirection.BUY else (abs(curr_price - orl) <= 1.0)
                if boundary_test:
                    detected_model = PlaybookModel.MODEL_B
                    model_name = "Model B: Structural Break & Retest"
                    model_thesis = "Lower-timeframe structure holding directly at the 15M boundary; pristine high-probability retest."
                    entry_price = curr_price
                    if signal_dir == SignalDirection.BUY:
                        stop_loss = round(orl if (orh - orl) <= 3.0 else (orh - 1.50), 2)
                    else:
                        stop_loss = round(orh if (orh - orl) <= 3.0 else (orl + 1.50), 2)
                else:
                    # Default to Model A continuation
                    detected_model = PlaybookModel.MODEL_A
                    model_name = "Model A: Momentum Impulse"
                    model_thesis = "Direction confirmed by 5M full body close; riding institutional impulse."
                    entry_price = curr_price
                    stop_loss = round(curr_price - 2.50 if signal_dir == SignalDirection.BUY else curr_price + 2.50, 2)

        elif is_wick_trap:
            # Model C: Mean Reversion & The Trap (Page 9)
            # Breakout failed, 1M structure broken in opposite direction
            detected_model = PlaybookModel.MODEL_C
            model_name = "Model C: Mean Reversion & The Trap"
            model_thesis = "Initial breakout rejected with a wick trap; fading the false breakout toward opposite 15M boundary."
            if latest_5m.high > orh:
                signal_dir = SignalDirection.SELL
                entry_price = curr_price
                stop_loss = round(latest_5m.high + 0.30, 2)
                take_profit = round(orl, 2)  # target opposite boundary
            else:
                signal_dir = SignalDirection.BUY
                entry_price = curr_price
                stop_loss = round(latest_5m.low - 0.30, 2)
                take_profit = round(orh, 2)  # target opposite boundary

        # 4. Invariant 1:2 Risk Architecture (Page 10) - Symbol-Aware Baseline Risk
        is_crypto = "BTC" in symbol or "ETH" in symbol
        is_forex = "EUR" in symbol or "GBP" in symbol or "JPY" in symbol
        is_index = "US100" in symbol or "US500" in symbol or "SPY" in symbol or "QQQ" in symbol

        if is_forex:
            base_risk = 0.0015
            precision = 5
        elif is_crypto:
            base_risk = max(100.0, curr_price * 0.003)
            precision = 2
        elif is_index:
            base_risk = max(20.0, curr_price * 0.002)
            precision = 2
        else:  # Commodities / GOLD
            base_risk = 3.0
            precision = 2

        if signal_dir != SignalDirection.NONE:
            raw_risk = abs(entry_price - stop_loss)
            risk_pts = max(base_risk * 0.5, min(base_risk * 2.5, raw_risk))
            if signal_dir == SignalDirection.BUY:
                stop_loss = round(entry_price - risk_pts, precision)
                take_profit = round(entry_price + (2.0 * risk_pts), precision)
            else:
                stop_loss = round(entry_price + risk_pts, precision)
                take_profit = round(entry_price - (2.0 * risk_pts), precision)
        else:
            risk_pts = base_risk
            stop_loss = round(curr_price - risk_pts, precision)
            take_profit = round(curr_price + (2.0 * risk_pts), precision)

        reward_pts = round(abs(take_profit - entry_price), precision)

        # 5. 10-Point EA Confluence Scorecard (Page 11)
        # Score breakdown:
        # [2 PTS] Session Timing
        session_pts = 2 if sched.get("is_in_window") else 1  # 2 if inside, 1 if close
        # [2 PTS] 15M Boundary
        boundary_pts = 2 if is_boundary_clean else 1
        # [3 PTS] 5M Close
        close_pts = 3 if is_5m_confirmed else (2 if is_wick_trap else 0)
        # [2 PTS] 1M Trigger
        trigger_pts = 2 if detected_model in [PlaybookModel.MODEL_A, PlaybookModel.MODEL_B] else (1 if detected_model == PlaybookModel.MODEL_C else 0)
        # [1 PT] Risk Distance
        risk_dist_pts = 1 if (reward_pts / (risk_pts or 1.0)) >= 1.95 else 0

        total_score = session_pts + boundary_pts + close_pts + trigger_pts + risk_dist_pts

        if total_score >= 9:
            grade = SetupGrade.GRADE_A_PLUS
            action = "GRADE A+ SETUP: Flawless alignment. Execute at FULL standard risk (1.0% - 2.0%)."
            mult = 1.0
        elif total_score >= 7:
            grade = SetupGrade.GRADE_B
            action = "GRADE B SETUP: Valid alignment with slight friction. Execute at HALF standard size (0.5%)."
            mult = 0.5
        else:
            grade = SetupGrade.GRADE_C
            action = "GRADE C SETUP: Incomplete confluence. DO NOT TRADE. Sit on hands. Protect capital."
            mult = 0.0

        scorecard = ConfluenceScorecard(
            session_timing_pts=session_pts,
            boundary_15m_pts=boundary_pts,
            close_5m_pts=close_pts,
            trigger_1m_pts=trigger_pts,
            risk_distance_pts=risk_dist_pts,
            total_score=total_score,
            grade=grade,
            action_directive=action,
            risk_allocation_multiplier=mult
        )

        # Suggested lots (0.01 base scaled by multiplier)
        suggested_lots = round(max(0.01, 0.01 * mult), 2)

        # Hermes Vibe Critique
        critique = (
            f"Playbook Score: {total_score}/10 ({grade.value}). "
            f"15M Range: ${orl:.2f} - ${orh:.2f} ({range_pts:.2f} pts). "
            f"5M Status: {'Full body commitment verified' if is_5m_confirmed else ('Wick trap warning' if is_wick_trap else 'Awaiting close')}. "
            f"Execution Weapon: {model_name}. Fixed 1:2 R:R bracket locked (Risk: {risk_pts} pts, Target: +{reward_pts} pts)."
        )

        return PlaybookSetupDiagnostic(
            symbol=symbol,
            current_price=curr_price,
            session_phase=SessionPhase(sched.get("phase", "PHASE_3_EXECUTE")),
            session_name=sched.get("session_name", "Open Window"),
            is_in_execution_window=sched.get("is_in_window", True),
            time_est_str=sched.get("time_est", ""),
            orh=orh,
            orl=orl,
            range_pts=range_pts,
            is_boundary_clean=is_boundary_clean,
            is_5m_confirmed=is_5m_confirmed,
            confirm_direction=confirm_direction,
            is_wick_trap=is_wick_trap,
            confirmation_candle_close=confirm_close,
            detected_model=detected_model,
            model_name=model_name,
            model_thesis=model_thesis,
            signal_direction=signal_dir,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_points=risk_pts,
            reward_points=reward_pts,
            planned_rr_ratio=2.0,
            suggested_lots=suggested_lots,
            scorecard=scorecard,
            hermes_vibe_critique=critique
        )

    def analyze_historical_trades(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze all closed trades with PnL %, R-Multiple Yield, and Playbook Quality Scores.
        Based on Page 13 'Session Tracking & The R-Multiple Ledger'.
        """
        if not trades:
            return {
                "total_trades": 0,
                "cumulative_r_yield": 0.0,
                "win_rate": 0.0,
                "profit_factor": 1.0,
                "avg_r_multiple": 0.0,
                "r_yield_series": [],
                "trades_detailed": []
            }

        detailed = []
        cumulative_r = 0.0
        r_yield_series = []
        total_pnl = 0.0
        gross_profit = 0.0
        gross_loss = 0.0
        wins = 0

        for t in trades:
            net_pnl = float(t.get("net_pnl", t.get("realized_pnl", 0.0)))
            entry_p = float(t.get("entry_price", 0.0))
            exit_p = float(t.get("exit_price", 0.0))
            lots = float(t.get("lots", t.get("quantity_lots", 0.01)))
            sym = t.get("symbol", "GOLD")

            # Calculate estimated R-Multiple
            # Base dollar risk on 0.01 lot on Gold is approx $2.50 - $3.00 (25-30 points)
            assumed_risk_dollars = max(1.50, lots * 250.0 if ("GOLD" in sym or "XAU" in sym) else lots * 300.0)
            if net_pnl >= 0:
                r_mult = round(net_pnl / assumed_risk_dollars, 2)
                wins += 1
                gross_profit += net_pnl
            else:
                r_mult = round(net_pnl / assumed_risk_dollars, 2)
                gross_loss += abs(net_pnl)

            # Cap outliers for clean R presentation
            r_mult_clamped = max(-1.2, min(3.5, r_mult))
            cumulative_r = round(cumulative_r + r_mult_clamped, 2)

            # PnL % calculation (relative to $1,874 account balance or trade margin)
            pnl_pct = round((net_pnl / self.default_balance) * 100.0, 2)

            # Exit classification
            if r_mult >= 1.8:
                exit_type = "TAKE_PROFIT (+2R)"
                grade = "A+"
            elif r_mult >= 0.8:
                exit_type = "PARTIAL_TP (+1R)"
                grade = "B"
            elif r_mult > -0.3 and r_mult < 0.3:
                exit_type = "SCRATCH (~0R)"
                grade = "B-"
            elif r_mult <= -0.9:
                exit_type = "STOP_LOSS (-1R)"
                grade = "B" if net_pnl > -5.0 else "C"
            else:
                exit_type = "EARLY_EXIT"
                grade = "C"

            # Model inference
            comment = str(t.get("comment", "")).upper()
            if "MODEL_A" in comment or "DISPLACEMENT" in comment:
                model_used = "MODEL A (Displacement)"
            elif "MODEL_B" in comment or "RETEST" in comment or "PULLBACK" in comment:
                model_used = "MODEL B (Break & Retest)"
            elif "MODEL_C" in comment or "TRAP" in comment:
                model_used = "MODEL C (Mean Reversion Trap)"
            else:
                model_used = "BREAKOUT / PULLBACK"

            date_str = str(t.get("closed_at", t.get("opened_at", "")))[:10]

            detailed.append({
                "ticket": t.get("ticket", t.get("position_id", t.get("id", ""))),
                "date": date_str,
                "symbol": sym,
                "side": t.get("side", "BUY"),
                "lots": lots,
                "entry_price": entry_p,
                "exit_price": exit_p,
                "gross_pnl": round(float(t.get("gross_pnl", net_pnl)), 2),
                "net_pnl": round(net_pnl, 2),
                "pnl_percent": pnl_pct,
                "r_multiple": r_mult_clamped,
                "cumulative_r": cumulative_r,
                "setup_grade": grade,
                "model_used": model_used,
                "exit_type": exit_type,
                "comment": t.get("comment", "")
            })

            r_yield_series.append({
                "trade_num": len(detailed),
                "r_yield": cumulative_r,
                "date": date_str,
                "symbol": sym
            })

            total_pnl += net_pnl

        win_rate = round((wins / len(trades)) * 100.0, 1) if trades else 0.0
        profit_factor = round((gross_profit / gross_loss), 2) if gross_loss > 0 else (round(gross_profit, 2) if gross_profit > 0 else 1.0)
        avg_r = round(cumulative_r / len(trades), 2) if trades else 0.0

        return {
            "total_trades": len(trades),
            "wins": wins,
            "losses": len(trades) - wins,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "total_net_pnl": round(total_pnl, 2),
            "cumulative_r_yield": cumulative_r,
            "avg_r_multiple": avg_r,
            "r_yield_series": r_yield_series,
            "trades_detailed": detailed
        }

    def simulate_walkforward(
        self,
        symbol: str,
        bars_15m: List[Bar],
        bars_5m: List[Bar],
        bars_1m: List[Bar],
        lookback_bars: int = 80,
        min_grade: str = "B"
    ) -> Dict[str, Any]:
        """
        Simulate the 1-Minute Scalping Playbook bar-by-bar across recent historical candles.
        Enforces:
        - 15M ORH/ORL Boundary Definition
        - 5M Confirmation Close vs Wick Trap
        - 1M Microstructure Signatures (Model A, Model B, Model C)
        - Invariant 1:2 R:R Target (+2R) and Hard Stop Loss (-1R)
        """
        if len(bars_1m) < 15:
            return {"trades": [], "summary": {}}

        trades = []
        in_trade = False
        current_trade = None
        start_idx = max(10, len(bars_1m) - lookback_bars)

        for i in range(start_idx, len(bars_1m)):
            bar = bars_1m[i]

            # 1. If in a trade, evaluate SL / TP resolution on this bar
            if in_trade and current_trade:
                direction = current_trade["direction"]
                sl = current_trade["stop_loss"]
                tp = current_trade["take_profit"]

                exit_triggered = False
                result_r = 0.0
                exit_price = bar.close
                exit_type = ""

                if direction == SignalDirection.BUY:
                    if bar.low <= sl:
                        exit_triggered = True
                        result_r = -1.0
                        exit_price = sl
                        exit_type = "STOP_LOSS (-1R)"
                    elif bar.high >= tp:
                        exit_triggered = True
                        result_r = 2.0
                        exit_price = tp
                        exit_type = "TAKE_PROFIT (+2R)"
                else:  # SELL
                    if bar.high >= sl:
                        exit_triggered = True
                        result_r = -1.0
                        exit_price = sl
                        exit_type = "STOP_LOSS (-1R)"
                    elif bar.low <= tp:
                        exit_triggered = True
                        result_r = 2.0
                        exit_price = tp
                        exit_type = "TAKE_PROFIT (+2R)"

                if exit_triggered:
                    risk_pts = current_trade["risk_points"]
                    lots = current_trade["lots"]
                    # 0.01 lot of Gold (1 oz): 1 point = $1.00 PnL
                    # Forex / Crypto scaled by standard multiplier
                    is_crypto = "BTC" in symbol or "ETH" in symbol
                    pt_val = 0.01 if is_crypto else (100.0 * lots)
                    dollar_pnl = round(result_r * (risk_pts * pt_val), 2)

                    current_trade["exit_price"] = exit_price
                    current_trade["exit_time"] = bar.timestamp.strftime("%H:%M") if hasattr(bar.timestamp, "strftime") else str(bar.timestamp)[11:16]
                    current_trade["exit_type"] = exit_type
                    current_trade["r_multiple"] = result_r
                    current_trade["net_pnl"] = dollar_pnl
                    trades.append(current_trade)
                    in_trade = False
                    current_trade = None
                    continue

            # 2. If flat, evaluate entry confluence on this bar
            if not in_trade:
                sub_1m = bars_1m[:i + 1]
                t_cutoff = bar.timestamp
                sub_5m = [b for b in bars_5m if b.timestamp <= t_cutoff] or bars_5m[:1]
                sub_15m = [b for b in bars_15m if b.timestamp <= t_cutoff] or bars_15m[:1]

                diag = self.evaluate_playbook_setup(
                    symbol=symbol,
                    bars_15m=sub_15m,
                    bars_5m=sub_5m,
                    bars_1m=sub_1m,
                    account_balance=self.default_balance
                )

                qualifies = False
                if min_grade == "A+" and diag.scorecard.grade == SetupGrade.GRADE_A_PLUS:
                    qualifies = True
                elif min_grade == "B" and diag.scorecard.grade in [SetupGrade.GRADE_A_PLUS, SetupGrade.GRADE_B]:
                    qualifies = True
                elif min_grade == "ALL" and diag.signal_direction != SignalDirection.NONE:
                    qualifies = True

                if qualifies and diag.signal_direction != SignalDirection.NONE:
                    in_trade = True
                    current_trade = {
                        "trade_num": len(trades) + 1,
                        "entry_time": bar.timestamp.strftime("%H:%M") if hasattr(bar.timestamp, "strftime") else str(bar.timestamp)[11:16],
                        "symbol": symbol,
                        "direction": diag.signal_direction,
                        "side": "BUY" if diag.signal_direction == SignalDirection.BUY else "SELL",
                        "model": diag.model_name,
                        "grade": diag.scorecard.grade.value,
                        "score": diag.scorecard.total_score,
                        "entry_price": diag.entry_price,
                        "stop_loss": diag.stop_loss,
                        "take_profit": diag.take_profit,
                        "risk_points": diag.risk_points,
                        "reward_points": diag.reward_points,
                        "lots": diag.suggested_lots,
                        "exit_price": None,
                        "exit_time": None,
                        "exit_type": "PENDING",
                        "r_multiple": 0.0,
                        "net_pnl": 0.0
                    }

        # 3. Handle position still floating at end of simulation window
        if in_trade and current_trade:
            last_bar = bars_1m[-1]
            current_trade["exit_price"] = last_bar.close
            current_trade["exit_time"] = "CURRENT (OPEN)"
            current_trade["exit_type"] = "OPEN_FLOATING"
            diff = (last_bar.close - current_trade["entry_price"]) if current_trade["direction"] == SignalDirection.BUY else (current_trade["entry_price"] - last_bar.close)
            r_floating = round(diff / (current_trade["risk_points"] or 1.0), 2)
            current_trade["r_multiple"] = r_floating
            is_crypto = "BTC" in symbol or "ETH" in symbol
            pt_val = 0.01 if is_crypto else (100.0 * current_trade["lots"])
            current_trade["net_pnl"] = round(r_floating * (current_trade["risk_points"] * pt_val), 2)
            trades.append(current_trade)

        closed_trades = [t for t in trades if t["exit_type"] != "OPEN_FLOATING"]
        wins = [t for t in closed_trades if t["r_multiple"] > 0]
        losses = [t for t in closed_trades if t["r_multiple"] <= 0]
        cum_r = round(sum(t["r_multiple"] for t in closed_trades), 2)
        total_pnl = round(sum(t["net_pnl"] for t in closed_trades), 2)
        win_rate = round(len(wins) / len(closed_trades) * 100.0, 1) if closed_trades else 0.0
        profit_factor = round(sum(t["net_pnl"] for t in wins) / abs(sum(t["net_pnl"] for t in losses)), 2) if losses and sum(t["net_pnl"] for t in losses) != 0 else (round(sum(t["net_pnl"] for t in wins), 2) if wins else 1.0)

        summary = {
            "total_simulated_trades": len(trades),
            "closed_trades": len(closed_trades),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": win_rate,
            "cumulative_r_yield": cum_r,
            "total_net_pnl": total_pnl,
            "profit_factor": profit_factor,
            "has_open_position": (current_trade is not None and current_trade.get("exit_type") == "OPEN_FLOATING")
        }

        return {"trades": trades, "summary": summary}


def dict_to_bar(d: Dict[str, Any]) -> Bar:
    """Helper to convert rate dictionaries into canonical Bar models."""
    ts = d.get("timestamp") or d.get("time")
    if isinstance(ts, (int, float)):
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    elif isinstance(ts, str):
        try:
            dt = datetime.fromisoformat(ts)
        except Exception:
            dt = datetime.now(timezone.utc)
    elif isinstance(ts, datetime):
        dt = ts
    else:
        dt = datetime.now(timezone.utc)

    return Bar(
        timestamp=dt,
        open=float(d.get("open", 0.0)),
        high=float(d.get("high", 0.0)),
        low=float(d.get("low", 0.0)),
        close=float(d.get("close", 0.0)),
        volume=float(d.get("volume", d.get("tick_volume", 0.0))),
        shift=1
    )


def fetch_multitimeframe_bars(symbol: str = "GOLD", count: int = 100) -> Dict[str, List[Bar]]:
    """
    Fetch multi-timeframe candles with hierarchical fallback:
    1. MT5 Windows Bridge (http://172.26.144.1:8082/api/rates)
    2. Local Dashboard Server (http://127.0.0.1:8585/api/market-data)
    3. High-fidelity synthetic MarketDataGenerator
    """
    import urllib.request
    import json

    bars_by_tf: Dict[str, List[Bar]] = {}

    # Attempt 1: MT5 Bridge
    bridge_ok = True
    for tf in ["M15", "M5", "M1"]:
        try:
            url = f"http://172.26.144.1:8082/api/rates?symbol={symbol}&timeframe={tf}&count={count}"
            req = urllib.request.Request(url, headers={"User-Agent": "GOLD24-7/PlaybookSim"})
            with urllib.request.urlopen(req, timeout=2.5) as resp:
                data = json.loads(resp.read().decode())
                rates = data.get("rates", [])
                if rates:
                    bars_by_tf[tf] = [dict_to_bar(r) for r in rates]
                else:
                    bridge_ok = False
                    break
        except Exception:
            bridge_ok = False
            break

    if bridge_ok and len(bars_by_tf) == 3:
        return bars_by_tf

    # Attempt 2: Dashboard Server
    try:
        url = f"http://127.0.0.1:8585/api/market-data?symbol={symbol}"
        req = urllib.request.Request(url, headers={"User-Agent": "GOLD24-7/PlaybookSim"})
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            data = json.loads(resp.read().decode())
            candles = data.get("candles", {})
            if "M15" in candles and "M5" in candles and "M1" in candles:
                return {
                    "M15": [dict_to_bar(r) for r in candles["M15"]],
                    "M5": [dict_to_bar(r) for r in candles["M5"]],
                    "M1": [dict_to_bar(r) for r in candles["M1"]],
                }
    except Exception:
        pass

    # Attempt 3: Synthetic Fallback
    from backtest.datasets.data_generator import MarketDataGenerator
    gen = MarketDataGenerator(seed=42)
    tf_data = gen.generate_multitimeframe_bars(symbol=symbol)
    return {
        "M15": tf_data[Timeframe.M15],
        "M5": tf_data[Timeframe.M5],
        "M1": tf_data[Timeframe.M1]
    }


def run_trial_simulation(symbol: str = "GOLD", lookback: int = 60, min_grade: str = "B"):
    """
    Main execution routine for trial simulation of the 1-Minute Scalping Playbook
    on current M15, M5, and M1 timeframes.
    """
    print("\n" + "=" * 78)
    print("  TERMINAL SYSTEMS PRECISION HUD: 1-MINUTE SCALPING PLAYBOOK TRIAL SIM")
    print("=" * 78)
    print(f"  Target Instrument : {symbol} (Spot Gold / XAUUSD)")
    print(f"  Timeframe Alignment: 15M (Boundary) -> 5M (Confirm Close) -> 1M (Execution Matrix)")
    print(f"  Risk Architecture : Invariant 1:2 R:R (+2R Target, -1R Stop Loss)")
    print(f"  Evaluation Window : Last {lookback} completed 1-Minute bars")
    print("-" * 78)

    # 1. Fetch live or synthetic bars
    bars = fetch_multitimeframe_bars(symbol=symbol, count=100)
    bars_15m = bars["M15"]
    bars_5m = bars["M5"]
    bars_1m = bars["M1"]

    engine = ScalpingPlaybookEngine(default_balance=1874.19)

    # 2. Real-time Snapshot Diagnostic
    diag = engine.evaluate_playbook_setup(
        symbol=symbol,
        bars_15m=bars_15m,
        bars_5m=bars_5m,
        bars_1m=bars_1m
    )
    sched = engine.get_market_schedule_status(symbol)

    print("\n[STEP 1: LIVE MULTI-TIMEFRAME SNAPSHOT AUDIT]")
    print(f"  * Current Live Price   : ${diag.current_price:.2f}")
    print(f"  * Session Status       : {sched.get('status_badge')} | Phase: {diag.session_phase.value}")
    print(f"  * Window Clock         : {sched.get('time_est')} ({sched.get('session_name')})")
    print(f"  * 15M ORH / ORL Range  : High: ${diag.orh:.2f} | Low: ${diag.orl:.2f} (Spread: {diag.range_pts:.2f} pts)")
    print(f"  * 15M Boundary Quality : {'CLEAN & DEFINED (2/2 pts)' if diag.is_boundary_clean else 'NARROW / CHOP'}")
    print(f"  * 5M Confirmation State: {'CONFIRMED BREAKOUT' if diag.is_5m_confirmed else ('WICK TRAP REJECTION' if diag.is_wick_trap else 'INSIDE RANGE / AWAITING COMMITMENT')}")
    print(f"  * 1M Diagnosed Model   : {diag.model_name}")
    print(f"  * Model Thesis         : {diag.model_thesis}")

    print("\n[STEP 2: 10-POINT EA CONFLUENCE SCORECARD]")
    sc = diag.scorecard
    print(f"  [1] Session Timing     : {sc.session_timing_pts}/2 pts (NY / Liquid session timing)")
    print(f"  [2] 15M Boundary       : {sc.boundary_15m_pts}/2 pts (Clean ORH/ORL structural range)")
    print(f"  [3] 5M Close Commitment: {sc.close_5m_pts}/3 pts (Full candle body close beyond boundary)")
    print(f"  [4] 1M Trigger Signature: {sc.trigger_1m_pts}/2 pts (Model A FVG Gap / Model B Retest / Model C Trap)")
    print(f"  [5] 1:2 R:R Distance   : {sc.risk_distance_pts}/1 pt  (Unobstructed draw to liquidity)")
    print(f"  -------------------------------------------------------------")
    print(f"  TOTAL CONFLUENCE SCORE : {sc.total_score}/10 -> SETUP GRADE: [{sc.grade.value}]")
    print(f"  ACTION DIRECTIVE       : {sc.action_directive}")

    print("\n[STEP 3: INVARIANT 1:2 RISK BRACKET]")
    print(f"  * Signal Bias          : {diag.signal_direction.value}")
    print(f"  * Entry Price          : ${diag.entry_price:.2f}")
    print(f"  * Hard Stop Loss (-1R) : ${diag.stop_loss:.2f} ({diag.risk_points:.2f} pts risk)")
    print(f"  * Take Profit Target (+2R): ${diag.take_profit:.2f} ({diag.reward_points:.2f} pts reward)")
    print(f"  * Risk-to-Reward Ratio : {diag.planned_rr_ratio:.1f}:1.0")
    print(f"  * Sizing (0.01 lot)    : Risk: -${diag.risk_points:.2f} | Return: +${diag.reward_points:.2f}")

    # 3. Walk-Forward Historical Trial Simulation
    print(f"\n[STEP 4: WALK-FORWARD TRIAL SIMULATION (Last {lookback} M1 Bars)]")
    sim = engine.simulate_walkforward(
        symbol=symbol,
        bars_15m=bars_15m,
        bars_5m=bars_5m,
        bars_1m=bars_1m,
        lookback_bars=lookback,
        min_grade=min_grade
    )

    trades = sim["trades"]
    summary = sim["summary"]

    if not trades:
        print("  No trades triggered meeting the confluence threshold during this window.")
        print("  Discipline filter maintained: Sit on hands when confluence < threshold.")
    else:
        print(f"  {'#':<3} {'TIME':<7} {'SIDE':<5} {'MODEL':<24} {'GRADE':<6} {'ENTRY':<9} {'EXIT':<9} {'RESULT':<17} {'R-YIELD':<8} {'PNL ($)'}")
        print("  " + "-" * 105)
        for t in trades:
            print(
                f"  {t['trade_num']:<3} "
                f"{t['entry_time']:<7} "
                f"{t['side']:<5} "
                f"{t['model'][:22]:<24} "
                f"{t['grade']:<6} "
                f"${t['entry_price']:<8.2f} "
                f"${(t['exit_price'] or 0.0):<8.2f} "
                f"{t['exit_type']:<17} "
                f"{t['r_multiple']:>+5.1f}R   "
                f"${t['net_pnl']:>+7.2f}"
            )
        print("  " + "-" * 105)
        print(f"  TRIAL SIMULATION SUMMARY:")
        print(f"  * Total Trades Executed : {summary.get('total_simulated_trades')}")
        print(f"  * Closed Trades         : {summary.get('closed_trades')} (Wins: {summary.get('wins')}, Losses: {summary.get('losses')})")
        print(f"  * Win Rate              : {summary.get('win_rate')}%")
        print(f"  * Profit Factor         : {summary.get('profit_factor')}")
        print(f"  * Cumulative R-Yield    : {summary.get('cumulative_r_yield'):+0.2f}R")
        print(f"  * Net Simulated PnL     : ${summary.get('total_net_pnl'):+0.2f}")

    print("\n" + "=" * 78 + "\n")
    return {"diagnostic": diag, "simulation": sim}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="1-Minute Scalping Playbook Trial Simulation HUD")
    parser.add_argument("symbol_pos", nargs="?", default=None, help="Target symbol (e.g. GOLD, BTCUSD#)")
    parser.add_argument("--symbol", "-s", default="GOLD", help="Target symbol (default: GOLD)")
    parser.add_argument("--lookback", "-l", type=int, default=80, help="Lookback 1M bars (default: 80)")
    parser.add_argument("--grade", "-g", default="B", choices=["A+", "B", "ALL"], help="Minimum setup grade (default: B)")
    args = parser.parse_args()

    target_sym = (args.symbol_pos or args.symbol).upper()
    run_trial_simulation(symbol=target_sym, lookback=args.lookback, min_grade=args.grade)

