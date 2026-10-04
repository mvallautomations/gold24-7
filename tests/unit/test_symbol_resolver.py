"""
Unit tests for Broker Symbol Resolver.
Verifies broker abstraction across XAUUSD, GAUUSD, BTCUSD, and ETHUSD.
"""

import pytest
from adapters.broker.symbol_resolver import BrokerSymbolResolver


def test_resolver_xm_defaults():
    resolver = BrokerSymbolResolver(broker="XM")

    # XAUUSD on XM resolves to GAUUSD
    res_gold = resolver.resolve("XAUUSD")
    assert res_gold.requested == "XAUUSD"
    assert res_gold.resolved in ["GAUUSD", "XAUUSD"]
    assert res_gold.broker == "XM"
    assert res_gold.digits == 2
    assert res_gold.point == 0.01

    # BTCUSD on XM
    res_btc = resolver.resolve("BTCUSD")
    assert res_btc.requested == "BTCUSD"
    assert res_btc.resolved in ["BTCUSD", "BTCUSD.m", "BITCOIN"]
    assert res_btc.digits == 2


def test_resolver_live_cache_matching():
    live_broker_universe = ["GAUUSD", "BTCUSD.m", "ETHUSD.m", "EURUSD_i"]
    resolver = BrokerSymbolResolver(broker="XM", active_mt5_symbols=live_broker_universe)

    # Should match live symbol from alias
    res_xau = resolver.resolve("XAUUSD")
    assert res_xau.resolved == "GAUUSD"
    assert res_xau.status == "RESOLVED"

    res_btc = resolver.resolve("BTCUSD")
    assert res_btc.resolved == "BTCUSD.m"
    assert res_btc.status == "RESOLVED"
