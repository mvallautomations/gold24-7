# Session Continuity Scratchpad: GOLD24-7 + OpenTraderWorld Integration

## Location and run (2026-10-25)
Repo now lives at `~/dev/gold24-7` (moved out of the vault's `code/`). Run: `docker compose up -d dashboard` (port 8585); daemon: `--profile daemon`. See `AGENTS.md`.

## Active Objective
Consolidate `projects/Stock-Trading` MT5 tools (Checklist, Indicators, Experts, Strategy Setups) into `gold24-7` research dashboard, and deploy the automated MT5 Daily History "Sure Sync" engine for OpenTraderWorld.

## Current State & Milestones Completed (Oct 21, 2026)
- **Consolidated Stock-Trading MT5 Stack**:
  - Implemented [core/indicators/stochastic.py](core/indicators/stochastic.py): Stochastic Oscillator (14,3,3), EMA Ribbon (20/50/200), and AutoTrendChannel fractal swing detection (`SH`, `SL`).
  - Implemented [core/checklist/engine.py](core/checklist/engine.py): Digitized 9-stage `PRE-ANALYSIS_CHECKLIST.md` with live MT5 telemetry auto-evaluations, PHT/server clock, and state persistence.
  - Implemented [core/experts/catalog.py](core/experts/catalog.py): Unified catalog for 4 EAs (`GOLD_TrainingMonitorEA`, `M1_Pullback_Benchmark_EA`, `BTCUSD_Pullback_Benchmark_EA`, `OptionB_Mitigate_And_Recoup`), 2 Indicators/Scripts, and 4 testable Strategy Setups.
  - Added REST endpoints in [dashboard/server.py](dashboard/server.py): `/api/checklist`, `/api/checklist/save`, `/api/indicators/live`, `/api/experts/catalog`, `/api/strategy-setups/test`, `/api/sync/daily-history`.
  - Integrated 3 new high-density interactive views in [dashboard/templates/index.html](dashboard/templates/index.html):
    1. `📋 Trading Checklist & SOP` (with auto-pass verification, state saving, and instructor summary export)
    2. `🔬 Indicators & Snapshot Lab` (live multi-timeframe EMA ribbon, Stochastic meter, and CSV snapshot parser)
    3. `🤖 Experts & Strategy Testing Matrix` (EA parameter guides and live paper simulation test triggers)
- **Deployed MT5 Daily History "Sure Sync" Engine**:
  - Created [scripts/auto_sync_daily_history.py](scripts/auto_sync_daily_history.py): Supports `--once` instant catch-up sync and `--watch-logout` daemon that automatically triggers journal sync when MT5 closes/logs out.
  - Created Windows launcher [scripts/watch_mt5_logout_and_sync.bat](scripts/watch_mt5_logout_and_sync.bat).
  - All 25 automated unit and smoke tests passing (`25 passed in 0.82s`).

- OpenTraderWorld running on port `5454` with PostgreSQL container on port `5432`.
- Formulated root cleanliness prompt for `m-2nd-brain`.
- Resolved `ModuleNotFoundError: No module named 'fastapi'` when running `dashboard/server.py` with system python by implementing PEP 405 auto-switch to `.venv` and adding `.vscode/settings.json`.
- Connected to live XM MetaTrader 5 on Windows (`C:\Program Files\XM Global MT5\terminal64.exe`, Account: 108489714) via [scripts/mt5_bridge_server.py](scripts/mt5_bridge_server.py) on port 8082. All 6 timeframes (D1 down to M1) stream live gold data ($4,140.07/oz).
- Resolved port 8585 Windows access via Windows localhost port relay. Dashboard is active and reachable at `http://localhost:8585` (or `http://172.26.144.249:8585`).
- Generated live quantitative trading signal for `GOLD#` powered by Hermes 3:8B on GPU via Ollama (`scripts/generate_gold_signal.py` and `/api/hermes/signal`).
- Created **BTCUSD# Expert Stack**:
  - [core/BTCUSD_Pullback_Benchmark_EA.mq5](core/BTCUSD_Pullback_Benchmark_EA.mq5): Specialized MT5 EA for XM `BTCUSD#` with 24/7 continuous crypto session, 2500 pt spread filter, and dynamic lot sizing.
  - [scripts/generate_btcusd_signal.py](scripts/generate_btcusd_signal.py): Standalone Hermes 3:8B Bitcoin Quantitative Signal generator.
  - Updated [adapters/broker/symbol_resolver.py](adapters/broker/symbol_resolver.py) with exact XM `BTCUSD#` contract specifications (`tick_value=0.01`, `spread=1500`).
  - Verified live signal generation: `BTCUSD#` at `$85,324.45`, all 21 test suites passing (`21 passed in 0.69s`).
- Live Monday Market Open Check on `GOLD#`:
  - Active MT5 Account detected: `335537672` (`XMGlobal-MT5 9`, Leverage: 1000).
  - Exact active symbol confirmed: `GOLD#` (Ultra-low spread ~ 29-31 points).
  - Price moved up from weekend close of $4,140.07 to **$4,147.36**.
  - Generated fresh live Hermes 3:8B trade signal: BUY Pullback (Entry: $4,147.46, SL: $4,132.50, TP: $4,168.00).

- Gold Trader Autonomous Stack Started:
  - XM MT5 Bridge Server active on Windows port 8082 (Account: `335537672`, `XMGlobal-MT5 9`, Leverage 1000).
  - OpenTraderWorld PostgreSQL database verified (`172.28.53.2:5432`) and Web Journal running on `http://localhost:5454`.
  - Ollama Daemon active on GPU with `hermes3:8b`.
  - GOLD24-7 Research & Paper-Trading Dashboard active on `http://localhost:8585`.
  - Autonomous Trading Daemon (`scripts/daemon_runner.py`) actively monitoring live XM MT5 candles across all 6 timeframes for `GOLD#`, evaluating setups, executing paper fills, and recording to OpenTraderWorld journal.

- Real-Time Dynamic Viewing Dashboard Deployed:
  - Added real-time auto-streaming controls (fast 3s, standard 5s, 15s, 30s, or pause) with animated countdown progress bar and tick direction flash (emerald/rose).
  - Built high-performance HTML5 Canvas dynamic candlestick charting engine with crosshair HUD, price axis tags, volume bars, and live MT5 rate streaming.
  - Interactive multi-timeframe switching (`D1`, `H4`, `H1`, `M15`, `M5`, `M1`) that instantly recalculates and updates candles without full page reloads.
  - Dynamic visual overlays: Support and Resistance liquidity corridors + Active trade entry/SL/TP bracket lines.
  - Created 4-mode view tabs: (1) Dynamic Cockpit, (2) Synchronous 6-Timeframe Matrix with sparkline charts, (3) Paper Ledger & Position Stream, (4) Hermes 3:8B AI Lab.
  - Fast symbol switcher chips (`GOLD#`, `GAUUSD`, `BTCUSD#`, `ETHUSD#`, `EURUSD`).
  - Added `/api/market-data` endpoint in `dashboard/server.py` serializing all 6 timeframes and live metrics. All 21 test suites passing.

- System Restart Verified:
  - XM MT5 Bridge Server verified active on Windows host port 8082 (Account `335537672`, `XMGlobal-MT5 9`, Leverage 1000).
  - OpenTraderWorld PostgreSQL database verified active with 22 journal entries; Caddy web UI running on `http://localhost:5454`.
  - Ollama Daemon confirmed serving `hermes3:8b` on GPU (`http://127.0.0.1:11434`).
  - Unit test suite verified (all 21 tests passing).
  - GOLD24-7 Dashboard restarted and healthy on `http://localhost:8585` (task-114).
  - Autonomous Trading Daemon restarted and actively streaming 20-second evaluation cycles for `GOLD#` (task-120).

- XM MT5 Live Account Trade Synchronization Delivered:
  - Enhanced Windows MT5 Bridge ([scripts/mt5_bridge_server.py](scripts/mt5_bridge_server.py)) with `history_deals_get`, `positions_get`, and `history_orders_get` JSON-RPC methods.
  - Created standalone synchronizer [scripts/sync_mt5_to_otw.py](scripts/sync_mt5_to_otw.py) which reconstructs completed round-trip trades from MT5 deal tickets, calculates weighted entry/exit prices, fees, realized PnL, parses brackets (`[tp ...]` / `[sl ...]`), and performs idempotent sync using `import_row_hash`.
  - Ingested **162 completed live trades** from active XM MT5 account `335537672` (120 `BTCUSD#`, 40 `GOLD#`, 2 `DOTUSD#`) into OpenTraderWorld.
  - Configured default OTW category to `XMGlobal-MT5 9 (335537672)` and purged synthetic paper simulations so the live account trades display immediately on `http://localhost:5454/journal`.
  - Integrated continuous live account sync into [scripts/daemon_runner.py](scripts/daemon_runner.py) so any newly closed trade in MetaTrader 5 is automatically journaled into OpenTraderWorld on every cycle.

- Hermes 3:8B Tailored for Live Open Trades & Loss Mitigation:
  - Banned all mentions of "paper account", "ENTER_PAPER", or "virtual capital" across prompts and models.
  - Hermes 3 persona re-grounded to manage real live XM MT5 account `335537672` (Balance: $87.09, Equity: ~$52-$55, Leverage 1:1000).
  - Built dedicated `generate_loss_mitigation_plan()` auditing open tickets (`1030357046`, `1030430820`, `1030444089`), alerting on missing Stop Losses, and providing step-by-step emergency loss mitigation directives.
  - Added live loss mitigation directives container to Cockpit and upgraded Tab 4 into `Hermes 3:8B Live Risk & Loss Mitigation Engine`.
  - Updated [dashboard/server.py](dashboard/server.py) and [scripts/daemon_runner.py](scripts/daemon_runner.py); all 21 test suites passing (`21 passed in 0.68s`).
- Option B Market Open Execution Executed Flawlessly at 06:05:00 AM UTC+8:
  - Background daemon (`task-943`) triggered exactly on market re-open:
    1. Closed near-breakeven outlier position Ticket `1030497010` (Deal `1051824833`, realized loss -$3.23).
    2. Set hard emergency Stop Losses on all 4 remaining positions:
       - Ticket `1030357046` (BUY 0.01 @ 4153.28) -> SL: `4132.00`
       - Ticket `1030467151` (SELL 0.01 @ 4126.86) -> SL: `4147.50`
       - Ticket `1030469892` (SELL 0.01 @ 4128.01) -> SL: `4147.50`
       - Ticket `1030480916` (SELL 0.01 @ 4133.68) -> SL: `4147.50`
  - Account Metrics: Balance `$122.42`, Equity `$69.74`.
  - Automatically synced Deal `1051824833` into OpenTraderWorld journal (total synced: 204 trades).
- Full Position Liquidation & Clean Slate Executed (07:44 AM UTC+8):
  - User requested to close all remaining trades to secure capital and sleep with 100% peace of mind.
  - Closed all 4 positions via MT5 bridge:
    - Ticket `1030357046` (BUY 0.01 @ 4153.28) -> Deal `1051831576`
    - Ticket `1030467151` (SELL 0.01 @ 4126.86) -> Deal `1051831578`
    - Ticket `1030469892` (SELL 0.01 @ 4128.01) -> Deal `1051831581`
    - Ticket `1030480916` (SELL 0.01 @ 4133.68) -> Deal `1051831584`
  - Current Account Metrics:
    - Open Positions: **0**
    - Balance: **$80.13** (Secured cleanly, beat original $76 estimate)
    - Equity: **$80.13**
    - Free Margin: **$80.13**
  - Synced all 4 closed deals into OpenTraderWorld journal (total synced: 213 trades).

## Session Resumed (2026-10-06 19:47 UTC+8)
- **Account Verified**: Real Live XM MT5 Account `335537672` (`XMGlobal-MT5 9`, Leverage 1:1000).
- **Starting Metrics**:
  - Open Positions: **0** (Clean slate, zero market exposure)
  - Balance: **$80.13**
  - Equity: **$80.13**
  - Free Margin: **$80.13**
- **Subsystem Health**:
  - XM MT5 Windows Bridge: **ONLINE** (Port 8082, PID 28548)
  - Ollama Daemon (GPU): **ONLINE** (`hermes3:8b`)
  - OpenTraderWorld: **ONLINE** (`http://localhost:5454`) with 213 synced trades
  - GOLD24-7 Dashboard: **ONLINE** (`http://localhost:8585`)
  - Autonomous Live Daemon: **ARMED & ACTIVE** (task-177, monitoring `GOLD#` every 10s)
- **1-Minute Scalping Playbook Trial Simulation Delivered (2026-10-13 07:04 UTC+8)**:
  - Resolved `ModuleNotFoundError: No module named 'core'` by adding automatic project root resolution and PEP 405 virtual environment switching to [core/playbook/scalping_playbook.py](core/playbook/scalping_playbook.py).
  - Built walk-forward multi-timeframe trial simulation engine (`simulate_walkforward`) and CLI HUD (`run_trial_simulation`).
  - Added [scripts/simulate_playbook.py](scripts/simulate_playbook.py) supporting configurable flags (`--symbol`, `--lookback`, `--grade`).
  - Completed live snapshot audit on current M15, M5, and M1 bars for XAUUSD (`GOLD`):
    - 15M ORH/ORL Range: High `$4171.97`, Low `$4168.53` (3.44 pts range).
    - 5M Confirmation: Full body close below ORL confirmed at `$4168.40`.
    - 1M Model: Model A (Displacement & Momentum Breakout with FVG gap).
    - 10-Point Scorecard: 9/10 Points (Grade A+ Setup).
    - Invariant 1:2 R:R Execution Bracket: SELL @ `$4168.40`, Hard SL `$4169.90` (1.50 pts risk), TP `$4165.40` (3.00 pts reward).
- **Dashboard & MT5 Bridge Service Revival (2026-10-15 07:10 UTC+8)**:
  - Root Cause of "nothing appears in browser": Following an environment restart, both the Uvicorn web server (port 8585) and the Windows MT5 Bridge (port 8082) had stopped, causing browser connection timeouts.
  - Revived XM MT5 Windows Bridge on port 8082 connecting to active account `318771003` (`XMGlobal-MT5 7`, Balance: $3,962.53, Equity: $3,938.02).
  - Started Uvicorn server on `0.0.0.0:8585` (task-245) with verified 200 OK responses to Windows host (`curl.exe http://localhost:8585/`).
  - Started Autonomous Live Daemon (`scripts/daemon_runner.py`, task-326) monitoring real-time active positions and M1 bars.
  - Verified JavaScript syntax in [dashboard/templates/index.html](dashboard/templates/index.html) with 0 errors across all 77 DOM IDs and endpoints.
  - Launched Windows browser directly to `http://localhost:8585`.
