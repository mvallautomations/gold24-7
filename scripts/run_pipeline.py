import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import asyncio
import json
import logging
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from core.models.candle import Timeframe
from core.models.signal import SignalDirection
from core.market.analyzer import MultiTimeframeMarketAnalyzer
from core.signals.evaluator import SignalEvaluator
from core.validation.validator import DeterministicValidator
from adapters.broker.symbol_resolver import BrokerSymbolResolver
from adapters.mt5.data_feed import MT5DataFeed
from agents.analyzer.interpreter import HermesMarketInterpreter
from agents.coach.trade_coach import HermesTradeCoach
from execution.paper.engine import PaperTradingEngine
from journal.ingestion.otw_journal_sync import OTWJournalIngestion
from journal.analytics.performance_engine import PerformanceEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("GOLD24-7")
console = Console()


async def run_pipeline(
    requested_symbol: str = "XAUUSD",
    broker: str = "XM",
    run_hermes: bool = True
):
    console.print(Panel.fit(
        f"[bold gold1]GOLD24-7 Research & Paper-Trading Engine[/bold gold1]\n"
        f"Mode: [green]SIMULATION_ONLY (PAPER)[/green] | Requested: [cyan]{requested_symbol}[/cyan] | Broker: [cyan]{broker}[/cyan]",
        border_style="gold1"
    ))

    # 1. Broker Symbol Resolution
    resolver = BrokerSymbolResolver(broker=broker)
    resolution = resolver.resolve(requested_symbol)
    console.print(f"[bold]1. Symbol Resolver:[/bold] Requested [yellow]{resolution.requested}[/yellow] -> Resolved to [green]{resolution.resolved}[/green] ({resolution.broker}) [{resolution.status}]")

    # 2. MT5 Multi-Timeframe Data Feed
    data_feed = MT5DataFeed(resolver=resolver)
    tf_data = await data_feed.get_multitimeframe_bars(resolution.requested)
    console.print(f"[bold]2. Data Feed:[/bold] Loaded {len(tf_data)} timeframes ({', '.join([tf.value for tf in tf_data.keys()])})")

    # 3. Deterministic Market Analyzer
    analyzer = MultiTimeframeMarketAnalyzer()
    market_state = analyzer.analyze_full_market(resolution.resolved, broker, tf_data)

    m1_atr = market_state.timeframes["M1"].atr
    console.print(
        f"[bold]3. Deterministic Analyzer:[/bold] Macro: [cyan]{market_state.macro_bias.value}[/cyan] | "
        f"Execution: [cyan]{market_state.execution_bias.value}[/cyan] | Confluence: [cyan]{market_state.mtf_confluence_score * 100:.0f}%[/cyan] | "
        f"Regime: [cyan]{market_state.market_regime.value}[/cyan] | Volatility: [magenta]{m1_atr.state.value}[/magenta] (Rank: {m1_atr.percentile}%)"
    )

    # 4. Signal Evaluator (Deterministic Rules)
    evaluator = SignalEvaluator(reward_ratio=1.5)
    signal = evaluator.evaluate(market_state)
    console.print(
        f"[bold]4. Signal Evaluator:[/bold] Setup: [yellow]{signal.setup.value}[/yellow] | "
        f"Direction: [{'green' if signal.direction == SignalDirection.BUY else ('red' if signal.direction == SignalDirection.SELL else 'white')}]{signal.direction.value}[/] | "
        f"Entry: {signal.entry_price} | SL: {signal.stop_loss} | TP: {signal.take_profit}"
    )

    # 5. Hermes 3 Qualitative Interpretation & Devil's Advocate
    if run_hermes and signal.direction != SignalDirection.NONE:
        console.print("[bold]5. Hermes 3 LLM Interpreter:[/bold] Requesting critique from Hermes 3:8B on GPU...")
        interpreter = HermesMarketInterpreter()
        interpretation = interpreter.interpret_signal(signal, market_state)
        console.print(f"   [italic]Confidence:[/italic] {interpretation.confidence_score * 100:.0f}% | [italic]Action:[/italic] {interpretation.recommended_action}")
        console.print(f"   [italic]Reasoning:[/italic] {interpretation.reasoning}")
        console.print(f"   [italic]Critique (Devil's Advocate):[/italic] [yellow]{interpretation.critique}[/yellow]")
        console.print(f"   [italic]Psychological Check:[/italic] [cyan]{interpretation.psychological_check}[/cyan]")
    else:
        console.print("[bold]5. Hermes 3 LLM Interpreter:[/bold] Skipped (no candidate direction or offline mode)")

    # 6. Deterministic Validator (Mathematical Law)
    validator = DeterministicValidator(min_risk_reward=1.2, max_spread_points=40)
    validation = validator.validate_signal(
        signal=signal,
        current_spread_points=resolution.spread_points,
        atr_value=m1_atr.current_atr,
        has_open_position=False
    )

    val_color = "green" if validation.is_valid else "red"
    console.print(f"[bold]6. Deterministic Validator:[/bold] Verdict: [{val_color}]{'PASSED' if validation.is_valid else 'REJECTED'}[/{val_color}]")
    if not validation.is_valid:
        console.print(f"   [red]Reason: {validation.rejection_reason}[/red]")
    else:
        console.print(f"   [green]Passed Rules: {len(validation.passed_rules)} checks passed.[/green]")

    # 7. Paper Trading Execution
    paper_engine = PaperTradingEngine(initial_balance=10000.0, risk_per_trade_pct=1.0)
    otw_sync = OTWJournalIngestion()
    coach = HermesTradeCoach()

    if validation.is_valid and signal.direction != SignalDirection.NONE:
        position = paper_engine.execute_signal(
            signal,
            point=resolution.point,
            tick_size=resolution.tick_size,
            tick_value=resolution.tick_value
        )
        if position:
            console.print(f"[bold green]7. Paper Engine Executed:[/bold green] {position.side.value.upper()} {position.quantity_lots} lots on {position.symbol} at {position.entry_price}")

            # Simulate price progression to demonstrate TP/SL fill
            exit_bar = tf_data[Timeframe.M1][-1]
            closed = paper_engine.on_price_update(
                symbol=position.symbol,
                high=position.take_profit + 0.5 if position.side.value == "long" else position.entry_price,
                low=position.entry_price if position.side.value == "long" else position.take_profit - 0.5,
                close=position.take_profit
            )

            if closed:
                closed_pos = closed[0]
                feedback = coach.generate_trade_review(closed_pos)
                console.print(f"[bold]8. Hermes Coach Debrief:[/bold] {feedback}")

                trade_id = otw_sync.ingest_closed_trade(closed_pos, coach_feedback=feedback)
                if trade_id:
                    console.print(f"[bold cyan]9. OpenTraderWorld Journal:[/bold cyan] Ingested trade [bold]{trade_id}[/bold] into PostgreSQL ledger.")
                else:
                    console.print(f"[bold yellow]9. OpenTraderWorld Journal:[/bold yellow] Logged locally (Docker PostgreSQL connection pending).")
    else:
        console.print("[bold yellow]7. Paper Engine:[/bold yellow] No trade executed. State set to [bold]WATCH / NO TRADE[/bold].")

    # 10. Performance Engine Summary
    summary = paper_engine.get_summary()
    table = Table(title="GOLD24-7 Research Session Performance")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    for k, v in summary.items():
        table.add_row(k.replace("_", " ").title(), str(v))
    console.print(table)


if __name__ == "__main__":
    asyncio.run(run_pipeline())
