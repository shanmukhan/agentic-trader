# How to use Agentic Trader

## 1. Scope and prerequisites

This release implements Phases 1–4 engineering: virtual execution/risk controls,
predeclared rules, isolated backtests, chronological ML research and opt-in
supervised feed automation.
It does not choose an investment universe, produce investment recommendations or
execute live trades. Sample trades are synthetic. Read
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

```sh
trading-agent serve
```

Open <http://127.0.0.1:8000>, enter the operator token, and select **Unlock / refresh**.
The responsive web dashboard shows account cards, readiness reasons, positions,
paper orders and controls. Desktop uses columns; mobile widths stack the panels.
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
