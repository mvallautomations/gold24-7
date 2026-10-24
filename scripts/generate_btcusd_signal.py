"""
BTCUSD# Quantitative Expert & Hermes 3:8B Signal Synthesizer
Directly connects to live XM MT5 via the Windows bridge, analyzes 24/7 crypto
market structure across 6 timeframes, and generates an institutional trade setup.
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


async def generate_btcusd_expert_signal(symbol: str = "BTCUSD#"):
    console.print(Panel(
        f"[bold orange1]HERMES 3:8B BITCOIN QUANTITATIVE EXPERT[/bold orange1]\n"
        f"Target Instrument: [bold cyan]{symbol}[/bold cyan] | Broker: [bold]XM Global MT5[/bold]\n"
        f"Market Schedule: [green]24/7 Crypto Continuous[/green]",
        border_style="orange1"
    ))

    client = MT5MCPClient()
    resolver = BrokerSymbolResolver(broker="XM")
    feed = MT5DataFeed(mcp_client=client, resolver=resolver)
    analyzer = MultiTimeframeMarketAnalyzer()
    interpreter = HermesMarketInterpreter()

    res = resolver.resolve(symbol)
    console.print(f"[dim]Symbol Resolution:[/dim] [green]{res.requested}[/green] -> [bold cyan]{res.resolved}[/bold cyan] (Broker: {res.broker}, Digits: {res.digits}, Point: {res.point})")

    tf_data = await feed.get_multitimeframe_bars(res.requested)
    state = analyzer.analyze_full_market(res.resolved, res.broker, tf_data)

    m1_bar = state.timeframes["M1"].forming_bar or state.timeframes["M1"].completed_bar
    m1_atr = state.timeframes["M1"].atr.current_atr
    console.print(
        f"[dim]Live Market Data:[/dim] Price=[bold green]${m1_bar.close:,.2f}[/bold green] | "
        f"M1 ATR=[bold]${m1_atr:,.2f}[/bold] | Macro Bias=[bold]{state.macro_bias.value}[/bold] | "
        f"Regime=[bold]{state.market_regime.value}[/bold]"
    )

    console.print("[yellow]Prompting Hermes 3:8B on GPU via Ollama for Bitcoin market analysis...[/yellow]")
    signal: SignalContract = interpreter.generate_hermes_signal(state, res)

    table = Table(
        title=f"Hermes 3:8B Bitcoin Signal: {signal.symbol_requested} ({signal.symbol_resolved})",
        border_style="orange1"
    )
    table.add_column("Parameter", style="cyan", no_wrap=True)
    table.add_column("Value", style="bold white")

    dir_style = "bold green" if signal.direction.value == "BUY" else "bold red"
    table.add_row("Direction", f"[{dir_style}]{signal.direction.value}[/{dir_style}]")
    table.add_row("Setup Type", signal.setup.value)
    table.add_row("Live Entry Price", f"${signal.entry_price:,.2f}")
    table.add_row("Stop Loss", f"${signal.stop_loss:,.2f} ({signal.risk_points:,.2f} pts risk)")
    table.add_row("Take Profit", f"${signal.take_profit:,.2f} (R:R {signal.risk_reward_ratio:.2f})")
    table.add_row("Confidence Score", f"{signal.llm_interpretation.confidence_score * 100:.0f}%")
    table.add_row("Trade Thesis", signal.llm_interpretation.reasoning)
    table.add_row("Risk Critique", signal.llm_interpretation.critique)
    table.add_row("Discipline Check", signal.llm_interpretation.psychological_check)

    console.print(table)
    return signal


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "BTCUSD#"
    asyncio.run(generate_btcusd_expert_signal(target))
