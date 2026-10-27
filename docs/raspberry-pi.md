# Raspberry Pi services and mobile monitoring

**26 October token/startup recovery:** a nonempty operator token shorter than 32
characters prevents startup. The sync command's `--generate` option creates a strong
replacement without printing it, privately backs up/updates local `.env` and sends
only that credential over SSH. It clears systemd's failed-start limit before
restarting changed/inactive Trader; a matching healthy service is left running.
The strong-token requirement and accounting policy remain unchanged. See
[generation, retry and recovery details](public-browser-access.md#operator-token-belongs-to-the-server-hosting-the-page).

## Using the workstation operator token deliberately

The service's initial token is generated independently in `/etc/agentic-trader.env`.
A workstation `.env` token needs [explicit single-value synchronization](public-browser-access.md#operator-token-belongs-to-the-server-hosting-the-page)
to work on this Pi. Normal service deployments continue to preserve the current Pi
credential. This command does not copy Kite credentials or account state.

The workstation deploy command provisions Agentic Trader and the sibling
`portfolio-advisor` project on the existing 64-bit Raspberry Pi. The owner confirmed
that `portfolio-advisor` is the project referred to as portfolio-analyzer.
Source lives in each project; the shared installer lives in `deployment/rpi/` here.

## Deploy and update

From this repository on the workstation (authenticate sudo privately first):

```sh
ssh -t lipi@192.168.1.13 'sudo -v'
bash deployment/rpi/deploy.sh lipi@192.168.1.13 ../portfolio-advisor
```

Requires key-based SSH, noninteractive sudo, Git, the local `.venv/bin/python`
(or `DEPLOY_PYTHON=/absolute/python`), existing RPi Monitor, Python 3.13/venv,
curl and internet package access on the Pi. Only tracked application/config/sample
files are bundled; working-tree edits to tracked files are included. New source modules/assets under Trader’s `src/trading_agent` are included by
explicit source-type allowlist before commit; untracked account/sample files and
untracked Advisor code remain excluded. Review source changes before deployment. The deployment
helpers themselves are included explicitly. SHA-256 manifests record exact deployed
content in addition to base Git revisions. Workstation `.env`, private account
configs and SQLite databases are excluded, even if accidentally tracked.

The installer uses the Pi's Debian-security-patched Python 3.13.5 without replacing
other services' interpreter. Private deployment tooling pins uv 0.13.5. Trader uses
`uv sync --frozen --no-dev --extra broker --extra ml --no-editable` with the distro
interpreter; Advisor installs its `requirements.lock`. Preparation happens before
service downtime. Releases are root-owned under `/opt/PROJECT/releases/RELEASE`;
`/opt/PROJECT/current` selects the installed code. Both are enabled at boot and
restart on failure. Writes are limited to the corresponding `/var/lib/PROJECT`.

| Monitor name / unit | Browser address on Pi | Persistent configuration and state |
| --- | --- | --- |
| `agentic-trader` / `agentic-trader.service` | `127.0.0.1:8010` | `/etc/agentic-trader.env` (root-private operator token); `/var/lib/agentic-trader/config/paper.toml`, `config/sessions.csv`, `data/`, `logs/` |
| `portfolio-advisor` / `portfolio-advisor.service` | `127.0.0.1:8501` | `/var/lib/portfolio-advisor/config/.env`; `/var/lib/portfolio-advisor/data/advisor.sqlite3` |

Fresh Trader state starts with **₹25,000.00 virtual cash**, paper mode and no broker
credentials, reviewed sessions, subscriptions or automatic feed/execution. Fresh
Advisor state starts in **demo mode**, with its shipped sample CSVs; its displayed
portfolio/recommendations are simulated. State/config are preserved on redeploy.
The installer never migrates the workstation's holdings, purchases or credentials.
Advisor's existing SQLite monetary columns remain REAL; deployment does not upgrade
that accounting implementation. Trader retains exact decimal-string accounting.

## Browser access and broker setup

For direct browser access, the optional [shanmukhan.com Investing profile](public-browser-access.md)
adds a home-page tab and HTTPS routes. After publishing it, use
`https://shanmukhan.com/agentic-trader/workspace` and
`https://shanmukhan.com/portfolio-advisor/`. The SSH path below remains a recovery option;
Advisor's local address then includes `/portfolio-advisor/`.


Keep this SSH session open on the workstation:

```sh
ssh -N -L 8010:127.0.0.1:8010 -L 8501:127.0.0.1:8501 lipi@192.168.1.13
```

Open <http://127.0.0.1:8010/workspace> and <http://127.0.0.1:8501>.
The service installer alone adds no Apache/public route or firewall/DNS change;
`publish-web.sh` installs the separately documented HTTPS profile.
An address-in-use error means a local port is occupied; stop the old tunnel or
choose another local port (and use that address). Trader accepts only explicitly
allowed origins; use localhost for this recovery route, not the Pi LAN address.
Advisor’s direct loopback service has no app login; the public proxy adds monitor-password
authentication. SSH provides access control for the recovery tunnel. Mobile service monitoring uses the
existing RPi Monitor connection, independently of browser access.

Retrieve the new Trader operator token privately with `sudo cat
/etc/agentic-trader.env` in an interactive SSH session; do not paste its contents
into chat/logs. Unlock the workspace and follow [broker setup](ui-setup.md): supply
the read-only Kite credentials, exchange a same-day session, import the catalog,
review sessions, select symbols and explicitly connect when ready. `/ready` returning
503 before these prerequisites are satisfied is expected; `/health` must return 200.
Expired sessions require normal manual renewal. No service start/restart arms paper
automation or authorizes live broker orders.

Advisor's existing import/login UI saves to `ADVISOR_ENV_FILE`, configured by its
unit to the private `/var/lib` file. Local development still uses project `.env`.
For CLI renewal, run from `/opt/portfolio-advisor/current` as its service user with
that same `ADVISOR_ENV_FILE`, using `python -m scripts.login`; do not put credentials
in command arguments. Restart Advisor after manual environment edits. Read-only
broker integration does not place orders. Expired/unavailable live sessions may
fall back to cached/demo inputs; review the UI's mode/data status before using output.

## RPi Monitor mobile controls

The installer appends exactly these mappings to the deployed backend's
`ALLOWED_SERVICES_JSON`, preserving existing entries and every other private setting:

```json
{"agentic-trader":"agentic-trader.service","portfolio-advisor":"portfolio-advisor.service"}
```

It validates/regenerates polkit using the **deployed** monitor renderer/template,
then restarts polkit and, only when configuration changed, RPi Monitor. The first
registration briefly interrupts camera/monitor connections. Local unrelated monitor
code edits are not deployed. No wildcard systemctl privilege is added.

Open the mobile app's Services view and refresh/reopen it. The list is server-driven;
no app rebuild is required. Active means the systemd process is running, not that
broker credentials/data/readiness are valid. Current mobile service controls act immediately, without a separate confirmation dialog.
Stop interrupts browser sessions and any connected feed; restart interrupts work and
reopens the same saved state. Inspect outstanding paper orders/holdings before using
these controls. A restart resets feed trust and may require operator setup again;
it does not repeat financial submissions. Use the app's separate confirmed power
controls for reboot/shutdown; deployment does not reboot the host.

## Checks, failures and recovery

```sh
ssh lipi@192.168.1.13 'systemctl is-enabled agentic-trader portfolio-advisor; systemctl is-active agentic-trader portfolio-advisor'
ssh lipi@192.168.1.13 'curl -fsS http://127.0.0.1:8010/health; curl -fsS http://127.0.0.1:8501/portfolio-advisor/_stcore/health'
ssh lipi@192.168.1.13 'sudo journalctl -u agentic-trader -u portfolio-advisor -n 50 --no-pager'
```

Package/download failure occurs before switching running code. Health failure after
the switch restores previous release links/units and prior running/enabled state;
monitor update failure also restores its env/rule. Persistent financial databases
are retained, never automatically rolled back. A first-install failure leaves the
new services stopped with private state retained for diagnosis. Fix the reported
cause and rerun. Repeated crashes hit systemd's five-starts/300-second limit; fix
configuration, then `sudo systemctl reset-failed UNIT; sudo systemctl start UNIT`.

Every attempt records a root-private `/var/backups/trading-services-RELEASE` with
manifest, previous links/units, monitor env/rule and, after services stop, a consistent
`state.tar`. Archives include credentials: keep them private. No automatic backup or
release pruning is installed; monitor disk space. New first-install state is created
after that initial snapshot, so an empty first snapshot does not contain later work.

For manual code rollback, stop the affected service, record a fresh state backup,
point `/opt/PROJECT/current` at a verified earlier release and start it. Restore a
database only after a separately reviewed accounting/integrity recovery; an older
release may not understand a newer schema. For monitor-only rollback restore
`monitor.env`/`monitor.rules` to their original paths with original ownership/modes,
then restart polkit and RPi Monitor. Removing a monitored service also requires
removing its mapping and regenerating the exact polkit allowlist. Do not restore an
old whole allowlist over unrelated later service additions.

## Validation record

Local validation: 28 Trader deployment/CLI/setup/snapshot checks and 42 Advisor
tests passed, including separate-process persistent configuration, token-file
renewal with test values and independent SQLite inspection. Bundle tests verify
secret/state exclusion, source hashes, symlink rejection and monitor conflict handling.
Device installation and checks are recorded below. These checks
do not establish real-market acceptance, profitability, phone interaction or
reboot/power-loss recovery.


### Device evidence — 25 October 2026

Installed release **20261025T151902-a2cbb050bbd8** on `lipi@192.168.1.13`,
64-bit `aarch64` host `rpi`, using the existing Debian 3.13.5 security-patched
interpreter. Backup: `/var/backups/trading-services-20261025T151902-a2cbb050bbd8`.
The first attempt failed on Advisor's old Mac editable path before switching any
service; its portable lockfile correction allowed the next install to complete.

Both units are enabled, active/running, with zero automatic restarts and exit status
zero. `systemd-analyze verify` passed; service journals had no warning/error entries
in the checked deployment period. Listener checks confirmed 8010/8501 bind only
127.0.0.1. Both health endpoints returned 200; Trader `/ready` returned the expected
503 with broker/calendar/subscription setup incomplete. Existing active Apache,
monitor, EllieEats, PostgreSQL and all three Netrava units remained active. Existing
inactive NexaLink/Redis monitor entries were preserved as inactive.

The deployed monitor's own settings/service-list provider returned both new names
as active alongside all eight existing mappings. Starting the already-running units
as `rpimonitor` with `systemctl --no-ask-password` succeeded, exercising the exact
polkit grants without interrupting them. No authentication bypass/JWT was created.

A controlled restart of both app units passed health checks again. Independent
read-only SQLite inspection before/after retained Trader cash **25000.00**, zero
orders/fills/positions, Advisor zero purchases and its one demo report. Both database
integrity checks returned `ok`. Service users could not write their release code.
A Pi-side Streamlit AppTest rendered the Advisor app without exceptions or error
components (13 metrics); existing `use_container_width` deprecation warnings remain.
That harness exercised **demo data**, not a broker session or physical browser/phone.

Phone service-button taps, native mobile acceptance, physical reboot/power-loss and
real-market/Kite acceptance were not performed. The current mobile service buttons
act immediately; review outstanding paper work before Stop/Restart. The generic
legacy streaming unit and independent operations watcher were not installed.


### Subsequent HTTPS profile — 25 October 2026

The current release is `20261025T162335-9e35f56ca62b`; the optional Investing profile
is now published on shanmukhan.com. Its final web backup is
`/var/backups/trading-web-20261025T163321`. Use the [current public browser guide](public-browser-access.md)
for the canonical URLs, Advisor monitor-password prompt, Trader operator token,
prefixed local recovery paths, preserved financial-state checks and acceptance limits.
The initial deployment evidence above remains historical.
