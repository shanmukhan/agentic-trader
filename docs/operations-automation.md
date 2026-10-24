# Daily operations automation and findings review

Implemented on 23 October 2026 from the
[checklist review](agentic-trader-checklist-review-and-findings.html). This guide
covers paper-only observation, scheduled acquisition and backup evidence. The
[daily checklist](daily-operator-checklist.md) remains the human operating procedure.

## Review of the findings against the code

The review correctly identifies opportunities to reduce repetitive work. Several
suggested safeguards already existed; they should be reused rather than bypassed.

| Finding | Repository evidence and implemented response |
|---|---|
| Browser polling is not continuous supervision | `api/app.py` already runs a one-second risk watchdog independently of the browser. It cannot observe its own process dying. Added a **separate supervisor process** with authenticated loopback checks and local alerts. |
| Freshness needs multiple checks | Added separate current-IST-date, future-evidence, source/draft hash, eligible-universe, duplicate-candle and per-symbol completed-session coverage checks. Profile check time is now recorded separately. |
| Daily prerequisites need a single report | Added `/api/operations` and `daily-report` with PASS, BLOCKED and NEEDS REVIEW rows, reason codes, observation times, source validation, setup state and current decision authority. Report generation grants no authority. |
| Orders/fills and cash need reconciliation | Existing `Database.reconcile` reconstructs exact cash, fees, holdings, order fills, reservations and desk authorization. Added its independent read-only snapshot to the daily audit, plus bounded lifecycle details and unresolved exits. No new financial arithmetic or retry mechanism replaces that verifier. |
| Repeatable preparation should be scheduled | Added opt-in IST scheduling of one acquisition attempt per reviewed session date. It verifies account identity, Manual state, mappings/held coverage, pending-order/fault gates and broker profile before acquisition. It reuses valid same-day data and stops before installation/reviews/mode activation. |
| Setup failures can partially persist | Existing guided setup already records phases, binds two-minute confirmation to inputs, deduplicates completed confirmation and stops interrupted/failed work for review. Kept those semantics. New scheduling records its intent before potentially ambiguous provider I/O; a repeated or interrupted attempt is reconciled, not blindly replayed. |
| A database file is not the full backup set | Added stopped-owner verified packages with the ledger, exact config, calendar and installed profile/data/source/model references. Added an isolated copy/hash/accounting restore drill. No engine recovery or pending-order cancellation runs. |
| Credentials and authority need human boundaries | Normal broker login/2FA, calendar/source/basis attestations, quarantine resolution, installation, mode activation, Approval trades and manual/SIP confirmations remain explicit. Automated downloads do not perform them. |

This is an implementation of the review's observation, validation, acquisition and
evidence recommendations. Automatic resumption of partially applied setup, remote
notification delivery, encrypted off-device replication, full service relocation and
real broker/device/power-loss acceptance remain separate work. They are not established
by synthetic tests or a successful local report.

## Generate one daily report

Start the intended UI service first. In another terminal at the repository root,
load the same trusted private environment using [the environment instructions](how-to-use.md#4-configure-a-paper-account).
Use the actual account config, not an unrelated default:

```sh
.venv/bin/trading-agent --config config/first-paper-session.toml daily-report \
  --output data/daily-report-YYYY-MM-DD-first
```

Replace the date and use a new output directory for every deliberate run. The command
uses the configured loopback host/port and operator bearer token. It checks that the
responding account ID and economic-policy fingerprint match the selected config.
Redirects and environment proxies are disabled; credentials are never command arguments.

Output is private `report.json`, `report.md` and a last-written SHA-256 `manifest.json`.
The report includes:

- Service/account identity, horizon, observation time, saved reviewed session/hours,
  current decision mode, actual desk blockers and authorization state.
- Dated successful broker profile-check evidence. A check today does not prove the
  token remains valid indefinitely or that streaming/history entitlement exists.
- Mappings/subscriptions for every selected token and retained holding, current-day
  basis-review gaps, usable/rejected/stale quotes, timestamps and stored depth sizes.
- Pending-order count, latest 200 orders with requested/filled/remaining quantity,
  cumulative fees, requested protective exits, pending sells and approval count.
  Full accounting uses the entire ledger; displayed order detail is explicitly bounded.
- Download run/state, exclusions, same-day source coverage and setup phase/recovery state.
- A separate read-only SQLite snapshot verifying integrity and exact accounting against
  persisted journal evidence. Account display and ledger audit can observe different
  moments while the service runs; compare their journal sequences. A report is not an
  atomic freeze of the running account across broker, source and audit reads.

PASS means that specific check passed at its observation time. NEEDS REVIEW requires
the documented operator action or a full audit; BLOCKED reports missing/invalid evidence.
Closed-market quote/entry blockers are expected. A **finished report** means report
publication completed, not that every prerequisite passed or trading is permitted.
`AUTHORIZED` describes an already selected active mode with no desk blockers; reading
it never authorizes a mode or a trade.

Exit 0 means evidence was written, even when checks are blocked. Exit 1 means config,
authentication, connectivity, identity or output publication failed. Inspect output
completion markers rather than treating an exit code as trade permission. Direct
CLI commands do not source `.env` automatically. Restart the owning server once to
load the new Python routes; this does not approve reviews or reconnect the feed.

## Run an independent monitor

For the same launcher-selected account, start a second terminal:

```sh
./scripts/start_operations.sh
```

The wrapper loads the same `.env` and optional session environment as `start_ui.sh`,
chooses the same default first-session config and runs observation only. An explicit
account and one-shot check are also supported:

```sh
./scripts/start_operations.sh config/first-paper-session.toml --once
```

Its default private state folder is `<database stem>.supervisor`. Set
`TRADING_OPERATIONS_OUTPUT` to choose another private directory. The lower-level
equivalent, with the environment already loaded, is:

```sh
.venv/bin/trading-agent --config config/first-paper-session.toml operations-watch \
  --output data/my-account-supervisor --interval 10
```

The interval accepts 5–300 seconds. The monitor runs outside the browser and outside
the account owner. It contacts only the local operations API, with bounded responses
and request timeouts. It alerts for unreachable/wrong/stale service evidence, clock
disagreement, feed/quote/basis problems in an open session, account fault/kill,
unresolved exits, intraday closed-session exposure, paused/unready decisions and failed
or interrupted preparation. After-hours feed/quote staleness alone is not a protection
incident. Intraday residual exposure and intentionally retained long-term holdings
remain distinct.

Files include `latest.json`, `audit.json`, `state.json` and `alert-<timestamp>.json`.
An alert transition is written privately and printed as one credential-free JSON line
on stderr. Recovery writes a transition listing cleared codes. Repeated identical
conditions do not produce repeated alert files. A file lock prevents duplicate owners
of one supervisor folder; a folder is bound to its account and records schedule options.
Do not erase a lock to defeat ownership or delete state to retry an uncertain operation.

Full source/ledger audits run at most once every five minutes, separately from liveness
polling. A daily report is saved on the first observed before-open, open and after-close
phase of a reviewed IST session; an unknown date gets a separate no-session report.
These are **observed snapshots**, not guaranteed exchange-closing valuations. Before-open
evidence cannot suppress the later after-close report. An incomplete folder is retained for
inspection and prevents silent overwrite. Report and alert files require an operator
retention policy; automatic deletion is not provided.

The monitor never changes mode, connects the feed, retries an order, confirms setup,
attests a basis review or invokes kill/flatten. The existing server risk watchdog
continues enforcing trading blocks independently. If the server is dead, the monitor
can record/alert that fact but cannot execute exits. A same-computer monitor cannot
report its own computer losing power or internet to a remote recipient. Local stderr
and files are the configured notification destinations; no email/Slack/SMS is sent.

### Enable scheduled data acquisition explicitly

After reviewing this behavior, use:

```sh
./scripts/start_operations.sh --download-universe nifty100 --after 08:30
```

`--after` is an IST time. Choose `nifty100` or `nifty500`; no policy is inferred.
The service must be running, in Manual, with a valid saved broker session and today's
reviewed session already in its calendar. Unknown calendar dates are not guessed from
weekdays. Before the saved close, the first observation at/after the configured time
can make one acquisition request. If startup is late, it attempts on the next poll
before close; after close or without a saved session, no acquisition runs.

Server checks run before the download: account reconciliation/policy, supported manual
setup, no custom profile override/active installation, catalog and held subscriptions,
no account fault/kill/pending orders, and a broker profile read. Broker login, 2FA and
token exchange remain manual. Valid same-day source/history is reused.

There are two durable records: the supervisor writes intent before HTTP, and the server
records date/universe/request identity in `<database stem>.operations/YYYY-MM-DD.json`
before starting provider work. Directory entries are flushed with the checkpoint.
Repeat server requests return the recorded job outcome. Switching universes on an
already claimed date requires manual review. Explicitly changing monitor options can
enable/disable acquisition but never clears a dated attempt or unknown outcome; it
cannot force another request on that date.

On refusal, timeout, interrupted claim or ambiguous result, the supervisor stops further
automatic acquisition attempts for that IST date and reports a review requirement.
The existing preparation status is read on later polls when its request ID is known.
An unknown outcome remains unknown until inspected. Refresh Strategies/operations
status, fix the cause and use the ordinary explicitly confirmed download control if
a new run is needed; do not delete receipts to force a replay. Existing preparation
workers still stop at the first provider error and never silently switch data sources.

A completed download remains **Ready for review**. Review the official sources,
calendar, exact ranked shortlist, holdings and included/manual basis reviews in
Strategies; explicitly **Confirm and prepare**, inspect remaining readiness and
separately select Approval/Automatic. The scheduler does not install a policy, create
a guided approval record, attest reviews, connect the socket or place orders. The
download limitations in [strategy preparation](strategy-preparation.md) still apply.

## Stopped-account evidence and backup package

After inspecting residual exposure, stop the owning service deliberately. With its
same environment/config, choose a new private destination:

```sh
.venv/bin/trading-agent --config config/first-paper-session.toml operations-backup \
  --output backups/installation-YYYY-MM-DD-first
```

The command takes the account's existing advisory owner lock without constructing
Database/PaperBroker. A running owner is refused. It never initializes an account,
recovers/cancels orders or changes mode. It checks integrity, exact persisted accounting,
horizon, starting cash, charges and economic-policy identity, then captures:

- `ledger.sqlite3`, created with SQLite's backup API including committed WAL state;
- the selected config and referenced reviewed calendar;
- the installed UI strategy run/pointer or explicit `TRADING_ANALYSIS_PROFILE`, including
  its daily dataset, source snapshots and referenced model, when present;
- an explicit `TRADING_PREPARATION_MODEL` directory when configured;
- `evidence.json` with verified ledger totals/identities and a final `manifest.json`
  mapping hashes, artifact roles and original paths to numbered private copies.

The copied ledger is independently reconciled and compared with the stopped source;
referenced files are checked again for concurrent changes. Files are mode 0600,
new directories 0700. Budgets are 256 referenced files, 128 MiB per file/ledger,
512 MiB total and 30 seconds for the cooperative SQLite backup phase. Missing, changed,
symlinked, oversized or corrupt references and existing output destinations fail.
Disk-full or other failure leaves incomplete evidence with **no completion manifest**.
Do not resume from or label that directory a valid backup.

This packages account artifacts, not Python/runtime installation or every research job,
uninstalled run, service configuration or environment file. Broker credentials and
operator environment are excluded; a config containing an `operator_token` field is
refused. Keep secrets in the separate private environment. Models supplied only to a
legacy bound service CLI are not discoverable from its ledger; preserve those service
arguments/strategy/feed-policy/model artifacts separately under its existing runbook.
The package itself is private but **not encrypted**. Encrypted off-device retention
and deployment/runtime configuration remain the operator's responsibility.

## Isolated restore drill

```sh
.venv/bin/trading-agent --config config/first-paper-session.toml operations-restore-drill \
  backups/installation-YYYY-MM-DD-first --output data/restore-drill-YYYY-MM-DD-first
```

The package must belong to the selected original account/config. The drill verifies
the completion manifest, bounded safe member names and every hash before copying to
a new separate directory, then checks the copied ledger's exact accounting, identity,
cash/fees/positions/pending-order evidence. Original absolute paths are never write
targets. Success writes `restore-result.json` last and `references.json` for review.
Corruption, wrong identity/policy, unsafe names, copy failure or existing destinations
fail; incomplete output is retained without a success marker.

This is an isolated **artifact and accounting drill**, not an automatic relocated
service startup. `paths_rebound` and `service_started` remain false. Use the references
mapping to review/rebind config, profile and artifact paths in a separate recovery
installation; the current immutable strategy pointers and data hashes cannot be
silently edited into activation authority. Verify startup and broker renewal there
under the [restore runbook](runbook.md#backup-and-restore-rehearsal). Do not point a
second running server at the original account. Actual reboot/power-loss/storage and
full service restoration on the target hardware remain unverified.

## Optional service-manager deployment

Reviewed templates are supplied in
[`deployment/launchd/com.example.trading-operations.plist`](../deployment/launchd/com.example.trading-operations.plist)
and [`deployment/systemd/trading-operations.service`](../deployment/systemd/trading-operations.service).
They run the monitor separately from the account owner and default to observation.
Adapt absolute paths, user, private environment/account and output folders using the
[existing deployment procedures](runbook.md). Check the macOS plist with `plutil -lint`.
The Linux template expects `/opt/agentic-trader` and the same private environment/config
as its account service. Add acquisition options only after reviewing the behavior above.

Templates were not installed or enabled by this change. Service-manager restart,
physical-device notification visibility and host-failure detection need real deployment
acceptance. A report or local unit test does not establish those results.
