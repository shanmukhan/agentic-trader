# V2 Phase 3 frontend implementation — 0.15.0

Subsequent **0.18.0** adds [Investment policy drafts](investment-policy-drafts.md) within
Strategies at `#strategies/investment-policy`. Its metadata-driven four-group form has
labelled blank/null choices and exact decimal text inputs. Incomplete drafts are allowed;
invalid values and inconsistent caps are rejected. Preview is nonpersistent; an explicit
shared-dialog acknowledgement saves an immutable snapshot. Editing a copy preserves the
original, and an identical save returns its existing identity. **Specified** grants no
activation, execution or backtest capability. The installed-strategy card and old anchors
remain accessible.

This controller does not poll. Refresh reads saved drafts; opening/previewing creates no
storage. Unsaved edits and uncertain outcomes guard navigation. Unknown save outcomes
must be refreshed/reconciled before an explicitly reviewed same-content retry. Lock,
pagehide and authorization failure clear form/preview/saved content and ignore late
responses. Drafts are never persisted to browser storage. The pure CLI schedule preview
is documented separately; the browser form installs no calendar or future execution.

Subsequent **0.17.0** adds a dedicated registered [Backtesting](browser-backtesting.md)
page with runtime availability, input review, confirmed run/cancel, saved outcomes,
verified exact report tables, compatible-resource comparison and uncertain-request
reconciliation. Its polling reads research state only; launch fails closed on the
implementation Mac and other-platform browser isolation is unsupported. Portfolio adds
[exact current allocation](portfolio-analytics.md), withholding weights when held marks
are missing/stale. It does not add target/rebalance or accepted account return history.

Version **0.16.0** added [price research](investment-research.md) and richer Discovery
rank explanations. The Phase 3 boundary below is historical; it is superseded only by
the narrower 0.16–0.18 additions. Fundamentals, executable new investment strategies, accepted
portfolio return/benchmark analytics and allocation/rebalance mutations remain unavailable.

This release implements the shared confirmation component, twelve grouped destinations
and a saved-state frontend over existing research and paper accounting. It keeps
FastAPI, SQLite/Decimal, local assets and guarded same-origin section frames. It does
not implement all future V2 engines. [Phase 2](phase-2/README.md) remains the design
reference, with later contracts explicitly distinct from these installed routes.

## Start, inputs and navigation

Run `./scripts/start_ui.sh` from the project directory and use its `/workspace` URL
(normally port 8004). Restart an older owning process gracefully first; 0.15.0 adds
Python routes and the launcher refuses a different UI version. Unlock with your local
`TRADING_OPERATOR_TOKEN`. Do not use a Zerodha request/access token as the unlock value.

Use [the route table](workspace.md#menu-and-unlock-behavior). At widths of 767 CSS
pixels and below, open **Menu · current screen** to reach every destination. Changing
sections clears unsaved local forms except that the policy-draft screen requires saving
or discarding edits first. Requests, login popups and confirmations guard
navigation, including same-screen anchor changes and the two Portfolio subviews.
Tokens stay in memory and are handed only to the current same-origin frame/path.
Reload, Lock, pagehide or authorization failure clears private content; late responses
cannot restore it. Lock does not stop an already running feed, undo an accepted server
action, close holdings or revoke server automation.

## Saved Dashboard and Portfolio

Dashboard shows exact server decimal strings for estimated net portfolio value,
available virtual cash, remaining holding cost basis and net unrealized P&L. It also
shows saved feed/session/mode/arming status, a next action, up to five saved candidates
and ten materialized proposal summaries. A proposal without a linked order is not a
completed trade. State is **at last refresh**; refresh never retries/approves a proposal.

Portfolio adds realized capital P&L, charged fees, reserved purchase cash, dated daily
accounting change, held shares and their quote coverage. Values inherit existing
account formulas: cash plus net held-share estimates and valued receivables; remaining
cost includes allocated purchase costs; net unrealized result subtracts that basis
from the net liquidation estimate. Net estimates already include assumed exit costs.
Reservations and delivery buffers restrict spending and are not completed purchases.
The displayed stored accounting-day baseline is not rolled by viewing this screen.
A daily accounting change is not a lifetime return.

Valuation explicitly distinguishes cash-only (`empty`), fresh, stale and incomplete
coverage. Saved bids or cost fallback can remain in a stale estimate. Unvalued
fractional claims are excluded and make the estimate incomplete; valued receivables
and received income are separately labelled. A current quote is not a guarantee of
exit liquidity. Dataset-declared synthetic context is labelled; historic broker/replay
provenance is otherwise unknown rather than certified.

**Purchases & SIP** opens the existing purchase/plan preview and confirmation page.
**Review holdings and request an exit** opens its existing aggregate holding workflow.
The 0.15 summary introduced no new financial engine. The later 0.17 current allocation
is a separate read-only method, not a purchase/target/rebalance or account-return workflow.

## Stock Discovery

Prepare and explicitly install genuine data through **Strategies** first. Discovery
reads the last installed prior-daily calculation; it does not refresh strategy data or
search the whole broker catalog. Search by symbol, filter result and sort by rank,
gross historical return, daily volatility or average turnover. Sorting uses exact
decimal comparisons, including values beyond JavaScript's safe integer range.

Expand **Why this result?** to inspect observations, last completed session, raw
close, availability, trend evidence, failed/missing checks and saved feed subscription
membership. Research rows are bounded to 500 and truncation is explicit. A candidate
is not an order, expected return, recommendation or probability of profit. Gross
research returns are before execution costs and tax.

Select two to four rows to compare actual saved metrics from the same recorded
completed session. Rows requiring missing data cannot be selected; differing coverage
blocks comparison. Clear or refresh to reset selections. They are memory-only and
never change subscriptions. Persistent named watchlists, fundamental filters, sector
classification, scores, drawdown and benchmark analytics remain unavailable.

## Other destinations

- **Stock Analysis** preserves [saved candle/indicator charts](market-analysis.md).
- **Strategies** preserves [preparation and explicit setup review](strategy-preparation.md).
- **Paper Trading** owns modes, full readiness, quote warnings and proposal approvals.
  Approval and Automatic still require their installed policy and independent gates;
  changing mode does not replay previously handled daily signals.
- **Trade History** preserves recorded orders, fills and proposals without an order.
- **Risk Management** preserves current-basis review, exposure and emergency controls.
- **Broker & Data** preserves the broker wizard and explicit connection confirmation.
- **Backtesting** now has the separate 0.17 [registered-job workflow](browser-backtesting.md).
  Review runtime capability before launch; unavailable OS isolation keeps it disabled.
  Saved report values are exact event-time simulation evidence, not invented daily metrics.
- **Settings** shows whitelisted active limits, horizon, policy and mode read-only.
  It omits credentials and local file paths and links to existing reviewed workflows.
  The current holding-session cap remains explicit; a long-term account label does
  not establish a months-to-years investment strategy.
- **Learning Center** searches eleven application concepts: paper execution, quote
  freshness, price basis, proposal/order/fill states, modes, basis, fees, research,
  backtest bias, risk and performance coverage. Its checklist links to existing setup;
  completing navigation never activates the account.

## Shared confirmation lifecycle

`dialogs.js` is used by Setup, Risk, Purchases, strategy review and mode/trade approval.
It positions the native dialog **before** autofocus in the visible parent viewport
intersected with the frame content, with 16px margins. It handles scale/borders and
visual viewport offsets, follows scroll/resize and content-size changes, and bounds
long review scrolling with sticky heading/actions. It allows one modal per document.
The shell menu becomes inert while open; the workspace Lock remains available.

Initial focus is Cancel. Cancel/Escape, native closure, Lock and pagehide clear pending
UI actions and restore trigger focus where available. Cancel posts nothing. Explicit
confirmation consumes the pending action once, then existing server review/risk/
idempotency controls govern the request. If a frame is offscreen it is revealed and
remeasured; no usable intersection means cancellation without submission. Return to
the section and review again. After a timeout, inspect saved status and activity
before retrying; an already received server mutation may have succeeded.

## Read API and recovery

The six new pages use authenticated `GET /api/workspace/views`, schema version 1.
It takes one SQLite `BEGIN` read cut on an independent `mode=ro` connection under the
engine lock and returns bounded saved research, ledger, configuration and materialized
proposal facts. It does not call desk view/tick, expiry, analysis refresh, broker APIs,
downloads, engine poll, reconciliation or recovery constructors. Failures return a
sanitized 503 and do not reach the generic mutation-fault handler. Credentials and
configuration paths are absent. See [API contracts](api-contracts.md).

**Refresh saved status** rereads this endpoint. After six seconds the display labels
itself stale; these saved-account views perform no automatic refresh or broker request.
The separate 0.17 Backtesting controller polls research job state while visible/unlocked
as documented in [browser-backtesting.md](browser-backtesting.md). A failed refresh retains
existing content only with an explicit stale/error label. Retry manually after checking
the server version/availability. HTTP 401/403 clears private content and requires an
unlock. Ten-second read timeout aborts and is safe to retry because it requested no
account change. Reads are coherent snapshots, not promises that readiness stays valid.
The existing operator pages and background workers retain their normal workflows.

## Validation and limits

Automated validation on 22 October 2026: 670 Python tests passed with 8,405/9,116
statements covered (92.20%); 148 Node UI tests passed; Ruff and mypy (99 source files)
passed. Python tests include independent SQLite fill/fee/cash/reservation reconstruction,
partial fills, stale marks, a simulated corporate-action fractional claim and whole
database equality before/after reads. Reads beyond proposal expiry/account-day changes
preserve mode/revision/materialized state. Read-only connections reject writes; a failed
read does not fault/revoke account authority. Functional checks serve all twelve routes
with framing/no-store controls, balanced markup and resolvable accessibility labels.

UI tests include exact rendering, missing/schema/error states, four-stock comparison,
coverage mismatch, pure GET behavior, origin/source/path guards, legacy aliases, mobile
menu state, modal navigation guards, late responses/lock/pagehide, and single-submit/
cancel behavior. Geometry simulations cover 360/768/1440px widths, deep scroll,
visual viewport keyboard/zoom offsets, scaled bordered frames, content resizing,
focus-before-open, offscreen refusal, native close and listener cleanup. These are
simulated DOM/layout inputs, not a rendered browser acceptance suite.

A disposable read-only local preview opened the locked twelve-destination shell in
Firefox. Interactive verification could not finish while Firefox was being actively
changed by the user; no operator account or broker action was used. Desktop/mobile
screenshots, actual keyboard/touch/200% zoom behavior in Firefox plus a second engine
and sustained real-feed/device acceptance remain open gates. Passing tests do not
certify profitability, live-market correctness or production financial integrity.
