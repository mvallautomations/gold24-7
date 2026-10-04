# GOLD24-7: MT5 + MCP + Hermes 3:8B + OpenTraderWorld Research & Paper-Trading Platform

> **Hard Safety Boundary**: This system is strictly authorized for **research, education, backtesting, and paper trading**. Live order execution is permanently disabled at the code and architectural level.

---

## 1. System Architecture

```text
                 ┌─────────────────────┐
                 │     MetaTrader 5    │
                 │     Market Data     │
                 └──────────┬──────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │      MT5 MCP        │
                 │ data / charts /     │
                 │ account metadata    │
                 └──────────┬──────────┘
                            │
                            ▼
              ┌──────────────────────────┐
              │   MARKET ANALYZER        │
              │ deterministic indicators │
              │ trend / S&R / ATR / etc. │
              └────────────┬─────────────┘
                           │
                           ▼
              ┌──────────────────────────┐
              │   SIGNAL EVALUATOR       │
              │ deterministic rules      │
              │ + setup classification   │
              └────────────┬─────────────┘
                           │
                           ▼
              ┌──────────────────────────┐
              │       HERMES 3:8B        │
              │ interpretation / coach   │
              │ explanation / critique   │
              └────────────┬─────────────┘
                           │
                           ▼
              ┌──────────────────────────┐
              │ DETERMINISTIC VALIDATOR  │
              │ final rule validation    │
              └────────────┬─────────────┘
                           │
                ┌──────────┴───────────┐
                │                      │
                ▼                      ▼
        ┌───────────────┐      ┌────────────────┐
        │ PAPER ENGINE  │      │    NO TRADE    │
        │ simulation    │      │ / WATCH STATE  │
        └───────┬───────┘      └────────────────┘
                │
                ▼
        ┌─────────────────┐
        │ TRADING JOURNAL │
        │ OpenTraderWorld │
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │ PERFORMANCE     │
        │ ENGINE          │
        │ metrics/errors  │
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │ DASHBOARD       │
        │ research UI     │
        └─────────────────┘
```

### Core Architectural Principle
> **The LLM interprets. Deterministic code calculates and validates.**
> Hermes 3:8B is utilized for qualitative pattern commentary, devil's advocate risk analysis, and cognitive bias coaching. Hermes never computes raw numerical price levels and has zero access to order dispatch routines.

---

## 2. Directory Structure

```text
gold24-7/
├── core/
│   ├── models/            # Bar, Timeframe, SRZone, ATRAssessment, SignalContract, PaperTrade
│   ├── indicators/        # Relative ATR VolatilityEngine, SR candidate zones, EMAs, RSI
│   ├── market/            # MultiTimeframeMarketAnalyzer (D1, H4, H1, M15, M5, M1)
│   ├── signals/           # SignalEvaluator (Symmetrical Pullback, Breakout, Reversal)
│   ├── validation/        # DeterministicValidator (10-point hard mathematical risk gate)
│   ├── configuration/     # AppConfig & environment settings
│   ├── M1_Pullback_Baseline_EA.mq5    # Documented baseline heuristic (NN_Crypto_Scalper)
│   └── M1_Pullback_Benchmark_EA.mq5   # Production-grade symmetrical benchmark EA
│
├── adapters/
│   ├── mt5/               # Multi-timeframe rate feed
│   ├── mcp/               # MT5 MCP JSON-RPC/SSE bridge client
│   ├── broker/            # BrokerSymbolResolver (XAUUSD -> GAUUSD / broker alias resolver)
│   └── journal/           # OpenTraderWorld direct PostgreSQL & API ingestion
│
├── agents/
│   ├── hermes/            # Ollama client connecting to Hermes 3:8B on GPU
│   ├── analyzer/          # HermesMarketInterpreter (risk critique & confidence score)
│   └── coach/             # HermesTradeCoach (post-trade journal debriefs)
│
├── execution/
│   ├── paper/             # PaperTradingEngine (simulated order book, lot sizing, slippage, PnL)
│   ├── safety/            # CircuitBreaker (daily drawdown limits, consecutive loss stop)
│   └── live_disabled/     # LiveBrokerAdapterDisabled (raises LiveExecutionForbiddenError)
│
├── backtest/
│   ├── engine/            # Bar-by-bar walk-forward historical simulator
│   ├── datasets/          # High-fidelity synthetic & historical multi-timeframe generator
│   ├── metrics/           # Performance metrics evaluator
│   └── walk_forward/      # Optimization windows
│
├── journal/
│   ├── schema/            # OpenTraderWorld database mappings
│   ├── ingestion/         # Direct PostgreSQL ingestion into journal_trades
│   └── analytics/         # PerformanceEngine (Sharpe, Profit Factor, Expectancy, Error analysis)
│
├── dashboard/             # FastAPI + Modern Glassmorphic Dark UI (Port 8585)
│   ├── server.py
│   └── templates/index.html
│
├── tests/
│   ├── unit/              # Indicator, resolver, validator, and paper engine unit tests
│   ├── contract/          # Canonical SignalContract JSON schema compliance tests
│   └── smoke/             # End-to-end full pipeline smoke tests
│
├── scripts/
│   ├── run_pipeline.py    # Master end-to-end pipeline execution CLI
│   ├── launch_dashboard.sh# Launch script for research web UI
│   └── test_hermes_coach_pipeline.py
│
├── docs/
│   └── BASELINE_EA_ANALYSIS.md # Detailed audit of baseline EA flaws & remedies
├── STATE.md
├── README.md
└── requirements.txt
```

---

## 3. Key Enhancements & Innovations

### 1. Broker Symbol Abstraction
* **No hardcoded `XAUUSD`**: Dynamically maps requested symbols (`XAUUSD`, `BTCUSD`, `ETHUSD`) to broker-specific symbols (e.g. `GAUUSD` or `GOLDmicro` on XM).
* Stores broker tick size, tick value, digits, and spread.

### 2. Multi-Timeframe Deterministic Market Analyzer
* Seamlessly evaluates **D1, H4, H1, M15, M5, and M1**.
* **Strict shift=1 enforcement**: Distinguishes `CURRENT_FORMING_BAR` (shift 0) from `COMPLETED_BAR` (shift 1), preventing false signals on unclosed ticks.
* Computes macro bias (D1/H4 consensus), execution bias (M15/M5), and mathematical confluence percentage.

### 3. Empirical Support / Resistance Candidate Zones
* Replaces naive single-price lines with candidate price clusters (`low`, `high`, `strength`, `touches`, `source`).
* Tracks multi-touch tests and recency weighting.

### 4. Relative ATR & Volatility State Engine
* Replaces faulty `ATR > 0` condition.
* Ranks current ATR against rolling historical distribution percentiles:
  * `< 15%`: `VERY_LOW` (flat chop, avoid scalping)
  * `15% - 35%`: `LOW`
  * `35% - 75%`: `NORMAL` (optimal trading regime)
  * `75% - 90%`: `HIGH`
  * `> 90%`: `EXTREME` (news spikes / gap hazard)
* Dynamically sizes stop-loss and take-profit distances via ATR multiples rather than arbitrary fixed points.

### 5. Symmetrical Benchmark EA (`M1_Pullback_Benchmark_EA.mq5`)
* Full **BUY and SELL symmetry**.
* Complete bar evaluation (`shift = 1` and `shift = 2`).
* Integrated relative ATR filter and dynamic ATR brackets.

### 6. OpenTraderWorld Journal Ingestion
* Automatically syncs executed paper positions and Hermes post-trade coaching debriefs into OpenTraderWorld's PostgreSQL database table `journal_trades`.

---

## 4. Quickstart Guide

### Activate Virtual Environment
```bash
cd code/gold24-7
source .venv/bin/activate
```

### Run Automated Test Suite
```bash
pytest
```
*14 tests passing across unit, contract, and smoke suites.*

### Run Master Pipeline CLI
```bash
python scripts/run_pipeline.py
```

### Launch Interactive Research Dashboard
```bash
./scripts/launch_dashboard.sh
```
*Open http://localhost:8585 in your browser to inspect live multi-timeframe charts, S/R zones, Hermes 3 commentary, and paper performance.*
