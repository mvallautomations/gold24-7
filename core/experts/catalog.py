"""
Experts, Indicators, and Strategy Setups Testing Matrix Catalog.
Consolidates MT5 tools from projects/Stock-Trading with algorithmic engines in gold24-7.
"""

from typing import Dict, List, Any
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
STOCK_TRADING_DIR = ROOT_DIR.parent / "projects" / "Stock-Trading"


def get_experts_catalog() -> List[Dict[str, Any]]:
    return [
        {
            "id": "gold_training_monitor",
            "name": "GOLD_TrainingMonitorEA.mq5",
            "type": "Read-Only Monitor",
            "origin": "projects/Stock-Trading/Experts/GOLD_TrainingMonitorEA.mq5",
            "status": "READY_TO_ATTACH",
            "role": "Real-time on-chart situational awareness. Computes EMA 20/50/200 and Stochastic (14,3,3) on chart timer. Emits popup and push alerts on extreme conditions (<20, >80).",
            "risk_profile": "ZERO RISK (Does not execute, modify, or close trades)",
            "parameters": [
                {"name": "InpExpectedSymbolFragment", "default": "GOLD", "desc": "Safety check for gold symbol"},
                {"name": "InpFastEMA / SlowEMA / TrendEMA", "default": "20 / 50 / 200", "desc": "EMA alignment calculation"},
                {"name": "InpStochK / D / Slowing", "default": "14 / 3 / 3", "desc": "Stochastic momentum parameters"},
                {"name": "InpPopupAlerts / InpTimerSeconds", "default": "true / 30s", "desc": "Alert frequency"}
            ],
            "setup_instructions": "Copy to MQL5/Experts/ → Compile in MetaEditor (F7) → Drag to H1 or M1 chart."
        },
        {
            "id": "m1_pullback_benchmark",
            "name": "M1_Pullback_Benchmark_EA.mq5",
            "type": "Symmetrical Pullback Scalper",
            "origin": "core/M1_Pullback_Benchmark_EA.mq5",
            "status": "ACTIVE_PAPER_BENCHMARK",
            "role": "Production-grade symmetrical EA. Full BUY and SELL symmetry, completed bar evaluation (shift=1), dynamic ATR stop loss and take profit brackets.",
            "risk_profile": "CONTROLLED (Invariant 1:2 R:R bracket, ATR percentile filter)",
            "parameters": [
                {"name": "InpAtrPeriod", "default": "14", "desc": "Relative ATR engine filter"},
                {"name": "InpRiskRewardRatio", "default": "2.0", "desc": "Strict 1:2 Risk-to-Reward enforcement"},
                {"name": "InpMaxSpreadPoints", "default": "35", "desc": "Dynamic spread gate"}
            ],
            "setup_instructions": "Copy to MQL5/Experts/ → Compile in MetaEditor → Run in MT5 Strategy Tester on M1."
        },
        {
            "id": "btcusd_pullback_benchmark",
            "name": "BTCUSD_Pullback_Benchmark_EA.mq5",
            "type": "24/7 Crypto Scalper",
            "origin": "core/BTCUSD_Pullback_Benchmark_EA.mq5",
            "status": "ACTIVE_CRYPTO_BENCHMARK",
            "role": "Specialized 24/7 crypto scalp EA calibrated for XM BTCUSD# contract specs (tick_value=0.01, spread=1500-2500 pts).",
            "risk_profile": "CONTROLLED (Dynamic lot sizing, crypto spread threshold)",
            "parameters": [
                {"name": "InpCryptoSpreadMax", "default": "2500 pts", "desc": "Crypto-specific spread gate"},
                {"name": "InpDynamicLots", "default": "0.01", "desc": "Micro-lot sizing for crypto testing"}
            ],
            "setup_instructions": "Attach to XM BTCUSD# chart window (M1 or M5 timeframe)."
        },
        {
            "id": "option_b_recoup",
            "name": "OptionB_Mitigate_And_Recoup.mq5",
            "type": "Drawdown Mitigation Engine",
            "origin": "core/OptionB_Mitigate_And_Recoup.mq5",
            "status": "SAFETY_STANDBY",
            "role": "Autonomous drawdown resolution and hedging engine for open positions with active market re-entry.",
            "risk_profile": "ADVANCED (Requires active supervision)",
            "parameters": [
                {"name": "InpMaxDrawdownMitigatePct", "default": "15.0%", "desc": "Trigger threshold for recoupment"},
                {"name": "InpHedgeRatio", "default": "0.5", "desc": "Conservative delta-hedging"}
            ],
            "setup_instructions": "Deploy only during controlled recovery or testing on demo account."
        }
    ]


def get_indicators_catalog() -> List[Dict[str, Any]]:
    return [
        {
            "id": "gold_auto_trend_channel",
            "name": "GOLD_AutoTrendChannel.mq5",
            "type": "Chart Object Helper / Swing Detector",
            "origin": "projects/Stock-Trading/Indicators/GOLD_AutoTrendChannel.mq5",
            "status": "READY_TO_ATTACH",
            "role": "Detects confirmed Swing Highs (SH) and Swing Lows (SL) using rolling lookback and left/right fractal bars. Draws candidate trendlines.",
            "parameters": [
                {"name": "InpLookbackBars", "default": "180 (D1) / 150 (H4) / 200 (H1) / 300 (M1)", "desc": "Analysis window"},
                {"name": "InpLeftBars / RightBars", "default": "3 to 4", "desc": "Fractal swing confirmation"},
                {"name": "InpDrawSwingLabels", "default": "true (SH=Tomato, SL=DeepSkyBlue)", "desc": "Chart labels"},
                {"name": "InpDrawCandidateLines", "default": "true (Orange dashed line)", "desc": "Trendline rays"}
            ],
            "setup_instructions": "Copy to MQL5/Indicators/ → Compile (F7) → Attach to D1, H4, H1, M1 charts."
        },
        {
            "id": "gold_daily_analysis_snapshot",
            "name": "GOLD_DailyAnalysisSnapshot.mq5",
            "type": "Export Script",
            "origin": "projects/Stock-Trading/Scripts/GOLD_DailyAnalysisSnapshot.mq5",
            "status": "READY_TO_RUN",
            "role": "Single-click data export script. Dumps last 100 bars with EMA20, EMA50, EMA200, and Stochastic %K/%D into MQL5/Files/GOLD_analysis_snapshot.csv.",
            "parameters": [
                {"name": "InpBarsToExport", "default": "100", "desc": "Number of completed bars to dump"},
                {"name": "InpFileName", "default": "GOLD_analysis_snapshot.csv", "desc": "Output destination"}
            ],
            "setup_instructions": "Drag onto active chart from Navigator → Scripts to generate fresh CSV."
        }
    ]


def get_strategy_setups_to_test() -> List[Dict[str, Any]]:
    return [
        {
            "id": "setup_1_mtf_ema_swing",
            "name": "Setup 1: Multi-Timeframe EMA & Swing Pullback",
            "category": "Trend Following / Swing Scalp",
            "primary_timeframe": "D1 + H4 Context → H1 Setup → M1 Execution",
            "entry_rule": "D1 & H4 Bullish EMA alignment (Close > 20 > 50 > 200). H1 pullbacks into EMA20/50 support. M1 prints confirmed Swing Low (SL) while Stochastic (14,3,3) crosses above 20.",
            "risk_rule": "SL placed below previous M1 swing low; TP targeted at 2x SL distance (Invariant 1:2 R:R).",
            "indicators_used": ["EMA 20/50/200", "Stochastic (14,3,3)", "GOLD_AutoTrendChannel"],
            "validation_gate": "MTF Confluence Score >= 70%, Spread <= 35 pts, Relative ATR != EXTREME.",
            "target_instrument": "GOLD# (XM Global) & XAUUSD",
            "test_status": "READY_FOR_PAPER_TEST"
        },
        {
            "id": "setup_2_1m_scalping_playbook",
            "name": "Setup 2: 1-Minute Scalping Playbook (Models A/B/C)",
            "category": "Opening Range Scalp",
            "primary_timeframe": "15M Range → 5M Confirmation → 1M Execution",
            "entry_rule": "First 15M candle forms Opening Range High/Low (ORH/ORL). 5M bar closes decisively outside range. 1M confirms execution entry via Model A (Direct Breakout Retest), Model B (Equilibrium Bounce), or Model C (Range Failure Reversal).",
            "risk_rule": "Hard mathematical 1:2 R:R (+2R Target, -1R Stop Loss). Maximum 2 setups per session phase.",
            "indicators_used": ["15M ORH/ORL Box", "5M Confirmation Close", "1M S/R Levels"],
            "validation_gate": "10-Point Scorecard Grade A+ (>=8 pts), Spread <= 32 pts.",
            "target_instrument": "GOLD#, BTCUSD#, US30",
            "test_status": "ACTIVE_LIVE_TEST"
        },
        {
            "id": "setup_3_stoch_extreme_reversal",
            "name": "Setup 3: Stochastic Extreme Reversal at Major S/R",
            "category": "Mean Reversion / Liquidity Sweep",
            "primary_timeframe": "H4 Liquidity Corridor → H1 Reversal",
            "entry_rule": "Price sweeps empirical H4 or D1 Support/Resistance zone (detected by SupportResistanceEngine). Stochastic %K drops below 15 or exceeds 85, then crosses back inside the band on a completed shift=1 candle.",
            "risk_rule": "SL outside liquidity zone buffer; TP at opposite 50% equilibrium level (min 1:1.5 R:R).",
            "indicators_used": ["SupportResistanceEngine", "Stochastic (14,3,3)", "Relative ATR"],
            "validation_gate": "Relative ATR regime must be NORMAL or HIGH (never VERY_LOW chop).",
            "target_instrument": "GOLD#, EURUSD, BTCUSD#",
            "test_status": "READY_FOR_PAPER_TEST"
        },
        {
            "id": "setup_4_news_volatility_gate",
            "name": "Setup 4: High-Impact News & Volatility Gate",
            "category": "Event Safety / Post-News Expansion",
            "primary_timeframe": "M15 + M5 post-news stabilization",
            "entry_rule": "30-minute mandatory freeze after high-impact USD events (CPI, NFP, FOMC). Wait for spread to return <= 35 pts and ATR to normalize. Enter on breakout of the 30-minute post-news range.",
            "risk_rule": "SL at midpoint of the post-news candle range; TP at +2R expansion.",
            "indicators_used": ["Relative ATR VolatilityEngine", "Economic Calendar Filter", "Live Spread Monitor"],
            "validation_gate": "No trading within 15 minutes before or 30 minutes after red folder event.",
            "target_instrument": "GOLD#",
            "test_status": "READY_FOR_PAPER_TEST"
        }
    ]
