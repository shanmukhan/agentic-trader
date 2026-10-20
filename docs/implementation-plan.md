# Implementation plan, enhancements and status

Prepared 20 October 2026; updated 21 October 2026. This is the execution record for the original
[project specification](../zerodha_ai_trading_agent_project_spec.md).

## Implemented scope

The repository delivers Phases 1–3 infrastructure/research and Phase 4 supervised
intraday paper-feed engineering, LT1–LT2 long-term paper mechanics and LT3a daily
research foundations. The paper horizons share transactional risk/execution mechanics. Rules/models
run offline or on explicitly configured dedicated paper accounts. No live adapter, profitability
or compliance readiness is implied. External account creation, entitlement checks
and OS service installation require real credentials/hardware and are not fabricated.

| Original work item | Implementation / evidence |
|---|---|
| Git and environment | `main` initialized; Python 3.13.16 `.venv`; hashed `uv.lock`; ignored secrets/runtime/data |
| Typed config and paper guard | Frozen validated TOML settings; alternate mode/public host rejected |
| Structured diagnostics | Rotating JSON with secret redaction, intent correlation in durable journal |
| Local app and health | FastAPI console, liveness, entry readiness, authenticated private API |
| Read-only broker contract | Restricted transport implementing official profile/catalog/history protocol |
| Manual authentication | Supported browser URL + hidden request-token exchange + private output file |
| Streaming and candles | Strict full-mode NSE decoder, disconnect/reconnect gating, 1m/5m builders, history storage |
| Database and account | Schema v1, WAL FULL, file ownership, atomic journal/materialized state, exactly ₹25k initial cash |
| Risk and execution | Fee/slippage-aware sizing, reservations, fill state machine, loss gates, stop/target/session exits |
| Kill and recovery | Durable switch, explicit operator reset, restart reconciliation/cancellation/requeued exits |
| Tests and quality | Unit, integration, functional CLI/API, replay, security, dependency audit, Ruff, mypy, CI |
| Deployment and recovery | macOS/Pi scripts, launchd/systemd templates, verified backup/restore tests |
| Research foundations | O(1) EMA/VWAP/Wilder ATR; service still rejects unconfigured ML |

## Enhancements and justified changes

1. **Atomic reservations and fills.** Sizing and cash/risk reservation share a writer
   transaction; cash, cost basis, fees, orders, fills and audit events commit together.
   One process owns an account, preventing a second startup from changing active work.
2. **Explicit calendar and time.** There is no baked-in possibly stale holiday list.
   Unknown dates are closed. Session time is IST; storage and epoch decoding are UTC.
   Reviewed early closes take precedence. The empty shipped calendar is intentional.
3. **Conservative research accounting.** Decimal money, tick-aware adverse prices,
   order-cumulative fees, estimated liquidation P&L, residual basis allocation,
   and cost-aware daily capacity extend the illustrative sizing formula.
4. **No false closes.** A stop, kill or watchdog request queues an exit; fresh data
   and actual simulated depth are required for fills. Remaining positions persist.
5. **Restart semantics.** Reconcile durable state first, cancel pre-crash pending
   orders, and request required exits again. This avoids reviving old entry intent.
6. **Configuration and schema safety.** Required metadata cannot silently reseed
   when missing; unknown schema and changed risk policies fail closed. New policy
   experiments use a new account. SQLite defaults remain durable rather than tuned
   to unsafe write modes for benchmark scores.
7. **Dependency exception.** The official SDK installed a vulnerable pinned Autobahn
   stack and a flagged Twisted dependency. It was removed, with no ignored advisory.
   A smaller allowlisted HTTPX/WebSocket implementation follows official broker
   protocols and has a clean re-scan. This also removes order-capable SDK methods
   from runtime. See [threat-model.md](threat-model.md).
8. **Lightweight research path.** Incremental Decimal indicators avoid pandas/NumPy
   startup/memory costs in the hot path. Heavy training dependencies are deferred
   until there is a chronological strategy dataset. TOML uses Python's standard
   parser instead of YAML, reducing dependencies. Public types and artifacts remain
   suitable for adding offline ML in later phases.
9. **Normalized schema.** Candidates, decisions, state transitions and system
   notifications live in the append-only journal; snapshots are transactionally
   derived. A few duplicate tables in the illustrative layout were unnecessary.
10. **Reviewable operations.** No host-wide services, users, firewall rules or broker
    plans were silently provisioned. Templates and instructions make these concrete
    for the operator while preserving this workspace's permissions and credentials.

## Phase 2 delivered — version 0.2.0

| Work item | Implementation / evidence |
|---|---|
| Predeclared rules | ORB and VWAP-continuation, completed 5m data, prior-volume reference, independent symbol/session state |
| Causal features | No active/future candles; missing opening/history disables that session; future-quote prefix-invariance test |
| Execution boundary | Existing fee/slippage/latency/depth risk broker; no candle-close fills or invented OHLC paths |
| Isolated research | New output account; backtests never open the service account; export never runs restart cancellation |
| Provenance | Raw-price manifest, reviewed sessions/sources, chronological typed JSONL, source/config/code hashes and unchanged-input checks |
| Reports | Net metrics, observed drawdown, partial-trade accounting, decisions, equity CSV, journal and incomplete-exposure gates |
| Commands | `research-demo`, `backtest`, `export-research`, and configurable strategy TOML |
| Performance | Constant per-candle work; measured p99 below 0.018 ms on this Mac, excluding input parsing/execution/network |
| Verification | Unit, integration, functional CLI, deterministic/leakage/failure tests; detailed research guide |

Enhancements to the Phase 2 plan:

- Require completed candles and observed quotes; OHLCV alone cannot reconstruct
  executable depth or stop/target ordering, so candle-only runs are refused.
- Even zero-latency experiments require a strictly later exchange quote to fill.
- Preserve positions at dataset exhaustion; disclose pending orders, stale valuations,
  held-position quote gaps and incomplete results instead of fabricating liquidation.
- Label synthetic/mixed/replay provenance explicitly, with one positive and one
  negative synthetic session rather than a profitability demonstration.
- Bound manifest/line reads, reject external/symlinked bundle paths and manual
  candidate events, and leave no loadable manifest after failed exports.
- Preserve source orders during export; disclose historical candle availability,
  fee matching and unavailable connection history as research assumptions.

See [backtesting.md](backtesting.md) for input construction, rules, reports and sample gates.

## Phase 3 delivered — version 0.3.0

| Work item | Implementation / evidence |
|---|---|
| Causal training schema | Twelve finite ordered features, completed-time checks, economic candidate fingerprint, no outcomes in features |
| Execution labels | Independent fee/risk/latency/depth-aware paper trials, time barriers and actual fill interval ends; exclusions retained |
| Provenance | Source manifest/hashes, full strategy/economic settings, label policy, code hash, sample/audit hashes and completion manifest |
| Chronological validation | Whole-session expanding walk-forward blocks, interval purge/embargo, independent later calibration and frozen final holdout |
| Baseline model | Train-only StandardScaler + fixed logistic regression + separate regularized sigmoid calibration; no hyperparameter search |
| Diagnostics/gates | ROC-AUC, Brier/log loss, training-only baseline, reliability/ECE, selected count/net label P&L and strict validation consistency |
| Safe artifacts | Bounded local JSON coefficients/reports, exact dimensions/schema, hash checks, no executable persistence, failed-gate refusal |
| Scored research | Same-availability-time ranking, deterministic ties, later portfolio replay and independent risk/model gate |
| Account continuity | Durable model version/schema marker, missing/changed gate refusal before recovery, idempotency includes vector |
| Lightweight inference | Pure Python twelve-feature math; optional training packages never imported for scoring; Pi setup uses runtime/broker extras |
| Commands/docs | `ml-build`, `ml-train`, `ml-demo`, `backtest --model`, full [ML guide](ml-research.md) and corresponding component updates |
| Verification | Unit/functional/causality/censoring/risk/integrity/determinism tests plus a separate inference/ranking benchmark |

Enhancements to the Phase 3 plan:

1. Label **all standalone feasible candidates**, rather than only trades selected
   by a competing portfolio. Preserve censored/rejected/unfilled/interrupted paths
   separately so missing outcomes never silently become negative labels.
2. Use actual quote-driven paper execution for labels. OHLC paths and forced horizon
   closes are not reconstructed. Label end includes the final liquidation fill,
   allowing delayed outcomes to be purged correctly across split boundaries.
3. Reserve separate calibration blocks in every fold; fitting scalers, base models
   or calibration on evaluation/holdout observations is prohibited.
4. Make model availability follow **final validation plus embargo**, not merely
   coefficient fitting. A historical replay cannot use future approval evidence.
5. Freeze fixed baseline coefficients before final holdout diagnostics, retain
   unsuccessful reports, and check diagnostic consistency again during loading.
6. Export inspectable JSON math rather than pickle/joblib. Keep training optional
   and outside the connected feed process; add measured inference/ranking latency.
7. Keep synthetic test settings separate from real research defaults. An explicit
   offline synthetic override relaxes only provenance and only on synthetic data.
8. Bind vectors to economic candidates and accounts to model identity. Model gates
   add rejection conditions without changing the original risk hash or any limit.

Synthetic end-to-end verification uses sixty training/validation sessions followed
by ten unseen invented sessions. It establishes software behavior only. There is no
empirically accepted market model or live readiness.

## Phase 4 engineering delivered — version 0.4.0

| Work item | Implementation / evidence |
|---|---|
| Supervised feed | Explicit `serve --stream --automate`, authenticated arm/disarm, universe-wide readiness and disarmed startup/restart/session |
| Safe account setup | `paper-init` checks profile/catalog and exclusively creates/binds a new account without conflicting manual model initialization |
| Causal history | Separate paced worker loads full completed current-session 5m data; incomplete/revised/obsolete responses fail and missed signals are not replayed |
| Independent execution | Same fee/depth/latency/sizing/kill broker, controller-bound submissions, durable proposal caps, model age/availability |
| Recovery | Disconnect/staleness cancels buys and disarms; stale holdings queue durable exits, without fake closes or automatic rearming |
| Policy continuity | Runtime/catalog/model/strategy/feed identities and used calendar definitions pinned; changed/removed automation fails before recovery |
| Observability | Recent timing windows, cumulative counts/maxima/exceedances, periodic status and observed per-run drawdown |
| Evidence | Source-preserving `paper-report`, net trades, incidents, clean-run/sample/model/latency gates; external/live flags always false |
| Drills | Synthetic partial fills, disconnect with holdings, silence and unclean pending-entry restart with separate ledgers/reports |
| Performance | Additive event-kind/time index, populated benchmark and test proving history network waits release the execution lock |
| Captured research data | Exports preserve first observed candle/connection clocks; missing clocks and unclocked supervised overrides fail |
| Verification/docs | Unit/concurrency/functional API/CLI tests, CI drills and complete [paper-feed guide](paper-feed.md) |

Enhancements to the Phase 4 plan:

1. Supervised arming replaces resumption of old entry authority after restart or
   reconnect. Protective handling continues independently while entries are disarmed.
2. Authoritative completed historical candles avoid unknown first-bar volume and
   partial-bar/history mixing. Backfill warms features without replaying missed trades.
3. History HTTP/rate pacing stays outside the quote/risk lock. Responses from obsolete
   connections are discarded, the whole universe is required and late signals are skipped.
4. Accounts bind their controller/model before recovery. Durable proposal counts
   survive rewarm/restart; model/rule changes use a new account.
5. Engineering evidence remains separate from empirical acceptance. Reports disclose
   recent-window quantiles, lost crash samples and unresolved exposure. No report can
   authorize live execution.

Actual feed duration, fill calibration, entitlement and Pi reboot/storage/power-loss
drills remain external acceptance work. Synthetic tests deliver the code milestone only.

## Phase 4 acceptance tooling and responsive console — version 0.4.1

The next locally implementable milestone extends acceptance support while actual
broker/device/model evidence remains pending. It does not advance into live execution.

| Work item | Implementation / evidence |
|---|---|
| Responsive operator UI | Packaged HTML/CSS/JS, account cards, readiness reasons, positions, recent orders, details and mobile CSS stacking |
| Consistent bounded view | Authenticated `/api/console`, engine-serialized snapshot, latest 200 orders and at most ten quote rows |
| Operator safety | Lock clears values/token and rejects late requests; stale indicators, serialized actions, explicit arm/reset confirmation, no automatic action retry |
| Local acceptance diagnostic | `preflight [--strict] [--output NEW_PATH]`, read-only WAL-aware accounting/integrity, identity/permission/calendar/disk/runtime checks |
| Evidence integrity | New private JSON/Markdown reports and last-written hash manifest; external/live acceptance always false |
| Deployment patch check | Explicit official SQLite WAL-reset fix branches; actual local runtime SQLite 3.53.1 |
| Validation | 284 Python tests, 13 JavaScript cases, 92% Python coverage; wheel includes and loads all UI assets |
| Usage and external work | Dedicated [console](operator-console.md) and [acceptance](acceptance.md) guides and corresponding component documentation |

Enhancements: diagnose accounts without acquiring write ownership/recovering orders;
keep heavy integrity work out of the feed/UI polling path; bound recent UI history;
retain exact decimal display; distinguish local checks, current session and external
acceptance. CSS supports mobile browsers but small-screen visual/physical-phone
acceptance remains pending because browser tooling did not yield reliable evidence.
Desktop Safari and the isolated virtual kill/reset/lock flow were verified locally.

## Long-term scope extension — LT1 delivered, version 0.5.0

The user extended the project to include long-term investing. This introduces a
separate paper horizon; it does not convert intraday accounts or implement the
original live infrastructure Phase 5. Full usage and explicit limits are in
[long-term.md](long-term.md).

| Work item | Implementation / evidence |
|---|---|
| Separate horizon | `investment_horizon`, dedicated config/database/8001 listener, durable binding and unchanged legacy intraday hash |
| Overnight lifecycle | Holdings survive close/weekend/restart; pending buys expire, requested exits remain latched until closure |
| Independent risk | Existing sizing, cash/depth/tick/latency limits plus durable observed peak/drawdown and gap-preserving daily reference |
| Price-basis integrity | Current-session operator review, previous accepted quote clock, pinned used calendar definitions and persistent corporate-action quarantine |
| Delivery costs | Observed retail NSE delivery schedule, exact partial-order fees, atomic per-symbol/day DP allocation and entry cash buffer |
| Reconstruction | Delivery fees/day markers, fills, review authority, quarantines and requested exits checked against journal/ledger on startup |
| Operator/API | Horizon badge, long-term risk/review panel and confirmed individual full-holding exit, authenticated typed endpoints |
| Evidence/drills | Source-preserving `long-term-report`; invented overnight partial/restart, opening-gap and unadjusted-action scenarios |
| Performance/validation | 328 Python + 17 JavaScript tests, 92% Python coverage; populated long-term p99 0.3288 ms on this Mac, excluding network/Pi |
| Documentation | New detailed long-term guide plus updated original specification, usage, API, risk, architecture, threat, operations, acceptance and tests |

Enhancements to the scope: require a separate account instead of changing intraday
semantics; preserve opening gaps rather than marking the new day's baseline at its
first new price; retain explicit exits across cancelled/restarted residual orders;
charge DP only on actual fills; block unaffordable exit fees without inventing cash;
reject a restarted selected feed that omits a held symbol; quarantine known corporate
actions instead of treating an unadjusted price jump as ordinary market P&L.

## LT2 delivered — reviewed corporate actions, version 0.6.0

| Work item | Implementation / evidence |
|---|---|
| Reviewed inputs | Bounded strict JSON, stable action/batch/receipt IDs, sourced ex-date sessions, explicit chronology and quarantine hash/complete-coverage assertion |
| Share ledger | Increasing splits and bonuses, conservative tick-adjusted protections, original holding identity/cost conservation and affected-order cancellation |
| Fractional handling | Exact rational claim, pro-rata basis rounded down to paise with exact holding residual, unknown valuation retained after whole-share exit, explicit cash-in-lieu receipt |
| Dividend ledger | Frozen gross/deduction/net receivable, nonspendable before payment, exact once-only net cash receipt and separately reported investment income |
| Integrity/recovery | Additive tables, atomic journal/materialized accounting, independent ordered fill/action/receipt reconstruction, cache/basis/protection verification and backup/restart tests |
| Operator workflow | Exclusive offline CLI, current-session review and post-application quote required on resume; existing protective exits retain their latch |
| Reports/console | Schema-2 evidence with claims/batches/quarantine hashes/income, adjusted whole-share metrics and separate console claim summary |
| Demonstration/performance | Invented split→dividend→bonus/fraction→exit→receipt lifecycle and a 2,000-quote populated unpaid-dividend benchmark, p99 0.2564 ms on this Mac |
| Standing requirement | [AGENTS.md](../AGENTS.md) records the user's instruction to update usage and component guides with every feature/workflow change |

Enhancements: apply actions only before the account crosses the first affected
ex-date price/trade basis; never infer a payment, fraction value or settled eligibility;
freeze explicit same-date action order; reject unsupported fraction chains and
reverse/complex issuer events rather than silently losing claims. Full schemas,
commands, retry/failure behavior and exclusions are in [corporate-actions.md](corporate-actions.md).

### Extended long-term roadmap

LT3 is implemented in dependency order: **LT3a delivered in 0.7.0** reviewed completed daily data,
point-in-time membership and total-return-aware causal screening with an accessible
offline research dashboard; **LT3b** quote-executed daily strategy research and
separate chronological ML validation; **LT3c** lot additions/SIP, reviewed rebalance
proposals and aggregate capital coordination. A daily bar cannot establish an
executable fill, and screening statistics cannot approve a model or portfolio.

LT3a delivers bounded streaming daily bundles, explicit period-benefit/availability
evidence, historical inclusion/exclusion/re-entry, consecutive rolling gross-return/
trend/volatility/turnover screening and deterministic candidate ranks. The private
offline dashboard explains statuses/metrics, filters/sorts, missing-data/empty states
and provenance without account/control access. Source/code hashes, mutation checks,
strict validation, invented adverse/gap/exclusion fixtures and unit/functional/UI
tests support review. **420 Python + 23 JavaScript tests, 92% coverage**; 538-bar Mac
analysis p50 **8.0033 ms** including input/validation/hashes. See
[daily-research.md](daily-research.md) for schemas, assumptions and exclusions.

| Milestone | Required implementation / acceptance | Status |
|---|---|---|
| LT1: overnight paper foundations | Lifecycle, delivery costs, reviews, risk, console, evidence and tests | Engineering delivered |
| LT2: corporate actions and cash/share ledger | Reviewed split/bonus/dividend entitlements and effective/payment dates, integral/fractional handling, atomic idempotency, independent reconstruction and recovery | Supported paper engineering delivered; complex actions/tax lots/custody remain excluded |
| LT3: daily research and portfolio management | Completed daily price/total-return data, point-in-time universe, causal strategy/ML validation, SIP/lot additions, rebalancing and cross-account allocation | LT3a delivered; LT3b quote-executed daily strategy research is next; LT3c portfolio mechanics pending |
| LT4: actual read-only holdings and supervised acceptance | Reviewed custody/sellable holdings/settlement reconciliation, calibrated costs/fills and sustained actual device/feed evidence | Pending external access and engineering |
| Live infrastructure / pilot | Existing separate empirical, compliance, adapter/reconciliation and explicit approval gates | Pending; execution unavailable |

Reviews and LT2 inputs are operator assertions, not verified corporate-action feeds.
Real settlement/custody, income tax/AMC, automatic long-term signals, complex actions,
lot/tax management and combined capital coordination are not implemented. Preserved
overnight state alone is not full investment-platform or production readiness.

## Remaining milestones and acceptance gates

| Milestone | Required next evidence |
|---|---|
| Real read-only session | Actual manual login, profile, history entitlement, full quote feed; tests currently mock Kite |
| Target-device operations | ARM64 Pi dependency installation, reboot/launchd/systemd/power-loss drill, disk monitoring |
| Empirical strategy validation | Actual matching raw candle/quote data, point-in-time universe/corporate-action review, calibrated fees/depth and retained unfavorable experiments |
| Empirical ML acceptance | Implemented Phase 3 workflow must pass on reviewed real data, with exclusion/selection/cost assumptions retained and later portfolio validation |
| Phase 4 external acceptance | Sustained actual supervised feed, calibrated fills/costs, full-session coverage review and target-device recovery/latency |
| Future live (Phases 5–6) | Separate explicit approval, current compliance and broker rules, separate reviewed adapter/reconciliation |

The code is portable by design, but local tests on this Mac are not a Raspberry Pi
deployment certificate. Backup tests and SQLite fault injection do not replace a real
power-loss rehearsal. A clean advisory scan is time-specific, not a future guarantee.
No live account action or order was attempted. See [test-plan.md](test-plan.md) for
the final measured validation record.
