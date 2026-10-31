# Native Android access component

## Watchlist and safety controls (backend 0.21.0)

Paired-phone sessions may use the authenticated `/api/desk/watchlist`, catalog search
and `/api/desk/safety/resume` routes through the existing desk allowlist. Native
1.1.0 reviews exact revisioned replacements and reset consequences before POST;
lost outcomes retain the durable inspection marker for the Watchlist destination.
All entry restrictions apply server-side to phone, browser and CLI accounts.
See [watchlist-safety.md](watchlist-safety.md) for inputs, outcomes and limitations.
New native/API cases were added and were not executed in this change.

## Verified 0.20.9 / Android 1.0.9 publication

Published **backend 0.20.9 / Android 1.0.9** on 29 October 2026. Release
`/opt/agentic-trader/releases/v0.20.9-20261029T170852-8e34e6bec934`, Trader PID 47194;
previous 0.20.8 code retained. Local/public health, manifest/installed-source hashes,
public daily-flow asset, installer metadata/certificate and downloaded APK hash match.
Other service PIDs remain 1193/1194. The official Nifty 50 scope is preserved.

Live timings: local account **0.163 s**, source-only check **0.073 s**, full accounting
report **0.787 s** (previously exceeded 55 seconds); public account **0.537 s**, source
check **0.250 s**. These are individual live acceptance measurements, not a load-test SLA.
The previously requested feed is connected with zero connection failures, broker profile
verified and Manual still selected. Current guidance is waiting for the next reviewed
entry, **30 October, 09:30 IST**. No trading mode or purchase was submitted by deployment.

Strict independent full SQLite comparisons pass: **both databases entirely unchanged**.
Broker credentials, phone registry, economic/risk configuration and other configuration
files are unchanged. The sole configuration difference is the installed-calendar file
reference; its reviewed file contents are byte-for-byte identical to the private baseline.
This difference is recorded separately, not represented as an unchanged whole-config hash.
Both strict unchanged-database assertions were retained and passed. No financial database
was restored.

Signed production **Android 1.0.9 / code 10** installed in place on Moto g52; cold launch
282 ms. Retained pairing and the already-authenticated production Discover screen were
verified using fixed-label navigation and boolean observations only. Two samples showed
saved research visible, no progress indicator, no Discover loading label and no network
error. No biometric was bypassed and no private screenshot or financial values were saved.
This is live phone/API navigation acceptance, distinct from the 33 invented offline UI
workflows. Temporary demo/test packages were removed. Actual market signals/fills and a
new sensor-authentication event were not asserted by this check.

Private evidence:
`/var/backups/trading-services-v0.20.9-20261029T170852-8e34e6bec934/acceptance.json`,
`latency-acceptance.json`, `feed-status.json` and `configuration-comparison.json` in the
same directory. Baseline:
`/var/backups/trader-v0.20.9-preflight-20261029T170828Z.json`.

## 0.20.9 source-only daily check

`GET /api/desk/preparation/audit` requires existing authorization and is permitted by the
phone's existing read-only desk scope. It returns schema/versioned shape `schema_version=1`,
`observed_at`, a minimal preparation identity (job ID/state/universe/snapshot/source-preview
hash), `source_validation`, `source_error` and an explicit non-authorizing label. It takes
a copy under the preparation lock, then validates bounded files outside that lock. No
setup/engine/quote/risk lock, catalog scan, broker request, ledger/integrity scan, mode
change or financial mutation is performed. Invalid/missing sources return null validation
and `SOURCE_INVALID_OR_UNAVAILABLE`; they never count as current data. Callers bind the
result to the current job and keep all existing server confirmation/revision checks.

Android automatic/reuse checks now use this endpoint. Full `/api/operations?audit=true`
and CLI daily reports retain their accounting audit and now cache basket resolution
once per report. Routine status and source-only evidence cannot replace that accounting
audit or grant trading permission. Initial Android account loading excludes automatic
checks; source-check failures have separate UI recovery and cancelled reads can resume.
No new token persistence, scope or retry permission is added.

Production backend **0.20.8** and signed **Android 1.0.8 / code 9** are published;
installer/source/version hashes, preserved registry/credentials, unchanged full financial
SQLite state and Moto biometric-entry installation are verified. See the release evidence
in [Android guide](android-app.md#guided-daily-home-android-108--code-9). Production
session authentication for the new flow remains distinct from offline UI simulation.

## 0.20.8 / Android 1.0.8 daily orchestration

No new endpoint, scope or trading permission is added. The native Home flow composes
existing read-only `POST /api/setup/profile`, `GET /api/desk`, `GET /api/setup` and
`GET /api/operations?audit=true`, then the existing catalog/download and guided preview/
confirm routes after Continue. A successful current profile is reused; profile failures
are not automatically equated with expiry. Read-only checks run while unlocked and
cannot acknowledge or arm trading. Audit reuse binds job ID/universe/hash-validity,
same-IST-date and completed-session coverage; its memory key changes at reviewed/proposed close,
new IST day and job/source/policy transitions. Routine polls do not repeatedly audit.

Browser callback preparation carries a non-secret Home-resume flag; biometric re-unlock
is still required. The installed server policy is reused; new explicit choices stay in memory until confirmation.
No response snapshot, broker/owner/session token, policy choice or financial values are added to preferences.
Guided confirm, connection and mode still use frozen reviews, acknowledgments/revisions,
server revalidation and existing unknown-result recovery. Partial guided receipts prevent
false completion; cancellation/failure stops automatic review opening. No live execution,
future automatic activation or blind mutation retry is introduced.

## Automatic official basket and analysis diagnostics — 0.20.7 / 1.0.7

`POST /api/desk/universe/nifty50` requires owner/scoped phone authentication and strict
`revision` plus `acknowledged: true`. Clients supply no stock names or source URL.
The server fetches and validates the allowlisted official list, then rechecks Manual/
revision, disconnected feed, no pending orders and held-stock preservation. It raises
legacy feed capacity to fit the full basket without changing financial policy. Source
unavailability, incomplete catalog, stale revision, active mode/feed and unresolved
orders fail closed. A source CSV is retained privately beside broker setup. A failed
persistence can require state inspection; the client never blindly repeats this POST.

Setup status adds `automatic_universe` (custom/nifty50). Desk adds `monitoring` with
universe/member/history coverage and `analysis_status` with bounded per-stock live-
candle checks, warm-up counts and plain reasons. Missing reviewed members are visible
rather than allowed to trade. Guided preparation accepts/defaults nifty50, with all
members included and data eligibility kept separate. Nifty 100/500 stay supported.
Capacity and automatic-universe settings are excluded from the financial fingerprint;
account limits, approvals, opaque phone authority and real-order restrictions remain.

Actual 0.20.7 migration verified all 50 official members, exact CSV hash, capacity 50,
50 discovery rows and connected feed. Full account DBs and economic fields are unchanged;
basket/capacity fields changed intentionally. Fourteen action/history exclusions remain
explicit and 36 cached histories require the newly completed session. See [evidence](raspberry-pi.md).

## Read-only mode guidance — 0.20.6 / Android 1.0.6

`GET /api/desk` adds `readiness.mode_guidance` schema 1: `state` (ready/waiting/
action_required), plain title/summary, server `now_ist`, configured `entry_window`,
nullable `next_entry_at`, `items` (code/title/detail/kind/target) and
`automatic_start: false`. Targets are a closed set: broker, strategy and risk.
The pure `desk.mode_guidance` component intersects reviewed exchange sessions with
the entry window, handles cutoff/special sessions and does not infer unreviewed dates.
Current open-entry quote waits do not incorrectly point to tomorrow. All actual
blockers remain represented, including unknown gates; guidance cannot grant authority.

Android freshly reads desk before mode review. A business-blocked choice opens live
help without a mode POST; only explicit review/acknowledgement/confirmation can submit.
Quiet status updates keep help current. Missing/contradictory `blockers`/`can_start`
fails closed. A 409 caused by changed readiness triggers read-only inspection and help,
never a financial retry. Server mode/revision/quote/risk gates are unchanged.

Backend 0.20.6 and Android 1.0.6 publication is verified: source/installed/public APK
hashes match, live mode guidance covers all blockers and both full financial DB/config
baselines are unchanged. Only Trader restarted. Sessions expire; unlock and follow
the displayed feed/session recovery steps. See [deployment evidence](raspberry-pi.md).

Actual deployment 0.20.5 and Android 1.0.5 publication passed hash/health verification.
On 29 October, the real phone login callback saved a Kite access token and verified
the broker profile. Status exposes only availability/verification flags, never the
saved token; the Android fallback request-token field stays empty by design. Return
to the app and unlock after browser login. Callback/profile success does not establish
history/stream entitlement. See [device and deployment evidence](android-app.md).

## Environment capability and Android 1.0.5

Backend **0.20.5** adds authenticated read-only `GET /api/trading-environment` for owner
and scoped phone sessions. Schema 1 returns `active: paper`, an available Paper entry,
a disabled Real entry with `LIVE_EXECUTION_NOT_IMPLEMENTED`, and
`switching_available: false`. There is no POST/PATCH environment control (405).
Settings still accepts only paper; Kite access remains read-only. Capability inspection
cannot write the ledger or change decision mode. The native selector is informational
and keeps Real disabled. Desk account mode must explicitly be paper before publication
or action; a missing capability route on an older backend does not enable Real.

Android batches snapshot reads and publishes completed batches together. Quiet polls
never set foreground busy/progress; generation/session/page checks prevent cancelled
reads publishing after newer work. Initial unlock preserves busy until initial data
arrives and presents branded loading in the meantime. Reviews/dialogs pause polling.
Production package, Keystore identity, biometric policy and no-automatic-write-retry
behavior are unchanged. Core SplashScreen 1.2.0 supplies native Android 11+ startup;
its artifact checksums are recorded in Gradle dependency verification.

Backend **0.20.5** publishes Android **1.0.5**, which retires idle sockets before the
upstream keep-alive close and retains paired UI state after saving the encrypted
credential. The existing financial authority is unchanged; the capability GET above is additive. This network fix keeps
automatic financial retries disabled and requires no replacement phone credential.
Cancellation/TLS close run off the Android UI thread; a fresh client is installed
before retiring the previous one, so cleanup cannot cancel a subsequent unlock.
Android 1.0.3 adds the selected supplied launcher artwork; the API and financial
behavior remain unchanged. The installer is verified and versioned as before.
Android 1.0.4 uses the existing `GET /api/operations?audit=true` contract for saved
history reuse. Default `audit=false` deliberately returns null source validation;
it must never be interpreted as a completed freshness check. The native client
binds reuse to the audited/current job identity and requested universe. Audit is
read-only and does not fetch provider history, change review status or grant authority.

Backend 0.20.0 adds `trading_agent.mobile`: credential/session authority, phone-bound
broker callbacks and public signed-installer delivery. It does not add live orders
or alter paper-account economics. See [Android usage](android-app.md).

## Authentication contract

| Route | Authority / behavior |
|---|---|
| POST `/api/mobile/devices` | Owner token only; validated label; one-time device ID/secret response |
| GET `/api/mobile/devices` | Owner sees all; phone sees itself |
| DELETE `/api/mobile/devices/{id}` | Owner or that phone; revoke credential and sessions |
| POST `/api/mobile/session` | Opaque ID/secret; rejects browser Origin; returns memory-only 900-second session |
| DELETE `/api/mobile/session` | Authenticated session logout |
| POST `/api/mobile/broker/login` | Start a five-minute attempt bound to authenticated phone |
| GET `/api/mobile/broker/login/{id}` | Original phone only; waiting/exchanging/verified/failed/expired |
| POST `/api/mobile/broker/login/{id}/exchange` | Original phone's fallback one-time token exchange |
| GET `/api/mobile/release` | Public APK version, package, minimum versions and hashes only |
| GET `/android`, `/downloads/agentic-trader.apk` | Public installation instructions and integrity-checked APK |

Central API authorization accepts either existing owner authority or a valid scoped
phone session. Explicit method/path boundaries allow existing paper/research/setup
controls; phone sessions cannot enroll another device. Origin protections on other
authenticated routes are retained, including prefixed deployments.

Pairing records live in a private atomic `.mobile.json` beside the account database,
separate from the financial ledger. Stored secrets and owner binding are SHA-256
hashes of random credentials; sessions are hashed in memory. There are at most eight
active devices and twenty bounded historical records. Restart clears sessions;
owner-token rotation invalidates every pairing. Five failed unlocks per minute per
known device (one bounded unknown bucket) trigger 429. Invalid/oversized authentication
JSON is sanitized and bounded to 4096 bytes; secrets are not echoed in errors.

Private/symlink/corrupt storage checks fail closed. Failed enrollment persistence
removes the unreturned credential from memory. Revocation removes authority in memory
even if persistence fails; the API reports 503 and requires owner retry before restart.
These storage failures are handled without faulting or modifying the paper ledger.

The registered Kite redirect stays `https://shanmukhan.com/agentic-trader/`.
`mobile_attempt` joins the existing `setup_state` redirect parameters; the public
root validates nonce, expiry and one-time waiting→exchanging transition before the
server performs token exchange. Replay never exchanges twice. HTML contains only a
fixed outcome; external `mobile-return.js` removes callback query history, with no
storage/broadcast. Broker account identity/entitlement remains SetupService's job.

## Installer integrity and deployment

`scripts/build_android.py` verifies the real APK signature/manifest before producing
public metadata. `bundle.py --android-apk` allows only fixed production filenames;
no native source, local SDK, Gradle cache or private signing material is bundled.
The server rejects symlinks, malformed production metadata, oversized files or a
hash mismatch. Runtime metadata verification is packaging integrity, not an independent
APK signature parser; the build's apksigner validation provides signature evidence.

Unit/functional tests use invented credentials, broker transports and packaging bytes.
They cover expiry/restart/rotation, scoping/revocation/rate limits, callback/fallback,
private storage failure, prefix delivery and tamper refusal. A phone-authenticated
synthetic purchase independently reopens SQLite to verify exact cash debit, quantity,
fees and replay idempotency. Read-only/security tests compare entire logical databases.
Actual signed APK, target Pi and device acceptance are recorded separately.
