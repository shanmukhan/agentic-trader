# Threat model and security decisions

Assets include Kite credentials, operator token, market data, simulated account
integrity and the host. The goal is to prevent live execution paths and accidental
loss of paper-account correctness. A hostile local administrator can change Python
or SQLite; this application does not claim protection from a compromised host.

| Threat | Implemented mitigation | Remaining operator responsibility |
|---|---|---|
| Live order submission | No order adapter; fixed HTTPS route allowlist; packet subscription messages only | Do not add a live adapter without separate review |
| Secret leakage | Environment/hidden prompt; new token files 0600; generic third-party errors; JSON redaction; access logs off | Protect shell/env files, backups, OS and process account |
| Cross-site controls | Bearer token, no cookies/CORS, Origin check, trusted Host, CSP, no inline script, no browser storage | Keep the token private and use loopback/SSH |
| Database corruption / power loss | WAL FULL sync, atomic fills, startup ledger reconciliation, exclusive owner, tested backup/restore | SSD/UPS, free-space monitoring, off-device encrypted backups |
| Stale / malformed feed | Typed validation, full-packet checks, mapping/tick validation, fresh-after-reconnect gating | Review calendars and catalog changes, monitor feed |
| Duplicate commands | Persistent intent fingerprint, 409 on conflicting reuse | Use stable unique IDs for each economic decision |
| Loss controls bypassed | Independent gate in transactional execution boundary, durable kill | Avoid editing durable state or policy hash directly |
| Compromised dependencies | Hashed version lock, audit check in CI, small runtime | Review upgrades and pin trusted CI action revisions in your deployment |

## Dependency audit decision

The initial official `kiteconnect==5.2.2` installation required
`autobahn[twisted]==19.11.2`. The 20 October 2026 audit reported
`PYSEC-2020-25`, `PYSEC-2026-4027`, and a Twisted advisory. The SDK's old pin is
also visible in [its package/source](https://github.com/zerodha/pykiteconnect) and the
[maintainer issue](https://github.com/zerodha/pykiteconnect/issues/211).
Rather than suppress advisories or force unsupported dependency overrides, the SDK
and its transitive stack were removed. The application implements only the needed
official [authentication](https://kite.trade/docs/connect/v3/user/),
[instruments](https://kite.trade/docs/connect/v3/market-quotes/),
[history](https://kite.trade/docs/connect/v3/historical/) and
[WebSocket](https://kite.trade/docs/connect/v3/websocket/) protocols with locked HTTPX
and websockets transports. Tests verify both forbidden calls before network access
and real response/packet parsing. The reduced environment passed a new advisory scan.
This is a documented security exception to the specification's SDK recommendation.

HTTP requests use TLS verification, fixed broker origin, ten-second timeout, no
environment proxy and no redirects. WebSocket URLs contain credentials as required
by Kite, so connection objects, exceptions and debug URLs must never be logged.
Third-party HTTP/WebSocket loggers are disabled during service execution. The socket
worker emits only generic connection state. Reauthentication remains manual.

The included secret-pattern script checks the working tree for project-specific
assignments and private-key headers; it is intentionally limited. It is not a full
history scanner or proof that no secret exists. Before sharing any repository,
review `git diff`, ignored files and deployment environment. Never commit real tokens.

No external alerts are sent. Kill/data-quality events are in the durable journal;
the dashboard and generic local error log provide local visibility. Integrating
paging/notifications is a later operational task requiring an explicitly chosen service.

## Phase 2 inputs and account isolation

Research accepts bounded JSON/JSONL, not executable models or arbitrary URLs. The
manifest fixes the local event filename. Symlinks, oversized records, unknown fields,
manual candidates and catalog/session mismatches fail. Availability clocks enforce
completed candles and observed quotes. No OHLC path or favorable fill is inferred.
Hash checks detect ordinary input changes, not a malicious local administrator.

Backtests use new private output accounts and never open the service account. Export
reads source data without an execution engine, preserving orders and balances. Its
manifest is written last so partial bundles are not loadable. Replay/mixed origins
retain synthetic labels; `synthetic: false` is not authenticated provenance proof.

Invalid runs retain sanitized failure state and partial research ledgers without a
success report. Policy/config/code/input/journal identities are recorded. Reports
contain market/research data, not credentials or profiles. No upload, notification
service or new runtime dependency was introduced for Phase 2.

## Phase 3 model artifacts and validation leakage

Offline fitting uses locked optional NumPy/scikit-learn packages. The execution
and model-loading path imports neither. It accepts fixed-name, bounded local JSON
files with finite typed coefficients and exact feature order, not executable pickle,
joblib or arbitrary model loaders. Local symlinks, partial manifests, hash failures,
unknown fields, dimension errors and inconsistent diagnostics fail. Report gates,
split windows and calibration bins are checked rather than trusting a summary flag.

Training-only scaling, disjoint later calibration, label-interval purge, whole-session
splits, frozen final coefficients and separate holdout address temporal leakage.
Model availability includes the final validation interval plus embargo, preventing
historical replays from using future approval evidence. Candidate fingerprints and
durable model binding prevent accidental feature/intent substitution or gate removal
on restart. Independent risk controls still apply to every scored order.

Hashes are integrity checks, not signatures or independent provenance attestation.
A local administrator can rewrite files and hashes; malicious code or fabricated
market data remains outside that guarantee. The `synthetic` declaration is not
authenticated. Protect/review datasets, configuration and artifacts. Synthetic
override never disables metric, context, risk or temporal checks and is refused
against non-synthetic data. No network model download or service upload is added.

## Phase 4 supervised feed boundary

Automation is explicit, private and paper only. Authenticated arm/disarm controls
use the existing Bearer/Origin/Host protections. Accounts bind configuration, universe,
model and runtime identity, and cannot drop the controller through normal restart.
The broker also requires its controller identity on new submissions. Direct Python
code and a malicious local administrator remain trusted-process boundaries.

History I/O runs outside quote/execution locks, with bounded universe, paced requests,
retry cadence, completed-time checks and reconnect-generation rejection. Changed
history revisions fault the runtime. No broker order route or executable model load
is introduced. Fault handling blocks entries even when storage cannot journal the
failure. Disconnect/staleness cancels buys and preserves unresolved liquidation.

Periodic metrics retain recent windows plus cumulative counts, maxima and exceedances;
reports explicitly disclose missing crash measurements and incomplete coverage.
Synthetic drills cannot pass provenance/sample/model evidence gates. No report can
enable live execution or attest empirical broker/device acceptance. No external
alert is sent; supervision remains the operator dashboard and local journal/logs.

## Console and acceptance diagnostic changes (0.4.1)

The static shell has no private values until Bearer authentication. Script and CSS
load from same-origin package resources; CSP now also restricts style to self and
blocks form navigation/objects. Text nodes render all dynamic values; no HTML
injection sink, browser persistence, external analytics or credential-bearing URL is
used. Fetches omit cookies and reject redirects. Lock/authorization failure clear
private values and discard late responses. Stale data disables arm/reset, and their
confirmation dialogs do not override server authorization/risk checks. Emergency
kill/flatten/disarm remain direct actions. Native phone/remote-access acceptance is
pending; this change does not expose a listener publicly.

The preflight reads an existing URI-escaped SQLite file with `mode=ro`, query-only,
untrusted schema and normal WAL locking. It bypasses process ownership only for
read-only inspection, never SQL mutation/recovery or initialization. It checks private
storage, local identities, disk and officially fixed SQLite WAL-reset version branches;
unknown vendor backports remain for review. Raw errors/environment credentials are
not included. Reports are private account/platform data with hashes for accidental
integrity only, not signatures or an acceptance authority. No network request,
credential probe, model execution or change to financial risk limits was added.

## Long-term boundaries (0.5.0)

A durable horizon binding, different economic-policy hash and separate charge version
prevent intraday/delivery account confusion before pending recovery. Legacy intraday
hashes are preserved. Existing intraday automation/research is refused for long-term
configs. Missing long-term markers/checkpoints and inconsistent delivery fee/review/
quarantine/exit evidence fail reconstruction; no protection is silently reseeded.

Authenticated typed review/exit routes preserve existing Bearer/Host/Origin/unknown-field
controls. Review assertions are not external corporate-action verification. The API
requires current reviewed dates/registered selected symbols and refuses clearing a
known quarantine; raw changed prices are blocked before financial processing.
UI reviews and exits require confirmation, use text rendering and do not persist
credentials. Review references live in private evidence: never put secrets in them.
No broker order method, custody synchronization, settlement permission, public listener
or actual cash/share adjustment capability was added. See [long-term.md](long-term.md).
