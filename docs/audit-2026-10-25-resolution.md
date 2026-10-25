# 25 October 2026 audit: resolution and remaining scope

Reviewed [the supplied audit](PROJECT_AUDIT_2026-10-25.md) against the current source,
including tests and financial safety constraints. Recommendations are hypotheses:
some absence claims were incorrect, and requiring a sell price above its stop would
prevent the protective exit that the stop is intended to request. The original audit
is retained as supplied; this document records the implemented disposition.

| Audit item | Disposition and evidence |
| --- | --- |
| 1.1 analysis charts | Implemented exact pointer/touch inspection, keyboard candle slider/crosshair, larger volume panel, dynamic dates, inline SMA swatches, optional saved RSI/MACD panels and close ± ATR envelope, readable candle widths and cached resize redraw. Display-range controls already supplied 50/100-candle focus. Values are saved evidence, never new client-side research. See [analysis](market-analysis.md). |
| 1.2 backtest charts | Added fresh-only equity, recorded drawdown below zero and compatible-report equity overlays. Missing/stale values break lines; exact tables remain. Optional fill scatter is on the roadmap. See [browser reports](browser-backtesting.md). |
| 1.3 portfolio visuals | Added cash/held-share allocation ring with exact labels and sorted estimated P&L bars. Unavailable weights and stale/incomplete/truncated P&L evidence disable plots. Per-position trends need a historical contract and remain open. |
| 1.4 dashboard signals | Existing paper-desk daily P&L already had sign classes. Shared Dashboard now also signs P&L/daily-accounting cards and labels the actual baseline date. No unsupported prior-close arrow or invented trend was added. |
| 2.1–2.2 CSS | Consolidated repeated top-level selectors and base tokens; scoped responsive rules remain distinct. Added theme tokens for surfaces, focus and signs. Theme override is an explicit media scope. |
| 2.3 HTML | Formatted all served HTML with structural indentation, retaining literal inline evidence and accessible IDs. |
| 2.4 dark mode | Follows system light/dark preference across shell and child pages; readable chart, control and status colors. |
| 2.5 loading | Shared visible loading placeholder and `aria-busy`; reduced-motion preference disables shimmer. Loading never turns a failed/stale read into a current value. |
| 2.6 token reuse | Already implemented by same-origin workspace memory handoff and direct-route redirect. Kept credentials out of sessionStorage; reload/Lock/pagehide clears access. |
| 2.7 setup class | Corrected to `setup-page` with its own layout rules. |
| 2.8 notifications | Persistent dismissible shell action feedback, explicit acknowledged action outcomes and separate assertive error regions. Origin/frame/path/unlock checks reject foreign or stale messages; Lock clears text. Polling success is not repeatedly toasted. |
| 2.9 approval accelerator | Added Alt+R to focus the first available review button, leaving Enter/review/confirmation explicit. Text fields, repeats, pending dialogs, busy and locked states ignore the shortcut. It never approves an order. |
| 2.10 access forms | Consistent visible token labels and named local-access regions. Workspace embedding hides repeated access forms as before. |
| 3.1 sell risk | Shared existing financial exit invariants for both horizons; gap-through-stop exits remain allowed. Independent SQLite tests verify exact fees/cash and rollback. See [risk](risk-policy.md). |
| 3.2 VWAP | Absence claim false: distinct hypothesis dispatch and tests already exist. No NotImplementedError was introduced. |
| 3.3 delivery buffer | Already derived from configured DP sell charge × max positions. Kept this conservative exact reserve; an arbitrary setting would allow inconsistency. |
| 3.4 ML | Expanding chronological folds, purging, embargo, calibration and frozen holdout already exist. Added descriptive named standardized/calibrated coefficient diagnostics and artifact agreement tests. Random folds/automatic search were not introduced; see [ML guide](ml-research.md). |
| 3.5 history retry | Added three-attempt bounded 429/503 retries with shared pacing/backoff. Authentication, malformed data and token exchange are not automatically retried. See [feed recovery](paper-feed.md). |
| 3.6 feed health | Added authenticated in-memory `/api/feed/status`; shell checks every ten seconds while visible/unlocked. Tick receipt age is not per-stock quote usability or trading readiness. |
| 3.7 exception handling | Claim false: framework handlers dispatch 404/401/403/422 before catch-all. Regression tests now prove rejected requests leave engine authority/accounting unchanged; genuine unhandled failures still fail closed. |
| 3.8 watchdog | Uses exception logging, preserving traceback while blocking entries. |
| 3.9 metrics | New exporter remains a separately specified optional operations feature; roadmap names owner and blockers. Health endpoint addresses the immediate polling concern. |
| 4.1 SVG tests | Added geometry, indicator-gap/warmup, pointer/keyboard inspection, comparison, drawdown and Lock cleanup checks. |
| 4.2 sizing properties | Added 800 deterministic generated cases against independent exhaustive Decimal oracles, plus exact fee boundaries; no new test dependency required. |
| 4.3 supervisor | Added a real-API/SQLite multi-iteration supervisor test with independent persisted-state inspection, alert/recovery and dedup checks. |
| 4.4 ML E2E | Existing CLI labeling/samples/train/load path already existed; strengthened probability [0,1] and coefficient/artifact checks. |
| 5.1 history structure | Static history guidance/heading now remains meaningful before unlock/JS, in addition to static order/proposal headings inside protected main. |
| 5.2 confirmations | Shared `confirmWith`/`confirm` owns captured callbacks and reviewed JSON bodies for Risk and Purchases; cancellation/close/open failure/pagehide revokes them. Backtest and policy controllers retain their distinct acknowledgement/idempotency/uncertain-outcome state. |
| 5.3 visibility | Claim false: metadata describes reusable section membership, while existing `section.hidden` controls actual visibility. Retained tested behavior. |
| 5.4 money tests | Added direct zero, sign, large, fractional, exponent, malformed and unavailable-input cases. Source decimal strings remain exact. |
| 6.1 disclosures | `<details>` is correct for user-controlled optional evidence/help. Removing disclosure semantics would reduce accessibility; retained them. |
| 6.2 errors | Dedicated assertive regions mirror changed errors; ordinary status retains polite announcements. |
| 6.3 positions heading | Linked positions disclosure to its visible heading. |
| 7.1 token generation | Explicitly recommends locally generated `secrets.token_hex(32)` and warns that length alone does not establish randomness; no credential is generated into chat/logs. |
| 7.2 TLS | Open deployment option with certificate/callback acceptance blockers. Loopback binding and auth remain; no self-signed-warning bypass. |
| 7.3 localhost | Retained existing loopback binding, Host/Origin protections and supported localhost URLs. Hostname resolution changes cannot make a loopback-bound socket publicly listen; IP-only allowlisting would break supported local workflows without solving compromised local host configuration. |
| 8.1 chart performance | Cached optional-panel/resize redraw avoids fetching/rebuilding exact tables; bounded SVG and accessible evidence retained. Canvas migration needs measured scale evidence. |
| 8.2 polling | Lightweight shell feed observation replaces any need to poll full console merely for connection state. Existing financial screens retain full snapshots to update their financial values and safeguards; push remains roadmap work. |
| 9 product gaps | Added [ROADMAP](ROADMAP.md) with ownership, priorities and blocked-by/acceptance fields for every named missing feature. No placeholder is promoted into working execution or licensed data. |
| 10 minor issues | HTML formatting, setup class, meta descriptions, access labels, visible Lock consequences and strict stream identity types addressed. Volume fill and opacity coexist (the audit's override claim was false); consolidated rules retain translucency. Empty token selection intentionally remains valid for initial offline setup. Indicator unit key naming follows a fixed server schema, not CSS class naming. |

Validation and acceptance scope is recorded in [the test plan](test-plan.md).
Synthetic tests and disposable browser fixtures are distinct from real-feed load,
licensed source, native worker, broker and physical-device acceptance.
