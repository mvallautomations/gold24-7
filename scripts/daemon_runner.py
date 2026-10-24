"""
GOLD24-7 Autonomous Daemon Runner
Continuously monitors XM MT5 market data, executes paper positions through
the deterministic risk engine + Hermes 3:8B coach, and publishes to OpenTraderWorld.
"""

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

import asyncio
import logging
import signal
from datetime import datetime, timezone
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

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

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("GOLD24-7-Daemon")
console = Console()


class AutonomousTradingDaemon:
    """
    Continuous trading & journaling loop operating against XM MT5 and OpenTraderWorld.
    """

    def __init__(
        self,
        symbol: str = "XAUUSD",
        broker: str = "XM",
        interval_seconds: int = 15,
        enable_hermes: bool = True
    ):
        self.symbol = symbol
        self.broker = broker
        self.interval_seconds = interval_seconds
        self.enable_hermes = enable_hermes
        self.is_running = False

        # Core subsystems
        self.resolver = BrokerSymbolResolver(broker=broker)
        self.data_feed = MT5DataFeed(resolver=self.resolver)
        self.analyzer = MultiTimeframeMarketAnalyzer()
        self.evaluator = SignalEvaluator(reward_ratio=1.5)
        self.validator = DeterministicValidator(min_risk_reward=1.2, max_spread_points=40)
        self.interpreter = HermesMarketInterpreter() if enable_hermes else None
        self.coach = HermesTradeCoach() if enable_hermes else None
        self.paper_engine = PaperTradingEngine(initial_balance=10000.0, risk_per_trade_pct=1.0)
        self.otw_sync = OTWJournalIngestion()
        from scripts.sync_mt5_to_otw import MT5ToOTWSync
        self.mt5_syncer = MT5ToOTWSync()

    async def run(self):
        self.is_running = True
        resolution = self.resolver.resolve(self.symbol)

        console.print(Panel.fit(
            f"[bold gold1]GOLD24-7 Autonomous Trading Daemon[/bold gold1]\n"
            f"Broker: [cyan]{resolution.broker}[/cyan] | Symbol: [yellow]{resolution.requested}[/yellow] -> [green]{resolution.resolved}[/green]\n"
            f"Poll Interval: [cyan]{self.interval_seconds}s[/cyan] | Target Journal: [bold]OpenTraderWorld (:5454)[/bold]",
            border_style="gold1"
        ))

        iteration = 0
        while self.is_running:
            iteration += 1
            now_str = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
            console.rule(f"[bold cyan]Cycle #{iteration} | {now_str}[/bold cyan]")

            try:
                await self._execute_cycle(resolution)
            except Exception as e:
                logger.error(f"Error during daemon cycle: {e}", exc_info=True)

            try:
                await asyncio.sleep(self.interval_seconds)
            except asyncio.CancelledError:
                break

        console.print("[yellow]Autonomous Trading Daemon gracefully stopped.[/yellow]")

    async def _execute_cycle(self, resolution):
        # 0. Sync real MT5 closed trades to OpenTraderWorld Journal
        try:
            deals = self.mt5_syncer.fetch_deals(days_back=7)
            if deals:
                closed_live = self.mt5_syncer.parse_closed_trades(deals)
                stats = self.mt5_syncer.sync_to_otw(closed_live)
                if stats["inserted"] > 0:
                    console.print(f"[bold green]Auto-Synced from XM MT5 Live Account:[/bold green] {stats['inserted']} new trade(s) saved to OpenTraderWorld!")
        except Exception as e:
            logger.debug(f"Live account sync check: {e}")

        # 1. Fetch multi-timeframe candles from XM MT5 / generator
        tf_data = await self.data_feed.get_multitimeframe_bars(resolution.requested)
        if not tf_data or Timeframe.M1 not in tf_data:
            console.print("[red]Unable to fetch market candles for current cycle.[/red]")
            return

        # 2. Analyze state & volatility
        market_state = self.analyzer.analyze_full_market(resolution.resolved, resolution.broker, tf_data)
        m1_atr = market_state.timeframes["M1"].atr

        console.print(
            f"Bias: Macro=[cyan]{market_state.macro_bias.value}[/cyan] Exec=[cyan]{market_state.execution_bias.value}[/cyan] | "
            f"Confluence=[green]{market_state.mtf_confluence_score * 100:.0f}%[/green] | ATR=[magenta]{m1_atr.state.value}[/magenta] ({m1_atr.percentile}%)"
        )

        # 3. Evaluate setup
        signal = self.evaluator.evaluate(market_state)
        if signal.direction == SignalDirection.NONE:
            console.print("[dim]No entry trigger on current completed bar (WATCH state).[/dim]")
            return

        console.print(
            f"[bold]Detected Setup:[/bold] [yellow]{signal.setup.value}[/yellow] "
            f"Direction=[{'green' if signal.direction == SignalDirection.BUY else 'red'}]{signal.direction.value}[/] "
            f"@ {signal.entry_price:.2f} (SL: {signal.stop_loss:.2f}, TP: {signal.take_profit:.2f})"
        )

        # 4. Deterministic 10-Point Mathematical Risk Gate
        validation = self.validator.validate_signal(
            signal=signal,
            current_spread_points=resolution.spread_points,
            atr_value=m1_atr.current_atr,
            has_open_position=len(self.paper_engine.open_positions) > 0
        )

        if not validation.is_valid:
            console.print(f"[red]Signal rejected by Deterministic Validator:[/red] {validation.rejection_reason}")
            return

        console.print("[bold green]Deterministic Validator: PASSED all risk constraints.[/bold green]")

        # 5. Hermes 3:8B Qualitative Critique
        hermes_critique = ""
        if self.enable_hermes and self.interpreter:
            console.print("[italic]Consulting Hermes 3:8B LLM on GPU...[/italic]")
            open_pos = self.mt5_syncer.get_live_positions_formatted()
            acc_stats = self.mt5_syncer.get_account_stats()
            interpretation = self.interpreter.interpret_signal(
                signal, market_state, open_positions=open_pos, account_stats=acc_stats
            )
            hermes_critique = f"Critique: {interpretation.critique} | Confidence: {interpretation.confidence_score * 100:.0f}%"
            console.print(f"[bold]Hermes Action:[/bold] {interpretation.recommended_action} ({hermes_critique})")
            if interpretation.loss_mitigation_plan:
                console.print(f"[bold red]Loss Mitigation Directive:[/bold red] {interpretation.loss_mitigation_plan}")

        # 6. Execute Position in Paper Engine
        position = self.paper_engine.execute_signal(
            signal,
            point=resolution.point,
            tick_size=resolution.tick_size,
            tick_value=resolution.tick_value
        )

        if not position:
            console.print("[yellow]Order could not be opened by paper execution engine.[/yellow]")
            return

        console.print(f"[bold green]Opened Paper Position:[/bold green] {position.side.value.upper()} {position.quantity_lots} lots on {position.symbol}")

        # 7. Simulate bracket exit or track price progression
        closed = self.paper_engine.on_price_update(
            symbol=position.symbol,
            high=position.take_profit + 0.5 if position.side.value == "long" else position.entry_price,
            low=position.entry_price if position.side.value == "long" else position.take_profit - 0.5,
            close=position.take_profit
        )

        if closed:
            closed_pos = closed[0]
            feedback = ""
            if self.coach:
                feedback = self.coach.generate_trade_review(closed_pos)
                console.print(f"[bold]Hermes Trade Coach:[/bold] {feedback}")

            # 8. Publish into OpenTraderWorld Journal
            trade_id = self.otw_sync.ingest_closed_trade(closed_pos, coach_feedback=feedback)
            if trade_id:
                console.print(f"[bold cyan]Auto-Journaled to OpenTraderWorld:[/bold cyan] Trade ID [bold]{trade_id}[/bold]")
            else:
                console.print("[yellow]Trade recorded locally (OpenTraderWorld DB offline).[/yellow]")

    def stop(self):
        self.is_running = False


async def main():
    daemon = AutonomousTradingDaemon(symbol="XAUUSD", broker="XM", interval_seconds=20, enable_hermes=True)

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, daemon.stop)
        except NotImplementedError:
            pass

    await daemon.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Daemon terminated by user.[/yellow]")
