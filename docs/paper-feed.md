# Phase 4: supervised live-feed paper trading

## Audit follow-up: historical retries and health reads

Historical intraday and daily candle reads now retry HTTP **429** and **503** at most
three total attempts. Each attempt retains the shared minimum 400 ms request spacing;
retry waits are one then two seconds. A numeric `Retry-After` can lengthen a wait up to
30 seconds. A larger numeric request stops this attempt for later operator review;
invalid/non-numeric values use the bounded exponential delay. Authentication errors,
redirects, other HTTP failures, malformed successful responses and transport failures
are not retried. Session-token exchange POSTs are never retried. No request range,
token, timestamp or candle availability is changed to obtain a successful response.

Exhaustion returns the existing sanitized unavailable error. Inspect the saved
preparation/download state and session/entitlement, then explicitly retry when ready;
there is no automatic new setup confirmation, install, connection or mode activation.
Mock HTTP transport tests verify request identity, pacing, retry limits and error
redaction. They do not establish broker availability or rate-limit acceptance.

For connection-only monitoring, authenticated `GET /api/feed/status` avoids the
full console snapshot and any database read. See [its precise timestamp and freshness
limits](api-contracts.md#lightweight-feed-observation). Empty `stream_tokens` remains a
valid offline/manual configuration; attempting a feed connection still requires at
least one reviewed selected instrument. Configured tokens must now be positive integer
values: booleans, decimal numbers and numeric strings are rejected at config load.

Manual Broker & Data streams now commit complete decoded quote frames together.
Every accepted quote/audit event and per-quote protection remains; read
[transaction, read-snapshot and failure behavior](quote-persistence.md). The separate
PaperService automated controller keeps its per-quote callback cadence.

Version 0.12.0 optionally routes an explicitly selected bound intraday strategy mode
through the [Trading desk](trading-desk.md): queue per-trade approval or submit eligible
paper entries automatically. It preserves the existing strategy/model/feed fingerprint,
warmup, per-symbol candidate cap and disarm safeguards. A disarmed/unready controller
cannot approve an older proposal. The normal manual-profile desk also supplies a
separate current-quote/prior-daily long-term pipeline. This does not turn broker
catalog access into profitable stock selection; reviewed real inputs remain required.

The 0.11.1 transport fix ignores full packets whose best bid/ask price or quantity
is zero. A real after-hours observation previously caused Quote validation to throw
and disconnect the socket. These packets now produce no executable Quote or callback;
valid packets in the same structurally valid batch remain available. Strict packet
identity/framing and remaining price/timestamp validation are preserved. Heartbeats
and empty books can sustain a connected transport without fresh executable prices.
An empty book immediately invalidates the affected symbol's earlier execution quote.
The controller applies its existing stale-universe/held-position safeguards, including
disarming/cancelling entries and the held-price kill latch. Another valid quote does
not automatically rearm it. Conflicting same-symbol packets in a batch cannot clear
an observed empty book. Manual partial candle builders reset for that symbol.
Existing freshness, session, basis and risk gates remain mandatory. Manual Setup
exposes safe bounded-retry diagnostics; see [UI recovery](ui-setup.md#after-hours-feed-offline-fix-0111).

Version 0.4.0 connects reviewed rule/model candidates to the read-only Kite feed and
the existing **virtual** broker. It adds explicit arming, outage controls, separate
history loading, telemetry and operations reports. No live orders or transfers are
implemented. This delivers Phase 4 engineering; sustained real-feed, broker entitlement,
fill calibration and target-device acceptance remain unverified.

## Whole-second Kite updates

The [official full-packet layout](https://kite.trade/docs/connect/v3/websocket/)
provides an integer exchange timestamp. Observed real packets have whole-second times
with multiple ordered books within a second. The updated broker/candle path accepts a
changed same-time book only when both quotes are Kite, symbol/token match, the exchange
time has no fractional part and receipt time strictly increases. Tick/depth, cumulative
volume, clock/freshness, basis and financial checks remain mandatory. Non-Kite/replay
input retains strictly increasing exchange times; older exchange times and ambiguous
receipt ties are rejected. No timestamp is fabricated or advanced to force acceptance.

An unchanged repeat at the same exchange time ignores receipt-time differences and
does nothing: no quote/receipt renewal, candles, fills or fault clearing. A changed tied
book can update quotes/marks, latch protection and add only actual cumulative-volume
deltas to candles. It does not call fill processing for that timestamp again. A later
strictly newer exchange timestamp is needed for another depth budget, in addition to
the existing order-creation/latency requirements. Zero-depth observations still
invalidate the symbol; malformed packets and backward/volume-regressing inputs retain
their fail-closed behavior.

Load the fix by stopping the owning terminal, running `./scripts/start_ui.sh` and
unlocking again; reopening an already running process does not load new Python code.
Review actual readiness and explicitly reconnect/choose the desired mode. Cancelled
daily proposals are retained and are not automatically replayed by a restart/mode switch.

Validation is split: synthetic raw-packet callback tests, exact persisted monetary
checks and the full suite verify deterministic behavior. An independent eight-second
real-feed probe into an isolated disposable engine accepted 68 quotes, including 20
changed same-second books, with no quality failures, runtime fault or orders. It was
not connected to the operator account's callbacks and is not sustained/device/fill
acceptance. No operating mode or historical proposal was changed by that probe.

## Run the offline fault drills

From the repository root using the prepared Python 3.13.16 environment:

```sh
.venv/bin/trading-agent paper-demo --directory data/paper-first
```

Use a new directory each time. No broker credentials or network are used. Each
scenario has its own ₹25,000 account, SQLite journal and `evidence/report.md`:

| Scenario | Verified behavior | Final virtual cash |
|---|---|---:|
| `partial_fills` | Two partial buys, residual cancellation at target, partial sells and exact net fees | ₹25,023.24 |
| `disconnect` | Holdings remain open while disconnected; queued exit fills on resumed fresh data; kill persists | ₹24,959.48 |
| `silence` | Watchdog detects stale quotes even with a connected socket; no invented close | ₹24,959.48 |
| `restart` | Unclean pending-entry restart cancels the old intent, restores cash reservation and starts disarmed | ₹25,000.00 |

`summary.json` and `summary.md` index the results. All data is invented. The reports
correctly fail non-synthetic/sample/model gates; the crash scenario fails clean shutdown.
These are software drills, not evidence of market performance or actual power-loss recovery.

## Prepare a dedicated connected paper account

Complete the manual authentication, private token, reviewed session CSV and broker
entitlement steps in [how-to-use.md](how-to-use.md). Keep `TRADING_MODE=paper`.
The [first-session checklist](first-paper-session.md) covers developer registration,
daily token capture and a manual order lifecycle before opting into automation.
Do not paste credentials into command arguments. The normal environment setup remains:

```sh
uv sync --frozen --extra broker
source .venv/bin/activate
set -a
source .env
set +a
cp config/paper.toml config/paper-session.toml
```

Edit `config/paper-session.toml` before initialization:

- Choose a **new** `database` path, for example `data/paper-session.sqlite3`.
- Set `stream_tokens` to current, reviewed NSE cash-equity tokens, within the explicit
  `stream_limit` (default 10). Tokens
  must match the broker's equity catalog; no guessed symbol mapping is accepted.
- Point `calendar` at your reviewed date/open/close/source CSV. Unknown dates remain closed.
- Preserve the intended economic limits and simulator assumptions. A model must match
  the same strategy, risk-policy and fee identities used in its training artifact.
- Set a private `TRADING_OPERATOR_TOKEN` of at least 32 characters in the environment.

Use `paper-init` instead of initializing this account with manual `init-db` or
`instruments`. It authenticates a read-only profile/catalog, checks the selected
tokens, creates a private database exclusively and binds the chosen automation/model
identity before any entry can occur. Existing database paths are refused. A partially
failed initialization is retained; investigate it and choose a new account path.

For an explicit **rule-only paper baseline**:

```sh
trading-agent --config config/paper-session.toml paper-init --rule-only
trading-agent --config config/paper-session.toml serve --stream --automate --rule-only
```

For a reviewed, approved **non-synthetic** model from [ml-research.md](ml-research.md):

```sh
trading-agent --config config/paper-session.toml paper-init \
  --model data/reviewed-model --strategy config/strategy.toml
trading-agent --config config/paper-session.toml serve --stream --automate \
  --model data/reviewed-model --strategy config/strategy.toml
```

Select exactly one of `--rule-only` and `--model`. There is no connected-feed
synthetic-model override. The model must pass its existing integrity/validation
gates and become available before a decision. Its validation age is limited to
thirty days by default. Expiry blocks arming/new decisions; it never changes an
existing protective stop or removes an open position.

`serve --stream` without `--automate` retains manual paper execution. Dedicated
automated accounts cannot restart in manual mode or change automation/model identity.
Use a new account for strategy, model, universe, feed policy or simulation changes.
Economic limits remain independent. Manual entry intents receive HTTP 409 on an
automated service; protective kill/flatten/cancel/reset controls remain available.

### Explicit stream capacity

`stream_limit` in the account TOML accepts an integer from 1 to 3,000. Existing
configurations default to 10. For example, set `stream_limit = 50` and supply fifty
reviewed tokens in `stream_tokens` before creating a new account with `paper-init`.
Then run the normal `serve --stream` command above. Existing dedicated accounts
still bind the selected universe; use a new account to change that universe.
Increasing capacity alone does not change cash, sizing, order limits or the
economic-policy fingerprint. Setup's symbol selection uses the same configured
capacity. The desk's ranked execution shortlist remains a separate ten-stock review.
Setup shows that capacity in its saved count, guidance and accessible symbol label,
and allows longer input for the configured selection. Only the symbol-selection
request receives the proportional bounded JSON allowance (at most 128 KiB);
credential/session mutations retain their 8 KiB ceiling. Over-capacity or oversized
selections fail without changing the saved configuration or financial ledger.

The read-only transport subscribes in batches of at most 500 and requests full
184-byte equity packets for every selected token. The configured frame ceiling
scales with capacity, including frames larger than the former 64 KiB limit.
Binary decoding supports up to 3,000 packets and still rejects truncated frames,
unknown/non-equity tokens, invalid packet sizes and trailing bytes before invoking
any executable quote callback. Duplicate catalog token/symbol identities are refused.
An oversized/malformed frame follows the existing bounded retry/disconnect path;
review diagnostics and configuration, reconnect explicitly and reassess readiness.
LTP-only observations cannot supply executable depth and remain unsupported.

The ceiling follows the [official Kite WebSocket contract](https://kite.trade/docs/connect/v3/websocket/).
It is a protocol allowance, not measured local processing capacity. History reads
remain sequential and rate-limited; large universes can miss the unchanged freshness
checks and remain disarmed. Measure the intended workload and reduce the selected
universe when history or quotes are stale. No 3,000-stock throughput, real-feed or
target-device acceptance is claimed. Synthetic tests cover 3,000-packet decoding,
501-token subscription/frame handling and a persisted fifty-symbol paper lifecycle.

## Arm and supervise

Open <http://127.0.0.1:8000> and unlock with the operator token. The service always
starts **disarmed**, including after clean restarts. The automation panel shows
readiness reasons, last completed candles, counters, timings, model identity and risk.

Before “Arm paper automation” can succeed, all selected symbols need fresh quotes
and good contiguous current-session five-minute history from the reviewed open to
the latest completed boundary. Default indicator warmup is fourteen bars, so the
earliest full history is normally available after 10:25 IST for a 09:15 session.
Arming also requires an open entry window, valid model age/availability if selected,
and no kill/fault. HTTP 409 explains a failed arm. A health 200 is not entry readiness.
`/ready` stays 503 while disarmed or blocked.

Backfilled observations warm features while entries are disabled. They never replay
missed signals. If a signal was consumed while disarmed, arming does not revive it;
only later eligible completed candles can produce new candidates. The rule's durable
per-symbol/day proposal cap survives history reload and restart, including rejected
proposals. A subsequent operator reset never rearms automation.

Disarm cancels pending buys and leaves filled holdings under the existing stop,
target, session and kill logic. It does not liquidate them. Use “Queue flatten” or
“Activate kill switch” to request liquidation, then verify actual later fills and
flatness. A queued exit is not cash or a completed close.

Arming expires at entry cutoff or a changed session date. Disconnect, missing/stale
universe quotes, quote-quality failures and history failures disarm entries and
cancel pending buys. Disconnects/stale held-position quotes activate the durable
kill and queue exits. Fresh quotes and observed depth are still required to fill;
reconnect never automatically rearms or resets the kill. Review, flatten, explicitly
reset when eligible, reload history, and arm again.

## Data flow and request pacing

The quote callback only validates/ingests quotes, advances paper fills and records
bounded telemetry. It performs no history HTTP request or model training. A separate
worker fetches completed current-session candles once per new five-minute boundary,
with a five-second retry cadence on failure. Responses must cover every required
bar of every selected symbol. A reconnect invalidates any in-flight old response.

History requests are sequential and spaced by at least 400 ms by default, below the
documented three historical requests per second. Other applications sharing the
same broker credentials must coordinate their own load. See the official
[rate limits](https://kite.trade/docs/connect/v3/exceptions/).

Signals use completed historical candles, not locally approximated stream bars.
Kite defines historical OHLCV and full-mode quote timestamps/day volume in its
[historical](https://kite.trade/docs/connect/v3/historical/) and
[WebSocket](https://kite.trade/docs/connect/v3/websocket/) contracts. A socket heartbeat
does not make an old instrument quote fresh. Stream snapshots do not reconstruct
every exchange trade, so the Phase 1 candle builder is not used as authoritative
automated signal history.

All candidates in one completed history response share its observed completion time
and are ranked together before independent risk admission. Quotes continue processing
while history waits on the network. Default five-second candle-age/quote checks still
apply; slow history or a large universe can make a signal too old, in which case it
is skipped. Reduce the reviewed universe or improve measured data delivery rather
than widening limits to make stale signals pass. No HTTP timing promise is assumed.

History revisions, future/bad candles, token/source mismatch, clock regression and
persistence errors fail closed. Some require a verified restart or a new reviewed
account. Used session boundaries/source references are pinned per date; adding future
reviewed dates is supported, while changing a previously used date is rejected.

## Configure operations limits

Both `paper-init` and `serve` accept `--feed-policy config/paper-feed.toml`:

| Setting | Default | Meaning |
|---|---:|---|
| `history_retry_seconds` | 5 | Minimum failed/new refresh retry interval |
| `history_spacing_ms` | 400 | Minimum monotonic spacing between history request starts |
| `telemetry_seconds` | 60 | Journal cadence for status and bounded timing summaries |
| `processing_budget_ms` | 50 | Provisional local processing evidence budget |
| `max_model_age_days` | 30 | Maximum elapsed time since model validation |
| `evidence_min_sessions` | 20 | Minimum distinct armed dates, never proof of full-day coverage |
| `evidence_min_trades` | 30 | Minimum completed trades for preliminary evidence |

These settings do not change cash, leverage, stops or sizing. Minimum sample settings
cannot be reduced below the shipped floors. Configuration is hashed into the dedicated
account identity. Do not edit stored fingerprints to bypass a mismatch.

## Retain operational evidence

After stopping the service to release its database lock:

```sh
trading-agent --config config/paper-session.toml paper-report \
  --output data/paper-evidence-001
```

This opens storage directly, checks integrity and reconciles accounting without
constructing a broker, cancelling pending orders or running startup recovery.
It writes `report.md`, `report.json`, `trades.jsonl` and a final `run.json` marker.
Repeated runs require new output directories. A directory without the completion
marker is incomplete. Preserve the original account/WAL and incident evidence.

Reports include net fill-ledger statistics, open positions/orders, current cash/fees,
per-run observed drawdown, quote origins, armed dates, incidents, clean-stop evidence,
configuration/code/journal identities and retained latency windows. Preliminary
gates require non-synthetic Kite-origin observations, twenty armed dates, thirty
completed trades, a bound model, flatness, clean run endings, no recorded incidents
or stale observed valuations, positive realized P&L and sufficient timing evidence.
Latency gates check retained p99 windows and the cumulative fraction above budget.
Passing these diagnostics does not certify market performance or deployment.

Timing stages cover quote processing, feed callback/lock wait, receipt-to-callback
delay, candle processing and separate history fetch time. Every stage keeps only its
latest 512 observations for percentiles, plus cumulative count, maximum and budget
exceedances. Reports do not invent global quantiles from those windows. Telemetry
is periodic; a crash can lose recent measurement samples. Observed drawdown resets
per process run and is not a complete cross-restart equity path.

`external_acceptance_verified` and `ready_for_live` remain false. Armed dates do not
prove full-session coverage. Before claiming Phase 4 empirical acceptance, retain
actual feed periods across market conditions, validate price/depth/fee assumptions,
review rejected/censored data and gaps, exercise outages/reboots/backup restoration
on the target device, and measure the full workload with the intended universe.
Future live infrastructure is a separate, explicitly authorized milestone.

## Service managers and tests

Existing deployment templates remain manual by default. For a reviewed dedicated
paper service, replace its command with the exact `serve --stream --automate ...`
invocation above and set `TRADING_CONFIG` to the dedicated account config. On macOS,
either adapt `scripts/run_service.sh` locally or put the explicit arguments in the
launchd plist. Keep credentials in the existing private environment mechanism. A
service-manager restart still requires authenticated manual arming after readiness.
No service was installed or enabled by this implementation.

```sh
pytest tests/paper tests/functional/test_paper_feed.py
python scripts/benchmark_paper.py --samples 2000 --output benchmark.json
```

The [populated Mac benchmark](performance.md#phase-4-populated-paper-pipeline) includes
partial fills, a held position, risk/accounting and periodic durable telemetry.
It excludes network, parsing, callback contention and actual Pi behavior.

## Export captured data for later research

After stopping the dedicated service, `export-research` with the same account config
preserves its recorded connection changes and **first observed candle availability**.
Backfilled bars keep their receipt time; they are not treated as known at close.
Candles sort by availability with chronological bar order within ties. Missing
observation records fail the export. External `--candles` overrides are refused on
automated accounts because those records lack the captured receipt clocks.
The exporter preserves source orders and journal. Legacy manual-source exports
retain their explicitly documented close-time assumption. See [backtesting.md](backtesting.md).

## Local readiness and responsive supervision (0.4.1)

Before target-device acceptance, use `preflight --strict --output NEW_PATH` with the
actual service config/environment. It preserves pending account work and can inspect
a running WAL snapshot. This checks local preparation only; it neither proves broker
entitlement/current feed readiness nor matches/approves a supplied model or full
controller configuration. Startup and arming still enforce those boundaries. Read
[acceptance.md](acceptance.md) for the exact checks and external evidence procedure.

The [responsive console](operator-console.md) now shows account cards, blocked-entry
reasons, positions, the latest 200 orders, and arm/reset confirmation dialogs. Display
staleness is independent of server feed freshness. Locking the page does not disarm
the feed. Kill/flatten/disarm remain immediate server requests, and queued exits still
need actual subsequent virtual fills. Desktop visual acceptance is recorded locally;
mobile visual/physical-device acceptance remains pending.

## Long-term service boundary (0.5.0)

This automatic feed controller remains intraday-only. Long-term uses a separate
`investment_horizon = "long_term"` account with manual operator hypotheses and ordinary
`serve --stream`, default port 8001. Passing `--automate`/intraday models is refused.
Its normal overnight disconnect/closure preserves holdings rather than forcing the
intraday exit policy. Long-term reviews, protective exits, delivery fees and current
limits are specified in [long-term.md](long-term.md); no automatic investment strategy
or actual settlement is claimed.
