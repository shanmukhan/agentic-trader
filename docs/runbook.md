# Operator runbook

## Start and stop

Use the separate [research guide](backtesting.md) for Phase 2 commands. Backtests and
research demos own independent accounts and can run beside a service if disk/CPU
headroom permits. Export requires the source service stopped to acquire its lock;
it does not run engine recovery or cancel source orders.

Work from the repository root as an unprivileged user. Load your private environment,
review the calendar and instrument tokens, and start `.venv/bin/trading-agent serve`
or `serve --stream`. Only one owner can open an account. Stop with Ctrl-C or the
service manager; allow up to thirty seconds for cleanup. Stopping does not declare
positions closed. Read [how-to-use.md](how-to-use.md) for token exchange and setup.

## Incident response

For research failures inspect `run.json` and the partial isolated ledger; do not
treat the run as a successful experiment. Fix the input and choose a new output
directory. Export folders without `manifest.json` are incomplete. Finished reports
with open exposure, stale valuations or data gaps remain incomplete; retain that
limitation instead of manufacturing a close or editing account rows.

| Symptom | Action and expected safe behavior |
|---|---|
| `/ready` is 503 | Inspect feed, reviewed session date, quote ages and kill. Health 200 alone is not permission for entries. |
| No operator access | Set a ≥32-character token in the service environment, restart, and enter it in the dashboard. |
| Account already owned | Locate the existing service; use its API or stop it. Never delete the lock file to bypass ownership. The OS releases the lock on process exit. |
| Credentials expired / connection retries exhausted | Entries remain blocked; complete normal manual login, update the private session environment and restart. |
| Quote timestamp / mapping failure | Check NTP/time sync and reviewed catalog. Do not relabel an instrument or adjust the clock to make a fixture pass. |
| Data gap / incomplete candle | Reload verified historical data and rewarm research indicators; never mark bad data as good. |
| Daily cutoff / loss streak | Inspect journal and pending exits. Finish flattening. Reset remains blocked until the budget is eligible, usually next flat session. |
| Kill with open positions | Keep monitoring fresh quotes and pending sells; a kill request is not a fill. Do not erase the database to clear the warning. |
| Disk full / SQLite fault | Entries latch off. Stop service, preserve journal/database/WAL, free space or replace storage, verify/restore, then restart and inspect recovery. |
| Accounting reconciliation fails | Keep service stopped. Retain failing artifacts, restore a separately verified backup to a new path, investigate before resuming. |
| Policy hash mismatch | Use a new account for changed risk/simulation policy; keep the original account intact for audit. |
| Next-day position remains | Entries stay killed for overnight exposure. Restore reviewed calendar/feed, let virtual exits fill, inspect and explicitly reset. |

The log is `logs/agent.jsonl`, rotating at 5 MB with three backups. It uses generic
structured errors and redaction. Audit details live in SQLite `events`, not raw broker
exceptions. Use a private database viewer to inspect events; do not publish account
data or credentials with incident reports. Local kill/data-quality journal entries
are the alert mechanism; remote notification delivery is not configured.

## Backup and restore rehearsal

1. Stop the service and confirm there is no owning process. Preserve the original
   database and sidecars before any recovery action.
2. Run `.venv/bin/trading-agent verify-db`. It checks SQLite integrity and reconstructs
   accounting from the ledger. Pending orders are cancelled during engine recovery.
3. Run `.venv/bin/trading-agent backup backups/paper-YYYY-MM-DD.sqlite3` using a new
   filename. The online backup API includes committed WAL contents and verifies the
   destination. Private file permissions are set from creation. Store an encrypted
   off-device copy under your own backup policy.
4. Copy the backup to a **new**, non-existing recovery directory/account path. Create
   a config copy changing only its database path. Preserve the original risk policy.
   Run `trading-agent --config config/recovery.toml verify-db`.
5. Start `serve` without stream first. Inspect cash, costs, positions and kill state.
   Restart with stream only after verified session/catalog/credentials are available.
   Cached quotes stay untrusted until fresh data arrives. Required exits requeue.

Do not copy only the main SQLite file while the original service is writing. Do not
delete WAL/SHM files on an active database. Do not use repair utilities that discard
rows and then continue trading. Tests cover a fault after an in-transaction fill;
deployment still requires actual storage/power-loss rehearsal on the target hardware.

## Raspberry Pi systemd deployment

Use a 64-bit OS, patched Python and the locked broker environment. The supplied unit
assumes `/opt/agentic-trader`, dedicated user/group `trading-agent`, data/log directories
owned by that user, and a root-managed private `/etc/agentic-trader.env` containing
the variables in `.env.example`. Create these with the machine administrator; the
setup script does not create accounts or modify system services automatically.
Create `data` and `logs` before starting: systemd restricts writes to these paths.
Keep the virtual environment and source readable/executable by the service user.

After adapting and reviewing `deployment/systemd/trading-agent.service`, install it
under `/etc/systemd/system/`, run `systemctl daemon-reload`, then
`systemctl enable --now trading-agent`. Check `systemctl status trading-agent` and
`journalctl -u trading-agent`. The template requests streaming, so valid credentials,
tokens and catalog are needed. To run offline, remove `--stream` in your local unit.
Restart after manual session renewal. Test a controlled reboot and verify preserved
paper cash/positions, connectivity reset and durable kill behavior. Do not install
a Python interpreter under `/tmp`; systemd uses `PrivateTmp`.

## macOS launchd deployment

Use a non-admin user and keep the machine awake during sessions. Copy/adapt
`deployment/launchd/com.example.trading-agent.plist`, replacing every absolute path.
Create `logs` first. Validate the edited file with `plutil -lint PATH`. Install it in
your user's `~/Library/LaunchAgents/`, then use
`launchctl bootstrap gui/$(id -u) PATH`. Use `launchctl bootout` to unload before
running account-owning CLI commands. The wrapper explicitly loads private `.env`.
`TRADING_STREAM` defaults to `0`; change to `1` only after read-only setup.

The template restarts abnormal exits with throttling. Test logout/login and a
controlled reboot yourself; this implementation has not enabled a system service or
verified power recovery on your hardware. Keep FileVault/firewall/updates enabled,
use SSH keys for remote access, and avoid public port forwarding. SSH local forwarding
preserves the localhost browser Origin expected by controls.

## Offline model operations

Follow [ml-research.md](ml-research.md) for `ml-build`, `ml-train` and scored backtests.
Use new output directories, preserve settings/data/audit/model/report together, and
keep training jobs outside the feed process. Pi setup installs broker/runtime extras;
the development/training environment additionally needs `ml` and `dev` extras.

If labels are sparse, inspect `manifest.json: counts` and `label_audit.jsonl` censor
reasons. Do not turn excluded/unfilled trades into negative labels. No sample/model
completion manifest means failure; preserve the partial folder and rerun separately.
A fitted model failing diagnostic gates retains validation files but cannot load.
Obtain better reviewed data or a newly predeclared hypothesis; do not edit gate flags.

A context mismatch means the strategy, economic policy or fee version differs;
restore matching reviewed inputs or retrain into a new artifact. A time rejection
means the replay overlaps model fitting/validation/embargo; supply a later dataset.
`--allow-synthetic-model` applies only to invented fixtures and cannot bypass other
gates. A model-version account mismatch requires a new account. Do not erase metadata
or restart a scored account as rule-only to remove its gate.

Phase 4 engineering now supplies opt-in supervised integration. Retained empirical
validation, deployment latency/load and actual outage/recovery drills remain pending.
Models attach only through an explicit dedicated account and configured service.

## Supervised paper service

Follow [paper-feed.md](paper-feed.md) for `paper-init`, opt-in `serve --automate`,
authenticated arming and `paper-report`. Use a new dedicated account, reviewed
tokens/calendar and either an explicit rule-only baseline or an approved non-synthetic
model. Service-manager restarts always remain disarmed. Keep training off this process.

If readiness reports history gaps, wait for the paced current-session backfill;
never mark active/local approximated bars complete. Broker history failures disarm
and retry; late signals are skipped. A changed historical revision or used calendar
date requires review rather than silent replacement. Coordinate shared API request load.

Disconnect/stale quotes cancel pending entries and disarm. Holdings trigger durable
kill exits, which remain unfilled until valid quotes/depth arrive. After recovery,
verify flatness and history, explicitly reset an eligible kill, then arm separately.
Disarm alone preserves protective handling of filled positions. Shutdown cancels
entries and retains unresolved positions; verify actual flatness before stopping.

Dedicated accounts refuse manual broker startup and changed identities. Use the
running authenticated API for status. After stopping, `paper-report` performs
integrity/accounting checks without recovery/cancellation. Preserve partial/failed
folders, source ledger and last telemetry. A crash can lose recent timing samples;
reports cannot certify full-day coverage, real hardware recovery or live readiness.

## Local preflight and browser supervision (0.4.1)

Run `trading-agent --config PATH preflight --strict --output NEW_PRIVATE_DIRECTORY`
with the service's environment to inspect local configuration/account health without
opening recovery or cancelling orders. It may read the running WAL account. Choose
a quiet period because integrity/accounting reads consume I/O and can delay WAL
recycling. Exit 2 identifies blocked required local checks, 1 a command/config/output
failure. Inspect the structured result rather than treating exit 0 without `--strict`
as a readiness approval. Missing accounts are reported, not initialized. Review
pending positions/orders before any later owning command. See
[acceptance.md](acceptance.md) for the five-second cooperative query budget, SQLite
fix branches and target-device procedures.

The responsive browser console is described in [operator-console.md](operator-console.md).
A stale banner means displayed values require refresh; it does not prove the server
stopped. Kill/flatten/disarm remain immediate requests when unlocked; arm/reset ask
for confirmation and require current display state. A timed-out control has an unknown
outcome: inspect state before retry. Lock clears the page/token but does not disarm
an automated service. Phone access needs a separately reviewed private route to the
loopback service; no public listener or mobile tunnel is installed here.

## Long-term account supervision (LT1)

Use its exact long-term config/database and default 8001 listener; intraday and
long-term capital are independent virtual seeds. Regular closes/restarts do not sell
these holdings. Before each session, inspect the prior quote basis and review all
intervening corporate actions for each held/selected symbol. Missing review blocks
raw-price acceptance; a false review persistently quarantines the symbol and retains
unresolved exposure. Do not clear it with a false no-action declaration or edit rows.

Requested holding exits remain latched through pending-order cancellation and restart;
normal polling restores residual exits, which still need usable reviewed quotes.
On `INSUFFICIENT_EXIT_FEE_CASH`, preserve the blocked holding/evidence rather than
manufacturing a sale or replenishment. On drawdown kill, waiting a date does not reset
the high-water loss limit. Preserve the account and review the experiment.

Capture `preflight` and, with ownership stopped, `long-term-report --output NEW_PATH`
before owning recovery/backup commands if pending-order state must be retained in
the report. Owning `verify-db`/`backup` still cancel old pending orders on engine startup;
exit latches survive and are restored on later polling. Restore to a new path with
matching horizon/risk/charges and the pinned reviewed calendar. No real custody or
settlement is inferred from successful SQLite recovery. Full procedures and limits:
[long-term.md](long-term.md).

## LT2 offline corporate-action operations (0.6.0)

1. Before the first affected ex-date quote, quarantine the symbol with an unchecked
   current-session review. Stop the service and preserve a consistent backup.
2. Run `long-term-report --output NEW` without engine recovery. Review the symbol's
   `quarantine_sha256`, complete issuer notices, virtual entitlement, ex/record and
   credit/payment dates, ratios, same-date sequence and net deductions.
3. Follow [corporate-actions.md](corporate-actions.md) to prepare bounded JSON and
   run `apply-corporate-actions --file FILE` with the exact long-term config. Failed
   requests roll back; successful batches cancel only the symbol's pending orders,
   retain exit intent, create claims and invalidate quotes/candles.
4. Restart, review the adjusted current-session basis and require a strictly later
   quote than the application clock. Unsupported actions or accepted ex-date prices
   require preserved evidence/new reviewed account reconstruction, never SQL edits.
5. Stop the service to record each reviewed `record-corporate-cash --file FILE`.
   Paid date must be causal; dividend net must equal its frozen entitlement. A
   receipt ID retry is safe; a second payment ID cannot pay an already paid claim.
6. Report again and independently reconcile cash, received income, receivables,
   unknown fractions and adjusted whole-share capital P&L. Unpaid fractions survive
   liquidation. An unknown fraction value delays portfolio marks/entries; individual
   usable-quote exits continue. No quote is invented to make a report look complete.

Backups include both new financial tables and claim metadata. Restore with 0.6.0 or
later. Missing/mismatched ledger/journal/cache/protective evidence fails startup;
retain failed source/inputs and rebuild a separate corrected paper account. There
is no arbitrary cash correction, reversal or real custody/payment operation. The
commands' generic failure output protects private input; inspect the reviewed JSON,
matching config, calendar, ownership and evidence using the detailed guide.

## LT3a daily research operations (0.7.0)

Use a reviewed manifest/JSONL bundle and an explicit aware `--as-of` clock. Keep
analysis output in a new directory outside the source. No service downtime, account
ownership, operator token or broker access is needed. Open the generated local
`index.html`; retain JSON/Markdown and the final hash manifest together. An absent
finished manifest means incomplete evidence; retain failed outputs and rerun into a
new directory after correcting inputs. Review calendar age/completeness, historical
membership, raw/benefit units, availability and all data-gap/excluded rows. Do not
convert a research rank directly into an order. Input/report references are private;
sharing the report shares those references. See [daily-research.md](daily-research.md).

## LT3b daily offline experiment operations (0.8.0)

Use new output directories and keep complete favorable/unfavorable/failed experiments.
Run `daily-backtest` / `daily-labels` with an explicit long-term config and reviewed
matching daily/quote sources. Training uses only a finished verified independent-label
bundle; daily scoring requires a separate later interval after validation plus embargo.
No command opens the configured account or requires broker credentials. Do not run
training inside a connected feed process or change account economics to bypass model
identity. Individual trial DBs can use substantial storage; monitor available disk.

On failure, preserve partial output; no finished manifest means no loadable evidence.
Review source clocks, actions, coverage and censored audits; rerun a corrected reviewed
experiment into a new directory. Open HTML locally and check full JSON for records
beyond the 200-row display. Do not force-close surviving research exposure to make a
result look complete. Detailed commands/recovery: [daily-execution.md](daily-execution.md).
