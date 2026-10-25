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
        symbol: str = "GOLD#",
        broker: str = "XM",
        interval_seconds: int = 10,
        enable_hermes: bool = True,
        live_execution: bool = False,
        profit_target: float = 100.0,
        circuit_breaker: float = 70.0,
        lot_size: float = 0.01
    ):
        self.symbol = symbol
        self.broker = broker
        self.interval_seconds = interval_seconds
        self.enable_hermes = enable_hermes
        self.live_execution = live_execution
        self.profit_target = profit_target
        self.circuit_breaker = circuit_breaker
        self.lot_size = lot_size
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
        mode_str = "[bold red]LIVE XM MT5 ACCOUNT[/bold red]" if self.live_execution else "[yellow]PAPER SIMULATION[/yellow]"

        console.print(Panel.fit(
            f"[bold gold1]GOLD24-7 Autonomous Trading Daemon[/bold gold1]\n"
            f"Mode: {mode_str} | Broker: [cyan]{resolution.broker}[/cyan] | Symbol: [green]{resolution.resolved}[/green]\n"
            f"Target Balance: [bold green]${self.profit_target:.2f}[/bold green] | Circuit Breaker: [bold red]${self.circuit_breaker:.2f}[/bold red] | Lot: [bold]{self.lot_size}[/bold]\n"
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

        # 1. Fetch live account statistics & verify profit target
        acc_stats = self.mt5_syncer.get_account_stats()
        balance = acc_stats.get("balance", 0.0)
        equity = acc_stats.get("equity", 0.0)
        open_positions = self.mt5_syncer.get_live_positions_formatted()

        acc_login = acc_stats.get("account_login", "336888981")
        console.print(f"Account {acc_login}: Balance=[bold green]${balance:.2f}[/bold green] | Equity=[bold]${equity:.2f}[/bold] | Open Trades=[bold]{len(open_positions)}[/bold]")

        # Check target profit halt
        if self.live_execution and balance >= self.profit_target and len(open_positions) == 0:
            console.print(Panel.fit(
                f"[bold green]🏆 PROFIT GOAL ACHIEVED![/bold green]\n"
                f"Account Balance (${balance:.2f}) reached or exceeded target (${self.profit_target:.2f}).\n"
                f"Autonomous trading halted safely to preserve clean profits.",
                border_style="green"
            ))
            self.stop()
            return

        # Check circuit breaker halt
        if self.live_execution and balance < self.circuit_breaker and len(open_positions) == 0:
            console.print(Panel.fit(
                f"[bold red]🚨 CIRCUIT BREAKER HIT![/bold red]\n"
                f"Account Balance (${balance:.2f}) dropped below safety limit (${self.circuit_breaker:.2f}).\n"
                f"Trading halted immediately to protect capital.",
                border_style="red"
            ))
            self.stop()
            return

        # 2. Strict Single-Position Guard: If already in a live trade, monitor only
        if len(open_positions) > 0:
            p = open_positions[0]
            floating_pnl = float(p.get("unrealized_pnl", p.get("profit", 0.0)))
            pnl_color = "bold green" if floating_pnl >= 0 else "bold red"
            console.print(
                f"[bold yellow]Active Live Position:[/bold yellow] Ticket #{p.get('ticket')} | "
                f"{p.get('side')} {p.get('lots', 0.01)} lots @ {p.get('entry_price')} | "
                f"Current: {p.get('current_price')} | Floating PnL: [{pnl_color}]${floating_pnl:.2f}[/{pnl_color}]"
            )
            console.print("[dim]Strict 1-trade limit active. Monitoring open trade until SL/TP exit.[/dim]")
            return

        # 3. Fetch multi-timeframe candles from XM MT5 / generator
        tf_data = await self.data_feed.get_multitimeframe_bars(resolution.requested)
        if not tf_data or Timeframe.M1 not in tf_data:
            console.print("[red]Unable to fetch market candles for current cycle.[/red]")
            return

        # 4. Analyze state & volatility
        market_state = self.analyzer.analyze_full_market(resolution.resolved, resolution.broker, tf_data)
        m1_atr = market_state.timeframes["M1"].atr

        console.print(
            f"Bias: Macro=[cyan]{market_state.macro_bias.value}[/cyan] Exec=[cyan]{market_state.execution_bias.value}[/cyan] | "
            f"Confluence=[green]{market_state.mtf_confluence_score * 100:.0f}%[/green] | ATR=[magenta]{m1_atr.state.value}[/magenta] ({m1_atr.percentile}%)"
        )

        # 5. Evaluate setup
        signal = self.evaluator.evaluate(market_state)
        if signal.direction == SignalDirection.NONE:
            console.print("[dim]No entry trigger on current completed bar (WATCH state).[/dim]")
            return

        console.print(
            f"[bold]Detected Setup:[/bold] [yellow]{signal.setup.value}[/yellow] "
            f"Direction=[{'green' if signal.direction == SignalDirection.BUY else 'red'}]{signal.direction.value}[/] "
            f"@ {signal.entry_price:.2f} (SL: {signal.stop_loss:.2f}, TP: {signal.take_profit:.2f})"
        )

        # 6. Deterministic 10-Point Mathematical Risk Gate
        validation = self.validator.validate_signal(
            signal=signal,
            current_spread_points=resolution.spread_points,
            atr_value=m1_atr.current_atr,
            has_open_position=len(open_positions) > 0
        )

        if not validation.is_valid:
            console.print(f"[red]Signal rejected by Deterministic Validator:[/red] {validation.rejection_reason}")
            return

        console.print("[bold green]Deterministic Validator: PASSED all risk constraints.[/bold green]")

        # 7. Hermes 3:8B Qualitative Critique
        hermes_critique = ""
        if self.enable_hermes and self.interpreter:
            console.print("[italic]Consulting Hermes 3:8B LLM on GPU...[/italic]")
            interpretation = self.interpreter.interpret_signal(
                signal, market_state, open_positions=open_positions, account_stats=acc_stats
            )
            hermes_critique = f"Critique: {interpretation.critique} | Confidence: {interpretation.confidence_score * 100:.0f}%"
            console.print(f"[bold]Hermes Action:[/bold] {interpretation.recommended_action} ({hermes_critique})")
            if interpretation.recommended_action in ["STAND_ASIDE", "PROTECT_CAPITAL"]:
                console.print(f"[yellow]Hermes recommended {interpretation.recommended_action}. Standing aside.[/yellow]")
                return

        # 8. Execution
        if self.live_execution:
            # Live Order Execution via XM MT5 Bridge Server
            import httpx
            bridge_url = "http://172.26.144.1:8082/rpc"
            try:
                # Fresh tick quote
                tick_res = httpx.post(bridge_url, json={"jsonrpc": "2.0", "method": "tick_get", "params": {"symbol": resolution.resolved}, "id": 1}, timeout=5.0).json()
                tick = tick_res.get("result", {})
                if not tick or not tick.get("ask"):
                    console.print("[red]Failed to get fresh tick quote from MT5 bridge.[/red]")
                    return

                is_buy = signal.direction == SignalDirection.BUY
                order_price = tick["ask"] if is_buy else tick["bid"]
                # Safe tight SL / TP calculation (3-4 points on Gold)
                sl_distance = max(2.5, min(5.0, abs(signal.entry_price - signal.stop_loss)))
                tp_distance = max(2.5, min(6.0, abs(signal.take_profit - signal.entry_price)))

                sl_price = round(order_price - sl_distance if is_buy else order_price + sl_distance, 2)
                tp_price = round(order_price + tp_distance if is_buy else order_price - tp_distance, 2)

                order_request = {
                    "action": 1,  # TRADE_ACTION_DEAL
                    "symbol": resolution.resolved,
                    "volume": float(self.lot_size),
                    "type": 0 if is_buy else 1,
                    "price": float(order_price),
                    "sl": float(sl_price),
                    "tp": float(tp_price),
                    "deviation": 20,
                    "magic": 240702,
                    "comment": "GOLD24-7_AUTO",
                    "type_time": 0,
                    "type_filling": 1
                }

                console.print(f"[bold cyan]Submitting Live XM Order:[/bold cyan] {'BUY' if is_buy else 'SELL'} {self.lot_size} {resolution.resolved} @ {order_price} (SL: {sl_price}, TP: {tp_price})...")
                res = httpx.post(bridge_url, json={"jsonrpc": "2.0", "method": "order_send", "params": {"request": order_request}, "id": 2}, timeout=7.0).json()

                if "result" in res and res["result"].get("retcode") in (0, 10009):
                    deal = res["result"].get("deal", "N/A")
                    order = res["result"].get("order", "N/A")
                    console.print(Panel.fit(
                        f"[bold green]🚀 LIVE MT5 ORDER FILLED SUCCESSFULLY![/bold green]\n"
                        f"Order Ticket: [bold]{order}[/bold] | Deal Ticket: [bold]{deal}[/bold]\n"
                        f"Symbol: [bold]{resolution.resolved}[/bold] | Lots: [bold]{self.lot_size}[/bold]\n"
                        f"Entry: [bold]{order_price}[/bold] | SL: [bold red]{sl_price}[/bold red] | TP: [bold green]{tp_price}[/bold green]",
                        border_style="green"
                    ))
                else:
                    err = res.get("error", res.get("result", {}))
                    console.print(f"[bold red]Live order rejected by MT5:[/bold red] {err}")
            except Exception as e:
                console.print(f"[bold red]Exception placing live order:[/bold red] {e}")
        else:
            # Paper execution fallback
            position = self.paper_engine.execute_signal(
                signal,
                point=resolution.point,
                tick_size=resolution.tick_size,
                tick_value=resolution.tick_value
            )
            if position:
                console.print(f"[bold green]Opened Paper Position:[/bold green] {position.side.value.upper()} {position.quantity_lots} lots on {position.symbol}")

    def stop(self):
        self.is_running = False


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="GOLD24-7 Autonomous Trading Daemon")
    parser.add_argument("--symbol", default="GOLD", help="Symbol to monitor and trade (default: GOLD)")
    parser.add_argument("--live", action="store_true", help="Enable live execution on MT5 account (336888981)")
    parser.add_argument("--target", type=float, default=2500.0, help="Profit target balance to auto-halt trading (default: 2500.0)")
    parser.add_argument("--circuit-breaker", type=float, default=1500.0, help="Circuit breaker minimum balance (default: 1500.0)")
    parser.add_argument("--interval", type=int, default=10, help="Evaluation interval in seconds (default: 10)")
    args = parser.parse_args()

    daemon = AutonomousTradingDaemon(
        symbol=args.symbol,
        broker="XM",
        interval_seconds=args.interval,
        enable_hermes=True,
        live_execution=args.live,
        profit_target=args.target,
        circuit_breaker=args.circuit_breaker,
        lot_size=0.01
    )

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
