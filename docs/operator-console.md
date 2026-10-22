# Risk Management: desktop and mobile browsers

Version **0.15.0** labels `/console` **Risk Management** (`#risk`). It retains
current-basis review, exposure, readiness and emergency/entry controls. **Broker &
Data** contains credentials, calendar and connection administration; **Settings**
is read-only configuration. **Paper Trading** contains modes and proposals, while
**Trade History** contains orders/fills. The saved Dashboard and Portfolio views
do not grant execution authority. See [workspace.md](workspace.md) for all routes.

Risk confirmations now use the same dialog helper as Setup, Purchases and strategy
reviews. It positions before opening in the visible parent viewport, restores focus
on close and cancels on Escape or pagehide. The menu remains inert while open;
Cancel sends nothing. A failed geometry/reveal closes safely. Lock/pagehide ignores
late reads; it does not undo an already received server action. Exact financial and
risk behavior is unchanged. See [the shared component guide](frontend-modernization.md).

The UI is a local browser application served by FastAPI. It is **paper only**.
There is no native Android/iOS app, installable PWA, public hosting or real-money
order screen. Desktop browsers use account cards and two-column readiness/controls;
CSS stacks cards and controls at viewport widths of 640 CSS pixels or less. Touch
controls are at least 44 CSS pixels high. Intermediate widths wrap the access form.

## Start and unlock

For the current workspace, `./scripts/start_ui.sh` opens the configured account,
including reusing a matching running server safely. [Browser Setup](ui-setup.md)
adds broker login/session exchange, catalog/symbol selection, reviewed calendar and
feed controls for manual accounts. The local unlock value is `TRADING_OPERATOR_TOKEN`
from `.env`, never a Zerodha redirect/request/access token. Version 0.11.0's
[shared workspace](workspace.md) keeps one in-memory unlock across menu sections.
Reload/new workspace tabs require another unlock; no browser credential storage or
cross-tab session synchronization was added. Ordinary page URLs route to the menu.

If an older process owns the configured port, stop it in its owning terminal with
Ctrl+C and run `./scripts/start_ui.sh` again; the launcher does not reload Python
modules inside that process. Unlock again after restart, inspect holdings/pending
work and explicitly reconnect or select a mode when ready. Navigation never submits
a financial change or re-arms a paused strategy.

Follow the [environment/token instructions](how-to-use.md) first. From the repository
root, with the private operator environment loaded:

```sh
.venv/bin/trading-agent serve
```

Open <http://127.0.0.1:8000> in a current browser. Enter the operator token and select
**Unlock / refresh**. The password field clears immediately. The token stays in the
page's memory and is sent only in the Authorization header. The app does not save
it to cookies, URLs, local storage or session storage. Do not save it in a shared
browser's password manager. **Lock** clears displayed private values, cancels pending
requests, closes confirmation dialogs and forgets the token. Reloading also locks.
Locking the page does not stop or disarm the server; use the relevant paper control
before leaving an armed account unattended.

No operator token means the public shell/health work but private account access is
disabled. Starting without `--stream` requires no Kite credentials, has no market
connection and normally shows blocked entries. Never enter a Kite API secret or
access token in the dashboard unlock field: it uses the separate operator token.
Broker API key/secret and one-time request token belong only in the labeled Setup
forms after local authentication. Secrets are not returned in setup status; the
public app key appears in its official login URL.

## Read the account

- **Virtual equity** includes adverse bid-side liquidation estimates and estimated
  remaining exit costs. A stale valuation remains an estimate.
- **Available cash** excludes pending entry cash reservations. Reserved cash and
  charged fees are shown separately. Display formatting groups Indian rupees and
  preserves all server decimal digits; the browser performs no financial arithmetic.
- **Day P&L** includes estimated liquidation costs. The details disclosure retains
  realized P&L, exposure, planned risk, loss streak and fee-policy identity.
- **Entry readiness** explains missing/stale data, sessions, feed, kill and automation
  state. Prerequisites do not approve a candidate; the server still enforces every
  independent risk/model gate. Manual services consider observed quotes; automated
  services additionally require their whole configured universe and explicit arming.
- **Open positions** show residual quantity, stop/target and estimated unrealized P&L.
  An empty list means flat. A queued exit does not imply a completed fill.
- **Paper orders** show the latest 200 recorded orders, newest insertion first, with
  IDs, state, reason and filled/requested quantity. A label discloses older omitted
  orders. Use the journal/reports or existing orders API for the full history.
- **Account and automation details** shows the server snapshot and bounded telemetry.
  Update times display IST; raw timestamps remain explicitly offset UTC.

Visible unlocked pages poll one authenticated `/api/console` response every three
seconds. Account, recent orders, quote readiness and automation are captured while
the engine lock prevents interleaved quote/control changes. Polling never submits
orders, arms automation, performs recovery or writes journal events.

Hidden tabs pause polling. Returning to the tab requests an update. After more than
six seconds without a successful response, values are labeled stale and arming/reset
are disabled. A request times out after ten seconds; overlapping polls are suppressed.
Kill/flatten/disarm remain available with an already unlocked account while display
updates fail. Authorization failure locks and clears values. This UI behavior does
not replace the independent server watchdog or stale-data gates.

## Controls and confirmation

**Activate kill switch** cancels pending entries, blocks new ones and queues required
exits. **Queue flatten** requests the same protective behavior with a distinct
operator reason. These and **Disarm entries** act immediately. Disarm cancels pending
buys while protective handling continues. Verify remaining positions and actual
paper fills after every exit request.

**Arm paper automation** opens a confirmation dialog and is available only when the
configured automated service reports readiness. **Reset kill switch** also requires
confirmation and remains subject to server flatness/budget/fault checks. Cancel is
the default focused dialog button. Reset does not rearm. Manual accounts disable the
automation controls. Controls are requests; a 409 rejection means they did not pass.

Actions are serialized and never automatically retried. A timed-out action has an
unknown outcome: refresh and inspect current state before deciding to retry. Earlier
in-flight polls cannot overwrite post-action values or repopulate a locked page.

## Mobile access

The page adapts to a narrow browser viewport. A phone's `127.0.0.1` refers to the
phone itself, so it cannot directly reach this computer's loopback listener. Mobile
operation requires a separately reviewed private path with the local listener still
protected, such as a suitable authenticated tunnel that preserves the allowed
Host/Origin and configured port. Do not change the host to `0.0.0.0`, add broad CORS,
or expose this port publicly to make a phone connect. No tunnel is provisioned here.

Before the 0.14.0 redesign, desktop Safari was visually checked on this Mac, including account values, readiness,
lock/unlock and the kill/reset confirmation flow in an isolated preview account.
JavaScript tests cover interaction and race handling, not browser layout or touch
behavior. Native phone/tablet rendering, small-screen visual acceptance and remote
access remain unverified; the available browser tooling did not provide reliable
mobile visual evidence. Those historical checks do not establish browser or device
acceptance of the 0.14.0 redesign. Complete those checks with the actual device before relying
on it for supervision. Keep a verified desktop operator path available.

See [acceptance.md](acceptance.md) for local preflight and remaining external work.

## Long-term account panel (0.5.0)

The separate long-term config uses <http://127.0.0.1:8001>. After unlock, the horizon
badge identifies the account. Its panel shows observed peak/drawdown, entry fee buffer
and up to eleven quarantine names; use the report for full quarantine history.
A symbol/date/source form records the raw-price review, with a confirmation dialog.
An unchecked no-action attestation requests a persistent quarantine and its dialog
warns that another review cannot clear it. Supported known actions require the
[offline adjustment workflow](corporate-actions.md). Review fields/details clear on
Lock; stale displays block review submission.

Each long-term holding has **Queue full paper exit** with symbol-specific confirmation.
It sends only the symbol, remains protective through partial fills/restarts and never
claims a completed sale. Intraday accounts hide this panel/actions. No buying, real
broker trading, account conversion or automatic long-term signal control was added.
Desktop Safari layout/horizon/buffer/review form was visually checked on an isolated
flat account with no feed or orders; actual handset verification remains pending.
Read [long-term.md](long-term.md) before using the new controls.

In 0.6.0 the panel also displays known unpaid dividends, unvalued fractional-claim
count and dividend income already received. Unpaid entitlements do not enlarge the
available-cash card. Unknown fraction value makes portfolio estimates stale; a
whole-share exit does not erase that claim. Applying batches/receipts requires the
service stopped and reviewed CLI input. On resume, submit a new clear review
covering the applied action and wait for a post-application usable quote. The
quarantine confirmation now points to that workflow. Lock clears the claim summary.
JavaScript tests verify these displays and confirmation text; handset visual/device
acceptance remains pending.

LT2 claim values use separate labeled cards with plain-language cash/valuation notes.
A status message explains whether the next step is quarantine resolution, a fractional
receipt or the ordinary session review. Labels and guidance clear when the UI locks.

## Separate daily research dashboard (0.7.0)

The offline daily report is generated by `daily-research-demo`/`daily-analyze`; open
its `index.html`. It is separate from the authenticated operator console and has no
financial controls. Provenance/as-of clock, summary cards, a filterable sortable
table, plain-language reasons, metric definitions, coverage/empty states, visible
keyboard focus and touch-sized controls support review on desktop/mobile browsers.
Analytical values round to two decimals; report JSON keeps full precision. It never
labels screening as execution, forecasts or model validation. Local JS tests cover
rendering, filtering, sorting, reset/focus, missing/empty states and safe text. Browser
pixel/handset inspection remains pending computer-use permissions. Follow
[daily-research.md](daily-research.md) for complete usage.

## Separate daily execution/validation dashboards (0.8.0)

`daily-execution-demo --directory NEW --with-ml` writes `portfolio/index.html`,
`labels/index.html`, `model/index.html` and `scored/index.html`. Open them directly
in a browser. They use responsive desktop/mobile layouts and no network, account
token, live refresh or trading controls. Exact money and IST clocks accompany
coverage/claim/open-exposure checks, search, evidence views and expandable policy.
Labels explicitly show that portfolio returns are not measured; failed validation
explains that loading is blocked. Tables cap display at 200 rows, retaining full
JSON/JSONL evidence and empty-state guidance. Keyboard focus/scrolling and clear
labels are tested. Actual handset/pixel acceptance remains pending. Full walkthrough:
[daily-execution.md](daily-execution.md). The authenticated connected console flow is unchanged.

## Contribution and SIP review page (0.9.0)

The long-term safeguards panel links to `/portfolio`. Unlock this separate tab using
the same private operator token. Exact cash/reservations and quote/risk state lead
into a server-computed purchase preview and explicit confirmation, then recent intent
states, actual debit, current aggregate holdings and original acquisition history.
SIP panels show due/upcoming/missed/cancelled dates and confirmed attempts; save and
cancel actions use dialogs. Due-plan budgets/IDs remain server supplied and read-only.

The page supports keyboard/touch/responsive browser use, text-only untrusted values,
lock/late-response invalidation and no automatic action retry. A changed/expired
preview must be reviewed again; unknown outcomes direct inspection by intent ID.
Original acquisitions are clearly distinguished from current pooled/tax ownership.
Emergency exits remain in the main console. See the full [walkthrough](portfolio-contributions.md).
Browser pixel/physical-handset acceptance remains pending.
