# UX audit — Agentic Trader V2

Audit date: 22 October 2026 IST. Baseline: commit `2d5c208`, application 0.14.0.
Scope: Phase 1 of [improvements.txt](../improvements.txt). This is an assessment and
proposed design, not acceptance of a completed V2 or permission for implementation.

## Evidence and limits

Reviewed the reference `images/Agentic Trader Dashboard UI Collage.png`, the user's
Firefox screenshot of the feed-confirmation dialog, all operator-page HTML/controllers,
the shared stylesheet/bridge, API contracts and UI tests. Existing 0.14 improvements
are part of the baseline: a light sidebar, exact portfolio metrics, separate Strategies,
progressive broker steps and saved-data analysis. Replacing them from scratch is not
justified. Reference balances, signals, backtest results and sample companies are
visual examples only; none may be copied as real account data.

The repository's Node tests simulate DOM behavior; HTTP/markup tests verify served
shells and label targets. They do not render CSS or establish mobile usability. Earlier
Firefox automation returned stale/mismatched captures and no isolated supported browser
was available. A read-only Firefox inventory during this audit found the browser in
active use on another page; it was not navigated or resized. No new desktop/mobile
rendering acceptance is claimed here. The supplied
screenshot establishes a real modal-visibility issue in the page version shown.

The baseline now includes a setup-dialog viewport patch in `api/static/setup.js:11`:
position before modal focus, bounded visible frame intersection, scroll/resize and
visual-viewport listeners, cancellation cleanup. An additional disposable Node harness
using the real controller passed scrolled-frame/resize/keyboard-viewport geometry and
cancel-without-POST checks. This is not a committed regression test or browser proof.
The user's rendered issue therefore remains an acceptance item until checked in Firefox.

## Findings by severity and operator impact

Severity: High = can obstruct a consequential decision or materially mislead; Medium =
repeated workflow friction/missing requested capability; Low = consistency/maintenance.
These are product/usability ratings, not claims of a security exploit.

| ID | Severity | Finding and evidence | Impact | Recommended acceptance condition |
|---|---|---|---|---|
| UX-01 | High | Modals use multiple placement models. Setup has a new parent-visible-viewport calculation (`setup.js:11`), desk/preparation separate parent-offset helpers (`desk.js:25`, `preparation.js:19`), while purchases and risk confirmations use native iframe-centered dialogs (`portfolio.js:80`, `dashboard.js:230`). | Confirmation text/buttons can be outside the operator's visible area; the supplied screenshot demonstrates this for Setup before its patch. Similar dialogs need testing, not assumptions. | Reuse one tested placement/lifecycle component; every dialog visible at 360/768/1440 widths, deep scroll, zoom and keyboard; focus returns, Escape/cancel send no mutation and confirmation sends once. |
| UX-02 | High | Application terms call a 20-session delivery hypothesis long-term; preparation policy describes a 20-session maximum (`desk.html` policy details; `daily_execution/contracts.py`). | A beginner expecting months/years can misunderstand entry/exit behavior. | Explain horizon and exit rules beside activation; do not change existing strategy behavior silently. Add separately versioned months-to-years policies after validation. |
| UX-03 | Medium | Requested Stock Discovery, Backtesting, Portfolio and Learning Center are not distinct complete browser destinations. Current routing is in `workspace.js:5`; discovery is an expanded strategy screen, backtests are CLI/reports. | Users cannot discover existing research and simulation capabilities from the main app. | Group twelve destinations into task groups; each has a working, honest purpose and empty/recovery states. |
| UX-04 | Medium | Dashboard exposes equity/cash/dated daily P&L/position count but not held cost basis, unrealized P&L, return/benchmark/allocation (`desk.html`, `desk.js:55`). | Values remain correct within their contract but do not answer the requested investment questions. | Define metrics first; show provenance/date and unavailable states. Never derive cash invested from cumulative buys or treat unknown values as zero. |
| UX-05 | Medium | Broker guide still requires app registration, operator versus broker tokens, profile/session checks, catalog, sourced calendar and basis review (`setup.html`, `setup.js:50`). Current wizard is a useful improvement. | Beginners can confuse saved, verified, connected, fresh and tradable. | Retain progressive steps and inline feedback; show separate connection, quote, review and execution readiness with one next safe action. Navigation must not attest or connect. |
| UX-06 | Medium | Saved chart offers 1d/1m/5m plus SMA20/50 and SVG/exact table, without pan/zoom or the requested long-term indicator workspace (`analysis.html`, `analysis.js`). | A chart exists but is not the requested interactive long-term analysis screen. | Add daily/weekly/monthly controls, coverage-aware indicators and chart interaction; retain exact table, gaps and snapshot labels. Defer intraday additions. |
| UX-07 | Medium | State/reason wording is duplicated across desk, console and setup; some strings retain old labels such as Advanced controls (`desk.js:4–7`). | The same blocker can point users at a destination they cannot identify. | One presentation dictionary tied to stable diagnostic codes; use actual menu labels and scoped actions. |
| UX-08 | Medium | No persistent cross-section proposal notification mechanism; one section is mounted at a time (`workspace.js:49–53`). | Approval proposals may expire while the operator researches elsewhere. | Consider an authenticated read-only count/expiry badge; permission-based sound/notifications only as an optional later preference. Never approve through an accidental hotkey. |
| UX-09 | Medium | Most activity/holding content is cards, scoped history pages and expandable JSON (`activity.html`, `portfolio.html`, controllers). No complete browser performance workspace. | Comparisons, partial fills, reservations and current holdings are hard to scan. | Responsive semantic tables with mobile card adaptation; orders, fills, proposals and holdings remain distinct. State page/window scope. |
| UX-10 | Medium | Responsive CSS and keyboard labels exist, but no rendered end-to-end browser suite is present (`tests/ui/*.test.cjs`, `test_redesign_accessibility.py`). | Passing DOM tests can miss clipping, iframe focus, scroll and actual chart layout. | Test real browsers at desktop/mobile widths and with keyboard/zoom; keep financial-state assertions independent of screenshots. |
| UX-11 | Low | `dashboard.css` layers later overrides over earlier styles (`dashboard.css:489` onward); dense controllers share no general dialog/state components. | Layout fixes can differ by specificity and page. | Consolidate tokens/components incrementally after behavior tests; no framework migration needed. |
| UX-12 | Low | README still describes 0.13.1, older menu labels/test counts while runtime is 0.14.0 (`README.md:3`). | Users may believe features are absent or misunderstand how to load the current server. | A versioned capability index and clear distinction between current behavior and historical changelog entries. |

## Preserve these strengths

- Paper-only anchoring; no live-order toggle or real-account promise.
- Exact server decimal amounts, dated daily P&L and stale/incomplete valuation disclosure.
- Separate proposal, preview, acceptance, later fill, fee and holding states.
- Server-side risk, liquidity, quote freshness, session and corporate-action review gates.
- Explicit confirmations and no automatic mutation retry after uncertain responses.
- In-memory operator unlock with origin/window checks, private-state clearing and accessible labels.
- Guided setup and disclosures rather than automatic attestations or hidden policy defaults.

## Proposed information architecture

Keep the current self-hosted FastAPI/HTML/JavaScript stack. Twelve destinations are
organized into groups rather than twelve equal top-level tabs. Existing URL aliases
and bookmarks survive; changing the shell must preserve authorization and pending-action
guards. Do not remove iframe isolation until a separate, justified migration is approved.

| Navigation group | Destination | Primary question |
|---|---|---|
| Overview | Dashboard | What do I hold, what changed, and what needs attention? |
| Research | Stock Discovery | Which supported stocks match my reviewed screen, and why? |
| Research | Stock Analysis | What does the available history and evidence show? |
| Plan & simulate | Strategies | What rules, horizon and allocation policy am I testing? |
| Plan & simulate | Backtesting | How did this declared policy behave on valid historical inputs? |
| Plan & simulate | Paper Trading | Which proposals need review, and which orders are pending? |
| My investments | Portfolio | What is held now, at what cost/risk and on what price basis? |
| My investments | Trade History | What was instructed, accepted, executed or cancelled, and why? |
| Controls | Risk Management | Which limits apply, and can I pause or request an emergency exit? |
| Controls | Broker & Data | Is the session/data valid, and how do I recover? |
| Controls | Settings | Which non-secret preferences and reviewed configurations apply? |
| Help | Learning Center | What do the terminology, limits and results mean? |

Incomplete setup surfaces a short contextual checklist. Learning Center is always
reachable, including on mobile. Keep a visible paper badge, operating mode, data-snapshot
time and accessible route to emergency controls. A green connected dot must not imply
open market, usable quotes, reviewed basis or permission to trade.

## Screen specifications for approval

**Dashboard:** first row: estimated net equity, available cash, held cost basis and
net unrealized P&L; second: realized P&L, appropriately defined portfolio return and
allocation. Each value has a definition, valuation time and incomplete-data state.
Unknown claim values block a definitive total/return. Benchmark shows Not configured
until a genuine compatible series is supplied. Follow with next action, data/strategy
state, top candidates and recent decisions. Empty accounts show useful setup guidance,
not invented sparklines, gains or orders.

**Discovery:** an evidence table with name, classification, usable coverage, turnover,
momentum/trend, volatility/drawdown and explanation. Missing licensed fundamentals are
Unavailable, not 0. Display positive, contradictory, excluded and missing evidence.
Use named deterministic ranks rather than arbitrary probabilities of profit. Compare
candidates on matching dates/bases; saving a watchlist does not subscribe or trade.

**Analysis:** supported saved symbols initially; broaden only after a validated history
lookup workflow. Daily/weekly/monthly OHLC and volume, SMA50/200, EMA, RSI, MACD and ATR
with enough-data rules. Support/resistance must state its algorithm and window; relative
strength needs actual benchmark data. Separate raw/adjusted basis, declared corporate
actions, chart age, current quote usability and research calculation dates. Charts
permit pan/zoom and retain an accessible exact-price table. No new intraday feature.

**Strategies:** versioned, explainable configurations with horizon, universe, data/basis,
entry/exit, rebalance and sizing rules. Trend/momentum can use validated existing inputs;
quality/value remains gated on licensed point-in-time fundamentals. Draft → validated
research definition → backtest → paper review → explicit activation are distinct steps.
Never silently replace a current policy or manufacture an ML model.

**Backtesting:** select an immutable data bundle and policy, view exclusions/cost/timing
assumptions and bias disclosures, run in an isolated account, inspect progress/cancel,
then compare equity, drawdown, fees and a compatible benchmark. Mark unavailable CAGR,
Sharpe/Sortino or win rate when sample length/denominators are insufficient. A report
is research evidence, not an activation or profit guarantee.

**Paper Trading / Portfolio / History:** shared filters and links, separate semantic
entities. Pending proposal reserves no money; accepted order reserves capacity; only
fills alter holdings/cash. Portfolio shows aggregate remaining quantities/cost basis,
protection levels, valued/unvalued claims and received income. Acquisition history is
not tax/FIFO current lot ownership. Confirmed SIP occurrences spend existing cash;
they do not deposit money or silently catch up missed dates.

**Risk / Broker / Settings:** distinguish risk-limit review, emergency controls,
credential/session lifecycle, history/stream diagnostics and non-secret preferences.
Settings edits validate coupled constraints and disclose restart requirements. Keep
raw technical evidence in optional disclosure; make the reason and safe recovery visible.

**Learning Center:** short contextual articles/tooltips for paper trading, quotes versus
candles, bid/ask/liquidity, volatility/drawdown, costs, position sizing, corporate actions,
backtest biases and waiting/declining. Text is educational, not personalized investment
advice or a recommendation to buy a security.

## Visual and interaction system

Reuse current white surfaces, neutral background and restrained teal/blue accents.
Color reinforces text/icons; red/green communicates financial direction or a named
state, never the sole signal. Use tabular figures, meaningful units and readable
responsive type. Do not round underlying money through binary floats. Provide at
least 44px primary touch targets, visible focus, semantic labels/headings/tables,
reduced motion and keyboard-operable chart/table alternatives. Token colors require
measured contrast in rendered contexts; no complete WCAG conformance claim is made.

Use one loading/error/empty/stale vocabulary. Preserve user edits across background
reads. Mutation controls show pending/unknown/completed outcome and prohibit duplicate
submits. Recheck server previews at confirmation. Browser reload never constitutes
operator consent, a reviewed calendar date or an automatic mode activation.

## Acceptance matrix and next step

Required rendered checks: Firefox and an available Chromium/WebKit target; widths
360, 768 and 1440px; 200% zoom; keyboard-only navigation; visible/focusable dialogs at
the top and deep scroll; long evidence and mobile keyboard; chart empty/partial/stale/
corrupt states; lock during pending reads; cancel and one-shot confirmation. Test in
a disposable synthetic account labelled as such. Broker/device acceptance is separate.

See [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) for staged work, ownership and
complexity, [GAP_ANALYSIS.md](GAP_ANALYSIS.md) for requirements and
[ARCHITECTURE_AUDIT.md](ARCHITECTURE_AUDIT.md) for the execution boundary. Stop after
Phase 1; further application changes require the approval requested in improvements.txt.
