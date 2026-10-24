import sys
import os
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Ensure execution within project virtual environment (.venv)
venv_python = ROOT_DIR / ".venv" / "bin" / "python"
if sys.prefix == sys.base_prefix and venv_python.exists():
    os.execv(str(venv_python), [str(venv_python)] + sys.argv)

import json
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any

from core.configuration.config import config
from core.models.candle import Timeframe
from core.market.analyzer import MultiTimeframeMarketAnalyzer
from core.signals.evaluator import SignalEvaluator
from core.validation.validator import DeterministicValidator
from adapters.broker.symbol_resolver import BrokerSymbolResolver
from adapters.mt5.data_feed import MT5DataFeed
from agents.analyzer.interpreter import HermesMarketInterpreter
from execution.paper.engine import PaperTradingEngine
from journal.analytics.performance_engine import PerformanceEngine
from backtest.engine.simulator import BacktestSimulator
from scripts.sync_mt5_to_otw import MT5ToOTWSync

app = FastAPI(title="GOLD24-7 Research & Paper-Trading Dashboard")

resolver = BrokerSymbolResolver(broker="XM")
data_feed = MT5DataFeed(resolver=resolver)
analyzer = MultiTimeframeMarketAnalyzer()
evaluator = SignalEvaluator(reward_ratio=1.5)
validator = DeterministicValidator(min_risk_reward=1.2)
paper_engine = PaperTradingEngine(initial_balance=10000.0)
interpreter = HermesMarketInterpreter()
mt5_syncer = MT5ToOTWSync()

latest_state: Dict[str, Any] = {}


@app.get("/api/status")
async def get_status():
    stats = mt5_syncer.get_account_stats()
    return {
        "status": "ONLINE",
        "environment": "LIVE_ACCOUNT",
        "is_simulation_only": False,
        "live_execution_permitted": False,
        "broker": stats.get("company", "XM Global Limited"),
        "account_login": stats.get("account_login", 335537672),
        "server": stats.get("server", "XMGlobal-MT5 9"),
        "currency": stats.get("currency", "USD"),
        "leverage": stats.get("leverage", 1000),
        "balance": stats.get("balance", 87.09),
        "equity": stats.get("equity", 53.98),
        "unrealized_pnl": stats.get("unrealized_pnl", 0.0),
        "open_positions": stats.get("open_positions_count", 0),
        "closed_positions": stats.get("total_closed_trades", 0),
        "win_rate": stats.get("win_rate", 0.0),
        "profit_factor": stats.get("profit_factor", 1.0),
        "is_live_account": True,
    }


@app.get("/api/evaluate")
async def evaluate_market(symbol: str = "GOLD#", use_hermes: bool = True):
    resolution = resolver.resolve(symbol)
    tf_data = await data_feed.get_multitimeframe_bars(resolution.requested)
    market_state = analyzer.analyze_full_market(resolution.resolved, resolution.broker, tf_data)

    if use_hermes:
        signal = interpreter.generate_hermes_signal(market_state, resolution)
    else:
        signal = evaluator.evaluate(market_state)
        if signal.direction.value != "NONE":
            interpreter.interpret_signal(signal, market_state)

    m1_atr = market_state.timeframes["M1"].atr
    validation = validator.validate_signal(
        signal=signal,
        current_spread_points=resolution.spread_points,
        atr_value=m1_atr.current_atr,
        has_open_position=any(p.symbol == resolution.resolved for p in paper_engine.open_positions.values())
    )

    if validation.is_valid and signal.direction.value != "NONE":
        pos = paper_engine.execute_signal(
            signal,
            point=resolution.point,
            tick_size=resolution.tick_size,
            tick_value=resolution.tick_value
        )

    global latest_state
    latest_state = {
        "resolution": resolution.dict(),
        "market_state": market_state.dict(),
        "signal": signal.dict(),
        "validation": validation.dict(),
        "paper_summary": paper_engine.get_summary()
    }
    return latest_state


@app.get("/api/hermes/signal")
async def get_hermes_signal(symbol: str = "GOLD#"):
    resolution = resolver.resolve(symbol)
    tf_data = await data_feed.get_multitimeframe_bars(resolution.requested)
    market_state = analyzer.analyze_full_market(resolution.resolved, resolution.broker, tf_data)
    open_pos = mt5_syncer.get_live_positions_formatted()
    account_stats = mt5_syncer.get_account_stats()
    signal = interpreter.generate_hermes_signal(
        market_state, resolution, open_positions=open_pos, account_stats=account_stats
    )
    loss_mitigation = interpreter.generate_loss_mitigation_plan(
        open_pos, account_stats, market_state, resolution
    )
    return {
        "signal": signal.dict(),
        "market_state": market_state.dict(),
        "resolution": resolution.dict(),
        "loss_mitigation": loss_mitigation,
        "account_stats": account_stats
    }


@app.get("/api/hermes/loss-mitigation")
async def get_hermes_loss_mitigation(symbol: str = "GOLD#"):
    resolution = resolver.resolve(symbol)
    tf_data = await data_feed.get_multitimeframe_bars(resolution.requested)
    market_state = analyzer.analyze_full_market(resolution.resolved, resolution.broker, tf_data)
    open_pos = mt5_syncer.get_live_positions_formatted()
    account_stats = mt5_syncer.get_account_stats()
    return interpreter.generate_loss_mitigation_plan(open_pos, account_stats, market_state, resolution)


@app.get("/api/market-data")
async def get_market_data(symbol: str = "GOLD#"):
    resolution = resolver.resolve(symbol)
    tf_data = await data_feed.get_multitimeframe_bars(resolution.requested)
    market_state = analyzer.analyze_full_market(resolution.resolved, resolution.broker, tf_data)

    candles_by_tf = {}
    for tf_key, bars in tf_data.items():
        tf_name = tf_key.value if hasattr(tf_key, "value") else str(tf_key)
        digits = resolution.digits if resolution.digits is not None else 2
        candles_by_tf[tf_name] = [
            {
                "time": int(b.timestamp.timestamp()),
                "time_str": b.timestamp.strftime("%H:%M" if tf_name in ["M1", "M5", "M15"] else "%b %d %H:%M"),
                "open": round(b.open, digits),
                "high": round(b.high, digits),
                "low": round(b.low, digits),
                "close": round(b.close, digits),
                "volume": round(b.volume, 2),
            }
            for b in bars
        ]

    latest_close = candles_by_tf.get("M1", [{}])[-1].get("close", 0.0) if candles_by_tf.get("M1") else 0.0
    d1_first = candles_by_tf.get("D1", [{}])[0].get("open", latest_close) if candles_by_tf.get("D1") else latest_close
    chg_24h = latest_close - d1_first if d1_first else 0.0
    chg_pct = (chg_24h / d1_first * 100) if d1_first else 0.0

    current_signal = evaluator.evaluate(market_state)
    m1_atr = market_state.timeframes["M1"].atr
    validation = validator.validate_signal(
        signal=current_signal,
        current_spread_points=resolution.spread_points,
        atr_value=m1_atr.current_atr,
        has_open_position=any(p.symbol == resolution.resolved for p in paper_engine.open_positions.values())
    )

    account_stats = mt5_syncer.get_account_stats()
    live_open_pos = mt5_syncer.get_live_positions_formatted()
    live_closed_pos = mt5_syncer.get_live_closed_trades_formatted(limit=50)

    display_open = live_open_pos if (live_open_pos or not paper_engine.open_positions) else [
        {
            "id": p.position_id,
            "symbol": p.symbol,
            "side": p.side.value.upper(),
            "entry_price": p.entry_price,
            "current_price": latest_close or p.current_price,
            "stop_loss": p.stop_loss,
            "take_profit": p.take_profit,
            "quantity_lots": p.quantity_lots,
            "unrealized_pnl": round((latest_close - p.entry_price if p.side.value == "long" else p.entry_price - latest_close) * p.quantity_lots * (100.0 if "XAU" in p.symbol or "GOLD" in p.symbol else 1.0), 2),
            "opened_at": p.opened_at.strftime("%H:%M:%S")
        }
        for p in paper_engine.open_positions.values()
    ]

    display_closed = live_closed_pos if live_closed_pos else [
        {
            "id": p.position_id,
            "symbol": p.symbol,
            "side": p.side.value.upper(),
            "entry_price": p.entry_price,
            "exit_price": p.exit_price,
            "realized_pnl": p.realized_pnl,
            "exit_reason": p.exit_reason,
            "opened_at": p.opened_at.strftime("%H:%M:%S"),
            "closed_at": p.closed_at.strftime("%H:%M:%S") if p.closed_at else ""
        }
        for p in paper_engine.closed_positions[-10:]
    ]

    bal = account_stats.get("balance", 87.09)
    unrl = account_stats.get("unrealized_pnl", 0.0)
    dd_pct = round(abs(unrl / bal * 100.0), 1) if bal > 0 and unrl < 0 else 0.0
    risk_level = "CRITICAL" if dd_pct >= 30.0 else ("ELEVATED" if dd_pct >= 15.0 else ("MODERATE" if dd_pct > 0 else "STABLE"))

    return {
        "symbol": resolution.resolved,
        "requested": resolution.requested,
        "broker": resolution.broker,
        "current_price": latest_close,
        "change_24h": round(chg_24h, 2),
        "change_pct": round(chg_pct, 2),
        "spread_points": resolution.spread_points,
        "digits": resolution.digits,
        "market_state": market_state.dict(),
        "candles": candles_by_tf,
        "signal": current_signal.dict(),
        "validation": validation.dict(),
        "paper_summary": paper_engine.get_summary(),
        "account_stats": account_stats,
        "account_summary": account_stats,
        "open_positions": display_open,
        "closed_positions": display_closed,
        "drawdown_pct": dd_pct,
        "risk_level": risk_level,
        "server_time": datetime.now(timezone.utc).strftime("%H:%M:%S UTC"),
        "is_mt5_live": data_feed.mcp_client.is_connected,
        "account_login": account_stats.get("account_login", 335537672),
        "account_server": account_stats.get("server", "XMGlobal-MT5 9"),
        "is_live_account": True
    }


@app.get("/api/research/latest")
async def get_latest_research():
    res_path = ROOT_DIR / "docs" / "research" / "phase2_results.json"
    if res_path.exists():
        with open(res_path, "r") as f:
            return json.load(f)
    return {"status": "NO_RUN_FOUND", "message": "Run scripts/run_phase2_validation.py first"}


@app.get("/api/research/regimes")
async def get_regimes_summary():
    res_path = ROOT_DIR / "docs" / "research" / "phase2_results.json"
    if res_path.exists():
        with open(res_path, "r") as f:
            data = json.load(f)
            return data.get("regimes", {})
    return {}


@app.get("/api/backtest")
async def run_backtest(symbol: str = "XAUUSD"):
    resolution = resolver.resolve(symbol)
    tf_data = await data_feed.get_multitimeframe_bars(resolution.requested)
    sim = BacktestSimulator(initial_balance=10000.0)
    result = sim.run_backtest(resolution.resolved, resolution.broker, tf_data, warmup_bars=40)
    return result


@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    with open(ROOT_DIR / "dashboard" / "templates" / "index.html", "r") as f:
        return f.read()


def start_dashboard():
    uvicorn.run(app, host=config.DASHBOARD_HOST, port=config.DASHBOARD_PORT)


if __name__ == "__main__":
    start_dashboard()
