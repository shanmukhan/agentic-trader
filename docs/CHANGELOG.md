# Change log

## 2026-10-21 — LT2 reviewed paper corporate actions (0.6.0)

Added exclusive offline `apply-corporate-actions`, `record-corporate-cash` and
isolated `corporate-actions-demo` commands. Strict bounded UTF-8 input rejects
ambiguous/duplicate fields, extra fields, nonfinite/subpaisa money, invalid ratios,
naive/future dates and unsupported context. Batches bind the current quarantine
hash, explicit complete coverage, stable issuer/batch IDs and sourced ex-date sessions.
Accepted ex-date quotes/fills and retroactive/same-date follow-up batches are refused.

Added increasing split/bonus quantities with original holding identity, total cost
conservation, tick-rounded protective levels and affected-order cancellation while
retaining durable exits. Exact rational fractional claims retain allocated basis
rounded down to paise, with the holding retaining the exact residual. Unknown
fraction values pause new entries/portfolio marks without erasing claims on sale.
Fraction chains and unsupported issuer events remain blocked rather than guessed.

Added frozen gross/deduction/net dividend receivables, nonspendable until an exact
reviewed net receipt, plus separate cash-in-lieu settlement and received investment
income. Atomic additive financial tables and journal/materialized changes preserve
original orders/fills. Independent ordered reconstruction verifies quantities, cash,
cost, adjusted protections, claims, receipts, basis boundaries and primary-key
receivable caches. Canonical retries write nothing; an already paid claim cannot
be credited with another payment ID. Backups preserve all evidence.

Updated report schema to 2 with full batches/claims/quarantine hashes, separate
income/fraction P&L and adjusted whole-share capital metrics. Console claim cards
explain spendability, incomplete valuations and the next required action; quarantine
confirmation points to the offline workflow. Values/guidance clear on Lock.
Added the detailed corporate-action usage guide and updated main/long-term usage,
plan/specification, architecture, API, risk, runbook, threat, acceptance, research,
performance and testing Markdown. `AGENTS.md` records the user's standing
usage/component-documentation, financial-test and clear accessible UI requirements.

Validation:

- **387 Python tests and 19 JavaScript tests passed**, **92% Python coverage**.
  New action contracts **95%**, accounting reconstruction **90%**, offline service
  **92%**, direct lifecycle drill **100%**; legacy suites remain passing.
- Invented split/dividend/bonus/fraction/exit/receipt drill: final cash **₹25,029.42**,
  realized capital P&L **−₹20.98**, received dividend income **₹50.40**, no holdings or
  claims left. These are software fixtures, not market-return evidence.
- 2,000-quote Mac benchmark with fourteen held shares/₹14 unpaid dividend:
  p50 **0.2003 ms**, p95 **0.2297 ms**, p99 **0.2564 ms**. SQLite WAL/FULL unchanged;
  parsing/network/contention/history/action replay/Pi are excluded.
- Ruff lint/format, mypy, secret-pattern/Markdown-link checks, frozen offline lock,
  dependency audit (no known vulnerabilities), wheel/source builds and extracted
  package imports/assets passed. No dependency was added.
- Original account read-only preflight still reconciles **₹25,000.00**, zero fees,
  no positions/pending orders and matching legacy policy/horizon. No recovery ran.
- Isolated responsive LT2 preview runs locally with invented unpaid/fraction claims.
  Browser visual inspection was blocked by pending Accessibility/Screen Recording
  permission; JavaScript workflow checks passed. Actual handset acceptance remains open.

Real custody/settlement, bank verification, statutory tax lots, complex actions,
corrections/reversals/deposits and validated daily strategies remain excluded.
Version 0.6.0 does not deliver the original live-adapter phase. The next engineering
item is LT3 daily research/portfolio management, with all external/live gates retained.

## 2026-10-20 — LT1 long-term paper foundations (0.5.0)

Expanded the user-requested plan to include long-term NSE cash-equity paper holdings.
Added a separately bound `investment_horizon`, dedicated config/database/8001 listener,
portfolio drawdown limit and separate delivery charge schedule. Legacy intraday
policy hash `642c1e1c9fabdd41278868d4e66108e201e7c1b15ddb888ed5ad9704afd1cbaa`
and existing intraday defaults/model artifacts remain unchanged. Horizon/policy
changes fail before pending recovery; a selected feed cannot omit a held symbol.
Each account has independent virtual capital, not a shared cross-account budget.

Added composed overnight day-roll/watch behavior: regular closes/weekends/restarts
preserve long-term holdings, entry residuals still expire, prior trusted portfolio
observations anchor the new day's P&L before opening quotes, and observed peak/
drawdown persist across dates. Protective stop/target/operator/kill exits remain
latched per holding until closure, including cancelled/restarted partial residuals.
Waiting for a new date cannot reset a breached long-term drawdown limit.

Added typed, authenticated current-session price-basis review and individual-holding
exit routes with console controls/confirmation. Missing review blocks raw quote
replacement and fills. Reviews pin the used calendar and prior quote basis; reported
corporate actions persistently quarantine symbols and cancel pending buys. Another
review cannot clear quarantine. No split/dividend/cash/share adjustment is invented.
Existing intraday automatic rules/ML/research are refused on long-term configs.

Delivery estimates include both-side STT, delivery stamp, variable taxes/fees and
atomic DP once per sold symbol/IST day across partial fills and replacement orders.
An entry cash buffer protects ordinary exit-fee capacity. Actual fee shortfall blocks
the fill without charging an unfilled DP amount, creating negative cash or deleting
the holding. Startup independently reconstructs delivery fees/day allocation,
review authority, quarantine, fill journal and durable exit evidence.

Added source-preserving `long-term-report`, three independent invented lifecycle
scenarios, an isolated populated benchmark and CI commands. Added the detailed
long-term guide and updated all corresponding plan/specification, usage, API,
architecture/risk, threat/operations, acceptance, research/model, performance/test
Markdown. The extended roadmap names LT2 corporate-action accounting, LT3 daily
research/portfolio management and LT4 actual custody/settlement acceptance. This
package version is not the original future live infrastructure Phase 5.

### LT1 validation and measured limits

- **328 Python tests and 17 JavaScript tests passed**; **92% Python coverage**.
  Forty-four new Python cases include financial outcomes, fault rollback, corruption,
  horizon/coverage rejection, API/CLI/report flows and lifecycle drills. Long-term
  policy **96%**, delivery verification **93%**, charges **100%**, independent broker
  **93%**, long-term demo **90%**, report **92%**, API **91%**.
- Ruff lint/format, mypy, secret-pattern/Markdown-link checks, frozen offline lock,
  dependency audit (no known vulnerabilities) and wheel/source builds passed.
  Packaged long-term modules and console assets load outside the repository.
- Populated 2,000-observation Mac benchmark: p50 **0.1843 ms**, p95 **0.2147 ms**,
  p99 **0.3288 ms**, fourteen held shares, WAL/FULL unchanged. Parsing, network,
  callback contention, history and actual Pi behavior are excluded.
- Invented independent outcomes: overnight/restart cash **₹25,379.54**, opening-gap
  cash **₹24,261.40**, quarantine account cash **₹17,986.78** plus fourteen retained
  shares. These are software fixtures, not market-return or profitability evidence.
- Original-account read-only preflight reconciled **₹25,000.00**, zero fees, no
  pending orders/positions, matching legacy intraday policy/charges. Missing operator
  token in the unconfigured shell remains correctly blocked. No source recovery ran.
- Desktop Safari visually displayed the isolated long-term account, horizon, fee
  buffer and review form. No Kite session, real order or custody action occurred.
  Mobile/actual-device checks remain pending.

LT1 does not implement corporate-action adjustments, actual custody/sellable holdings/
settlement, daily long-term strategies/ML, SIP/rebalancing/tax lots or aggregate capital
allocation. Virtual same-day protective exits/immediate sale cash are simulation
simplifications. Real-feed/model/strategy/device acceptance and all live phases
remain pending under the documented gates.

## 2026-10-20 — Responsive console and local acceptance tooling (0.4.1)

Continued Phase 4 acceptance support with a responsive packaged HTML/CSS/JavaScript
operator console: account cards, readiness reasons, observed quotes, positions,
latest orders and raw details. Added authenticated `/api/console` for engine-serialized
state capture with a 200-order/ten-quote bound. Existing order/control/risk contracts
remain in force. CSS stacks panels and touch-sized controls for narrow viewports;
there is no native mobile app or public listener.

Added memory-only unlock/lock, clearing of private values, rejection of late/older
poll responses, visible-tab polling, overlapping-request suppression, six-second
stale display protection and request timeouts. Arm/reset ask for confirmation and
stale data blocks them; emergency kill/flatten/disarm remain direct requests. Actions
are serialized with no automatic retry. Timeout messages disclose unknown outcomes,
and queued exits are not represented as fills. Dynamic rendering uses text nodes,
fetches reject redirects/omit cookies, and same-origin static CSS permits a tighter CSP.

Added `preflight [--strict] [--output NEW_PATH]` before the owning CLI startup path:
read-only WAL-aware ledger/integrity and stored-identity checks plus runtime, SQLite
fix branches, calendar, permissions, token presence, disk and catalog diagnostics.
It does not create missing accounts, construct a broker, take ownership, recover or
cancel pending work, call Kite, validate an external model or arm anything. Queries
have cooperative budgets and retain normal locking; heavy integrity scans stay out
of UI/feed processing. Private JSON/Markdown reports have a final hash manifest.
Strict exit 2 identifies blocked required local checks; external/live acceptance
always remains false. Full controller identity is still verified at actual startup.

Added console/acceptance usage guides and updated corresponding plan/specification,
architecture/API, performance, threat model, runbook, tests and paper-feed documents.
Added Node 24 JavaScript checks to CI; no Python or browser runtime dependency was
added. Package/version/lock now identify 0.4.1.

### Validation

- **284 Python cases and 13 JavaScript cases passed**; Python coverage **92%** overall,
  preflight **97%**, console view **93%**, API **90%**, paper broker **93%**.
- Ruff lint/format, mypy, secret-pattern/Markdown-link checks, frozen offline lock/sync,
  dependency audit (no known vulnerabilities) and wheel/source builds passed. Packaged UI assets load outside the repository.
- Desktop Safari account/readiness and lock/unlock/kill/reset behavior checked in an
  isolated virtual preview. Its balance remains ₹25,000, flat, kill inactive.
- Original account read-only preflight reconciles ₹25,000.00 with no pending orders
  or positions; missing operator-token configuration is correctly reported blocked.
- Local Python **3.13.16**, SQLite **3.53.1**, macOS ARM64. Real broker, hardware,
  sustained-session, fill/model acceptance and mobile visual/handset checks remain
  pending. Browser tooling did not provide reliable mobile visual verification.

## 2026-10-20 — Phase 4 supervised paper-feed engineering (0.4.0)

Added explicitly enabled supervised paper automation, authenticated arm/disarm and
universe-wide readiness to the private console/API. Startup, restart, reconnect and
new sessions remain disarmed. Backfill warms features with entries disabled and
does not replay missed signals. Manual entry intents are disabled on dedicated
automated services; existing protective controls and independent risk remain active.

Added `paper-init` for exclusive creation and read-only catalog/profile checking,
binding the selected model/rule policy before any manual model identity is assigned.
Accounts pin runtime/rule/strategy/feed policy, universe, model and synthetic mode;
used calendar definitions are pinned by date. Removed/changed automation is rejected
before pending-entry recovery. Controller-free submissions fail at the broker.
Durable proposal counts survive history reload and restart, including rejected orders.

Added a separate history worker with monotonic request spacing, bounded retry cadence,
completed-session response checks and connection-generation invalidation. HTTP waits
release the quote/risk lock. The worker uses authoritative completed historical 5m
bars, avoiding unknown initial streamed volume/partial-bar mixing; slow or missing
history skips entries. Default 400 ms request spacing respects the documented
historical request budget. No network operation was added to the execution adapter.

Disconnect/staleness disarms and cancels pending buys before resumed data can fill
them. Stale holdings or disconnects queue durable kill exits; unavailable data never
fabricates liquidation. Reconnect/reset does not rearm. Models retain Phase 3 loader
gates and additionally require non-synthetic provenance, current availability and
the configured validation age, including cancellation before pending buys fill after
expiry. No synthetic override exists on the connected service.

Added bounded timing rings and cumulative counts/maxima/budget exceedances, periodic
journal telemetry and observed per-run equity/drawdown. Added source-preserving
`paper-report` with reconciliation, net trades, incidents, clean-run/sample/model/
latency gates and explicit measurement limits. Recent windows are not represented
as global quantiles; crash losses in telemetry and incomplete coverage are disclosed.
External acceptance and live readiness always remain false.

Added `paper-demo` with independent partial-fill, disconnect-with-holdings, silent-feed
and unclean-restart accounts/evidence. Added a populated durable pipeline benchmark,
CI commands and complete corresponding plan/specification/usage/architecture/API/
risk/security/runbook/performance/testing Markdown. Added the compatible schema-v1
event-kind/time index for fast durable proposal-cap lookups. Economic hashes, money
semantics and WAL/FULL durability are preserved; no dependency was added.

### Phase 4 validation

- **259 tests passed**, including all 215 previous regressions and 44 new unit,
  integration/concurrency and functional cases. Coverage: **92% overall**, paper
  runtime **91%**, service **90%**, reports/demo **93%**, metrics **100%** and
  independent paper broker **93%**.
- Ruff lint/format, mypy, secret-pattern and Markdown-link checks, frozen lock
  verification and wheel/source builds passed. Dependency audit found no known
  vulnerabilities; no advisory was ignored.
- Synthetic partial-fill cash reconciled to ₹25,023.24; disconnected/silent recovery
  accounts to ₹24,959.48; cancelled unclean-restart account stayed ₹25,000. Each starts
  independently at ₹25,000. These invented outcomes have no market interpretation.
- The 2,000-observation populated Mac benchmark measured p99 **0.4791 ms**, including
  nineteen partial buys, a nineteen-share holding, risk/accounting/performance and
  periodic durable telemetry. Network, parsing, callback contention, history I/O and
  Pi behavior are excluded. No durability setting was weakened.
- Original service-account integrity/accounting checks passed; it remains flat at
  **₹25,000.00**, with zero fees/reservations and no feed connection.

No real broker connection, order, deployment or funds transfer was attempted.
Supervised-source research exports preserve first observed candle availability and
recorded connection changes. Missing observation clocks or external unclocked candle
overrides are refused, preventing backfills from being treated as known at close.
Actual entitlement/feed duration, fill/cost calibration, market/model acceptance,
target-device latency and physical recovery drills remain pending. Future live
infrastructure still requires separate explicit approval.

## 2026-10-20 — Phase 3 chronological ML research (0.3.0)

Added a versioned twelve-feature causal schema with finite values, completed-time
and instrument checks, and a normalized fingerprint binding economic candidate
identity. Labels use independent standalone paper accounts with existing fee-aware
risk sizing, depth, partial fills, tick rounding and later-quote latency. Predeclared
time barriers queue exits before reading subsequent prices; intervals end at actual
last fills. Unfilled, unresolved, interrupted and bad/gapped paths are censored and
audited rather than converted into negative targets or forced closes.

Added hash-verified sample bundles preserving source manifests, full strategy and
economic settings, label policy, sessions, code identity, counts and execution audit.
Readers validate bounded local paths/records, uniqueness, universe/session context,
outcome-count consistency and immutable inputs. Completion manifests are written
last. Labeling uses temporary independent accounts plus a retained quote observer;
it never opens or changes the configured service account.

Added whole-session expanding walk-forward splits with timestamp-interval purging
and strict embargo, train-only scaling/logistic fitting, disjoint later regularized
sigmoid calibration, and a final holdout inspected after coefficients freeze. Fixed
settings replace parameter search. Diagnostics include ROC-AUC, Brier/log loss,
training-prevalence baseline, reliability/ECE, selected counts and net counterfactual
P&L. Insufficient fitting data fails; failed evaluation models retain diagnostics
and cannot load. Model availability follows the latest final validation label,
declared session close or source observation, plus embargo.

Added bounded JSON-only artifacts and a lightweight pure-Python loader/scorer.
The loader checks hashes, schema/order/dimensions, finite math, report identities,
split windows, reliability consistency, derived acceptance gates and contextual
strategy/policy/fee matching. No pickle or joblib is loaded. Synthetic override
relaxes provenance only, requires all metric gates, and only scores synthetic data.
Integrity hashes do not authenticate a maliciously rewritten local bundle.

Added same-availability-time probability ranking before independent risk admission.
The paper broker rechecks feature/candidate/model context, availability and threshold;
all previous sizing, cash, loss, position, freshness and kill gates remain in force.
Vector changes conflict under an existing intent. Model version/schema metadata
prevents silent gate removal on restart; missing metadata fails before cancelling
pending orders. The original economic-policy hash encoding is preserved. No database
schema migration, live route, network execution adapter or connected automation was added.

Added `ml-build`, `ml-train`, `ml-demo` and `backtest --model`, separate real/synthetic
training policies, optional locked training dependencies, CI steps and a scoring/ranking
benchmark. The Pi setup now installs only broker/runtime extras. Updated the supplied
specification, implementation plan and corresponding architecture, risk, security,
API, runbook, performance, test and usage Markdown; added the detailed ML usage guide.

### Phase 3 validation

- **215 tests passed**, including all 159 previous regressions and 56 added unit,
  integration and functional cases. Reported coverage: **93% overall**, features/schema
  **100%**, training/samples **99%**, inference **97%**, labeling **94%**,
  validation diagnostics **91%** and independent paper execution **93%**.
- Ruff lint/format, mypy, working-tree secret-pattern checks, local Markdown links,
  frozen lock verification and offline wheel/source builds for **0.3.0** passed.
- Current installed dependency audit: **no known vulnerabilities**, no ignored
  advisory. Optional NumPy 2.5.4 / scikit-learn 1.9.1 dependencies are hashed in the
  lock. A fresh-process test confirms loading imports no heavy training/persistence stack.
- The synthetic functional workflow labels sixty candidates (30 per class), passes
  invented walk-forward/holdout diagnostics, and correctly fails `non_synthetic`.
  Ten subsequent sessions remain outside training and validation. Their rule/scored
  portfolio results are reproducible and documented as invented software fixtures.
- The original service account passed integrity/accounting checks and remains flat
  at **₹25,000.00**, with zero fees, zero reservations and no feed connection.
- The 10,000-observation Mac benchmark measured score p99 **0.0012 ms** and ten-candidate
  score/rank p99 **0.0144 ms**. These exclude feature creation, parsing, artifact I/O,
  risk/commit, training and network. Durable quote-path recheck measured p99 **0.156 ms**
  in the existing empty-portfolio fixture; no durability setting was weakened.

No model has been empirically accepted on real market data. Quote density, exclusions,
historical fees, corporate actions, selection bias, actual broker access, Pi operations
and connected paper-feed validation remain external acceptance work. Synthetic passes
and small local latency measurements do not establish profitability or live readiness.

## 2026-10-20 — Phase 2 strategy research (0.2.0)

Added immutable, versioned ORB and VWAP-continuation rule settings and independent
per-symbol/session state. Signals use completed contiguous 5m candles, session VWAP,
rising EMA, Wilder ATR, prior-only relative volume, turnover/price/spread/freshness
filters, ATR stops/targets and a per-session candidate cap. Candidates still pass
the existing cost-aware risk engine; connected-feed strategy automation is deferred.

Added streaming typed raw-price dataset bundles with reviewed sessions, provenance,
availability/chronology checks, restricted paths, bounded reads, synthetic labels,
input hashes and post-run mutation checks. Added a source-preserving exporter that
retains calendar references, accepts verified candle overrides and never runs source
order recovery. Failed exports leave no loadable manifest.

Added isolated quote-driven backtesting and `backtest`, `research-demo`,
`export-research` commands. No OHLC tick path or signal-close fill is invented.
Even zero latency requires a strictly later exchange quote. Research accounts retain
unfinished positions/orders and report gaps/stale valuations as incomplete. Outputs
include decision explanations, equity CSV, completed net-trade statistics, observed
drawdown, fill/accounting journals, reproducibility hashes and runtime versions.

The synthetic two-session fixture contains a winner and loser: final cash ₹24,974.03,
estimated fees ₹20.27 and net P&L −₹25.97 under defaults. It does not establish
profitability. Historical fee matching, queue/impact effects, sparse observations
and incomplete connection history remain disclosed research limitations.

Added leakage, metric, provenance, failed-input/export and source-order isolation
tests, CLI functional checks, a constant-work strategy benchmark, CI coverage of that
benchmark and detailed corresponding architecture/API/risk/security/runbook/usage
documentation. Updated the specification/implementation plan and package to 0.2.0.
No runtime dependency or schema migration was introduced.

### Phase 2 validation

- **159 tests passed**, including the entire Phase 1 regression suite and 51 added
  strategy/data/export/metrics/CLI/causality cases. Reported coverage is **91% overall**,
  **95% rule strategies**, **94% dataset validation**, **95% export**, and **99% metrics/reporting**.
- Ruff lint/format, mypy, working-tree secret-pattern check and local Markdown links
  passed. Wheel and source distribution builds for **0.2.0** succeeded offline.
- Final installed dependency audit found **no known vulnerabilities**; no advisories
  were suppressed and runtime dependencies did not change.
- The functional research demo completed both net-positive and net-negative trades.
  The service paper account remained flat at **₹25,000.00** and passed integrity and
  accounting verification.

The 2,000-evaluation benchmark measured p99 ORB **0.0177 ms**, VWAP **0.0168 ms** on
this Mac. It excludes input construction/decoding, disk, network and execution.
Real-market performance, actual Kite access, Pi deployment and ML remain unverified.

## 2026-10-20 — Initial paper platform

Initialized Git on `main` and implemented the Phase 1 paper-only plan from the supplied
specification. Added Python 3.13.16 environment metadata, exact hashed dependency lock,
package entry point, safe config/secret examples, local private runtime, setup scripts
and Git exclusions for credentials, environments, logs and trading artifacts.

Added validated domain types, Decimal money, UTC/IST separation, reviewed session
calendar, read-only HTTP authentication/profile/catalog/history, strict full-mode
equity WebSocket decoder and bounded reconnection. Removed the initially evaluated
official SDK after its pinned transport failed the vulnerability scan; implemented
the limited official protocol with audited transports and documented the deviation.

Added SQLite schema v1, WAL/FULL durability, exclusive ownership, atomic journal,
idempotent intent fingerprints, accounting reconstruction, paper cash/positions,
cost-aware risk sizing/reservations, latency/depth/partial fills, cumulative fees,
daily/streak/stop/target/session risk gates, persistent kill and conservative restart
recovery. Added credential-free health, entry readiness, authenticated operator API,
Origin/Host/security headers, local dashboard and redacted rotating diagnostics.

Added incremental candle/feature infrastructure, explicit unavailable ML stub,
deterministic replay/demo reports, backup verification, deployment templates, CI,
unit/integration/functional/replay/security checks, secret-pattern check and benchmark.
Updated the specification and corresponding architecture, risk, security, API, test,
performance, usage and operator documentation. Later strategy/ML/live phases remain
gated as described in the implementation plan.

### Local validation record

- **108 tests passed**, including unit, integration, functional CLI/API, replay,
  security, real process-death recovery and seeded partial-execution sequences.
- Coverage reported **90% overall**, **93% paper execution**, and **100% costs/sizing**.
- Ruff lint/format, mypy, project secret-pattern check, shell syntax and launchd plist
  validation passed. All local Markdown links resolve.
- Final dependency scan: **no known vulnerabilities**; the editable local project
  itself is not a PyPI advisory target. No advisories were suppressed.
- Frozen/offline environment sync, source distribution and wheel build succeeded;
  the build backend is pinned to Hatchling 1.32.4.
- The real default paper database was initialized at exactly **₹25,000.00** and
  passed integrity/accounting verification. It is ignored by Git and has no holdings.
- The committed 2,000-event Mac benchmark records p99 indicator update **0.0028 ms**
  and quote ingestion/journal/risk/durable commit **0.153 ms**. Typed model construction,
  network, populated-account execution and ML are outside these timer boundaries.

The final pass also normalized financial/time formatting in idempotency fingerprints,
added durable sequence numbers to same-time exit reissues, strengthened persisted
reservation/fee/policy validation, and checked generic error redaction for headers
and JSON-shaped messages. Corresponding regression tests and component docs were updated.

No actual Kite credentials, broker subscription purchase, live order, host-wide
service installation or Raspberry Pi hardware test was performed. Functional broker
tests use controlled transport responses. Configured remote CI has not executed here.
