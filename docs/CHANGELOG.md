# Change log

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
