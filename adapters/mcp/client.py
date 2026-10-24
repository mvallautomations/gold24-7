"""
MT5 MCP Client: Interacts with the MT5 MCP Server / Bridge over HTTP/SSE.
Retrieves market data, ticks, and symbol lists without ever placing live orders.
"""

from typing import List, Dict, Any, Optional
import httpx
import logging
from core.configuration.config import config

logger = logging.getLogger(__name__)


class MT5MCPClient:
    """
    Client for MT5 MCP Bridge.
    Strict read-only inspection of charts, accounts, and tick streams.
    """

    def __init__(self, base_url: Optional[str] = None):
        url = (base_url or config.MT5_MCP_SERVER_URL).rstrip("/")
        if url.endswith("/sse"):
            url = url[:-4]
        self.base_url = url
        self.is_connected = False

    async def ping(self) -> bool:
        """Check if MT5 MCP server is reachable."""
        candidate_urls = [self.base_url]
        # Allow fallback between gateway IP and localhost
        if "172." in self.base_url:
            import re
            localhost_url = re.sub(r"https?://172\.[0-9.]+", "http://127.0.0.1", self.base_url)
            if localhost_url not in candidate_urls:
                candidate_urls.append(localhost_url)
        elif "127.0.0.1" in self.base_url or "localhost" in self.base_url:
            candidate_urls.append(f"http://{config.MT5_HOST}:{config.MT5_PORT}")

        for url in candidate_urls:
            try:
                async with httpx.AsyncClient(timeout=2.0) as client:
                    res = await client.get(f"{url}/health")
                    if res.status_code == 200:
                        self.base_url = url
                        self.is_connected = True
                        return True
            except Exception:
                continue

        self.is_connected = False
        return False

    async def get_symbols(self) -> List[str]:
        """Fetch available instrument universe from MT5."""
        if not self.is_connected:
            return ["XAUUSD", "GAUUSD", "BTCUSD", "ETHUSD", "EURUSD", "GBPUSD"]

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.post(f"{self.base_url}/rpc", json={
                    "jsonrpc": "2.0",
                    "method": "symbols_get",
                    "params": {},
                    "id": 1
                })
                if res.status_code == 200:
                    data = res.json()
                    return data.get("result", {}).get("symbols", [])
        except Exception as e:
            logger.warning(f"Error fetching symbols via MT5 MCP: {e}")

        return ["XAUUSD", "GAUUSD", "BTCUSD", "ETHUSD"]

    async def get_rates(
        self,
        symbol: str,
        timeframe: str = "M1",
        count: int = 100
    ) -> List[Dict[str, Any]]:
        """Fetch historical candle rates."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.post(f"{self.base_url}/rpc", json={
                    "jsonrpc": "2.0",
                    "method": "rates_get",
                    "params": {"symbol": symbol, "timeframe": timeframe, "count": count},
                    "id": 2
                })
                if res.status_code == 200:
                    return res.json().get("result", {}).get("rates", [])
        except Exception as e:
            logger.debug(f"MT5 MCP rates_get offline: {e}")

        return []
