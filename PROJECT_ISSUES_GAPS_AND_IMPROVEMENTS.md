# Agentic Trader: Comprehensive System Audit, Issues, Gaps, and Modernization Roadmap

## Current-code resolution review — 24 October 2026

The original audit below describes a **0.14.0 historical baseline**. The checked-out
application is **0.19.0**, plus the fixes recorded here. Absolute absence claims,
old line numbers, reported workloads/timeouts and historical test totals below must
not be read as verified measurements of the current implementation. This review
checked the named code paths and retained the original report for traceability.

**Fixed** means the named concrete defect was addressed; **partial** identifies both
implemented protection and remaining work; **already exists** corrects an obsolete
absence claim; **deferred** means the capability remains unavailable. These labels
do not certify broker, market, operating-system or device acceptance.

| Finding | Current disposition and evidence | Remaining boundary |
|---|---|---|
| **3.1 Tick writes** | **Partial — fixed per-quote commit amplification for manual-feed frames.** [`PaperBroker.ingest_batch`](src/trading_agent/execution/paper_broker.py) runs every ordered quote's risk/fill logic inside one transaction; [`SetupService.connect`](src/trading_agent/api/setup.py) consumes the decoded batch callback. [`test_quote_batches.py`](tests/unit/test_quote_batches.py) independently compares persisted state with sequential execution and checks rollback. | Every accepted quote and financial event remains durable; no lossy one-second cache was introduced. Single-packet frames and the dedicated `PaperService` per-quote runtime retain their existing cadence. WAL growth and sustained throughput still need workload measurements. |
| **3.2 Read/write contention** | **Partial.** [`Database.read_snapshot`](src/trading_agent/persistence/database.py) opens a separate query-only read connection and consistent WAL transaction. Account snapshots, console, orders, readiness and proposal-alert reads use it; [`test_database_snapshots.py`](tests/unit/test_database_snapshots.py) checks committed visibility during a writer and write rejection. | No read pool or independent engine was added. Views that combine memory and persisted authority still require the engine lock; other status/preparation paths retain their existing locks/transactions. This does not establish a latency/504 acceptance result. |
| **3.3 Ten-symbol transport ceiling** | **Fixed for configurable full-depth feeds.** [`Settings.stream_limit`](src/trading_agent/settings.py) accepts 1–3,000, default 10. [`QuoteStream`](src/trading_agent/broker/readonly_kite.py), setup and `PaperFeed` use that ceiling, 500-token subscription batches and larger bounded frames. The [fifty-symbol functional test](tests/functional/test_stream_capacity.py) independently checks stored quotes and 1,500 candles. | Full-depth NSE equity mode only; no LTP tier or runtime universe hot-swap. The desk's reviewed ranked shortlist remains ten. The protocol ceiling is not proof of 3,000-stock local throughput; historical reads and freshness gates remain limiting. See [feed usage](docs/paper-feed.md). |
| **3.4 Process failure and recovery** | **Partial — existing containment corrected.** [`QuoteStream._run`](src/trading_agent/broker/readonly_kite.py) already catches parse/control/callback failures, disconnects and performs bounded retries; a malformed frame does not inherently terminate the API process. The [watchdog](src/trading_agent/api/app.py) latches execution faults. | One process still owns account writes. Worker/IPC migration and automatic clearing of accounting/runtime faults are deferred. Recovered transport never authorizes rearming; fault investigation remains required. |
| **3.5 Configuration rewrite** | **Fixed.** [`SetupService._persist_config`](src/trading_agent/api/setup.py) uses `tomlkit` document mutation, validates the complete proposed settings and financial identity, then uses the existing private temporary-file/fsync/replace writer. [Setup unit tests](tests/unit/test_setup.py) cover comments, structured TOML and replacement failure. | External policy edits are refused until reviewed restart. Invalid TOML is not repaired or partially installed. See [setup recovery](docs/ui-setup.md). |
| **3.6 POSIX-only ownership** | **Fixed abstraction; platform acceptance partial.** The shared [`lock_exclusive`](src/trading_agent/persistence/locking.py) selects POSIX `flock` or Windows nonblocking first-byte `msvcrt.locking`; database, service and auxiliary ownership sites use it. [Lock tests](tests/unit/test_locking.py) cover contention and the Windows adapter. | Windows adapter tests use a simulated module on this host. Full native-Windows deployment, launch scripts, filesystem permissions and device behavior remain unverified. |
| **4.1 Short strategy horizon** | **Partial.** Legacy [`DailyStrategy`](src/trading_agent/daily_execution/contracts.py) still defaults to 20 holding sessions and fixed brackets. [`PolicyParameters`](src/trading_agent/investment_research/policy.py), immutable drafts and [`policy_schedule`](src/trading_agent/investment_research/policy_schedule.py) already represent months/years and monthly/quarterly review previews. | Drafts cannot activate a policy, run a backtest or submit an order. Months-to-years execution, fundamental accumulation and trailing stops remain open; existing strategy semantics were preserved. See [draft limits](docs/investment-policy-drafts.md). |
| **4.2 Long-term backtesting absence** | **Already exists, with scope limits.** [`daily_execution.runner.run_daily`](src/trading_agent/daily_execution/runner.py) and `daily-backtest` use a separate long-term policy, recorded quote/depth clocks, delivery costs and reviewed corporate-action/receipt events. [Replay tests](tests/daily_execution/test_execution.py) and [corporate-routing tests](tests/daily_execution/test_corporate_routing.py) verify exact execution. | The older intraday runner intentionally refuses delivery policies. There is no new unified months/years rebalance backtester or automatic dividend reinvestment. Browser replay registration still caps execution at 252 sessions; multi-year execution acceptance remains open. See [daily research execution](docs/daily-execution.md). |
| **4.3 Portfolio construction** | **Partial.** Exact cash/risk/notional sizing remains in [`risk/limits.py`](src/trading_agent/risk/limits.py). Current holdings allocation and sector/weight **draft inputs** already exist in [`portfolio_metrics`](src/trading_agent/investment_research/portfolio_metrics.py) and [`PolicyParameters`](src/trading_agent/investment_research/policy.py). | Draft limits are not enforced portfolio policy. ERC/volatility-target sizing, sector/correlation admission, target-weight rebalance planning and execution remain unimplemented. Current allocation is descriptive, not a rebalance recommendation; see [allocation limits](docs/portfolio-analytics.md). |
| **4.4 Real OMS/EMS** | **Deferred by the current product boundary.** [`RestrictedKiteHTTP`](src/trading_agent/broker/readonly_kite.py) retains its explicit read allowlist; virtual order/fill recovery already exists in [`PaperBroker`](src/trading_agent/execution/paper_broker.py). | No live placement, margin checks, postback reconciliation or real-money gateway was added. `improvements.txt` explicitly requires paper-only execution during modernization; the roadmap is not authorization to enable it. |
| **5.1 Fundamentals** | **Deferred.** [`series_snapshot`](src/trading_agent/investment_research/series.py) and the analysis API explicitly return unavailable fundamentals with `LICENSED_SOURCE_NOT_CONFIGURED`; missing values are not zero. | No company-financial schema, licensed provider integration or fundamental screen exists. It requires reviewed source/licensing, publication/availability clocks and parsing tests. |
| **5.2 Raw prices and adjustments** | **Already exists for investment research.** [`series.py`](src/trading_agent/investment_research/series.py) causally adjusts all OHLC and inverse volume for known share changes, resets gaps and aggregates weekly/monthly periods. [`/api/research/series`](src/trading_agent/api/analysis.py) supplies the current research chart; [series tests](tests/unit/test_investment_series.py) verify split/basis timing and aggregation. | The legacy `/api/analysis` raw view remains explicitly labelled. Cash dividends affect a separate analytical gross index, not adjusted OHLC or executable prices. Missing action/calendar evidence is excluded, never inferred; no source-accuracy certification is claimed. |
| **5.3 Daily login friction** | **Deferred automation; existing flow improved previously.** [Setup](src/trading_agent/api/setup.py) uses official token exchange and nonce-bound callback capture, with manual login/2FA remaining at Zerodha. | No headless login, password/TOTP storage or browser-login automation was introduced. `improvements.txt` requires the official API rather than browser automation. Expired sessions require an explicit new supported login. |
| **6.1 Iframes** | **Partial.** The iframe shell remains. [`workspace-bridge.js`](src/trading_agent/api/static/workspace-bridge.js) validates both message origin and parent source; [`dialogs.js`](src/trading_agent/api/static/dialogs.js) already manages parent-viewport confirmation geometry and focus/navigation lifecycle. | No SPA/framework migration was made. Page context can still be rebuilt across surfaces. The historical blanket token-leak assertion is not established by the reviewed origin/source-checked bridge alone; an actual exploit would need separate evidence. |
| **6.2 Polling** | **Deferred push transport.** [`desk.js`](src/trading_agent/api/static/desk.js), dashboard and workspace retain bounded polling and stale/error presentation. The new lightweight alert read avoids using full desk refresh to discover proposals. | No SSE/WebSocket UI push was added. Polling, browser throttling and network latency still delay observations; no instantaneous delivery claim. |
| **6.3 Chart interaction** | **Partial; absence claims corrected.** [`analysis.js`](src/trading_agent/api/static/analysis.js) already renders volume, SMA overlays and the daily/weekly/monthly investment view, with exact accessible tables and indicator availability. | Zoom/pan/crosshair, oscillator subcharts and execution markers remain unavailable. No chart library migration was added; [investment research](docs/investment-research.md) documents saved-data limits. |
| **6.4 Proposal expiry alerts** | **Partial — implemented workspace alerts.** [`/api/desk/alerts`](src/trading_agent/desk/api.py) reads bounded persisted metadata without expiring/approving proposals. [`workspace.js`](src/trading_agent/api/static/workspace.js) shows a cross-section countdown/banner, pending-count title and opt-in desktop notifications, with stale/error and lock cleanup. [Workspace UI tests](tests/ui/workspace.test.cjs) cover alert lifecycle. | Checks require the unlocked workspace to remain open; browser sleep/permission/platform restrictions can prevent timely notifications. No audio chime, service-worker push or background delivery guarantee. Alerts confer no trade authority and cannot extend expiry. |
| **6.5 Cognitive overload** | **Already partially improved.** The [workspace shell](src/trading_agent/api/static/workspace.html) and [setup](src/trading_agent/api/static/setup.html) already use prominent state/next-action cards, progressive step disclosure and details for explanations; [`desk.html`](src/trading_agent/api/static/desk.html) leads with portfolio/readiness values. | Beginner usability and physical mobile/desktop acceptance are not established merely by automated accessibility checks. No complete UX replacement was made in this fix. |
| **6.6 Raw reason codes** | **Fixed for the cited known blockers.** [`desk.js`](src/trading_agent/api/static/desk.js) maps calendar, price-basis, shortlist and quote/candle-gap reasons to actionable language, preserving safe rendering and diagnostic fallback. [Desk UI tests](tests/ui/desk.test.cjs) exercise the guidance. | Unknown future codes still receive readable fallback text; messages do not bypass server gates or claim unavailable review actions succeeded. |
| **7.1 Plaintext broker secrets** | **Deferred credential-store migration.** [`SetupService`](src/trading_agent/api/setup.py) retains private sidecar storage, hides secret/access-token values from responses and rejects nonprivate/symlink sidecars. Config/secret writes use atomic replacement. | File permissions are not encryption. Keychain/Secret Service or passphrase-key lifecycle integration, migration/recovery and native-platform tests remain open. Backups and local account access still require protection. |
| **7.2 Memory-only operator token** | **Deferred authentication redesign.** [`workspace.js`](src/trading_agent/api/static/workspace.js) deliberately keeps bearer authority in memory and clears it on lock; [bridge checks](src/trading_agent/api/static/workspace-bridge.js) restrict token delivery. | Reload/reopen still requires unlock. No persistent browser storage, cookie session, inactivity-session service or TLS deployment was added; do not describe this as fixed persistence. |
| **7.3 Circuit-band fills** | **Partial existing liquidity protection; daily bands deferred.** [`_parse_binary`](src/trading_agent/broker/readonly_kite.py) discards empty-sided books and invalidates prior execution depth; [`PaperBroker`](src/trading_agent/execution/paper_broker.py) still requires fresh quotes and observed depth. | No reviewed daily upper/lower circuit source or explicit band gating exists. Available depth does not prove real exchange fillability; simulated fills remain subject to stated limitations. |
| **8.1 Test totals** | **Already exists; historical counts superseded.** Current suites include execution/accounting, [annual performance contracts](tests/unit/test_investment_performance.py), causal adjusted series, SIP authority and the new batching/read/config/locking/alerts tests. | The original 1,248/193 totals are historical audit statements. Actual tests run for this change are recorded in [CHANGELOG](docs/CHANGELOG.md) and the [implementation plan](docs/implementation-plan.md); they are not broker/device acceptance. |
| **8.2 Coverage gaps** | **Partial.** Existing tests already check annual performance, split/dividend receipts, future-prefix invariance and SIP idempotency; the blanket claim that only short paths are tested is obsolete. | No integrated 3–5-year multi-action/reinvestment execution acceptance was established. Fundamental-provider and real-OMS rejection tests remain absent because those components are unimplemented; simulated core tests cannot substitute for them. |

**Persistence decision:** complete quote events are required by
[`corporate_actions.accounting`](src/trading_agent/corporate_actions/accounting.py)
to reject corporate adjustments that cross accepted ex-date observations, and by
[`backtesting.export`](src/trading_agent/backtesting/export.py) to preserve causal
quote availability and replay evidence. Throttling away those events would change
financial authority. Frame batching reduces commit overhead while preserving their
sequence, immediate durability, per-quote risk checks and fail-closed rollback.

**Capabilities outside the numbered findings:** reviewed cash-budget additions and
explicit-date SIP templates already exist in [`portfolio`](src/trading_agent/portfolio/service.py)
and [their usage guide](docs/portfolio-contributions.md). Every due occurrence still
requires a fresh preview and separate confirmation; there is no scheduler or cash
injection. Policy draft/review-date planning is implemented, while target-weight
rebalance proposals/execution and shared-capital coordination remain future work.
An unresolved sector-weight draft or review calendar must never be represented as
an implemented portfolio-construction engine.

## Historical audit — 0.14.0 baseline

The following original findings and modernization roadmap are retained as historical
input. The current-code matrix above takes precedence where it corrects them.

**Audit Date:** 24 October 2026  
**Audited Target:** `/Users/shanmukhan/Developer/repo/agentic-trader`  
**Historical Baseline:** Version `0.14.0` (Git HEAD `f03ba7b`)  
**Scope:** Deep-dive repository audit across Architecture, Broker Connectivity, Market Data, Strategy & Investment Models, Risk Management, Frontend UI/UX, Testing, and Security.  
**Reference Directives:** `improvements.txt`, `AGENTS.md`, and `docs/implementation-plan.md`.

---

## 1. Executive Summary & Context

The **Agentic Trader** platform is an algorithmic equity trading system developed for the Indian National Stock Exchange (NSE). The codebase is a modular Python monolith (Python 3.13) with a FastAPI backend and a vanilla JavaScript frontend. 

The application currently operates as a **supervised paper trading and causal research platform**. It incorporates rigorous financial math (exact Python `Decimal` arithmetic, integer share quantities, and statutory transaction fee modeling) and conservative fail-safe mechanisms (single-process file locking via `fcntl.flock`, transactional SQLite with write-ahead logging (WAL), and kill-switch facilities).

### The Modernization Imperative (`improvements.txt`)
Under the V2 modernization mandate in `improvements.txt`, the application's primary mission is shifting from a short-holding-period paper engine toward a **beginner-friendly, reliable, and well-tested long-term stock investment and automated paper-trading platform** (holding periods of months to years), with eventual support for controlled live execution via Zerodha Kite Connect. 

Existing working safeguards, audit trails, and causal boundaries must be preserved, but major structural gaps across backend concurrency, data modeling, strategy horizon, and frontend user experience prevent the platform from achieving its long-term investment goals.

---

## 2. Architecture & Technology Stack Inventory

| Component / Layer | Current Implementation | Source Evidence | Architectural Assessment & Limits |
| :--- | :--- | :--- | :--- |
| **Language & Runtime** | Python `>=3.13,<3.14`, Hatchling build system, `uv` lockfile | [`pyproject.toml:1`](file:///Users/shanmukhan/Developer/repo/agentic-trader/pyproject.toml#L1-L25) | Modern runtime; strictly single-process local deployment. |
| **Backend Framework** | FastAPI (ASGI), Pydantic v2 validation, Uvicorn | [`api/app.py:27`](file:///Users/shanmukhan/Developer/repo/agentic-trader/src/trading_agent/api/app.py#L27-L45) | Synchronous and asynchronous mix; threadpool offloading. |
| **Database & Persistence** | SQLite 3 (WAL mode, `synchronous=FULL`, foreign keys enabled) | [`persistence/database.py:91`](file:///Users/shanmukhan/Developer/repo/agentic-trader/src/trading_agent/persistence/database.py#L91-L155) | High durability; severe write amplification on incoming market ticks. |
| **Concurrency & Locking** | Reentrant in-process lock (`threading.RLock`) + SQLite `BEGIN IMMEDIATE` + POSIX `fcntl.flock` | [`persistence/database.py:95`](file:///Users/shanmukhan/Developer/repo/agentic-trader/src/trading_agent/persistence/database.py#L95-L101) | Single-writer bottleneck; POSIX-only (incompatible with native Windows). |
| **Broker Connectivity** | Custom read-only HTTP client (`RestrictedKiteHTTP`) & binary WebSocket client (`QuoteStream`) | [`broker/readonly_kite.py:50`](file:///Users/shanmukhan/Developer/repo/agentic-trader/src/trading_agent/broker/readonly_kite.py#L50-L105) | Read-only by design; strictly blocks live order routes; 10-token hard cap. |
| **Frontend Architecture** | Shell container (`workspace.html`) hosting sub-views in an `<iframe>` over `postMessage` | [`api/static/workspace.html:45`](file:///Users/shanmukhan/Developer/repo/agentic-trader/src/trading_agent/api/static/workspace.html#L45) | Legacy micro-frontend antipattern; modal clipping, scroll jitter, token leaks. |
| **Client Transport** | Client-side HTTP polling (every 3s on Dashboard, 5s on Desk) | [`api/static/desk.js:119`](file:///Users/shanmukhan/Developer/repo/agentic-trader/src/trading_agent/api/static/desk.js#L119) | High request overhead, latency lag, lack of real-time push. |
| **Visualization** | Hand-rolled inline SVG coordinate rendering | [`api/static/analysis.js:45`](file:///Users/shanmukhan/Developer/repo/agentic-trader/src/trading_agent/api/static/analysis.js#L45-L67) | No zoom, no pan, no crosshair, no volume profile; raw unadjusted prices. |
| **Testing Suite** | Pytest (Python) + Node test runner (UI JavaScript) | `tests/` (1248 Pytest, 193 Node tests) | All tests pass, but major gaps exist in long-term backtesting & live simulation. |

---

## 3. Critical Backend & Architectural Issues

### 3.1 Tick Ingestion Write Amplification & Disk Thrashing
- **File:** [`src/trading_agent/execution/paper_broker.py:753-785`](file:///Users/shanmukhan/Developer/repo/agentic-trader/src/trading_agent/execution/paper_broker.py#L753-L785)
- **Problem:** Every incoming quote packet from Zerodha's WebSocket triggers an exclusive SQLite transaction (`BEGIN IMMEDIATE`):
  ```python
  tx.execute(
      "INSERT INTO quotes VALUES (?,?,?) ON CONFLICT(symbol) DO UPDATE SET "
      "time=excluded.time,payload=excluded.payload",
      (quote.symbol, stamp(quote.exchange_time), quote.model_dump_json()),
  )
  self.db.event(tx, stamp(now), "quote", quote.symbol, quote.model_dump(mode="json"))
  ```
  Because the database is configured with `PRAGMA synchronous=FULL` ([`database.py:117`](file:///Users/shanmukhan/Developer/repo/agentic-trader/src/trading_agent/persistence/database.py#L117)), each transaction issues a blocking `fsync()` system call to flush WAL frames to disk.
- **Impact:** During active market hours with 10 subscribed liquid stocks, quote feeds emit 50 to 200 ticks per second. Writing each tick to SQLite and appending an audit event causes severe I/O thrashing, rapid WAL growth, and CPU spikes.
- **Improvement:** Decouple tick ingestion from SQLite persistence using an in-memory quote ring buffer or Redis/in-memory cache. Ticks should evaluate pending bracket orders in memory; quote snapshots should be flushed to disk periodically (e.g., 1-second throttle or on significant price changes) rather than on every raw tick.

### 3.2 Lock Contention on Global Re-entrant Locks
- **File:** [`src/trading_agent/execution/paper_broker.py:739`](file:///Users/shanmukhan/Developer/repo/agentic-trader/src/trading_agent/execution/paper_broker.py#L739), [`src/trading_agent/persistence/database.py:156`](file:///Users/shanmukhan/Developer/repo/agentic-trader/src/trading_agent/persistence/database.py#L156)
- **Problem:** All operations—quote ingestion, watchdog checks, order placement, position reconciliation, and API status queries (`/api/paper/status`, `/api/paper/console`, `/api/desk`)—compete for the same `self.lock = threading.RLock()` and SQLite write lock.
- **Impact:** When the WebSocket thread is processing a burst of ticks, incoming REST requests from the UI hang until the tick transaction commits. Operators experience UI latency spikes and occasional HTTP 504 timeouts.
- **Improvement:** Separate read queries from write transactions. Utilize SQLite WAL's multi-reader capability by maintaining separate read-only connection pools for REST endpoints while reserving a single dedicated writer connection for the execution engine.

### 3.3 Hardcoded 10-Symbol Stream Bottleneck
- **File:** [`src/trading_agent/settings.py:68`](file:///Users/shanmukhan/Developer/repo/agentic-trader/src/trading_agent/settings.py#L68-L71), [`src/trading_agent/broker/readonly_kite.py:405`](file:///Users/shanmukhan/Developer/repo/agentic-trader/src/trading_agent/broker/readonly_kite.py#L405), [`src/trading_agent/broker/readonly_kite.py:343`](file:///Users/shanmukhan/Developer/repo/agentic-trader/src/trading_agent/broker/readonly_kite.py#L343)
- **Problem:** The platform enforces an artificial limit of 10 symbols across multiple layers:
  1. `Settings.validate_policy()` raises `ValueError("provide up to ten distinct positive instrument tokens")` if `len(stream_tokens) > 10`.
  2. `QuoteStream.__init__()` raises `ValueError("stream requires one to ten reviewed instruments")` if `not 1 <= len(self.instruments) <= 10`.
  3. `_parse_binary()` asserts `if count > 10: raise ValueError("unexpected packet count")`.
- **Impact:** Zerodha Kite Connect supports streaming quotes for up to 3,000 instruments simultaneously in binary mode. The platform's 10-symbol hard constraint prevents real-time monitoring of broader market universes (such as Nifty 50, Nifty 100, or Nifty Midcap 150).
- **Improvement:** Parameterize the streaming limit. Remove the artificial `count > 10` assertion in the binary parser, handle dynamic batch subscriptions, and support tiered subscription modes (e.g., full depth for active watchlist, LTP-only for broader universe).

### 3.4 In-Memory Single Process Architecture & SPOF
- **File:** [`src/trading_agent/api/app.py:74-77`](file:///Users/shanmukhan/Developer/repo/agentic-trader/src/trading_agent/api/app.py#L74-L77)
- **Problem:** The background watchdog runs in the main server process. If an unhandled exception occurs in the WebSocket callback, watchdog loop, or SQLite driver:
  ```python
  except Exception:
      engine.faulted = True
      engine.set_connected(False)
      logging.getLogger(__name__).error("watchdog failed; entries blocked")
  ```
  The engine sets `faulted = True`, permanently halts order processing, and blocks all new trades until an operator manually restarts the process.
- **Impact:** While defensive against runaway errors, running the entire platform inside a single Uvicorn process means that an error in market data decoding crashes the entire trading desk and UI server.
- **Improvement:** Decouple market data ingestion, strategy execution, and API presentation into resilient worker processes connected via IPC or message queues (e.g., multiprocessing or lightweight Unix domain sockets).

### 3.5 Fragile Regex-Based Configuration Rewriting
- **File:** [`src/trading_agent/api/setup.py:100-127`](file:///Users/shanmukhan/Developer/repo/agentic-trader/src/trading_agent/api/setup.py#L100-L127)
- **Problem:** `SetupService._persist_config()` mutates `config/paper.toml` on disk by reading the raw file text and applying regular expression replacements (`re.subn(rf"(?m)^{key}\s*=.*$", ...)`).
- **Impact:** Modifying configuration via regex is fragile. It risks corrupting nested TOML tables, mangling comments, or producing invalid TOML syntax if keys appear in multiple sections. If the process is terminated while writing the file, configuration is corrupted.
- **Improvement:** Use a round-trip AST-preserving TOML library (such as `tomlkit`) combined with atomic temporary file swapping (`os.replace`).

### 3.6 POSIX-Only Locking Prevents Windows Deployment
- **File:** [`src/trading_agent/persistence/database.py:98`](file:///Users/shanmukhan/Developer/repo/agentic-trader/src/trading_agent/persistence/database.py#L98), [`src/trading_agent/main.py:603`](file:///Users/shanmukhan/Developer/repo/agentic-trader/src/trading_agent/main.py#L603)
- **Problem:** Single-process ownership relies on Unix `fcntl.flock()`. This call fails immediately with `AttributeError` or `ModuleNotFoundError` on Windows systems.
- **Impact:** The application cannot run natively on Windows without WSL (Windows Subsystem for Linux), limiting adoption for non-technical users.
- **Improvement:** Introduce a cross-platform file locking abstraction (e.g., using `portalocker` or `msvcrt.locking` on Windows).

---

## 4. Trading, Strategy & Execution Gaps

### 4.1 Strategy Horizon Mismatch: 20-Day Momentum vs. Long-Term Investing
- **File:** [`src/trading_agent/daily_execution/contracts.py:40-49`](file:///Users/shanmukhan/Developer/repo/agentic-trader/src/trading_agent/daily_execution/contracts.py#L40-L49), [`src/trading_agent/daily_execution/strategy.py:120-145`](file:///Users/shanmukhan/Developer/repo/agentic-trader/src/trading_agent/daily_execution/strategy.py#L120-L145)
- **Problem:** The platform's only automated daily strategy (`DailyStrategy`) is a short-term momentum model with:
  - 20-session momentum lookback (`momentum_sessions = 20`)
  - 50-session trend filter (`trend_sessions = 50`)
  - Fixed 2% stop-loss (`stop_pct = 2`)
  - Fixed 4% take-profit target (`target_pct = 4`)
  - Strict 20-session maximum holding period (`max_hold_sessions = 20`, capped at 252 in schema)
- **Gap vs. V2 Goal:** `improvements.txt` explicitly prioritizes **holding periods of months to years**. Forcing exits after 20 trading sessions (approximately 1 calendar month) or hitting a tight 4% target is an intraday/swing trading model, not long-term value compounding.
- **Improvement:** 
  1. Implement long-term trend-following and fundamental accumulation policies with flexible multi-month holding horizons.
  2. Implement trailing stops (e.g., ATR-based chandelier stops or moving average trailing stops) instead of fixed 2%/4% hard brackets that prematurely truncate compounding winners.

### 4.2 Complete Absence of Long-Term Backtesting in Execution Engine
- **File:** [`src/trading_agent/backtesting/runner.py:52-53`](file:///Users/shanmukhan/Developer/repo/agentic-trader/src/trading_agent/backtesting/runner.py#L52-L53)
- **Problem:** The primary backtesting runner explicitly prohibits non-intraday backtesting:
  ```python
  if policy.investment_horizon != "intraday":
      raise ValueError("the current rule backtester supports intraday hypotheses only")
  ```
- **Impact:** Users cannot backtest long-term investment strategies over multi-year periods (e.g., 3, 5, or 10 years of NSE data) through the standard backtesting runner. The backtesting UI in `backtesting.html` only runs pre-packaged research jobs.
- **Improvement:** Develop a unified daily/weekly long-term backtesting engine capable of replaying multi-year daily bars, accounting for dividends, stock splits, portfolio rebalancing, and exact statutory delivery charges (STT, DP charges, exchange fees).

### 4.3 Rudimentary Position Sizing & Portfolio Construction
- **File:** [`src/trading_agent/risk/limits.py:9-57`](file:///Users/shanmukhan/Developer/repo/agentic-trader/src/trading_agent/risk/limits.py#L9-L57)
- **Problem:** Position sizing in `size()` is computed via a basic binary search that fits integer quantities within available cash and a fixed risk budget:
  - Upper bound: `min(cash / price, exposure_room / price, position_cap / price, risk_budget / (price - stop_fill))`
- **Gaps:**
  1. **Zero Volatility Parity:** Highly volatile small-cap stocks are allocated the same dollar risk as large-cap blue chips. Sizing does not use Average True Range (ATR) or historical standard deviation.
  2. **No Sector or Correlation Caps:** The engine allows all positions to concentrate in the same industry (e.g., 100% IT or 100% Banking).
  3. **No Target Weight Rebalancing:** No mechanism exists to maintain target portfolio weights (e.g., 5% per stock) or periodically rebalance back to benchmark weights.
- **Improvement:** Implement modern portfolio allocation models: Equal Risk Contribution (ERC), Volatility Target Sizing, and periodic target-weight rebalancing.

### 4.4 Complete Absence of Live Order Management (OMS / EMS)
- **File:** [`src/trading_agent/broker/readonly_kite.py:50-80`](file:///Users/shanmukhan/Developer/repo/agentic-trader/src/trading_agent/broker/readonly_kite.py#L50-L80)
- **Problem:** `RestrictedKiteHTTP` explicitly excludes all order placement and modification routes (`/orders/regular`, `/orders/amo`, `/orders/margins`, `/portfolio/positions`). It only exposes read-only profile and historical candle endpoints.
- **Gap:** The platform is currently 100% paper-only. Supporting "controlled automatic trading through Zerodha Kite Connect" (as required in `improvements.txt`) requires building an entire live execution gateway:
  - Live order state machine (PENDING -> OPEN -> COMPLETE / REJECTED / CANCELLED)
  - Postback webhook receiver or order book polling
  - Zerodha margin calculation pre-flight checks
  - Order amendment and cancellation handlers
  - Broker position vs. internal ledger reconciliation
- **Improvement:** Build a modular `BrokerGateway` interface with an audited `ZerodhaLiveGateway` implementing the full Kite Connect OMS/EMS lifecycle with pre-trade margin verification and order recovery reconciliation.

---

## 5. Market Data, Corporate Actions & Fundamental Analysis Gaps

### 5.1 Complete Absence of Fundamental Data Schema & Ingestion
- **File:** [`src/trading_agent/daily_research/dataset.py:20-50`](file:///Users/shanmukhan/Developer/repo/agentic-trader/src/trading_agent/daily_research/dataset.py#L20-L50), [`src/trading_agent/api/analysis.py:94`](file:///Users/shanmukhan/Developer/repo/agentic-trader/src/trading_agent/api/analysis.py#L94)
- **Problem:** The system has **zero schema, storage, or ingestion pipelines for company financial statements or fundamental metrics**. In `analysis.js`, the fundamentals card displays:
  `"Unavailable · A licensed company-data source is not configured."`
- **Gap vs. V2 Goal:** `improvements.txt` specifies that users must be able to screen and rank stocks using:
  - Market capitalization, Revenue & Earnings growth
  - Profitability metrics (ROE, ROCE, Operating Margin)
  - Debt & leverage (Debt-to-Equity, Interest Coverage)
  - Valuation ratios (P/E, P/B, EV/EBITDA, Dividend Yield)
- **Improvement:** 
  1. Define a strongly typed point-in-time fundamental schema (`CompanyFundamentals`) with quarterly and annual publication timestamps.
  2. Implement an ingestion adapter supporting reliable financial data providers or NSE corporate filing scrapers.
  3. Clearly distinguish unavailable/unreported fundamental data from zero-valued metrics.

### 5.2 Unadjusted Historical Candle Prices Distort Technical Charts
- **File:** [`src/trading_agent/api/analysis.py:61`](file:///Users/shanmukhan/Developer/repo/agentic-trader/src/trading_agent/api/analysis.py#L61)
- **Problem:** Historical daily candles served to the frontend analysis chart are flagged as `"quality": "reviewed_raw_daily"`. Prices are **raw unadjusted closes**.
- **Impact:** When a company executes a stock split (e.g., 1:10 split) or bonus issue, the raw price drops abruptly on the ex-date. On `analysis.html`, this appears as a massive artificial 90% crash. Moving averages (SMA 50, SMA 200) calculated on unadjusted prices become invalid and distorted for months following the split.
- **Improvement:** Provide split- and bonus-adjusted candle series alongside raw series. Historical chart overlays and technical indicators must calculate against corporate-action-adjusted closes.

### 5.3 Manual Daily Broker Re-Authentication Friction
- **File:** [`src/trading_agent/api/setup.py:250-290`](file:///Users/shanmukhan/Developer/repo/agentic-trader/src/trading_agent/api/setup.py#L250-L290)
- **Problem:** Zerodha Kite Connect access tokens expire daily between 06:00 and 07:30 AM IST. Currently, every morning the operator must manually:
  1. Open a browser window to Zerodha's login portal.
  2. Complete username, password, and TOTP 2FA.
  3. Copy the redirected URL containing `request_token`.
  4. Paste the request token into the setup wizard.
- **Impact:** High friction for operators. Unattended server or headless cloud deployments cannot re-establish data feeds without human morning intervention.
- **Improvement:** Implement an optional headless login helper utilizing pyotp (TOTP) and browser automation (or direct Kite session handshake) for automated morning session renewal in secure environments.

---

## 6. Frontend UI/UX Flaws & Usability Gaps

### 6.1 Iframe Micro-Frontend Antipattern
- **File:** [`src/trading_agent/api/static/workspace.html:45`](file:///Users/shanmukhan/Developer/repo/agentic-trader/src/trading_agent/api/static/workspace.html#L45), [`src/trading_agent/api/static/workspace-bridge.js:1-69`](file:///Users/shanmukhan/Developer/repo/agentic-trader/src/trading_agent/api/static/workspace-bridge.js#L1-L69)
- **Problem:** The application shell (`workspace.html`) loads sub-dashboards (`/dashboard`, `/discovery`, `/analysis`, `/strategies`, `/portfolio`, `/setup`) inside an `<iframe>`. The host and child communicate via `window.postMessage`.
- **Flaws & User Friction:**
  1. **Height Calculation Flickering:** The child measures `doc.body.getBoundingClientRect().height` and sends `workspace-height` to resize the parent frame. Expanding accordions, loading tables, or rendering charts cause visible layout stutter and jumpy scrollbars.
  2. **Dialog Clipping:** `<dialog>` modals inside the iframe are constrained to the iframe viewport and cannot properly overlay the parent navigation bar or full browser screen.
  3. **State Loss on Tab Switch:** Switching sidebar tabs updates `iframe.src`, tearing down the previous page's JavaScript context and re-instantiating the DOM from scratch.
  4. **Browser Back/Forward Breakage:** Browsers struggle to synchronize the parent hash (`#portfolio`) with the iframe's internal history stack.
- **Improvement:** Migrate from iframe encapsulation to a modern Single Page Application (SPA) architecture using clean modular components without iframes.

### 6.2 HTTP Polling vs. Real-Time Streaming (SSE / WebSockets)
- **File:** [`src/trading_agent/api/static/desk.js:119`](file:///Users/shanmukhan/Developer/repo/agentic-trader/src/trading_agent/api/static/desk.js#L119), [`src/trading_agent/api/static/dashboard.js:130`](file:///Users/shanmukhan/Developer/repo/agentic-trader/src/trading_agent/api/static/dashboard.js#L130)
- **Problem:** The frontend relies on hardcoded `setInterval()` timers polling the backend every 3 to 5 seconds over HTTP REST.
- **Flaws:**
  - Quote updates, fill confirmations, and risk states are delayed by up to 5 seconds.
  - Generates continuous server CPU load and burns mobile battery.
  - In semi-autonomous approval mode, proposals with a 120-second countdown lose 5 seconds before the operator even sees them.
- **Improvement:** Implement Server-Sent Events (SSE) or a client WebSocket connection from FastAPI to stream price ticks, proposal arrivals, fill notifications, and connection state changes instantaneously.

### 6.3 Missing Professional Interactive Charting
- **File:** [`src/trading_agent/api/static/analysis.js:39-67`](file:///Users/shanmukhan/Developer/repo/agentic-trader/src/trading_agent/api/static/analysis.js#L39-L67)
- **Problem:** Candlestick charts are rendered as fixed SVG lines and rectangles (`W=920, H=420`).
- **Flaws:**
  - No interactive mouse crosshair showing OHLCV coordinates.
  - No pinch-to-zoom or click-and-drag panning.
  - No multi-timeframe toggles (weekly and monthly candles are absent).
  - No indicator sub-charts (RSI and MACD are displayed only as single numerical text values in a table, not as visual oscillating charts).
  - No trade execution markers (no visual markers where paper buys or sells occurred).
- **Improvement:** Integrate a high-performance financial charting library (such as TradingView Lightweight Charts or Canvas OHLC) supporting multi-timeframe zoom/pan, indicator overlays, volume bars, and trade markers.

### 6.4 Silent Expiration of Trade Proposals in Semi-Autonomous Mode
- **File:** [`src/trading_agent/api/static/desk.js:84-89`](file:///Users/shanmukhan/Developer/repo/agentic-trader/src/trading_agent/api/static/desk.js#L84-L89)
- **Problem:** When strategy rules emit a trade proposal awaiting operator approval (`expires_at` in 120s), the notification is only visible if the operator currently has the `#paper` or `#dashboard` tab open and focused.
- **Flaws:** If the operator switches to another application or browser tab, proposals silently expire after 2 minutes. There is no Web Audio chime, no HTML5 desktop notification, and no browser tab title badge (e.g., `"(1) Proposal - Agentic Trader"`).
- **Improvement:** Add audio chimes via Web Audio API, Web Notifications API (desktop push), and favicon/title badges when a trade proposal is awaiting review.

### 6.5 The "Wall of Text" Cognitive Overload
- **File:** [`src/trading_agent/api/static/workspace.html:28-43`](file:///Users/shanmukhan/Developer/repo/agentic-trader/src/trading_agent/api/static/workspace.html#L28-L43), [`src/trading_agent/api/static/setup.html:15-55`](file:///Users/shanmukhan/Developer/repo/agentic-trader/src/trading_agent/api/static/setup.html#L15-L55)
- **Problem:** Dashboard and setup screens present dense, multi-paragraph legal disclaimers, academic operational rules, and procedural essays.
- **Flaws:** In an active trading terminal, critical operational metrics (connection state, account equity, daily P&L, quote freshness) are buried beneath educational text. Beginners are intimidated by wall-of-text explanations rather than guided by visual status cards and progressive disclosure.
- **Improvement:** Redesign screens using visual hierarchy: bold glanceable KPI cards, intuitive color-coded status badges, and contextual popover tooltips for educational explanations.

### 6.6 Cryptic Raw System Error Identifiers
- **File:** [`src/trading_agent/api/static/desk.js:4-11`](file:///Users/shanmukhan/Developer/repo/agentic-trader/src/trading_agent/api/static/desk.js#L4-L11)
- **Problem:** The UI surfaces backend enums directly when preconditions fail:
  - `RESEARCH_CALENDAR_NOT_CURRENT`
  - `LONG_TERM_REVIEW_REQUIRED`
  - `QUOTE_CANDLE_PRICE_GAP`
  - `EXECUTION_SHORTLIST_NOT_REVIEWED`
- **Flaws:** Beginners cannot deduce the corrective action required without reading developer runbooks.
- **Improvement:** Replace raw error codes with actionable, friendly guidance (e.g., replace `LONG_TERM_REVIEW_REQUIRED` with *"Today's market session requires a price-basis confirmation. [Click here to review corporate actions]"*).

---

## 7. Security, Resilience & Safety Audit

### 7.1 Plaintext API Secret Storage on Disk
- **File:** [`src/trading_agent/api/setup.py:97`](file:///Users/shanmukhan/Developer/repo/agentic-trader/src/trading_agent/api/setup.py#L97)
- **Problem:** Kite Connect API secrets and access tokens are written to `<database_path>.kite.json` in unencrypted JSON.
- **Impact:** Although protected by filesystem permissions (`0600`), storing sensitive financial API keys in plaintext on disk creates exposure to local process inspection, backup leaks, or accidental git commits.
- **Improvement:** Encrypt stored broker secrets using AES-256-GCM derived from an operator master passphrase, or integrate with OS-level secure credential stores (macOS Keychain, Linux Secret Service).

### 7.2 In-Memory Operator Token Drop
- **File:** [`src/trading_agent/api/static/workspace.js:10`](file:///Users/shanmukhan/Developer/repo/agentic-trader/src/trading_agent/api/static/workspace.js#L10)
- **Problem:** The operator token (`TRADING_OPERATOR_TOKEN`) is held only in a JavaScript closure variable `token`. 
- **Impact:** Refreshing the browser page, duplicating the tab, or reopening an expired session permanently wipes the token from memory, forcing the operator to re-copy and paste a 32+ character hex token repeatedly.
- **Improvement:** Store the session token in an `HttpOnly`, `SameSite=Strict`, `Secure` session cookie with an explicit inactivity timeout.

### 7.3 Missing Symbol Circuit Band Protections
- **File:** [`src/trading_agent/execution/paper_broker.py:760-779`](file:///Users/shanmukhan/Developer/repo/agentic-trader/src/trading_agent/execution/paper_broker.py#L760-L779)
- **Problem:** While the system checks global portfolio loss limits and per-trade stop losses, it does not check NSE upper/lower circuit limits (price bands).
- **Impact:** If a stock hits a lower circuit limit (where trading halts and bids vanish), simulated paper orders could execute at stale quotes that would be completely unfillable in the real market.
- **Improvement:** Ingest NSE daily circuit limits from Kite Connect and halt simulated order fills when prices touch upper or lower circuit thresholds.

---

## 8. Testing, Verification & Code Quality

### 8.1 Current Test Suite Status
The existing automated test suite is exceptionally rigorous in accounting and causality:
- **Pytest:** 1,248 tests passed in 38.86 seconds (100% pass rate).
- **Ruff:** 0 linting or formatting errors across all source and test files.
- **Mypy:** 0 type errors across all 124 source files under strict type checking.
- **Node UI Tests:** 193 tests passed in 146 ms across 13 test suites.

### 8.2 Missing Test Coverage Areas
1. **Multi-Year Long-Term Backtesting:** Current unit tests only validate up to 20 daily sessions or 5-minute intraday bars. Zero tests validate multi-year compounding, multiple corporate action cycles, or dividend re-investment over 3–5 years.
2. **Fundamental Data Parsing:** No unit tests exist for parsing balance sheets, P/E ratios, or revenue growth rates.
3. **Live Execution Gateway Failure Modes:** No mock tests exist for Kite Connect order placement rejection codes (e.g., insufficient margin, circuit limits, broker downtime).

---

## 9. Comprehensive Prioritized Action Plan & Roadmap

Below is the structured, phased implementation roadmap to modernize Agentic Trader into a world-class long-term investment and paper-trading platform:

```
+---------------------------------------------------------------------------------------------------+
|                                  AGENTIC TRADER MODERNIZATION ROADMAP                             |
+---------------------------------------------------------------------------------------------------+
| PHASE 1: CORE ENGINE & DATA FOUNDATIONS (High Priority)                                           |
|  - In-Memory Quote Cache: Decouple tick ingestion from SQLite fsync writes                       |
|  - Expand Stream Limit: Remove 10-symbol hard constraint in settings and binary decoder           |
|  - Cross-Platform Locking: Replace fcntl.flock with portalocker for Windows compatibility         |
|  - Safe Config Mutations: Replace regex TOML substitution with atomic tomlkit updates            |
+---------------------------------------------------------------------------------------------------+
                                                 |
                                                 v
+---------------------------------------------------------------------------------------------------+
| PHASE 2: LONG-TERM STRATEGY & BACKTESTING ENGINE (High Priority)                                  |
|  - Multi-Year Daily Backtester: Remove intraday-only constraint in backtesting runner             |
|  - Split-Adjusted Historical Data: Provide split/bonus adjusted candle series for charts & models |
|  - Long-Term Strategy Pipeline: Support months-to-years holding periods with trailing stops       |
|  - Dynamic Position Sizing: ATR-weighted volatility parity and portfolio sector caps              |
+---------------------------------------------------------------------------------------------------+
                                                 |
                                                 v
+---------------------------------------------------------------------------------------------------+
| PHASE 3: MODERN FRONTEND SPA & INTERACTIVE CHARTING (Medium Priority)                             |
|  - Eliminate Iframes: Rebuild workspace into a cohesive Single Page Application (SPA)            |
|  - Real-Time Push: Replace HTTP polling (3-5s) with Server-Sent Events (SSE) or WebSockets        |
|  - Interactive Charts: Integrate TradingView Lightweight Charts with zoom, pan, crosshair & volume|
|  - Proposal Alerts: Web Audio chime and desktop notifications for Approval-mode proposals         |
|  - UI/UX Redesign: Clean light fintech theme, glanceable KPI cards, friendly error translations   |
+---------------------------------------------------------------------------------------------------+
                                                 |
                                                 v
+---------------------------------------------------------------------------------------------------+
| PHASE 4: FUNDAMENTAL DATA & PORTFOLIO REBALANCING (Medium Priority)                               |
|  - Fundamental Data Schema: Ingest P/E, P/B, ROE, ROCE, Debt/Equity, Earnings/Revenue growth       |
|  - Long-Term Stock Screener: Multi-factor screening combining fundamentals + price trends         |
|  - Target Portfolio Rebalancing: Multi-stock target weight allocation and rebalance planner       |
|  - Automated SIP Scheduler: Background scheduler for periodic virtual cash investment             |
+---------------------------------------------------------------------------------------------------+
                                                 |
                                                 v
+---------------------------------------------------------------------------------------------------+
| PHASE 5: CONTROLLED LIVE BROKER EXECUTION (Future Phase)                                          |
|  - BrokerGateway Abstraction: Modular interface separating PaperBroker and ZerodhaLiveGateway     |
|  - Live Order Lifecycle: Pre-flight margin checks, order placement, order status reconciliation  |
|  - TOTP Headless Login: Automated morning authentication helper for headless servers              |
|  - Circuit Band Halts: Protection against trading at exchange upper/lower price freeze bands      |
+---------------------------------------------------------------------------------------------------+
```

---

## 10. Traceability Matrix to Repository Documentation

In compliance with repository working rules in [`AGENTS.md`](file:///Users/shanmukhan/Developer/repo/agentic-trader/AGENTS.md):
- **Deferred Intraday Features:** Retained in [`docs/INTRADAY_FUTURE_ROADMAP.md`](file:///Users/shanmukhan/Developer/repo/agentic-trader/docs/INTRADAY_FUTURE_ROADMAP.md).
- **Architecture Inventory & Threat Modeling:** Detailed in [`docs/ARCHITECTURE_AUDIT.md`](file:///Users/shanmukhan/Developer/repo/agentic-trader/docs/ARCHITECTURE_AUDIT.md) and [`docs/threat-model.md`](file:///Users/shanmukhan/Developer/repo/agentic-trader/docs/threat-model.md).
- **Requirements & Gap Details:** Cross-referenced with [`docs/GAP_ANALYSIS.md`](file:///Users/shanmukhan/Developer/repo/agentic-trader/docs/GAP_ANALYSIS.md) and [`docs/UX_AUDIT.md`](file:///Users/shanmukhan/Developer/repo/agentic-trader/docs/UX_AUDIT.md).
- **Operational Procedures:** Detailed in [`docs/how-to-use.md`](file:///Users/shanmukhan/Developer/repo/agentic-trader/docs/how-to-use.md) and [`docs/daily-operator-checklist.md`](file:///Users/shanmukhan/Developer/repo/agentic-trader/docs/daily-operator-checklist.md).
