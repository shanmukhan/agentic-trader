# Deferred intraday roadmap

Audit date: **22 October 2026 (IST)**. Baseline: **0.14.0**, Git
`2d5c208`. This is a Phase 1 planning artifact for
[improvements.txt](../improvements.txt), not authorization to implement new intraday
behavior or enable real execution.

The current modernization prioritizes long-term stock investment over months to
years. Preserve existing intraday code, configurations, standalone CLI workflows
and account identities. Do not change intraday signal, entry/exit, sizing, indicator,
proposal-cap or session semantics unless a critical security or correctness issue
requires a narrowly scoped fix. Any such exception needs documented evidence,
regression tests and explicit disclosure of its impact on existing accounts.
The user's explicit Phase 1 stop still applies: this audit records even confirmed
correctness findings for approval; it does not implement their fixes.
Shared presentation/accessibility corrections may support both horizons while
preserving their financial behavior.

## Current foundation to retain

| Component | Existing behavior / evidence | Boundary |
|---|---|---|
| Completed-candle rules | [strategy/rules.py](../src/trading_agent/strategy/rules.py) implements opening-range breakout and VWAP continuation, completed 5-minute history, session-local state, EMA/ATR/volume/spread filters and bounded proposal counts. [Rule tests](../tests/backtesting/test_rules.py) cover warmup, gaps, invalid/future data and signal caps. | Experimental hypotheses; no claim of expected profit or suitability. A five-minute evaluation interval is not a schedule that guarantees trades. |
| Quote execution and risk | [PaperBroker](../src/trading_agent/execution/paper_broker.py), [settings](../src/trading_agent/settings.py) and [sizing](../src/trading_agent/risk/limits.py) enforce exact paper cash/risk reservations, depth-bound fills, adverse prices, later-quote timing, freshness, kill/loss and session controls. | Market data access is not execution authority. No real broker order transport exists in this pipeline. |
| Causal historical replay | [backtesting](backtesting.md), [runner](../src/trading_agent/backtesting/runner.py) and [runner tests](../tests/backtesting/test_runner.py) use completed candles plus observed quotes, independent accounts and no fabricated terminal liquidation. | Candle-only input cannot reconstruct bid/ask execution or intrabar barrier order. Missing paths remain incomplete. |
| Separate ML research | [ml-research.md](ml-research.md), [splits](../src/trading_agent/ml/splits.py) and [inference](../src/trading_agent/ml/inference.py) provide chronological research, artifact checks and optional later scored replay. | Intraday artifacts/features are distinct from daily delivery models. Model checks add gates and never replace risk. |
| Supervised feed operation | [paper-feed.md](paper-feed.md) documents explicit arming, quality/history readiness, bounded reconnect, disarm/cancel behavior, durable proposal caps and restart binding. | Reconnect, kill reset or a fresh quote does not automatically rearm. Protective exits still need usable later quotes. |
| Audit and accounting | [database reconciliation](../src/trading_agent/persistence/database.py), [desk accounting](../src/trading_agent/desk/accounting.py) and [recovery tests](../tests/integration/test_risk_and_recovery.py) distinguish signals, decisions, orders and fills. | A cancelled proposal can have no order. Changing modes must not silently replay a terminal daily decision or duplicate an existing order. |

The previously implemented Kite whole-second ordering exception is a shared
market-data correctness fix, not a new intraday strategy. It accepts only ordered
live Kite updates with matching identity, whole-second exchange ties and strictly
later receipts; tied updates do not replenish fill liquidity or invent exchange
timestamps. Backward/ambiguous clocks, replay conflicts and volume regression still
fail closed. Preserve [ordering tests](../tests/unit/test_quote_ordering.py) and
[raw-packet workflow tests](../tests/functional/test_live_quote_ordering.py).

### Confirmed remaining correctness finding for review

The supervised [PaperFeed.on_quote](../src/trading_agent/paper/runtime.py) still
uses full-object inequality after `engine.ingest` returns false. An otherwise
identical Kite observation with a later `received_time` is an engine no-op but is
different as a full Quote object, so the runtime records `QUOTE_QUALITY`, clears
that symbol's latest quote and disarms. The audit's isolated synthetic account
reproduced armed → disarmed without an engine data-quality event; cash stayed
₹25,000 and no orders existed. No genuine broker or operator account was used.

Treat this as a **Medium** correctness/availability finding requiring a narrow
reviewed fix and a regression case, rather than changing the strategy or broadly
ignoring quote rejections. Tests must distinguish harmless unchanged observations,
strictly later valid book updates, stale data, out-of-order/ambiguous clocks,
backward cumulative volume and invalid liquidity. Do not renew freshness, replenish
same-timestamp depth, suppress genuine incidents or automatically rearm. The
architecture audit records the reproduction. No Phase 1 application fix was made.

## Deferred work and prerequisites

| Future work | Technical requirements and dependencies | Principal risk / acceptance requirement | Complexity |
|---|---|---|---|
| Full intraday research/monitoring workspace | Reuse current authenticated read APIs and immutable research artifacts; keep Manual/Approval/supervised authority distinct; display signal/order/fill time and incomplete history. | A polished chart or a connected socket must not imply readiness. Test actual viewport, keyboard focus, stale/empty/error states and confirmation placement. | M/L |
| Broader intraday experiments | Predeclare hypothesis/configuration, holdout and selection protocol; acquire reviewed chronological quote/depth/candle datasets and point-in-time universe; keep gaps and adverse outcomes. | Parameter search and today's survivors can manufacture apparent edge. Require separate unseen-period evaluation and retained failed experiments. | L/XL |
| Execution-quality calibration | Collect permitted genuine quote observations and reference cost schedules; quantify observation gaps, price/depth coverage and adverse slippage scenarios. Keep fill-model assumptions versioned. | Sparse ticks do not show exchange queue position, hidden liquidity or market impact. Do not describe paper fills as broker-accepted execution. | XL plus external evidence |
| Historical cost schedules | Version-effective statutory/broker estimates, rounding and account-class semantics; preserve fee-version identity for existing accounts/replays. | Current observed rates applied across past dates are estimates. Independent reference cases must verify partial-fill and cumulative-fee behavior. | L |
| Operational reliability and diagnostics | Measure reconnect/disarm/recovery with bounded retries; source clocks, usable-quote ages, heartbeat, rejected observations and history coverage; sanitized durable incident reports. | An outage must revoke entry authority before unsafe I/O, never mint liquidity, discard holdings or auto-rearm. Fault injection and restart drills must independently reconcile balances. | L |
| Performance work on supported hardware | Profile complete quote→risk→persist path, bounded history/data queues and lock contention; use actual target device and disk. Preserve deterministic replay and transaction guarantees. | Synthetic microbenchmarks omit network/disk/device load; optimization can reorder events or weaken financial atomicity. Require before/after correctness and genuine device measurements. | M/L |
| Cross-account capital management | Requires the long-term account registry and reviewed capital-allocation authority first; independently seeded virtual accounts remain distinct until an explicit design exists. | Summing independent accounts or label trials double-counts capital. Enforce aggregate pending reservations atomically across accounts if later implemented. | XL |
| Additional indicators or signal types | Separate proposals, versioned causal calculations, completed-input warmup, parameter bounds and independent reference tests. | Added indicators are not evidence of improved returns. Do not alter current defaults, silently reuse daily models or bypass the existing signal cap. | M/L per hypothesis |
| Real execution | **Not part of this roadmap's approved implementation.** Would require a separate user-authorized project, exchange/broker compliance and custody/settlement/order reconciliation design. | All modernization execution stays paper-only; no live API order route, credential scope or automatic authority should be added here. | Separate approval and scope |

## Proposed phases, only after long-term priorities and approval

1. **I0 · Freeze and characterize existing behavior.** Record configuration,
   schemas, hashes, horizon boundaries and reproducible fixture outputs. Run
   intraday unit/integration/CLI/recovery coverage. Catalogue critical defects
   separately; keep ordinary feature requests deferred. Exit: baseline documented,
   no unapproved financial behavior change and no real execution capability.
2. **I1 · Improve observability and read-only presentation.** Expose actual
   readiness, data gaps, authority and distinct proposal/order/fill outcomes through
   existing APIs; validate desktop/mobile interactions. Exit: operators can diagnose
   a blocked or idle strategy without bypassing its controls.
3. **I2 · Establish empirical source and simulation evidence.** Acquire permitted
   point-in-time/quote datasets, review historical costs, predeclare experiments,
   and test held-out periods. Retain incomplete/censored/adverse results. Exit:
   explicit coverage and simulation limits; no claim of reliable profits.
4. **I3 · Run separately authorized supervised paper acceptance.** Use an isolated
   virtual account, explicit arm, observed session calendar, bounded recovery and
   operator-visible incidents. Test disconnect, stale feed, restart, loss/kill,
   partial fills and end-of-session handling. Exit: independent reconciliation and
   documented observed behavior, with live-readiness still false.
5. **I4 · Consider optional new intraday research.** Only if separately prioritized,
   add one versioned hypothesis or capability at a time after the earlier evidence
   gates. Compare using a predeclared method; preserve old configurations/accounts.
   Any eventual real-money project remains a separate authorization boundary.

## Validation and evidence boundaries

This audit inspected the existing intraday tests and documentation; it did not
run a strategy on the operator's account, arm automation, change broker credentials
or place any order. Phase 1 test execution is recorded in
[ARCHITECTURE_AUDIT.md](ARCHITECTURE_AUDIT.md) and
[IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md).

Synthetic lifecycle drills establish deterministic software behavior. Historical
replay establishes results only for its supplied observations and assumptions.
Short read-only broker probes establish only those observed packets and clocks.
Mac timing microbenchmarks do not establish device/network latency, sustained market
reliability, fill realism or investment performance. Future evidence must identify
its source, horizon, account, observation interval and missing coverage, while
keeping all credentials private and execution paper-only.
