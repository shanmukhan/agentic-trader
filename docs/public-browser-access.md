# Browser access on shanmukhan.com

## NSE reference suggestion — 27 October 2026

The step-5 reference now defaults to the official NSE holidays/notices URL. It stays
editable, preserves edits/clearing across refresh, and resets to the suggestion after
Lock/unlock. Review remains explicit and unchecked by default. Local validation passed
234 UI and 33 focused functional checks, including independent exact-account state.
Public `/agentic-trader/setup` and `/agentic-trader/setup.js` checks passed. Trader
kept PID **26035**; independent financial state stayed unchanged. Private rollback:
`/var/backups/trader-ui-nse-reference-default-20261027T152406Z`. Patch evidence is
recorded separately in the current release's `deployment-ui-patches.json`; the
installed assets and source copies match the recorded updated hashes. Future full
source deployments include this default normally.
Published at **20:54:06 IST on 27 October 2026** as a two-asset update with
before/after hashes, private rollback copies and separate patch metadata. The service
was not restarted and no account/calendar files were written. The original release manifest remains a record of its base
bundle. Existing browser tabs need reload to load updated JavaScript. Real-date
review, broker and physical-device acceptance remain separate.

The existing home page gains an **Investing** navigation tab linking two tools:

| Tool | Address | Sign-in |
| --- | --- | --- |
| Agentic Trader | `https://shanmukhan.com/agentic-trader/workspace` | Existing `TRADING_OPERATOR_TOKEN` |
| Portfolio Advisor | `https://shanmukhan.com/portfolio-advisor/` | Existing RPi Monitor username/password, via the browser's HTTPS login prompt |

Open <https://shanmukhan.com/#investing> on a computer or phone and choose a tool.
No SSH tunnel is needed for those URLs. Services start automatically on the Pi;
opening a page loads the app. The existing site products and `/monitor/` routes
remain in the same shared HTTPS virtual host. No DNS/certificate/router changes
or public application port listeners are needed.

Trader's shell remains locked until you supply the operator token. Do not enter a
Kite token or the monitor password there. Retrieve the operator token privately from
`/etc/agentic-trader.env` if necessary. Follow [broker setup](ui-setup.md), including
reviewed sessions, selected instruments and an explicit feed connection. The Kite
redirect for this profile is `https://shanmukhan.com/agentic-trader/`; register it
with the broker. Paper mode and existing financial policy/identity remain unchanged.
Readiness can return 503 while broker/calendar/feed requirements are incomplete.

Advisor has no built-in application login, so Apache authenticates its entire route,
including assets and WebSocket upgrades. Use your existing monitor credentials in
the browser prompt, then check the dashboard's demo/live and data freshness status.
The public route does not connect a broker, migrate workstation accounts or place
orders. Basic authentication is cached by browsers; use a private window and close
that window to end the browser's cached sign-in. This is independent of the mobile
monitor's token/session login.

## Operator token belongs to the server hosting the page

A workstation `.env` and the Pi's `/etc/agentic-trader.env` are separate private
configuration files. First installation generates an independent Pi operator token;
normal deployments preserve it and do not copy workstation credentials. A token
from one server can therefore return 401 on another. The workspace now identifies
its server-specific token and explains both sources. Paste only the value, without
quotes, `TRADING_OPERATOR_TOKEN=` or a `Bearer` prefix. Kite tokens and monitor
passwords are separate credentials.

To explicitly make the Pi accept the operator token in this project's local `.env`:

```sh
ssh -t lipi@192.168.1.13 'sudo -v'
.venv/bin/python deployment/rpi/sync_operator_token.py lipi@192.168.1.13
```

If the local token is too short or you want a fresh strong token, generate and sync
without printing the credential:

```sh
.venv/bin/python deployment/rpi/sync_operator_token.py lipi@192.168.1.13 --generate
```

This generates a random 43-character token using `secrets.token_urlsafe(32)`, backs
up the full local `.env` privately under `backups/operator-token-*`, updates only its
operator-token assignment with mode 0600, then performs the Pi sync. Read the new
value from your private `.env` and reload/unlock the browser. Do not substitute a
short password. The application requires at least 32 characters; the helper accepts
only the documented URL-safe characters. `--generate` rotates the token on every
invocation. After an SSH/sudo/verification failure, retain that generated local value
and retry the ordinary command **without** `--generate`; the local backup is retained
and no automatic rollback of an uncertain remote update is performed. Broker secrets
in the local backup remain local and are not sent to the Pi.

The command reads exactly one literal URL-safe token (32–1024 letters, digits,
underscores or hyphens; optional quotes/export/comments are accepted). It does not
source or execute `.env`, expand variables, or copy broker/account configuration.
Only that value travels over SSH stdin, never command arguments or output. It
backs up the existing Pi env under root-private `/var/backups/trading-operator-token-*`,
atomically replaces the token with mode 0600 and the original owner, clears the
failed-start limit and restarts Trader when the file changes or the service is not
active, then checks an authenticated public workspace read.
Reload and unlock browser tabs with the synchronized value; the previous Pi token
is no longer valid. The usual restart/feed recovery requirements still apply.

An invalid/missing/duplicate **new workstation** token or symlink target fails
before replacement. The Pi file must contain exactly one token assignment. Its
existing value may be short, empty, contain punctuation or have broken quoting;
a valid incoming value now repairs it while preserving its exact previous bytes
in the private backup. Missing/duplicate Pi assignments remain blocked for manual
review. A backup of an invalid old credential is evidence for review, not a guarantee
that restoring it will produce a working login. A
matching file on a healthy service is a no-op with authentication verification. An
inactive/failed service is restarted even when the file already matches. If verification fails
after replacement, inspect the service and the private backup before retrying; the
command does not automatically restore credentials or financial databases. If the
file was already updated manually while the process kept an older token, restart
`agentic-trader` explicitly, then rerun verification. Restore a reviewed backup of
`/etc/agentic-trader.env` and restart Trader to revert a token change, retaining later
unrelated configuration edits. Never paste token values into chat or logs.

## Deploy or update the public profile

Prepare the updated app source, run tests, then authenticate sudo privately:

```sh
ssh -t lipi@192.168.1.13 'sudo -v'
bash deployment/rpi/deploy.sh lipi@192.168.1.13 ../portfolio-advisor
bash deployment/rpi/publish-web.sh lipi@192.168.1.13 ../rpi-setup
```

The source of the landing page, Apache include, authenticator and web installer is
`rpi-setup/scripts/`; `publish-web.sh` copies exactly those reviewed artifacts. It
preserves the existing virtual host, adding one HTTPS-only include, takes a private
backup, validates Apache, restarts only the two applications for the profile and
gracefully reloads Apache. The normal app installer preserves the public profile
and uses Advisor's prefixed health endpoint when the public drop-in is installed.

The first web publish installs distro packages `libapache2-mod-authnz-external`
and `python3-argon2`, enables the required Apache modules, and writes:

- `/etc/apache2/snippets/trading-apps.conf`: only the two app routes.
- `/usr/local/libexec/trading-web-auth`: bounded pipe-based password verification.
- `/etc/apache2/trading-web-auth.json`: root-owned, `www-data`-readable (0640)
  **username/Argon2 hash snapshot only**, no plaintext password or monitor JWT secret.
- `/etc/systemd/system/portfolio-advisor.service.d/public-web.conf`: Streamlit base
  path, canonical browser domain/443 and explicit HTTPS origin/hostname allowlists.
- `/etc/agentic-trader.env`: `TRADING_PUBLIC_ORIGIN=https://shanmukhan.com` and
  `TRADING_PUBLIC_PATH=/agentic-trader`, preserving the existing operator token.

Re-run **publish-web.sh** after changing the monitor username/password to refresh its
minimal identity snapshot; changing the monitor hash alone does not revoke an old
snapshot. The authenticator never reads the full monitor env at request time and
never logs credentials. Apache removes the Basic Authorization header before
proxying to Advisor. Trader keeps its own Bearer header and operator authority.
App request paths are excluded from the existing access log, because broker redirect
queries can contain request tokens. Existing local journals should still be kept private.

## Application and proxy boundaries

Trader accepts one explicitly configured HTTPS host and origin, in addition to
existing loopback operation. Empty settings retain local behavior. Prefix validation
rejects nested/traversal/ambiguous prefixes and origin validation rejects wildcards,
user info, ports, paths, query strings, fragments and control-character normalization.
These deployment fields are excluded from economic-policy fingerprints.

The ASGI middleware strips only the exact configured prefix before routing. Bundled
HTML/JS/CSS URL literals for known routes/assets are adapted to the prefix, including
iframe message dictionaries and the broker callback. API payloads, user input,
financial records and unknown/suffix-only strings are never rewritten. Root health
and authenticated APIs remain available over loopback. Uvicorn trusts forwarded
scheme/address headers only from loopback and only in the explicit public profile;
Apache overwrites those headers. Wrong Host is rejected; financial POSTs still need
the operator Bearer token and an allowed Origin. No general CORS grant is added.

Advisor's Streamlit base path remains intact through Apache, including WebSocket
upgrades; CORS and XSRF stay enabled. Its database/credentials stay in the private
`/var/lib/portfolio-advisor` tree. Existing REAL monetary storage remains unchanged.

## Failure and recovery

- **Advisor login prompt repeats / 401:** check monitor username/password and refresh
  the snapshot after credential changes. No financial action occurs on failed login.
- **Trader access rejected:** use the operator token, canonical HTTPS URL and matching
  public-origin settings. Other origins remain denied. Old Kite redirects to `/`
  need updating to the prefixed callback.
- **Advisor WebSocket 403 after configuration edits:** Streamlit's multiple-value
  environment options use whitespace-separated values, not JSON array strings.
  Keep the tested drop-in format and retain CORS/XSRF protections.
- **502/503 or disconnected dashboard:** inspect the appropriate service in RPi Monitor,
  refresh after recovery, and review data freshness. A running process is separate
  from broker readiness. Existing Stop/Restart controls act immediately.
- **Web publish fails:** prior vhost/home/env/drop-in/helper/identity files are restored;
  applications restart and Apache reloads the validated old configuration. Account
  databases are never restored automatically. Newly installed distro packages may remain.

Private rollback files and source hashes live under `/var/backups/trading-web-TIMESTAMP`.
For manual rollback, restore those specific files with original modes/owners and
remove files absent before this publish, then daemon-reload, restart both apps,
validate/reload Apache. Preserve unrelated changes made since the backup. Removing
the public profile restores the original SSH-only browser-access workflow.

The shared domain is one browser origin: its scripts can affect that origin's other
pages. These are trusted owner-hosted applications; no untrusted plugins/uploads
are published as executable content by this profile. Separate app origins remain
an option for a later isolation change.

## Validation

Local validation includes the full Python suite, Node UI checks, a prefixed controller
test for API/iframe paths and credential handoff, all bundled-script syntax checks,
wrong-host/origin/token tests, independent SQLite/Decimal accounting, unchanged
economic fingerprints, auth failure cases and landing-page accessibility/navigation
contracts. Public HTTPS/config/WebSocket and state checks are recorded below. Synthetic authentication/UI evidence is distinct from real credential,
broker, handset, power-loss or profitability acceptance.

Implementation references: [Apache WebSocket proxying](https://httpd.apache.org/docs/2.4/mod/mod_proxy_wstunnel.html),
[Streamlit base path/origin configuration](https://docs.streamlit.io/develop/api-reference/configuration/config.toml),
and [Apache external authenticator pipe protocol](https://github.com/phokz/mod-auth-external/blob/master/mod_authnz_external/INSTALL).


### Executed device/public checks — 25 October 2026

- Installed current application release `20261025T162335-9e35f56ca62b`. Its private
  stopped-service backup is `/var/backups/trading-services-20261025T162335-9e35f56ca62b`.
- Published the final web profile with rollback backup
  `/var/backups/trading-web-20261025T163321` (**22:03:21 IST**). The initial pre-web
  configuration remains in `/var/backups/trading-web-20261025T162410`; intermediate
  snapshots record the tested allowlist-format correction.
- Public HTTPS home and all checked Trader shell/assets/setup routes returned 200.
  The new Investing links and prior SparkCards/EllieEats links were present. The
  deployed operator token allowed a private workspace read; a wrong-origin financial
  POST returned 403 before any mutation. Advisor pages, health and socket paths
  returned the expected unauthenticated 401/browser login challenge.
- The first isolated WebSocket probe found JSON-style list values were being treated
  as literal strings by Streamlit's Click environment parsing. The final drop-in uses
  whitespace-separated repeated-value settings, with a regression test; CORS/XSRF
  were never disabled to work around this failure.
- Native Argon2 verification and an isolated **loopback-only Apache** instance using
  the deployed proxy/auth helper with a disposable synthetic identity passed positive
  and negative auth, Advisor HTML/health, and an authenticated Streamlit WebSocket
  upgrade. The test instance was stopped and removed; no test identity or alternative
  login was installed on the public vhost. The owner's real password was not entered.
- The minimal production identity snapshot exactly matched the current monitor
  username/hash. A non-secret request-token-shaped probe confirmed private app query
  strings were absent from the existing access log. Apache configuration and systemd
  unit verification passed. Apache, both apps, RPi Monitor, EllieEats, PostgreSQL and
  the Netrava backend were active; `/monitor/health` remained 200. A separate final
  audit found Netrava identity failed and relay inactive, with recorded stops at
  **21:21:11/12 IST**, before this profile's first **21:54** publish. Identity logs
  show the existing realm/import filename mismatch. Neither unit was changed or
  started by this publishing workflow; their independent recovery remains separate.
- Independent read-only SQLite integrity checks passed. Hashes of Trader orders,
  fills, positions and monetary metadata, and Advisor purchases/holdings/reports,
  matched their pre-publish values exactly after app updates, profile restarts and
  WebSocket probes. No broker order or accepted financial-control mutation was used.
- Local validation passed **1,364 Python tests, 233 Node UI tests and six
  infrastructure/auth/navigation/environment checks**, plus Ruff, formatting, mypy,
  secret-pattern, template-render, shell and whitespace checks. New UI checks cover
  prefixed API/iframe navigation, same-origin credential handoff and the landing tab's
  semantic links, visible mobile entry, keyboard focus and responsive style contracts.

Rendered physical-browser/narrow-screen inspection, real-owner browser sign-in,
phone taps, broker/session acceptance and reboot/power-loss qualification were not
performed. The isolated authentication/WebSocket evidence is synthetic and is not
represented as a real-owner or trading-acceptance result.


### Operator-token correction — 25 October 2026

The workstation `.env` token initially returned 401; the independent Pi token
returned 200. Explicit synchronization at **23:01:21 IST** made the workstation token
match both `/etc/agentic-trader.env` and the running service; authenticated public
reads returned **200** before and after deploying corrected help text. Repeating the
sync was a no-op with 200, confirming the synchronized credential survives normal
redeployment. No token value was printed or placed on command arguments.

Private credential backup:
`/var/backups/trading-operator-token-20261025T173121240741Z/agentic-trader.env`.
Current application release for the corrected help:
`20261025T173439-293e424fcefc`. Public HTML checks confirmed the server-specific token
label, Pi env path and explicit-sync guidance. Independent database integrity and
financial-state hashes remained unchanged. **32 focused Python checks and all 233
Node UI tests passed**, including executing the exact generated remote helper in an
isolated process. This validates operator access; it does not assert broker, market,
phone interaction or power-loss acceptance.


### Repairing an invalid existing Pi token — 25 October 2026

A reported sync failure occurred at `old_token = read_token(previous)`: the incoming
workstation token had passed validation, but the helper incorrectly required the
existing Pi value to satisfy the new-token format. Replacement now validates the
incoming value and the uniqueness of the target assignment, while allowing malformed
old values to be replaced. It still rejects ambiguous duplicate/missing assignments
and symlink targets before changing anything. CLI errors no longer dump a traceback
and the embedded remote program.

**38 focused token-sync/public-hosting checks passed**, including independent-process
execution for unchanged, short, punctuation-bearing, empty and incorrectly quoted
old values; byte-preserving private backups; duplicate refusal; secret-free stdin/argv
boundaries; concise SSH failure; and independent exact-accounting verification.
The corrected command repaired the real Pi file and returned authenticated HTTPS
**200**, with a private backup at
`/var/backups/trading-operator-token-20261025T175752958380Z` (**23:27:52 IST**).
Independent read-only SQLite integrity and before/after orders/fills/positions/monetary
hash checks passed unchanged. No token value was displayed. No application-source
redeploy was required: this helper runs from the workstation and sends its current
implementation over SSH. This is operator-access validation, separate from broker,
market, handset or power-loss acceptance.


### Startup recovery from a short token — 26 October 2026

At investigation both local/Pi tokens were 11 characters. The deployed Settings
validator rejected the Pi token with `operator token requires at least 32 characters`,
causing the unit's retry loop/start-limit failure. The sync helper independently
rejected the same weak local value before SSH. The token minimum was retained.

Added explicit `--generate`, private local backup, and automatic `reset-failed` before
restarting a changed or inactive service. Generated/saved a strong replacement in
both private configurations and restored the actual service at **08:27:02 IST**.
Authenticated public workspace read returned **200**. Local backup:
`backups/operator-token-20261026T025701788408Z`; Pi backup:
`/var/backups/trading-operator-token-20261026T025702846449Z`.
No credential value was displayed. Independent SQLite integrity and before/after
cash/orders/fills/positions checks, healthy no-op verification and final service
state are recorded with this recovery. Local validation: **42 focused tests passed**,
including generation/privacy, real CLI generation in an isolated process, failed-unit
reset/restart ordering, unchanged-file recovery and exact persisted financial state.
These are access/startup checks, not broker, strategy-profitability or handset acceptance.
