"""
Multi-Timeframe Market Analyzer: Produces deterministic, structured market state
across D1, H4, H1, M15, M5, and M1 timeframes.
Strictly separates CURRENT_FORMING_BAR from COMPLETED_BAR (shift 1).
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field
import numpy as np

from core.models.candle import Bar, BarShift, Timeframe, CandleStructure
from core.models.zones import SRZone, ZoneType
from core.models.indicators import VolatilityState, TrendDirection, ATRAssessment, IndicatorSummary
from core.models.signal import MarketRegime
from core.indicators.volatility import VolatilityEngine
from core.indicators.zones import SupportResistanceEngine
from core.indicators.moving_averages import compute_ema, compute_rsi, determine_trend


class TimeframeAnalysis(BaseModel):
    timeframe: Timeframe
    forming_bar: Optional[Bar] = Field(None, description="Shift 0 - active unclosed bar")
    completed_bar: Bar = Field(..., description="Shift 1 - finalized closed bar")
    trend: TrendDirection
    atr: ATRAssessment
    ema_fast: float
    ema_slow: float
    rsi: float
    candle_structure: CandleStructure
    support_zones: List[SRZone]
    resistance_zones: List[SRZone]
    swing_highs: List[float]
    swing_lows: List[float]


class MultiTimeframeMarketState(BaseModel):
    symbol: str
    broker: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    macro_bias: TrendDirection = Field(..., description="D1 & H4 consensus trend")
    execution_bias: TrendDirection = Field(..., description="M15 & M5 trend")
    mtf_confluence_score: float = Field(..., description="0.0 to 1.0 consensus score")
    market_regime: MarketRegime
    is_safe_to_evaluate: bool = True
    timeframes: Dict[str, TimeframeAnalysis]


class MultiTimeframeMarketAnalyzer:
    """
    Orchestrates deterministic multi-timeframe evaluation.
    Guarantees no LLM hallucination of price levels, ATR, or trend direction.
    """

    def __init__(self):
        self.volatility_engine = VolatilityEngine(period=14, lookback_window=100)
        self.sr_engine = SupportResistanceEngine(swing_window=3, cluster_tolerance_pct=0.002)

    def analyze_single_timeframe(
        self,
        timeframe: Timeframe,
        bars: List[Bar]
    ) -> TimeframeAnalysis:
        """Analyze a single timeframe's bar sequence."""
        if not bars:
            raise ValueError(f"No bars provided for timeframe {timeframe}")

        # Separate forming bar (shift 0) and completed bars (shift >= 1)
        forming_bar = next((b for b in bars if b.shift == 0), None)
        completed_bars = [b for b in bars if b.shift >= 1]

        if not completed_bars:
            raise ValueError(f"No completed bars (shift >= 1) found for {timeframe}")

        last_completed = completed_bars[-1]
        closes = [b.close for b in completed_bars]

        # 1. Indicators
        atr_assessment = self.volatility_engine.assess_volatility(completed_bars)
        trend = determine_trend(completed_bars, fast_period=9, slow_period=21)
        ema_fast = compute_ema(closes, 9)[-1]
        ema_slow = compute_ema(closes, 21)[-1]
        rsi = compute_rsi(completed_bars, 14)

        # 2. Support & Resistance Zones
        all_zones = self.sr_engine.build_zones(completed_bars, timeframe, atr=atr_assessment.current_atr)
        curr_price = last_completed.close
        support_zones = [z for z in all_zones if z.type == ZoneType.SUPPORT and z.high <= curr_price * 1.002]
        resistance_zones = [z for z in all_zones if z.type == ZoneType.RESISTANCE and z.low >= curr_price * 0.998]

        # 3. Swings
        sh_tuples, sl_tuples = self.sr_engine.find_swings(completed_bars)
        swing_highs = [round(p, 4) for _, p in sh_tuples[-5:]]
        swing_lows = [round(p, 4) for _, p in sl_tuples[-5:]]

        # 4. Candle Structure (Impulse vs Pullback)
        is_impulse = False
        is_pullback = False
        pullback_depth = 0.0

        if len(completed_bars) >= 2:
            prev_bar = completed_bars[-2]
            # Bullish impulse followed by shallow pullback
            if prev_bar.is_bullish and prev_bar.body_range > (atr_assessment.current_atr * 0.5):
                is_impulse = True
                if last_completed.close < prev_bar.close and last_completed.low > prev_bar.mid_point:
                    is_pullback = True
                    pullback_depth = (prev_bar.close - last_completed.close) / (prev_bar.total_range or 1.0)
            # Bearish impulse followed by shallow pullback
            elif prev_bar.is_bearish and prev_bar.body_range > (atr_assessment.current_atr * 0.5):
                is_impulse = True
                if last_completed.close > prev_bar.close and last_completed.high < prev_bar.mid_point:
                    is_pullback = True
                    pullback_depth = (last_completed.close - prev_bar.close) / (prev_bar.total_range or 1.0)

        candle_struct = CandleStructure(
            timeframe=timeframe,
            completed_bar=last_completed,
            forming_bar=forming_bar,
            is_impulse=is_impulse,
            is_pullback=is_pullback,
            pullback_depth=round(pullback_depth, 3)
        )

        return TimeframeAnalysis(
            timeframe=timeframe,
            forming_bar=forming_bar,
            completed_bar=last_completed,
            trend=trend,
            atr=atr_assessment,
            ema_fast=round(ema_fast, 4),
            ema_slow=round(ema_slow, 4),
            rsi=round(rsi, 2),
            candle_structure=candle_struct,
            support_zones=support_zones[-3:],
            resistance_zones=resistance_zones[:3],
            swing_highs=swing_highs,
            swing_lows=swing_lows,
        )

    def analyze_full_market(
        self,
        symbol: str,
        broker: str,
        timeframe_data: Dict[Timeframe, List[Bar]]
    ) -> MultiTimeframeMarketState:
        """
        Evaluate full multi-timeframe suite (D1, H4, H1, M15, M5, M1).
        """
        tf_results: Dict[str, TimeframeAnalysis] = {}

        for tf, bars in timeframe_data.items():
            tf_results[tf.value] = self.analyze_single_timeframe(tf, bars)

        # Macro Bias (D1 + H4)
        d1_trend = tf_results.get("D1", tf_results.get("H1")).trend if ("D1" in tf_results or "H1" in tf_results) else TrendDirection.NEUTRAL
        h4_trend = tf_results.get("H4", tf_results.get("H1")).trend if ("H4" in tf_results or "H1" in tf_results) else TrendDirection.NEUTRAL

        if d1_trend == h4_trend and d1_trend != TrendDirection.NEUTRAL:
            macro_bias = d1_trend
        elif d1_trend != TrendDirection.NEUTRAL:
            macro_bias = d1_trend
        else:
            macro_bias = h4_trend

        # Execution Bias (M15 + M5 + M1)
        m15_trend = tf_results.get("M15", tf_results.get("M5")).trend if ("M15" in tf_results or "M5" in tf_results) else TrendDirection.NEUTRAL
        m5_trend = tf_results.get("M5", tf_results.get("M1")).trend if ("M5" in tf_results or "M1" in tf_results) else TrendDirection.NEUTRAL
        m1_trend = tf_results.get("M1", tf_results.get("M5")).trend if ("M1" in tf_results or "M5" in tf_results) else TrendDirection.NEUTRAL

        if m15_trend == m5_trend and m15_trend != TrendDirection.NEUTRAL:
            execution_bias = m15_trend
        else:
            execution_bias = m1_trend

        # Confluence calculation
        all_trends = [tf.trend for tf in tf_results.values()]
        bullish_count = sum(1 for t in all_trends if t == TrendDirection.BULLISH)
        bearish_count = sum(1 for t in all_trends if t == TrendDirection.BEARISH)
        total_tfs = len(all_trends) or 1

        confluence_score = round(max(bullish_count, bearish_count) / total_tfs, 2)

        # Market Regime
        m5_atr = tf_results.get("M5", list(tf_results.values())[0]).atr
        if m5_atr.state in [VolatilityState.EXTREME]:
            regime = MarketRegime.VOLATILE
        elif confluence_score >= 0.65:
            regime = MarketRegime.TRENDING
        elif m5_atr.state in [VolatilityState.VERY_LOW, VolatilityState.LOW]:
            regime = MarketRegime.RANGING
        else:
            regime = MarketRegime.UNCERTAIN

        return MultiTimeframeMarketState(
            symbol=symbol,
            broker=broker,
            macro_bias=macro_bias,
            execution_bias=execution_bias,
            mtf_confluence_score=confluence_score,
            market_regime=regime,
            is_safe_to_evaluate=m5_atr.is_tradable,
            timeframes=tf_results
        )
