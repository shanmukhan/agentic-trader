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
