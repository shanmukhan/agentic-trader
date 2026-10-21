# First paper session with live Kite data

Verified against the local 0.9.0 implementation and official Zerodha documentation
on 21 October 2026. Run commands from the repository root. This guide describes
manual paper trading first; supervised intraday automation is a separate workflow.

## What can be tested now

The app can consume real Kite prices/depth and submit orders to its **local virtual
broker**. Cash, holdings, fees and fills are simulated; it does not send broker
orders or debit your Zerodha trading balance. A market-data subscription can still
cost money. The default seed is ₹25,000 of virtual cash per separate account.

Both intraday and long-term paper accounts are supported. Long-term holdings persist
overnight and support reviewed purchases/additions/SIP through `/portfolio`.
Intraday accounts request end-of-session exits. No simulated exit can fill without
usable quotes and liquidity. Simulated results do not establish real execution or
strategy profitability.

The engineering tests and invented replay evidence are available, but **your login,
data entitlement, sustained real feed and physical-device acceptance are not yet
verified**. Existing demo accounts/calendars are synthetic. Use a new database for
this test rather than reusing the preview, demo or original paper account.

For an immediate test without an API account, run:

```sh
.venv/bin/trading-agent portfolio-demo --directory data/portfolio-first-local-test
```

Choose a new directory each time. This is an offline long-term lifecycle/accounting
drill, not live market data. See [portfolio-contributions.md](portfolio-contributions.md)
for its UI preview instructions.

## 1. Get a Kite application

Use your own Zerodha account and [Kite developer console](https://developers.kite.trade/).
Create a developer account if needed, select **My Apps → Create New App**, and enter
your app name, matching Zerodha client ID and description. Set the redirect URL to
`http://127.0.0.1:8004/` for this local example. Zerodha permits a loopback redirect
for testing. The postback URL is optional and is not used by this paper app.

The current paid **Connect** plan is listed at **₹500 per month per API key** and
includes real-time WebSocket and historical data. The free **Personal** plan does
not include those feeds. Check the subscription and billing terms in your console
before purchasing; this application does not buy or renew a subscription for you.
See the official [registration instructions](https://support.zerodha.com/category/trading-and-markets/general-kite/kite-api/articles/how-do-i-sign-up-for-kite-connect)
and [pricing](https://support.zerodha.com/category/trading-and-markets/general-kite/kite-api/articles/what-are-the-charges-for-kite-apis).

Copy the app's **API key** and **API secret** into your private local `.env` file.
Do not send credentials, passwords, 2FA codes or token-bearing redirect URLs in chat.
This integration uses production **read-only data endpoints** and local execution.
Kite also publishes a [sandbox API reference](https://kite.trade/docs/connect/v3/sandbox/);
its endpoints and demo credentials are not integrated into this app. Do not enter
sandbox credentials into this production-data workflow.

## 2. Set up the private local environment

The prepared workspace already has Python 3.13.16 and `.venv`. On another machine,
follow [how-to-use.md](how-to-use.md#2-install-and-verify) to install frozen dependencies,
including the `broker` extra. No new virtual environment is needed here.

If `.env` does not exist, copy `.env.example` to `.env`. Preserve an existing file.
Then run:

```sh
chmod 600 .env
.venv/bin/python -c 'import secrets; print(secrets.token_urlsafe(32))'
```

Use the generated random value for `TRADING_OPERATOR_TOKEN`. Edit `.env` locally:

| Variable | Purpose |
|---|---|
| `TRADING_MODE` | Must remain `paper` |
| `KITE_API_KEY` | Identifies your developer app |
| `KITE_API_SECRET` | Private app secret used for token exchange |
| `KITE_ACCESS_TOKEN` | Initially empty; the login step supplies today's session |
| `TRADING_OPERATOR_TOKEN` | Your separately generated local dashboard/API password, at least 32 characters |

The dashboard uses **only the operator token**. Never enter your Kite API secret
or access token in its unlock field. Load your trusted private shell file explicitly:

```sh
set -a
source .env
set +a
```

The CLI does not automatically load `.env`. Commands below select a config explicitly,
overriding any `TRADING_CONFIG` left in your environment.

## 3. Obtain the daily access token

```sh
.venv/bin/trading-agent login-url
```

Open the returned `login_url` in your browser. Complete Zerodha login and 2FA yourself.
After success, the browser redirects to your registered URL with a `request_token`
query parameter. Copy **only that parameter's value**. There is no automatic callback
handler in this project. Before the service starts, the loopback page may report a
connection failure; the redirected address still contains the token. Do not change
the configured redirect merely to bypass an actual broker authentication error.

Exchange the token promptly at the hidden prompt:

```sh
.venv/bin/trading-agent exchange-token --output .env.session-first
source .env.session-first
.venv/bin/trading-agent profile
```

Choose a different new session filename if it already exists; the CLI refuses to
overwrite files. It writes the access token privately with mode 0600, without
printing it. A successful profile confirms authentication, **not streaming entitlement**.
Do not publish the profile output, which contains personal account information.
Remove the request-token query from the browser address after capture.

Kite's request token is single-use and lasts only a few minutes. Its access token
normally expires at **06:00 the next day**, and can become invalid sooner through
session/logout actions. Repeat the browser/exchange flow after expiry. Source `.env`
first and then the current session file in each new terminal; sourcing `.env` again
afterwards can replace the loaded access token with an empty/old value. Restart the
stream service after changing its environment. There is no automatic token refresh
or 2FA bypass. See the official [login and token lifecycle](https://kite.trade/docs/connect/v3/user/).

## 4. Create a dedicated account and reviewed feed

Choose **one** horizon before initializing. Use separate config/database files if
testing both. Do not convert an existing account by changing its horizon/risk policy.

| First test | Copy this template to `config/first-paper-session.toml` |
|---|---|
| Manual intraday | `config/paper.toml` |
| Manual long-term, including portfolio UI | `config/long-term.toml` |

In the copied config, set:

```toml
database = "data/first-live-paper.sqlite3"
host = "127.0.0.1"
port = 8004
calendar = "config/sessions.csv"
```

Use a new database path and an unused port. Leave `mode = "paper"` and review the
template's cash/risk/execution limits before initialization. Defaults are engineering
limits, not an investment allocation recommendation. Do not change economic limits
after initialization; use a new account for a different policy.

The calendar initially contains only a header. Review actual NSE session/holiday
notices and add only confirmed dates, actual open/close times and a source reference,
using [the calendar instructions](how-to-use.md#5-review-the-exchange-calendar).
Do not copy dates from invented demos or assume every weekday is open. Normal
configured entry hours are **09:30–14:30 IST**, with earlier cutoffs for early closes.
Outside an open reviewed session, blocked entries are expected.

With this account's service stopped, initialize and import the current equity catalog:

```sh
.venv/bin/trading-agent --config config/first-paper-session.toml init-db
.venv/bin/trading-agent --config config/first-paper-session.toml instruments
sqlite3 data/first-live-paper.sqlite3 'select symbol,token,tick from instruments order by symbol;'
```

Select a small reviewed NSE cash-equity universe from this actual catalog. Set
`stream_tokens` in the copied TOML to its numeric instrument tokens (one to ten).
Do not guess tokens or use `NSE:DEMO`. Include every held symbol when restarting.
Then run:

```sh
.venv/bin/trading-agent --config config/first-paper-session.toml preflight --strict
.venv/bin/trading-agent --config config/first-paper-session.toml serve --stream
```

Resolve the specific preflight findings. A passing local preflight does not prove
broker entitlement or a functioning network feed. This starts **manual** paper
execution; no automation flag belongs on a long-term service.

## 5. Run and inspect the first virtual order

1. Open <http://127.0.0.1:8004/> and unlock with `TRADING_OPERATOR_TOKEN`. Verify
   the intended horizon, seed cash, selected symbols, connection and quote times.
2. For **long-term** accounts, complete the current IST session's corporate-action
   review for each symbol in the main console. Only attest clear after reviewing
   intervening actions since its last accepted quote, including offline dates. An
   unresolved action must stay quarantined. Wait for a new accepted fresh quote
   after the review; see [long-term.md](long-term.md#3-review-the-price-basis-before-processing-each-session).
3. For long-term purchases, open <http://127.0.0.1:8004/portfolio>, unlock there,
   enter a reviewed symbol and virtual cash budget, and supply tick-aligned stop/target
   prices for a new holding. Calculate the preview, inspect quantity, fees, cash and
   risk, then explicitly confirm. Existing holding additions retain protections.
   Start with a single reviewed order rather than creating a recurring plan immediately.
4. For **manual intraday** entries, use the authenticated
   [`POST /api/paper/intents` contract](api-contracts.md), with your real catalog
   symbol, a unique intent ID, a current timezone-aware decision timestamp and valid
   stop/target. The main intraday console is for monitoring/control; it has no manual
   purchase form. The risk engine chooses quantity. Do not reuse the invented API
   example's symbol, prices or old timestamp.
5. Confirm the actual order state and later fills in the UI. Submission/HTTP success
   is not a fill: a rejection includes reasons, and accepted orders need later usable
   ticks after latency. Partial fills/cancellation/expiry are expected possibilities.
6. Review holdings, charged fees, reserved cash and valuation freshness. Test the
   available paper exit/flatten control while data is flowing and verify subsequent
   sell fills, final cash and position state. A kill blocks new entries and requests
   exits; it cannot instantly liquidate without quotes. Do not reset it merely to
   suppress a loss/fault reason. Intraday requests its configured session exit;
   long-term holdings remain until a supported exit is triggered and filled.

Use the UI/authenticated API while the service owns the account. Stop it before
database-owning `status`, `verify-db`, `backup`, `instruments` or other owning CLI
commands: opening an engine performs restart recovery/cancels old pending orders.
The `preflight` command is a read-only exception. Never edit cash/positions directly.
Only loopback access is supported; see [operator-console.md](operator-console.md)
for private remote/mobile access.

## Failure and daily recovery

| Symptom | What to check |
|---|---|
| `profile` authentication error | Matching app key/client ID, loaded private environment, fresh successful token exchange |
| Exchange fails or file already exists | Retry login for a fresh request token; select a new output file before exchanging; do not repeatedly reuse a spent token |
| Profile works, feed fails/403 | Correct paid app's key, active data entitlement, fresh access token and network; profile alone does not verify WebSocket permission |
| `/health` works but `/ready` is 503 | Read readiness reasons: session/calendar, entry time, fresh depth/quotes, selected catalog, kill/risk state; health proves only process liveness |
| Long-term prices/orders remain blocked | Complete genuine per-symbol current-session basis review; wait for a later accepted quote; resolve quarantines through the corporate-action workflow |
| Order rejected/zero quantity | Inspect risk, cash/fees, tick size, stop/target, spread, limits and quote freshness; do not weaken safeguards simply to force a fill |
| Token expires/feed stops | Stop the service, login again, source the new session file, restart the same account/config and inspect recovery before resuming |
| After-market/weekend test | Use an isolated offline demo; the live feed cannot supply an executable open session on demand |

Once the manual lifecycle works, use [paper-feed.md](paper-feed.md) for a **different
new dedicated intraday account** with explicit `paper-init` and supervised arming.
Rule-only mode is an experimental baseline. The long-term research/ML pipeline is
offline; this release does not automatically trade long-term models or execute SIP
plans unattended. Intraday and long-term seeds/exposure limits are separate, not
one shared capital pool.
