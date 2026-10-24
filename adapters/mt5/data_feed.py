"""
MT5 Multi-Timeframe Data Feed: Translates raw broker rates into canonical Bar models.
Provides seamless fallback to synthetic historical market data when MT5 is offline.
"""

from typing import Dict, List, Optional
from datetime import datetime, timezone
import logging

from core.models.candle import Bar, BarShift, Timeframe
from adapters.mcp.client import MT5MCPClient
from adapters.broker.symbol_resolver import BrokerSymbolResolver
from backtest.datasets.data_generator import MarketDataGenerator

logger = logging.getLogger(__name__)


class MT5DataFeed:
    """
    Supplies the pipeline with clean, multi-timeframe candle datasets.
    """

    def __init__(
        self,
        mcp_client: Optional[MT5MCPClient] = None,
        resolver: Optional[BrokerSymbolResolver] = None
    ):
        self.mcp_client = mcp_client or MT5MCPClient()
        self.resolver = resolver or BrokerSymbolResolver()

    async def get_multitimeframe_bars(
        self,
        requested_symbol: str
    ) -> Dict[Timeframe, List[Bar]]:
        """
        Fetch all 6 canonical timeframes (D1, H4, H1, M15, M5, M1) for requested symbol.
        """
        resolution = self.resolver.resolve(requested_symbol)
        resolved_sym = resolution.resolved

        # If live MT5 MCP is connected, retrieve live rates
        is_live = await self.mcp_client.ping()
        if is_live:
            if not self.resolver.active_mt5_symbols:
                live_symbols = await self.mcp_client.get_symbols()
                if live_symbols:
                    self.resolver.update_mt5_symbol_cache(live_symbols)
                    resolution = self.resolver.resolve(requested_symbol)
                    resolved_sym = resolution.resolved

            bars_by_tf = {}
            for tf in [Timeframe.D1, Timeframe.H4, Timeframe.H1, Timeframe.M15, Timeframe.M5, Timeframe.M1]:
                raw_rates = await self.mcp_client.get_rates(resolved_sym, tf.value, count=100)
                if raw_rates:
                    bars_by_tf[tf] = self._parse_rates(raw_rates)
            if len(bars_by_tf) == 6:
                return bars_by_tf

        # Fallback to high-fidelity synthetic market data
        logger.info(f"Using high-fidelity market data generator for {resolved_sym} ({resolution.broker})")
        start_price = 2650.0 if "XAU" in resolved_sym or "GAU" in resolved_sym or "GOLD" in resolved_sym else (
            65000.0 if "BTC" in resolved_sym else 1.0850
        )
        return MarketDataGenerator.generate_multitimeframe_suite(
            symbol=resolved_sym,
            start_price=start_price,
            seed=int(datetime.now(timezone.utc).timestamp()) % 10000
        )

    def _parse_rates(self, raw_rates: List[Dict]) -> List[Bar]:
        bars = []
        n = len(raw_rates)
        for i, r in enumerate(raw_rates):
            shift = n - 1 - i
            shift_type = BarShift.CURRENT_FORMING_BAR if shift == 0 else BarShift.COMPLETED_BAR
            ts = datetime.fromtimestamp(r["time"], timezone.utc) if isinstance(r["time"], (int, float)) else datetime.now(timezone.utc)
            bars.append(Bar(
                timestamp=ts,
                open=float(r["open"]),
                high=float(r["high"]),
                low=float(r["low"]),
                close=float(r["close"]),
                volume=float(r.get("tick_volume", r.get("volume", 0))),
                shift=shift,
                shift_type=shift_type
            ))
        return bars
