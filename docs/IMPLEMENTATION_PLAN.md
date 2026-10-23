# Agentic Trader V2 — proposed implementation plan

Date: 22 October 2026 IST. Baseline: `2d5c208`, version 0.14.0.
Updated: 23 October 2026 IST for the 0.19.0 usability pass.
Version **0.19.0** adds local labelled SVG icons, compact shell/status feedback,
progressive setup/valuation/chart explanations and a four-step policy-draft form
with contextual help and linked validation. It preserves exact money, stale/missing
evidence, reviewed actions and draft/account separation. See [the interface guide](ui-experience.md)
and [validation record](test-plan.md). It does not complete Phase 5 or change the
implementation-Mac native-worker gate or external acceptance status.

Authority: [improvements.txt](../improvements.txt). The user authorized continued
implementation. Version **0.18.0** adds a distinct blank/nullable investment-policy
draft contract, immutable reviewed private snapshots in Strategies and pure calendar
review-date previews through an offline stdout-only CLI. It records months/years and
monthly/quarterly options without selecting an active policy or creating execution
authority. See [the draft workflow and boundaries](investment-policy-drafts.md).
Validation: **1,213 Python / 186 UI tests**, **92.13% statement coverage**;
Ruff/format/mypy passed. The disposable desktop Firefox draft workflow and independent
saved-file/accounting checks passed; broader rendered and execution acceptance remain open.

The earlier **0.17.0** slice implements registered isolated browser-job lifecycle/report
views and exact read-only allocation, plus pure gated daily-performance functions.
**Phase 5 is incomplete.** Launch fails closed on the implementation Mac; Linux/Pi
browser isolation is unsupported. Investment-policy execution/adapters,
parity/OOS/walk-forward/benchmark/rebalancing and external acceptance remain open.
The historical [implementation record](implementation-plan.md) separates implemented
behavior, simulated/local validation and actual platform/broker/device acceptance.
See [browser backtesting](browser-backtesting.md) and [portfolio analytics](portfolio-analytics.md).
Historical 0.17 integrated evidence: **958 Python / 172 UI tests**, **91.87% statement coverage**,
Ruff/mypy passed. A disposable synthetic desktop Firefox smoke check covered registered
inputs, unavailable launch and the allocation view. Native worker and broader rendered
acceptance remain open. Registered identity binds code and observed fees as well as data.

## Decision and scope

Keep Python 3.13, FastAPI/Uvicorn, Pydantic, SQLite/Decimal accounting and the existing
self-hosted HTML/JavaScript frontend. Extend tested components incrementally. A framework
rewrite, multi-service migration or live-order adapter is not justified by this audit.
Preserve working intraday code, independent risk, corporate-action review, idempotency,
authorization and paper-only execution. Do not change the operator's current mode,
credentials, watchlist, reviews or holdings during modernization testing.

The new priority is months-to-years NSE investing. The current delivery strategy's
20-session hypothesis must be labelled accurately and kept versioned. A new investment
horizon/policy requires explicit configuration and separate out-of-sample evidence;
it must not silently change the semantics of an existing account or ML artifact.
Quality/value strategies and many fundamentals filters depend on a reliable licensed
point-in-time source that has not yet been selected. Unavailable data remains absent.
No system or result may be represented as reliably selecting profitable stocks.

## Evidence and capability baseline

Read [ARCHITECTURE_AUDIT.md](ARCHITECTURE_AUDIT.md), [UX_AUDIT.md](UX_AUDIT.md) and
[GAP_ANALYSIS.md](GAP_ANALYSIS.md) together. Existing capabilities include causal daily
research, quote-executed delivery backtests, chronological ML validation, exact durable
paper execution, corporate-action/claim accounting, manual contributions/SIP and a
light workspace. They are assets to integrate, not missing modules to recreate.

Read-only local validation executed for this audit:

| Check | Actual result | Limit |
|---|---|---|
| `.venv/bin/pytest -q --cov=trading_agent --cov-report=term-missing:skip-covered` | 660 passed; 8,322/9,033 statements covered, 92.13% | Synthetic/local tests; SQLite unclosed-connection ResourceWarnings need test-fixture cleanup; not proof of a production leak |
| `node --test tests/ui/*.test.cjs` | 117 passed on Node 22.14.0 | Simulated DOM, not a browser layout engine |
| `.venv/bin/ruff check .` | Passed | Static lint |
| `.venv/bin/mypy src/trading_agent` | Passed, 98 source files | Does not establish semantic trading correctness |
| `.venv/bin/python scripts/check_secrets.py` | Project-specific patterns clean | Limited pattern scan, not exhaustive history/secret audit |
| Disposable existing-Setup-controller geometry harness | Pre-focus, deep scroll, parent/visual viewport resize and cancel cleanup passed, no mutation | Temporary `/private/tmp` harness, not a committed browser regression test |
| Broker/error probes | Mocked 403/429/503 recovery classification and synthetic repeated-quote controller behavior inspected/reproduced | No authenticated broker call or operator-account mutation |

Python was 3.13.16. Official Kite authentication, instruments, history, WebSocket and
error/rate-limit documentation was reviewed on 22 October 2026. Current dependency
advisory scanning, a wheel build and deployment/performance benchmarks were not rerun;
older recorded results must not be described as fresh audit acceptance. Desktop/mobile
rendering, sustained real-feed behavior, profitability and target-device acceptance
remain unverified. User-provided screenshots/reference images are evidence/inspiration,
not tests performed by this audit.

## Priorities before expansion

1. **UI confirmation reliability:** validate the existing setup viewport patch in the
   actual Firefox workspace; unify modal geometry/focus/cancel lifecycle across
   Setup, Risk, Purchases and strategy screens. Keep every financial action/confirmation.
2. **Calendar and strategy semantics:** support explicitly reviewed cross-year source
   calendars; formalize first-entry opportunity/gap and missing-data exit semantics;
   add differential tests between connected daily desk and offline replay before
   reusing research/model claims across them.
3. **Data and recovery evidence:** classify broker authentication/throttle/outage errors,
   preserve safe retry limits, version catalog evidence and add credential-free setup
   audit records. Handle the reproduced dedicated intraday repeat false-pause only as
   a separately reviewed correctness fix, not an intraday feature expansion.
4. **Investment-focused information:** make data coverage, horizon, action/price basis
   and missing fundamentals obvious; retain correct current financial state/definitions.
5. **Research, backtesting and portfolio integration:** expose existing valid research
   engines through bounded, isolated browser workflows before adding new strategies.

## Phases, deliverables and estimates

Estimates below are indicative focused engineering effort after approval, using the
current stack. They are not a delivery commitment, a staffing assumption or evidence
that missing data/licenses can be obtained. Browser/device and source-provider access
may add calendar time. Re-estimate after each acceptance gate rather than promising
all phases at once.

| Phase | Proposed work | Complexity | Indicative effort | Exit gate |
|---|---|---|---|---|
| 1 — Audit | Inspect modules/tests/reference, four audit/planning documents, deferred intraday roadmap | Complete | Completed | Presented; user approved Phase 2 |
| 2 — Architecture & UX contracts | [Design package](phase-2/README.md): grouped twelve destinations, screen/component/metric/API/data/strategy/job contracts, offline prototype, fix-first and migration acceptance | Design deliverables complete | Original estimate 3–5 days; no time-based acceptance claim | Reproducible design checks passed; source/license/investment parameters and rendered acceptance remain explicit future gates; no runtime implementation |
| 3 — Frontend modernization | Shared dialogs, twelve grouped destinations/aliases, saved-state Dashboard/Discovery/comparison/Portfolio/Settings/Learning, CLI guidance; existing workflows retained | Runtime slice implemented in 0.15.0 | Automated checks passed; rendered gate open | 670 Python/148 UI tests; exact persisted reads/privacy/geometry verified; full rendered keyboard/touch/zoom/browser acceptance pending |
| 4 — Stock research | Fifteen causal indicators; review-bound daily/weekly/monthly share-adjusted research; exact existing-rank evidence; local benchmark adapter; fundamentals unavailable | Price-research scope implemented in 0.16.0 | 828 Python/157 UI tests; source and rendered gates remain | Independent causal/basis/warmup/aggregation/benchmark/ledger-isolation checks pass; source licensing, longer acquisition and full browser/device acceptance remain open |
| 5 — Backtesting & paper investment | Browser job lifecycle around existing isolated replay, declared months-to-years strategy versions, benchmark/return metrics, OOS/walk-forward reports, allocation/rebalance proposals, exact portfolio analytics | Jobs/analytics slice 0.17.0; policy-draft/date-planning slice 0.18.0; full scope incomplete | Original estimate 12–20 days; remaining work requires re-estimation | Registered lifecycle/report/allocation/pure metrics and separate draft/date contracts implemented; real OS launch unavailable on implementation Mac. Draft execution/backtest, parity, OOS/walk-forward, benchmark/rebalance and operational gates remain; paper-only |
| 6 — Reliability & security | Broker recovery taxonomy, audit provenance, migrations/read-only admin, bounded reads, resource cleanup, operational acceptance and deployment checks | High | 5–10 days plus observation time | Credential/authorization/fault tests, migration/backup/reconcile gates, rendered browser and sustained broker/device evidence separately labelled |

The original approximate estimate for Phases 2–6 was **34–60 engineering days**.
With the design package delivered, the original ranges for Phases 3–6 total
**31–55 engineering days**, before data licensing and external acceptance delays. Reliability/correctness prerequisites are pulled forward
as needed; phase numbers do not justify shipping a known obstructive workflow first.
Scope can be narrowed after approval to an evidence-backed price-only investment MVP.

## Proposed modules and contracts

**Shared interface:** local reusable dialog/async-status/semantic-table/metric components.
Retain the current token in memory and verified origin/window handoff. First stabilize
the existing frame shell; remove frames only with an approved replacement design and
parity/security/history tests. No notification permissions or trade-approval hotkeys
are requested automatically.

**Data layer:** immutable versioned source manifests, catalog acquired-at/hash/source,
reviewed calendars crossing year boundaries, prices with event/availability/basis clocks,
and separate licensed fundamentals/sector/benchmark schemas. Raw, adjusted and total-return
series must have explicit semantics. Missing symbol/history/action coverage never becomes
an invented price, fundamental zero, inferred open session or certified quote provenance.

**Research:** deterministic versioned screening/feature contracts independent of order
submission. Rankings include positive/contradictory/missing evidence and exclusion reasons.
Weekly/monthly aggregation needs coverage/partial-period rules; indicators need warmup,
corporate-action and missing-bar rules. Current constituents cannot be historical
point-in-time membership. No arbitrary score is a profit probability.

**Strategies/portfolio:** separate signal, target allocation, proposal, reviewed decision,
order, fill and remaining holding. Define cash reserve, per-stock/sector concentration,
unknown classification and rebalance turnover/cost thresholds; all proposed limits must
pass coupled risk constraints. ₹25,000 remains pilot capital, not authorization to
increase risk, deposit money, or change the current account. Existing frozen/bound
financial policies require explicit migration/restart handling.

**Simulation/performance:** immutable request-bound job, isolated scratch database,
progress/cancel, durable report manifest and explicit failure/restart recovery. Reuse
existing daily replay/fee/corporate-action handling with declared parity boundaries.
CAGR requires a valid elapsed period; Sharpe/Sortino require declared sampling/risk-free
assumptions and nonzero denominators. Show NA and sample limitations. Return definitions
must distinguish costs held, external flows, realized/unrealized P&L, dividends and
unvalued fractional claims. Benchmarks require genuine compatible data and provenance.

**Broker/reliability:** keep the broker data client method/path allowlist and TLS/timeout/
redirect protections. Use typed credential-free failure reasons and bounded safe retries;
refreshing an expired session is an explicit login workflow. Version evidence without
silently replacing held mappings. Operational audit records exclude secrets/request tokens.
Read-only diagnostics must not instantiate a recovering account engine. Schema migrations
must preserve exact balances, order identities, events and fail closed on unknown versions.

## Acceptance and test gates

- Relevant unit, integration, HTTP, DOM and real-browser tests for every implemented
  workflow; no testing-only assertion of market profitability.
- Independent SQLite ledger/fee/claim/holding reconciliation before/after mutations,
  duplicate/retry/conflict/cancel/crash cases and migration round trips.
- No-look-ahead tests for point-in-time membership, prices, fundamentals, benefits,
  model availability, open/completed periods and later executable quote timing.
- Strategy differential tests for specified shared semantics, with intentional
  differences declared in the profile/model/report compatibility identity.
- No broker/order request from viewing, previewing, locking, reloading, reopening an
  expired signal or missing data; existing no-replay behavior changes only by explicit design.
- Credentials absent from URLs, logs, evidence and browser responses except the existing
  authorized local credential-entry flow; malicious origins/paths/extra fields rejected.
- Firefox plus an available second engine at 360/768/1440px, 200% zoom, keyboard and
  mobile keyboard. Confirmations stay visible at deep scroll, cancel posts nothing,
  confirm posts once, late responses cannot restore locked data.
- Real broker/device checks use explicit operator-reviewed actions and carry separate
  dates, duration, data source and acceptance limits. Never create real-money orders.

## Documentation and approval boundary

After each phase, update `how-to-use.md`, detailed usage/component guides, the existing
`implementation-plan.md` and `CHANGELOG.md` with actual behavior, tests and limitations.
Include changed files, what passed, what remains and the next acceptance gate. Update
these V2 planning documents as decisions change; avoid contradictory status claims.
Intraday proposals remain in [INTRADAY_FUTURE_ROADMAP.md](INTRADAY_FUTURE_ROADMAP.md).

**The user authorized continuation through the current Phase 5 slice.** Registration,
job lifecycle/report interfaces, current allocation, pure daily metrics and separate
policy-draft/date-planning contracts are implemented; that does not complete Phase 5
or establish OS/broker/device acceptance. The user's “both” preference is represented
as months/multi-year horizon and monthly/quarterly cadence options. Specific durations,
targets and reserves begin unset in each draft; no active account selection is made.
Continue with verified platform isolation, connected/replay specifications and explicit
new strategy/data/performance evidence before claiming the full paper-investment scope.
No status authorizes live execution, invented data, increased financial risk or changes
to the operator's installed strategy/account without its existing explicit workflow.
