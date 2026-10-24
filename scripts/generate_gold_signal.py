"""
Standalone script to generate a live Hermes 3:8B signal for GOLD / GOLD#
using live multi-timeframe MT5 market data.
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
import json
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from adapters.mcp.client import MT5MCPClient
from adapters.mt5.data_feed import MT5DataFeed
from adapters.broker.symbol_resolver import BrokerSymbolResolver
from core.market.analyzer import MultiTimeframeMarketAnalyzer
from agents.analyzer.interpreter import HermesMarketInterpreter
from core.models.signal import SignalContract

console = Console()


async def generate_signal(symbol: str = "GOLD#"):
    console.print(Panel(f"[bold gold1]HERMES 3:8B LIVE SIGNAL GENERATOR[/bold gold1]\nTarget Instrument: [bold cyan]{symbol}[/bold cyan]", border_style="gold1"))

    client = MT5MCPClient()
    resolver = BrokerSymbolResolver(broker="XM")
    feed = MT5DataFeed(mcp_client=client, resolver=resolver)
    analyzer = MultiTimeframeMarketAnalyzer()
    interpreter = HermesMarketInterpreter()

    res = resolver.resolve(symbol)
    console.print(f"[dim]Symbol Resolution:[/dim] [green]{res.requested}[/green] -> [bold cyan]{res.resolved}[/bold cyan] ({res.broker})")

    tf_data = await feed.get_multitimeframe_bars(res.requested)
    state = analyzer.analyze_full_market(res.resolved, res.broker, tf_data)

    m1_close = state.timeframes["M1"].forming_bar.close if state.timeframes["M1"].forming_bar else state.timeframes["M1"].completed_bar.close
    console.print(f"[dim]Live Market Data:[/dim] Price=[bold green]${m1_close:,.2f}[/bold green] | Macro Bias=[bold]{state.macro_bias.value}[/bold] | Regime=[bold]{state.market_regime.value}[/bold]")

    console.print("[yellow]Prompting Hermes 3:8B on GPU via Ollama for quantitative trade thesis...[/yellow]")
    signal: SignalContract = interpreter.generate_hermes_signal(state, res)

    table = Table(title=f"Hermes 3:8B Trade Signal: {signal.symbol_requested} ({signal.symbol_resolved})", border_style="cyan")
    table.add_column("Parameter", style="cyan", no_wrap=True)
    table.add_column("Value", style="bold white")

    dir_style = "bold green" if signal.direction.value == "BUY" else "bold red"
    table.add_row("Direction", f"[{dir_style}]{signal.direction.value}[/{dir_style}]")
    table.add_row("Setup Type", signal.setup.value)
    table.add_row("Entry Price", f"${signal.entry_price:,.2f}")
    table.add_row("Stop Loss", f"${signal.stop_loss:,.2f} ({signal.risk_points:,.2f} pts risk)")
    table.add_row("Take Profit", f"${signal.take_profit:,.2f} (R:R {signal.risk_reward_ratio:.2f})")
    table.add_row("Confidence", f"{signal.llm_interpretation.confidence_score * 100:.0f}%")
    table.add_row("Reasoning", signal.llm_interpretation.reasoning)
    table.add_row("Risk Critique", signal.llm_interpretation.critique)
    table.add_row("Discipline Check", signal.llm_interpretation.psychological_check)

    console.print(table)
    return signal


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "GOLD#"
    asyncio.run(generate_signal(target))
