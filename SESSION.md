# Session Continuity Scratchpad: GOLD24-7 + OpenTraderWorld Integration

## Active Objective
Deliver and configure Option B (Sibling Repositories with Unified Orchestration) between `opentraderworld` and `gold24-7`, including an autonomous trading daemon and unified system launcher.

## Current State
- Option B confirmed by user.
- Created `scripts/daemon_runner.py` for continuous XM MT5 market monitoring, 10-point mathematical risk validation, Hermes 3:8B qualitative critique on GPU, paper execution, and automatic publishing to OpenTraderWorld PostgreSQL ledger (`journal_trades`).
- Created unified master Windows launcher: `start-gold247-system.bat` in `m-2nd-brain/code/`.
- OpenTraderWorld running on port `5454` with PostgreSQL container on port `5432`.
- Formulated root cleanliness prompt for `m-2nd-brain`.
- Resolved `ModuleNotFoundError: No module named 'fastapi'` when running `dashboard/server.py` with system python by implementing PEP 405 auto-switch to `.venv` and adding `.vscode/settings.json`.
- Connected to live XM MetaTrader 5 on Windows (`C:\Program Files\XM Global MT5\terminal64.exe`, Account: 108489714) via [scripts/mt5_bridge_server.py](file:///home/vall/m-2nd-brain/projects/gold24-7/scripts/mt5_bridge_server.py) on port 8082. All 6 timeframes (D1 down to M1) stream live gold data ($4,140.07/oz).
- Resolved port 8585 Windows access via Windows localhost port relay. Dashboard is active and reachable at `http://localhost:8585` (or `http://172.26.144.249:8585`).
- Generated live quantitative trading signal for `GOLD#` powered by Hermes 3:8B on GPU via Ollama (`scripts/generate_gold_signal.py` and `/api/hermes/signal`).
- Created **BTCUSD# Expert Stack**:
  - [core/BTCUSD_Pullback_Benchmark_EA.mq5](file:///home/vall/m-2nd-brain/projects/gold24-7/core/BTCUSD_Pullback_Benchmark_EA.mq5): Specialized MT5 EA for XM `BTCUSD#` with 24/7 continuous crypto session, 2500 pt spread filter, and dynamic lot sizing.
  - [scripts/generate_btcusd_signal.py](file:///home/vall/m-2nd-brain/projects/gold24-7/scripts/generate_btcusd_signal.py): Standalone Hermes 3:8B Bitcoin Quantitative Signal generator.
  - Updated [adapters/broker/symbol_resolver.py](file:///home/vall/m-2nd-brain/projects/gold24-7/adapters/broker/symbol_resolver.py) with exact XM `BTCUSD#` contract specifications (`tick_value=0.01`, `spread=1500`).
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
  - Enhanced Windows MT5 Bridge ([scripts/mt5_bridge_server.py](file:///home/vall/m-2nd-brain/projects/gold24-7/scripts/mt5_bridge_server.py)) with `history_deals_get`, `positions_get`, and `history_orders_get` JSON-RPC methods.
  - Created standalone synchronizer [scripts/sync_mt5_to_otw.py](file:///home/vall/m-2nd-brain/projects/gold24-7/scripts/sync_mt5_to_otw.py) which reconstructs completed round-trip trades from MT5 deal tickets, calculates weighted entry/exit prices, fees, realized PnL, parses brackets (`[tp ...]` / `[sl ...]`), and performs idempotent sync using `import_row_hash`.
  - Ingested **162 completed live trades** from active XM MT5 account `335537672` (120 `BTCUSD#`, 40 `GOLD#`, 2 `DOTUSD#`) into OpenTraderWorld.
  - Configured default OTW category to `XMGlobal-MT5 9 (335537672)` and purged synthetic paper simulations so the live account trades display immediately on `http://localhost:5454/journal`.
  - Integrated continuous live account sync into [scripts/daemon_runner.py](file:///home/vall/m-2nd-brain/projects/gold24-7/scripts/daemon_runner.py) so any newly closed trade in MetaTrader 5 is automatically journaled into OpenTraderWorld on every cycle.

- Hermes 3:8B Tailored for Live Open Trades & Loss Mitigation:
  - Banned all mentions of "paper account", "ENTER_PAPER", or "virtual capital" across prompts and models.
  - Hermes 3 persona re-grounded to manage real live XM MT5 account `335537672` (Balance: $87.09, Equity: ~$52-$55, Leverage 1:1000).
  - Built dedicated `generate_loss_mitigation_plan()` auditing open tickets (`1030357046`, `1030430820`, `1030444089`), alerting on missing Stop Losses, and providing step-by-step emergency loss mitigation directives.
  - Added live loss mitigation directives container to Cockpit and upgraded Tab 4 into `Hermes 3:8B Live Risk & Loss Mitigation Engine`.
  - Updated [dashboard/server.py](file:///home/vall/m-2nd-brain/projects/gold24-7/dashboard/server.py) and [scripts/daemon_runner.py](file:///home/vall/m-2nd-brain/projects/gold24-7/scripts/daemon_runner.py); all 21 test suites passing (`21 passed in 0.68s`).
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

## Next Session Recoup Blueprint (Ready for User's Return)
- **Starting Capital**: $80.13
- **Recovery Target**: $125.65 (Net gain needed: +$45.52)
- **Trading Rules**:
  1. **Strictly 1 Open Trade at a Time** (Max positions = 1).
  2. **Fixed Lot Size**: 0.01 lot exclusively on `GOLD#` ($1 per point).
  3. **High Probability Scalps**: Targeting +15 to +30 pips ($1.50 to $3.00) per trade with tight hard Stop Loss (10-15 pips).
  4. **Auto-Stop Trigger**: Engine automatically halts all trading when balance touches or exceeds $125.65.





