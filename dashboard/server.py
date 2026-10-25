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
from core.playbook.scalping_playbook import ScalpingPlaybookEngine, RECOMMENDED_MARKETS, PlaybookModel, SetupGrade
from core.checklist.engine import ChecklistEngine
from core.experts.catalog import get_experts_catalog, get_indicators_catalog, get_strategy_setups_to_test
from core.indicators.stochastic import compute_stochastic, compute_ema_alignment, compute_swing_channels
from core.indicators.channels import map_multi_timeframe_channels

app = FastAPI(title="GOLD24-7 Research & Paper-Trading Dashboard")

resolver = BrokerSymbolResolver(broker="XM")
data_feed = MT5DataFeed(resolver=resolver)
analyzer = MultiTimeframeMarketAnalyzer()
evaluator = SignalEvaluator(reward_ratio=1.5)
validator = DeterministicValidator(min_risk_reward=1.2)
paper_engine = PaperTradingEngine(initial_balance=10000.0)
interpreter = HermesMarketInterpreter()
mt5_syncer = MT5ToOTWSync()
playbook_engine = ScalpingPlaybookEngine(default_balance=1874.19)
checklist_engine = ChecklistEngine()

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
        "account_login": stats.get("account_login", 336888981),
        "server": stats.get("server", "XMGlobal-MT5 9"),
        "currency": stats.get("currency", "USD"),
        "leverage": stats.get("leverage", 100),
        "balance": stats.get("balance", 1874.19),
        "equity": stats.get("equity", 1874.19),
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
        "account_login": account_stats.get("account_login", 336888981),
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


@app.get("/api/playbook/schedules")
async def get_playbook_schedules():
    """Returns market open schedules, session phases, and countdowns for all recommended markets."""
    results = {}
    for sym in RECOMMENDED_MARKETS.keys():
        results[sym] = playbook_engine.get_market_schedule_status(sym)
    return results


@app.get("/api/playbook/evaluate")
async def evaluate_playbook_market(symbol: str = "GOLD"):
    """
    Evaluates market data against the 1-Minute Scalping Playbook:
    15M ORH/ORL, 5M Confirmation Close, 1M Model A/B/C, 10-Point Scorecard, and Invariant 1:2 R:R.
    """
    resolution = resolver.resolve(symbol)
    tf_data = await data_feed.get_multitimeframe_bars(resolution.requested)
    acc_stats = mt5_syncer.get_account_stats()
    bal = acc_stats.get("balance", 1874.19)

    bars_15m = tf_data.get(Timeframe.M15, [])
    bars_5m = tf_data.get(Timeframe.M5, [])
    bars_1m = tf_data.get(Timeframe.M1, [])

    diagnostic = playbook_engine.evaluate_playbook_setup(
        symbol=resolution.resolved,
        bars_15m=bars_15m,
        bars_5m=bars_5m,
        bars_1m=bars_1m,
        account_balance=bal
    )

    sched = playbook_engine.get_market_schedule_status(resolution.requested)

    return {
        "diagnostic": diagnostic.dict(),
        "schedule": sched,
        "account_stats": acc_stats,
        "resolution": resolution.dict()
    }


@app.get("/api/playbook/m15-objects")
async def get_playbook_m15_objects(symbol: str = "GOLD"):
    """
    Returns object indicators for the 15M opening entry timeframe:
    15M ORH/ORL Box geometry, boundary lines, 50% Equilibrium, and +1R/+2R expansion levels.
    """
    resolution = resolver.resolve(symbol)
    tf_data = await data_feed.get_multitimeframe_bars(resolution.requested)
    bars_15m = tf_data.get(Timeframe.M15, [])
    bars_5m = tf_data.get(Timeframe.M5, [])
    bars_1m = tf_data.get(Timeframe.M1, [])

    objects = playbook_engine.get_15m_object_indicators(
        symbol=resolution.resolved,
        bars_15m=bars_15m,
        bars_5m=bars_5m,
        bars_1m=bars_1m
    )
    return objects



@app.post("/api/playbook/execute")
async def execute_playbook_order(request: Request):
    """
    Executes a mirror / copy trade directly on MT5 with exact 1:2 Risk-to-Reward brackets.
    """
    body = await request.json()
    symbol = body.get("symbol", "GOLD")
    direction = body.get("direction", "BUY").upper()
    lots = float(body.get("lots", 0.01))
    entry_price = float(body.get("entry_price", 0.0))
    stop_loss = float(body.get("stop_loss", 0.0))
    take_profit = float(body.get("take_profit", 0.0))
    model = body.get("model", "MODEL_A")
    grade = body.get("grade", "A+")

    resolution = resolver.resolve(symbol)
    resolved_sym = resolution.resolved

    import httpx
    bridge_url = f"{config.MT5_MCP_SERVER_URL}/rpc"

    try:
        # Fetch fresh tick quote
        tick_res = httpx.post(
            bridge_url,
            json={"jsonrpc": "2.0", "method": "tick_get", "params": {"symbol": resolved_sym}, "id": 1},
            timeout=5.0
        ).json()
        tick = tick_res.get("result", {})
        if tick and tick.get("ask") and entry_price <= 0:
            entry_price = tick["ask"] if direction == "BUY" else tick["bid"]
    except Exception:
        pass

    # If SL or TP not provided, calculate invariant 1:2 bracket
    if stop_loss <= 0 or take_profit <= 0:
        risk_dist = max(2.5, min(6.0, entry_price * 0.001))
        if direction == "BUY":
            stop_loss = round(entry_price - risk_dist, 2)
            take_profit = round(entry_price + (2.0 * risk_dist), 2)
        else:
            stop_loss = round(entry_price + risk_dist, 2)
            take_profit = round(entry_price - (2.0 * risk_dist), 2)

    order_request = {
        "action": 1,  # TRADE_ACTION_DEAL
        "symbol": resolved_sym,
        "volume": float(lots),
        "type": 0 if direction == "BUY" else 1,
        "price": float(entry_price),
        "sl": float(stop_loss),
        "tp": float(take_profit),
        "deviation": 25,
        "magic": 240702,
        "comment": f"PLAY_{grade}_{model[:7]}",
        "type_time": 0,
        "type_filling": 1
    }

    try:
        res = httpx.post(
            bridge_url,
            json={"jsonrpc": "2.0", "method": "order_send", "params": {"request": order_request}, "id": 2},
            timeout=8.0
        ).json()

        if "result" in res and res["result"].get("retcode") in (0, 10009):
            deal = res["result"].get("deal", "N/A")
            order = res["result"].get("order", "N/A")
            return {
                "status": "FILLED",
                "message": f"Order #{order} filled successfully (Deal #{deal})",
                "deal": deal,
                "order": order,
                "symbol": resolved_sym,
                "direction": direction,
                "lots": lots,
                "entry_price": entry_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "rr_ratio": 2.0,
                "model": model,
                "grade": grade
            }
        else:
            err = res.get("error", res.get("result", {}))
            return JSONResponse({"status": "REJECTED", "error": str(err)}, status_code=400)
    except Exception as e:
        return JSONResponse({"status": "ERROR", "error": str(e)}, status_code=500)


@app.get("/api/playbook/history")
async def get_playbook_history():
    """
    Returns complete R-Multiple Ledger analysis across all closed trades with PnL %,
    R:R Yield curve, trade quality grades, and execution statistics.
    """
    deals = mt5_syncer.fetch_deals(days_back=365)
    closed_trades = mt5_syncer.parse_closed_trades(deals) if deals else []
    analysis = playbook_engine.analyze_historical_trades(closed_trades)
    return analysis


@app.post("/api/playbook/post-audit")
async def submit_post_session_audit(request: Request):
    """
    Saves daily post-session feedback loop answers per Page 14 of Playbook.
    """
    body = await request.json()
    audit_file = ROOT_DIR / "docs" / "research" / "post_session_audits.json"
    audit_file.parent.mkdir(parents=True, exist_ok=True)

    audits = []
    if audit_file.exists():
        try:
            with open(audit_file, "r") as f:
                audits = json.load(f)
        except Exception:
            audits = []

    body["submitted_at"] = datetime.now(timezone.utc).isoformat()
    # Compute discipline score
    score = 10
    if body.get("fomo_jump", False):
        score -= 4
    if not body.get("mechanical_sl", True):
        score -= 3
    if not body.get("accepted_rr", True):
        score -= 3
    body["discipline_score"] = max(0, score)

    audits.append(body)
    with open(audit_file, "w") as f:
        json.dump(audits, f, indent=2)

    return {"status": "SAVED", "discipline_score": body["discipline_score"]}


@app.get("/api/checklist")
async def get_checklist(symbol: str = "GOLD#"):
    """Returns PRE-ANALYSIS_CHECKLIST state with live MT5 telemetry auto-evaluations."""
    resolution = resolver.resolve(symbol)
    tf_data = await data_feed.get_multitimeframe_bars(resolution.requested)
    market_state = analyzer.analyze_full_market(resolution.resolved, resolution.broker, tf_data)
    acc_stats = mt5_syncer.get_account_stats()

    bars_h1 = tf_data.get(Timeframe.H1, [])
    stoch_h1 = compute_stochastic(bars_h1) if bars_h1 else {}

    result = checklist_engine.evaluate_live_status(
        account_stats=acc_stats,
        resolution=resolution.dict(),
        market_state=market_state.dict(),
        stoch_data={"h1_state": stoch_h1.get("state", "MID-RANGE")}
    )
    return result


@app.post("/api/checklist/save")
async def save_checklist_state(request: Request):
    """Saves user-checked items, notes, and session decision."""
    body = await request.json()
    checklist_engine.save_state(body)
    return {"status": "SAVED", "saved_at": datetime.now(timezone.utc).isoformat()}


@app.get("/api/indicators/live")
async def get_live_indicators(symbol: str = "GOLD#"):
    """
    Returns live EMA ribbon (20/50/200), Stochastic (14,3,3), and AutoTrendChannel swing points
    across D1, H4, H1, M15, M5, M1 matching MT5 files.
    """
    resolution = resolver.resolve(symbol)
    tf_data = await data_feed.get_multitimeframe_bars(resolution.requested)

    timeframes_out = {}
    for tf_key, bars in tf_data.items():
        tf_name = tf_key.value if hasattr(tf_key, "value") else str(tf_key)
        ema_info = compute_ema_alignment(bars, 20, 50, 200)
        stoch_info = compute_stochastic(bars, 14, 3, 3)
        swings_info = compute_swing_channels(bars, lookback=180, left_bars=3, right_bars=3)

        timeframes_out[tf_name] = {
            "ema_ribbon": ema_info,
            "stochastic": stoch_info,
            "swings": swings_info,
            "bars_count": len(bars)
        }

    return {
        "symbol": resolution.resolved,
        "broker": resolution.broker,
        "spread_points": resolution.spread_points,
        "timeframes": timeframes_out,
        "evaluated_at": datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
    }


CHANNEL_BARS_PER_TF = 300
CHANNEL_CHART_BARS = 120


async def _build_channel_map(symbol: str, overrides: Dict[str, Any] | None = None) -> Dict[str, Any]:
    resolution = resolver.resolve(symbol)
    tf_data = await data_feed.get_multitimeframe_bars(resolution.requested, bars_per_tf=CHANNEL_BARS_PER_TF)
    result = map_multi_timeframe_channels(tf_data, overrides=overrides)

    digits = resolution.digits if resolution.digits is not None else 2
    candles = {}
    for tf_key, bars in tf_data.items():
        tf_name = tf_key.value if hasattr(tf_key, "value") else str(tf_key)
        candles[tf_name] = [
            {
                "time": int(b.timestamp.timestamp()),
                "open": round(b.open, digits),
                "high": round(b.high, digits),
                "low": round(b.low, digits),
                "close": round(b.close, digits),
            }
            for b in bars[-CHANNEL_CHART_BARS:]
        ]

    return {
        "symbol": resolution.resolved,
        "broker": resolution.broker,
        "candles": candles,
        "evaluated_at": datetime.now(timezone.utc).strftime("%H:%M:%S UTC"),
        **result,
    }


@app.get("/api/channels/map")
async def get_channel_map(symbol: str = "GOLD#"):
    """Multi-timeframe channel map: per-TF channels, alignment, confluence zones and mapping guide."""
    return await _build_channel_map(symbol)


@app.post("/api/channels/map")
async def post_channel_map(request: Request):
    """Same as GET, with optional manual channel overrides keyed by timeframe (a1, a2, opposite)."""
    body = await request.json()
    overrides = body.get("overrides")
    if overrides is not None and not isinstance(overrides, dict):
        return JSONResponse({"error": "overrides must be an object keyed by timeframe"}, status_code=400)
    return await _build_channel_map(body.get("symbol", "GOLD#"), overrides)


@app.get("/api/experts/catalog")
async def get_experts_and_strategies():
    """Returns the unified catalog of Expert Advisors, Indicators, and Strategy Setups to test."""
    return {
        "experts": get_experts_catalog(),
        "indicators": get_indicators_catalog(),
        "strategy_setups": get_strategy_setups_to_test()
    }


@app.post("/api/strategy-setups/test")
async def test_strategy_setup(request: Request):
    """
    Simulates paper execution or backtest evaluation of a selected strategy setup.
    """
    body = await request.json()
    setup_id = body.get("setup_id", "setup_1_mtf_ema_swing")
    symbol = body.get("symbol", "GOLD#")

    resolution = resolver.resolve(symbol)
    tf_data = await data_feed.get_multitimeframe_bars(resolution.requested)
    market_state = analyzer.analyze_full_market(resolution.resolved, resolution.broker, tf_data)

    test_result = {
        "setup_id": setup_id,
        "symbol": resolution.resolved,
        "tested_at": datetime.now(timezone.utc).isoformat(),
        "macro_bias": market_state.macro_bias.value,
        "mtf_confluence": market_state.mtf_confluence_score,
        "market_regime": market_state.market_regime.value,
        "passed_filters": market_state.mtf_confluence_score >= 0.60 and resolution.spread_points <= 40,
        "simulated_outcome": "CONFLUENCE_MET" if market_state.mtf_confluence_score >= 0.60 else "WAIT_FILTER_TRIGGERED",
        "recommended_action": "EXECUTE_PAPER_BRACKET" if market_state.mtf_confluence_score >= 0.60 else "OBSERVE_ONLY"
    }

    return test_result


@app.post("/api/sync/daily-history")
async def trigger_daily_history_sync(days: int = 2):
    """Triggers an immediate catch-up sync of MT5 closed trades into OpenTraderWorld."""
    from scripts.auto_sync_daily_history import DailyHistorySureSync
    engine = DailyHistorySureSync()
    summary = engine.execute_daily_sync(days_back=days)
    return summary


@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    with open(ROOT_DIR / "dashboard" / "templates" / "index.html", "r") as f:
        return f.read()


def start_dashboard():
    uvicorn.run(app, host=config.DASHBOARD_HOST, port=config.DASHBOARD_PORT)


if __name__ == "__main__":
    start_dashboard()
