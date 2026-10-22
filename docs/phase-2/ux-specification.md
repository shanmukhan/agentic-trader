# Phase 2 — navigation, screen and interaction specification

Status: **design contract 1.0, 22 October 2026 IST**. The user approved Phase 2 after
the [audit](../UX_AUDIT.md). This document specifies Phase 3 work; it does not claim
new routes, features or financial behavior are installed. Runtime remains 0.14.0.

## Product and navigation decisions

Prioritize months-to-years investing with a light, white-surface interface. Retain
working paper workflows, risk gates, corporate-action accounting and CLI research.
Do not add intraday features or a real-execution choice. Keep technical evidence in
progressive disclosures while making material restrictions and consequences visible.

[Navigation manifest](navigation.json) is the machine-readable screen/alias contract.
Future canonical workspace hashes use `#screen/section`, with the same bounded anchor
validation and origin/window checks as today. All twelve destinations have one owner:

| Group | Screen and canonical hash | Owner of the user's task |
|---|---|---|
| Overview | Dashboard `#dashboard` | Glanceable account value, warnings and next action; links to tasks |
| Research | Stock Discovery `#discovery` | Filter/rank/compare saved supported research; maintain research watchlists |
| Research | Stock Analysis `#analysis` | Inspect one symbol's history, indicators, coverage and evidence |
| Plan & simulate | Strategies `#strategies` | Draft, validate, backtest and install explicitly reviewed policy versions |
| Plan & simulate | Backtesting `#backtesting` | Start/cancel isolated research jobs and inspect immutable results |
| Plan & simulate | Paper Trading `#paper` | Review proposals, select an explicit mode and monitor pending orders |
| My investments | Portfolio `#portfolio` | Aggregate holdings, allocation/income; manual purchase/SIP subflows |
| My investments | Trade History `#history` | Filter recorded decisions/orders/fills and inspect exact evidence |
| Controls | Risk Management `#risk` | Review exposure/limits/basis; emergency and protective controls |
| Controls | Broker & Data `#broker` | Session/login, catalog, subscriptions, reviewed sessions and feed recovery |
| Controls | Settings `#settings` | Local preferences, active config and reviewed changes |
| Help | Learning Center `#learn` | Definitions, examples, failure explanations and contextual lessons |

Aliases preserve `desk→dashboard`, `activity→history`, `console→risk`, `setup→broker`,
`overview→learn`. Existing analysis/strategies/portfolio links retain meaning; the old
Portfolio purchase form becomes a Portfolio subsection, not a new automatic order.
Legacy shortlist/setup/basis fragments are listed in the manifest and must reveal the
correct section even while the relevant action is disabled. Current route behavior is
unchanged in Phase 2. Redirects never confirm an action, change account or reset an intent.

The desktop sidebar groups links with headings and highlights the exact destination.
Below 768px use an accessible navigation disclosure with all twelve destinations,
current-page label and a reachable Help entry. No sideways-only hidden destinations.
Navigation closes a mobile menu only after the destination guard passes. Back/forward
must restore route/section, not private preview authority. Do not persist bearer tokens
in history, URLs, cookies or browser storage. Do not create a second unlocked account.

## Shell and information order

Header: Agentic Trader, **Paper only**, named account/horizon, current mode, data-snapshot
time and a labelled route to emergency controls. No live trading selector. Locked
state hides private amounts and credentials; closing the browser is not presented as
stopping the server. A generic unlocked badge is not a feed/quote/readiness badge.

Content: page title and one-sentence purpose, task-level next action, relevant data,
then supporting evidence. Dashboard leads with financial values; a blocker affects the
next-action panel without replacing all holdings/history with a long instruction wall.
Each component owns a concise Loading, Empty, Missing, Stale, Incomplete, Failed or
Available state with a time/source and safe recovery. Use actual underlying reason codes
and human wording; a failed read must not silently replace retained values with zero.

[Offline design prototype](prototype.html) lets the user review grouped navigation,
example missing/stale states, and a contained confirmation. It is **not connected to
an account**, does not call APIs and contains no financial results. Its template-only
controls are labelled/disabled. Its artificial state picker is a design-review tool,
not a proposed account-setting control. No broker or order action can execute there.

## Screen contracts

Every screen includes paper-only anchoring, data/source dates and an exact-data path.
Dates/operations display in IST; canonical server timestamps remain aware UTC. Money
and quantities preserve [financial-metrics.md](financial-metrics.md); formatting is not
permission to recompute a server financial amount with JavaScript Number.

### Dashboard — INV-UI-01

Show estimated net portfolio value, available cash, remaining holding cost basis,
net unrealized P&L; secondary realized capital P&L, received income and properly defined
account return. Each has a compact definition/coverage state. No unknown claim or stale
mark is silently included as zero. A dated daily P&L is not called Today when its baseline
has not rolled. The allocation chart uses cash plus gross held-share value, with claims shown
separately outside its denominator; unknown sectors form an explicit Unknown category. No invented equity or allocation curve.

Follow with one next safe action, feed/quote/calendar/strategy state, top-ranked eligible
research and recent decisions with scope. A rank is not a profit probability. Benchmark
shows Not configured or Insufficient coverage until a compatible genuine series exists.
Dashboard links to Paper Trading rather than duplicating approval controls in two places.
A read must not expire proposals, poll execution, rearm, subscribe or download history.

### Stock Discovery — INV-UI-02

Inputs: immutable reviewed run, as-of date, supported universe and explicit filters.
Present symbol, share classification, coverage, turnover, momentum/trend, volatility,
drawdown and documented rank. Where no fundamental provider exists, show Unavailable
with source requirement; do not activate zero-valued filters or manufacture rankings.
Missing data remains visible/excluded by policy, never a hidden pass. Each row expands
Why it passed / Contradictions / Missing evidence / Risks and exact source windows.

Users can compare two to four supported candidates on the same calculation date/basis.
Named research watchlists are distinct from execution subscriptions; saving one does not
change subscriptions or risk authority. Apply an execution shortlist only through the
existing disconnected/Manual/no-pending reviewed workflow, retaining held symbols.

### Stock Analysis — INV-UI-03

Supported-symbol lookup is limited to verified catalog/research identifiers with explicit
coverage, not a promise of complete all-NSE history. Daily/weekly/monthly candles and volume;
selectable SMA50/200, EMA, RSI, MACD, ATR, drawdown and declared support/resistance.
Reference formulas/warmup/gap/partial-period rules are in
[strategy-and-data-contracts.md](strategy-and-data-contracts.md). Do not add new minute
strategy features; retain existing minute views under their legacy supported workflow.

Chart interaction: pan, zoom, reset view, crosshair with exact OHLC/time, accessible data
table, keyboard-reachable equivalent selection. A maintained library can be locally
bundled after dependency/license/CSP evaluation; no mandatory Plotly/framework migration
is approved. No external script request carries operator/broker credentials. Preserve
source basis and unavailable intervals; distinguish historical data from current quote
usability. Relative strength and fundamentals remain unavailable without traceable inputs.

Evidence panel: bullish, bearish, missing-data and risk observations tied to actual
calculations. No “buy now”, invented model confidence or performance claim from a chart.

### Strategies — INV-UI-04

Separate installed legacy policy, new drafts and validated artifacts. Each shows horizon,
universe, entry/exit, rebalance, sizing, data/basis, model and version identity. Preserve
the current 20-session policy and compatibility as legacy; do not rename it as a
months-to-years strategy. New templates (trend, momentum, quality/value, rebalance, SIP)
are hypotheses. Unavailable fundamentals disable dependent templates with an explanation.

Draft → input validation → isolated backtest → review → explicit installation → Manual.
Paper mode activation stays a distinct confirmation with current readiness. Required
investment parameters stay unset until reviewed; no aggressive prefilled new limits.
A download/review/install failure shows durable completed phases and safe recovery.
Never backfill or precheck a corporate-action or exchange-session attestation.

### Backtesting — INV-UI-05

Inputs: immutable valid data bundle, exact strategy version, date range, predeclared
execution/cost/benchmark assumptions and evaluation split. Show available historical
membership, daily/quote path, action and benchmark coverage before starting. Daily OHLC
alone cannot create a broker-like intrabar fill path. A current-constituent snapshot is
marked survivorship-biased and cannot masquerade as historical membership.

Start creates an isolated bounded research job, not a paper-account order. Progress,
Cancel and interrupted/restart states remain explicit. Cancel requests stop work;
partial output is incomplete and cannot become a validated final report. Report views:
overview, equity/drawdown, costs/trades, monthly returns, benchmark and validation/coverage.
Show metric NA reasons, open/censored positions and raw exact exports. Historical outcomes
never activate a strategy or change account limits. No automatic download/subscription
or retry of an uncertain mutation. Dataset/strategy errors link to the responsible task.

### Paper Trading — INV-UI-06

Owns pending proposal queue, expiry, operating-mode controls and pending-order status.
Manual / Approval / Automatic are paper authority states, not promises of a trade.
Show source session/signal, expiry, reason, estimated costs/risk, available review and
explicit decline. Proposal expiry is server-authoritative. A cross-screen read-only
pending count may be added without approving or resetting identities; notifications
are optional and user-permission based. No single-key approval shortcuts.

Review obtains a fresh server-bound preview; confirm revalidates expiry, revision,
price, quantity and financial bounds. Material dependency changes or expiry require a new review; a newer usable quote
may confirm only inside the original reviewed quantity/price/cash/risk bounds.
Cancellation, rejection, already-handled daily signals and pause causes are distinct.
An accepted order reserves capacity; fills require later usable quotes/liquidity.
Mode changes retain existing cancellation/protection consequences and explicit consent.

### Portfolio — INV-UI-07

Default: remaining aggregate holdings with quantities, pooled cost, current mark/time,
estimated liquidation value, net unrealized P&L, stop/target and valuation/basis state.
Separate allocation, cash/reservations/buffer, income/claims and acquisition history.
Original filled lots are not FIFO/tax-lot current ownership. Unknown claims block complete
valuation/return but do not erase known components. Do not combine independently seeded
accounts into one capital pool or add historical label-trial accounts to the portfolio.

Manual purchase/addition and SIP are subsections using existing preview/confirm routes.
A budget is a cash cap including costs, not a deposit. Additions retain holding protection
unless a separately supported reviewed action changes it. A due SIP requires its own
review; missing dates do not catch up. Exits identify the whole remaining holding and
confirm the queued request; do not claim a queue has filled or settled.

### Trade History — INV-UI-08

Distinct views for decisions, orders, fills and original acquisitions; filters for date,
symbol, side and state with cursor scope. Display proposed/authorized/submitted/updated/
filled times independently. Cancellation without an order means no trade. Partial fills,
fees, cash debit/credit, original reason and mode/authorizer remain inspectable. Cash
received/spent is not capital P&L. Exports reflect their exact scope and provenance.
Avoid automatic list replacement while reading expanded evidence; provide Refresh.

### Risk Management — INV-UI-09

Lead with current effective limits, exposure, available cash/reserve, known/unknown
concentration, drawdown and outstanding blocks. Add per-limit definitions/current usage;
ceilings are not targets. Policy edits require strict coupled validation, current-version
binding, preview and explicit confirmation or a new-account migration where required.
A disabled limit cannot be bypassed by changing only the UI. No new aggressive defaults.

Keep emergency kill, queued flatten/holding exit, entry disarm and reset/arm semantics
as documented today. The existing immediate emergency-stop path is not silently converted
into a delayed confirmation. Consequential queued exits/configuration/activation use their
review/confirmation contracts. Reset does not rearm. Corporate-action review/quarantine
requires actual evidence and never claims true merely to clear a warning.

### Broker & Data — INV-UI-10

Separate session saved/verified/expired, feed requested/connected, usable quotes and
history entitlement. Retain six progressive source/session/catalog/calendar/feed steps,
inline progress, duplicate suppression and correct recovery. Defaults 09:15–15:30 IST
remain editable but do not approve a date. Cross-year preparation needs reviewed sources
for every relevant year; a weekday guess must not clear insufficient coverage.

Typed expiry, entitlement, throttle, outage, malformed and configuration states show
appropriate next actions. Token exchange is not blindly retried. Never return saved API
secrets/token values in reads, URLs, logs or previews. Catalog changes present sourced
version/diff and preserve held/pending/historical identities. Read-only views do not
connect. Connection confirmation lists selected symbols and pending-fill/protection
consequences. It must be visible before focus moves into it, at any supported scroll.

### Settings — INV-UI-11

Read-only current account/horizon/strategy, paths as safe labels where meaningful,
version and operational configuration first. Local display preferences do not grant
financial authority. Separate Restart required / Effective now / Requires new account
for changes. Any future policy editor uses Risk Management's review rather than an
alternate unsafeguarded endpoint. Do not expose stored secrets; credentials belong in
Broker & Data's explicit local setup. No remote binding, live order toggle or automatic
notification permission. Destructive data/account changes are outside this design.

### Learning Center — INV-UI-12

Short lessons: paper versus real, candles versus quotes, bid/ask/depth, stale prices,
fees/basis, P&L/returns, volatility/drawdown, position sizing, corporate actions, SIP,
backtest biases and decision outcomes. Contextual term help links here and is reachable
without hover. Teach why waiting/reviewing/rejecting may be appropriate. Source dates,
limitations and uncertainty are visible; educational examples are labelled synthetic.
A lesson never automatically fills risk values, approves a proposal or recommends a stock.

## Shared interaction contracts

### Confirmation and overlay — INV-COMP-01

Retain a native `dialog` top layer inside each currently isolated same-origin section,
backed by **one shared local placement/lifecycle helper**. Use the intersection of the
parent visual viewport and iframe bounds, convert parent coordinates into child
coordinates, reserve 16px padding and cap height with internal scroll. Horizontal
bounds follow the visible content area; 320px widths and 200% zoom must not clip it.
Compute placement **before** `showModal` moves focus, then follow parent/visual viewport
scroll and resize while open. Use no account data in postMessage geometry messages.
If no visible intersection exists, safely reveal the triggering section before opening;
do not create a zero-height confirmation or silently run the action.

Focus the least consequential available action with `preventScroll`, contain focus
natively, retain accessible title/description and return focus to the triggering
control on close if present. Escape/Cancel clear pending authority and remove listeners.
Lock/navigation/pagehide clean up pending UI and ignore late responses; they cannot undo
an already received action. Long dialogs keep title/consequences visible and controls
reachable; never obscure holdings consequences behind an optional tooltip.

Guard transitions: closed → reviewing → review-ready → submitting → success/unknown/
rejected. One confirm submits once; duplicate clicks do nothing. Do not replace a fresh
server preview with client arithmetic. Unknown outcomes require reading recorded state
before retry, not an automatic second mutation. Unsupported/expired previews close or
disable confirmation with a clear recovery action. Emergency stop preserves its existing
immediate path. Placement fixes do not change the meaning/timing of financial authority.

### Async states and forms — INV-COMP-02

One visible pending label/live status near the initiating control. Keep user edits during
background reads. Separate a timeout of a pure GET from the unknown result of a mutation.
Do not announce every market tick. Reads may be retried explicitly; no silent write retry.
Invalid fields link to readable errors. Group human attestation separately from defaults;
no prechecked review. Navigation guards active requests, login popups and confirmations.
Abandoned ordinary unsaved drafts are warned about only when information would be lost;
do not add arbitrary permission prompts to simple reads.

### Exact metric, status and table — INV-COMP-03

A metric receives server-decimal value/null, named definition, state, observed/as-of time,
coverage and unavailable reason. Keep quantity/currency/percentage units explicit. Null
is “Unavailable”/“Not configured” with a reason, never zero. Retained stale values display
their stale label beside the value. A state badge uses text/icon plus color. Stable
semantic tables provide header scopes, caption, numeric alignment, keyboard-accessible
row actions and mobile row-detail/card adaptation. Scope/filter/page counts are explicit.
No decorative gain arrows, performance curves or market-open badges without real data.

## Visual system and validation

[Design system](design-system.md) defines tokens, spacing, typography, responsive bounds,
contrast targets and component variants. [Acceptance plan](acceptance-plan.md) binds
screen/component IDs to rendered, workflow, security and financial validation. The
prototype is a design review surface; neither it nor screenshots establish a financial
calculation, broker acceptance or production accessibility conformance.
