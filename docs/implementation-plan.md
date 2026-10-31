# Implementation plan, enhancements and status

## 31 October 2026 — implemented watchlist permissions and operator safety

Backend 0.21.0 / Android source 1.1.0 (code 11). Implement the NSE catalog picker,
private workspace tab/native bottom tab, durable account permissions, explicit
replacement confirmation and empty-list entry blocking. Enforce watchlist membership
and conservative safety restrictions in PaperBroker for every connected entry path;
retain held stocks for exits. Add daily accepted-intent quota, fee-inclusive 25%
equity sizing, persistent 25% drawdown pause/reset and daily price-integrity latch.
Reuse existing exact money accounting, no-borrow/no-short and ledger fault handling.
Persist the overlay separately from existing immutable economic/model policy hashes;
it can only constrain their authority. Runtime feed shortlists intersect permissions.
Offline research is explicitly separate. External funding is not an implemented
workflow; audited flow adjustment remains required before funding can be added.

Add unit, functional, browser and native regression sources, including independent
SQLite checks of money/reservations/fills. Tests are intentionally **not executed**
on this change at the user's request. See [watchlist-safety.md](watchlist-safety.md)
for implemented behavior, recovery, activation semantics and acceptance limits.
Static Python/JS syntax, Ruff, mypy (135 files), whitespace and secret-pattern
checks pass. Android compilation remains unverified: wrapper download timed out;
the installed Gradle offline fallback lacks Android Gradle plugin 9.4.1.
Deployment and native package publication are not requested or marked complete.

## 29 October 2026 — resolve opening timeout and share the browser daily flow

Backend **0.20.9**, Android **1.0.9 / code 10**. Reproduce the >55-second full report
and identify repeated basket resolution under shared locks. Cache the basket, isolate UI
source checks from full accounting, finish initial account loading independently, preserve
fresh values on source-only failure and recover cancelled checks. Extend the four-step
flow to browser Dashboard/Strategies with quiet polling and guarded late-read handling.
Keep explicit policy/setup/feed/mode reviews and all existing account/market safeguards.
Validation: **1,435 Python tests** pass (52.40 seconds), **252 browser JS tests**,
**22 native unit tests**, and **33 offline Compose workflows** on Moto g52 pass
(83.993 seconds). Source-only checks independently preserve persisted SQLite state;
full report basket resolution stays bounded. Phone tests cover slow/failing/cancelled
audit reads with no global busy bar, no financial side effects and recovery. Discover and other cached
daily tabs show saved data immediately and refresh quietly; source timestamps and stale
read protections remain. Exact 1440px/390px browser layouts were visually inspected
with invented data; the 390px document has no horizontal overflow. Lint has
zero errors (37 nonblocking advisories); Ruff/format/mypy and whitespace checks pass.
Signed **Android 1.0.9 / code 10** retains the existing v3 certificate and security
manifest. APK SHA-256:
`28eb2e42f9515bef49519592836ac85c8db5e500dc2fde51ecc7e9d446cef5b8`.
Simulated/browser fixture checks do not establish production biometric or market-fill
acceptance. Live publication and navigation evidence follows.

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



## 29 October 2026 — simplify the native daily journey

Android **1.0.8 / code 9**, backend **0.20.8**: implement Access/Data/Review/Trade on
Home and Strategy; move repeated advanced preparation controls behind expansion. Bound
automatic saved-profile/source audits, cache only verified matching current data, invalidate
at reviewed close/day/source changes, reuse confirmed policy and advance requested downloads
to a single explicit setup preview. Skip valid installation for reconnection/readiness;
retain all confirmations, biometric/2FA, stale/unknown-result guards and server authority.
All native research/backtest/policy workflows remain. No backend behavior changes besides
release identity.

Validation: **22 native unit tests**, **30 offline Compose workflows** on Moto g52
(77.569 seconds), **1,433 Python tests** (51.64 seconds) and **244 browser JS tests**
pass. Native coverage includes pre-install proposed-calendar close invalidation, current
server-policy reuse, one connection review and visible failure without retry. Exact
invented balances remain unchanged; backend financial tests independently reopen SQLite.
Lint has zero errors / 37 nonblocking style advisories. Ruff, format, mypy (133 source
files) and whitespace checks pass. Signed production v3 APK keeps the existing certificate,
package, biometric protection, disabled backup/debug/cleartext and permission allowlist.
APK SHA-256: `1a7228a77e89369040f2f7b473c6cd74caecb909e6d978cb93f0b30174a05188`.
Phone tests use invented offline data in a separate package without Internet permission;
they do not establish authenticated production broker/biometric or live-market acceptance.
Published **backend 0.20.8 / Android 1.0.8** on 29 October 2026. Fresh release
`/opt/agentic-trader/releases/v0.20.8-20261029T122533-c74cc8f8668b`, Trader PID 43484;
previous 0.20.7 code retained. Local/public health, manifest/installed-source hashes,
Paper-only capabilities, public installer metadata, certificate and downloaded APK hash
are verified. Other services retain PIDs 1193/1194. Independent full logical comparisons
show **both SQLite databases entirely unchanged**; configuration, broker credentials and
mobile pairing registry hashes are unchanged. No financial database was restored.

Existing official Nifty 50 monitoring remains intact. The previously requested feed was
restored after a successful read-only broker profile check; it is connected and **Manual
remains selected**. No paper mode or purchase was armed/submitted. Production guidance
still requests current data and gives the next reviewed entry as **30 October, 09:30 IST**;
this UI release does not fabricate fresh history or guarantee a signal/fill.

Signed production **1.0.8 / code 9** installed in place on Moto g52; cold launch succeeded
(442 ms), package/version and retained biometric-unlock entry verified. Temporary demo/
test packages were removed. Production screenshots were not recorded and biometrics were
not bypassed. Authenticated production use of the new daily flow remains separate from
the 30 fully simulated offline UI workflows.

Private deployment evidence:
`/var/backups/trading-services-v0.20.8-20261029T122533-c74cc8f8668b/acceptance.json`
and `connection-acceptance.json` in the same directory. Preflight:
`/var/backups/trader-v0.20.8-preflight-20261029T122408Z.json`.


## 29 October 2026 — full official Nifty 50 automation and live candle evaluation

Backend **0.20.7**, Android **1.0.7 / code 8**: remove hard-coded ten-stock shortlist/
guided limits; default preparation to Nifty 50 and automatically select its official
basket. Retain held names, raise operational capacity as needed and keep history/source
exclusions separate from monitored membership. Scope discovery to the basket; move
manual names to Advanced and expose coverage/signal diagnostics. No cash, exposure,
position or economic fingerprint change.

The observed 6.442-second serial ten-stock acquisition exceeded the five-second candle
limit. Production analysis now seeds history off the decision path and consumes new
completed live candles. Seeding/late results cannot replay trades; incomplete/gapped
inputs block and re-seed. Five-second freshness and all financial gates remain.
Validation: **1,433 Python tests** pass (50.73 seconds), **244 browser JS**, **15
native unit** and **24 offline Compose workflow tests** pass (65.181 seconds on Moto
g52). Simulated fifty-stock signals produce real fixture orders/fills within unchanged
risk caps, with independently reopened SQLite exact cash/fees and holdings verified.
Delayed warm-up, stale/gapped/incomplete data, Manual/late results and bounded retries
remain blocked appropriately. The phone tests use separate no-Internet demo packages
and invented balances. Lint: zero errors / 36 existing advisories; Ruff, format, mypy
and whitespace pass. Signed Android 1.0.7 verifies v3 signature, unchanged certificate,
package, biometric/backup/cleartext policy. Official current CSV count/hash verification
is live public-source evidence; prospective production signal/fill acceptance is separate.
Publication and actual basket-migration evidence are recorded below.


Signed production **Android 1.0.7 / code 8** is installed on Moto g52. Cold launch
succeeded (1,015 ms), package/version and retained biometric pairing screen verified.
Demo/test packages were removed. APK SHA-256:
`9acb26e3bfb1cb459e914c4f83c0e3e4220702c73d65eb8438cb476f98b2b415`.
Published and verified **backend 0.20.7 / Android 1.0.7**, 29 October 2026.
Release `/opt/agentic-trader/releases/v0.20.7-20261029T105213-a74ff224ca49`, Trader PID
41760. Public/local health, installed/source and published installer/APK hashes match;
other services retain PIDs 1193/1194. The official-basket endpoint was applied with the
fresh revision: **50 official members, 50 monitored, 50 discovery rows, capacity 50,
automatic_universe=nifty50**. Exact membership was independently compared against
the retained source CSV, SHA-256
`f5ba4027d935ae72879d5c24bbebf0e8439ec8ed504ffdf4175fde69206244b3`.
Saved broker credentials are unchanged and profile verification succeeded. The previously
requested feed was restored and is connected. Manual remains selected; no mode was armed
and no purchase instruction was submitted by the migration.

Independent full SQLite logical comparisons show **both databases entirely unchanged**,
including cash/fees/orders/fills/positions. Economic configuration is unchanged; only
operational basket/capacity fields were intentionally updated. Held symbols were retained.
The current 50 rows include **14 corporate-action history exclusions** and **36 with
reviewed cached history**. After today's close, the latest completed session is missing
from that cache; the 36 therefore show needs-data. Trade correctly requests preparation
and gives the next reviewed entry as 30 October, 09:30 IST. Use the default Nifty 50
preparation flow for current history; do not treat coverage as a valid buy signal.

Private evidence:
`/var/backups/trading-services-v0.20.7-20261029T105213-a74ff224ca49/acceptance.json`,
`nifty50-acceptance.json` and `final-state.json` in that same directory.
Preflight: `/var/backups/trader-v0.20.7-preflight-20261029T105201Z.json`;
financial scope baseline: `/var/backups/trader-v0.20.7-universe-baseline-20261029T105145Z.json`.
Previous 0.20.6 code is retained; no financial DB was restored. Actual 50-member saved
scope and feed connection are verified, while fresh next-cycle candles/signals/fills and
an authenticated production phone tap flow remain separate from simulated UI tests.

## 29 October 2026 — proactive native Trade guidance

Android **1.0.6 / code 7**, backend **0.20.6**. Implemented plain, time-aware readiness
on Trade and on attempts to choose Approval/Automatic. Pure server guidance calculates
next entry from reviewed sessions intersected with configured times, distinguishes
waits/actions, handles special sessions/cutoff/missing dates and retains every blocker.
Completed checks and direct setup links reduce manual investigation. Native mode taps
freshly inspect state, show live help when blocked and retain explicit review/confirm.
A changed-readiness rejection shows new reasons without a retry. Stale/missing status
fails closed. No mode gates, accounting, automatic arming or broker execution changed.

Validation: **1,421 Python tests** pass (61.16 seconds), including eight pure time/
session cases and the independently persisted HTTP flow. **14 native unit**, **22
offline Compose workflows** (58.532 seconds on Moto g52) and **244 browser JS tests**
pass. Demo/test packages use invented balances and no Internet; new tests verify
blocked Approval has a visible time-aware explanation, quiet readiness transition
without a write, direct setup navigation, failed fresh reads and changed-readiness
409 handling without retry. Existing acknowledgement/duplicate-tap tests still pass.
Reviewed the simulated Approval dialog screenshot. Lint: zero errors / 36 existing
advisories. Ruff, formatting, mypy and whitespace checks pass. Signed APK v3 verification
confirms unchanged certificate/package and no debugging, backup or cleartext traffic.
Physical production installation/publication evidence is recorded separately.

Signed production **1.0.6 / code 7** installed in place on the Moto g52; cold launch
succeeded (884 ms). Package/version are verified and the existing biometric-unlock
screen remains, preserving pairing. Temporary demo/test apps were removed. This is
installation/entry acceptance; the new production Trade flow remains distinct from
the fully simulated UI evidence until the paired app is unlocked against 0.20.6.
APK SHA-256: `2e937a50aaf1cfa61517381c4efe854d511ffdac5abad4ad1c9edda143fc3d4c`.
Published **backend 0.20.6 / Android 1.0.6** on 29 October 2026:
`/opt/agentic-trader/releases/v0.20.6-20261029T063226-ce5c7f2eee46`, Trader PID 38450.
Local/public health, installed/source hashes, live schema-1 mode guidance, Paper-only
capabilities, installer metadata/certificate and downloaded APK hashes are verified.
Live guidance reports action-required with no future entry time while the current
reviewed entry window is open; it does not incorrectly tell the user to wait until
tomorrow. All current server blockers have corresponding explanatory items.
Independent full SQLite comparisons show **both account databases unchanged**; Trader
config/env hashes unchanged. Advisor/Monitor PIDs 1193/1194 retained. Preflight:
`/var/backups/trader-v0.20.6-preflight-20261029T063210Z.json`.
Private acceptance:
`/var/backups/trading-services-v0.20.6-20261029T063226-ce5c7f2eee46/acceptance.json`.
Previous 0.20.5 code is retained; no financial DB was restored. Restart expires phone
sessions and market-data verification/connection; encrypted phone pairing and saved
broker credentials survive. Unlock and use Trade's live Broker & data link for any
required session check/reconnection. No mode or feed is activated automatically.
Production phone installation/entry is verified; the new authenticated tap flow is
covered by the separate simulated Moto UI tests and live server guidance verification,
not claimed as an observed production phone confirmation.

Post-restart read-only Kite profile verification succeeded at
`2026-10-29T06:35:04.899814+00:00` (12:05 IST). The saved access token is available
and verified in this run; another Zerodha sign-in is unnecessary. Feed connection is
still off and Manual remains selected. During the current reviewed entry window,
Trade correctly directs **Connect market data** and **Wait for fresh usable prices**
instead of displaying a future start time. Use **Open Broker & data** → **Connect
paper market data**, review and confirm. This can resume pending fills/protective exits;
it does not choose Approval/Automatic. Broker-check evidence:
`/var/backups/trading-services-v0.20.6-20261029T063226-ce5c7f2eee46/post-deploy-broker-check.json`.

## 29 October 2026 — native branding, stable refresh and environment selector

Android **1.0.5 / code 6**, backend **0.20.5**: selected logo and Agentic Trader name
on the biometric entry page; matching native light splash with reduced-motion-aware
fade; initial branded loading until account data is complete. Fixed recurring Home
flicker by keeping quiet polls out of foreground busy/progress and publishing one
completed snapshot. Stable progress spacing and object reuse reduce layout changes;
new foreground work cancels quiet reads with generation guards. Stale errors remain
visible and actions blocked until recovery. Reviews and dialogs pause polling.

Paper/Real selector shows Paper active and Real unavailable, per the user's chosen
scope. Authenticated GET capabilities expose the actual paper-only backend limitation;
no environment write endpoint or real execution is added. Unexpected non-paper account
responses fail closed. Financial reviews, token storage and biometric policies remain.

Validation: 1,412 Python tests (55.96 seconds), 244 browser JavaScript tests,
eleven native unit tests and seventeen offline Compose UI tests (47.594 seconds)
pass. Native UI tests ran on Moto g52 in separate no-Internet demo/test packages,
using invented balances. Reviewed captured lock, loading and environment screens;
quiet-refresh tests verify stable button bounds/enabled state, no progress indicator,
atomic publication, review cancellation and no account write. Lint: zero errors,
36 existing advisories. Ruff, formatting, mypy and whitespace checks pass. Signed
Android 1.0.5 / code 6 verifies v3 signature, unchanged signing certificate,
no debugging, no backup and no cleartext network. Production publication and physical
biometric acceptance are recorded separately below.

Signed production **1.0.5 / code 6** was installed in place on the Moto g52 and cold
launch succeeded (Android reported COLD, 793 ms activity launch). The existing
**Unlock with biometrics** screen was retained, and its native fingerprint prompt
opened without re-pairing. Subsequently, actual fingerprint unlock showed authenticated
controls and loaded account values without a network/auth error. Temporary offline
demo/test packages were removed. A later extended production refresh observation did
not complete while the app was no longer visible; stable quiet-poll controls/layout
are established by the separate offline UI regressions, not that interrupted capture.
Final APK SHA-256: `8983ab7e9773125871777919247438b48a6ea446d1e7298f0ef45b3aecfd17f7`.

Published and verified **backend 0.20.5 / Android 1.0.5**, 29 October 2026.
Release `/opt/agentic-trader/releases/v0.20.5-20261029T020620-4407a0cfb30a`;
Trader PID 35291. Local/public health, installed/source hashes, paper-only capability,
installer metadata, certificate and downloaded APK hashes all match. Independent
full SQLite logical comparisons found **both account databases unchanged**; private
Trader config/env hashes also match. Advisor/Monitor retain PIDs 1193/1194.
Preflight: `/var/backups/trader-v0.20.5-preflight-20261029T020553Z.json`.
Private acceptance: `/var/backups/trading-services-v0.20.5-20261029T020620-4407a0cfb30a/acceptance.json`.
Previous 0.20.4 release is retained for code-only rollback; no financial DB restoration
was performed. Pairings survive restart; memory-only phone sessions require a new unlock.
Post-restart physical fingerprint/account-load was observed successfully as above.

Actual Zerodha sign-in was also confirmed after deployment: server status reports
`access_token_available: true` and `profile_verified_this_run: true`; latest observed
profile check `2026-10-29T02:11:34.184605+00:00` (07:41 IST). The automatic callback
saved the credential privately; the manual fallback field is intentionally empty.
The user-initiated login updates the broker credential after the earlier deployment
configuration comparison. An independent post-login read again found **both full
financial databases unchanged**. Credential-free evidence:
`/var/backups/trading-services-v0.20.5-20261029T020620-4407a0cfb30a/post-broker-login-acceptance.json`.
This establishes actual callback/profile acceptance, not history entitlement,
streaming connectivity or real-order execution.

## 28 October 2026 — native reuse of recent preparation

Android **1.0.4**, backend **0.20.4**: corrected use of unaudited lightweight status
in daily preparation. Explicit `?audit=true` supplies freshness evidence; matching
valid same-day/same-universe ready or installed data is reused without history reads.
Job identity is checked after audit; concurrent work is shown or rechecked. Explicit
fresh requests, invalid/stale/incomplete evidence and universe changes still acquire
data. UI names the reused download/time and states no candles were downloaded.
All source/policy/calendar reviews and financial authority remain unchanged.

Validation: 1,411 Python, eleven native unit and eleven offline simulated UI tests
pass. The demo tests used a separate no-Internet phone package, removed afterward.
The API regression independently verifies exact persisted cash/full DB contents,
source bytes and provider-call counts across repeated audits. Live source audit
shows the current Nifty 100 download qualifies. The compiled production predicate
accepted the real audited response and rejected unaudited status without a download.
No actual broker history was requested by these checks; saved job/snapshot unchanged.

Signed 1.0.4 / code 5 installed in place on Moto g52; pairing preserved. Published
`v0.20.4-20261028T171417-775c61599b3d`, Trader PID 29643. Public APK/source/installed
hashes verified; both full account DB/config hashes and unrelated PIDs 1193/1194
unchanged. Private versioned backup includes `acceptance.json`. Production-button
acceptance requiring biometric unlock remains distinct from the simulated UI tests.

## 28 October 2026 — supplied Android icon

Android **1.0.3**, backend **0.20.3**: choose the wordless supplied blue/teal growth
artwork for small launcher sizes. Legacy/adaptive density resources, safe foreground
padding, normal/round icons and a separate notification glyph are implemented.
Source art is unchanged; `scripts/build_android_icons.py` regenerates packaged PNGs
with macOS `sips`. This asset-only update retains signing identity and phone pairing.
Actual 1.0.2 biometric login/account load without network error was verified before
this update; idle locking subsequently hid private data. Build/device/publication
validation: ten PNG sizes checked and density preview visually inspected; seven native
unit and 42 focused API/deployment tests pass, release lint zero errors / 36 advisories.
Signed 1.0.3 / code 4 installed and cold-launched on Moto g52; pairing/authenticated
controls retained without network/auth errors. Financial/login policies are unchanged.

Deployed/verified `v0.20.3-20261028T164611-8df9aa2528da`, Trader PID 28798. Public
APK bytes match the signed artifact; both account DB/config hashes and unrelated
service PIDs 1193/1194 unchanged. Private versioned backup contains `acceptance.json`.

## 28 October 2026 — background locking follow-up

Android **1.0.2**, backend **0.20.2**: actual Moto crash stacks identify TLS close
on the UI thread during cancellation/locking. Socket/call cleanup now runs on a
background executor; tokens/private state clear immediately, and a new HTTP client
is installed before retiring the old one. No automatic financial retries or relaxed
TLS/StrictMode policy. Seven native unit tests pass. An opt-in device test exercises
the actual transport's public reads, idle interval, UI cancellation, cleanup completion
and fresh-client read without credentials. It passed on the Moto g52 in a temporary
package compiling the exact transport/test sources; the package was removed. All
1,410 Python, 244 browser UI and seven native unit tests pass; lint has zero errors.
Signed 1.0.2 updated the actual Moto in place and retained its encrypted pairing.
Actual 1.0.2 biometric login/account load without network/auth errors was verified;
later idle locking hid private values. No account instruction sent.

Deployed/verified `v0.20.2-20261028T163249-8e5e7ba037e2`, Trader PID 28144;
public APK bytes match the signed artifact. Both full account DB/config hashes
and Advisor/Monitor PIDs 1193/1194 are unchanged. Private `acceptance.json` recorded
under the matching versioned backup. Broker/history and biometric enrollment-change
acceptance remain external.

## 28 October 2026 — native connection recovery patch

Android **1.0.1**, backend release **0.20.1**. Actual Moto pairing/biometric-encrypted
storage succeeded; an idle pooled connection subsequently failed with `unexpected
end of stream`. A public-endpoint diagnostic reproduced it after 6.5 seconds idle.
The client now evicts idle sockets after one second without enabling mutation retries.
Paired UI state survives session failures once its encrypted credential is saved.
Existing signed installations update in place, retaining the hardware-protected pairing.

Validation: 1,410 Python tests and six Android unit tests pass, including a real local
socket regression verifying new connections and exactly one invented instruction.
Release lint/manifest/signature checks pass. No broker login or financial command
was submitted. Actual phone and deployment evidence will be recorded after verification.

## 28 October 2026 — Android full native companion implemented

Backend **0.20.0**, Android **1.0.0**, native Compose light UI, Android 11+.
The requested browser-feature coverage is implemented through sixteen native
destinations, including research/indicators, all policy draft fields, backtests,
portfolio/SIP and consequential paper controls. [Coverage and use](android-app.md).
One preparation action verifies the session/catalog and current history; login
returns through a phone/nonce-bound server callback and resumes after biometric
unlock. Existing factual source/calendar reviews, previews, accounting and mode
confirmations remain authoritative. No browser content is embedded in a WebView.

Security foundation includes per-phone hashed/revocable credentials, hardware-backed
strong-biometric-bound AES-GCM storage, fifteen-minute memory-only sessions, origin/
scope checks, fixed HTTPS, backup/secure-window/overlay protection, background/idle
locking and best-effort logout. Requests do not silently retry; durable outcome
inspection survives cancelled writes/recreation. Separate offline fixtures have no
Internet permission and cannot authorize production. Public installer delivery is
hash-verified, and the build validates the real APK signature/manifest. The private
signing identity is excluded from deployment and Git. [Component](mobile-api.md).

Validation complete: **1,410 Python + 244 Node UI + 5 Android unit + 7 Android offline
workflow + 2 production negative-security tests**, Ruff/format/mypy/whitespace, release
lint (0 errors; 28 advisory warnings), synthetic screen QA and actual signed APK
installation/cold launch in an isolated API 33 ARM64 emulator. Independent SQLite
reads verify exact fees/cash/fill quantities and duplicate request behavior.

Deployed and verified release `v0.20.0-20261028T152359-e41c1fc957f7`, Trader PID 26277;
public APK matches the signed local artifact. Both full account databases and private
config hashes are unchanged; Advisor/Monitor PIDs 1193/1194 unchanged. Previous code
retained, private `acceptance.json` recorded under its versioned deployment backup.

Actual Moto g52 / Android 13 installation and cold launch were subsequently verified
on 28 October 2026. External acceptance remains: hardware-backed positive biometric
pairing/unlock/enrollment change, app update, broker login and history entitlement.
OS-isolated backtests may remain unavailable on the Pi. No background push, remote
device attestation, security certification, actual market validation or unfinished
investment-engine milestone is asserted. These limits are visible in usage docs/UI.

## 28 October 2026 — 0.19.2: prerequisites, automatic connection feedback and autofill

Strategy download now requires a saved Kite session explicitly verified during the
current server run and current IST date, plus an NSE-token catalog. A prerequisite
panel before the buttons states what is missing and links directly to Broker & Data
steps 3/4. Unknown/stale status disables download. The backend independently refuses
unverified requests before creating a job, files or provider reads. The worker still
rechecks the frozen session; profile failure clears that verification so retry is
blocked until a new explicit check. An older failing worker cannot revoke a newer
successful verification. Profile success does not establish historical entitlement.

Broker & Data polls local setup status every three seconds while a feed is requested
and the tab is visible/unlocked, skipping pending requests and confirmations. It shows
connecting/retrying, connected success or a fixed failure/recovery reason beside the
buttons; network errors mark status stale and the next check can recover. Polling uses
GET only, preserves edited/cleared inputs and session-action feedback, and discards late
responses after Lock/pagehide. It also reconciles an uncertain Connect result without
repeating that action. Streaming worker retry limits and trading safeguards are unchanged.

The shared unlock form now supports password-manager autofill with username `operator`
and the operator token as the password. The app retains tab-memory-only access; saving
and autofill remain under the browser/password manager's control. Hosted Kite setup uses
`https://shanmukhan.com/agentic-trader/` as the exact registered redirect URL. Developer
console: `https://developers.kite.trade/apps`; API base: `https://api.kite.trade`.

Validation: **1,400 Python tests and 242 Node UI tests passed**, plus Ruff lint/
format, mypy, secret-pattern and whitespace checks. Added unit/functional coverage
for missing/prior-day/future verification, missing tokens/catalog, no job/provider
reads before verification, profile-failure revocation and a newer-check race. Synthetic
API polling and failed-prerequisite/recovery tests independently preserve full SQLite
contents and exact ₹25,000.00 cash. UI tests cover state transitions, hidden/locked/
confirmation/overlap guards, uncertain Connect reconciliation, stale recovery, form
preservation and password-manager markup. Labeled desktop previews were inspected;
mobile password-manager, broker, real-market and handset acceptance remain separate.

Deployed after renewed sudo authorization as
`v0.19.2-20261028T032717-5b4caa55c9b5`; Trader PID 19373. Public/local health
report 0.19.2; source/installed hashes and public prerequisite/autorefresh/autofill
assets passed verification. Independent integrity/full logical-state comparisons
found both account databases unchanged, and Trader private config hashes matched.
Advisor/Monitor retained PIDs 1193/1194. Private rollback and `acceptance.json`:
`/var/backups/trading-services-v0.19.2-20261028T032717-5b4caa55c9b5`.
A one-time workspace reload loads the new scripts; subsequent connection status
updates are automatic. Restart clears in-memory broker verification/feed authority;
check the saved session and explicitly reconnect when ready.

## 28 October 2026 — backend release 0.19.1 and scoped Pi updates

Version **0.19.1** includes the strategy-download feedback and broker-verification
stage fix described below. Package, source and lock versions match. `/health` now
returns the running backend `version` alongside paper/alive status. Deployment
manifests include each project's declared version, Git base and exact file hashes;
new release directories use `vVERSION-UTC_TIMESTAMP-MANIFEST_HASH`.

Added `bash deployment/rpi/deploy.sh USER@PI --trader-only` for an existing Trader
installation. It packages only Trader, prepares dependencies before stopping it,
backs up its state privately, switches to a fresh release and requires the new
health version to match. Advisor, monitor registration and other app state are
excluded from this update. Failure after switching restores prior code/service
configuration and starts the prior service; financial databases are never restored
automatically. The existing combined deploy command remains available. Backend
versioning is recorded as a standing instruction in `AGENTS.md`.

Validation: **1,392 Python tests and 236 Node UI tests passed**, plus Ruff
lint/format, mypy, secret-pattern and whitespace checks. Deployment tests cover
matching source/project/lock versions, code-only Trader-only manifests, unsafe-version
refusal and an isolated SSH/SCP CLI workflow. These tests use invented local fixtures.

Deployed to `lipi@192.168.1.13` as
`v0.19.1-20261028T030028-773cf72602db`; only Trader restarted (PID 16781).
Local and public HTTPS health report **0.19.1**, installed/source hashes match and
public strategy/setup assets passed checks. Independent read-only integrity and full
logical-state comparisons found both Trader and Advisor SQLite databases unchanged;
Trader env/calendar/config hashes also match. Advisor PID 1193 and Monitor PID 1194
were retained. Private rollback/evidence:
`/var/backups/trading-services-v0.19.1-20261028T030028-773cf72602db`, including
`acceptance.json`; the prior release remains available. This proves deployment and
state preservation, not a repaired broker session or market/device acceptance.
The narrow Firefox screenshot was a temporary local layout preview; production
continues to use its existing responsive full-width desktop layout.

## 28 October 2026 — make strategy-download failures visible at the action

Strategies now shows a bordered, tinted **Download failed — action needed** alert
immediately below the download buttons, with the reason and a direct Broker & Data
step-3 link for session/history failures. The original summary badge remains secondary.
Screen-reader alert semantics, an underlined keyboard-accessible recovery link, wrapping
text and existing responsive columns preserve access without relying on color alone.
Failed/cancelled/interrupted jobs no longer claim an active source read or show an
active progress bar. Retry remains explicit and confirmed; partial stock counts remain
visible. Running pre-history reads use indeterminate progress. The worker now records
`broker_session` before profile verification and `official_sources` only after success.
No credentials are refreshed automatically and no installation or trading mode is
activated by failure/retry feedback.

Validation: **236 Node UI tests and 34 focused Python tests passed**. Added checks for
inline alert placement, failure/retry/Lock transitions, legacy failed jobs, accurate
worker stages and a failed-session → explicit-retry API workflow. Independently read
SQLite state and exact ₹25,000.00 cash remained unchanged throughout the synthetic
failure/recovery workflow. A local Firefox preview using invented failed-job status
was visually inspected at desktop and narrow content widths; this is not broker,
real-market or physical handset acceptance. The UI and backend stage change are included in deployed release **0.19.1** above.
The original 270 focused checks were followed by the complete release checks.
See [preparation recovery](strategy-preparation.md#download-failure-and-retry).

## 27 October 2026 — default NSE review-reference URL

Pre-commit validation for the complete Pi/browser/token/default-reference change:
**1,387 Python tests and 234 Node UI tests passed**, plus Ruff lint/format, mypy,
secret-pattern and whitespace checks. Normalized Python examples in the existing
backend roadmap to satisfy the repository's required formatting check; no example
behavior was changed. Advisor's 42 tests and six Pi-setup infrastructure tests also
passed, with all Apache templates rendering successfully.

Broker & Data → step 5 now prefills the reference with the official NSE holidays/
exchange-notices URL on the first successful unlock, alongside the existing normal
hours. The reference remains editable; refresh preserves edits and intentional
clearing. Lock clears the field and a fresh unlock restores the suggestion. Its
accessible help explains that a URL is a starting reference, not a calendar check.
The review checkbox stays unchecked; the existing confirmation and server-side
attestation guard remain required. No session is saved simply by unlocking, refreshing
or showing the suggested URL.

Validation: **234 Node UI tests and 33 focused Python functional tests passed**.
Checks cover initial defaults, edit/clear preservation, Lock/unlock, confirmation/
cancellation and the submitted default reference. Functional tests reject unchecked
review and independently verify exact ₹25,000.00 cash/full SQLite state remains
unchanged while the reviewed calendar stores the reference. These are synthetic
workflow tests, not a real-date/NSE calendar approval. Published on the Pi at 20:54:06 IST without a service restart (PID 26035 unchanged).
Public asset checks passed, no calendar/account files were written and independent
financial-state hashes were unchanged. Private rollback copies and separate
base-release patch metadata are recorded in the [browser runbook](public-browser-access.md).

## 26 October 2026 — recover service startup after a weak operator token

Diagnosed the real Pi startup loop as the Settings token minimum: both local and
Pi values were 11 characters. The app requires at least 32; the helper's URL-safe
validation correctly rejected the local input before sending it. Retained that
requirement and added explicit `--generate` to create a 43-character cryptographic
replacement, privately back up/update local `.env`, and sync only the token to the Pi.
Changed or inactive units now have their failed-start limit reset before restart;
a matching healthy unit remains running. No generated token is printed or put on argv.

Recovered the actual Pi service and authenticated HTTPS read (200). Both credential
files have the strong replacement, with private local/Pi backups. Independent SQLite
integrity and before/after financial state checks passed; a healthy repeat was a no-op.
**42 focused tests passed**, covering generation/CLI secret boundaries, local-config
preservation, reset-before-restart and inactive-unit recovery, old-value repair and
exact persisted cash/ledger checks. See [commands, paths, retries and limits](public-browser-access.md).
Startup/access validation does not establish broker/market/handset acceptance.

## 25 October 2026 — allow valid token replacement when the Pi value is invalid

Fixed a sync failure after incoming-token validation: the old Pi value was also
being subjected to the new-token URL-safe/length restriction. A single existing
assignment can now be replaced even when its old value is empty, short, contains
punctuation or has broken quoting; its original bytes remain in a root-private
backup. Invalid new values, duplicate/missing target assignments and symlinks are
still refused. Remote update failures and CLI SSH failures now produce concise
messages instead of dumping a traceback and embedded remote source.

Validation: **38 focused tests passed**, including separate-process execution of
the generated remote program against five old-value cases, private backup and
unrelated-config preservation, duplicate refusal, secret transport and isolated CLI
failure. Repaired the actual Pi credential using the user's current `.env` value;
authenticated public read returned **200**. Independent SQLite integrity and financial
state hashes remained unchanged. See [usage, recovery and private evidence paths](public-browser-access.md).
This validates access, not broker/market/handset/power-loss acceptance.

## 25 October 2026 — correct Pi operator-token mismatch and guidance

Confirmed the workstation `.env` and Pi env contained different operator tokens:
local token returned HTTP 401 while the running Pi token returned 200. Explicitly
synchronized only the workstation operator token over SSH stdin, preserved a private
backup and restarted Trader. Authenticated public workspace read then returned 200.
No broker credentials or account data were copied.

Added `deployment/rpi/sync_operator_token.py` for an explicit, validated token-only
workflow with private atomic replacement, idempotent file handling and HTTPS read
verification. The workspace label, help and rejection message now identify the
hosting server instead of suggesting any workstation `.env` must work remotely.
See [usage and failure/recovery behavior](public-browser-access.md#operator-token-belongs-to-the-server-hosting-the-page).

Validation: 32 focused token-sync/public-hosting tests and all 233 Node UI tests
passed; checks cover parsing/rejection, backup permissions, unrelated configuration
preservation, secret-free argv, remote-script compilation, token reload rejection
and independent SQLite/Decimal cash/ledger invariance. Real Pi authentication was
verified without displaying either token; a repeated sync returned a no-op and 200.
Deployed release `20261025T173439-293e424fcefc` serves the corrected help. Independent
before/after financial-state hashes and DB integrity remained unchanged/passing. This is access validation, not broker,
real-market or physical-device acceptance.

## 25 October 2026 — shanmukhan.com Investing browser profile

Implemented an Investing home-page tab and exact HTTPS paths for Trader and Advisor
through the existing shared Apache vhost. Trader gains validated optional public
host/origin/prefix settings, bundled known-route asset URL adaptation and loopback-only
forwarded-header trust. Transport fields are excluded from economic fingerprints;
Bearer/Origin guards remain. Advisor uses its Streamlit base path, explicit origin
and host checks, WebSocket proxy support, and browser Basic login checked against
an Argon2-only snapshot of the existing monitor identity. Credential headers are
removed before proxying; private path access-log suppression and web rollback preserve
existing routes and account state. The normal app installer preserves public settings
and uses the correct prefixed Advisor health URL. Reviewed new Trader source modules
can now be bundled before commit, while account/sample state stays excluded.

Local validation: **1,364 Python tests**, **232 existing Node UI tests plus one new
prefixed controller test**, six infrastructure/auth/navigation/environment checks, Ruff, mypy
on 126 source files and shell syntax checks passed. Financial checks independently
inspect SQLite using Decimal and assert unchanged policy identities. Public deployment completed with valid Apache/systemd configuration, expected HTTPS
pages/login challenges and a synthetic isolated authenticated WebSocket upgrade.
Independent database-state hashes stayed unchanged; the existing home/monitor
routes and the two requested app services passed. A separate pre-publish Netrava
identity/relay failure is recorded in the browser runbook. The initial multiple-value environment parsing issue was
corrected with native whitespace-separated values and a regression check. Exact
backups, checks and acceptance limits are in [the browser runbook](public-browser-access.md);
synthetic checks do not establish broker, handset, power-loss or profitability acceptance.

## 25 October 2026 — deployed Raspberry Pi services and mobile monitoring

Added code-only, hash-manifest packaging and a shared release installer for
Agentic Trader plus the confirmed sibling Portfolio Advisor project. Both run as
dedicated users with root-owned code, persistent private state, localhost:8010/8501,
boot enablement and restart-on-failure. Preparation precedes downtime; failed health
or monitor updates restore prior code/units/monitor configuration while retaining
financial state. Existing monitor mappings are extended using the deployed renderer
and exact polkit grants; no local unrelated monitor edits, public routes or
workstation credentials/accounts are deployed. Advisor supports a private persistent
`ADVISOR_ENV_FILE`; its lockfile no longer embeds a Mac editable path.

Validation: **28 focused Trader tests and all 42 Advisor tests passed**, including
code-only bundle hashes/secret exclusion, monitor conflicts/partial-write recovery,
separate account processes and independent persisted SQLite/Decimal checks. Ruff,
shell syntax and whitespace checks passed. Deployed release
`20261025T151902-a2cbb050bbd8` is enabled and healthy on the real aarch64 Pi; systemd
unit verification and an actual controlled app restart passed. Trader retained
**₹25,000.00 virtual cash**, no orders/fills/positions; Advisor retained one demo
report and no purchases. Both independent DB integrity checks passed. Deployed
monitor service-list provider and its unprivileged polkit start permission checks
passed. Pi-side Advisor UI harness rendered without errors using **demo data**.

Trader readiness remains 503 pending explicit broker/session/calendar setup. Mobile
entries need refresh, no rebuild; the current service buttons act immediately without
separate confirmation. Physical phone taps, reboot/power-loss and real-market/broker
acceptance remain unperformed. See [commands, private access, exact device evidence,
limitations and recovery](raspberry-pi.md). Existing Streamlit width deprecations remain.

## 25 October 2026 — audit fixes and clearer paper workflows

Reviewed every numbered finding in `PROJECT_AUDIT_2026-10-25.md`; the
[audit resolution](audit-2026-10-25-resolution.md) distinguishes implemented fixes,
incorrect absence claims and source/contract-dependent work. Added an owned,
prioritized [roadmap](ROADMAP.md) without promoting unavailable features to execution.

Analysis adds exact touch/pointer/keyboard inspection, responsive readable candle
widths, larger volume, date labels, SMA swatches and optional saved RSI/MACD/ATR
panels. Backtesting draws fresh-only equity/drawdown/compatible-report overlays,
retaining exact tables and stale gaps. Portfolio adds available-weight allocation
and fresh complete P&L summaries; decimal/exponent sign/order and numeric rank
handling retain exact labels. No historical return or prior-close trend is invented.

Consolidated canonical CSS before responsive/theme overrides, added system dark mode,
reduced-motion loading, named/consistent access forms, static history guidance,
formatted HTML, assertive error regions and dismissible current-frame action feedback.
Visible Lock guidance and cleanup retain in-memory access only. Alt+R focuses a
proposal review without approving. Shared confirmations capture reviewed callbacks
and revoke them on cancellation/failure/Lock; page-specific authority checks remain.

Backend adds authenticated ledger-free feed observation, committed receipt-age cache,
bounded historical 429/503 retries, watchdog tracebacks, shared safe sell invariants
and strict stream identities. Gap-through-stop exits remain allowed. Intraday zero
and derived delivery fee buffers now serialize consistently as exact decimal strings.
ML readable reports add descriptive standardized/calibrated coefficients without
changing strict artifacts, chronological folds, purging or final holdout selection.

Validation: **1,335 Python tests and 232 Node UI tests passed**; **92.06% statement
coverage** (11,151/12,113), Ruff lint/format, mypy on 125 files, secret-pattern and
whitespace checks passed. Financial tests use independent SQLite reads/exhaustive
Decimal oracles, including 800 generated sizing cases, exact gap-exit fees,
cross-horizon fee-buffer contracts, supervisor loop persistence and ML artifact checks.
The full run emitted **52 SQLite ResourceWarnings** in existing test paths; resource
lifecycle remains separately reviewable.

Desktop Firefox verified disposable synthetic Dashboard/Portfolio values and accessible
visual labels. An independent full SQLite dump stayed unchanged: cash ₹20,495.23,
three orders/fills/positions, 27 events and no pending orders. Other charts/theme/narrow
behavior have automated checks; complete rendered dark/narrow/chart interaction and
physical-device/broker/native-worker acceptance remain open. The fixture server was
stopped. No user account, broker order or trading-mode change was performed.

## 24 October 2026 — issue-report reliability fixes

Revalidated `PROJECT_ISSUES_GAPS_AND_IMPROVEMENTS.md` against 0.19.0 rather than its
historical 0.14.0 references. Its current-code matrix covers every numbered finding
and corrects obsolete absence claims without promoting draft/planning features into
execution capabilities.

Implemented configured 1–3,000 full-depth stream capacity (default ten), bounded
subscription/frame handling, expanded feed initialization/history bounds and unchanged
economic policy identities. Manual setup consumes decoded frame batches: all accepted
quote/audit events and every per-quote risk/fill check remain, with one transaction per
frame, per-quote live clock sampling and rollback revoking frame trust. Complete quote evidence remains required for
corporate-action reconciliation and causal exports. The automated controller retains
its per-quote callback cadence. Query-only independent WAL readers remove writer
reservation from account/console/order/readiness/proposal metadata reads; combined
memory/ledger views still serialize on the engine lock.

Replaced regex configuration mutation with round-trip `tomlkit`, retaining complete
schema/economic-policy checks and private atomic file replacement. Shared lazy
POSIX/Windows advisory locking covers account/auxiliary stores without asserting
native Windows app acceptance. Added a bounded authenticated read-only proposal-alert
resource, workspace-wide count/title/deadline, opt-in desktop notifications and clear
expiry/stale/error/lock behavior, plus actionable cited blocker guidance. Countdown
updates do not continuously announce through the live status region.

See [persistence and recovery](quote-persistence.md), [capacity](paper-feed.md),
[configuration](ui-setup.md) and [alerts](trading-desk.md) for commands/inputs/results.
Validation: **1,292 Python / 202 Node UI tests passed**, with **91.98% statement
coverage**, Ruff lint/format, mypy and offline dependency-lock checks passing. Details
and resource-warning/platform limitations are in [test-plan.md](test-plan.md).
Synthetic unit/functional tests independently inspect persisted monetary state;
rendered Firefox desktop/narrow checks use a disposable invented account.

Remaining work is explicit: single-writer/engine contention and journal growth;
sustained large-universe real feeds; executable months/years/trailing/rebalance
policies and integrated multi-year validation; licensed PIT fundamentals and portfolio
concentration models; SPA/push/advanced charts; credential-store/session migration;
reviewed circuit-band inputs; native OS/device/market acceptance. No live execution,
headless login or automatic clearing of financial/runtime faults was added.

## Daily operations automation (23 October 2026)

Reviewed the supplied [findings](agentic-trader-checklist-review-and-findings.html)
against code. Existing server watchdog, exact ledger/authorization reconciliation,
guided setup checkpoints, two-minute binding and restart-to-Manual remain in use.
Added `operations/` for consolidated read-only evidence, independent loopback monitoring,
opt-in IST acquisition and source-preserving backup/drills. See [the component guide](operations-automation.md).

`/api/operations` separates service/account/broker observation times, calendar,
mappings/held subscriptions, current reviews, quote quality, order/exit residue and
current authority. Audits check source hashes/date/per-symbol session coverage and a
separate read-only accounting snapshot. The external supervisor records local alert
and recovery transitions, five-minute audits and observed daily reports. Acquisition
requires explicit opt-in, a reviewed current session, Manual, account/order/catalog
and broker preflight. Supervisor/server checkpoints precede ambiguous I/O; repeats
reconcile known attempts or stop for review. No setup confirmation, review attestation,
feed connection, order or mode activation is automated.

Stopped-owner packages use the advisory lock and SQLite backup API without constructing
Database/PaperBroker. They preserve pending state and verify the copied ledger plus
referenced config/calendar/installed data/source/model files before manifest publication.
An isolated drill verifies hashes/accounting without rebinding paths or starting a service.
Private CLI commands, launcher and inactive launchd/systemd templates are supplied.

Validation: **1,248 Python / 193 UI tests**, Ruff lint/format, mypy, shell syntax and
plist validation passed. Unit/functional evidence includes source corruption/freshness,
auth/origin, repeated/unknown attempts, monitoring faults, exact partial/full/rejected/
cancelled-order backups, installed artifacts, disk failure and isolated restoration.
See [test-plan.md](test-plan.md). Real broker/market/device/power-loss/service-manager
acceptance, remote alerts, encrypted off-device replication and full relocated startup
remain separate. Interrupted setup still stops for explicit review; no automatic
rollback/resumption or broader trading authority is claimed. Phase 5 remains unchanged.

## Daily operator documentation (23 October 2026)

Added [a complete daily operator checklist](daily-operator-checklist.md) explaining
the strategy-data bundle, current-IST-day guided setup requirement, immutable saved
history, valid same-day reuse and new-completed-session refresh. Separates initial,
daily and conditional work; covers broker renewal, Manual preparation, source/calendar
and shortlist review, held-symbol basis exceptions, feed/quote readiness, independent
mode activation, proposals/SIP, supervision, horizon-specific closing and account-bound
reports/verification/backups. Linked the checklist from usage, preparation and runbook.

Validation: documentation/source consistency review and **128 local Markdown links
checked across six files**, including launcher/config selection, preparation/guided freshness checks,
desk mode/readiness and CLI report/backup ordering. Official Kite authentication and
historical-candle references were checked. No runtime, financial policy or workflow
implementation changed; no broker/account actions or real-market/device acceptance
were performed. Existing implementation milestones remain unchanged.

## Workspace usability pass (0.19.0, 23 October 2026)

Reviewed the existing Dashboard, Portfolio, Analysis, Broker, Backtesting and Risk
interfaces for repeated explanation, status hierarchy, icon consistency and narrow
layouts. Added a local SVG sprite with text-labelled navigation/action/section icons,
a compact header, a collapsible setup explanation with its current next step visible,
shorter routine saved-view feedback, folded valuation definitions and grouped chart
help/legend. Timestamp, stale/incomplete evidence, exact decimals, authorization and
financial confirmation semantics remain unchanged.

The policy-draft screen now presents its existing four parameter groups as explicit
steps with progress, Previous group/Next group, contextual unit help and field-linked validation.
Navigation does not save, preselect financial inputs or grant execution authority.
Existing reviewed preview/save, immutable snapshots, unsaved-change/uncertain-outcome
guards and lock privacy remain. See [the detailed interface guide](ui-experience.md)
and [validation scope](test-plan.md). Automated/local rendered evidence must remain
distinct from sustained broker, real-market and target-device acceptance.

**Validation:** 1,216 Python / 193 UI tests passed, 92.13% statement coverage;
Ruff lint, source/test format and mypy passed. A disposable desktop Firefox check
covered icons, policy groups/validation/deep-scroll review/Escape, Portfolio warnings
and Risk grouping. Independent SQL retained unchanged empty-account accounting.
See [the full evidence and limits](test-plan.md).

This is a usability refinement, not completion of Phase 5. Native-worker acceptance,
new investment execution/backtest adapters, connected parity, OOS/walk-forward,
portfolio benchmark and target/rebalance remain pending.

## V2 Phase 5 policy-draft planning slice (0.18.0, 23 October 2026)

Implemented a separate schema-1 nullable policy specification with both months/years
and monthly/quarterly options, exact decimal strings, explicit choice metadata, coupled
allocation limits and versioned semantic identity. No financial defaults are selected;
incomplete drafts retain missing fields. A complete draft is `specified`, never active,
and has no investment execution/backtest adapter. Existing legacy identities remain
separate.

The Strategies subview `#strategies/investment-policy` provides a blank four-group form,
exact server preview, explicit acknowledgement, immutable snapshot save and editing a
copy. Private storage is separate from the operator ledger; read/preview creates no
storage, saved identities are revalidated, repeated reviewed content is idempotent,
and unsafe/corrupt evidence fails closed. Unsaved/uncertain state guards navigation;
unknown outcomes require reading saved evidence before a separately reviewed retry.

The pure schedule preview and `investment-policy DRAFT_JSON` CLI support explicitly
declared calendars, month/year anniversary clamping and monthly/quarterly full-period
coverage. They print planning evidence without saving/installing a calendar, opening an
account, scheduling execution or changing holdings. Missing/future-known evidence and
the 400-cycle budget stay explicit unavailable states. Calendar completeness is the
operator's unverified assertion; dates are not promised exchange openings or minimum
holding/profitability guarantees.

Integrated validation: **1,213 Python / 186 UI tests**, **92.13% statement coverage**,
Ruff/format/mypy passed. A disposable Firefox workflow covered explicit choices,
deep-scroll review/Escape/save, persisted snapshot reload and the preserved strategy
setup; independent private JSON/SQL checks confirmed unchanged virtual accounting.
The contract's 132 unit cases pass; schedule/store/API/CLI/UI integration evidence is
recorded in [test-plan.md](test-plan.md). See [the detailed usage/component guide](investment-policy-drafts.md)
for exact inputs, expected results and recovery. Local/synthetic checks remain distinct
from rendered browser/device, native worker, real-market and investment execution acceptance.

**Phase 5 remains incomplete.** No new policy activation/execution/replay adapter,
connected parity, OOS/walk-forward, target allocation/rebalance or full real-platform
acceptance is supplied. The 0.17 native-worker capability remains unavailable on this
Mac. Next implementation must preserve these boundaries while adding separately
specified and tested execution/data/performance behavior; a saved draft is no authority.

## Historical 0.17 integration evidence

Final 0.17 integration evidence: **958 Python / 172 UI tests**, **91.87% statement
coverage**, Ruff/mypy (113 files) passed. Resource identities bind implementation and
observed fee assumptions; changes require registration/review again. A disposable
synthetic desktop Firefox smoke check covered input selection, disabled runtime launch
and the allocation view. It does not close the native-worker, device or full Phase 5 gates.

## V2 Phase 5 first implementation slice (0.17.0, 22 October 2026)

Added `research_jobs/`: CLI-only immutable input registration, one-worker/one-queue
admission, resource/hash-bound idempotency, durable job/cancel/restart states and verified
bounded report publication. `/api/backtests/*` authenticates existing local operator
access; browser mutations require explicit acknowledgement, with no path/upload/model
execution input. Workers get a separate scratch ledger, an allowlisted environment,
Darwin OS sandbox and verified hard budgets. The UI reviews policy/source/holding cap,
retains failed/cancelled/interrupted states, reconciles uncertain submissions using the
same request key and compares only identical registered resources/methods.

Runtime launch fails closed. On this Mac the hard 2 GiB address-space limit could not
be set and the Codex sandbox denied the native sandbox probe. Actual isolated-worker
acceptance is open; Linux/Pi browser jobs have no implemented backend. Read/registration
and simulated lifecycle tests are not substitutes for that gate. Actual budgets are
60 s wall/30 s CPU, 2 GiB address space, 32 MiB combined input/individual output,
128 MiB combined output, 64 KiB log, 100,000 rows, ten symbols/252 replay sessions,
100 retained jobs and 32 registered resources. No automatic cleanup/resume is supplied.

Added pure `portfolio_metrics` and daily-cut `performance` contracts with private
34-digit Decimal arithmetic. Portfolio exposes exact actual-cash/current-accepted-bid
whole-share allocation; receivables/fractional claims are excluded consistently and
reservations/buffers/pending orders remain separately labelled commitments. Missing,
stale, unreviewed or incomplete held evidence disables weights without cost fallback.
The read does not mutate account state. Daily metrics require explicit baseline,
reviewed daily cuts/calendar, known-zero flows and sufficient samples/assumptions.
Existing accounts and event-time replay curves do not supply that history, so their
CAGR/Sharpe/Sortino/monthly-return suite remains unavailable rather than inferred.

This is **partial Phase 5**, not acceptance of the full investment product. Registered
browser runs reuse legacy offline rules (default 20-session holding cap); connected
parity, new months-to-years policies, OOS/walk-forward browser orchestration, portfolio
benchmark returns, target allocation/rebalancing and real-platform acceptance remain
open. The user requested both months/multi-year horizons and monthly/quarterly reviews;
future configuration must support those options, but no concrete active policy was
selected. No operator account, mode, broker credential or real order was changed.

See [browser commands, limits and recovery](browser-backtesting.md) and
[allocation/performance definitions](portfolio-analytics.md). Final integrated automated
validation is recorded in [test-plan.md](test-plan.md); rendered desktop/mobile,
sustained broker/device, source licensing and profitability acceptance remain separate.

## V2 Phase 4 price research implemented (0.16.0, 22 October 2026)

The user authorized the next planned phase. Added `investment_research/` with
34-significant-digit Decimal indicators, gap/membership/availability segmentation,
coherent known-share-action OHLC/inverse-volume adjustment, a separate gross TRI,
explicit reviewed weekly/monthly aggregation and a bounded local benchmark adapter.
Fifteen indicators expose definitions, warmup, value/null, basis and availability.
Future data and incomplete periods never become invented bars or zero-filled metrics.
Benchmark comparison requires compatible declared gross INR sources and matched daily
coverage; source/license declarations and calendar reviews remain unverified assertions.

Added authenticated pure `GET /api/research/series` and isolated `investment-analyze`
reports. Legacy `/api/analysis` raw daily/minute meanings, strategy/ML/risk identities
and paper authorization are preserved. The UI supports daily/weekly/monthly research,
exact indicator/evidence tables, gap-safe SMA overlays and a display-only 50/100/all
range control. Discovery explains actual legacy filters/thresholds/ties without
reranking. No user account, watchlist, credential, review, holding or server was changed.

Validation: **828 Python tests passed**, **157 UI tests passed**, **92.38%** statement
coverage (9,066/9,814); Ruff, changed-Python format, mypy on 104 source files, limited
secret patterns and whitespace checks passed. New suites include 26 indicator,
34 series, 59 benchmark, 23 ranking and 16 functional API/CLI tests. Arithmetic uses
independent Fraction/Decimal references. HTTP reads past expiry/day rollover preserve
whole SQLite dumps, exact partial-fill cash/basis/fees/reservations and mode/revision;
failures sanitize 503 without financial fault recovery. CLI tests deny socket access,
prove no account/lock/WAL creation and independently hash private completed outputs.
Legacy raw split charts and full-history warmup before 300-bar display clipping are
covered. UI checks include exact strings, warmup, calendar/benchmark gaps, inert
research actions, range-only redraw and lock/late-response privacy.

See [usage, schemas and recovery](investment-research.md). Licensed fundamentals,
new investment policies, multi-year acquisition, browser backtest jobs, portfolio
return/benchmark/allocation analytics and operational acceptance remain future work.
Existing preparation still supplies 60 sessions from its supported current-year
source: longer research needs an explicitly reviewed longer bundle. Full rendered
browser/mobile/device and sustained real-feed acceptance remain open; tests are
synthetic/local evidence and establish no profitability or provider entitlement.
The coverage run still emits SQLite ResourceWarnings in test workflows; cleanup
remains a reliability finding rather than proof of a production leak.


## V2 Phase 3 frontend slice implemented (0.15.0, 22 October 2026)

The user requested the next implementation phase after Phase 2. Implemented shared
native confirmation geometry/focus/cancel lifecycle across Setup, Risk, Purchases,
strategy and mode/trade reviews; twelve grouped destinations with a compact mobile
menu and preserved legacy aliases; read-only Dashboard, Stock Discovery/comparison,
Portfolio and Settings; CLI-only Backtesting guidance and searchable Learning Center.
Paper Trading now owns readiness/modes/proposals; Trade History retains orders/fills.
Purchases/SIP/aggregate exits remain accessible through guarded Portfolio subviews.

`GET /api/workspace/views` uses a separately closed SQLite read-only connection under
the engine lock and returns bounded saved facts/decimal strings. It does not tick,
expire, refresh, poll, download or reconcile. Tests independently reconstruct persisted
fill/cash/basis/fee/reservation values and prove whole-database/mode/revision equality
for reads past accounting-day/proposal-expiry boundaries. Missing fundamentals, jobs,
return/benchmark and allocation engines remain unavailable; no new investment strategy
or broker recovery behavior was installed. Risk and intraday semantics are preserved.

Validation: 670 Python tests, 148 Node UI tests, 92.20% statement coverage
(8,405/9,116), Ruff and mypy (99 source files) passed. Simulated geometry covers
360/768/1440px, deep scroll, visual viewport zoom/keyboard offsets, scale/borders,
long content, focus, Escape/cancel/late close and cleanup. HTTP/DOM checks cover all
routes, labels, framing/privacy, exact rendering, comparisons and late-response locks.
A disposable read-only preview opened the locked shell in Firefox; interactive
verification was interrupted by user browser activity. Rendered keyboard/touch/mobile/
200% zoom/second-engine and sustained broker/device acceptance are **not complete**.
SQLite ResourceWarnings remain test-workflow cleanup findings, not new prod-leak proof.

See [implemented component scope and recovery](frontend-modernization.md). Frontend
code is delivered incrementally; the Phase 3 rendered acceptance gate stays open.
Phases 4–6 research/job/reliability expansion remain future work. No user account,
credential, watchlist, holding or server process was changed by implementation testing.


## Phase 2 architecture and UX design completed (22 October 2026)

The user's post-audit approval covered Phase 2. Delivered the
[design package](phase-2/README.md): modular-monolith/authority/migration decisions,
additive API/job contracts, grouped twelve-destination navigation and aliases,
all screen/shared-component states, light visual system, financial definitions and
synthetic examples, legacy/new policy parity/data contracts, and fix-first acceptance.
The [offline prototype](phase-2/prototype.html) has no account/network/storage or
financial results. Proposed runtime behavior remains explicitly unimplemented.

Validation: 6 simulated prototype tests passed; 12 destinations/15 proposed strategy
vectors/11 contrast pairs/document links/HTML labels/structure/offline boundaries passed;
129 independent arithmetic/contract comparisons over 7 synthetic ledger cases and 2
return paths passed. Ruff/format and whitespace checks passed. Financial examples are
design evidence, not persisted-account or strategy acceptance. Runtime source, tests,
configuration and version were unchanged; the full Phase 1 suite was not rerun.
Browser layout, broker/device acceptance, licensed sources and complete investment
parameters remain future gates. Phase 3 starts with the shared confirmation helper,
rendered regression tests and grouped navigation, retaining existing safeguards.


## V2 audit approval boundary (22 October 2026)

Phase 1 requested in `improvements.txt` is documented in [ARCHITECTURE_AUDIT.md](ARCHITECTURE_AUDIT.md),
[UX_AUDIT.md](UX_AUDIT.md), [GAP_ANALYSIS.md](GAP_ANALYSIS.md) and the distinct new
[IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md). The uppercase/underscore plan is the
V2 proposal; this file remains the historical implemented-status record. Current
0.14.0 is the audit baseline, not completion of the requested months-to-years product.
No application code or operator account was changed during Phase 1. Existing setup
modal code was assessed with a disposable geometry harness; rendered acceptance is
still required. Fresh validation: 660 Python tests/92.13% statement coverage, 117 UI
DOM tests, Ruff, mypy (98 modules), and limited project secret patterns passed.
The coverage run emitted unclosed SQLite connection warnings in test workflows;
resource cleanup and rendered/strategy-parity tests are audit findings.

The new plan prioritizes confirmation visibility, reviewed cross-year calendar input,
connected/replay strategy semantics, data provenance/recovery and investment workflows.
It preserves current functionality, exact paper accounting and independent risk gates;
no live order support is proposed. Intraday changes remain deferred except a separately
reviewed correctness issue. That Phase 1 approval boundary was satisfied by the later Phase 2 and Phase 3 instructions; it is not a current stop instruction.


## Light workspace and real saved-data analysis (0.14.0, 22 October 2026)

Implemented the supplied light/sidebar direction using the existing self-hosted
HTML/JavaScript architecture. Six main areas have distinct entry points; a secondary
purchase/SIP link and contextual onboarding retain existing capabilities. Dashboard
shows server-decimal account estimates, dated daily P&L, position count, valuation
limits, market status, next action, proposal queue and confirmed operating modes.
Strategy preparation and shortlist move to `/strategies` without changing installation,
review or trading authority. Legacy desk fragments migrate through the guarded shell.
Risk Center prioritizes emergency/entry controls and basis reviews; broker and feed
administration remains separate. Broker steps use native keyboard disclosures and
explicit navigation while preserving confirmation and first-unlock default hours.

`api/analysis.py` adds a bounded, authenticated, side-effect-free saved-data view.
Installed reviewed daily data is checked for integrity and availability; saved
completed minute candles exclude gaps, unknown volume and incomplete bars. Return at
most 300 display bars, calculate Decimal SMA 20/50 before display truncation, expose
raw OHLC/source limitations and separate existing quote usability. The SVG is a visual
approximation with exact accessible table data; no broker requests or order controls.
Minute provenance is unknown because it is absent from persisted Candle records.

No framework or external asset dependency was added. The existing same-origin section
frames remain; native scroll fallback is retained for documents over the bounded
height. No graphical backtest, arbitrary strategy builder, notification permission,
financial policy editor or real-order capability was invented. Existing CLI research
and financial actions retain their reviewed workflows. Release version is 0.14.0 in
package metadata/runtime/lockfile so older Python services require explicit restart.

Validation: 660 Python and 117 UI tests, Ruff lint/format and mypy (98 source files)
passed. Coverage includes real served markup labels/structure, route/framing/authorization,
private-state clearing, step navigation without mutation, exact huge/fractional money,
stale valuation/date labels and independent SQLite equality for analysis requests,
including an expired pending proposal that must remain untouched by reading. See the
[test plan](test-plan.md) for final automated counts. A disposable no-broker preview
server was used only for local checks; Firefox capture was unreliable, so desktop/mobile
visual and device acceptance remain unverified. No operator account restart, activation,
setup confirmation or test order was performed.


## Same-second quote handling, cancellation causes and idle-mode explanation (22 October 2026)

Live journal inspection traced six Approval proposals created at 10:52:31 IST to a
safety cancellation at 10:52:36, with repeated data-order failures and no orders.
A later read-only status showed Manual/SESSION_FEED_OR_RISK_PAUSE despite recovered
7/7 quotes. Automatic activations also encountered the already terminal daily signal
identities; existing no-replay behavior is preserved and now explained in the UI.

The model/broker/candle path now recognizes changed Kite whole-second ties ordered by
strictly later receipt time and matching identity/source. Unchanged repeats exclude
receipt time from equality and do not renew clocks, liquidity or clear faults. Tied
changes update actual books/marks/protection/cumulative-volume candles but skip fill
processing for that timestamp. Replay order, backward/ambiguous timestamps, volume,
tick/depth, basis, session, latency and independent financial checks stay in force.

New cancellation records retain concrete pause causes and a durable `desk_pause` event;
hard failures revoke memory authority without first depending on snapshot I/O. Activity
separates proposal/order cancellation and created/updated times. Long-term desks show a
current-day/profile daily signal summary from the existing bounded history, explaining
cancelled/expired/declined/submitted signals without resetting them or forcing retries.

Validation: 650 Python tests, 99 UI tests, Ruff lint/format and mypy passed. New raw-packet
functional callbacks keep Approval active through eight seconds of tied updates and
still cancel on a real backward quote. Unit checks independently reconcile persisted
cash/fills/fees and confirm one depth budget, same-second protective exit latching with
later fills, actual candle deltas, hard-fault authority revocation and no replay.
Distinct external evidence: an eight-second raw probe observed repeated/changed tied
books; an isolated corrected engine then accepted 68 real quotes (20 changed ties),
with zero quality failures, faults or orders. The operator account was not restarted,
rearmed or used for test orders. Sustained/device/execution acceptance remains pending.
Updated main/detailed usage, API, architecture, feed, risk and validation documents.

## Direct daily-review recovery actions (22 October 2026)

Added **Review today’s setup** in the next-step notice, expanded quote details and
quote/basis readiness cards. The existing guided summary opens directly with an
unchecked acknowledgement, reusing an existing installed policy only when the operator
has not selected another. First-time policy selection stays explicit; no ML fallback.
Buttons require a current IST source snapshot, Manual mode and supported guided setup.
Stale/missing data and custom/legacy configurations show recovery guidance instead.
Lock/cancel/late-response guards remain; successful status removes the shortcut.

Validation: 97 JavaScript tests and 17 guided unit/HTTP workflow tests passed, plus
Ruff lint/format checks. Added independent persisted SQLite/exact cash/config checks
showing preview and rejected acknowledgement do not record a basis review or order.
UI cases cover current/stale data, installed versus first/ML policy, cancel/lock,
readiness-card wiring, single explicit confirmation and removal after resolution.
No new Python runtime behavior or dependencies. Updated main, detailed, component and
validation guides; child-page re-entry loads these controls without another restart.

Operational evidence is separate: a 22 October genuine-data download completed 65 × 60
sessions and a preview; those did not approve reviews. Later read-only inspection at
10:51 IST found seven current-day reviews, incoming stored quote timestamps, Manual
mode, zero API blockers, ₹25,000 cash, zero fees and no orders/holdings. No confirmation
request was sent by this assistant. This is a bounded real-feed observation, not
full-session, strategy-profit, phone/Pi or interactive browser acceptance.

## Open-session quote explanations and working shortlist links (22 October 2026)

Read-only inspection of the existing account found incoming quotes rejected for all
eight selected symbols with `LONG_TERM_REVIEW_REQUIRED`, reviews dated 21 October and
no accepted stored quotes. This explains the observed connected/open-session screen;
it is not an independent broker probe or new action approval. The price-basis gate is
preserved. A shared read-only quote diagnostic now distinguishes basis review from
missing/old/rejected/post-reconnect quotes and disconnection in desk and console views.
Readiness shows the current reviewed-session state and blocker-specific next actions.

Workspace links now retain fragments across standalone redirects and section changes,
defer reveal until unlocked/rendered, expand details, focus the review section and
scroll the outer viewport with the applicable sticky-menu offset. Height updates precede
scrolling, and polling does not repeat the jump. Legacy `apply-shortlist` targets the
containing review section instead of a disabled button. Origin/source checks, guarded
section changes and explicit mutations/confirmations remain; viewing cannot apply a list.

Validation: full 637 Python and 90 JavaScript tests passed; Ruff lint/format and mypy
passed. Tests cover next-day blocked incoming quotes across both APIs, independent
persisted SQLite/exact cash equality, post-review new quotes, stale/reconnect/rejection
states, direct/same-section/cross-section links, hidden targets, detail expansion,
desktop/mobile sticky offsets, keyboard focus and spoofed-message rejection. Updated
main/detailed usage, workspace, API and validation guides. These tests simulate workflow;
interactive browser/device acceptance and actual fresh quote execution remain pending.
Reload the workspace for navigation; restart an older Python service for diagnostics.
No operator-owned service, review, feed, shortlist or mode was changed by this work.

## Feed-selection explanation and session-hour defaults (22 October 2026)

Setup step 4 now explains reference catalog versus saved live subscriptions, the app's
ten-symbol limit, token/tick meanings, broader Nifty 100/500 screening and unsaved-input
versus committed-list behavior. Added an accessible saved subscription heading/count
and input help. No actual account selection is changed by these explanatory UI edits.

Step 5 initializes editable 09:15/15:30 IST fields on unlock. Refresh preserves edits,
including intentionally cleared values; lock clears them and a later unlock restores
defaults. Date-specific review, reference, confirmation and server calendar validation
remain mandatory; no session is implicitly saved and existing hours are not rewritten.
Validation: 28 setup/workspace UI and 24 setup unit/API tests pass, covering defaults,
edit preservation, cancel/confirm payloads, unreviewed/blank-time rejection, independent
saved-calendar reads and exact persisted financial-state equality. These are simulated
workflow checks; no broker/market or interactive device acceptance is claimed.

## Saved broker session feedback (22 October 2026)

Implemented visible progress, a pending button label and inline live success/error
feedback in setup step 3. Failed rechecks clear stale local profile verification,
give connectivity/login recovery and permit explicit retry; locking/auth failure
clears feedback and late results cannot restore it. Existing authenticated read-only
profile routes and private token persistence are unchanged. Login/exchange requests
also report their progress/results beside the controls. UI assets load on section
re-entry without restarting the account service.

Validation: 25 setup/workspace UI tests and 23 setup unit/API tests exercise delayed
success, duplicate prevention, failure/retry, timeout, lock/auth clearing, secret
redaction and independent persisted SQLite/credential/config equality. Broker responses
are simulated. Firefox initially showed an unverified session and later displayed
“Profile verified this run” on 22 October. This is an observed UI status, not an
independent broker probe or streaming acceptance. Automated coordinate clicks returned
`noWindowsAvailable`; desktop/mobile interactive acceptance of the updated UI is pending.

## Simplified combined preparation review (0.13.1)

Implemented the requested shorter setup: download → choose policy → review one summary
and acknowledgement → confirm. Existing same-day completed downloads are reused.
The authenticated summary binds exact at-most-ten ranked stocks, held symbols, source
coverage, all calendar dates/hours, unused-account corrections, eligible current-day
basis reviews and entry hours. Confirmation coordinates existing disconnect, immutable
install, shortlist, listed reviews and connection controls. No freeform reference or
separate feed/shortlist click is required on this path. Advanced CSV/individual controls
remain available. Every mode activation stays a separate explicit choice after readiness.

The two-minute preview expires on time, source/account/shortlist changes or newly
completed missing history. Pending orders, used calendar conflicts, faults and no
candidates refuse action. Held positions, quarantines and uncovered earlier quote basis
are excluded from combined current-day attestations. Setup persists phase/outcome before
side effects, reports partial completion, never automatically retries after failure or
restart, and returns identical completed confirmations without repeating connection/reviews.
Model/data/ranking work remains outside the engine lock; the streaming worker is joined
without that lock. The installation gate covers the whole coordinated operation.

UI: one primary finish button, source/calendar/stock review dialog, unchecked consolidated
acknowledgement, clear Manual/closed-hour outcome, hidden advanced forms, and an embedded
workspace dialog sized/positioned to the visible parent viewport. Locks discard private
summaries and late responses; pending reviews block menu navigation and periodic refresh.
Detailed usage and recovery: [strategy-preparation.md](strategy-preparation.md).

Validation is recorded in [test-plan.md](test-plan.md). All new provider/execution tests
use invented data, including independent Decimal cash/fee reconciliation. The user's
running server, saved account, actual review assertions and mode were not changed.
External market/ML/device gates below remain open; this work does not establish profit.


Validation completed locally: **630 Python tests**, **77 JavaScript tests**, **92%**
overall Python coverage; Ruff lint/format (152 files), mypy (96 source files), frozen
offline lock/sync, sdist/wheel build and project secret checks passed. Isolated Chrome
checks at 1440 × 1100 and 390 × 844 verified no horizontal overflow, visible bounded
review dialog, initially unchecked acknowledgement, consolidated confirmation, Manual
outcome, current-day review persistence and shared unlock into activity, with no browser
exceptions. The embedded-parent resize/scroll listeners are removed on close/lock/unload.
No actual account reviews, strategy or mode were applied during validation.

## Genuine strategy preparation and actionable readiness (0.13.0)

Implemented operator-requested genuine-data acquisition in Trading desk: fixed official
Nifty 100/500 constituent CSV, NSE capital-market holidays and equity-action snapshots,
catalog/INE equity matching and up to 60 completed daily Kite sessions. All returned
action kinds in the interval and incomplete history are excluded. Downloads are
background, cancellable, quota-paced and separate from quote/risk authority; progress,
sources, period, coverage and exclusion reasons are visible. No per-stock history read
is made for known action exclusions. Failures are bounded/sanitized, with no data or ML
fallback. A read-only real-source probe returned 100 constituents, 60 proposed completed
sessions, 65 action-free catalog matches and exact 60-session Kite history for one share.
This verifies source/read plumbing, not all-stock coverage or current-market profitability.

Subsequently completed the actual Nifty 100 acquisition: 35 action exclusions, 65
catalog-matched eligible shares, each with all 60 expected daily candles (3,900 rows).
Stored only genuine source snapshots and an unreviewed draft through a strictly read-only
catalog adapter. No actual account/configuration, reviews, strategy/mode or orders were
changed. The new UI will load this pending review after the operator restarts the older
owning server. Validation: 614 Python / 71 JS tests, 92% coverage, static/type checks,
frozen offline environment and build/secret checks; synthetic headless desktop/mobile
layout and installation/navigation checks passed independently of the real data download.

Added an editable calendar and explicit class/basis/policy review, optional server-selected
compatible ML, an explicitly chosen experimental rules policy and private immutable profile
installation. It preserves existing used session definitions, holds Manual, requires a
disconnected feed/no pending orders and rechecks generation/state after out-of-lock
validation. Saved profile/data hashes restore in Manual on restart. Current constituents
are `prospective_snapshot`, available no earlier than observation/review; historical
execution/ML rejects them. Existing point-in-time contracts remain the default.

The desk now shows actionable strategy, transport, per-symbol freshness/basis, market and
entry-window, shortlist, analysis/model and risk cards beside mode explanations. Browser
refresh preserves unsaved preparation reviews. Detailed guide: [strategy-preparation.md](strategy-preparation.md).
Independent current-market model/expectancy validation, point-in-time universe acquisition,
unattended daily refresh, automatic action accounting and early-year/cross-year source
automation remain open; the supported explicit custom-bundle workflow remains available.

Found the actual account's saved 15:15 close conflicting with the normal 15:30 proposal.
Added visible hour differences and a separate strict acknowledgement for correcting an
unused account only; quotes/candles, pinned reviews, trades, actions and portfolio/SIP/
desk-instruction usage prevent correction, rechecked after validation. No actual calendar
was changed automatically. Installation blocks arming; midnight invalidates source runs.
Verified the actual Nifty 500 source contains 501 rows with six unsupported series/dummy
entries; exclude those individually and retain 495 supported shares within the 500-symbol
analysis limit. This is current-source parsing evidence, not their daily history acceptance.

## Trading desk and decision modes (0.12.0)

Delivered a default Trading desk and separate Buy / sell activity section. Explicit
manual/approval/automatic paper modes control strategy proposals for both horizons.
Reviewed daily bundles can screen up to 500 symbols, with separate equity-share
classification, current matching calendar, strict real/synthetic/model provenance and
bounded held-preserving shortlist review. Intraday uses causal completed five-minute
rules; long-term uses prior completed daily rules and optional matching validated ML.
A missing real profile/model is visible and blocks activation; the old five stocks
are not replaced or called profit picks. Rules-only is an explicit experimental policy.

Durable proposals have preview/expiry/mode-generation/price-gap bounds, quantity/cash/
risk revalidation and explicit authorization before the independent paper broker.
The broker journals exact authorization identity with its order transaction; restart
links a matching committed order or cancels unsubmitted authority without replay.
Discretionary sells follow the selected mode; protective exits do not wait. Mode/data/
risk pauses revoke authority before I/O, cancel unfilled desk buys and retain holdings.
Activity uses indexed cursors and exact Decimal cash-flow/fee/fill evidence. Daily
ranking/history I/O stay outside risk locks; only the execution daily timeline is held.

This completes the workflow implementation, not the original profit-evidence/data
acquisition milestones. No genuine daily bundle/model was installed, no actual user
account or mode was changed and no real/paper order was placed in that account.
See [trading-desk.md](trading-desk.md) for commands, configuration, recovery and limits.
Broader automatic data acquisition, qualified net-expectancy ranking and prospective
real-market acceptance remain the next priority; LT3c2/LT3c3 also remain open.

Prepared 20 October 2026; updated 21 October 2026. This is the execution record for the original
[project specification](../zerodha_ai_trading_agent_project_spec.md).

## Implemented scope

### Verified after-hours feed repair (0.11.1)

Diagnosed the actual 8004 feed failure with a valid broker profile and successful
read-only WebSocket: all five selected full packets had empty bid/ask sides after
hours. Skip zero-depth/price observations without manufacturing executable Quotes
or disconnecting; retain strict framing/identity and other validation. Immediately
invalidate prior fresh depth per symbol, reset manual partial candles and apply existing
intraday stale-data safeguards without silently rearming. Added safe stream state,
consecutive retry budget/failure category, receipt time and ignored-book
count to authenticated Setup and explanatory UI. Added meaningful unit, HTTP lifecycle,
pending-order/accounting and UI checks. Updated usage/restart and component documents.
The corrected worker stayed connected in an isolated 15-second actual broker check;
five unusable observations, zero usable quotes, no account callbacks or orders.
No operator-owned process was stopped or restarted by this work. Port 8004 was no
longer listening at the final local check; the operator can start the corrected version
with `./scripts/start_ui.sh` and explicitly reconnect in Setup.
This does not complete fresh-market execution, full-session or strategy acceptance.

### Shared workspace and explicit operating guidance (0.11.0)

Added the requested clear menu and a shared in-memory local unlock across its Start
here, Trading console, Broker & feed setup and Purchases & SIP sections. Direct page
URLs route to the workspace; root goes to the guide. Reload/new workspace tabs still
require unlock. Pending requests/confirmations/login windows block navigation, and
lock/authorization failure clears shared access. Scoped same-origin framing and
origin/window/view checks preserve the bearer-only boundary without browser storage.
Workspace metadata explains actual account mode, configured hours, feed-not-requested
versus disconnected and the difference between trade/strategy/monitoring frequencies.
The [new workspace guide](workspace.md) gives restart and next-session instructions.
This changes navigation, not financial policy, order submission or automatic discovery.

### New priority: broader profit-oriented discovery for both horizons

The operator clarified that “best” means potential profit, after being asked to
choose five manual feed symbols. The next priority is now the staged
[stock-selection implementation plan](stock-selection-plan.md): real data coverage,
reviewed broad equity membership, separate intraday/long-term net-of-cost evaluation,
explainable candidate/selection UI and prospective paper acceptance. Profile-driven
screening, strategy modes and activity UI are now implemented (0.12.0); real-data
acquisition/qualified profit validation and prospective acceptance remain pending. Current account data has no accepted quotes or
stored candles; available research inputs inspected were synthetic. Do not substitute
stock names, demo ranks, index membership or unvalidated gross returns for evidence.
LT3c2 rebalancing and other outstanding work remain open after this new priority.

### Browser setup and repeat startup (0.10.0)

Implemented in response to actual operator-token/request-token confusion and manual
setup friction. `/setup` now separates local authorization from Kite credentials,
opens the official login with state-bound popup handoff, explicitly exchanges and
verifies the session, imports a catalog, validates/persists selected symbols, adds
operator-reviewed immutable session definitions and controls the manual feed.
`scripts/start_ui.sh` opens a matching running account or starts its UI/browser;
`serve --open` remains the lower-level option. No secret is returned in status or
stored in browser persistence, and the independent broker/risk boundary is retained.

The real app registration/payment/login/2FA remain external. First local runtime,
operator credential and economic-policy setup, bound automation, complex corporate
actions and research/model acceptance retain their documented workflows. This does
not complete LT3c2 rebalancing, ETF-specific accounting or real-market acceptance.
The [new detailed usage guide](ui-setup.md) covers commands, private persistence,
failure/recovery and limits. Test evidence is recorded in the change log.

The [live-data first paper-session guide](first-paper-session.md) records developer
registration, officially checked plan requirements, private daily token handling,
isolated manual intraday/long-term setup and acceptance/recovery steps. This is
operator documentation, not evidence of an actual broker login/feed session or a
sandbox integration. External data entitlement and sustained market-feed acceptance
remain pending.
The first-session recovery instructions also distinguish copied-config port
selection, a diagnostic-only preflight, offline UI startup and the nonempty catalog
selection required by streaming. Local UI availability does not establish live-data
or session readiness.
The first actual profile/WebSocket observation is now recorded in
[acceptance.md](acceptance.md#first-connected-session-observation-21-october-2026),
with calendar/price-basis and full-quote acceptance still pending. Catalog `EQ`
membership can include ETFs; instrument-class-aware charges and corresponding
unit/functional accounting checks are required before claiming ETF execution support.

The repository delivers Phases 1–3 infrastructure/research and Phase 4 supervised
intraday paper-feed engineering, LT1–LT2 long-term paper mechanics and LT3a daily
research foundations plus LT3b offline quote-executed daily strategy/ML validation
and LT3c1 reviewed contributions/SIP.
The paper horizons share transactional risk/execution mechanics. Rules/models
run offline or on explicitly configured dedicated paper accounts. No live adapter, profitability
or compliance readiness is implied. External account creation, entitlement checks
and OS service installation require real credentials/hardware and are not fabricated.

| Original work item | Implementation / evidence |
|---|---|
| Git and environment | `main` initialized; Python 3.13.16 `.venv`; hashed `uv.lock`; ignored secrets/runtime/data |
| Typed config and paper guard | Frozen validated TOML settings; alternate mode/public host rejected |
| Structured diagnostics | Rotating JSON with secret redaction, intent correlation in durable journal |
| Local app and health | FastAPI console, liveness, entry readiness, authenticated private API |
| Read-only broker contract | Restricted transport implementing official profile/catalog/history protocol |
| Manual authentication | Supported browser URL + hidden request-token exchange + private output file |
| Streaming and candles | Strict full-mode NSE decoder, disconnect/reconnect gating, 1m/5m builders, history storage |
| Database and account | Schema v1, WAL FULL, file ownership, atomic journal/materialized state, exactly ₹25k initial cash |
| Risk and execution | Fee/slippage-aware sizing, reservations, fill state machine, loss gates, stop/target/session exits |
| Kill and recovery | Durable switch, explicit operator reset, restart reconciliation/cancellation/requeued exits |
| Tests and quality | Unit, integration, functional CLI/API, replay, security, dependency audit, Ruff, mypy, CI |
| Deployment and recovery | macOS/Pi scripts, launchd/systemd templates, verified backup/restore tests |
| Research foundations | O(1) EMA/VWAP/Wilder ATR; service still rejects unconfigured ML |

## Enhancements and justified changes

1. **Atomic reservations and fills.** Sizing and cash/risk reservation share a writer
   transaction; cash, cost basis, fees, orders, fills and audit events commit together.
   One process owns an account, preventing a second startup from changing active work.
2. **Explicit calendar and time.** There is no baked-in possibly stale holiday list.
   Unknown dates are closed. Session time is IST; storage and epoch decoding are UTC.
   Reviewed early closes take precedence. The empty shipped calendar is intentional.
3. **Conservative research accounting.** Decimal money, tick-aware adverse prices,
   order-cumulative fees, estimated liquidation P&L, residual basis allocation,
   and cost-aware daily capacity extend the illustrative sizing formula.
4. **No false closes.** A stop, kill or watchdog request queues an exit; fresh data
   and actual simulated depth are required for fills. Remaining positions persist.
5. **Restart semantics.** Reconcile durable state first, cancel pre-crash pending
   orders, and request required exits again. This avoids reviving old entry intent.
6. **Configuration and schema safety.** Required metadata cannot silently reseed
   when missing; unknown schema and changed risk policies fail closed. New policy
   experiments use a new account. SQLite defaults remain durable rather than tuned
   to unsafe write modes for benchmark scores.
7. **Dependency exception.** The official SDK installed a vulnerable pinned Autobahn
   stack and a flagged Twisted dependency. It was removed, with no ignored advisory.
   A smaller allowlisted HTTPX/WebSocket implementation follows official broker
   protocols and has a clean re-scan. This also removes order-capable SDK methods
   from runtime. See [threat-model.md](threat-model.md).
8. **Lightweight research path.** Incremental Decimal indicators avoid pandas/NumPy
   startup/memory costs in the hot path. Heavy training dependencies are deferred
   until there is a chronological strategy dataset. TOML uses Python's standard
   parser instead of YAML, reducing dependencies. Public types and artifacts remain
   suitable for adding offline ML in later phases.
9. **Normalized schema.** Candidates, decisions, state transitions and system
   notifications live in the append-only journal; snapshots are transactionally
   derived. A few duplicate tables in the illustrative layout were unnecessary.
10. **Reviewable operations.** No host-wide services, users, firewall rules or broker
    plans were silently provisioned. Templates and instructions make these concrete
    for the operator while preserving this workspace's permissions and credentials.

## Phase 2 delivered — version 0.2.0

| Work item | Implementation / evidence |
|---|---|
| Predeclared rules | ORB and VWAP-continuation, completed 5m data, prior-volume reference, independent symbol/session state |
| Causal features | No active/future candles; missing opening/history disables that session; future-quote prefix-invariance test |
| Execution boundary | Existing fee/slippage/latency/depth risk broker; no candle-close fills or invented OHLC paths |
| Isolated research | New output account; backtests never open the service account; export never runs restart cancellation |
| Provenance | Raw-price manifest, reviewed sessions/sources, chronological typed JSONL, source/config/code hashes and unchanged-input checks |
| Reports | Net metrics, observed drawdown, partial-trade accounting, decisions, equity CSV, journal and incomplete-exposure gates |
| Commands | `research-demo`, `backtest`, `export-research`, and configurable strategy TOML |
| Performance | Constant per-candle work; measured p99 below 0.018 ms on this Mac, excluding input parsing/execution/network |
| Verification | Unit, integration, functional CLI, deterministic/leakage/failure tests; detailed research guide |

Enhancements to the Phase 2 plan:

- Require completed candles and observed quotes; OHLCV alone cannot reconstruct
  executable depth or stop/target ordering, so candle-only runs are refused.
- Even zero-latency experiments require a strictly later exchange quote to fill.
- Preserve positions at dataset exhaustion; disclose pending orders, stale valuations,
  held-position quote gaps and incomplete results instead of fabricating liquidation.
- Label synthetic/mixed/replay provenance explicitly, with one positive and one
  negative synthetic session rather than a profitability demonstration.
- Bound manifest/line reads, reject external/symlinked bundle paths and manual
  candidate events, and leave no loadable manifest after failed exports.
- Preserve source orders during export; disclose historical candle availability,
  fee matching and unavailable connection history as research assumptions.

See [backtesting.md](backtesting.md) for input construction, rules, reports and sample gates.

## Phase 3 delivered — version 0.3.0

| Work item | Implementation / evidence |
|---|---|
| Causal training schema | Twelve finite ordered features, completed-time checks, economic candidate fingerprint, no outcomes in features |
| Execution labels | Independent fee/risk/latency/depth-aware paper trials, time barriers and actual fill interval ends; exclusions retained |
| Provenance | Source manifest/hashes, full strategy/economic settings, label policy, code hash, sample/audit hashes and completion manifest |
| Chronological validation | Whole-session expanding walk-forward blocks, interval purge/embargo, independent later calibration and frozen final holdout |
| Baseline model | Train-only StandardScaler + fixed logistic regression + separate regularized sigmoid calibration; no hyperparameter search |
| Diagnostics/gates | ROC-AUC, Brier/log loss, training-only baseline, reliability/ECE, selected count/net label P&L and strict validation consistency |
| Safe artifacts | Bounded local JSON coefficients/reports, exact dimensions/schema, hash checks, no executable persistence, failed-gate refusal |
| Scored research | Same-availability-time ranking, deterministic ties, later portfolio replay and independent risk/model gate |
| Account continuity | Durable model version/schema marker, missing/changed gate refusal before recovery, idempotency includes vector |
| Lightweight inference | Pure Python twelve-feature math; optional training packages never imported for scoring; Pi setup uses runtime/broker extras |
| Commands/docs | `ml-build`, `ml-train`, `ml-demo`, `backtest --model`, full [ML guide](ml-research.md) and corresponding component updates |
| Verification | Unit/functional/causality/censoring/risk/integrity/determinism tests plus a separate inference/ranking benchmark |

Enhancements to the Phase 3 plan:

1. Label **all standalone feasible candidates**, rather than only trades selected
   by a competing portfolio. Preserve censored/rejected/unfilled/interrupted paths
   separately so missing outcomes never silently become negative labels.
2. Use actual quote-driven paper execution for labels. OHLC paths and forced horizon
   closes are not reconstructed. Label end includes the final liquidation fill,
   allowing delayed outcomes to be purged correctly across split boundaries.
3. Reserve separate calibration blocks in every fold; fitting scalers, base models
   or calibration on evaluation/holdout observations is prohibited.
4. Make model availability follow **final validation plus embargo**, not merely
   coefficient fitting. A historical replay cannot use future approval evidence.
5. Freeze fixed baseline coefficients before final holdout diagnostics, retain
   unsuccessful reports, and check diagnostic consistency again during loading.
6. Export inspectable JSON math rather than pickle/joblib. Keep training optional
   and outside the connected feed process; add measured inference/ranking latency.
7. Keep synthetic test settings separate from real research defaults. An explicit
   offline synthetic override relaxes only provenance and only on synthetic data.
8. Bind vectors to economic candidates and accounts to model identity. Model gates
   add rejection conditions without changing the original risk hash or any limit.

Synthetic end-to-end verification uses sixty training/validation sessions followed
by ten unseen invented sessions. It establishes software behavior only. There is no
empirically accepted market model or live readiness.

## Phase 4 engineering delivered — version 0.4.0

| Work item | Implementation / evidence |
|---|---|
| Supervised feed | Explicit `serve --stream --automate`, authenticated arm/disarm, universe-wide readiness and disarmed startup/restart/session |
| Safe account setup | `paper-init` checks profile/catalog and exclusively creates/binds a new account without conflicting manual model initialization |
| Causal history | Separate paced worker loads full completed current-session 5m data; incomplete/revised/obsolete responses fail and missed signals are not replayed |
| Independent execution | Same fee/depth/latency/sizing/kill broker, controller-bound submissions, durable proposal caps, model age/availability |
| Recovery | Disconnect/staleness cancels buys and disarms; stale holdings queue durable exits, without fake closes or automatic rearming |
| Policy continuity | Runtime/catalog/model/strategy/feed identities and used calendar definitions pinned; changed/removed automation fails before recovery |
| Observability | Recent timing windows, cumulative counts/maxima/exceedances, periodic status and observed per-run drawdown |
| Evidence | Source-preserving `paper-report`, net trades, incidents, clean-run/sample/model/latency gates; external/live flags always false |
| Drills | Synthetic partial fills, disconnect with holdings, silence and unclean pending-entry restart with separate ledgers/reports |
| Performance | Additive event-kind/time index, populated benchmark and test proving history network waits release the execution lock |
| Captured research data | Exports preserve first observed candle/connection clocks; missing clocks and unclocked supervised overrides fail |
| Verification/docs | Unit/concurrency/functional API/CLI tests, CI drills and complete [paper-feed guide](paper-feed.md) |

Enhancements to the Phase 4 plan:

1. Supervised arming replaces resumption of old entry authority after restart or
   reconnect. Protective handling continues independently while entries are disarmed.
2. Authoritative completed historical candles avoid unknown first-bar volume and
   partial-bar/history mixing. Backfill warms features without replaying missed trades.
3. History HTTP/rate pacing stays outside the quote/risk lock. Responses from obsolete
   connections are discarded, the whole universe is required and late signals are skipped.
4. Accounts bind their controller/model before recovery. Durable proposal counts
   survive rewarm/restart; model/rule changes use a new account.
5. Engineering evidence remains separate from empirical acceptance. Reports disclose
   recent-window quantiles, lost crash samples and unresolved exposure. No report can
   authorize live execution.

Actual feed duration, fill calibration, entitlement and Pi reboot/storage/power-loss
drills remain external acceptance work. Synthetic tests deliver the code milestone only.

## Phase 4 acceptance tooling and responsive console — version 0.4.1

The next locally implementable milestone extends acceptance support while actual
broker/device/model evidence remains pending. It does not advance into live execution.

| Work item | Implementation / evidence |
|---|---|
| Responsive operator UI | Packaged HTML/CSS/JS, account cards, readiness reasons, positions, recent orders, details and mobile CSS stacking |
| Consistent bounded view | Authenticated `/api/console`, engine-serialized snapshot, latest 200 orders and at most ten quote rows |
| Operator safety | Lock clears values/token and rejects late requests; stale indicators, serialized actions, explicit arm/reset confirmation, no automatic action retry |
| Local acceptance diagnostic | `preflight [--strict] [--output NEW_PATH]`, read-only WAL-aware accounting/integrity, identity/permission/calendar/disk/runtime checks |
| Evidence integrity | New private JSON/Markdown reports and last-written hash manifest; external/live acceptance always false |
| Deployment patch check | Explicit official SQLite WAL-reset fix branches; actual local runtime SQLite 3.53.1 |
| Validation | 284 Python tests, 13 JavaScript cases, 92% Python coverage; wheel includes and loads all UI assets |
| Usage and external work | Dedicated [console](operator-console.md) and [acceptance](acceptance.md) guides and corresponding component documentation |

Enhancements: diagnose accounts without acquiring write ownership/recovering orders;
keep heavy integrity work out of the feed/UI polling path; bound recent UI history;
retain exact decimal display; distinguish local checks, current session and external
acceptance. CSS supports mobile browsers but small-screen visual/physical-phone
acceptance remains pending because browser tooling did not yield reliable evidence.
Desktop Safari and the isolated virtual kill/reset/lock flow were verified locally.

## Long-term scope extension — LT1 delivered, version 0.5.0

The user extended the project to include long-term investing. This introduces a
separate paper horizon; it does not convert intraday accounts or implement the
original live infrastructure Phase 5. Full usage and explicit limits are in
[long-term.md](long-term.md).

| Work item | Implementation / evidence |
|---|---|
| Separate horizon | `investment_horizon`, dedicated config/database/8001 listener, durable binding and unchanged legacy intraday hash |
| Overnight lifecycle | Holdings survive close/weekend/restart; pending buys expire, requested exits remain latched until closure |
| Independent risk | Existing sizing, cash/depth/tick/latency limits plus durable observed peak/drawdown and gap-preserving daily reference |
| Price-basis integrity | Current-session operator review, previous accepted quote clock, pinned used calendar definitions and persistent corporate-action quarantine |
| Delivery costs | Observed retail NSE delivery schedule, exact partial-order fees, atomic per-symbol/day DP allocation and entry cash buffer |
| Reconstruction | Delivery fees/day markers, fills, review authority, quarantines and requested exits checked against journal/ledger on startup |
| Operator/API | Horizon badge, long-term risk/review panel and confirmed individual full-holding exit, authenticated typed endpoints |
| Evidence/drills | Source-preserving `long-term-report`; invented overnight partial/restart, opening-gap and unadjusted-action scenarios |
| Performance/validation | 328 Python + 17 JavaScript tests, 92% Python coverage; populated long-term p99 0.3288 ms on this Mac, excluding network/Pi |
| Documentation | New detailed long-term guide plus updated original specification, usage, API, risk, architecture, threat, operations, acceptance and tests |

Enhancements to the scope: require a separate account instead of changing intraday
semantics; preserve opening gaps rather than marking the new day's baseline at its
first new price; retain explicit exits across cancelled/restarted residual orders;
charge DP only on actual fills; block unaffordable exit fees without inventing cash;
reject a restarted selected feed that omits a held symbol; quarantine known corporate
actions instead of treating an unadjusted price jump as ordinary market P&L.

## LT2 delivered — reviewed corporate actions, version 0.6.0

| Work item | Implementation / evidence |
|---|---|
| Reviewed inputs | Bounded strict JSON, stable action/batch/receipt IDs, sourced ex-date sessions, explicit chronology and quarantine hash/complete-coverage assertion |
| Share ledger | Increasing splits and bonuses, conservative tick-adjusted protections, original holding identity/cost conservation and affected-order cancellation |
| Fractional handling | Exact rational claim, pro-rata basis rounded down to paise with exact holding residual, unknown valuation retained after whole-share exit, explicit cash-in-lieu receipt |
| Dividend ledger | Frozen gross/deduction/net receivable, nonspendable before payment, exact once-only net cash receipt and separately reported investment income |
| Integrity/recovery | Additive tables, atomic journal/materialized accounting, independent ordered fill/action/receipt reconstruction, cache/basis/protection verification and backup/restart tests |
| Operator workflow | Exclusive offline CLI, current-session review and post-application quote required on resume; existing protective exits retain their latch |
| Reports/console | Schema-2 evidence with claims/batches/quarantine hashes/income, adjusted whole-share metrics and separate console claim summary |
| Demonstration/performance | Invented split→dividend→bonus/fraction→exit→receipt lifecycle and a 2,000-quote populated unpaid-dividend benchmark, p99 0.2564 ms on this Mac |
| Standing requirement | [AGENTS.md](../AGENTS.md) records the user's instruction to update usage and component guides with every feature/workflow change |

Enhancements: apply actions only before the account crosses the first affected
ex-date price/trade basis; never infer a payment, fraction value or settled eligibility;
freeze explicit same-date action order; reject unsupported fraction chains and
reverse/complex issuer events rather than silently losing claims. Full schemas,
commands, retry/failure behavior and exclusions are in [corporate-actions.md](corporate-actions.md).

### Extended long-term roadmap

LT3 is implemented in dependency order: **LT3a delivered in 0.7.0** reviewed completed daily data,
point-in-time membership and total-return-aware causal screening with an accessible
offline research dashboard; **LT3b delivered in 0.8.0** quote-executed daily strategy
research and separate chronological ML validation; **LT3c1 delivered in 0.9.0**
reviewed cash-budget additions/acquisition history/SIP; **LT3c2 next** reviewed
rebalance proposals; **LT3c3** aggregate capital coordination. A daily bar cannot establish an
executable fill, and screening statistics cannot approve a model or portfolio.

LT3a delivers bounded streaming daily bundles, explicit period-benefit/availability
evidence, historical inclusion/exclusion/re-entry, consecutive rolling gross-return/
trend/volatility/turnover screening and deterministic candidate ranks. The private
offline dashboard explains statuses/metrics, filters/sorts, missing-data/empty states
and provenance without account/control access. Source/code hashes, mutation checks,
strict validation, invented adverse/gap/exclusion fixtures and unit/functional/UI
tests support review. **420 Python + 23 JavaScript tests, 92% coverage**; 538-bar Mac
analysis p50 **8.0033 ms** including input/validation/hashes. See
[daily-research.md](daily-research.md) for schemas, assumptions and exclusions.

| Milestone | Required implementation / acceptance | Status |
|---|---|---|
| LT1: overnight paper foundations | Lifecycle, delivery costs, reviews, risk, console, evidence and tests | Engineering delivered |
| LT2: corporate actions and cash/share ledger | Reviewed split/bonus/dividend entitlements and effective/payment dates, integral/fractional handling, atomic idempotency, independent reconstruction and recovery | Supported paper engineering delivered; complex actions/tax lots/custody remain excluded |
| LT3: daily research and portfolio management | Completed daily price/total-return data, point-in-time universe, causal strategy/ML validation, SIP/lot additions, rebalancing and cross-account allocation | LT3a/LT3b/LT3c1 delivered; LT3c2 reviewed rebalance proposals next; LT3c3 capital coordination pending |
| LT4: actual read-only holdings and supervised acceptance | Reviewed custody/sellable holdings/settlement reconciliation, calibrated costs/fills and sustained actual device/feed evidence | Pending external access and engineering |
| Live infrastructure / pilot | Existing separate empirical, compliance, adapter/reconciliation and explicit approval gates | Pending; execution unavailable |

Reviews and LT2 inputs are operator assertions, not verified corporate-action feeds.
Real settlement/custody, income tax/AMC, automatic long-term signals, complex actions,
lot/tax management and combined capital coordination are not implemented. Preserved
overnight state alone is not full investment-platform or production readiness.

## LT3b delivered — quote-executed daily strategy and separate ML, version 0.8.0

| Work item | Implementation / evidence |
|---|---|
| Reviewed executions | Separate strict bounded quote/control/action bundle; matching catalog, exact sourced daily calendars, availability clocks and structural raw price/benefit checks |
| Causal strategy | Prior completed available daily windows, current PIT universe, applied-action reference basis, deterministic simultaneous rank, one proposal/session and bounded session-horizon/screen exits |
| Exact delivery replay | Isolated account, existing durable Decimal broker/risk/fees/DP/action/cash ledger, later quote/depth fills, retained unresolved exposure and independent reconstruction |
| Independent labels | Separate account per standalone candidate; full net outcomes and actual final fill intervals; explicit partial/unfilled/interrupted/gap/cash-action/capacity exclusions |
| Separate daily ML | Own twelve-feature/model namespaces, expanding whole-session interval purge/embargo, train-only scaling, separate calibration, frozen holdout and retained failed diagnostics |
| Later scoring | Bounded JSON math, hash/audit/context/gate checks, after-validation availability, probability rank/threshold and independent risk; pure Python inference |
| Explanatory UI | Responsive offline portfolio/label/validation/scored dashboards, exact money, searchable evidence, incomplete states, chronology and plain-language next steps |
| Validation/docs | 479 Python + 29 JavaScript tests, 92% coverage; complete [daily execution guide](daily-execution.md), main usage/component updates, CI/demo/benchmark |

Enhancements: keep independent cash-specific dividend/payment intervals censored
instead of guessing a counterfactual deduction; keep quiet declared sessions in
training chronology; use actual market-open elapsed coverage rather than counting
overnight time as missing ticks; require model availability after the last declared
source session close plus embargo; preserve actual incomplete trial accounts and
explicitly separate label sums/observer state from portfolio returns. Source hashes
and final manifests support consistency, not authenticated broker provenance.

Measured Mac fixture: durable three-session/nine-trade replay p50 **35.4865 ms**,
p99 **47.7677 ms**; warmed single-symbol screen p99 **0.0074 ms**. No unsafe SQLite
tuning or new runtime dependency. These timings exclude network/Pi and do not claim
large-universe performance. Actual daily data acquisition, empirical acceptance,
historical fee matching and custody remain pending. Daily models do not enable the
connected long-term service. **Next locally implementable item: LT3c lot additions/SIP,
reviewed rebalancing and aggregate capital coordination**, before LT4 actual holdings.

## LT3c1 delivered — reviewed contribution foundation, version 0.9.0

LT3c is deliberately split by financial dependency: stable contribution identity/
cash accounting first; reviewed rebalance proposals second; aggregate account capital
coordination third. This preserves independent reconstruction and review at each step.
It does not mark all portfolio management or tax-lot accounting complete.

| Work item | Implementation / evidence |
|---|---|
| Reviewed contributions | Read-only exact preview, fresh quote/holding/capacity hash, explicit authenticated confirmation, atomic budget/order/proof reservation |
| Safe holding additions | Existing-plus-added position room, shared daily/per-trade/aggregate risk and cash/fee checks, retained protection/opening identity, exit-latch refusal |
| Acquisition history | Original filled BUY orders, actual cash/fees and partial entries; distinct current aggregate pooled holdings; no FIFO/tax-lot attribution |
| SIP occurrences | Immutable reviewed source-session dates, fixed cash caps/new-holding percentages, one confirmed attempt/date, explicit missed/due/cancelled states and no automatic catch-up/funding |
| Atomic cancellation/recovery | Pending plan buys cancelled with plan; restart cancels residue, retains fills and consumed occurrence; identical approval retries return original state |
| Independent integrity | Additive tables/schema/journal, reconstructed plan/approval/hash/order authority, first-fill basis and later price-cap/time checks, existing Decimal fills/fees/actions/claims reconciliation |
| Responsive UI | `/portfolio` with exact previews, clear confirmations, due-plan buttons, reserved/spent cash, pending orders, current holdings, original lot history, stale/locked states |
| Evidence/performance | Deterministic invented restart/SIP lifecycle, 511 Python + 36 UI tests, 92% coverage; populated preview p99 0.1784 ms, durable confirmation/fill p99 1.5532 ms |
| Usage | [Detailed contribution/SIP guide](portfolio-contributions.md), main usage and component/specification updates; no new dependency or broker capability |

Enhancements: spend only already available virtual cash rather than infer future
deposits; require an explicitly reviewed session list rather than guess holiday
roll-forward; separate original acquisition history from current pooled ownership;
leave the original intent route's duplicate-holding guard intact; atomically cancel
plan remainder without selling filled shares. The demo's mutable UI copy is separate
from frozen financial evidence. Network/device/market acceptance remains external.

**Next: LT3c2 reviewed rebalance proposals**, followed by LT3c3 shared capital
coordination. Partial discretionary trims/execution, per-lot ownership/FIFO/taxes,
deposits/withdrawals and connected daily automatic signals remain outside this release.

## Remaining external milestones and acceptance gates

| Milestone | Required next evidence |
|---|---|
| Real read-only session | 21 October 2026: actual saved-session profile authentication and five-symbol WebSocket connection observed; accepted full quotes, history entitlement and sustained checks pending; unit transports remain mocked |
| Target-device operations | ARM64 Pi dependency installation, reboot/launchd/systemd/power-loss drill, disk monitoring |
| Empirical strategy validation | Actual matching raw candle/quote data, point-in-time universe/corporate-action review, calibrated fees/depth and retained unfavorable experiments |
| Empirical ML acceptance | Implemented Phase 3 workflow must pass on reviewed real data, with exclusion/selection/cost assumptions retained and later portfolio validation |
| Phase 4 external acceptance | Sustained actual supervised feed, calibrated fills/costs, full-session coverage review and target-device recovery/latency |
| Future live (Phases 5–6) | Separate explicit approval, current compliance and broker rules, separate reviewed adapter/reconciliation |

The code is portable by design, but local tests on this Mac are not a Raspberry Pi
deployment certificate. Backup tests and SQLite fault injection do not replace a real
power-loss rehearsal. A clean advisory scan is time-specific, not a future guarantee.
No live account action or order was attempted. See [test-plan.md](test-plan.md) for
the final measured validation record.
