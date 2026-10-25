# Project Audit — Agentic Trader
**Date: 2026-10-25**
**Scope: entire source tree except `.md` files**
**Auditor: automated deep code review**

---

## Executive Summary

The project is a well-disciplined, paper-only trading system built on FastAPI + vanilla HTML/CSS/JS. Security is deliberately conservative (loopback-only, HMAC tokens, strict CSP, no client-side risk math). However, there are significant gaps in **data visualisation** (graphs used far less than the data warrants), **UI/UX consistency**, **CSS architecture debt**, **accessibility shortcuts**, and **missing backend features** that are repeatedly mentioned as "unavailable" in the UI. Several tests also have structural gaps.

---

## 1. Visualisation & Graph Gaps

### 1.1 SVG Candlestick Chart (`analysis.js` / `analysis.html`)

**Implemented:** A vanilla SVG candlestick chart with SMA 20/50/200 overlays and a volume panel.

**Issues and improvements:**

| Gap | Detail | Recommendation |
|-----|--------|----------------|
| No chart interactivity | Hover tooltips are SVG `<title>` only — not usable on touch devices. No crosshair, no click-to-zoom. | Add an overlay `<rect>` listener that positions a floating tooltip near the cursor. |
| Volume panel is minuscule | Volume bars are rendered in a 45px-tall section relative to a 420px SVG (~11% of chart height). | Allocate at least 20–25% of chart height to volume; it is a key signal. |
| No MACD / RSI sub-charts | Indicators (RSI, MACD, MACD histogram) are only displayed as table rows even though their values are computed server-side. | Add optional sub-chart panels beneath the main chart for RSI and MACD. These are the standard display location for those indicators. |
| No date x-axis labels on densely populated charts | Only 3 date labels are drawn for all chart widths. | Draw 5–8 labels dynamically based on `bars.length` and chart width. |
| SMA lines lack inline legend | SMA 20/50/200 colour is defined in CSS class strings in JS; the legend is text-only below the chart. | Add an inline SVG legend swatch per line inside the chart section. |
| No ATR band overlay option | ATR14 is computed server-side but only shown in a table. | Offer an optional ATR-envelope toggle showing `price ± ATR`. |
| Chart does not re-draw on window resize | `width: 100%` CSS applies but the SVG viewBox is fixed at `920 × 420`. On very small screens, candle bodies become sub-pixel thin. | Call `chart()` on `ResizeObserver` or render with responsive `width/height` attrs. |

### 1.2 Backtesting Reports (`backtesting.html` / `backtesting.js`)

The backtesting page outputs equity history, drawdown history, and orders/fills as plain HTML tables. **No chart is drawn for any of these.** Both the equity curve and drawdown curve are standard, expected outputs for any backtesting interface.

| Missing | Impact | Recommendation |
|---------|--------|----------------|
| Equity curve chart | Operator cannot visually assess drawdown periods, recovery time or final return shape. | Render an SVG line chart of `equity` over `session` for each completed report. |
| Drawdown curve chart | Max drawdown point is invisible in a table of numbers. | Add a second sub-chart showing rolling drawdown as a filled area below zero. |
| Trade scatter (price vs time) | Cannot see clustering or outlier fills visually. | Optional: render a price series + small triangles for buy/sell fills. |
| Comparison delta chart | Two-report comparison shows tabular differences only. | Add a side-by-side equity curve overlay for the two selected reports. |

### 1.3 Portfolio / Holdings View (`investment.html`)

The holdings view shows a flat table of stocks with net unrealised P&L. Missing:

| Missing | Recommendation |
|---------|----------------|
| Allocation pie/donut chart | `allocation-section` shows a weight table. A simple SVG arc chart would make over-concentration immediately obvious. |
| P&L bar chart per holding | A horizontal bar chart sorted by unrealised P&L would be far more scannable than a table. |
| Equity-over-time sparkline | A small dashboard sparkline per position would show trend at a glance. |

### 1.4 Dashboard (`desk.html` / `investment.html` dashboard-view)

The "Virtual portfolio summary" metrics panel contains four KPIs rendered as plain text. Currently:

- Day P&L is a plain number with no green/red colouring (`.financial-gain` / `.financial-loss` CSS classes exist but are only applied in the holdings table, not the dashboard metric cards).
- No trend indicator on equity across the session.
- No delta arrow showing change from prior close.

---

## 2. UI/UX Issues

### 2.1 CSS Architecture: Two `:root {}` Blocks Overwriting Defaults

`dashboard.css` has **two separate `:root {}` blocks** — one at line 1 and a second at line 490. The second block silently overrides `font-size` (to `15px`) and redefines `--subtle`, `--positive`, `--negative`:

```css
/* Line 1 */
:root { --bg:#f5f7fa; font-family: system-ui, …; }
…
/* Line 490 — second :root block */
:root { --subtle:#eef7f5; --positive:#13754c; --negative:#b42332; font-size:15px; }
```

**Fix:** Merge all `:root` variables into a single canonical block at the top of the file.

### 2.2 CSS: Selectors Declared and Overridden Multiple Times

Rules for `.muted`, `.panel`, `h1`, `h2`, `h3`, `button`, `input`, `body` are all redeclared multiple times in the same 800-line CSS file (e.g., `h2` defined at line 51, then overridden at line 493; `button` at line 159, then at lines 500, 503, 504). This creates an implicit ordering dependency that is very fragile to modify.

**Fix:** Organise into clearly labelled comment sections with each selector appearing in exactly one block. Use CSS custom property overrides for theme-specific values.

### 2.3 Compressed/Minified HTML in Production Source Files

Files like `activity.html` (5 lines), `portfolio.html` (53 lines, many extremely long), `desk.html` (43 lines), and `backtesting.html` contain their entire markup in very few lines without formatting. There is no minification step in the build — these are served directly from disk.

**Fix:** Format all HTML files with standard indentation for debuggability.

### 2.4 `color-scheme: light` Hardcoded — No Dark Mode

Every HTML file includes `<meta name="color-scheme" content="light">` and all CSS variables use light-only values. There is no `prefers-color-scheme: dark` media query anywhere in `dashboard.css`. For a trading console used during early morning/after-hours work, dark mode significantly reduces eye strain.

**Fix:** Add a `@media (prefers-color-scheme: dark) { :root { … } }` block with dark-mode token overrides.

### 2.5 No Loading Skeleton / Shimmer State

Pages display "Locked" or blank `—` dashes for all values while data loads after unlock. There is no skeleton/shimmer placeholder. The result is a jarring flash of empty content after unlock.

**Fix:** Add a `.skeleton` CSS class with a shimmer animation applied to metric cards and record rows while data is fetching.

### 2.6 Operator Token Re-Entry on Every Sub-Page

Every standalone HTML page (analysis, portfolio, backtesting, setup, investment-policy, desk) has its own token unlock form. When the workspace shell (`workspace.html`) is used, the token is shared via `workspace-bridge.js`. However, direct-URL access to `/analysis`, `/portfolio`, etc., requires re-entering the 40+ character token each time the page loads.

**Fix:** When navigating between pages within the same browser tab session, offer a `sessionStorage` bridge (cleared on tab close) that pre-fills the token field. No persistence across sessions; saves repeated typing during a single operator session.

### 2.7 `setup.html`: Body Class Is Wrong

```html
<body class="portfolio-page">  <!-- in setup.html -->
```

The broker setup page uses the `.portfolio-page` CSS class, which is a copy-paste error.

**Fix:** Change to `<body class="setup-page">` and add `.setup-page`-specific overrides in the CSS.

### 2.8 No Global Toast / Notification System

Success and error feedback is rendered per-page into `#message` or `role="status"` paragraphs with a brief in-place text change. There is no consistent global notification system. Consequential operations (arming automation, queuing an exit) could benefit from a persistent, acknowledged notification.

**Fix:** Implement a fixed-position toast notification bar at the top of the workspace shell. Individual pages within the iframe can `postMessage` toast events to the parent frame.

### 2.9 No Keyboard Shortcut to Approve Proposals

The proposal approval flow on `desk.html` (Paper Trading) requires: read proposal → click approve button → confirm dialog → confirm button. There is no keyboard shortcut or accelerator for frequent approval-mode operation.

**Fix:** Add `accesskey` attributes or a keyboard shortcut (e.g., `Alt+A` for Approve) to the primary proposal action button with appropriate disclosure text.

### 2.10 Asymmetric Token Form Pattern Across Pages

`index.html` (Risk Management) correctly wraps the label in `class="sr-only"` for the compact access form. `analysis.html` shows the label inline. Other pages vary. This creates an inconsistent layout when pages are embedded inside the workspace iframe (`.workspace-child .access { display:none; }` hides access, but the pattern inconsistency will cause issues when pages are loaded directly).

**Fix:** Standardise the access form pattern across all sub-pages.

---

## 3. Backend / Python Gaps

### 3.1 `risk/limits.py` — Only Buy-Side Sizing, No Sell-Side Validation

[`limits.py`](file:///Users/shanmukhan/Developer/repo/agentic-trader/src/trading_agent/risk/limits.py) implements only `size()` for buy orders. There is no analogous function validating exit/sell orders. Exit logic is scattered in `paper_broker.py` and `delivery.py` without a unified risk gate.

**Fix:** Extract a `size_exit()` function or a shared validation confirming exit price is above stop before proceeding.

### 3.2 `strategy/rules.py` — `vwap_continuation` Hypothesis Not Clearly Implemented

```python
hypothesis: Literal["opening_range_breakout", "vwap_continuation"] = "opening_range_breakout"
```

`vwap_continuation` is selectable in `StrategySettings` but the `RuleStrategy.evaluate()` method does not appear to dispatch differently based on this value. If both hypotheses share the same logic, this is a silent misconfiguration risk.

**Fix:** Add an explicit `NotImplementedError` guard or clear dispatch in `evaluate()`, and add a test that `vwap_continuation` either produces distinct signals or raises clearly.

### 3.3 `settings.py` — `delivery_fee_buffer` Not a Configured Setting

The `delivery_fee_buffer` value appears in `dashboard.js` responses and console snapshots but is not a field in [`settings.py`](file:///Users/shanmukhan/Developer/repo/agentic-trader/src/trading_agent/settings.py) — it is computed or hard-coded elsewhere.

**Fix:** Make delivery fee buffer an explicit, configurable setting with a clear default.

### 3.4 `ml/training.py` — No Cross-Validation, No Feature Importance

[`training.py`](file:///Users/shanmukhan/Developer/repo/agentic-trader/src/trading_agent/ml/training.py) uses a single `LogisticRegression` with a single train/calibration split. There is no k-fold cross-validation, no feature importance export, and no hyperparameter search (C is fixed per config).

**Fix:** Add a `cross_validate()` path for research use and expose feature coefficients in the training report.

### 3.5 No Rate-Limit Retry in Candle Fetch Code

The `repository.py` and `candles.py` market data fetch logic paces reads at "at least 400 ms apart" (per UI description) but has no exponential backoff or retry on HTTP 429/503 responses from the broker API.

**Fix:** Add a retry loop with exponential backoff for broker API calls in the historical download path.

### 3.6 No Lightweight Feed Health Endpoint

The feed connection state is polled by the UI every 3 seconds via `/api/console`. This endpoint aggregates significant data (positions, orders, quotes, readiness reasons). A connection-status check should not require this much work.

**Fix:** Add a lightweight `/api/feed/status` endpoint returning `{connected, feed_connected, faulted, last_tick_ms}` for fast health polling.

### 3.7 Exception Handler Faults Engine on All Unhandled Exceptions

```python
@app.exception_handler(Exception)
async def safe_error(request, exc):
    engine.faulted = True
    engine.set_connected(False)
    desk.mode = "manual"
    …
```

This handler catches **all** exceptions including FastAPI `RequestValidationError` (422) and 404s before FastAPI's built-in handlers. A malformed API request will fault the engine unnecessarily.

**Fix:** Explicitly exclude `HTTPException` and `RequestValidationError` from this handler.

### 3.8 Watchdog Thread Swallows Exception Traceback

```python
except Exception:
    engine.faulted = True
    logging.getLogger(__name__).error("watchdog failed; entries blocked")
```

No `exc_info=True` — the traceback is lost in the log.

**Fix:** `logging.getLogger(__name__).error("watchdog failed; entries blocked", exc_info=True)`

### 3.9 No Prometheus / OpenMetrics Endpoint

The observability directory exists but there is no `/metrics` endpoint. A paper trading system running locally could trivially export counters for orders, fills, proposals, feed latency, and Python GC stats.

**Fix:** Add an optional `--metrics` flag that mounts a `/metrics` endpoint using the `prometheus_client` library.

---

## 4. Test Coverage Gaps

### 4.1 No Tests for SVG Chart Rendering

`tests/ui/analysis.test.cjs` exists but likely covers only data-binding and lock/unlock flows. The SVG chart rendering code path (`chart()` in `analysis.js`) involves coordinate math, segment-break handling, and axis label placement — all of which need dedicated unit tests.

### 4.2 `risk/limits.py` — No Property-Based Tests

The `size()` function involves binary search over integer quantities with multiple constraint interactions. Property-based testing with `hypothesis` would catch edge cases (e.g., when two constraints are exactly equal, or when fees exceed the risk budget at quantity 1).

### 4.3 No Integration Test for `operations-watch` Supervisor

The supervisor (`operations-watch` command) is a critical safety component but has no integration test that exercises a full supervisor loop with a real database.

### 4.4 No ML Pipeline End-to-End Smoke Test

There is no end-to-end smoke test that runs `labeling → samples → training → inference` on a minimal synthetic dataset and verifies the output probability is in [0, 1].

---

## 5. HTML/JS Structural Issues

### 5.1 `activity.html` — Entire Page Rendered by `desk.js`

The `activity.html` file is 5 lines and serves only a shell. All HTML for orders, fills, and decision history is dynamically rendered by `desk.js`. Screen reader users see an empty locked page initially with no structural landmarks.

**Fix:** Add static `<h2>` headings and brief descriptions in the HTML so the pre-JS structure is meaningful.

### 5.2 Multiple Pages Re-Implement `confirmAction()` Independently

`dashboard.js`, `portfolio.js`, `backtesting.js`, and `investment-policy.js` all contain their own confirm-action + dialog orchestration pattern. The shared `dialogs.js` provides `createDialogs()` but each page still duplicates button-state management and pending-action storage.

**Fix:** Move pending-action + confirmation-dialog orchestration into `dialogs.js` as a higher-level `confirmWith(dialog, action, body)` utility.

### 5.3 `data-desk-section` Attribute for Visibility Management

`desk.html` uses `data-desk-section="paper"` attributes on `<section>` elements to control which sections are visible based on investment horizon. This is a custom data-attribute-driven visibility system that duplicates what `section.hidden` or `aria-hidden` could do more cleanly.

**Fix:** Use `section.hidden = true/false` toggles instead of custom data attributes for visibility management.

### 5.4 `money.js` Not Tested for Edge Cases

`money.js` is a critical financial formatting utility (1,421 bytes). It should have explicit tests for very large numbers, negative numbers, zero, string inputs (Decimal strings from server), and `null`/`undefined` inputs.

---

## 6. Accessibility Issues

### 6.1 `<details>/<summary>` Used for Content Panels

Throughout the app, `<details>` is used for persistent content sections ("Positions & protection levels", "Open orders & reservations"). Screen readers announce these as disclosure widgets, which is semantically incorrect for what are effectively content panels.

**Fix:** For sections that are conditionally shown based on account state, use `aria-hidden` on a `<div>` instead.

### 6.2 Error State Uses Class Change Instead of `role="alert"`

```javascript
el('message').className = error ? 'error' : '';
```

Errors are indicated by adding class `error` (colour change) but the element keeps `role="status"`. For errors, `role="alert"` is more appropriate (assertive, does not wait for a pause in speech). An element cannot change its role dynamically.

**Fix:** Add a separate hidden `<p id="error-alert" role="alert" class="sr-only"></p>` and mirror error messages into it.

### 6.3 `#positions-panel` `<h2>` Inside Collapsed `<details>`

The `<h2 id="positions-heading">` is inside a collapsible `<details>` block. The `<details>` itself has no `aria-labelledby` pointing to the heading. The summary text and `h2` text are different, creating ambiguity for screen readers.

---

## 7. Security / Configuration Observations

### 7.1 Operator Token Entropy Not Documented

```python
if token and len(token) < 32:
    raise ValueError("operator token requires at least 32 characters")
```

32 characters of printable ASCII can have as low as ~26 bits of entropy if all lowercase. The documentation should explicitly recommend `secrets.token_hex(32)` (64 hex characters, 256 bits of entropy).

### 7.2 No HTTPS Support Locally

The server runs HTTP on loopback. Modern browsers increasingly restrict certain APIs (e.g., notifications, clipboard) on HTTP even on localhost. A self-signed TLS option would future-proof the setup.

### 7.3 `localhost` in Trusted Hosts Can Be Overridden

```python
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "[::1]"])
```

`localhost` can be overridden in `/etc/hosts`. The more defensive approach is to allow only `127.0.0.1` and `[::1]`.

---

## 8. Performance Observations

### 8.1 SVG Chart Re-Renders Fully on Every Call

The SVG chart calls `el('price-chart').replaceChildren()` and redraws the entire SVG from scratch on every stock/timeframe/range change. For 500 candles, this creates ~1,500+ DOM elements on each render.

**Fix:** Consider `<canvas>` for chart rendering (much faster, supports pixel-level control) or cache the SVG element and update only the visible range without redrawing indicators.

### 8.2 `/api/console` Polled Every 3 Seconds With Full Payload

The full console snapshot (positions, orders, quotes, readiness reasons) is fetched every 3 seconds. This may cause SQLite lock contention under the watchdog.

**Fix:** Consider WebSocket or SSE for push-based updates. If polling is kept, make the 3-second interval configurable and consider a separate lightweight status endpoint.

---

## 9. Missing Features Acknowledged in the UI

The following features are explicitly mentioned as "unavailable" in the HTML with no implementation visible:

| Feature | Page/Location | Status Label in UI |
|---------|---------------|-------------------|
| Named research watchlists | `investment.html` discovery-view | "not available yet" |
| Allocation targets / sector charts | `investment.html` holdings-view | "unavailable until contracts implemented" |
| Portfolio benchmark comparison | `investment.html` | listed as unavailable |
| Return curves | `investment.html` | listed as unavailable |
| Company fundamentals | `analysis.html` | "licensed source not configured" |
| Policy backtesting & execution | `investment-policy.html` | "unavailable" |
| VWAP continuation strategy | `strategy/rules.py` | listed in enum, implementation unclear |
| ETF-specific fee validation | `setup.html` | "not validated" |

**Recommendation:** Add a `docs/ROADMAP.md` with ownership, priority, and blocked-by fields for each item.

---

## 10. Minor / Cosmetic Issues

| File | Issue |
|------|-------|
| `desk.html` | Entire HTML on a single line — unreadable in editor |
| `dashboard.css` line 641 | `.volume-bar { fill:#338d80; }` overrides `.volume-bar { opacity:.35; }` from line 610 without explicitly restoring opacity — volume bars appear solid, not semi-transparent |
| `analysis.js` | `indicatorDefinitions` array is defined at module level but references CSS class naming conventions via `key.endsWith('_pct')` — brittle coupling between data layer and CSS naming |
| `settings.py` | `stream_tokens: tuple[int, ...] = ()` accepts empty tuples silently; feed connection with zero tokens only errors at runtime, not at config load |
| `workspace.html` | Important context ("Lock clears access, does not stop the server") is buried in the `<footer>` — invisible on smaller screens |
| All HTML pages | No `<meta name="description">` tag on any page |
| `portfolio.html` | `<section class="panel access">` has no `aria-labelledby` pointing to its `<h2>` |

---

## Summary Priority Matrix

| Priority | Area | Item |
|----------|------|------|
| **High** | Graphs | Equity curve + drawdown chart in backtesting — currently absent, expected standard |
| **High** | Graphs | MACD/RSI sub-charts in analysis — data computed, not displayed |
| **High** | Backend | Fix blanket exception handler faulting engine on all errors |
| **High** | Backend | Add `exc_info=True` to watchdog logging |
| **High** | CSS | Merge duplicate `:root` blocks; remove duplicate selector redeclarations |
| **Medium** | Graphs | Volume panel height; interactive hover tooltips; dynamic date labels |
| **Medium** | UX | Dark mode support; skeleton loading states; global toast system |
| **Medium** | UX | Session-level token persistence to avoid repeated re-entry |
| **Medium** | Backend | Retry logic for broker API; sell-side risk validation; `vwap_continuation` guard |
| **Medium** | Accessibility | `role="alert"` for errors; `<details>` semantic misuse |
| **Low** | HTML | Format compressed HTML files; fix `setup.html` body class mismatch |
| **Low** | Backend | Prometheus metrics endpoint; named watchlists; fundamentals source |
| **Low** | Tests | Property-based tests for risk sizing; SVG chart tests; ML pipeline smoke test |
