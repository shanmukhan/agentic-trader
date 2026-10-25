# Change log

## 25 October 2026 — audit fixes and clearer paper workflows

Reviewed every numbered finding in `PROJECT_AUDIT_2026-10-25.md`; the
[audit resolution](audit-2026-10-25-resolution.md) distinguishes implemented fixes,
incorrect absence claims and source/contract-dependent work. Added an owned,
prioritized [roadmap](ROADMAP.md) without promoting unavailable features to execution.

Analysis adds exact touch/pointer/keyboard inspection, responsive readable candle
widths, larger volume, date labels, SMA swatches and optional saved RSI/MACD/ATR
panels. Backtesting draws fresh-only equity/drawdown/compatible-report overlays,
retaining exact tables and stale gaps. Portfolio adds available-weight allocation
and fresh complete P&L summaries; decimal/exponent sign/order and numeric rank
handling retain exact labels. No historical return or prior-close trend is invented.

Consolidated canonical CSS before responsive/theme overrides, added system dark mode,
reduced-motion loading, named/consistent access forms, static history guidance,
formatted HTML, assertive error regions and dismissible current-frame action feedback.
Visible Lock guidance and cleanup retain in-memory access only. Alt+R focuses a
proposal review without approving. Shared confirmations capture reviewed callbacks
and revoke them on cancellation/failure/Lock; page-specific authority checks remain.

Backend adds authenticated ledger-free feed observation, committed receipt-age cache,
bounded historical 429/503 retries, watchdog tracebacks, shared safe sell invariants
and strict stream identities. Gap-through-stop exits remain allowed. Intraday zero
and derived delivery fee buffers now serialize consistently as exact decimal strings.
ML readable reports add descriptive standardized/calibrated coefficients without
changing strict artifacts, chronological folds, purging or final holdout selection.

Validation: **1,335 Python tests and 232 Node UI tests passed**; **92.06% statement
coverage** (11,151/12,113), Ruff lint/format, mypy on 125 files, secret-pattern and
whitespace checks passed. Financial tests use independent SQLite reads/exhaustive
Decimal oracles, including 800 generated sizing cases, exact gap-exit fees,
cross-horizon fee-buffer contracts, supervisor loop persistence and ML artifact checks.
The full run emitted **52 SQLite ResourceWarnings** in existing test paths; resource
lifecycle remains separately reviewable.

Desktop Firefox verified disposable synthetic Dashboard/Portfolio values and accessible
visual labels. An independent full SQLite dump stayed unchanged: cash ₹20,495.23,
three orders/fills/positions, 27 events and no pending orders. Other charts/theme/narrow
behavior have automated checks; complete rendered dark/narrow/chart interaction and
physical-device/broker/native-worker acceptance remain open. The fixture server was
stopped. No user account, broker order or trading-mode change was performed.

## 2026-10-24 — Issue-report corrections and reliability fixes

Re-audited the 0.14.0 report against current 0.19.0 code and added a
[finding-by-finding disposition matrix](../PROJECT_ISSUES_GAPS_AND_IMPROVEMENTS.md).
Corrected obsolete claims about daily delivery replay, adjusted daily/weekly/monthly
research, investment-policy drafts and manual SIP templates. Genuine product gaps
remain labelled rather than reported complete.

Manual broker-feed frames now share one financial commit without dropping accepted
quote events or per-quote risk/fill checks. Live processing time is sampled per quote;
failed frames roll back financial changes and revoke symbol trust. Independent
query-only WAL snapshots remove writer reservation from selected operator reads.
Candle commits and the automated controller retain their documented separate behavior;
engine serialization and journal growth remain limitations.

Added `stream_limit` (default ten, range 1–3,000), bounded full-mode frames/subscription
batches and expanded feed/history bounds while preserving financial fingerprints.
Setup API/status, accessible labels/input capacity and confirmation now reflect the
configured ceiling; only symbol-selection requests get the bounded larger body budget.
Replaced regex TOML rewriting with `tomlkit` while retaining schema/policy validation
and private atomic replacement. A shared nonblocking lock helper selects POSIX or
Windows APIs across account/auxiliary stores.

An indexed read-only proposal-alert endpoint supports a cross-section workspace banner,
count/deadline/title and opt-in desktop notifications. Expiry/stale/failure/Lock states
stay explicit, countdowns avoid repeated live-region announcements and known price-gap/
calendar/review errors give actionable guidance. Alerts do not approve trades or extend
deadlines. See [usage/recovery](how-to-use.md) and [persistence limits](quote-persistence.md).

Validation: **1,292 Python tests and 202 Node UI tests passed**; **91.98% statement
coverage** (11,106/12,075), Ruff lint/format, mypy on 125 source files, offline dependency
lock validation and whitespace checks passed. New tests independently check exact cash,
fees/delivery-DP, persisted sequential/batch equivalence, protective exits/partial fills,
rollback/freshness, committed reads, configuration/ownership failures, expanded selection
and alert authority. The suite emitted 63 SQLite ResourceWarnings in existing test paths;
these were not treated as evidence of fault-free resource lifecycle.

Disposable Firefox desktop/320×480 checks verified proposal visibility across sections,
readable controls and Lock cleanup; independent SQLite reads showed ₹25,000 cash,
zero orders/fills/positions and the unchanged awaiting proposal. These were invented
local fixtures, not operator/broker acceptance. No user account or broker action was
performed. Native Windows operation, real-feed scale, physical-device notification
visibility and full multi-year investment/rebalance/fundamental/security migrations
remain open. See [validation scope](test-plan.md).

## 2026-10-23 — Daily reports, independent supervision and guarded acquisition

Implemented observation/acquisition/evidence recommendations from the
[checklist review](agentic-trader-checklist-review-and-findings.html). Added authenticated
`/api/operations` and `daily-report` with reason-coded prerequisites, source-date/hash/
session coverage, independent exact accounting verification, bounded order lifecycle
details, pending exits and actual current authority. Broker profile success now has
a separate timestamp without asserting continuing token validity.

Added `operations-watch` and `scripts/start_operations.sh` for independent local alert/
recovery transitions, five-minute audits and observed daily snapshots. Explicit opt-in
schedules one current-IST-date acquisition attempt through existing preparation with
session/account/order/catalog/broker gates and durable receipts. Unknown outcomes are
inspected rather than replayed. No source/basis attestation, installation, connection
or mode change is performed. Added inactive launchd/systemd templates.

`operations-backup` / `operations-restore-drill` privately preserve and verify the
stopped ledger/config/calendar/installed strategy/data/model set without order recovery.
Drill success verifies isolated artifacts/accounting, not path rebinding/service startup.
See [usage, limits and recovery](operations-automation.md). **1,248 Python / 193 UI
tests passed**, with Ruff lint/format, mypy, shell/plist checks. External broker/market/
device acceptance, remote alerts, encrypted off-device retention and full deployment
restoration remain separate work; explicit trading authority is preserved.

## 2026-10-23 — Daily manual-operation and strategy-data guide

Added [daily-operator-checklist.md](daily-operator-checklist.md) with the contents and
purpose of strategy downloads, per-trading-day guided refresh, current IST source-date
checks, same-day reuse and after-close refresh behavior. Documents each manual step,
why it is required, expected results and recovery, from startup/broker access through
source/basis review, activation, order supervision and end-of-day reports/backups.
Distinguishes initial setup, conditional tasks, long-term holdings and intraday exits;
clarifies that downloads do not update themselves, train ML or authorize trades.
Linked from how-to-use, strategy preparation and runbook; clarified the usage guide's
intraday flatness instruction for long-term operators.

Validation: reviewed against current launcher/controllers/CLI and existing component
guides; **128 local Markdown links across six files passed**, and official Kite
authentication/candle references were checked. `git diff --check` passed.
Documentation only; no new runtime tests or financial changes. No broker downloads,
operator attestations, order activity or external acceptance performed.

## 2026-10-23 — Workspace usability and local icons (0.19.0)

Added a same-origin SVG icon sprite for all twelve labelled navigation destinations
and selected access, refresh and section headings. Icons remain decorative; text,
keyboard focus, active-destination semantics and confirmations carry their meaning.
The compact header preserves paper identity and lock access. Setup keeps its next
step visible while its longer explanation starts collapsed after unlock. Removed
the repeated general unsaved-form notice; actual draft/request/navigation guards remain.

Shortened routine saved-view feedback without changing observation timestamps or stale
states. Portfolio keeps valuation coverage visible and groups scope/formulas in details;
Stock Analysis groups chart help/legend. Policy drafts present their existing four
groups as steps with progress, Previous group/Next group, unit-aware help and field-linked errors.
Step navigation has no persistence or financial defaults; exact preview and explicit
acknowledged save remain unchanged. Shared responsive styles retain readable exact
tables, visible focus and labelled touch targets. No financial or broker behavior changes.

Backtest evidence tables are individually expandable, with bounded scrolling; bundle
labels lead job cards and full job identity remains available. Risk actions are split
into emergency and entry fieldsets. Analysis distinguishes an empty stock inventory
from an unmatched search and disables Open chart without a result. Corrected policy
previews clear obsolete error feedback.

Validation: **1,216 Python / 193 UI tests**, **92.13% statement coverage**, Ruff lint,
source/test formatting and mypy pass. Disposable desktop Firefox checked rendering,
policy step/validation/dialog/Escape, Portfolio warnings and Risk grouping; independent
SQL showed unchanged empty-account accounting. No user account or broker action.

See [usage, component behavior and recovery](ui-experience.md). Validation scope is
recorded in [test-plan.md](test-plan.md); rendered checks must use a disposable account.
Full Phase 5, native-worker, investment execution/rebalance and external broker/device
acceptance remain open; this usability pass does not close those gates.

## 2026-10-23 — V2 Phase 5 investment-policy drafts and date previews (0.18.0)

Added a separate nullable schema-1 investment-policy draft family with months/years
horizons, monthly/quarterly reviews and explicit screening/allocation/exit choices.
No investment value is preselected. Strict exact decimal strings normalize to four
places (turnover two), invalid types/precision/choices fail, and allocation caps must
agree. Semantic identity excludes names/time/storage; only fully specified drafts gain
a proposed policy-version hash, with activation/backtesting still unsupported.

Strategies now links to `#strategies/investment-policy`: four labelled parameter groups,
incomplete drafts, exact preview/acknowledgement, immutable saved snapshots and **Edit
a copy**. Separate owner-private `.investment-policies` storage revalidates identities,
bounds and permissions; an identical reviewed save returns its existing snapshot.
Unsaved edits guard navigation, and uncertain saves require refresh/reconciliation
before an explicitly confirmed same-content retry. No automatic save/retry is performed.
Existing strategy preparation, legacy anchors and account controls remain available.
Unsaved/request/review state also triggers the browser's standard unload warning;
explicit lock clears local choices. Malformed preview responses cannot leave an
invisible pending dialog or block recovery.

Added pure calendar-month/year review-date previews and stdout-only `investment-policy`
CLI inspection. Dates use explicit original-day clamping, exclusive anniversary end,
full calendar-month/quarter coverage and an aware knowledge clock. Calendar completeness
is an unverified operator assertion. Missing/future-known evidence stays unavailable;
out-of-horizon reviews are skipped, empty covered periods never invent weekdays, and
the 400-cycle budget returns unavailability rather than hidden truncation.

See [commands, schemas, persistence and recovery](investment-policy-drafts.md) and
[validation record](test-plan.md). This remains a partial Phase 5 delivery: draft policy
execution/backtest adapters, connected parity, target/rebalance, OOS/walk-forward and
real-market/platform/device acceptance are unfinished. The 0.17 browser-job runtime gate
remains unavailable on the implementation Mac. No active policy, paper mode, account
cash/holding, broker credential or order is changed by creating these research drafts.
Validation: **1,213 Python / 186 UI tests**, **92.13% statement coverage**,
Ruff/format/mypy passed. A disposable Firefox workflow saved and reopened a draft;
independent file/SQL checks preserved its virtual cash, fees, orders and holdings.
Corrected accidental dependency-version edits; all 66 dependency lock records retain
their original pins, with only the project release version changed.

## 2026-10-22 — V2 Phase 5 registered jobs and portfolio analytics slice (0.17.0)

Added `research_jobs/`: CLI-only immutable input registration, one-worker/one-queue
admission, resource/hash-bound idempotency, durable job/cancel/restart states and verified
bounded report publication. `/api/backtests/*` authenticates existing local operator
access; browser mutations require explicit acknowledgement, with no path/upload/model
execution input. Workers get a separate scratch ledger, an allowlisted environment,
Darwin OS sandbox and verified hard budgets. The UI reviews policy/source/holding cap,
retains failed/cancelled/interrupted states, reconciles uncertain submissions using the
same request key and compares only identical registered resources/methods.
Resource identity also binds the Python implementation hash and complete observed fee
schedule. Changed code/costs require registration/review again before admission; reports
must retain the reviewed runtime identity as well as passing independent financial checks.

Runtime launch fails closed. On this Mac the hard 2 GiB address-space limit could not
be set and the Codex sandbox denied the native sandbox probe. Actual isolated-worker
acceptance is open; Linux/Pi browser jobs have no implemented backend. Read/registration
and simulated lifecycle tests are not substitutes for that gate. Actual budgets are
60 s wall/30 s CPU, 2 GiB address space, 32 MiB combined input/individual output,
128 MiB combined output, 64 KiB log, 100,000 rows, ten symbols/252 replay sessions,
100 retained jobs and 32 registered resources. No automatic cleanup/resume is supplied.

Added pure `portfolio_metrics` and daily-cut `performance` contracts with private
34-digit Decimal arithmetic. Portfolio exposes exact actual-cash/current-accepted-bid
whole-share allocation; receivables/fractional claims are excluded consistently and
reservations/buffers/pending orders remain separately labelled commitments. Missing,
stale, unreviewed or incomplete held evidence disables weights without cost fallback.
The read does not mutate account state. Daily metrics require explicit baseline,
reviewed daily cuts/calendar, known-zero flows and sufficient samples/assumptions.
Existing accounts and event-time replay curves do not supply that history, so their
CAGR/Sharpe/Sortino/monthly-return suite remains unavailable rather than inferred.

This is **partial Phase 5**, not acceptance of the full investment product. Registered
browser runs reuse legacy offline rules (default 20-session holding cap); connected
parity, new months-to-years policies, OOS/walk-forward browser orchestration, portfolio
benchmark returns, target allocation/rebalancing and real-platform acceptance remain
open. The user requested both months/multi-year horizons and monthly/quarterly reviews;
future configuration must support those options, but no concrete active policy was
selected. No operator account, mode, broker credential or real order was changed.

See [browser commands, limits and recovery](browser-backtesting.md) and
[allocation/performance definitions](portfolio-analytics.md). Final integrated automated
validation is recorded in [test-plan.md](test-plan.md): **958 Python / 172 UI tests**,
**91.87% statement coverage**, Ruff/mypy passed. A disposable synthetic Firefox smoke
check passed input/unavailable-launch/allocation rendering; broader rendered/mobile,
sustained broker/device, source licensing and profitability acceptance remain separate.

## 2026-10-22 — V2 Phase 4 causal price research (0.16.0)

The user authorized the next planned phase. Added `investment_research/` with
34-significant-digit Decimal indicators, gap/membership/availability segmentation,
coherent known-share-action OHLC/inverse-volume adjustment, a separate gross TRI,
explicit reviewed weekly/monthly aggregation and a bounded local benchmark adapter.
Fifteen indicators expose definitions, warmup, value/null, basis and availability.
Future data and incomplete periods never become invented bars or zero-filled metrics.
Benchmark comparison requires compatible declared gross INR sources and matched daily
coverage; source/license declarations and calendar reviews remain unverified assertions.

Added authenticated pure `GET /api/research/series` and isolated `investment-analyze`
reports. Legacy `/api/analysis` raw daily/minute meanings, strategy/ML/risk identities
and paper authorization are preserved. The UI supports daily/weekly/monthly research,
exact indicator/evidence tables, gap-safe SMA overlays and a display-only 50/100/all
range control. Discovery explains actual legacy filters/thresholds/ties without
reranking. No user account, watchlist, credential, review, holding or server was changed.

Validation: **828 Python tests passed**, **157 UI tests passed**, **92.38%** statement
coverage (9,066/9,814); Ruff, changed-Python format, mypy on 104 source files, limited
secret patterns and whitespace checks passed. New suites include 26 indicator,
34 series, 59 benchmark, 23 ranking and 16 functional API/CLI tests. Arithmetic uses
independent Fraction/Decimal references. HTTP reads past expiry/day rollover preserve
whole SQLite dumps, exact partial-fill cash/basis/fees/reservations and mode/revision;
failures sanitize 503 without financial fault recovery. CLI tests deny socket access,
prove no account/lock/WAL creation and independently hash private completed outputs.
Legacy raw split charts and full-history warmup before 300-bar display clipping are
covered. UI checks include exact strings, warmup, calendar/benchmark gaps, inert
research actions, range-only redraw and lock/late-response privacy.

See [usage, schemas and recovery](investment-research.md). Licensed fundamentals,
new investment policies, multi-year acquisition, browser backtest jobs, portfolio
return/benchmark/allocation analytics and operational acceptance remain future work.
Existing preparation still supplies 60 sessions from its supported current-year
source: longer research needs an explicitly reviewed longer bundle. Full rendered
browser/mobile/device and sustained real-feed acceptance remain open; tests are
synthetic/local evidence and establish no profitability or provider entitlement.
The coverage run still emits SQLite ResourceWarnings in test workflows; cleanup
remains a reliability finding rather than proof of a production leak.


## 2026-10-22 — V2 Phase 3 shared frontend and saved-state workspace (0.15.0)

The user requested the next implementation phase after Phase 2. Implemented shared
native confirmation geometry/focus/cancel lifecycle across Setup, Risk, Purchases,
strategy and mode/trade reviews; twelve grouped destinations with a compact mobile
menu and preserved legacy aliases; read-only Dashboard, Stock Discovery/comparison,
Portfolio and Settings; CLI-only Backtesting guidance and searchable Learning Center.
Paper Trading now owns readiness/modes/proposals; Trade History retains orders/fills.
Purchases/SIP/aggregate exits remain accessible through guarded Portfolio subviews.

`GET /api/workspace/views` uses a separately closed SQLite read-only connection under
the engine lock and returns bounded saved facts/decimal strings. It does not tick,
expire, refresh, poll, download or reconcile. Tests independently reconstruct persisted
fill/cash/basis/fee/reservation values and prove whole-database/mode/revision equality
for reads past accounting-day/proposal-expiry boundaries. Missing fundamentals, jobs,
return/benchmark and allocation engines remain unavailable; no new investment strategy
or broker recovery behavior was installed. Risk and intraday semantics are preserved.

Validation: 670 Python tests, 148 Node UI tests, 92.20% statement coverage
(8,405/9,116), Ruff and mypy (99 source files) passed. Simulated geometry covers
360/768/1440px, deep scroll, visual viewport zoom/keyboard offsets, scale/borders,
long content, focus, Escape/cancel/late close and cleanup. HTTP/DOM checks cover all
routes, labels, framing/privacy, exact rendering, comparisons and late-response locks.
A disposable read-only preview opened the locked shell in Firefox; interactive
verification was interrupted by user browser activity. Rendered keyboard/touch/mobile/
200% zoom/second-engine and sustained broker/device acceptance are **not complete**.
SQLite ResourceWarnings remain test-workflow cleanup findings, not new prod-leak proof.

See [implemented component scope and recovery](frontend-modernization.md). Frontend
code is delivered incrementally; the Phase 3 rendered acceptance gate stays open.
Phases 4–6 research/job/reliability expansion remain future work. No user account,
credential, watchlist, holding or server process was changed by implementation testing.


## 2026-10-22 — V2 Phase 2 architecture and UX contracts

- Completed the approved design phase in [phase-2/README.md](phase-2/README.md):
  architecture/authority/migration, twelve grouped screens/aliases, screen/component
  and light-theme specifications, exact financial/provenance/null definitions,
  data/indicator/policy parity, API/idempotency/job/error/recovery contracts.
- Added a clearly nonconnected offline prototype, navigation manifest, synthetic
  arithmetic fixtures, 15 proposed strategy acceptance vectors and reproducible
  design validators. No application code, risk default, account, route, credential,
  policy or runtime version changed; Phases 3–6 remain implementation work.
- Actual checks passed: 6 prototype DOM tests, design/route/link/HTML/offline checks,
  11 palette contrast pairs and 129 independent arithmetic/contract comparisons
  across 7 invented ledger cases/2 return paths; Ruff/format/whitespace passed.
  Strategy scenarios are specified, not executed financial workflows. The runtime
  suite was not rerun for documentation-only work. Rendered browser, broker/device,
  source licensing and empirical strategy acceptance remain separate future gates.
- Updated main/component usage references, the V2 proposal and historical delivery
  record. Next implementation slice is shared confirmation reliability and navigation.


## 2026-10-22 — V2 Phase 1 audit and approval plan

- Added architecture and UX audits, requirements gap matrix, phased implementation
  proposal and deferred intraday roadmap from `improvements.txt`. Audited baseline
  commit `2d5c208`/0.14.0; no application code or operator account changes in this phase.
- Verified existing CLI research/backtesting, paper execution and exact accounting
  instead of labelling those modules absent. Identified product gaps, early-year
  calendar failure, strategy-parity differences, legacy intraday repeat false-pause,
  broker recovery/provenance/audit gaps and rendered modal/browser acceptance needs.
- Fresh tests: 660 Python passed with 92.13% statement coverage, 117 Node UI tests,
  Ruff and mypy (98 source files) passed. Limited project secret scan clean. Test
  SQLite ResourceWarnings recorded; no full production security/device acceptance claim.
  A disposable setup-controller geometry check passed, without a feed/connect mutation.
- Documentation links point to the V2 proposal; implementation requires the user's
  explicit post-audit approval. No framework migration, real order or risk relaxation.


## 2026-10-22 — 0.14.0 light workspace and saved-data analysis

- Replace the dark tab strip with a responsive light sidebar: Dashboard, Market &
  Analysis, Strategies, Paper Trading, Risk Center and Broker & Settings. Keep
  Purchases & SIP as a subordinate workflow and Help/onboarding outside the main areas.
- Lead Dashboard with exact account equity/cash, dated daily P&L, position count,
  stale/incomplete valuation notices, market status and next action. Separate strategy
  preparation/shortlist at `/strategies`; preserve existing preview/confirmation and
  legacy desk fragments. Activity counts state their page/window scope.
- Guide broker setup with actual connection/session/calendar/subscription state and
  six keyboard-accessible disclosure steps. Open the relevant first step once;
  preserve operator edits/open steps on refresh. Navigation does not save settings.
- Add authenticated read-only `/api/analysis` and the Market & Analysis screen: saved
  completed daily/1m/5m OHLC, volume, SMA 20/50, exact table, quote status and prior
  screening context. No broker download, subscription, strategy evaluation or trade
  occurs on viewing. Preserve raw basis, data gaps/integrity/availability checks and
  explicit unknown minute-bar provenance. See [market-analysis.md](market-analysis.md).
- Keep in-memory unlock, origin/window checks, financial gates and operator action
  contracts. No new strategy builder, graphical backtest or performance promise is
  supplied. Version alignment prevents the launcher silently reusing an older server.
- Validation: 660 Python and 117 UI tests, Ruff lint/format and mypy (98 source files)
  passed; details and limits are recorded in [test-plan.md](test-plan.md).
  The running operator account was not restarted or used for test orders. Firefox
  capture did not reliably render the disposable preview; visual/device acceptance
  remains outstanding.


## 2026-10-22 — Prevent false quote-order pauses and explain cancelled signals

- Fix live whole-second Kite handling: ignore unchanged repeats without refreshing
  freshness, and accept changed tied books only in strict receipt order with valid
  identity/source/volume. Update marks/protection/candles while skipping repeated fill
  processing at that exchange timestamp. Replay/backward/ambiguous and financial guards
  remain; no timestamp or liquidity is invented.
- Persist specific pause causes and previous-mode events; distinguish cancelled
  unapproved proposals from orders and display both proposal/update times. Explain
  daily signals already handled, preserving terminal history and no automatic replay
  when switching to Automatic. No trade, mode activation or retry was introduced.
- Validation: 650 Python and 99 UI tests; Ruff and mypy passed. Independent exact
  ledger, tied-book/fill/protection/candle, authority-revocation and raw-callback tests
  passed. A separate isolated eight-second real-feed engine accepted 68 quotes with
  20 changed tied books, zero quality failures/faults and no orders; sustained/device
  acceptance is still separate. The running operator account was not restarted/rearmed.
- Updated usage, trading desk, feed, risk, API, architecture, implementation and test
  guides. A real backend restart is required to load these Python changes; existing
  cancelled daily proposals remain terminal after the upgrade.

## 2026-10-22 — Make pending daily review directly actionable

- Add **Review today’s setup** beside next-step/quote warnings and readiness cards.
  Reuse the existing guided summary, unchecked acknowledgement and explicit confirmation.
  Retain an installed policy without a first-policy default or ML fallback. Require
  same-day source data/Manual/supported setup; show stale/unavailable recovery guidance.
- Hide the shortcut after resolution and clear it on lock; cancel/preview/restart do
  not approve reviews. Updated usage, strategy, workspace and validation documentation.
- Validation: 97 UI tests and 17 guided unit/API workflow tests passed; Ruff passed.
  New independent persisted-state checks cover the preview/confirmation boundary.
- Distinct actual observation: today's 65-stock/60-session download and preview completed;
  later read-only status showed seven current-day reviews, accepted quote timestamps
  and zero blockers in Manual, with ₹25,000 cash, zero fees and no trades. No review
  confirmation was submitted by this assistant; sustained/device acceptance remains open.

## 2026-10-22 — Explain blocked live quotes and repair shortlist navigation

- Confirmed from the existing journal that incoming quotes for eight selected symbols
  were blocked by missing current-day price-basis reviews. Yesterday's reviews do not
  cover today; no review or quote-acceptance safeguard was relaxed.
- Replaced generic stale/missing labels with shared read-only basis/feed/quality/clock
  explanations. Show the reviewed session's current open/closed state and specific
  next actions, instead of always telling an open-session operator to wait for opening.
- Preserve readiness-link fragments through the workspace; reveal/focus shortlist and
  quote details after unlock/render, expand details and scroll below sticky navigation.
  Legacy `/desk#apply-shortlist` opens the containing review section. Opening links
  does not apply a shortlist; feed/Manual/no-pending and explicit confirmation remain.
- Validation: 637 Python and 90 JavaScript tests, Ruff and mypy passed. Independent
  persisted financial-state equality, daily rollover/new-quote requirements, navigation,
  focus, responsive offsets and origin checks are covered with simulated workflows.
  Actual account inspection was read-only; broker/device execution acceptance remains
  pending. Reload workspace assets; restart an older Python server for new diagnostics.

## 2026-10-22 — Explain feed symbols and default session hours

- Explain catalog lookup versus the saved live-feed watchlist, the application limit
  of ten subscriptions, token/tick meanings and broader Trading desk screening. Label
  saved subscriptions/count separately from unsaved symbol input.
- Default editable session times to 09:15 AM / 03:30 PM IST on unlock. Refresh keeps
  edits; date/source review and explicit confirmation are required before any save.
  No account selection, existing session or financial policy is changed by loading.
- Updated main/detailed usage, workspace and implementation docs. Validation: 28
  setup/workspace JavaScript and 24 setup unit/API tests passed, including independent
  persisted calendar and exact financial-state checks. Broker responses are simulated;
  interactive desktop/mobile acceptance of these changes remains pending.

## 2026-10-22 — Visible saved broker session checks

- Show step-3 progress and success/failure beside the broker session buttons, with
  a pending check label, duplicate prevention and explicit timeout/retry/login recovery.
  Failed rechecks clear the page's stale verification claim. Login/exchange requests
  also show inline progress/results; lock/auth failures clear private feedback.
- Updated usage, setup, workspace and implementation documentation. UI-only assets
  load on section re-entry or workspace reload; no server restart is required.
- Validation: 25 setup/workspace JavaScript tests and 23 setup unit/API Python tests
  passed, including exact cash and independent persisted database/config/credential
  preservation through mocked profile success, failure and retry. Firefox subsequently
  displayed “Profile verified this run”; no independent broker/streaming acceptance is
  claimed. Coordinate automation returned `noWindowsAvailable`, limiting browser QA.

## 2026-10-21 — One combined paper setup review (0.13.1)

- Replaced the normal CSV/notes/multiple-review workflow with policy selection and one
  source/calendar/stock summary and acknowledgement. Advanced individual controls remain.
- Coordinated disconnect, strategy/calendar installation, held-preserving ranked shortlist,
  explicitly listed eligible reviews for today and feed reconnection. Setup stays Manual;
  Approval/Automatic still need separate confirmation after actual readiness passes.
- Added two-minute account/source-bound previews, durable phase/outcome reporting,
  completed-retry idempotence and interruption recovery without replay. Pending orders,
  used-calendar conflicts, faults and unqualified stocks cannot be bypassed. Held-position
  basis, quarantines and uncovered histories keep their separate review requirements.
- Added visible-parent viewport sizing/positioning for embedded setup and mode/trade confirmation dialogs, private
  summary clearing on lock, navigation/poll guards and specific timeout recovery messaging.
- Corrected Nifty 100 source links; updated main/detailed usage, component, API, architecture,
  implementation and validation guides. No actual account review, mode or trade was activated.


- Validation: 630 Python and 77 JavaScript tests, 92% coverage; lint/format/types, frozen
  offline environment, build, secrets and isolated desktop/mobile browser flow passed.

## 2026-10-21 — Genuine-data strategy preparation and clearer readiness (0.13.0)

- Added in-app Nifty 100/500 source/history acquisition, cancellable background progress,
  official source snapshots/hashes, action/catalog/coverage exclusions and shared historical
  read pacing. Added read-only daily candles without an order-capable broker transport.
- Added explicit calendar/basis/policy reviews, editable session CSV, experimental rules
  choice or separately supplied validated ML, immutable profile installation and hashed
  restart selection. Installation stays Manual and requires disconnected/no-pending state.
- Distinguished prospective current constituent snapshots from historical point-in-time
  membership; retrospective daily execution/ML refuses the former. Retrieval and review
  clocks are not backdated.
- Added per-prerequisite actions, current IST/entry/session information, quote age/basis,
  missing-profile guidance directly beside disabled modes and preserved review form edits.
- Updated main/detailed usage, source/provenance, test, component and implementation guides.
  A real read-only probe verified official sources and one full 60-session broker response;
  no user strategy, review, mode or order was activated by that check.
- Completed a separate genuine Nifty 100 download into private pending-review artifacts:
  65 × 60 completed daily rows, 35 conservative action exclusions. Used a read-only
  catalog connection; no account/configuration writes or review/mode activation.
- Validation: 614 Python tests, 71 JavaScript tests, 92% coverage; Ruff, mypy, frozen
  offline environment, build and secret checks. Isolated synthetic desktop/mobile browser
  checks verified the review/installation flow and shared unlock without exceptions.
- Show saved/proposed session conflicts and allow a separately acknowledged correction
  only for an unused account. Quote/review/execution/instruction usage protects history,
  rechecked after validation. Explain 15:30 exchange close versus 15:15 strategy flatten.
  Block arming during installation and reject mixed-date source downloads.
- Handle temporary index constituents above the named count; explicitly exclude REIT/
  trade-to-trade/dummy rows. Real Nifty 500 parsing retained 495 supported shares from
  501 source rows; no unsupported class is promoted to an equity share.

## 2026-10-21 — Trading desk, approval modes and explainable activity (0.12.0)

Added a default Trading desk with actual mode/activation, clear data blockers,
proposal-first layout and separate Buy / sell activity. Manual, per-trade approval
and automatic paper modes work with reviewed intraday and long-term profiles; legacy
bound intraday can route through the same approval workflow. Protective exits remain
independent. Browser section changes retain one unlock; mobile uses a horizontally
scrollable menu with accessible header Lock. Fixed a misleading initial locked
message after successful desk unlock. No real-order capability was added.

Broader discovery reads reviewed real daily bundles for up to 500 symbols, separates
share classification from catalog EQ, excludes unsupported/unmatched candidates and
previews a held-preserving catalog shortlist of at most ten. Current quotes and
completed intraday/prior-daily rules drive proposals. Rules-plus-ML requires a matching
independently validated model; no synthetic model/data or silent fallback is permitted
in connected profile loading. This does not supply a real bundle/model, automatic
broad-data acquisition or empirically qualified expected-profit ranking. The existing
five-symbol account, capital, mode, reviews and broker session were not changed.

Approval previews enforce expiry, profile/mode generation, live price/signal gaps,
quantity/cash/price/risk bounds, and fresh independent broker checks. BUY authority is
journaled before submission and fingerprint-verified/journaled in the broker transaction;
recovery links a matching committed order or cancels unsubmitted authority without
replay. A second clock check after durable authorization prevents stale execution
through a slow write, clock regression, session/expiry or model-age rollover. Manual
feed callbacks also measure freshness after acquiring the risk lock, so queued stale
quotes cannot fill another pending order using a clock captured before lock wait. SELL linkage is atomic. Mode/data/risk pauses revoke memory authority before
I/O and cancel unfilled desk buys. Short feed disconnects notify the desk immediately,
so reconnecting before the watchdog poll cannot restore authority. Activity retains
manual/legacy/protective origins, actual fills/fees, declined/expired/blocked proposals
and exact cash flow with bounded order/fill cursor pages.

Validation: **582 Python tests**, **62 JavaScript tests**, **92% Python coverage**;
lint/types/secrets, frozen offline environment and source/wheel build checks passed.
Tests include both signal pipelines, real rule evaluation with mocked history, model
threshold revalidation, quote/holding/mode changes, approval quantity bounds, immediate
feed revocation, protective exits without approval, loss-response/restart recovery,
journal corruption, exact independent ledger checks, held shortlist preservation,
more than 100 partial fills and nonblocking risk controls during slow history I/O.
An isolated headless browser verified desktop/390-pixel layouts, no page overflow,
shared unlock, explicit preview/confirmation and ACCEPTED with zero fills in activity.
Synthetic small-fixture loopback p99: desk **0.9474 ms**, activity **0.7265 ms**;
[benchmark scope](benchmark-desk-macos.json) excludes external acquisition, broad-market
load, real-market profit acceptance and Pi/physical-phone evidence. All browser/demo
orders used separate temporary synthetic accounts. User-owned services were not restarted.

## 2026-10-21 — Keep after-hours empty books from disconnecting the feed (0.11.1)

Fixed the verified full-packet parser failure when the broker sends an empty bid/ask
or zero side quantity. Ignore these observations without emitting an executable quote
or disconnecting; preserve valid packets elsewhere in the batch and strict framing,
identity and remaining Quote validation. No financial policy or order capability changes.
Earlier executable depth for an affected symbol immediately loses freshness; manual
candle builders reset and intraday applies its existing stale-data safeguards. A later
valid quote cannot silently rearm automation. Conflicting same-symbol packets in one
batch cannot restore freshness past an observed empty book.
Setup now reports credential-free connection state, bounded retry progress/exhaustion,
fixed failure categories, last transport receipt time and ignored-book count, with
clear recovery instructions. Raw broker messages/authenticated URLs stay private.

Validation: **547 Python tests**, **56 JavaScript tests**, **93% Python coverage**;
Ruff/mypy passed. Unit cases cover each empty side/quantity, mixed packets, unknown
tokens/trailing corruption and retry exhaustion/redaction. A functional pending-order
case keeps the socket connected while proving exact unchanged cash/fees/reservations,
orders/positions and no fill. Unit/service checks also prove prior fresh depth cannot
authorize a new entry, valid data restores freshness, and automation disarms without
losing the transport or rearming. Actual isolated read-only worker check remained connected
for 15 seconds with five ignored books and no usable quotes/orders. User-owned server
and persisted account were left untouched. Port 8004 was no longer listening at the
final check; start the launcher to load the fix and explicitly reconnect. Fresh
market/full-session, sustained device and actual paper-fill acceptance remain pending.

## 2026-10-21 — Shared menu, one workspace unlock and next-step guidance (0.11.0)

Added `/workspace` with Start here, Trading console, Broker & feed setup and Purchases
& SIP. One local in-memory unlock now covers menu navigation. Explicit lock, reload/
new workspace tabs and authorization failures require a new unlock; browser-tab
visibility alone does not log out. Late messages/responses cannot restore cleared
access. Fixed-route same-origin section handoff checks origin, frame window and active
view; only the three section routes permit same-origin framing, while outer/API
routes retain framing denial. Active mutations/dialogs/Setup login windows block
navigation. Changing sections clears unsaved forms/previews, not confirmed server work.

Added authenticated read-only workspace metadata and an actionable guide explaining
feed startup, genuine calendar/basis review, actual entry hours, manual long-term
entries, separately configured five-minute intraday signals and monitoring intervals.
Preserved manual CLI callback capture and the guarded broker popup handoff. Startup
opens the workspace directly and refuses reuse of older UI versions. No new dependency,
financial policy, automatic selector or trading scheduler was added. Updated relevant
usage, API, architecture, security, test and implementation documents.

Validation: **539 Python tests** and **54 JavaScript tests** passed, **93% Python
coverage**; Ruff/mypy, secret checks, frozen offline lock/sync and source/wheel build
passed. Package inspection includes the workspace assets and excludes private
account configs/data. HTTP/DOM checks cover frame policy, actual account cadence,
shared-token integration, pending-action guards, global lock and late responses.
Local read-only account inspection preserves ₹25,000.00, zero fees/positions/pending
orders and matching risk policy. The operator-owned 8004 process was left running;
one manual restart is needed to load the new backend routes. No broker login,
connection change, attestation, arming or order was performed during this change.
Physical-browser/phone/pixel and actual popup acceptance remain distinct pending checks.

## 2026-10-21 — Clarified profit-oriented discovery scope and data gap

Recorded the operator's selection goal for both intraday and long-term paper trading:
broader candidates evaluated for potential net profit rather than a fixed five-symbol
watchlist. Added `stock-selection-plan.md` with data/universe acquisition, chronological
cost-aware validation, independent horizon rankings, explainable UI, execution approval
separation and prospective paper acceptance. This is pending work, not a stock-pick
or profitability claim. Read-only inspection found 5,184 catalog rows, no accepted
quotes/candles, six synthetic daily and sixteen synthetic intraday bundles, and no
declared-real input bundles of those inspected formats. No feed/account change or
order was performed. Linked main usage/implementation status and clarified that
Setup's disabled login requires disconnect only when replacing a session.
Validation: Markdown links, secret-pattern and whitespace checks; documentation-only,
so financial/unit/functional suites were not rerun.

## 2026-10-21 — Browser broker setup and repeatable UI startup (0.10.0)

Clarified all local unlock screens/errors: `TRADING_OPERATOR_TOKEN` is the local
credential, while the Zerodha redirect value is a short-lived request token for
broker exchange. Added `/setup` for authenticated manual-account credentials,
official login popup, origin/window/state-bound token handoff, explicit exchange
and profile verification, catalog import, exact selected-symbol/token/tick validation,
reviewed current/future calendar additions and feed connect/disconnect. Setup cannot
submit/arm, override risk, omit held symbols, change economic policy or rewrite
existing session definitions. Confirmations disclose resumed pending fills/exits.

UI broker values persist in a private atomic server-side file, not browser storage.
Secret request bodies are bounded and errors do not echo credentials. Login states
expire and are consumed before external exchange. Manual CLI redirects remain
supported. Calendar snapshots are written before config replacement; failures leave
the prior live/configured definition intact. The manual feed uses explicit server
credentials without mutating process environment; supervised automation stays separate.

Added executable `scripts/start_ui.sh`, safe authenticated reuse of a matching local
server, and `serve --open`. The shortcut loads trusted private environment files,
defaults to the workspace's existing first-session config, starts without a feed and
opens a browser. Existing server checks reject redirects, proxies and mismatched
account identity. No new dependency was added. Updated main/detailed usage, API,
operator, architecture, security, test and plan documents. External registration,
subscription payment and login/2FA still happen on Zerodha; policy/bootstrap,
complex corporate actions and research/model workflows are not all browser actions.

Validation: **535 Python tests passed**, **45 JavaScript tests passed**, **93% overall
Python coverage**; Ruff, mypy, secret-pattern/whitespace/shell checks, frozen offline
lock verification/environment sync and source/wheel build passed. No dependency was
added. The updated 8004 service returns 200 for console, portfolio, Setup/assets and
health; unauthenticated setup returns 401 and the correct local operator token works.
The selected five-symbol read-only stream reconnects, while calendar/basis gates
correctly leave readiness 503. Exact account reconciliation preserves ₹25,000.00,
zero fees/orders/positions and economic identity. The private `.env` selector was
corrected from the old 8001 config to the existing 8004 account. Actual shortcut reuse
preserved the running PID and opened the browser without another account process.
Private `config/*-session.toml` copies are now ignored by Git/source packaging.
Browser popup/2FA and physical phone/pixel acceptance remain operator-run; simulated
callback/DOM tests do not establish those checks. No actual token exchange, calendar
attestation, price-basis clearance, arming or order was submitted during this upgrade.

## 2026-10-21 — Operator-selected first read-only feed connection

Validated the operator's five supplied symbols/tokens/tick sizes against the local
downloaded NSE catalog and updated only the private first-session feed selection.
Checked actual Kite profile authentication without displaying personal fields or
credentials. Restarted the previously offline 8004 service with read-only streaming;
the authenticated console reports a connected feed and exactly the five selected
symbols. API state and read-only reconciliation preserve ₹25,000.00, zero fees,
no positions and no orders. Saved a separate private connection observation beside
preflight evidence; no account config, credentials or private evidence is committed.

Documented this partial external evidence separately from completed acceptance:
current calendar/long-term basis reviews are missing, full quotes are not accepted
for execution and readiness stays 503. No order, basis approval or calendar change
was performed. Found that a selected instrument is a gold ETF; documented the
existing equity-share fee assumption and missing ETF-specific policy/exclusion.
Instrument-class accounting is now an explicit prerequisite for ETF paper execution
claims. Updated usage, long-term, acceptance and plan guides. No application source
or economic policy changed; validation comprises actual profile/connection/API
observations, read-only accounting, Markdown links, secret scan and whitespace.

## 2026-10-21 — First-session dashboard startup diagnosis

Diagnosed the local first-session config retaining the long-term template's 8001
port and an empty stream selection. Corrected its local listener to 8004 without
changing financial identity or the existing account/database path. Started the
manual console without a feed while the operator selects instruments; an unrelated
older preview on 8001 remains running. Local loopback HTTP verification returned
200 for `/`, `/portfolio`, `/health` and authenticated `/api/status`; `/ready` is
correctly 503 without market/session prerequisites. Pre-start read-only accounting
reconciled ₹25,000.00, zero fees, no pending orders and no positions.

Expanded usage/first-session recovery instructions: preflight is not a server,
its limitations are informational, copied ports must match the browser URL, and
streaming requires an actual nonempty catalog selection. No broker login, market
session review, universe choice or order was performed. The operator's local config
and private credentials are not included in the documentation commit. Documentation
checks cover local links, secret patterns and whitespace; no application source or
financial behavior changed, so unit/functional suites were not rerun.

## 2026-10-21 — First live-data paper-session instructions

Added `first-paper-session.md`, linked from the main usage and horizon/feed guides.
Checked official developer registration, ₹500/month market-data plan, loopback
redirect and daily authentication lifecycle. Documented hidden token exchange,
private environment load order, fresh isolated account/catalog/calendar, manual
intraday API versus long-term portfolio UI, fill verification and daily recovery.
Distinguished the local simulator with production read-only data from the separately
documented, unintegrated Kite sandbox. Corrected older long-term wording that still
said additions/SIP were unavailable. No execution/account behavior changed; no
broker credentials, subscription, login or live-market acceptance was exercised.
Validation: 217 local Markdown targets, documented command help, secret-pattern scan
and whitespace checks passed. A fresh isolated synthetic `portfolio-demo` reconciled
₹25,273.45 cash, ₹22.35 fees and four acquisition lots; it made no broker requests.
Read-only default-account preflight preserved ₹25,000.00, zero fees/positions/orders
and the original policy identity. It correctly remains blocked by the unloaded
operator token, unreviewed current session and unselected catalog; broker entitlement
is unverified. Unit/functional suites were not rerun for documentation only.

## 2026-10-21 — LT3c1 reviewed contributions, acquisition history and SIP (0.9.0)

Started the next portfolio-management dependency after LT3b. Split LT3c into
contribution/SIP foundations, reviewed rebalance proposals and then aggregate
capital coordination, documenting which part is delivered. Added exact cash-budget
purchases and holding additions through read-only previews and explicit confirmation.
Preview hashes bind quote, holding/protections, cash/exposure/risk and plan context.
Existing-plus-new position capacity, fee-inclusive cash budget and shared broker risk
remain enforced. Ordinary manual intents still reject duplicate holdings; additions
cannot loosen stops/targets or override pending/latched exits.

Added immutable explicitly sourced-session SIP schedules, deterministic occurrence
identity and one confirmed attempt/date, due/upcoming/missed/cancelled states,
idempotent retries and atomic cancellation of pending plan residue. Filled shares
remain protected. No automatic deposits, holiday roll-forward, catch-up or unattended
purchase is inferred. Historical acquisition lots group original BUY fills/costs/fees;
current adjusted pooled holdings remain distinct from tax/FIFO ownership.

Added compatible empty tables/indexes, durable approval/plan events/schema, independent
authority/hash/order reconstruction, first-fill holding basis and later cap/clock
checks. Shared sizing was extracted without changing normal intraday economics or
legacy risk hashes. Restart cancels pending entry residue and returns existing intent
state on retry. Existing delivery/action/claim/DP and pooled capital P&L remain shared.
The security import check now parses AST across execution/portfolio/risk/action modules
instead of treating a table name containing `requests` as a network import.

Added authenticated responsive `/portfolio` UI, shared exact money formatter, concrete
preview/dialog, due-plan review, stale/lock/unknown-response handling, spent/reserved
cash, recent purchase orders, current holdings and original acquisition history.
Private values remain in memory/text DOM. Main console links to the new page.
Added deterministic `portfolio-demo` with separate frozen evidence and mutable UI
working copy/config/calendar, leaving configured accounts unopened.

Validation: **511 Python + 36 JavaScript tests, 92% Python coverage**. New cases cover
cash/protections/addition room, partial/restart/idempotency, stale/changed previews,
concurrency/atomic rollback, damaged proof, SIP authority/calendar/missed/cancel,
split→addition→partial sale→DP reconstruction, deterministic journal, isolated CLI,
authenticated/origin/typed API and UI preview/confirmation/lock/staleness/no-retry.
The invented lifecycle independently reconciles six shares sold, four acquisition
lots, ₹22.35 fees and ₹25,273.45 final cash = seed + ₹273.45 capital P&L.
Populated Mac benchmark: preview p99 **0.1784 ms** (1,000 calls), durable reviewed
addition plus next fill p99 **1.5532 ms** (twenty calls), retaining WAL/FULL. Network,
browser, warmup and actual Pi are excluded. Full usage/component/spec/plan docs updated.

Only LT3c1 is complete. Reviewed rebalance proposals, cross-account capital enforcement,
per-lot current/FIFO/tax attribution, funding/withdrawals, custody/settlement, actual
market/device acceptance and all live phases remain pending.

Final local checks: Ruff lint/format, mypy, frozen offline lock/sync and installed
package consistency pass. Sdist/wheel build and all shared/new console resources
load outside the repository. Secret checks and local links in 23 Markdown files pass;
online advisory audit reports no known vulnerabilities. Read-only preflight preserves
the original account at ₹25,000, zero fees/events/positions/orders and its original
risk hash; operator/calendar/broker/device readiness remains explicitly incomplete.
The separate demo copy runs at localhost:8003/portfolio; actual HTTP asset/CSP/auth/
four-lot checks pass and frozen source hashes remain intact while it runs. The page
was opened; browser pixel/physical-phone acceptance remains pending permissions.

## 2026-10-21 — LT3b daily quote execution and separate chronological ML (0.8.0)

Implemented the next long-term dependency after completed daily screening. Added
`daily-backtest`, `daily-labels`, `daily-train` and `daily-execution-demo --with-ml`,
using matching raw daily/quote bundles, reviewed sourced calendars, strict clocks,
current PIT membership and applied corporate-action reference basis. Prior daily
features advance once by availability with bounded windows and rare late-row rebuilds.
Daily decisions rank only simultaneous candidates and retain session-limit/screen exits.

Portfolio execution reuses the exact Decimal transactional delivery broker, risk,
latency/depth/adverse ticks, fees/DP, action and cash ledger. Fresh later quotes drive
fills; unfinished positions/orders/claims and missing coverage are preserved. Calendar
source definitions are retained for corporate-action review. Independent label trials
retain favorable/adverse completed full-entry outcomes and explicit unfilled, partial,
interrupted, stale/gap, capacity and unresolved exclusions. Cash-specific dividends/
receipts censor counterfactual trials rather than guessing different account deductions.

Added separate daily feature/model identity with whole-session interval purge/embargo,
train-only scaling, separate sigmoid calibration, fixed logistic baseline and frozen
final holdout. Coefficients freeze before holdout diagnostics; unsuccessful evidence
is retained but loading fails. Model availability follows source/label/session-close
evidence plus embargo, with a strictly later independent scored replay. JSON-only
pure Python scoring, context/hash/audit/cash checks, synthetic provenance/override and
existing independent risk remain enforced. Shared numerical helpers gained structural
types; intraday feature/model authorization and long-term service guards are unchanged.

Added responsive private self-contained portfolio/label/validation/scored dashboards:
exact money, IST clocks, search/view/clear, incomplete exposure, explicit label-vs-
portfolio meaning, chronological checks and useful failure/next-step guidance. Updated
main usage, detailed daily execution guide, plan/specification and corresponding
component docs. Standing documentation requirement remains in root AGENTS.md.

Validation: **479 Python + 29 JavaScript tests, 92% Python coverage**; financial
reconstruction/later fills, overnight/session-limit exits, sourced split replay,
dividend routing, exclusions, chronology/purge, audit/model tampering, failed gates,
no training imports during scoring, isolated CLI and UI exact-money/search/empty/
incomplete/failed-model cases. Full synthetic workflow produces 150 labels (100
positive, 50 adverse) and a distinct ten-session scored replay; no market edge is implied.
Twenty-run Mac durable replay p50 **35.4865 ms**, p99 **47.7677 ms**, including
219 daily bars/36 quotes/nine trades, validation/hashes/report writes. Warmed screen
p99 **0.0074 ms** over 1,000 observations. Network, training/label trials and Pi excluded.

LT3c lot/SIP/rebalance/aggregate capital mechanics are next. Actual source/model
acceptance, historical fee matching, custody/settlement and device/browser pixel
acceptance remain pending. No live route or connected long-term automation was added.

Final checks: Ruff lint/format and mypy pass; frozen offline lock/sync and installed
dependency consistency pass; source distribution and wheel build, with all three UI
asset groups loaded/rendered from the wheel outside the repository. Secret-pattern
and 22 Markdown-file local-link checks pass. Online `pip-audit --skip-editable`
reports no known vulnerabilities. No dependency was added. Read-only preflight
preserves the original intraday account at ₹25,000, zero fees, zero journal events,
no positions/orders and the unchanged legacy risk hash. Missing operator/session/
broker/device prerequisites remain disclosed; local trading readiness is not claimed.
The generated offline portfolio HTML was opened. Browser pixel/phone verification
remains pending the previously unavailable computer-use permissions.

## 2026-10-21 — LT3a daily research and explanatory dashboard (0.7.0)

Continued after LT2 into the next dependency of the long-term roadmap. Added
`daily-research-demo` and `daily-analyze`, strict bounded raw daily bundles with
explicit price/basis availability, share factors/distributions in previous-share
units and point-in-time universe inclusion/exclusion/re-entry. Missing, late or
excluded data cannot be forward-filled into a candidate; gaps/re-entry reset windows.
Explicit historical as-of clocks prevent future valid prices/benefits changing
features/ranks. Membership must be knowable before its effective session opens.

Added streaming Decimal gross-return/trend/volatility/turnover screening with bounded
rolling state, binary-search membership and deterministic qualified-candidate ranks.
The gross index assumes same-close distribution reinvestment before costs, tax or
payment delays; it is not an execution backtest or the LT2 cash ledger. No account,
broker, trading endpoint, model approval or risk-policy change was added.

Added a self-contained responsive offline research dashboard with provenance/IST
analysis clock, candidate/data summary cards, searchable/filterable/sortable results,
plain-language reasons, metric definitions and useful empty/incomplete states.
Accessible labels, column scopes, keyboard scrolling/focus and touch-sized controls
support inspection. Untrusted values render as text; escaped embedded JSON and
hash-bound CSP need no network dependencies. Analytical display rounding is disclosed;
raw Decimal values remain in JSON. Private report files/source/Python hashes and a
last-written artifact manifest support reproducible review and mutation detection.

Added an invented six-symbol ninety-session fixture retaining an unfavorable trend,
illiquidity, missing data, re-entry and historical exclusion beside one candidate.
Added detailed daily usage and updated main/long-term usage, roadmap/specification,
API, architecture, research/model, console, risk, operations, threat, acceptance,
performance and test documentation. LT3b quote-executed daily strategy/ML and LT3c
portfolio/lot/SIP/rebalance/allocation remain pending; no original live phase advanced.

Validation:

- **420 Python tests and 23 JavaScript tests passed**, **92% Python coverage**.
  Daily analysis **97%**, strict input **93%**, renderer/demo **100%**. New cases
  exercise future-prefix invariance, late basis/price, corporate benefit math,
  membership/gaps, malformed/ambiguous input, source mutation, artifacts and CLI
  isolation; UI cases verify text safety, filtering/sorting/reset/focus and empty states.
- Thirty-run 538-bar/six-symbol Mac benchmark: p50 **8.0033 ms**, p95 **15.2105 ms**,
  maximum/p99 **20.4069 ms**, including loading/validation/analysis/input/Python hashes.
  Fixture creation, HTML writing, network/history, execution and actual Pi are excluded.
- Ruff lint/format, mypy, secret-pattern/Markdown-link checks, frozen offline lock,
  unchanged-dependency audit, wheel/source builds and extracted report assets passed.
- The offline dashboard is generated for review. Pixel-level browser/handset checks
  remain blocked by pending computer-use permissions; no visual acceptance is claimed.

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
