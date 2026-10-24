# How to use Agentic Trader

Daily operations now have a [read-only report, independent monitor, opt-in IST data
acquisition and verified backup/restore drill](operations-automation.md). Run
`./scripts/start_operations.sh` beside the owning UI server for local monitoring;
add `--download-universe nifty100 --after 08:30` only to opt into scheduled acquisition.
It stops at downloaded evidence: review/install, current-day basis attestations and
Approval/Automatic activation remain explicit. No service-manager template is enabled
automatically. The guide covers commands, output, uncertain outcomes and deployment limits.

For the complete daily routine, read [Daily operator checklist and strategy-data
explanation](daily-operator-checklist.md). It covers every manual step from opening
the account through reviews, activation, supervision, reconciliation and backups,
with reasons, expected results and recovery. The normal guided strategy workflow
needs a current-IST-day download and explicit review; saved bundles do not refresh
automatically. Reuse valid same-day work. Catalog imports and app registration are
conditional/initial tasks, while long-term price-basis reviews are session-specific.

Version **0.19.0** improves the existing interface with labelled local SVG icons,
a compact workspace header, a collapsible setup explanation and shorter repeated
status messages. Portfolio keeps valuation state visible while folding formulas into
details; Stock Analysis groups chart help and the legend. Investment-policy drafts now
use four steps with progress, contextual unit help and field-linked validation. Moving
between steps never saves or selects financial defaults. All existing exact values,
stale/missing states, navigation guards and reviewed confirmations remain in force.
Restart an older owning UI server, reload the workspace and unlock to load this version.
See [the interface guide and recovery behavior](ui-experience.md).

Version **0.18.0** adds **Strategies → Investment policy drafts**. Choose a months-based
or multi-year holding horizon and monthly or quarterly reviews, with explicit screening,
allocation and exit limits. All fields start blank; incomplete drafts can be reviewed
and saved as separate immutable snapshots. **Specified** records your choices; it does
not activate a policy or enable its execution/backtest. Save/discard unsaved edits before
menu navigation. An uncertain save requires refreshing saved snapshots before an explicit
same-content retry. No automatic save/retry or account-policy change occurs.
See [inputs, exact values, confirmations and recovery](investment-policy-drafts.md).

The new offline command `investment-policy DRAFT_JSON` prints a canonical inspection
without saving or opening an account. Add `--calendar CALENDAR_JSON --start YYYY-MM-DD
--as-of AWARE_ISO_TIMESTAMP` together for a bounded monthly/quarterly review-date preview.
Calendar coverage must explicitly cover each whole period; its completeness is your
unverified declaration. Missing coverage/choices remain unavailable. Preview dates never
schedule execution or establish a minimum holding period or profitable strategy.
See [the exact CLI/calendar schema](investment-policy-drafts.md#inspect-a-local-draft-or-preview-review-dates).

The earlier **0.17.0** Phase 5 slice remains available: **Backtesting** has registered
inputs, confirmed isolated-job admission, saved lifecycle/cancellation and verified
bounded report views. Launch requires verified OS isolation and hard limits; it is
**unavailable on the implementation Mac**, and the browser-job backend currently
supports only Darwin sandboxing. Registration and saved reads remain available.
See [browser backtesting](browser-backtesting.md) for commands, limits and recovery.

**Portfolio** adds exact cash/held-share allocation at current accepted bids, with
claims and pending commitments shown separately. Missing/stale held prices disable
weights. A pure daily-performance calculator is implemented, but accounts and legacy
replays lack accepted daily valuation/flow history: CAGR, Sharpe, Sortino and monthly
portfolio returns stay unavailable there. See [portfolio analytics](portfolio-analytics.md).

The existing offline replay retains its actual strategy/holding-session cap (default
20); connected parity, out-of-sample/walk-forward browser orchestration, executable
months-to-years strategies, target allocation and rebalancing remain unfinished Phase 5
work. Drafts now record both horizon/cadence options, while each draft requires a specific
choice. No draft selects an active account policy or changes its holding duration.

Phase 4 price research remains available: Daily/Weekly/Monthly charts, 15 causal
fixed-precision indicators, explicit warmup/gap states, known share-action-adjusted
OHLC/volume, price drawdown and optional traceable local benchmarks. Range controls
change display only; Discovery explains existing predicates without reranking.
Weekly/monthly completeness requires a hash-bound review. Preparation still supplies
at most 60 completed sessions from its supported current-year source, so long warmup
needs separately reviewed history. Licensed fundamentals remain unavailable.
See [investment research](investment-research.md).

The twelve-destination light workspace retains existing paper authorization, risk,
setup, purchases/SIP and shared confirmations. No upgrade activates an account or
changes credentials/watchlists/holdings. Automated synthetic/local evidence is distinct
from rendered browser/mobile, real OS, broker, source-license and device acceptance;
those external gates remain open. See [the frontend component guide](frontend-modernization.md)
and [validation record](test-plan.md).

**Stock Analysis** charts actual saved daily/minute candles and indicators; it
does not download from the broker when opened. Missing/stale data stays visible,
and a chart is not an execution quote or a trade approval. See
[Stock Analysis](market-analysis.md) for sources, inputs and limitations.

**If the feed connects but Approval/Automatic stay disabled:** open Paper Trading →
**Your next step**. A socket supplies quotes; it does not install a strategy, validate
ML or open a market session. The cards now explain every prerequisite, current IST
time, next reviewed opening, entry hours and each selected stock's quote age/basis.

In **Broker & Data**, step 4 separates the complete catalog lookup from the account's
saved live-feed watchlist (at most ten symbols under the app's current limit). The
displayed names are editable saved subscriptions; broader Nifty 100/500 research is
available in **Strategies**. The connection overview recommends a numbered setup
step. Open any step or use Back/Continue; navigation never saves or connects.
Editing the input does not change the saved list until
you validate, save and confirm. Step 5 now defaults to **09:15 AM–03:30 PM IST**.
The times remain editable and survive status refresh; review the date/notices, supply
a reference and explicitly confirm before saving. Defaults do not approve a session.

**Feed connected, market open, but no usable quotes:** a missing daily price-basis
review can block incoming long-term quotes before they are stored. Yesterday's review
does not cover today. With current-day data ready, select **Review today’s setup**
beside the warning, inspect the summary/sources and explicitly confirm. This uses the
existing installed policy unless you selected another policy; a first setup still needs
an explicit policy choice. The summary lists which daily reviews are eligible and
which need separate attention. The shortcut opens a preview; approval is still pending
until **Confirm and prepare**. It disappears after the blocker clears. For older/missing
data, use the displayed preparation link to download current-day sources first.
Quote details in Paper Trading and Risk Management explain
this separately from an old quote, a rejected observation or a disconnected feed.
Resolve the supported shortlist, review actual current-day corporate actions/price
basis in Risk Management and await a new valid quote. Do not approve a review merely
to clear the warning. See [quote and shortlist recovery](trading-desk.md#open-session-with-no-usable-quotes).
**Review the ranked shortlist** now opens and focuses the review section; it never
applies the list. Reload the whole workspace for the navigation fix. The new Python
diagnostics require restarting an older server in its owning terminal, then running
`./scripts/start_ui.sh`, unlocking and explicitly reconnecting as appropriate.

**Approval proposals cancelled, or Automatic looks idle:** inspect Paper Trading.
A cancelled proposal without an order bought no shares. A safety pause cancels pending
approval authority and returns the desk to Manual; recovering quotes do not rearm it.
The corrected Kite path accepts receipt-ordered whole-second book updates without
reusing that second's fill liquidity; unchanged repeats cannot renew freshness.
See [cancellation and idle-mode recovery](trading-desk.md#cancelled-proposals-and-idle-automatic-mode).
To load this Python fix, stop the owning server with Ctrl+C, run
`./scripts/start_ui.sh`, reload/unlock, then review readiness before explicitly choosing
a mode. Restart retains cancelled history. Existing daily signals are not replayed by
mode changes; Automatic still needs a new eligible signal and independent risk approval.

For the missing strategy, use **Strategies** → **Prepare a paper strategy**:

1. Check your saved broker session and import the NSE catalog in **Broker & Data**.
   Step 3 shows **Checking…**, then a result directly below the buttons. A successful
   profile check does not prove streaming access or fresh quotes. On failure, check
   connectivity and retry; if expired, disconnect a requested feed in step 6 and
   complete a fresh login/token exchange. See [session-check recovery](ui-setup.md#saved-session-check-feedback).
2. In Strategies, choose Nifty 100 or Nifty 500 and confirm **Download strategy data**.
   Watch progress; review sources and exclusions. It can run after hours. Your feed,
   mode and virtual cash are unchanged by the download.
3. Choose **Rules only** explicitly for the experimental paper policy, or **Rules + ML**
   if a separately supplied matching model is configured. Click **Review and finish setup**.
4. Review the summary: exact ranked stocks, source links, all proposed session dates/hours,
   saved calendar corrections and any eligible price-basis reviews included for today.
   Check the **one acknowledgement** and click **Confirm and prepare**. The server handles
   disconnect → install → apply shortlist → listed current-day reviews → request connection.
   No review notes, CSV copying or separate feed/shortlist buttons are needed on this path.
   Used calendar history, held-position basis and quarantines need separate review; they
   cannot be cleared automatically. Calendar editing remains under **Advanced: edit dates
   and install separately**. Setup stays Manual and does not change virtual capital.
5. Return to Paper Trading. When readiness permits, choose **Start approval mode** or **Start automatic paper mode**
   and confirm. Use **Paper Trading** for reasons, orders, later fills and fees.
   After hours the setup can finish, but modes still wait for an open entry session and
   fresh usable quotes. No future automatic activation is scheduled.

If your screenshot already shows **65 / 65 downloaded · Ready for review**, start at
step 3; there is no need to repeat a same-day completed download. A two-minute review
expiry or changed account needs a fresh summary, not necessarily a new download.
Downloads must be refreshed on a new IST date or after a newly completed daily session.
If setup stops, the displayed phase explains what remains. Earlier saved steps remain;
refresh status, resolve the problem and review again. Never assume a failed HTTP response
means nothing was saved. The same completed confirmation is returned without repeating
connection/review steps. Restart interrupts pending attempts rather than replaying them.

If your currently running UI is older, stop its owning terminal with Ctrl+C and run
`./scripts/start_ui.sh` once. The launcher detects an existing matching server; it
does not hot-reload Python modules. Unlock again after restarting. No process or
strategy is automatically restarted or armed by this upgrade.

See [Strategy preparation](strategy-preparation.md) for exact inputs, source review,
ML configuration, early-year/calendar limits, interrupted download recovery, refreshes
and persistence behavior. Existing custom `TRADING_ANALYSIS_PROFILE` configurations
remain supported and take precedence on restart; clear that override explicitly when
switching to the UI-managed profile.

The decision workflow introduced in 0.12.0 now appears across Dashboard, Strategies
and Paper Trading. Manual, approval/semi-autonomous and automatic paper modes
are explicit, confirmed choices. Proposals explain their source and require fresh
bounded previews; activity distinguishes acceptance from actual quote-driven fills.
Both intraday and long-term strategy profiles are implemented, with independent risk
checks and protective exits. Your old five subscriptions are not silently replaced.
A reviewed real-data profile and matching validated model are prerequisites for
rules-plus-ML discovery; real-data acquisition is now available through the reviewed
0.13 workflow above, while matching model evidence remains separately required. Read the
[complete new workflow and configuration guide](trading-desk.md) before activating.

Version 0.11.1 fixes a verified after-hours feed disconnection: full quote packets
with an empty bid/ask or zero side quantity are ignored without disconnecting.
They cannot create accepted quotes, candles or paper fills. Any earlier quote for
an affected symbol is immediately unusable until a new valid quote passes acceptance;
other symbols retain their independent freshness checks. Setup step 6 now shows
safe connection failure/retry details and a count of these unusable observations.
Restart an older server once to load the fix, then explicitly connect and refresh
Setup status; see [the exact recovery steps](ui-setup.md#after-hours-feed-offline-fix-0111).
Connected transport still requires fresh executable quotes, reviewed sessions and
all independent risk/basis checks before trading.

## 1. Scope and prerequisites

The operator's latest goal is profit-oriented candidate discovery for **both**
intraday and long-term accounts, beyond a manually selected watchlist. The
[stock-selection plan](stock-selection-plan.md) now records profile-driven screening,
approval/automatic execution and activity UI; real-data acquisition/acceptance remain next. A current feed
selection is not a stock ranking, and the current research rules/synthetic tests do
not establish profitable real-market picks. Real data and independent net-of-cost
validation are prerequisites; reviewed profile-driven screening is available, while automatic broad-data acquisition
and empirical qualified-profit rankings remain pending.

This release implements Phases 1–4 engineering: virtual execution/risk controls,
predeclared rules, isolated backtests, chronological ML research and opt-in
supervised intraday feed automation, long-term paper holdings/corporate actions and
offline completed-daily screening, quote execution and separate daily ML validation.
Long-term accounts also support reviewed cash-budget contributions and explicit-session SIP plans.
Reviewed profiles can propose a bounded execution shortlist and paper strategy
decisions; this does not establish qualified profit forecasts or execute live trades. Sample trades are synthetic. Read
[risk-policy.md](risk-policy.md) before submitting paper intents.

Use macOS or 64-bit Raspberry Pi OS, a patched Python **3.13.16**, local disk with
room for an expanding quote journal, and an accurate system clock. Python's supported
releases are listed at [python.org](https://www.python.org/downloads/).
For Pi, prefer an SSD and reliable power. Do not put the database on a network drive.
Use one owning process per account database. A second process fails to acquire its lock.

## 2. Install and verify

Install `uv` using its [official instructions](https://docs.astral.sh/uv/getting-started/installation/).
Then run these commands from the repository root:

```sh
uv sync --frozen --all-extras
source .venv/bin/activate
trading-agent environment
sh scripts/check_environment.sh
pytest --cov=trading_agent
ruff check .
mypy src/trading_agent
python scripts/check_secrets.py
pip-audit --skip-editable
```

`uv.lock` contains exact package versions and artifact hashes. Always use `--frozen`
for deployment. `pyproject.toml` expresses supported version ranges; do not replace
the lock with an unconstrained `pip install`. The `broker` extra supplies HTTP and
WebSocket transports; the `dev` extra supplies checks and `ml` supplies offline
training. Runtime/scoring does not import the training stack. For a smaller deployed
environment, use `uv sync --frozen --extra broker` after development validation.
`scripts/setup_macos.sh` and `scripts/setup_pi.sh` wrap the initial setup.

The workspace prepared for this implementation already contains `.venv`, backed by
an ignored `.python-runtime` copy of patched Python. It does not depend on `/tmp`.
To run it immediately, use `.venv/bin/trading-agent ...`. Both directories are local
artifacts and must be recreated on another machine. `uv` itself is not installed
globally by this repository.

## 3. Run the offline demonstration first

```sh
trading-agent demo --directory data/demo-first
```

This creates a separate virtual account, a reviewed **synthetic** session, one
imaginary `NSE:DEMO` instrument, an entry intent, subsequent fill quotes, and a
target exit. It writes `events.jsonl`, `report.json`, and `demo.sqlite3` inside that
directory. It does not contact Kite or use real credentials. Reusing the directory
is refused to prevent mixing runs; use `data/demo-second` for another run.

Expected result for this fixture: two fills, zero remaining positions, ₹25,099.11
cash, and ₹5.39 estimated fees. This is a deliberately constructed accounting
example, not a strategy result. Repeated runs in new directories produce identical
results and journal hashes.

## 4. Configure a paper account

```sh
cp .env.example .env
chmod 600 .env
python -c 'import secrets; print(secrets.token_urlsafe(32))'
```

Put the generated value in `TRADING_OPERATOR_TOKEN` in `.env`. Keep the file private.
`TRADING_MODE` must equal `paper`; any other value aborts startup. To load values in
your shell explicitly:

```sh
set -a
source .env
set +a
trading-agent init-db
```

Do not paste credentials into shell commands, source code, issue reports, or chat.
`.env` is a shell file, so only source files you created and trust. The CLI does not
implicitly load environment files. The launchd wrapper explicitly loads `.env`.

`config/paper.toml` contains the full policy. File paths resolve from the working
directory. Copy it for isolated experiments and select it with:

```sh
trading-agent --config config/my-paper.toml init-db
```

The argument belongs **before** the command. Set a different `database` for each
account/experiment. Monetary config values are decimal strings. Risk and simulation
settings are hashed into the account; changing them requires a new database. Never
edit balances or risk state directly in SQLite. Changing the starting cash of an
existing account is rejected.

## 5. Review the exchange calendar

`config/sessions.csv` deliberately contains only a header. Unknown dates are closed.
Consult the [NSE exchange holiday notices](https://www.nseindia.com/resources/exchange-communication-holidays)
and current circulars, then add reviewed dates and actual open/close times:

```csv
date,open,close,source
YYYY-MM-DD,09:15,15:30,URL-or-reference-of-reviewed-NSE-notice
```

Replace the example placeholders; do not paste them literally. Add only confirmed
sessions. Do not assume weekdays are open. A missing source or duplicate date is
rejected. Early closes move the entry cutoff and flatten request to fifteen minutes
before the listed close. The configured 09:30–14:30 entry window and 15:15 flatten
time still apply when earlier. Special evening sessions outside the supported
policy are not supported; leave them closed. Restart after calendar edits.

## 6. Start the dashboard without Kite

For the easiest repeat start and browser setup, run:

```sh
./scripts/start_ui.sh
```

The workspace shortcut selects the existing first-session config (currently port
8004), opens a matching running server or starts one without a feed, and opens your
browser. Keep its terminal running; Ctrl+C stops a server started there. See
[ui-setup.md](ui-setup.md) for selection precedence, first setup, repeated starts,
daily login, credentials, catalog/symbol selection, sourced calendar and feed controls.
`TRADING_OPERATOR_TOKEN` from your private `.env` unlocks the local app;
**Zerodha request/access tokens do not**. The [workspace menu](workspace.md) retains
one unlock while moving among the twelve sidebar destinations and Purchases & SIP. Reload/new
workspace tabs still require unlocking; merely switching browser tabs does not
intentionally lock access. **Learning Center** explains the connection steps,
actual configured hours and manual/automated trading frequency. The Dashboard’s
contextual onboarding links to unfinished strategy, calendar or feed setup.

The lower-level command with an explicitly loaded environment remains:

```sh
trading-agent serve
```

Open <http://127.0.0.1:8000>, enter the operator token, and select **Unlock / refresh**.
The responsive light workspace shows portfolio values and next actions first.
Use **Strategies** for preparation and shortlist review, **Paper Trading** for
orders/fills, **Risk Management** for exposure, basis review and emergency/entry controls,
and **Broker & Data** for credentials and feed administration. Desktop uses a
sidebar and columns; narrow widths adapt the navigation and stack panels.
There is no native Android/iOS app. It polls one consistent response every three
seconds while visible and marks old data stale after six seconds. Displayed update
times use IST; detailed raw timestamps remain UTC. **Lock** clears account values and
the token from the tab without stopping/disarming the server. Arming and kill reset
require confirmation; kill/flatten/disarm act immediately. See the complete
[console guide](operator-console.md), including order-history limits, timed-out actions,
mobile/private access and the remaining physical-device checks.

With no feed, `/health` is 200 and `/ready` is 503. This is expected. The app starts
without Kite credentials. With no operator token, the public page and health checks
work and all account/control routes return 503. A stale displayed valuation is an
estimate; check `valuation_fresh` before interpreting it.

Only loopback binding is permitted. Do not expose the port publicly. For remote
operation, use a private connection with an SSH local port forward to the loopback
listener. The API has no cookie login and does not enable CORS.

## 7. Connect read-only Kite market data

Version 0.10.0 provides the [browser Setup workflow](ui-setup.md) at `/setup` on
manual services. Login/2FA and app registration remain on Zerodha's site, while
the local page handles explicit exchange/profile, catalog import, symbol selection,
reviewed session additions and connect/disconnect. The CLI steps below remain valid.

For the complete first-session sequence, developer-app registration, current plan
requirements, private daily-token handling and separate intraday/long-term UI flows,
follow [First paper session with live Kite data](first-paper-session.md).
If the example URL refuses connections, follow its
[dashboard startup checks](first-paper-session.md#if-the-dashboard-url-does-not-open):
the copied config's port must match the URL, preflight does not start a server,
and streaming cannot start with an empty token selection. An offline `serve`
can load the console while keeping entries blocked until feed setup is complete.
Feed selection is separate from execution eligibility: catalog `EQ` rows can include
ETFs, while current fee estimates model equity shares. Read the detailed guide's
instrument-class limits before submitting orders. The current partial real-session
evidence is recorded in [acceptance.md](acceptance.md#first-connected-session-observation-21-october-2026).

An appropriate Kite application and market-data entitlement are required. Verify
current availability in the [Kite documentation](https://kite.trade/docs/connect/v3/)
and developer console before purchasing anything. The application uses the official
HTTP/WebSocket protocol through restricted transports. The official Python SDK is
omitted because its pinned transport failed the dependency scan; see
[implementation-plan.md](implementation-plan.md).

1. Register a Kite app and supported redirect URL. Complete the normal browser login
   and 2FA yourself. No login or 2FA bypass is implemented.
2. Add `KITE_API_KEY` and `KITE_API_SECRET` to the private `.env`, then reload it.
3. Run `trading-agent login-url`, open the returned URL, and finish manual login.
4. Read the one-time `request_token` from the redirect URL. Exchange it promptly:

   ```sh
   trading-agent exchange-token --output .env.session
   source .env.session
   trading-agent profile
   ```

   The request token is entered at a hidden prompt, not as a command-line argument.
   `.env.session` is created mode 0600 and refuses to overwrite an existing file.
   Archive/remove the old private session file yourself before a new exchange, or
   choose `.env.session-next`. Copying its variable into `.env` is necessary if using
   the launchd wrapper, which sources `.env` only. For systemd, update the private
   `EnvironmentFile` and restart. Never print the file in logs.
5. With the service stopped, run `trading-agent instruments` to import the NSE cash
   catalog. Select one to ten reviewed tokens in `stream_tokens` in TOML. Inspect the
   catalog locally using `sqlite3 data/paper.sqlite3 'select symbol,token,tick from instruments;'`.
   The numeric token is checked against the symbol and tick size. Instrument changes
   require review; conflicting remappings are rejected.
6. Ensure today's reviewed session exists, then run:

   ```sh
   trading-agent serve --stream
   ```

The worker subscribes in full mode, validates binary packets and UTC exchange epochs,
and records quote receipt times. Missing depth, unexpected instruments, invalid
packets, broker errors, or transport failures disable entries. A reconnect requires
new quotes for each instrument; cached quotes do not establish freshness. Transient
failures retry with bounded exponential backoff, up to ten consecutive failures.
After exhaustion or authentication expiry, fix the session and restart the worker.

Kite documents access-token expiry at 06:00 the next day, with earlier invalidation
possible. Repeat supported manual login when needed; there is no refresh bypass.
See the [official login flow](https://kite.trade/docs/connect/v3/user/).

## 8. Download historical candles

Stop the service before database-owning CLI commands. Import instruments first.

```sh
trading-agent historical NSE:INFY \
  --start 2026-10-01T09:15:00+05:30 \
  --end 2026-10-01T15:30:00+05:30 --minutes 5
```

The symbol is an example, not a recommendation. Choose a confirmed session, an
instrument in your catalog, and a range in the past. Requests are limited to thirty
days each and sent once without retry loops. Respect the current broker rate limits;
run downloads serially. Only completed candles are stored. Conflicting revisions
fail instead of overwriting earlier research data. Gap flags prevent the feature
engine from accepting incomplete series; explicitly reload/rewarm it with verified
contiguous historical data before later strategy use.

## 9. Submit a virtual intent

Phase 1 has no automatic strategy. An authenticated operator or local research
client may submit an intent through `POST /api/paper/intents`. Use the example schema
in [api-contracts.md](api-contracts.md). Do this only with fresh connected quotes,
a known session, a valid stop/target on the instrument tick grid, and a current aware
`decision_time`. Quantity is assigned by the risk engine, not by the client.

An accepted intent reserves cash and risk. It does not fill immediately. A later
quote must satisfy simulated latency, liquidity, entry time, and the price cap.
Adverse repricing cancels it. The TTL is thirty seconds. Partial fills retain
reservations for the unfilled amount. Every state transition and fill is journaled.
Reuse an intent ID only for an equivalent normalized candidate: an identical
request returns the existing order; different instructions return 409. Rejected
IDs also remain durable; corrected instructions require a new ID.

## 10. Kill, flatten, and reset

**Activate kill switch** durably disables entries, cancels pending buys, and queues
virtual sells for open positions. **Queue flatten** does the same with a different
audit reason. Exits wait for a later fresh quote, an open reviewed session and bid
liquidity. Stop and target triggers use bid prices. At 15:15 IST or fifteen minutes
before an early close, the watchdog requests exits even if no ticks arrive. It cannot
invent liquidity. An unresolved overnight position keeps entries blocked.

**Reset kill switch** requires authentication, no position or pending order, no
unresolved fault, and no current daily-loss/streak breach. It never resets account
balances. Loss/streak budgets roll on a new local date only when the portfolio is
flat; kill state remains enabled until explicitly reset. On restart, all old pending
orders are cancelled with `RESTART_RECOVERY`; holdings are reconciled and any required
kill/stop/session exits are requested again from fresh data. Inspect recovery before
resuming experiments.

## 11. Replay your own fixtures

Use a new account TOML with its own database and reviewed fixture calendar. Create
an instrument file such as:

```json
[{"symbol":"NSE:DEMO","token":1,"tick_size":"0.05","lot_size":1}]
```

```sh
trading-agent --config config/replay.toml replay data/demo-first/events.jsonl \
  --instruments config/replay-instruments.json
```

Fixtures are JSONL events with `type` and an aware `time`, in chronological order.
Supported types: `connection` (boolean `connected`), `quote` (validated quote object),
`candidate` (candidate object), `kill`, and `clock`. See the demo's `events.jsonl` for
all required fields. This is execution replay, not a strategy backtest. It uses no
wall-clock time and no network. Preserve the fixture, config, calendar, charge
version, code revision and report for comparison.

## 12. Daily operation and recovery

Use the [full daily checklist](daily-operator-checklist.md) for the current browser
workflow and the long-term/intraday distinction. The flatness instruction below
applies to intraday operation; intentionally retained long-term holdings persist
overnight and must be inspected rather than treated as automatically sold.

Before the session: verify clock synchronization, free disk, reviewed calendar,
private credentials, previous-session flatness, and database verification. Start
the feed and inspect dashboard readiness and freshness. During operation monitor
feed state, journal growth, positions and pending exits. After the session verify
flatness, stop the service, back up and reconcile:

```sh
trading-agent verify-db
trading-agent backup backups/paper-2026-10-20.sqlite3
```

Backup refuses an existing destination and uses SQLite's backup API, not a live
file copy. Rehearse restore and reboot using [runbook.md](runbook.md). Do not delete
the original database to resolve an unexplained discrepancy. `Ctrl-C` shuts down the
service; open paper positions remain durable and are not falsely marked closed.

## 13. Performance and troubleshooting

Run `python scripts/benchmark.py --output benchmark.json` on the deployment machine.
The baseline in [performance.md](performance.md) is a local synthetic measurement.
There is no high-frequency or network-latency guarantee. The indicator path uses
constant work per candle; durable writes stay synchronous. Keep ML training and
large backtests off the feed process. See the runbook for readiness failures,
database ownership, stale data, expired sessions, disk-full faults and service setup.

## 14. Phase 2 strategy research

```sh
trading-agent research-demo --directory data/research-first
trading-agent backtest data/research-first/dataset \
  --strategy config/strategy.toml --output data/research-second
```

Read [backtesting.md](backtesting.md) for rule definitions, data bundles, export,
metrics and limitations. Both commands create independent accounts beneath the
requested output directories. `serve --stream` does not automatically submit these
rules. Completed candles and observed bid/ask quotes are required; candle-only
history is refused instead of being converted into assumed fills.

## 15. Phase 3 offline ML

```sh
trading-agent ml-demo --directory data/ml-first
trading-agent backtest data/ml-first/future-data --model data/ml-first/model \
  --allow-synthetic-model --output data/ml-first-scored-again
```

Read the detailed [ML usage guide](ml-research.md) before using real research data.
The synthetic demo labels sixty candidates, trains/calibrates on separate chronological
blocks, evaluates walk-forward/final holdout periods, and compares rules/scoring on
ten later sessions. It cannot pass the non-synthetic acceptance gate and provides no
market-performance evidence. Every command creates new output paths and leaves the
service account untouched.

For reviewed datasets, use `ml-build`, then `ml-train --training config/ml.toml`,
then `backtest --model` on data starting after validation plus embargo. Preserve the
sample audit, model/validation manifests, hypotheses and failed results. Real research
defaults require at least ninety sessions plus sufficient examples in every block.
Default manual services still reject ML-dependent intents without a model.
Version 0.4.0 additionally supports dedicated supervised accounts as described below.

## 16. Phase 4 supervised paper feed

```sh
trading-agent paper-demo --directory data/paper-first
```

This runs credential-free synthetic partial-fill, disconnect, silent-feed and
unclean-restart drills. It leaves the service account untouched and retains separate
ledgers/evidence reports. Read [paper-feed.md](paper-feed.md) for the detailed connected
setup. Use a new dedicated account config with reviewed tokens/calendar and a private
operator token, then select exactly one policy:

```sh
trading-agent --config config/paper-session.toml paper-init --rule-only
trading-agent --config config/paper-session.toml serve --stream --automate --rule-only
```

Use `--model data/reviewed-model` in both commands instead of `--rule-only` for an
approved non-synthetic model matching the selected economic/strategy policy. The
service starts disarmed and requires authenticated arming after current-session
history and every selected quote are ready. Disconnect/staleness/restart never
automatically rearm. Manual entry intents are disabled on dedicated automated accounts.
Stop the service, then use `paper-report --output NEW_PATH` with the same config for
integrity/reconciliation and source-preserving operational evidence. Real broker,
fill-model and target-device acceptance remain unverified; execution stays virtual.

## 17. Read-only local acceptance diagnostics

```sh
trading-agent --config config/paper.toml preflight --strict
trading-agent --config config/paper.toml preflight --output data/preflight-first
```

This command can inspect a running account without startup recovery or cancelling
pending orders. It checks local runtime, SQLite patch level, disk, permissions,
calendar, integrity/accounting and stored identities. A missing account is reported
without creating it. Use the service's actual environment/config. No broker call,
model approval or runtime arming occurs. `--strict` exits 2 for blocked required
local checks; ordinary diagnostics exit 0 even when checks are blocked. Command or
configuration errors exit 1. A new private output folder contains JSON/Markdown and
a final hash manifest. Read [acceptance.md](acceptance.md) for exact limits, cooperative
query budget, WAL sidecar behavior and actual broker/device acceptance procedures.

## 18. Long-term paper holdings (LT1)

```sh
trading-agent long-term-demo --directory data/long-term-first
trading-agent --config config/long-term-session.toml init-db
trading-agent --config config/long-term-session.toml instruments
trading-agent --config config/long-term-session.toml serve --stream
```

Create the working config from `config/long-term.toml`, reviewing database/calendar/
actual tokens and loading the private environment before the latter commands. The
separate UI defaults to <http://127.0.0.1:8001>. Each horizon has its own virtual seed;
capital is not shared. Follow [long-term.md](long-term.md) for complete setup, current
price-basis reviews, typed entry/exit requests, overnight/restart protection, DP fees,
source-preserving reports and actual acceptance limits. Ordinary closes do not sell
these holdings. Reported corporate actions quarantine the symbol; use the reviewed
offline adjustment workflow below. Daily long-term strategies, SIP/rebalancing and
real settlement remain later work.
Intraday research/automation commands are refused on a long-term config.

## 19. Reviewed corporate actions and cash receipts (LT2)

```sh
trading-agent corporate-actions-demo --directory data/corporate-actions-first
# Stop the owning service before the following source-account operations.
trading-agent --config config/long-term-session.toml long-term-report --output data/before-actions-first
trading-agent --config config/long-term-session.toml apply-corporate-actions --file /absolute/private/path/reviewed-actions.json
trading-agent --config config/long-term-session.toml record-corporate-cash --file /absolute/private/path/reviewed-receipt.json
```

Read [corporate-actions.md](corporate-actions.md) before preparing either financial
input. It provides complete schemas, ratio/date/evidence rules, quarantine hashes,
ordered same-date batches, fractional cost/claim treatment, withholding/net receipts,
idempotent retries, failure/recovery instructions and unsupported cases. An action
batch never supplies spendable dividend cash. A recorded receipt credits only its
existing claim, once. Old symbol quotes are invalidated; restart, review the adjusted
current-session basis and wait for a quote after the application clock. Whole-share
exits remain latched; unresolved fractions keep portfolio valuation stale. Reports
now use schema 2 and disclose income, receivables and fractional claims separately.

The standing documentation requirement is recorded in [AGENTS.md](../AGENTS.md):
every added feature or changed workflow must update this guide and its detailed
component guide as part of the same implementation.

## 20. Daily research and the offline dashboard (LT3a)

```sh
trading-agent daily-research-demo --directory data/daily-research-first
trading-agent daily-analyze /absolute/path/reviewed-daily-bundle \
  --as-of 2026-10-20T16:00:00+05:30 --policy config/daily-research.toml \
  --output data/daily-research-reviewed-first
```

Open the output's `index.html` in a browser. It is a private self-contained research
dashboard, with provenance/as-of clock, summary cards, symbol/status filters,
sorting, reasons, metric explanations and data-quality/empty states. No server,
token, account or network connection is required. JSON/Markdown evidence and a final
hash manifest accompany it. Displayed analytical values round to two decimals;
raw Decimal strings remain in JSON. No order or execution return is produced.

Read [daily-research.md](daily-research.md) for full manifest/JSONL schemas, historical
universe events, raw prices, explicit split/distribution units, availability clocks,
gap handling, policy rules, failed-output recovery and benchmark boundaries. The
gross analytical index assumes same-close reinvestment, excluding costs, tax and
payment delays; it does not represent the LT2 ledger's actual paper cash behavior.
Lot/SIP/rebalance/capital coordination remain later stages. Keep unfavorable research artifacts and never use
the invented demo calendar/prices as actual market evidence.

## 21. Daily quote execution and separate daily ML (LT3b)

```sh
trading-agent daily-execution-demo --directory data/daily-execution-first --with-ml
open data/daily-execution-first/portfolio/index.html
open data/daily-execution-first/model/index.html
```

Use a new directory. This offline example creates three-symbol invented daily and
quote inputs, a portfolio replay, 150 independent outcome labels, chronological
model validation and a later ten-session scored replay. It uses separate private
accounts and requires no login/token or service account changes. Synthetic evidence
does not establish profitability. The browser reports support desktop/mobile
layouts; there is no native app, live refresh or trading control.

For reviewed inputs, use the dedicated long-term policy and matching daily/quote
bundles. Global config precedes the command:

```sh
trading-agent --config config/long-term.toml daily-backtest \
  /absolute/path/daily /absolute/path/execution \
  --strategy config/daily-strategy.toml --output data/daily-portfolio-first
trading-agent --config config/long-term.toml daily-labels \
  /absolute/path/daily /absolute/path/execution \
  --strategy config/daily-strategy.toml --output data/daily-labels-first
trading-agent daily-train data/daily-labels-first \
  --training config/daily-ml.toml --output data/daily-model-first
trading-agent --config config/long-term.toml daily-backtest \
  /absolute/path/later-daily /absolute/path/later-execution \
  --strategy config/daily-strategy.toml --model data/daily-model-first \
  --output data/daily-scored-first
```

Open `index.html` in each output. Start with **What needs attention**, then inspect
trades/decisions, search symbols/reasons and expand financial/model details. Labels
show excluded/censored counts and explicitly do not report portfolio returns.
Validation shows split counts, calibration and held-out checks. Full JSON evidence
accompanies tables capped at 200 display rows. Exact decimal money and IST times
remain clear; incomplete exposure, quotes and claims are never hidden by an invented
final sale. Failed statistical checks block scoring. For invented models only,
`--allow-synthetic-model` allows an explicitly synthetic later replay while retaining
all other checks. The first replay event must follow final validation plus embargo.

Read [daily-execution.md](daily-execution.md) for schemas/event examples, action and
quote consistency, strategy/coverage assumptions, exact fees, independent label
exclusions, feature identities, purge/calibration/holdout, model availability,
failure/recovery and performance. Preserve partial failed outputs; absence of a
finished manifest prevents loading. Correct reviewed inputs and rerun into a new
directory. Daily model validation/training remains offline. Version 0.12.0 can
consume a matching validated real daily model in the separate reviewed
[reviewed strategy profile](trading-desk.md); it does not bypass readiness/risk checks.
LT3c1 now supplies reviewed contributions/SIP. LT3c2 rebalance proposals and LT3c3
aggregate capital coordination remain next.

## 22. Reviewed purchases, holding additions and SIP (LT3c1)

```sh
trading-agent portfolio-demo --directory data/portfolio-first
```

This invented isolated lifecycle confirms two scheduled purchases, adds to a
holding, cancels an unfilled partial-entry remainder on restart and exits six
shares. Four acquisition lots and exact cash/fees remain independently reconcilable.
Read `report.md`/`report.json`; `manifest.json` protects completed source artifacts.
No original service account is opened. Reuse of the directory fails.

On a manual long-term service, open <http://127.0.0.1:8001/portfolio> or follow the
main console's long-term link. Unlock with the same private operator token. Enter a
symbol, maximum cash debit including buy fees and review reference. New holdings
need reviewed stop/target prices; additions keep the existing levels. **Calculate
server preview**, inspect quantity/debit/risk/caps and then explicitly confirm in the
dialog. Previewing reserves no cash; confirming reserves existing virtual cash.
Orders fill only on later usable quotes. A changed/expired preview needs a new
review. Inspect the stable intent ID after any uncertain response before a new purchase.

SIP plans save increasing, explicitly reviewed exchange dates, a cash budget and
new-holding protection percentages. Each due occurrence needs a separate preview
and confirmation. Missed dates never catch up, and no deposit or automatic order is
created. Cancellation stops future occurrences and pending plan buys; acquired
shares retain their safeguards. One confirmed attempt per plan/date remains consumed
even after cancellation, partial fill or restart.

Current aggregate holdings and original acquisition history are shown separately.
Original lots include actual partial fills and buy fees; sales/actions change the
current pooled holding separately. These are not FIFO/tax ownership lots. The UI
shows recent order states, actual cash spent, remaining reservations and original
costs with exact decimal formatting and responsive browser layouts.

The demo writes a separate `preview.sqlite3` and `preview.toml` for UI inspection:
set your private operator token and run
`trading-agent --config data/portfolio-first/preview.toml serve`, then open
<http://127.0.0.1:8003/portfolio>. Its historical invented calendar/feed cannot approve
current entries. The working copy is excluded from frozen source evidence so
recovery cannot overwrite it. Do not serve or modify `paper.sqlite3` in the evidence bundle.

Read [portfolio-contributions.md](portfolio-contributions.md) for all UI steps,
API schemas, plan bounds, cash/risk constraints, idempotency, backup/recovery,
calendar revision and performance. LT3c1 is complete; reviewed rebalancing and
cross-account capital coordination remain separate next milestones.
