# Start, unlock and configure the paper app in your browser

## Safe account configuration updates

Saving the reviewed feed selection or session calendar updates only `stream_tokens`
or `calendar` in the server-selected account TOML file. The round-trip TOML parser
handles quoted keys and multiline values, retaining unrelated settings and comments.
The proposed complete config is validated against the settings schema and the running
account's financial policy before any write. Setup cannot change financial limits.

After selecting symbols in **Broker & Data**, the saved config and setup status show
the same catalog-backed instrument tokens. With the feed disconnected, restart using
the same `--config` path to load that selection. A malformed TOML file, unexpected
table, external financial-policy edit or failed atomic replacement leaves both the
previous config and running selection unchanged. Preserve the file, correct/review it
locally, and refresh setup status before retrying. A partial temporary file never
replaces the account config. This validation is local simulated evidence; it does not
verify broker credentials, market entitlements or native Windows operation.

In 0.15.0, this section is **Broker & Data** (`#broker`). Step 6 confirmations use the shared native dialog positioned before autofocus in the currently visible parent viewport. Scroll/resize/visual viewport changes keep it bounded; Escape/Cancel clears the pending action and restores focus, with no POST. If it cannot be revealed, return to the section and review again. Current position tests are simulated geometry; live broker acceptance is separate. See [shared dialog behavior](frontend-modernization.md).

The light workspace now has twelve grouped destinations. **Dashboard** shows saved
portfolio and market/account state; **Paper Trading** contains readiness, modes and
proposals; **Trade History** contains actual orders and fills. **Portfolio** links to
Purchases & SIP. **Learning Center** includes the setup checklist, while incomplete
setup also shows contextual guidance. See [all routes](workspace.md) and
[Stock Analysis](market-analysis.md) for saved charts and their limits. Viewing a
chart does not start a broker download.

**Broker & Data** now starts with a connection overview: actual connected,
requested or disconnected state, broker-session verification, saved-subscription
count, reviewed calendar and the next troubleshooting action. Its six settings
steps are keyboard-accessible disclosures. The first unlocked status opens the
relevant step; expand any step or use **Back** and **Continue**. Status refresh
preserves the open step and unsaved input. Moving between steps never saves,
checks credentials, connects data, approves a date or arms trading. A **Check saved
broker session** recommendation opens step 3; the explicit check button there
performs the broker request. `/setup#feed-connection` opens step 6 directly.
Lock clears private status, edited fields and open steps; unlock obtains a fresh
status and chooses a new starting step. Existing action confirmations remain in place.

The combined strategy setup is in **Strategies**. Once the broker
session/catalog and same-day download are available, choose a policy, select **Review
and finish setup**, inspect the sources/dates/stocks, check one acknowledgement and
confirm. The server handles feed disconnection, installation, shortlist, listed eligible
current-day reviews and reconnection. No trading mode is activated. The previous calendar
CSV and individual controls remain under Advanced. See
[strategy-preparation.md](strategy-preparation.md) for the full simplified process.


The strategy wizard also shows saved/proposed calendar differences and can correct an
unused account after a separate explicit acknowledgement. Any accepted quote/candle,
pinned review or execution/instruction usage prevents correction, rechecked after
validation. Setup's per-date form retains its stricter existing-definition behavior.
Normal 15:30 exchange close is separate from a strategy's 15:15 flatten/cutoff.

The [strategy preparation workflow](strategy-preparation.md) remains separate from broker setup.
The feed can connect while modes remain disabled: it supplies transport, not a
strategy or usable after-hours depth. **Your next step** now lists separate strategy,
connection, quote, session, entry-window, shortlist/model and basis checks with actions.
Use **Prepare a paper strategy** to download genuine Nifty 100/500 history and inspect
sources/exclusions; review the proposed calendar and basis yourself, select a policy
explicitly, then install while disconnected in Manual. No model, financial approval
or executable quote is created by connecting or installing.

In setup step 5, **NSE notice / review reference** means the official URL/circular or
review notes used to check the selected date and hours. For a reviewed normal cash-equity
session use 09:15 AM–03:30 PM IST; the app rejects evening times. Check the actual
holiday/special notices and tick the review box only after that review. The preparation
wizard can propose a larger calendar from downloaded sources, but still requires your
review and never changes already used account hours.

Use **Paper Trading** for readiness/modes/proposals and **Trade History** for reasons, actual
orders and fills. **Strategies** contains preparation, profile coverage and ranked
shortlist review; its separate `/strategies` page uses the existing controllers.
Legacy `/desk#strategy-setup` and shortlist anchors route there.
**Broker & Data** retains broker administration and **Risk Management** retains
basis reviews/kill/flatten. See [Dashboard and strategy setup](trading-desk.md) for the additional
reviewed analysis profile; broker connection alone does not install stock rankings or ML.

Version 0.10.0 added authenticated setup for **manual** paper accounts; 0.11.0 adds
the [shared workspace menu and step-by-step guide](workspace.md). The existing
Python 3.13.16 environment and frozen dependencies remain sufficient. The page is
responsive browser UI, not a native mobile app. No real order or fund transfer exists.

## Saved-session check feedback

In **Broker & Data → step 3**, select **Check saved broker session**. No request-token
input is needed: this checks the server's saved access token. The button changes to
**Checking saved broker session…** and a polite live status directly below the buttons
shows progress, followed by success or an error. Setup actions remain disabled while
the request is pending; there is no automatic retry. Previously, errors appeared only
at the top of the long setup page, so a failed check could appear to do nothing.

Success verifies broker profile access only. It does not connect the feed, establish
streaming/history entitlement or approve fresh quotes. A failed recheck removes the
page's earlier verification claim; the saved token is preserved. Check connectivity
and retry. If the token has expired, disconnect any requested feed in step 6, complete
**Open Zerodha login** and 2FA, then **Exchange and verify session** with the new
one-time request token. Login/exchange requests also show progress/results in step 3.
The UI stops waiting after 30 seconds. A profile-check timeout allows an explicit
retry; it does not consume a one-time login token. An exchange timeout remains uncertain:
refresh status before proceeding and start a new login if another exchange is needed.

To load this UI-only change, switch to another workspace section and back to
**Broker & Data**, or reload the workspace and unlock again. Existing servers read
the setup assets on request; no service restart is needed. Verify with
`node --test tests/ui/setup.test.cjs tests/ui/workspace.test.cjs` and
`.venv/bin/pytest tests/unit/test_setup.py tests/functional/test_setup_api.py -q`.
These use simulated broker responses; they do not certify your current broker session.

## Connected feed but missing quotes during an open session

Daily long-term price-basis reviews apply to one IST date. Without today's review,
incoming prices are rejected before quote storage, even with a valid broker session,
connected feed and open market. A missing accepted quote therefore does not prove
that the socket is silent. Paper Trading/Risk Management show this review blocker
explicitly; quote freshness and execution readiness remain separate checks.

With a same-day download ready, use **Review today’s setup** directly in Paper Trading's
warning/quote details. Inspect and confirm the combined source/calendar/shortlist and
eligible current-day reviews. It preserves the installed policy unless you explicitly
chose another; there is no automatic first policy or ML fallback. The button only
previews; **Confirm and prepare** is the consequential approval. If the button is
disabled, follow its current-day download/Manual/custom-profile guidance. Restarting
does not approve the review, and another restart is unnecessary for this UI shortcut.

Review/apply the supported ranked shortlist in Strategies while disconnected in
Manual, resolve the selected symbols' current-day basis in Risk Management, reconnect
explicitly as necessary and wait for new valid quotes. Do not approve unknown actions
just to obtain prices. See [the full recovery steps](trading-desk.md#open-session-with-no-usable-quotes).
The shortlist review link now preserves its fragment, focuses the review section and
does not apply anything automatically. Reload the workspace for the link fix; restart
an older Python server as described in the recovery guide for the new diagnostic API.

If prices are already reviewed but proposals cancel almost immediately, inspect
**Paper Trading** and the current mode. A safety pause returns the desk to Manual;
new good quotes do not rearm it. The whole-second Kite update fix prevents legitimate
receipt-ordered books/repeats from being mistaken for backward data, while preserving
clock/volume/depth checks and one fill budget per exchange timestamp. Restart once to
load that Python change; see [exact cancellation/Automatic behavior](trading-desk.md#cancelled-proposals-and-idle-automatic-mode).
Cancelled daily signals remain terminal when switching to Automatic; its new summary
explains already-handled signals rather than implying immediate new trades.

## After-hours feed offline fix (0.11.1)

On 21 October 2026 after market hours, a read-only probe confirmed a valid profile
(HTTP 200), successful WebSocket handshake and five 184-byte full packets. All five
had a zero bid or ask. The old parser raised a positive-price validation error and
the worker treated it as a broken connection. This was an application bug; neither
missing calendar approval nor a proven expired token explained this occurrence.

The corrected parser ignores full packets with zero bid/ask prices or side quantities,
keeps the healthy connection, and preserves valid packets elsewhere in the same batch.
It never substitutes last price for missing depth. Unknown tokens, malformed framing,
unsupported modes, crossed books and other Quote validation still fail closed.
Ignored observations are excluded from accepted quotes, candles, marking and fills.
An affected symbol's earlier quote immediately loses execution freshness even within
its normal age limit, until another valid quote is accepted. Its partial candle
builders reset rather than silently bridge the missing book. An empty-sided symbol
also cannot become usable through a conflicting valid packet in the same batch.
Other symbols keep their independent freshness checks. The intraday controller runs
its existing stale-data safeguards immediately: disarm entries/cancel pending buys,
and latch the kill switch for affected holdings where the existing policy requires
it. A later valid quote restores data freshness but never silently rearms automation.

To load this fix on your existing 8004 account:

1. Review holdings/pending orders. If an old server is still running, press **Ctrl+C**
   in its terminal. If it is already stopped, go directly to the next step.
   Offline periods cannot fill exits; restart recovery cancels old pending order residue.
2. From the repository root, run `./scripts/start_ui.sh` and keep that terminal open.
3. Reload `/workspace` and unlock with `TRADING_OPERATOR_TOKEN` from your private `.env`.
4. Open **Broker & Data**. Select **Check saved broker session** in step 3.
   If verification succeeds, keep that session. If it fails, complete a fresh login
   and exchange using the existing instructions below; a new login is not necessary
   merely because an after-hours book has no buy/sell side.
5. In step 6, select **Connect paper market data**, review and confirm. Wait a few
   seconds, then select **Refresh setup status**. The new backend reports version
   0.11.1; the launcher refuses to reuse an older running server.
6. Expect **WebSocket connected**, possibly with **Empty-sided/zero-liquidity quotes
   ignored**. The console can still show stale/missing quotes after market hours.
   That means there is no fresh executable quote, not that the socket is broken.
7. During a genuinely reviewed open exchange session, complete calendar and per-symbol
   long-term basis reviews and check fresh quotes/readiness. Do not attest an invented
   session or loosen safeguards to make the status green.

Step 6 distinguishes connecting, reconnecting and exhausted retries. Fixed failure
descriptions identify handshake refusal (session/permission), timeout, broker error,
invalid data or application processing failure. They never show raw broker messages,
URLs or credentials. Refresh explicitly to see progress. There are at most ten
consecutive failures with bounded exponential backoff; a valid binary message,
including a heartbeat, resets that failure budget. After exhaustion, **Disconnect
market data**, resolve the stated cause, then reconnect explicitly. Disconnecting
also re-enables replacement login/selection controls. Investigate invalid-data or
processing failures rather than repeatedly reconnecting a faulty account.

A diagnostic-only fixed-worker check stayed connected for 15 seconds, ignored all
five empty-sided observations and produced zero usable quotes. Its callbacks were
isolated from the account; no paper/broker orders or review attestations were made.
This is a brief actual transport check, not a full-session/fresh-execution acceptance.
The implementation did not stop/restart an operator process. At its final local check,
8004 was no longer listening, so the next action is to start the updated launcher.

## Why the Zerodha redirect token does not unlock the app

| Value | Where it comes from | Where to use it |
|---|---|---|
| `TRADING_OPERATOR_TOKEN` | Your private local `.env`, generated during initial setup | Unlock the trading console, Setup and portfolio pages |
| Kite API key / secret | Your app in the Kite developer console | Setup → Save app credentials; never in the local unlock field |
| `request_token` | Zerodha's redirect after successful browser login | Setup → Exchange and verify session; single-use and short-lived |
| `access_token` | Server exchanges the request token and verifies the profile | Server-only market-data session; not a dashboard password |

Open your private local `.env` in your editor and copy **only the value** after
`TRADING_OPERATOR_TOKEN=` into the dashboard unlock field. Do not include the variable
name or surrounding quotes. Do not send any token in chat. The error message and all
three access panels now explicitly distinguish local access from broker access.

The operator token is retained only in workspace/active-section memory and sent as a bearer
header. One workspace unlock covers its menu sections. A separate workspace tab or
reload requires another unlock; simply changing browser tabs does not intentionally
lock it. Lock/reload clears it; no URL, cookie,
local/session storage or password-manager persistence is implemented. Locking a page
does not stop the server, disconnect quotes, disarm automation or close holdings.

## Start the UI yourself

In Terminal, from the repository root:

```sh
./scripts/start_ui.sh
```

For this workspace, this selects the existing `config/first-paper-session.toml`
and opens <http://127.0.0.1:8004/workspace>. A matching same-version server is opened without
starting another database owner or running recovery. If no server listens, it starts
one in the foreground and opens the browser. Keep that terminal running. Press
**Ctrl+C** for a graceful stop; inspect positions/pending orders beforehand because
offline periods cannot fill protective exits. Restart recovery cancels old pending
orders and requires fresh accepted quotes before entries.

To select another account explicitly:

```sh
./scripts/start_ui.sh config/your-account.toml
```

Selection precedence: explicit argument; custom `TRADING_CONFIG`; the workspace's
first-session config when present and the environment otherwise selects the default
paper config; finally `config/paper.toml`. URLs use the selected config's host/port,
so do not assume every account is on 8004. Loopback is enforced.

The launcher loads your trusted `.env`, then `.env.session-first` if present.
`TRADING_SESSION_FILE` may select a different private session file. It never prints
credentials. `TRADING_OPERATOR_TOKEN` must already exist and pass the 32-character
minimum. The frozen environment, local operator credential and account's financial
policy still require initial local setup; this launcher does not install Python,
purchase a subscription, choose risk limits or replace an existing account.

An occupied port, wrong operator credential, older server without Setup, or different
account identity produces a clear refusal to start another process. Review the old
server's terminal/config; do not kill an unrelated account merely to reuse its port.
The existing-server probe refuses HTTP redirects and bypasses HTTP proxy settings,
so it does not forward the local bearer token to another destination.

The equivalent lower-level start, after loading the environment yourself, is:

```sh
.venv/bin/trading-agent --config config/first-paper-session.toml serve --open
```

This starts **without a feed**, even if broker credentials were saved earlier. It
keeps the UI usable after token expiry. Connect explicitly in Setup. To start with
an already validated selection/session, retain `serve --stream --open`; broker
failures can then prevent startup. Do not use the shortcut on an automation-bound
account: retain its exact `paper-init`/`--automate`/model policy from [paper-feed.md](paper-feed.md).

## Use Setup

Open <http://127.0.0.1:8004/setup> for the current workspace or follow the console's
**Kite login, feed selection and session setup** link. Unlock with your operator
token once in the shared workspace; menu navigation retains that local access.
No private setup API is accessed before unlocking. Refresh setup status is
explicit, not automatic background login or credential probing.

1. **Register your Kite app externally.** Use the developer-console link. Set the
   redirect URL to the exact loopback root shown on Setup, including the port. The
   optional postback is unused. App creation, account onboarding, subscription
   purchase, login and 2FA stay on Zerodha's site. Check current market-data
   entitlement/billing there; profile success alone does not prove it.
2. **Save app credentials, if necessary.** Existing environment credentials are
   recognized. Do not resave them merely to view status. To replace them, disconnect
   first; replacement clears the saved broker access token. Password inputs clear
   before waiting for a response. No existing secret or access token is returned.
   The API key is a public app identifier and appears in the official login URL.
3. **Open Zerodha login.** Complete the real browser login/2FA. The login popup's
   registered callback returns its one-time token to the originating Setup tab,
   guarded by matching origin, popup identity and a five-minute random login state.
   The UI popup callback removes its query before handing off. Select **Exchange
   and verify session** promptly; exchange is explicit, not automatic. If browser
   opener isolation or a blocked popup prevents capture, allow the popup and start
   a fresh login, then manually copy only `request_token` into the field. Legacy
   CLI redirects without a Setup popup remain available for manual capture.
4. **Check the saved broker session** to verify profile access. The server persists
   a successfully exchanged token privately; copying it into `.env` and restarting
   are no longer necessary for the running manual account. Tokens still expire
   daily; there is no refresh or 2FA bypass. Disconnect before a replacement login.
   Starting a new login supersedes an earlier pending attempt. An uncertain/failed
   exchange consumes that attempt locally; start a new login, not a replay.
5. **Download / validate catalog**, then enter comma-separated symbols within the
   configured capacity shown beside the field (10 by default).
   The catalog is a lookup of supported names/tokens; it does not stream all catalog
   instruments. The current saved watchlist receives live quotes for paper fills and
   holdings monitoring. Names are not hardcoded. Set `stream_limit` to an integer
   from 1 through 3,000 in the account TOML and restart the owning service before
   reviewing a larger selection. The UI reads this configured limit from authenticated
   setup status; guidance, counts, the accessible field label and text capacity all
   use it. **Saved feed subscriptions (N of capacity)** shows the committed selection separately
   from unsaved input edits. The count/list changes only after validation and explicit
   confirmation succeed. Tokens identify instruments to the broker; tick is the
   permitted rupee price increment. For wider discovery, use Strategies' Nifty
   100/500 preparation and review the proposed execution shortlist. Qualifying reviewed
   shares are ranked by historical gross return, not a proven future-profit estimate.
   `BEL` and `NSE:BEL` normalize to the same exact catalog instrument. Review the
   symbol list in the confirmation dialog, then save. The server resolves tokens
   and tick sizes; missing/duplicate symbols and held-symbol omissions are refused.
   Disconnect first and resolve pending orders before selection changes. Conflicting
   imported mappings roll back rather than silently changing ticks/tokens.
   Large symbol-selection requests have a bounded size budget proportional to capacity,
   never above 128 KiB; other setup requests, including credentials/session exchange,
   retain the 8 KiB maximum. An oversized, over-count or invalid request changes no
   saved selection or account balances. Trim extra JSON padding/escaped spellings,
   correct the symbol list and review again. Increasing transport capacity does not
   expand the desk's separate ten-stock ranked execution shortlist or validate
   throughput. See [feed workload limits](paper-feed.md#explicit-stream-capacity).
6. **Add a reviewed session.** Enter a current/future IST date, supported opening
   and closing times, and a source reference. Review NSE notices yourself and check
   the attestation; the UI never assumes weekdays or prechecks the box. Confirm the
   date/times/reference in the dialog. On unlock, open defaults to **09:15 AM** and
   close to **03:30 PM IST**. Both remain editable; status refresh preserves edits,
   including a cleared value. Lock clears the form; unlocking restores the defaults
   and an unchecked review. Default hours do not create or approve calendar entries.
   Supported special-session changes must still fit the existing 09:15–15:30 bounds;
   this change does not extend supported exchange hours. Review the
   date-specific notices. Existing definitions cannot be changed;
   identical repeats are a no-op. Unsupported evening sessions stay closed. A
   private immutable calendar snapshot is written before the config points at it;
   the running engine uses the saved definitions without a restart. Future dates
   still need individual review. Only the next 31 current/future definitions display.
7. **Connect paper market data.** Review the selected symbols and explicit
   confirmation that new quotes can resume existing pending fills/protective exits.
   This verifies the broker profile and starts the
   full-mode stream for the selected catalog. A requested/connected socket does
   not prove fresh usable quotes. Refresh setup status, then inspect readiness in
   Paper Trading or Risk Management. The connect button never arms automation or submits a new order intent.
8. **Complete long-term price-basis reviews separately.** Risk Management's existing
   per-symbol current-session review is still required. A calendar entry does not
   attest that corporate actions are absent. Review actions since the last accepted
   quote, including offline periods, and preserve unresolved quarantines. Wait for
   new accepted quotes before a [portfolio purchase preview](portfolio-contributions.md).

The `EQ` catalog category can include ETFs such as GOLDCASE. Current costs assume
equity shares; ETF-specific fee/classification support remains pending. A feed
subscription is not execution approval. Setup still permits monitoring catalog EQ
rows; the strategy profile excludes symbols lacking reviewed equity-share
classification. This does not add ETF fee/accounting support.
Leave unsupported instruments out of paper order submission and basis approvals.

## Private persistence and account boundaries

Per-account `config/*-session.toml` copies are ignored by Git and source packaging,
along with `.env*` secrets and `data/`. This includes the workspace's first-session
config. Keep other private account configs outside tracked templates or explicitly
ignore them before packaging/sharing. The current workspace's `.env` account selector
was corrected to the existing port-8004 first-session config; no credential value or
financial policy changed.

UI credentials/session are stored as `<database-stem>.kite.json` beside the selected
database, with mode 0600, through atomic replacement. This is private plaintext, not
encrypted storage; keep the machine/account storage private. Symbol selection and
the private calendar path update only the server-selected account config, preserving
its other fields/comments. Financial policy changes are refused. No browser-supplied
filesystem path, broker endpoint, order method or shell command is accepted.

Stored UI credentials take precedence over environment broker values for the manual
service. Existing `login-url`, `exchange-token`, `profile`, `instruments` and historical
CLI commands retain their environment-based behavior. They do not automatically read
the UI credential store. The CLI exchange's no-overwrite private session file remains
supported. Automated accounts keep their existing environment/bound-controller flow.

Individual file writes are atomic. A failed calendar config update can leave an
unused private snapshot, while the previous config/live calendar stays unchanged.
Do not delete calendars referenced by a config or mutate used calendar history.
Malformed/nonprivate/symlink credential files fail closed at startup and require
local investigation; setup does not silently discard a stored session.

## Failures and recovery

| Situation | Recovery |
|---|---|
| Local authorization failed | Use the operator value from the `.env` loaded by the server; a redirect token is not the local credential |
| Credential/login/catalog/selection controls disabled | Disconnect the existing requested feed first; automation-bound accounts use their dedicated workflow |
| Zerodha login disabled but session is verified | No new login is needed. To replace the session, confirm Disconnect in step 6, refresh status, then use step 3; no need to restart the server |
| Token expired or exchange outcome uncertain | Refresh status, disconnect, open a fresh login and exchange the new one-time token; no automatic action retries |
| Profile passes, feed fails | Check paid data entitlement, current app key/session and network; reconnect only after inspecting status |
| Page locks during a pending operation | Sensitive fields and late responses clear; the server may have completed the operation, so unlock/refresh before retrying |
| Broker request fails | Setup returns a credential-free explanation and keeps independent account/risk controls available; raw third-party errors are withheld |
| Calendar/symbol save refused | Read the reason; resolve pending orders/held-symbol omissions or investigate changed policy/mapping; do not edit SQLite to bypass it |
| `/ready` is 503 | Inspect current calendar, per-symbol reviews, new accepted quotes, entry hours and all risk/fault reasons in the console |
| Disconnect market data | Confirmation is required; holdings remain and fills/exits must wait for fresh quotes after reconnect |

Complex corporate-action batches/receipts, policy changes, research/model approval,
OS deployment and physical-device recovery remain the documented offline workflows.
This release does not turn every administrative task into a browser action.

The selected symbols are a manual feed universe. Automatic profit-oriented discovery
for both horizons is specified in [stock-selection-plan.md](stock-selection-plan.md)
and is not implemented by the symbol-selection form.

## Confirmation dialog position and audit status

The baseline setup controller positions confirmation dialogs within the visible
workspace area before focus, and follows scrolling/resizing (including a mobile
visual viewport). This addresses the off-screen native iframe centering shown in
the operator's screenshot; actual Firefox rendering still requires verification.
Leave Broker & Data and return to load current static assets, or reload and
unlock again. A Python restart is not required solely for this static-script change.
Neither action confirms a connection. Cancel if the full explanation is not visible;
reopening must still show the selected stocks and the pending-fill/protection warning.
Only your explicit Confirm requests the feed. Connection remains distinct from fresh
quotes and risk approval. See [UX_AUDIT.md](UX_AUDIT.md) for the broader modal/focus
acceptance gap and [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) for the V2 approval
boundary. Phase 1 itself changes documentation only, not application behavior.
