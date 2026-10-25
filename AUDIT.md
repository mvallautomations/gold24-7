# GOLD24-7 Repository Audit

Audit date: 2026-10-23  
Scope: repository contents and the current working-tree versions of the requested files. No code was modified. Existing working-tree modifications were present before this report was added.

## 1. Files present / missing

### README tree comparison

`present` means the README-claimed file or directory exists in the repository; `missing` means no corresponding path was found; `renamed-to` identifies the actual path when the README's requested path is not present as written.

| README claim | Status | Observation |
|---|---|---|
| `core/models/` | present | `candle.py`, `signal.py`, `trade.py`, `zones.py`, and related models exist. |
| `core/indicators/` | present | Directory exists. |
| `core/market/` | present | Directory exists. |
| `core/signals/` | present | Directory exists. |
| `core/validation/` | present | `validator.py` exists. |
| `core/configuration/` | present | Configuration is present at `core/configuration/config.py`. |
| `core/M1_Pullback_Baseline_EA.mq5` | present | — |
| `core/M1_Pullback_Benchmark_EA.mq5` | present | — |
| `adapters/mt5/` | present | Contains `data_feed.py`. |
| `adapters/mcp/` | present | Contains `client.py`. |
| `adapters/broker/` | present | Contains `symbol_resolver.py`. |
| `adapters/journal/` | present | Directory exists. |
| `agents/hermes/` | present | Contains `client.py`. |
| `agents/analyzer/` | present | Contains `interpreter.py`. |
| `agents/coach/` | present | Contains `trade_coach.py`. |
| `execution/paper/` | present | Contains `engine.py`. |
| `execution/safety/` | present | Contains `circuit_breaker.py`. |
| `execution/live_disabled/` | present | Contains `live_blocker.py`. |
| `backtest/engine/` | present | Contains `simulator.py`. |
| `backtest/datasets/` | present | Contains generator and regime modules. |
| `backtest/metrics/` | missing | No metrics directory/files found. |
| `backtest/walk_forward/` | present | Contains `validator.py`. |
| `journal/schema/` | missing | No files found under this path; no checked-in table schema or migration found. |
| `journal/ingestion/` | present | Contains `otw_journal_sync.py`. |
| `journal/analytics/` | present | Contains analytics modules. |
| `dashboard/server.py` | present | — |
| `dashboard/templates/index.html` | present | — |
| `tests/unit/` | present | — |
| `tests/contract/` | present | — |
| `tests/smoke/` | present | — |
| `tests/integration/` | missing | No integration tests found. |
| `scripts/run_pipeline.py` | present | — |
| `scripts/launch_dashboard.sh` | present | — |
| `scripts/test_hermes_coach_pipeline.py` | present | — |
| `docs/BASELINE_EA_ANALYSIS.md` | present | — |
| `STATE.md`, `README.md`, `requirements.txt` | present | — |
| Requested `config.py` at repository root | renamed-to: `core/configuration/config.py` | No root `config.py` exists. |
| Requested `symbol_resolver.py` | renamed-to: `adapters/broker/symbol_resolver.py` | — |
| Requested MCP `client.py` | renamed-to: `adapters/mcp/client.py` | The other requested Hermes client is `agents/hermes/client.py`. |
| Requested `data_feed.py` | renamed-to: `adapters/mt5/data_feed.py` | — |

### Additional files

Files and paths beyond the README's explicitly named files/tree include:

- Root/configuration: `.env.example`, `.gitignore`, `pytest.ini`, `vite.config.ts`, `.vscode/settings.json`, `.vscode/launch.json`, `HANDOFF.md`, `SESSION.md`.
- Core: `core/BTCUSD_Pullback_Benchmark_EA.mq5`, `core/OptionB_Mitigate_And_Recoup.mq5`, `core/checklist/`, `core/experts/`, `core/indicators/stochastic.py`, `core/playbook/` (including two MQL5 files and `scalping_playbook.py`).
- Dashboard: `dashboard/templates/index.html.backup`.
- Docs/research: `docs/1-Minute_Scalping_Playbook.pdf`, `docs/playbook_summary.txt`, `docs/playbook_images/`, and `docs/research/` (including phase-2 reports, results, and baseline config).
- Scripts: `scripts/daemon_runner.py`, `scripts/execute_market_open_mitigation.py`, `scripts/generate_btcusd_signal.py`, `scripts/generate_gold_signal.py`, `scripts/mt5_bridge_server.py`, `scripts/restart_mt5_bridge.ps1`, `scripts/run_phase2_validation.py`, `scripts/simulate_playbook.py`, `scripts/sync_mt5_to_otw.py`, `scripts/auto_sync_daily_history.py`, `scripts/watch_mt5_logout_and_sync.bat`.
- Tests: `tests/unit/test_checklist_and_stochastic.py`, `tests/unit/test_research_validation.py`, `tests/unit/test_validator_and_safety.py`.

### Requested sorted file inventory

The requested `find . -type f ... | sort > /tmp/tree.txt` command was run in WSL. It produced 3,584 paths because it includes `.venv/lib/python3.12/site-packages`; the raw file is `/tmp/tree.txt`. The repository-source inventory below is the same extension/name filter with generated `.venv`, `.git`, and `__pycache__` paths excluded, so it is useful for understanding project files rather than third-party installed packages:

```text
./.env.example
./adapters/broker/symbol_resolver.py
./adapters/mcp/client.py
./adapters/mt5/data_feed.py
./agents/analyzer/interpreter.py
./agents/coach/trade_coach.py
./agents/hermes/client.py
./backtest/ablation/runner.py
./backtest/datasets/data_generator.py
./backtest/datasets/regimes.py
./backtest/engine/simulator.py
./backtest/walk_forward/validator.py
./core/BTCUSD_Pullback_Benchmark_EA.mq5
./core/M1_Pullback_Baseline_EA.mq5
./core/M1_Pullback_Benchmark_EA.mq5
./core/OptionB_Mitigate_And_Recoup.mq5
./core/checklist/engine.py
./core/configuration/config.py
./core/experts/catalog.py
./core/indicators/__init__.py
./core/indicators/moving_averages.py
./core/indicators/stochastic.py
./core/indicators/volatility.py
./core/indicators/zones.py
./core/market/analyzer.py
./core/models/__init__.py
./core/models/candidate.py
./core/models/candle.py
./core/models/indicators.py
./core/models/signal.py
./core/models/trade.py
./core/models/zones.py
./core/playbook/Playbook_15M_OpeningRange_Indicator.mq5
./core/playbook/Playbook_Scalping_Cockpit_EA.mq5
./core/playbook/scalping_playbook.py
./core/signals/evaluator.py
./core/validation/validator.py
./dashboard/server.py
./dashboard/templates/index.html
./dashboard/templates/index.html.backup
./execution/live_disabled/live_blocker.py
./execution/paper/engine.py
./execution/safety/circuit_breaker.py
./journal/analytics/performance_engine.py
./journal/analytics/r_multiple.py
./journal/ingestion/otw_journal_sync.py
./scripts/auto_sync_daily_history.py
./scripts/daemon_runner.py
./scripts/execute_market_open_mitigation.py
./scripts/generate_btcusd_signal.py
./scripts/generate_gold_signal.py
./scripts/mt5_bridge_server.py
./scripts/restart_mt5_bridge.ps1
./scripts/run_phase2_validation.py
./scripts/run_pipeline.py
./scripts/simulate_playbook.py
./scripts/sync_mt5_to_otw.py
./scripts/test_hermes_coach_pipeline.py
./scripts/watch_mt5_logout_and_sync.bat
./tests/contract/test_signal_contract.py
./tests/smoke/test_end_to_end_smoke.py
./tests/unit/test_checklist_and_stochastic.py
./tests/unit/test_indicators.py
./tests/unit/test_paper_engine.py
./tests/unit/test_research_validation.py
./tests/unit/test_symbol_resolver.py
./tests/unit/test_validator_and_safety.py
```

## 2. Safety boundary status

- `ENVIRONMENT`, `ALLOW_LIVE_EXECUTION`, and `IS_SIMULATION_ONLY` use `Field(..., frozen=True)` in `core/configuration/config.py` (lines 13–15). These are Pydantic field settings, not a hard, process-independent lock: `BaseSettings` still accepts configuration at construction, and not all endpoints consult these settings before dispatch.
- `execution/live_disabled/` exists. `LiveBrokerAdapterDisabled.order_send`, `buy`, `sell`, `modify_position`, and `close_position` all raise `LiveExecutionForbiddenError` directly or delegate to `order_send` (`execution/live_disabled/live_blocker.py:21–37`).
- The blocker is not the only execution path. Direct order dispatch is present outside it:
  - `dashboard/server.py:411` sends JSON-RPC `order_send`; the corresponding `/api/playbook/execute` endpoint is at line 349.
  - `scripts/daemon_runner.py:263` sends JSON-RPC `order_send`.
  - `scripts/mt5_bridge_server.py:231,273,290` calls `mt5.order_send`.
  - MQL5 `trade.Buy`/`trade.Sell` calls exist in `core/M1_Pullback_Baseline_EA.mq5:215`, `core/M1_Pullback_Benchmark_EA.mq5:228,240`, `core/BTCUSD_Pullback_Benchmark_EA.mq5:247,253`, `core/OptionB_Mitigate_And_Recoup.mq5:285,298`, and `core/playbook/Playbook_Scalping_Cockpit_EA.mq5:491,495`.
- `dashboard/server.py:56–70` reports `environment: "LIVE_ACCOUNT"` and `is_simulation_only: False`; `dashboard/server.py:106–114` also invokes live account-position and account-stat readers. These are inconsistent with a paper-only product declaration.
- Tests asserting the forbidden-execution exception exist: `tests/unit/test_validator_and_safety.py::test_live_execution_blocker_fatal_exception` and `tests/unit/test_research_validation.py::test_live_broker_adapter_strictly_disabled`. The current tests do not cover the dashboard/daemon/bridge order-dispatch routes or the MQL5 EAs.

**Status: the stated hard safety boundary is not upheld repository-wide.** The live-disabled adapter itself rejects its write methods, but live-capable order paths coexist elsewhere and are not routed through it.

## 3. Confirmed bugs

Line references are to the current working-tree contents.

1. **Fallback symbol list can poison the resolver's live-symbol cache.** `MT5MCPClient.get_symbols()` returns a synthetic default list when disconnected and another fallback list after a failed/invalid request (`adapters/mcp/client.py:55–72`). `MT5DataFeed` stores any nonempty result into `resolver.active_mt5_symbols` (`adapters/mt5/data_feed.py:43–48`). Thus fallback symbols can be treated as the live broker catalogue.
2. **Resolver uses an unanchored substring match.** `adapters/broker/symbol_resolver.py:91–94` accepts `req_clean in active.upper()`. A requested ticker can therefore resolve to a different active instrument whose name merely contains the requested text.
3. **Non-numeric bar timestamps are mislabeled as current time.** Numeric epoch values are explicitly interpreted as UTC (`adapters/mt5/data_feed.py:76`); any other `time` value is replaced with `datetime.now(timezone.utc)` instead of parsed. This is a timestamp substitution, not an error in the numeric epoch timezone conversion.
4. **Broker specifications are hardcoded and used as defaults.** `DEFAULT_SPECS` contains static digits, point, tick value, lot bounds/step, and spread values (`adapters/broker/symbol_resolver.py:52–59`), and `_build_resolution` applies those values (`:108–124`). If no live broker metadata is available, calculations can use stale or inaccurate values.
5. **Synthetic bars can enter ordinary paper-trade flow without provenance gating.** When live data is unavailable or incomplete, `get_multitimeframe_bars()` returns generated bars (`adapters/mt5/data_feed.py:54–68`). `/api/evaluate` then validates and calls `paper_engine.execute_signal()` without checking whether those bars were synthetic (`dashboard/server.py:80–113`). No source field exists on `Bar` (`core/models/candle.py:38–47`), so downstream paper execution cannot distinguish the fallback source.
6. **`Bar` has no source/provenance flag.** `core/models/candle.py:38–47` defines timestamp, OHLCV, shift, and shift type only.
7. **Embedded database credential is present.** `OTW_DATABASE_URL` is hardcoded with an embedded credential in `core/configuration/config.py:33`; `.env.example` also contains a database URL entry (line 24). The credential value is intentionally not reproduced here. Treat it as exposed and rotate/revoke it; remove committed credentials and check repository history/deployments for copies.

## 4. LLM integration current state

- `agents/hermes/client.py` calls the local Ollama HTTP API at `{OLLAMA_BASE_URL}/api/generate`; configured defaults are `http://127.0.0.1:11434` and model string `hermes3:8b` (`core/configuration/config.py:27–29`).
- The client extracts `data.get("response", "").strip()` from the Ollama response and returns raw text. It has async and synchronous variants.
- `agents/analyzer/interpreter.py` strips optional Markdown fences and calls `json.loads`. It then maps keys and coerces selected values into `LLMInterpretation` or `SignalContract` fields. The model classes are Pydantic models, but there is no explicit JSON Schema validation of the model response, no strict extra-field rejection, and several values are defaulted/coerced.
- A deterministic response is returned on HTTP/non-200 or connection failure (`agents/hermes/client.py:44–51,71–78,80–88`). Parse failures in the interpreter also choose hardcoded fallback values (`agents/analyzer/interpreter.py:99–125` and `:219–225` onward).
- **Safety concern:** the system prompt explicitly permits `EXECUTE_LIVE` (`agents/analyzer/interpreter.py:30–35`); this is not itself an execution call, but reinforces that prompts/LLM output are not a safety boundary. The direct broker routes listed in §2 are outside the blocker.

## 5. Dashboard current capabilities

### Routes in `dashboard/server.py`

| Method | Route |
|---|---|
| GET | `/api/status` |
| GET | `/api/evaluate` |
| GET | `/api/hermes/signal` |
| GET | `/api/hermes/loss-mitigation` |
| GET | `/api/market-data` |
| GET | `/api/research/latest` |
| GET | `/api/research/regimes` |
| GET | `/api/backtest` |
| GET | `/api/playbook/schedules` |
| GET | `/api/playbook/evaluate` |
| GET | `/api/playbook/m15-objects` |
| POST | `/api/playbook/execute` |
| GET | `/api/playbook/history` |
| POST | `/api/playbook/post-audit` |
| GET | `/api/checklist` |
| POST | `/api/checklist/save` |
| GET | `/api/indicators/live` |
| GET | `/api/experts/catalog` |
| POST | `/api/strategy-setups/test` |
| POST | `/api/sync/daily-history` |
| GET | `/` |

### Panels/components present

- Multi-timeframe OHLC candlestick chart rendered to an HTML canvas, with timeframe controls, drawing/object toolbar, chart HUD, and 15M/5M/1M playbook overlays.
- Playbook/copy-trader copilot and scorecard.
- Multi-market schedules/cards and a strategy setup testing matrix.
- R-multiple ledger, KPI cards, cumulative R-yield canvas chart, and daily post-session audit form.
- MT5 positions/account panel with open-position table and account KPIs.
- Hermes risk-auditor panel.
- Pre-analysis/pre-trade checklist panel with save controls.
- MT5 indicator/snapshot lab and expert advisor directory.

### Gaps or misleading UI

- **Chart:** present as a custom canvas implementation; no `lightweight-charts` dependency or CDN integration was found.
- **Provider health:** no truthful LLM/provider health panel. `/api/status` returns a fixed `"ONLINE"` status and account-like values, rather than a provider health probe.
- **Checklist:** present.
- **Hedge exposure:** no dedicated hedge-pair or aggregate hedge exposure panel/endpoint found.
- **ELI10:** no dedicated “explain like I’m 10” mode or panel found.
- The UI and routes expose copy-trading/live-account language and order controls, while the README claims permanent paper-only operation.

## 6. Journal schema

- No checked-in DDL, ORM mapping, or migration exists under `journal/schema/`; the directory is absent/empty.
- The ingestion path is `OTWJournalIngestion.ingest_closed_trade()` in `journal/ingestion/otw_journal_sync.py`. It directly inserts into external `journal_trades` (lines 76–102) and writes a JSON value to the `fields` column (the `fields` object at lines 62–74, passed through `psycopg2.extras.Json` at lines 124–126).
- Table/columns referenced by the insert: `journal_trades`; `id`, `category_id`, `ticker`, `asset_class`, `side`, `entry_at`, `exit_at`, `entry_price`, `exit_price`, `quantity`, `fees`, `leverage`, `multiplier`, `signal_name`, `feedback`, `currency`, `unit_type`, `stop_price`, `brackets`, `entries`, `exits`, `fields`, `created_at`, `updated_at`. This is the application insert contract, not a verified complete database schema.
- None of `llm_provider`, `llm_model_id`, `llm_fallback_used`, `pre_trade_checklist`, `adaptive_regime`, `hedge_pair_id`, or `strategy_mode` is present as an explicit inserted column or repository schema field.
- Current extension point: `fields` already carries JSON metadata, so such metadata can fit there without adding a join table, subject to the external database column accepting JSON. There is no in-repository schema alteration/migration mechanism. A normalized/queryable join extension would require external schema changes and corresponding ingestion changes; no such table currently exists.

## 7. Dependency state

Current `requirements.txt`:

```text
pydantic>=2.7.0
pydantic-settings>=2.2.0
httpx>=0.27.0
fastapi>=0.111.0
uvicorn>=0.30.0
pytest>=8.2.0
pytest-asyncio>=0.23.0
pandas>=2.2.0
numpy>=1.26.0
psycopg2-binary>=2.9.9
pyyaml>=6.0.1
rich>=13.7.0
python-dotenv>=1.0.1
```

- `freelm`: absent.
- `jsonschema`: absent.
- `httpx`: present, requirement `>=0.27.0`.
- `lightweight-charts`: absent as a Python dependency; dashboard currently uses built-in canvas drawing, not this library/CDN.

## 8. Deviations from the manifest

This section maps each specifically requested §3 check to the actual target state:

| Check | Target state | Finding |
|---|---|---|
| Cache poisoning in `get_symbols()` | `adapters/mcp/client.py` exists; it is named under `adapters/mcp/`, not root. | Fallback lists are returned on disconnected/error paths and then cached by `MT5DataFeed`; issue confirmed. |
| Unanchored resolver substring matching | `adapters/broker/symbol_resolver.py` exists. | `req_clean in active.upper()` present; issue confirmed. |
| Timezone/timestamp handling in data feed | `adapters/mt5/data_feed.py` exists. | Numeric Unix times are UTC; non-numeric timestamps are replaced by current UTC. Confirmed timestamp substitution for non-numeric input, not a blanket UTC-offset bug. |
| Hardcoded broker specifications | `adapters/broker/symbol_resolver.py` exists. | Static `DEFAULT_SPECS` values used by fallback resolutions; issue confirmed. |
| Synthetic data leaking into paper trades | `adapters/mt5/data_feed.py`, `dashboard/server.py`, and `execution/paper/engine.py` exist. | Synthetic fallback is not marked or rejected before `/api/evaluate` paper execution; issue confirmed. |
| Missing `source` flag on `Bar` | `core/models/candle.py` exists. | `Bar` model has no source/provenance field; missing capability confirmed. |
| `OTW_DATABASE_URL` credential | `core/configuration/config.py` exists; requested bare `config.py` is renamed there. | Embedded credential is present at line 33 (value redacted); rotation required. `.env.example` also has a DB URL entry. |

## 9. Risks & blockers

1. **Critical live-order paths exist despite the stated prohibition.** `/api/playbook/execute`, `scripts/daemon_runner.py`, `scripts/mt5_bridge_server.py`, and multiple MQL5 EAs expose or implement order placement outside the blocker. The bridge dispatches MT5 `order_send` methods directly. This is the principal safety blocker.
2. **Synthetic data is indistinguishable from broker data in downstream signals and paper execution.** There is no `Bar.source`, and the pipeline can execute a paper signal after generating fallback bars.
3. **Credential exposure.** The database URL includes an embedded credential in tracked configuration; rotate it and account for any copies in history, logs, or deployments. The report deliberately omits the secret.
4. **Weak signal-resolution integrity.** Unanchored substring matching and default broker specs can associate the wrong symbol or inaccurate instrument math with a signal.
5. **Timestamp validity is not guaranteed for non-numeric inputs.** Replacing a supplied timestamp with current time can distort bar ordering and derived indicators.
6. **Test coverage does not gate the risky paths.** The suite asserts that the blocker throws, but does not test that all dashboard/script/bridge/MQL5 write paths are impossible. There are no integration tests under the README-claimed `tests/integration/`.
7. **LLM output validation is permissive.** Parsing uses JSON decoding and model construction/coercion, not a strict response schema; fallback and malformed-output paths are only partly covered by collected tests.
8. **Database schema is external and undocumented here.** There is no checked-in schema or migration to verify the real `journal_trades` column types or evolve them safely.

### Test collection

Only `pytest --collect-only -q` was run; no tests were executed. It collected 25 tests:

```text
tests/contract/test_signal_contract.py::test_signal_contract_schema_compliance
tests/smoke/test_end_to_end_smoke.py::test_full_pipeline_smoke
tests/smoke/test_end_to_end_smoke.py::test_backtest_simulator_smoke
tests/unit/test_checklist_and_stochastic.py::test_stochastic_calculation
tests/unit/test_checklist_and_stochastic.py::test_ema_alignment
tests/unit/test_checklist_and_stochastic.py::test_checklist_engine
tests/unit/test_checklist_and_stochastic.py::test_catalog_retrieval
tests/unit/test_indicators.py::test_volatility_engine_relative_atr
tests/unit/test_indicators.py::test_support_resistance_zones
tests/unit/test_indicators.py::test_moving_averages_and_trend
tests/unit/test_paper_engine.py::test_lot_size_calculation
tests/unit/test_paper_engine.py::test_paper_execution_and_tp_hit
tests/unit/test_research_validation.py::test_lookahead_prevention_and_shift_indexing
tests/unit/test_research_validation.py::test_candidate_journaling_and_counterfactuals
tests/unit/test_research_validation.py::test_r_multiple_analytics
tests/unit/test_research_validation.py::test_buy_sell_symmetry
tests/unit/test_research_validation.py::test_walk_forward_window_partitioning
tests/unit/test_research_validation.py::test_live_broker_adapter_strictly_disabled
tests/unit/test_research_validation.py::test_validator_enforces_paper_only
tests/unit/test_symbol_resolver.py::test_resolver_xm_defaults
tests/unit/test_symbol_resolver.py::test_resolver_live_cache_matching
tests/unit/test_validator_and_safety.py::test_live_execution_blocker_fatal_exception
tests/unit/test_validator_and_safety.py::test_validator_rejects_live_environment
tests/unit/test_validator_and_safety.py::test_validator_bracket_geometry
tests/unit/test_validator_and_safety.py::test_circuit_breaker_tripping
```

## Appendix A. First 30 lines of requested files

The excerpts below are from the current working-tree versions of these requested files. The configuration secret is not in the excerpt; any credential references elsewhere in the report are redacted.


### `core/configuration/config.py`

```py

"""
Global configuration for GOLD24-7 Research & Paper Trading Platform.
Enforces that LIVE trading is permanently locked to FALSE.
"""

from typing import List, Dict, Any
from pydantic_settings import BaseSettings
from pydantic import Field


class AppConfig(BaseSettings):
    # Hard Safety Boundary
    ENVIRONMENT: str = Field(default="PAPER", frozen=True)
    ALLOW_LIVE_EXECUTION: bool = Field(default=False, frozen=True)
    IS_SIMULATION_ONLY: bool = Field(default=True, frozen=True)

    # Broker & Symbol Resolver
    DEFAULT_BROKER: str = "XM"
    DEFAULT_SYMBOLS: List[str] = ["XAUUSD", "GAUUSD", "BTCUSD", "ETHUSD"]

    # MT5 / MCP Connection
    MT5_MCP_SERVER_URL: str = "http://172.26.144.1:8082"
    MT5_HOST: str = "172.26.144.1"
    MT5_PORT: int = 8082

    # Hermes 3 LLM (Ollama)
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    HERMES_MODEL: str = "hermes3:8b"
    HERMES_TIMEOUT_SEC: float = 30.0


```


### `adapters/broker/symbol_resolver.py`

```py

"""
Broker Symbol Resolver: Dynamically maps requested generic symbols (e.g. XAUUSD, BTCUSD)
to actual broker-specific MT5 instrument names (e.g. GAUUSD, GOLDmicro, BTCUSD.m).
Queries MT5 directly when connected, with deterministic alias fallbacks.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)


class SymbolResolution(BaseModel):
    requested: str
    resolved: str
    broker: str
    status: str  # RESOLVED, AMBIGUOUS, NOT_FOUND, FALLBACK
    digits: int = 2
    point: float = 0.01
    tick_size: float = 0.01
    tick_value: float = 1.0
    min_lot: float = 0.01
    max_lot: float = 100.0
    lot_step: float = 0.01
    spread_points: int = 15
    is_live_supported: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)



```


### `adapters/mcp/client.py`

```py

"""
MT5 MCP Client: Interacts with the MT5 MCP Server / Bridge over HTTP/SSE.
Retrieves market data, ticks, and symbol lists without ever placing live orders.
"""

from typing import List, Dict, Any, Optional
import httpx
import logging
from core.configuration.config import config

logger = logging.getLogger(__name__)


class MT5MCPClient:
    """
    Client for MT5 MCP Bridge.
    Strict read-only inspection of charts, accounts, and tick streams.
    """

    def __init__(self, base_url: Optional[str] = None):
        url = (base_url or config.MT5_MCP_SERVER_URL).rstrip("/")
        if url.endswith("/sse"):
            url = url[:-4]
        self.base_url = url
        self.is_connected = False

    async def ping(self) -> bool:
        """Check if MT5 MCP server is reachable."""
        candidate_urls = [self.base_url]
        # Allow fallback between gateway IP and localhost

```


### `adapters/mt5/data_feed.py`

```py

"""
MT5 Multi-Timeframe Data Feed: Translates raw broker rates into canonical Bar models.
Provides seamless fallback to synthetic historical market data when MT5 is offline.
"""

from typing import Dict, List, Optional
from datetime import datetime, timezone
import logging

from core.models.candle import Bar, BarShift, Timeframe
from adapters.mcp.client import MT5MCPClient
from adapters.broker.symbol_resolver import BrokerSymbolResolver
from backtest.datasets.data_generator import MarketDataGenerator

logger = logging.getLogger(__name__)


class MT5DataFeed:
    """
    Supplies the pipeline with clean, multi-timeframe candle datasets.
    """

    def __init__(
        self,
        mcp_client: Optional[MT5MCPClient] = None,
        resolver: Optional[BrokerSymbolResolver] = None
    ):
        self.mcp_client = mcp_client or MT5MCPClient()
        self.resolver = resolver or BrokerSymbolResolver()


```


### `core/validation/validator.py`

```py

"""
Deterministic Validator: Final hard mathematical gate before paper execution.
Enforces the fundamental architectural law:
"The LLM interprets. Deterministic code calculates and validates."
"""

from typing import List, Optional
from core.models.signal import SignalContract, SignalDirection, ValidationResult, VolatilityState


class DeterministicValidator:
    """
    Independent validation gate.
    Hermes (or any LLM) cannot bypass these rules or invent prices.
    """

    def __init__(
        self,
        min_risk_reward: float = 1.2,
        max_risk_reward: float = 5.0,
        max_spread_points: int = 50,
        min_atr_multiplier: float = 0.5,
        max_atr_multiplier: float = 4.0,
        max_account_risk_pct: float = 1.0,
    ):
        self.min_risk_reward = min_risk_reward
        self.max_risk_reward = max_risk_reward
        self.max_spread_points = max_spread_points
        self.min_atr_multiplier = min_atr_multiplier
        self.max_atr_multiplier = max_atr_multiplier

```


### `execution/paper/engine.py`

```py

"""
Simulated Paper Trading Engine: Realistic virtual execution, slippage modeling,
lot sizing, position tracking, and bracket order fulfillment.
"""

from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
import math
import logging

from core.models.signal import SignalContract, SignalDirection
from core.models.trade import PaperOrder, PaperPosition, PositionSide, TradeStatus
from execution.safety.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)


class PaperTradingEngine:
    """
    Simulated order book and position manager.
    Operates completely decoupled from live MT5 order pipelines.
    """

    def __init__(
        self,
        initial_balance: float = 10000.0,
        risk_per_trade_pct: float = 1.0,
        slippage_points: float = 1.5,
        fee_per_lot: float = 3.50  # $3.50 per standard lot turn
    ):

```


### `agents/analyzer/interpreter.py`

```py

"""
Hermes Market Interpreter: Interprets deterministic indicators and provides
qualitative critique, live open trade loss mitigation, and psychological check.
Tailored for live account XMGlobal-MT5 9 (335537672, Leverage 1:1000).
"""

import json
import logging
from typing import Optional, Any, List, Dict
from core.models.signal import (
    SignalContract,
    LLMInterpretation,
    SignalDirection,
    SetupType,
    MarketRegime,
    VolatilityState,
    TrendDirection
)
from core.market.analyzer import MultiTimeframeMarketState
from agents.hermes.client import HermesClient

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are Hermes 3, an elite quantitative trading mentor, risk manager, and loss mitigation critic for a live XM MT5 trading account (XMGlobal-MT5 9, Login: 336888981, Leverage: 1:100).
Your core directives:
1. Real money is on the line. NEVER mention "paper", "paper account", "virtual capital", or "ENTER_PAPER".
2. Prioritize capital preservation, mitigating floating drawdown on live open positions, and cutting toxic exposure.
3. If open positions exist with floating losses or without Stop Losses, prioritize explicit loss mitigation rules (emergency stops, partial trims, trailing SL) over new aggressive entries.
4. Output MUST be valid JSON adhering strictly to the requested schema:

```


### `agents/coach/trade_coach.py`

```py

"""
Hermes Trade Coach: Post-trade feedback, performance critique, and journal debrief.
"""

from typing import Dict, Any, Optional
from core.models.trade import PaperPosition
from agents.hermes.client import HermesClient
import logging

logger = logging.getLogger(__name__)


class HermesTradeCoach:
    """
    Evaluates completed paper trades and writes journal debriefs.
    Identifies behavioral leaks (e.g. premature exits, holding losers, revenge trading).
    """

    def __init__(self, client: Optional[HermesClient] = None):
        self.client = client or HermesClient()

    def generate_trade_review(self, position: PaperPosition) -> str:
        """
        Generate qualitative post-trade feedback for OpenTraderWorld journal.
        """
        pnl_str = f"+${position.realized_pnl:.2f}" if position.realized_pnl >= 0 else f"-${abs(position.realized_pnl):.2f}"
        outcome = "WIN" if position.realized_pnl > 0 else "LOSS"

        prompt = f"""
REVIEW COMPLETED PAPER TRADE:

```


### `agents/hermes/client.py`

```py

"""
Hermes 3 LLM Client: Connects to local Ollama Hermes 3:8B on GPU.
Structured JSON prompt formatting with deterministic fallbacks when Ollama is offline.
"""

from typing import Dict, Any, Optional
import httpx
import json
import logging
from core.configuration.config import config

logger = logging.getLogger(__name__)


class HermesClient:
    """
    Client for Hermes 3:8B running locally via Ollama.
    Strictly isolated: Can NEVER execute orders or mutate market data.
    """

    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        self.base_url = (base_url or config.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or config.HERMES_MODEL
        self.timeout = config.HERMES_TIMEOUT_SEC

    async def generate_response(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Query Hermes with asynchronous HTTP request."""
        endpoint = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,

```


### `dashboard/server.py`

```py

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

import json
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any

from core.configuration.config import config
from core.models.candle import Timeframe
from core.market.analyzer import MultiTimeframeMarketAnalyzer
from core.signals.evaluator import SignalEvaluator
from core.validation.validator import DeterministicValidator
from adapters.broker.symbol_resolver import BrokerSymbolResolver
from adapters.mt5.data_feed import MT5DataFeed
from agents.analyzer.interpreter import HermesMarketInterpreter
from execution.paper.engine import PaperTradingEngine

```


### `dashboard/templates/index.html`

```html

<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>GOLD24-7 • Precision Scalping Cockpit & Copy Trader HUD</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700;800&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-base: #131722;
      --bg-surface: #1e222d;
      --surface-1: #1e222d;
      --surface-2: #242835;
      --surface-3: #2a2e39;
      --border-subtle: #2a2e39;
      --border-active: #363a45;
      --border-cyan: #2962ff;
      --text-main: #d1d4dc;
      --text-muted: #787b86;
      --text-dim: #5d606b;
      --accent-gold: #ffeb3b;
      --accent-gold-glow: rgba(255, 235, 59, 0.2);
      --accent-cyan: #2962ff;
      --accent-cyan-glow: rgba(41, 98, 255, 0.25);
      --accent-green: #089981;
      --accent-green-glow: rgba(8, 153, 129, 0.25);
      --accent-red: #f23645;
      --accent-red-glow: rgba(242, 54, 69, 0.25);

```


### `dashboard/templates/index.html.backup`

```backup

<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>GOLD24-7 — Real-Time Research & Autonomous Trading Cockpit</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-dark: #07090e;
      --surface-1: #0f1420;
      --surface-2: #161d2d;
      --surface-3: #1e283d;
      --border-subtle: rgba(255, 255, 255, 0.08);
      --border-active: rgba(0, 210, 255, 0.4);
      --text-main: #f3f6fc;
      --text-muted: #8b9bb4;
      --text-dim: #54647e;
      --accent-gold: #f5a623;
      --accent-gold-glow: rgba(245, 166, 35, 0.25);
      --accent-cyan: #00d2ff;
      --accent-cyan-glow: rgba(0, 210, 255, 0.25);
      --accent-green: #00e676;
      --accent-green-glow: rgba(0, 230, 118, 0.25);
      --accent-red: #ff3366;
      --accent-red-glow: rgba(255, 51, 102, 0.25);
      --accent-purple: #a855f7;
      --accent-purple-glow: rgba(168, 85, 247, 0.25);

```


### `journal/analytics/performance_engine.py`

```py

"""
Performance Engine: Quantitative analytics, win/loss attribution,
and error classification for research trades.
"""

from typing import List, Dict, Any, Optional
import numpy as np
from core.models.trade import PaperPosition


from journal.analytics.r_multiple import RMultipleAnalyzer


class PerformanceEngine:
    """
    Computes institutional performance metrics across closed paper trades.
    """

    @staticmethod
    def calculate_metrics(positions: List[PaperPosition], initial_balance: float = 10000.0) -> Dict[str, Any]:
        if not positions:
            base_metrics = {
                "total_trades": 0,
                "win_rate_pct": 0.0,
                "profit_factor": 1.0,
                "sharpe_ratio": 0.0,
                "max_drawdown_pct": 0.0,
                "total_net_pnl": 0.0,
                "average_trade_pnl": 0.0,
                "expectancy": 0.0,

```


### `journal/analytics/r_multiple.py`

```py

"""
R-Multiple Analytics Engine: Computes standardized risk-unit (R) metrics,
expectancy, drawdown in R, win/loss streaks, long/short symmetry, and regime breakdowns.
"""

from typing import List, Dict, Any, Optional
import numpy as np
from core.models.trade import PaperPosition, PositionSide


class RMultipleAnalyzer:
    """
    Standardizes performance analysis using R-multiples where 1R is the initial risk unit.
    """

    @staticmethod
    def calculate_trade_r(position: PaperPosition) -> float:
        """
        Calculate realized R for a single closed position.
        1R = abs(entry - stop_loss) * lots * contract_multiplier
        """
        multiplier = 100.0 if any(g in position.symbol for g in ["XAU", "GAU", "GOLD"]) else (
            1.0 if any(c in position.symbol for c in ["BTC", "ETH"]) else 100000.0
        )
        initial_risk_dollars = abs(position.entry_price - position.stop_loss) * position.quantity_lots * multiplier
        if initial_risk_dollars <= 0:
            return 0.0

        r_multiple = position.realized_pnl / initial_risk_dollars
        return round(float(r_multiple), 4)

```


### `journal/ingestion/otw_journal_sync.py`

```py

"""
OpenTraderWorld Journal Ingestion: Ingests paper trades and simulation signals
directly into the local OpenTraderWorld PostgreSQL database and journal ledger.
"""

from typing import Optional, Dict, Any, List
import uuid
import json
import psycopg2
from psycopg2.extras import Json
from datetime import datetime, timezone
import logging

from core.models.trade import PaperPosition, PositionSide
from core.configuration.config import config

logger = logging.getLogger(__name__)


class OTWJournalIngestion:
    """
    Synchronizes paper trade executions and Hermes coaching feedback
    into OpenTraderWorld's institutional trading journal tables.
    """

    def __init__(
        self,
        db_url: Optional[str] = None,
        category_id: Optional[str] = None
    ):

```


### `requirements.txt`

```txt

pydantic>=2.7.0
pydantic-settings>=2.2.0
httpx>=0.27.0
fastapi>=0.111.0
uvicorn>=0.30.0
pytest>=8.2.0
pytest-asyncio>=0.23.0
pandas>=2.2.0
numpy>=1.26.0
psycopg2-binary>=2.9.9
pyyaml>=6.0.1
rich>=13.7.0
python-dotenv>=1.0.1

```


### `tests/contract/test_signal_contract.py`

```py

"""
Contract tests verifying canonical JSON serialization and safety guarantees of SignalContract.
"""

import json
from core.models.signal import (
    SignalContract,
    SignalDirection,
    SetupType,
    MarketRegime,
    VolatilityState,
    LLMInterpretation,
    ValidationResult
)


def test_signal_contract_schema_compliance():
    sig = SignalContract(
        symbol_requested="XAUUSD",
        symbol_resolved="GAUUSD",
        broker_name="XM",
        direction=SignalDirection.BUY,
        setup=SetupType.PULLBACK,
        market_regime=MarketRegime.TRENDING,
        entry_price=2650.50,
        stop_loss=2645.50,
        take_profit=2658.00,
        risk_reward_ratio=1.5,
        risk_points=5.0,
        volatility_state=VolatilityState.NORMAL,

```


### `tests/smoke/test_end_to_end_smoke.py`

```py

"""
Smoke tests for complete end-to-end pipeline.
"""

import pytest
import asyncio
from core.models.candle import Timeframe
from core.market.analyzer import MultiTimeframeMarketAnalyzer
from core.signals.evaluator import SignalEvaluator
from core.validation.validator import DeterministicValidator
from adapters.broker.symbol_resolver import BrokerSymbolResolver
from backtest.datasets.data_generator import MarketDataGenerator
from execution.paper.engine import PaperTradingEngine
from backtest.engine.simulator import BacktestSimulator


def test_full_pipeline_smoke():
    # 1. Resolve Symbol
    resolver = BrokerSymbolResolver(broker="XM")
    res = resolver.resolve("XAUUSD")
    assert res.resolved in ["GOLD#", "GOLD", "GAUUSD", "XAUUSD"]

    # 2. Generate Market Data
    tf_data = MarketDataGenerator.generate_multitimeframe_suite(symbol=res.resolved, start_price=2650.0)
    assert len(tf_data) == 6

    # 3. Analyze Market
    analyzer = MultiTimeframeMarketAnalyzer()
    market_state = analyzer.analyze_full_market(res.resolved, res.broker, tf_data)
    assert market_state.symbol == res.resolved

```


### `tests/unit/test_checklist_and_stochastic.py`

```py

"""
Unit tests for Stochastic, Checklist Engine, and Experts Catalog.
"""

from datetime import datetime, timezone
import pytest
from core.models.candle import Bar, Timeframe
from core.indicators.stochastic import compute_stochastic, compute_ema_alignment, compute_swing_channels
from core.checklist.engine import ChecklistEngine
from core.experts.catalog import get_experts_catalog, get_indicators_catalog, get_strategy_setups_to_test


def test_stochastic_calculation():
    bars = []
    base_time = datetime(2026, 10, 21, 12, 0, tzinfo=timezone.utc)
    for i in range(30):
        price = 4100.0 + (i % 5) * 2.0
        bars.append(Bar(
            timestamp=base_time,
            open=price,
            high=price + 2.0,
            low=price - 1.0,
            close=price + 1.0,
            volume=100.0,
            timeframe=Timeframe.M1,
            shift=1
        ))

    stoch = compute_stochastic(bars, k_period=14, d_period=3, slowing=3)
    assert "k" in stoch

```


### `tests/unit/test_indicators.py`

```py

"""
Unit tests for deterministic indicators: Relative ATR, S&R zones, and moving averages.
"""

import pytest
from datetime import datetime, timezone, timedelta
from core.models.candle import Bar, Timeframe, BarShift
from core.models.indicators import VolatilityState, TrendDirection
from core.models.zones import ZoneType
from core.indicators.volatility import VolatilityEngine
from core.indicators.zones import SupportResistanceEngine
from core.indicators.moving_averages import compute_ema, compute_rsi, determine_trend
from backtest.datasets.data_generator import MarketDataGenerator


def test_volatility_engine_relative_atr():
    bars = MarketDataGenerator.generate_bars(symbol="GAUUSD", timeframe=Timeframe.M1, n_bars=150, base_volatility=1.0)
    engine = VolatilityEngine(period=14, lookback_window=100)

    assessment = engine.assess_volatility(bars)
    assert assessment.current_atr > 0
    assert 0.0 <= assessment.percentile <= 100.0
    assert assessment.state in [
        VolatilityState.VERY_LOW,
        VolatilityState.LOW,
        VolatilityState.NORMAL,
        VolatilityState.HIGH,
        VolatilityState.EXTREME,
    ]
    # Ratio to historical mean should be finite and positive

```


### `tests/unit/test_paper_engine.py`

```py

"""
Unit tests for PaperTradingEngine: lot sizing, simulated execution,
and bracket TP/SL hit handling.
"""

import pytest
from core.models.signal import SignalContract, SignalDirection, SetupType, VolatilityState
from core.models.trade import PositionSide, TradeStatus
from execution.paper.engine import PaperTradingEngine


def test_lot_size_calculation():
    engine = PaperTradingEngine(initial_balance=10000.0, risk_per_trade_pct=1.0)
    # $10,000 * 1% = $100 risk
    # Stop distance = $10 (1000 ticks on $0.01 tick)
    # 1000 * $1.0 tick value = $1000 loss per 1.0 lot
    # lots = $100 / $1000 = 0.10 lots
    lots = engine.calculate_lots(stop_distance=10.0, tick_size=0.01, tick_value=1.0)
    assert lots == 0.10


def test_paper_execution_and_tp_hit():
    engine = PaperTradingEngine(initial_balance=10000.0, risk_per_trade_pct=1.0, slippage_points=1.0)

    sig = SignalContract(
        symbol_requested="XAUUSD",
        symbol_resolved="GAUUSD",
        direction=SignalDirection.BUY,
        setup=SetupType.PULLBACK,
        entry_price=2650.0,

```


### `tests/unit/test_research_validation.py`

```py

"""
Comprehensive Unit & Regression Tests for Phase 2 Strategy Validation:
Verifies:
1. Strict look-ahead prevention and shift=1 completed bar semantics
2. Candidate setup journaling and NO_TRADE counterfactual evaluation
3. Institutional R-multiple analytics (expectancy, drawdown, streaks)
4. Long (BUY) vs. Short (SELL) directional symmetry
5. Walk-forward non-overlapping window partitioning
6. Live execution adapter blocking (LiveExecutionForbiddenError)
"""

import pytest
from datetime import datetime, timezone, timedelta
from core.models.candle import Bar, Timeframe, BarShift
from core.models.signal import SignalContract, SignalDirection, SetupType, MarketRegime
from core.models.candidate import CandidateSetup, DecisionType, CounterfactualOutcome
from core.models.trade import PaperPosition, PositionSide, TradeStatus
from core.validation.validator import DeterministicValidator
from execution.live_disabled.live_blocker import LiveBrokerAdapterDisabled, LiveExecutionForbiddenError
from journal.analytics.r_multiple import RMultipleAnalyzer
from backtest.engine.simulator import BacktestSimulator, HermesAblationMode
from backtest.walk_forward.validator import WalkForwardValidator
from backtest.datasets.regimes import RegimeDatasetGenerator, MarketRegimeType


def test_lookahead_prevention_and_shift_indexing():
    """Ensure multi-timeframe slicing never exposes future data and strictly marks forming vs completed."""
    tf_data = RegimeDatasetGenerator.generate_multitimeframe_suite(
        MarketRegimeType.BULLISH, "GAUUSD", seed=10
    )

```


### `tests/unit/test_symbol_resolver.py`

```py

"""
Unit tests for Broker Symbol Resolver.
Verifies broker abstraction across XAUUSD, GAUUSD, BTCUSD, and ETHUSD.
"""

import pytest
from adapters.broker.symbol_resolver import BrokerSymbolResolver


def test_resolver_xm_defaults():
    resolver = BrokerSymbolResolver(broker="XM")

    # XAUUSD on XM resolves to GAUUSD
    res_gold = resolver.resolve("XAUUSD")
    assert res_gold.requested == "XAUUSD"
    assert res_gold.resolved in ["GOLD#", "GOLD", "GAUUSD", "XAUUSD"]
    assert res_gold.broker == "XM"
    assert res_gold.digits == 2
    assert res_gold.point == 0.01

    # BTCUSD on XM
    res_btc = resolver.resolve("BTCUSD")
    assert res_btc.requested == "BTCUSD"
    assert res_btc.resolved in ["BTCUSD#", "BTCUSD", "BTCUSD.m", "BITCOIN"]
    assert res_btc.digits == 2


def test_resolver_live_cache_matching():
    live_broker_universe = ["GAUUSD", "BTCUSD.m", "ETHUSD.m", "EURUSD_i"]
    resolver = BrokerSymbolResolver(broker="XM", active_mt5_symbols=live_broker_universe)

```


### `tests/unit/test_validator_and_safety.py`

```py

"""
Unit tests for DeterministicValidator, Safety Guards, and Live Execution Blocker.
"""

import pytest
from core.models.signal import SignalContract, SignalDirection, SetupType, VolatilityState
from core.validation.validator import DeterministicValidator
from execution.live_disabled.live_blocker import LiveBrokerAdapterDisabled, LiveExecutionForbiddenError
from execution.safety.circuit_breaker import CircuitBreaker


def test_live_execution_blocker_fatal_exception():
    blocker = LiveBrokerAdapterDisabled()
    with pytest.raises(LiveExecutionForbiddenError) as exc_info:
        blocker.order_send()
    assert "Live order execution is permanently disabled" in str(exc_info.value)

    with pytest.raises(LiveExecutionForbiddenError):
        blocker.buy()

    with pytest.raises(LiveExecutionForbiddenError):
        blocker.sell()


def test_validator_rejects_live_environment():
    validator = DeterministicValidator()
    # Contract pretending to be live
    sig = SignalContract(
        symbol_requested="XAUUSD",
        symbol_resolved="GAUUSD",

```
