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
