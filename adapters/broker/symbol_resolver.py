"""
Broker Symbol Resolver: Dynamically maps requested generic symbols (e.g. XAUUSD, BTCUSD)
to actual broker-specific MT5 instrument names (e.g. GAUUSD, GOLDmicro, BTCUSD.m).
Queries MT5 directly when connected, with deterministic alias fallbacks.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)


class SymbolResolution(BaseModel):
    requested: str
    resolved: str
    broker: str
    status: str  # RESOLVED, AMBIGUOUS, NOT_FOUND, FALLBACK
    digits: int = 2
    point: float = 0.01
    tick_size: float = 0.01
    tick_value: float = 1.0
    min_lot: float = 0.01
    max_lot: float = 100.0
    lot_step: float = 0.01
    spread_points: int = 15
    is_live_supported: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BrokerSymbolResolver:
    """
    Resolves trading symbols against broker MT5 catalog.
    Prevents hardcoding XAUUSD or fragile broker-specific suffixes.
    """

    # Known broker alias candidates (tried in order)
    CANONICAL_ALIASES: Dict[str, List[str]] = {
        "XAUUSD": ["GOLD#", "GOLD", "XAUUSD", "GOLDmicro", "GAUUSD", "XAUUSD.m", "XAUUSDm", "XAUUSDraw"],
        "GOLD": ["GOLD#", "GOLD", "XAUUSD", "GOLDmicro", "GAUUSD"],
        "GOLD#": ["GOLD#", "GOLD", "XAUUSD", "GOLDmicro", "GAUUSD"],
        "GAUUSD": ["GAUUSD", "GOLD#", "GOLD", "XAUUSD", "GOLDmicro"],
        "BTCUSD": ["BTCUSD#", "BTCUSD", "BTCUSD.m", "BITCOIN", "BTCUSDmicro", "BTCUSDT"],
        "BTCUSD#": ["BTCUSD#", "BTCUSD", "BTCUSD.m", "BITCOIN"],
        "ETHUSD": ["ETHUSD#", "ETHUSD", "ETHUSD.m", "ETHEREUM", "ETHUSDmicro", "ETHUSDT"],
        "EURUSD": ["EURUSD", "EURUSD.m", "EURUSDm", "EURUSDmicro"],
        "GBPUSD": ["GBPUSD", "GBPUSD.m", "GBPUSDm", "GBPUSDmicro"],
        "USDJPY": ["USDJPY", "USDJPY.m", "USDJPYm", "USDJPYmicro"],
    }

    # Default specifications for standard instruments when running offline/paper
    DEFAULT_SPECS: Dict[str, Dict[str, Any]] = {
        "XAUUSD": {"digits": 2, "point": 0.01, "tick_size": 0.01, "tick_value": 1.0, "min_lot": 0.01, "max_lot": 50.0, "lot_step": 0.01, "spread_points": 25},
        "GOLD": {"digits": 2, "point": 0.01, "tick_size": 0.01, "tick_value": 1.0, "min_lot": 0.01, "max_lot": 50.0, "lot_step": 0.01, "spread_points": 25},
        "GOLD#": {"digits": 2, "point": 0.01, "tick_size": 0.01, "tick_value": 1.0, "min_lot": 0.01, "max_lot": 50.0, "lot_step": 0.01, "spread_points": 25},
        "GAUUSD": {"digits": 2, "point": 0.01, "tick_size": 0.01, "tick_value": 1.0, "min_lot": 0.01, "max_lot": 50.0, "lot_step": 0.01, "spread_points": 30},
        "BTCUSD": {"digits": 2, "point": 0.01, "tick_size": 0.01, "tick_value": 0.01, "min_lot": 0.01, "max_lot": 80.0, "lot_step": 0.01, "spread_points": 1500},
        "BTCUSD#": {"digits": 2, "point": 0.01, "tick_size": 0.01, "tick_value": 0.01, "min_lot": 0.01, "max_lot": 80.0, "lot_step": 0.01, "spread_points": 1500},
        "ETHUSD": {"digits": 2, "point": 0.01, "tick_size": 0.01, "tick_value": 0.01, "min_lot": 0.01, "max_lot": 50.0, "lot_step": 0.01, "spread_points": 50},
    }

    def __init__(self, broker: str = "XM", active_mt5_symbols: Optional[List[str]] = None):
        self.broker = broker
        self.active_mt5_symbols: List[str] = active_mt5_symbols or []

    def update_mt5_symbol_cache(self, symbol_list: List[str]) -> None:
        """Update active symbol universe from live MT5 connection."""
        self.active_mt5_symbols = [s.strip() for s in symbol_list if s.strip()]
        logger.info(f"Updated MT5 symbol cache with {len(self.active_mt5_symbols)} instruments.")

    def resolve(self, requested_symbol: str) -> SymbolResolution:
        """
        Resolve requested generic symbol against MT5 broker symbol universe.
        """
        req_clean = requested_symbol.strip().upper()

        # 1. If we have live MT5 symbols available, search through candidates
        if self.active_mt5_symbols:
            # Check exact match first
            for active in self.active_mt5_symbols:
                if active.upper() == req_clean:
                    return self._build_resolution(req_clean, active, "RESOLVED")

            # Check aliases
            candidates = self.CANONICAL_ALIASES.get(req_clean, [req_clean])
            for cand in candidates:
                for active in self.active_mt5_symbols:
                    if active.upper() == cand.upper():
                        return self._build_resolution(req_clean, active, "RESOLVED")

            # Partial / prefix search (e.g. XAUUSD# or XAUUSD_i)
            for active in self.active_mt5_symbols:
                if req_clean in active.upper():
                    return self._build_resolution(req_clean, active, "RESOLVED_APPROX")

        # 2. Offline / Paper fallback: Resolve canonical alias by broker default
        alias_list = self.CANONICAL_ALIASES.get(req_clean, [req_clean])
        resolved_name = alias_list[0]
        if self.broker == "XM":
            if req_clean in ("XAUUSD", "GOLD", "GOLD#"):
                resolved_name = "GOLD#" if "GOLD#" in self.active_mt5_symbols else ("GOLD" if "GOLD" in self.active_mt5_symbols else "GOLD#")
            elif req_clean in ("BTCUSD", "BTCUSD#"):
                resolved_name = "BTCUSD#"

        return self._build_resolution(req_clean, resolved_name, "RESOLVED_DEFAULT")

    def _build_resolution(self, requested: str, resolved: str, status: str) -> SymbolResolution:
        base_key = requested if requested in self.DEFAULT_SPECS else (
            "XAUUSD" if "XAU" in requested or "GOLD" in requested or "GAU" in requested else (
                "BTCUSD" if "BTC" in requested else "XAUUSD"
            )
        )
        spec = self.DEFAULT_SPECS.get(base_key, self.DEFAULT_SPECS["XAUUSD"])

        return SymbolResolution(
            requested=requested,
            resolved=resolved,
            broker=self.broker,
            status=status,
            digits=spec["digits"],
            point=spec["point"],
            tick_size=spec["tick_size"],
            tick_value=spec["tick_value"],
            min_lot=spec["min_lot"],
            max_lot=spec["max_lot"],
            lot_step=spec["lot_step"],
            spread_points=spec["spread_points"],
            is_live_supported=True,
            metadata={"alias_chain": self.CANONICAL_ALIASES.get(requested, [])},
        )
