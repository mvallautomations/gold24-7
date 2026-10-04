import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

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

app = FastAPI(title="GOLD24-7 Research & Paper-Trading Dashboard")

resolver = BrokerSymbolResolver(broker="XM")
data_feed = MT5DataFeed(resolver=resolver)
analyzer = MultiTimeframeMarketAnalyzer()
evaluator = SignalEvaluator(reward_ratio=1.5)
validator = DeterministicValidator(min_risk_reward=1.2)
paper_engine = PaperTradingEngine(initial_balance=10000.0)
interpreter = HermesMarketInterpreter()

latest_state: Dict[str, Any] = {}


@app.get("/api/status")
async def get_status():
    return {
        "status": "ONLINE",
        "environment": "PAPER",
        "is_simulation_only": True,
        "live_execution_permitted": False,
        "broker": resolver.broker,
        "balance": paper_engine.balance,
        "equity": paper_engine.equity,
        "open_positions": len(paper_engine.open_positions),
        "closed_positions": len(paper_engine.closed_positions),
    }


@app.get("/api/evaluate")
async def evaluate_market(symbol: str = "XAUUSD"):
    resolution = resolver.resolve(symbol)
    tf_data = await data_feed.get_multitimeframe_bars(resolution.requested)
    market_state = analyzer.analyze_full_market(resolution.resolved, resolution.broker, tf_data)

    signal = evaluator.evaluate(market_state)

    interpretation = None
    if signal.direction.value != "NONE":
        interpretation = interpreter.interpret_signal(signal, market_state)

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


@app.get("/api/backtest")
async def run_backtest(symbol: str = "XAUUSD"):
    resolution = resolver.resolve(symbol)
    tf_data = await data_feed.get_multitimeframe_bars(resolution.requested)
    sim = BacktestSimulator(initial_balance=10000.0)
    result = sim.run_backtest(resolution.resolved, resolution.broker, tf_data, warmup_bars=40)
    return result


@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    with open("/home/vall/m-2nd-brain/code/gold24-7/dashboard/templates/index.html", "r") as f:
        return f.read()


def start_dashboard():
    uvicorn.run(app, host=config.DASHBOARD_HOST, port=config.DASHBOARD_PORT)


if __name__ == "__main__":
    start_dashboard()
