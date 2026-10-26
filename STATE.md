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
- **Location**: `~/dev/gold24-7`. Run: `.venv/bin/python -m uvicorn dashboard.server:app --host 0.0.0.0 --port 8585` or docker compose.
- **Account**: XM MT5 Account `169588864` (`XMGlobal-MT5 2`, Leverage 1:500, Balance: $524.36, Equity: $514.17).
- **Active Symbols**: `GOLD#` and `GOLD24-7#` (configured with live ticks, rates, and 24/7 schedules).
- **MT5 Bridge**: Online on Windows host port 8082 (PID 25328).
- **Dashboard**: `http://localhost:8585` (online, serving real-time MT5 stream and open positions).

## Test Status
- `pytest`: **55 / 55 tests passing** (unit, characterization, contract, smoke).
- MT5 live tick & rate streaming for `GOLD#` and `GOLD24-7#`: **VERIFIED PASS**.
- End-to-end dashboard API (`/api/status`, `/api/market-data`): **VERIFIED PASS**.

## Deployment Status
- Research / Paper Trading Platform: **OPERATIONAL**.
- Hard Safety Boundary: **STRICTLY ENFORCED** (Simulation only).

## Next Action
1. Review live cockpit at `http://localhost:8585`.
2. Toggle between `GOLD#` and `GOLD24-7#` chips on the dashboard header.

## Blockers
- None. System is fully operational and streaming live data.
