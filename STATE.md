# GOLD24-7 System State Tracker

## Current Phase
Phase 2: Full Architecture Implemented, Verified, & Deployed

## Current Branch
`main` (workspace tracking `origin/main`)

## Existing Working Components
1. **Core Data Models & Signal Contract**:
   - `core/models/`: `Bar`, `Timeframe`, `SRZone`, `ATRAssessment`, `SignalContract`, `PaperOrder`, `PaperPosition`.
   - Strict `shift=1` vs `shift=0` differentiation.
   - Frozen safety boundary: `environment: "PAPER"`, `is_simulation_only: true`, `live_execution_permitted: false`.
2. **Deterministic Indicator & Volatility Engine**:
   - `core/indicators/volatility.py`: `VolatilityEngine` calculating Relative ATR percentiles and categorical states (`VERY_LOW`, `LOW`, `NORMAL`, `HIGH`, `EXTREME`).
   - `core/indicators/zones.py`: `SupportResistanceEngine` identifying empirical candidate price zones with touch counts, strength scores, and ATR cluster envelopes.
   - `core/indicators/moving_averages.py`: EMA(9), EMA(21), RSI(14), and trend direction.
3. **Multi-Timeframe Market Analyzer**:
   - `core/market/analyzer.py`: Analyzes D1, H4, H1, M15, M5, and M1 timeframes simultaneously.
   - Computes macro bias (D1/H4), execution bias (M15/M5/M1), confluence score, and market regime.
4. **Deterministic Signal Evaluator**:
   - `core/signals/evaluator.py`: Classifies setups (`PULLBACK`, `BREAKOUT`, `REVERSAL`) with full long/short symmetry on completed bars (shift 1).
5. **Deterministic Validator (Mathematical Law)**:
   - `core/validation/validator.py`: 10-point hard mathematical risk audit (environment checks, spread envelope, volatility gating, R:R limits, SL/TP geometry, ATR multiplier bounds).
6. **Hermes 3:8B Integration (GPU-Accelerated)**:
   - `agents/hermes/`: Connects to local Ollama `hermes3:8b` running on CUDA RTX 4060 GPU.
   - `agents/analyzer/interpreter.py`: Produces structured JSON qualitative interpretation, devil's advocate risk critique, and psychological sanity checks.
   - `agents/coach/trade_coach.py`: Generates post-trade debriefs and lessons learned.
7. **Execution & Hard Safety Layer**:
   - `execution/live_disabled/live_blocker.py`: `LiveBrokerAdapterDisabled` raises fatal `LiveExecutionForbiddenError` on any order placement attempt.
   - `execution/safety/circuit_breaker.py`: Enforces max daily drawdown and consecutive loss trading halts.
   - `execution/paper/engine.py`: Simulates position opening, lot sizing, slippage modeling, and bracket TP/SL hits.
8. **OpenTraderWorld Journal & Performance Engine**:
   - `journal/ingestion/otw_journal_sync.py`: Live ingestion directly into OpenTraderWorld PostgreSQL database (`public.journal_trades`). Verified with live trade ID `eae80bc0-1f3c-4350-a02f-09d8c46dce3e`.
   - `journal/analytics/performance_engine.py`: Computes Sharpe ratio, Max Drawdown, Expectancy, Win Rate, and error attribution.
9. **Backtesting & Data Generation**:
   - `backtest/engine/simulator.py`: Bar-by-bar walk-forward simulator.
   - `backtest/datasets/data_generator.py`: Generates aligned 6-timeframe synthetic candle series with realistic price regimes.
10. **Research Dashboard**:
    - `dashboard/server.py`: FastAPI backend on port `8585`.
    - `dashboard/templates/index.html`: Dark-mode UI with multi-timeframe pills, S/R zones, Hermes critique, live JSON contract, and paper performance.
11. **Baseline EA Audit & Benchmark EA**:
    - `docs/BASELINE_EA_ANALYSIS.md`: Comprehensive audit of `NN_Crypto_Scalper.mq5` (`M1_Pullback_Baseline_EA`).
    - `core/M1_Pullback_Benchmark_EA.mq5`: Production-grade symmetrical MQL5 benchmark with shift-1 logic and relative ATR filter.

## Environment Status
- **Host OS**: Linux (WSL2 Ubuntu 24.04 on Windows 11 Legion)
- **GPU**: NVIDIA RTX 4060 Laptop (8 GB VRAM) active via CUDA 13.2 / Ollama daemon
- **Python**: Python 3.12.3 in dedicated `.venv/`
- **Location**: `~/dev/gold24-7` (moved out of the vault 2026-10-25). This repo has its own `docker-compose.yml`: `docker compose up -d dashboard` serves 8585.
- **Docker**: OpenTraderWorld stack running (PostgreSQL 18 at `172.28.53.3:5432`, Core API at `:5454`)
- **Dashboard**: `http://localhost:8585` (host process or the `dashboard` compose service; do not run both)

## Test Status
- `pytest`: **14 / 14 tests passing** (unit, contract, smoke).
- End-to-end live pipeline with Hermes 3:8B on GPU: **VERIFIED PASS**.
- OpenTraderWorld PostgreSQL insertion: **VERIFIED PASS**.

## Deployment Status
- Research / Paper Trading Platform: **OPERATIONAL**.
- Hard Safety Boundary: **STRICTLY ENFORCED** (Simulation only).

## Next Action
1. User review of the research dashboard at `http://localhost:8585`.
2. Expand walk-forward backtesting periods across longer historical CSV datasets.
3. Connect MT5 MCP Bridge on Windows host whenever live MT5 tick streaming is desired.

## Blockers
- None. System is fully operational and tested.
