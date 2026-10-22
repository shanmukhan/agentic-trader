# Threat model and security decisions

## Registered research boundary (0.17.0)

Browser jobs accept only a registered opaque resource identity/hash, stable request key
and explicit acknowledgement under existing operator authorization. Local CLI registration
validates/copies bounded inputs; arbitrary browser paths, URLs, uploads, executable models
and code are unsupported. A worker gets a separate scratch ledger, allowlisted environment,
read access to its registered inputs/runtime and a deny-by-default Darwin network/write
sandbox with hard resource budgets. The operator account/token/broker configuration is
not a worker input. Private storage and an exclusive research-owner lock protect lifecycle
state; cancellation and report publication serialize, and interrupted work never resumes.

Capability fails closed when OS restrictions/budgets cannot be verified. Current Mac
launch is unavailable; Linux/Pi browser isolation is unsupported. Native denied/allowed
read/write/network, resource-kill and target-device acceptance remain explicit gates.
Mocked launchers and synthetic datasets do not establish this security boundary.

Reports are hash/request checked and their scratch SQLite accounting is independently
reopened read-only before bounded JSON publication and again on reads. Raw databases,
executable HTML, arbitrary artifacts, raw credentials and operator paths are not served.
Sanitized research errors never invoke account mutation recovery. Retained capacity is
bounded; no automatic deletion/archival migration is supplied. See
[browser-backtesting.md](browser-backtesting.md) for actual limits and failure recovery.

## Genuine-data preparation (0.13.0)

Mode activation is blocked throughout installation. An optional strict acknowledgement
can correct conflicting hours only when execution/quote/candle, pinned review,
action/payment and portfolio/SIP/desk-instruction tables are unused. The gate is rechecked
after validation; used definitions cannot be overwritten. IST date changes invalidate
acquisition/installation rather than mixing different source coverage dates.

New authenticated POSTs under `/api/desk/preparation/{download,cancel,install}` use the
same bearer/Origin controls as the trading desk. Download requests have an idempotent
request identity, closed universe enum and mode revision. Install binds the exact
source hash, edited bounded calendar, explicit policy and three strict acknowledgements.
No HTTP client may select an arbitrary data/model path or URL. The optional model path
is server-selected through `TRADING_PREPARATION_MODEL`, validated with existing strict
loaders and never automatically replaced with rules.

Public reads use a fixed HTTPS host/path allowlist (NSE/NSE Indices), no redirects or
environment proxies, bounded streamed responses and timeouts. Broker access adds only
the read-only `day` historical interval, retains the no-order route allowlist and uses
a shared 400 ms historical-read limiter. Neither broker credentials nor third-party
exception text are published in job state or artifacts. Data/network work holds no
quote/risk lock. Private regular server-owned files, bounded reads, hashes and immutable
job identities protect preparation/restore; changed data cannot be silently selected.

Current constituent snapshots are explicitly prospective. Their observation/review
clocks cannot establish historical membership/ML validation; offline execution rejects
them. Missing/empty official action sources fail closed, and every returned action in
the full interval excludes that stock. Calendar proposals require explicit completeness,
hours and special-notice review before installation. Installation requires Manual,
disconnected feed, no pending orders, unchanged revision and compatible existing session
definitions, rechecked after out-of-lock research loading. Holdings, capital, current-day
basis reviews and independent protective exits are preserved. Installation never arms.

The active profile/data pointer survives restart, while strategy authority does not.
Data I/O errors return sanitized preparation failures rather than declaring a financial
account fault. Partial installation can leave a reviewed calendar configured before the
profile pointer is committed; remain Manual and inspect/retry the exact review. No
automatic account recovery, source completeness attestation or profitability claim is made.

## Strategy authority and decision history (0.12.0)

The new desk/activity frames use the existing exact origin/window/view handoff; public
shells contain no private account data. Modes require an authenticated explicit
confirmation and current revision; trade approval requires a server-stored preview
hash and fresh bounded revalidation. Browser clients cannot create arbitrary strategy
proposals or provide model/data paths. Data/model loading is bounded, typed JSON/TOML,
not pickle/code, and production profiles reject synthetic fixtures. A failed ML policy
never silently falls back to rules. Profile/model/source identities are retained.

Authority is revoked in memory before durable cancellation so a journal fault cannot
leave an active mode. Quantity/cash/risk caps cannot grow through a changed quote.
Mode/session/feed/model/risk changes invalidate unsubmitted work; fresh data does not
implicitly reactivate it. Broker-transaction authority proofs plus journal/table
reconciliation detect missing/mismatched decision provenance. BUY restart recovery
links a matching order or cancels unsubmitted authority; it never repeats an order.
Protective exits remain independent of approvals. These invariants do not protect
against a fully compromised local OS/operator rewriting all code and evidence.
Headless preview uses an isolated synthetic database/profile, not operator credentials.

Version 0.11.1 exposes fixed credential-free feed failure codes and bounded retry
counts through authenticated Setup. Never include raw exception strings, broker text
messages, socket URLs or headers: these can contain session credentials. Last receipt
time includes heartbeats and is explicitly not a fresh-quote attestation. Empty books
invalidate prior executable depth per symbol without manufacturing prices/quantities;
strict batch identity/framing checks precede callbacks. Intraday's existing stale-data
safeguards remain active while the transport stays connected.

## Shared in-memory workspace (0.11.0)

Local menu navigation retains one operator token in workspace/active-section memory.
It never uses URLs, cookies or browser storage. Only fixed Console/Setup/Portfolio
views receive it, after exact origin/window/active-view checks; each child also
checks its parent. A lock or section authorization failure removes the active view
and clears shared authority. Reload/new workspace tabs require a new local unlock;
visibility changes alone do not intentionally log out. Server actions already
received can still complete after locking, so unknown-outcome recovery still applies.

Framing is deliberately relaxed only for `/console`, `/setup` and `/portfolio` to
same-origin ancestors. Workspace/root/API/other routes retain DENY and/or
`frame-ancestors 'none'`; outside-origin framing remains prohibited. The parent
cannot embed arbitrary URLs from its hash or child messages. The same-origin
application remains a single trust boundary, not protection from same-origin XSS
or a compromised OS user. Popup callback state/origin/window guards and legacy CLI
capture remain intact. No server cookie or cross-tab credential broadcasting exists.

## Authenticated browser setup (0.10.0)

The new manual-account `/setup` shell has no private values until local operator
authentication. Existing Host/Origin/bearer controls apply to every setup API; broker
credentials cannot unlock it. Secret-bearing bodies are bounded and parsed without
validation input echoes; third-party exceptions are replaced with fixed messages.
No browser path, endpoint or shell command is accepted. The API never returns a
stored secret/access token. The public API key appears in the official HTTPS login
URL. UI inputs clear before requests, lock clears all private state/late responses,
and no browser persistence or external script was introduced.

Credential/session storage is an atomic mode-0600 plaintext file beside the account,
not encryption. Symlink/nonprivate stored credential files fail closed. The browser
popup requires matching origin, opener window and random five-minute state; the
server consumes a login attempt before exchange, and the popup callback removes its
query. CLI manual redirects remain explicit. A stolen operator credential still
grants local account/setup authority; this is not broker-scope isolation or protection
against the same OS user. The launcher refuses redirects/proxies and verifies the
authenticated account-path hash before reusing a running server.

Calendar additions require explicit operator review, immutable existing definitions
and a private snapshot committed before config replacement. The UI cannot verify
that an operator's source/attestation is truthful. No price-basis, quarantine, loss,
kill, model or financial-policy override was added. Quote connection/reconnection
may resume existing paper fills/exits; confirmations explain that distinction.
See [ui-setup.md](ui-setup.md) for persisted-file and recovery limits.

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

## LT2 reviewed financial mutations (0.6.0)

Exclusive local offline commands now adjust supported *paper* shares and issuer
claims; they expose no new HTTP mutation route, network client or real-money scope.
Input is UTF-8, regular/nonsymlinked, bounded to 64 KiB, extra/duplicate-key rejecting,
strict for ratios/coverage, aware and causal for dates, exact for money. Policy,
horizon, original price/trade basis and current quarantine hash must match. The
complete-coverage assertion is an operator trust boundary, not verified issuer data.

Stable IDs, unique claim payment, atomic ledger/journal/materialized writes and
independent reconstruction prevent accidental duplicate credits, missing fractional
basis and orphaned payment state. Action calendar evidence is pinned before recovery.
Known dividend claims are nonspendable and unknown fractions retain stale valuation.
Unresolved fraction chains and unsupported issuer events fail rather than silently
creating shares, receipt values or settled eligibility. Hashes detect inconsistency;
a malicious filesystem owner can rewrite evidence and remains outside this model.

Keep reviews, input files and reports private and free of credentials/account IDs.
Old versions cannot be used on an LT2 account; preserve backups and use this release
or later. These features do not synchronize demat/bank state or authorize live use.
See [corporate-actions.md](corporate-actions.md).

## LT3a offline input/report surface (0.7.0)

Daily analysis adds no account/HTTP/network authority. Bounded regular nonsymlinked
manifest/JSONL input rejects duplicate keys, extra fields, invalid OHLC, unknown or
unordered rows, future use and late membership knowledge. Prices remain raw with
explicit reviewed period-benefit units. Hash/mutation checks protect reproducibility,
not source truth or malicious filesystem-owner rewrites. Metadata asserting real
provenance is not independently verified. Generated JSON escapes HTML delimiters;
UI rendering uses text nodes, restrictive hash CSP and no fetch/storage/eval sink.
Outputs are private, fsynced and completed with a final hash manifest. Research can
be misleading if the operator omits calendar/universe/corporate-action evidence;
those assumptions and lack of execution/model approval remain visible in the report.

## LT3b delivery evidence and daily model input (0.8.0)

New daily quote/control/action inputs use strict tagged schemas, bounded local
nonsymlink files, duplicate-key rejection, aware nondecreasing clocks, catalog and
exact sourced-calendar agreement, with before/after hashes. New private output
accounts avoid service recovery/mutation. Hash manifests are written only after
reconciliation, closed DB hashing and artifact completion. Sample loading cross-checks
completion audits, candidate/feature identity and full net cash outcome. JSON model
loading checks dimensions, chronology, validation consistency and context; no executable
serialization is accepted. Synthetic flags/overrides cannot relax statistical or risk gates.

The owner can rewrite every hash/file; these checks do not authenticate market,
issuer or bank provenance. Counterfactual cash entitlements are not inferred. Escaped
embedded JSON, text-only DOM rendering and hash CSP keep reports local with no network
or trade authority. Training remains offline and daily models cannot arm a connected
long-term service. See [daily-execution.md](daily-execution.md) for workflow/limits.

## LT3c1 contribution authority and SIP input (0.9.0)

Typed bounded immutable requests, exact preview context hashes, authenticated origin
checks and writer-transaction revalidation prevent stale approval or duplicate intent
from adding exposure. A unique plan/date and deterministic server-issued ID prevent
new IDs from replaying a consumed occurrence. Additions preserve existing protections
and require independent cash/risk/holding capacity; ordinary intents still refuse them.
No automatic funding/scheduler, external broker client or cross-account writer is added.

Journal/table/schema reconstruction checks missing/rehashed proof, order economics,
first-fill holding basis, caps and timing before normal recovery. Hash consistency
is not protection against an owner rewriting all evidence. Network-import checks now
parse AST across execution/portfolio/risk/action modules, avoiding table-name false
positives while widening coverage. Shared money rendering uses decimal strings;
private page values remain in memory and clear on lock. No browser persistence or
client sizing authority. See [portfolio-contributions.md](portfolio-contributions.md).
