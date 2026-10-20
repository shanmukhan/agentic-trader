# Operator console: desktop and mobile browsers

The UI is a local browser application served by FastAPI. It is **paper only**.
There is no native Android/iOS app, installable PWA, public hosting or real-money
order screen. Desktop browsers use account cards and two-column readiness/controls;
CSS stacks cards and controls at viewport widths of 640 CSS pixels or less. Touch
controls are at least 44 CSS pixels high. Intermediate widths wrap the access form.

## Start and unlock

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
access token in the dashboard: it uses the separate operator token.

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

Desktop Safari was visually checked on this Mac, including account values, readiness,
lock/unlock and the kill/reset confirmation flow in an isolated preview account.
JavaScript tests cover interaction and race handling, not browser layout or touch
behavior. Native phone/tablet rendering, small-screen visual acceptance and remote
access remain unverified; the available browser tooling did not provide reliable
mobile visual evidence. Complete those checks with the actual device before relying
on it for supervision. Keep a verified desktop operator path available.

See [acceptance.md](acceptance.md) for local preflight and remaining external work.
