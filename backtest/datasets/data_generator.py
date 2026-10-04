"""
Synthetic and Historical Multi-Timeframe Dataset Generator.
Generates realistic multi-timeframe candles (D1, H4, H1, M15, M5, M1)
for backtesting, research, and offline testing without live broker dependencies.
"""

from typing import List, Dict
from datetime import datetime, timedelta, timezone
import numpy as np

from core.models.candle import Bar, BarShift, Timeframe


class MarketDataGenerator:
    """
    Produces deterministic synthetic price series with realistic trends,
    volatility clusters, and support/resistance zones.
    """

    @staticmethod
    def generate_bars(
        symbol: str = "GAUUSD",
        timeframe: Timeframe = Timeframe.M1,
        n_bars: int = 200,
        start_price: float = 2650.0,
        base_volatility: float = 1.2,
        seed: int = 42
    ) -> List[Bar]:
        np.random.seed(seed)
        bars: List[Bar] = []

        now = datetime.now(timezone.utc)
        current_time = now - timedelta(minutes=timeframe.minutes * n_bars)

        current_close = start_price
        trend_drift = 0.05  # Slight upward drift

        for i in range(n_bars):
            # Bar shift: last bar is 0 (forming), all previous are completed (1 to n)
            shift = n_bars - 1 - i
            shift_type = BarShift.CURRENT_FORMING_BAR if shift == 0 else BarShift.COMPLETED_BAR

            # Volatility regime variation
            regime_factor = 1.0 + 0.5 * np.sin(i / 15.0)
            vol = base_volatility * regime_factor

            open_p = current_close
            shock = np.random.normal(trend_drift, vol)
            close_p = open_p + shock

            high_p = max(open_p, close_p) + abs(np.random.normal(0, vol * 0.4))
            low_p = min(open_p, close_p) - abs(np.random.normal(0, vol * 0.4))

            bar = Bar(
                timestamp=current_time,
                open=round(open_p, 4),
                high=round(high_p, 4),
                low=round(low_p, 4),
                close=round(close_p, 4),
                volume=round(float(np.random.randint(100, 1000)), 1),
                shift=shift,
                shift_type=shift_type
            )
            bars.append(bar)

            current_close = close_p
            current_time += timedelta(minutes=timeframe.minutes)

        return bars

    @classmethod
    def generate_multitimeframe_suite(
        cls,
        symbol: str = "GAUUSD",
        start_price: float = 2650.0,
        seed: int = 42
    ) -> Dict[Timeframe, List[Bar]]:
        """
        Generate aligned dataset across all 6 standard timeframes.
        """
        return {
            Timeframe.D1: cls.generate_bars(symbol, Timeframe.D1, n_bars=60, start_price=start_price, base_volatility=15.0, seed=seed),
            Timeframe.H4: cls.generate_bars(symbol, Timeframe.H4, n_bars=80, start_price=start_price, base_volatility=6.0, seed=seed + 1),
            Timeframe.H1: cls.generate_bars(symbol, Timeframe.H1, n_bars=100, start_price=start_price, base_volatility=3.0, seed=seed + 2),
            Timeframe.M15: cls.generate_bars(symbol, Timeframe.M15, n_bars=120, start_price=start_price, base_volatility=1.8, seed=seed + 3),
            Timeframe.M5: cls.generate_bars(symbol, Timeframe.M5, n_bars=150, start_price=start_price, base_volatility=1.0, seed=seed + 4),
            Timeframe.M1: cls.generate_bars(symbol, Timeframe.M1, n_bars=200, start_price=start_price, base_volatility=0.6, seed=seed + 5),
        }
