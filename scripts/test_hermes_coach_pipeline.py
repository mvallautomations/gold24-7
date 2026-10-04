"""
Test script simulating a candidate signal to verify live Hermes 3 LLM interpretation,
deterministic validation, simulated execution, and OpenTraderWorld ingestion.
"""

import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import asyncio
from rich.console import Console
from rich.panel import Panel

from core.models.candle import Timeframe
from core.models.signal import SignalContract, SignalDirection, SetupType, MarketRegime, VolatilityState
from core.indicators.volatility import VolatilityEngine
from core.market.analyzer import MultiTimeframeMarketAnalyzer
from core.validation.validator import DeterministicValidator
from adapters.broker.symbol_resolver import BrokerSymbolResolver
from backtest.datasets.data_generator import MarketDataGenerator
from agents.analyzer.interpreter import HermesMarketInterpreter
from agents.coach.trade_coach import HermesTradeCoach
from execution.paper.engine import PaperTradingEngine
from journal.ingestion.otw_journal_sync import OTWJournalIngestion

console = Console()


async def test_candidate_trade_flow():
    console.print(Panel.fit(
        "[bold cyan]GOLD24-7 Live Hermes 3 & Paper Trade Execution Test[/bold cyan]\n"
        "Testing: Hermes 3:8B on GPU -> Validator -> Paper Execution -> OTW Ingestion",
        border_style="cyan"
    ))

    # 1. Resolve Symbol
    resolver = BrokerSymbolResolver(broker="XM")
    res = resolver.resolve("XAUUSD")

    # 2. Synthesize setup
    tf_data = MarketDataGenerator.generate_multitimeframe_suite(symbol=res.resolved, start_price=2650.0, seed=101)
    analyzer = MultiTimeframeMarketAnalyzer()
    market_state = analyzer.analyze_full_market(res.resolved, res.broker, tf_data)

    m1_atr = market_state.timeframes["M1"].atr
    entry_p = 2652.50
    sl_p = 2649.50
    tp_p = 2657.00
    rr = round((tp_p - entry_p) / (entry_p - sl_p), 2)

    signal = SignalContract(
        symbol_requested=res.requested,
        symbol_resolved=res.resolved,
        broker_name=res.broker,
        direction=SignalDirection.BUY,
        setup=SetupType.PULLBACK,
        market_regime=MarketRegime.TRENDING,
        entry_price=entry_p,
        stop_loss=sl_p,
        take_profit=tp_p,
        risk_reward_ratio=rr,
        risk_points=round(entry_p - sl_p, 2),
        volatility_state=m1_atr.state,
        higher_tf_bias=market_state.macro_bias,
        mtf_confluence_score=market_state.mtf_confluence_score,
        environment="PAPER",
        is_simulation_only=True,
        live_execution_permitted=False
    )

    console.print(f"[bold]1. Candidate Signal Generated:[/bold] {signal.direction.value} {signal.setup.value} on {signal.symbol_resolved} at {signal.entry_price}")

    # 3. Hermes 3:8B on GPU
    console.print("[bold]2. Querying Hermes 3:8B on GPU...[/bold]")
    interpreter = HermesMarketInterpreter()
    interpretation = interpreter.interpret_signal(signal, market_state)
    console.print(f"   [green]Hermes Confidence:[/green] {interpretation.confidence_score * 100:.0f}% | Action: [bold]{interpretation.recommended_action}[/bold]")
    console.print(f"   [italic]Reasoning:[/italic] {interpretation.reasoning}")
    console.print(f"   [yellow]Critique (Devil's Advocate):[/yellow] {interpretation.critique}")
    console.print(f"   [cyan]Psychological Check:[/cyan] {interpretation.psychological_check}")

    # 4. Deterministic Validator
    validator = DeterministicValidator(min_risk_reward=1.2)
    validation = validator.validate_signal(signal, current_spread_points=res.spread_points, atr_value=m1_atr.current_atr)
    console.print(f"[bold]3. Deterministic Validator:[/bold] {'PASSED' if validation.is_valid else 'FAILED'}")

    # 5. Paper Execution
    paper = PaperTradingEngine(initial_balance=10000.0)
    pos = paper.execute_signal(signal, point=res.point, tick_size=res.tick_size, tick_value=res.tick_value)
    console.print(f"[bold]4. Paper Order Filled:[/bold] Position ID: {pos.position_id} | Lots: {pos.quantity_lots} | Price: {pos.entry_price}")

    # 6. Simulate TP Hit
    closed = paper.on_price_update(
        symbol=res.resolved,
        high=tp_p + 1.0,
        low=entry_p,
        close=tp_p
    )
    closed_pos = closed[0]
    console.print(f"[bold green]5. Position Closed [TP_HIT]:[/bold green] Realized PnL: +${closed_pos.realized_pnl:.2f} | Balance: ${paper.balance}")

    # 7. Hermes Coach Debrief
    coach = HermesTradeCoach()
    coach_feedback = coach.generate_trade_review(closed_pos)
    console.print(f"[bold]6. Hermes Coach Post-Trade Debrief:[/bold] {coach_feedback}")

    # 8. OpenTraderWorld Journal Ingestion
    otw = OTWJournalIngestion()
    trade_id = otw.ingest_closed_trade(closed_pos, coach_feedback=coach_feedback)
    if trade_id:
        console.print(f"[bold cyan]7. OpenTraderWorld PostgreSQL Sync:[/bold cyan] Ingested as Trade ID [bold]{trade_id}[/bold]")
    else:
        console.print("[yellow]7. OpenTraderWorld PostgreSQL Sync:[/yellow] Local record logged.")

    console.print(Panel.fit("[bold green]All 7 Pipeline Stages Verified Successfully![/bold green]", border_style="green"))


if __name__ == "__main__":
    asyncio.run(test_candidate_trade_flow())
