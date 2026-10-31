# Change log

## 31 October 2026 — backend 0.21.0 / Android 1.1.0: NSE watchlist and safety

Add authenticated browser/native Watchlist selection from the saved NSE catalog.
Persist permissions per account; reject out-of-list buys at proposal, preview,
submission and fill boundaries. Empty lists block new entries. Replacement cancels
pending buys and pauses desk authority; held stocks remain exit only. Add a 25%
equity order-cost ceiling including buy fees, five accepted entry slots per IST
day, durable 25% drawdown pause with explicit reconciled-reference reset, and daily
price-integrity lockouts. Preserve cash-only/held-quantity, ledger-fault and existing
risk gates. External funding remains unsupported; historical research stays isolated.
Version files move together to 0.21.0; Android source is 1.1.0 / code 11.

Tests were added but **not run**, per the user's explicit instruction. Ruff lint/format,
Python source parsing, mypy (135 source files), JavaScript syntax, whitespace and
project secret-pattern checks pass. Android source compilation could not complete:
the wrapper download timed out, and the installed Gradle 9.7.1 offline fallback
could not resolve the uncached Android Gradle plugin 9.4.1. No live deployment, market/broker,
biometric/device acceptance or published APK is claimed by this entry.

## 29 October 2026 — backend 0.20.9 / Android 1.0.9 timeout fix and browser parity

Fix the 1.0.8 opening spinner/timeout: live full-audit request exceeded 55 seconds while
normal local reads initially took 0.007–0.172 seconds. Cache execution-basket resolution
once per full report, add a lightweight authenticated source-only audit, and move initial
Android automatic checks out of foreground loading. Separate failed-source recovery from
fresh account status, retaining no mutation retry. Browser Dashboard/Strategies now have
Access → Data → Review → Trade, policy/data reuse, catalog automation and requested-download
follow-through. Routine browser polling is quiet and serial/controller-safe. All setup,
feed and mode confirmations, financial/risk checks, biometrics and source exclusions remain.
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



## 29 October 2026 — backend 0.20.8 / Android 1.0.8 guided daily steps

Simplify native Home/Strategy into Access → Data → Review → Trade with one next action.
Automatically check saved access and current source/history evidence; skip valid data and
installed setup, follow a requested download through to one review, and visibly reuse the
last confirmed policy. First policy choice, setup acknowledgment, feed effects and trading
mode confirmation remain explicit. Connection outcomes/readiness refresh automatically;
waiting cannot arm trading. Advanced controls and all native destinations remain available.
No financial/risk/market-execution logic changes; backend bump identifies the release.
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

## 29 October 2026 — backend 0.20.7 / Android 1.0.7 full Nifty 50 basket

Removed the two hard-coded ten-stock cuts. Nifty 50 preparation, whole-basket guided
selection and an authenticated official-selector endpoint avoid manually choosing names.
The entire supported basket is monitored; reviewed data, signals and risk control buys.
Holdings are retained and legacy feed capacity is raised operationally. Discovery is
scoped to the basket, with coverage/exclusions and per-stock reasons visible on Android.

New production intraday analysis seeds official history in the background and evaluates
completed live-feed candles without waiting for a REST basket. Warm-up never places
an order or replays a missed signal; missing/gapped inputs re-seed, and all existing
five-second freshness, mode/revision and financial checks remain unchanged.
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

## 29 October 2026 — backend 0.20.6 / Android 1.0.6 Trade next steps

Trade now explains current readiness, completed checks, next reviewed entry start and
remaining waits/actions beside mode selection. Tapping blocked Approval/Automatic
rechecks status and opens useful guidance with setup links. The dialog updates quietly
and transitions to a review option when ready; it never activates a mode on its own.
Next-start calculations respect reviewed special sessions and configured cutoff, and
never guess unreviewed dates. Mode confirmation retains server gates/revision checks;
changed-readiness 409s show updated help with no write retry. Stale/missing status blocks
confirmation. Android biometrics/pairing/signature and paper accounting are unchanged.

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

## 29 October 2026 — backend 0.20.5 / Android 1.0.5 branding and stable refresh

Added Agentic Trader branded biometric entry and matching native light splash using
the selected supplied logo; no artificial startup delay. Initial loading waits for a
complete account snapshot. Fixed visible busy/progress toggling on five-second polls,
partial snapshot rendering and old-read races. Foreground progress keeps a fixed slot;
reviews/dialogs pause polling. Network failures retain the last snapshot, marked stale.

Paper/Real selector shows Paper active and Real disabled with the missing execution/
reconciliation explanation. Authenticated read-only environment capabilities are now
available; no account switching or live order execution is implemented. Unexpected
non-paper desk responses block actions. Existing package/signing/pairing are retained.

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

## 28 October 2026 — backend 0.20.4 / Android 1.0.4 reuse recent daily history

Fixed **Check & prepare today** fetching candles again despite a valid recent
download. The native app requested lightweight `/api/operations`, whose source
validation is intentionally null, and treated the omitted audit as stale evidence.
It now requests `?audit=true`, verifies source hashes/IST date/per-symbol coverage,
matches the selected universe and rechecks the current ready/installed job identity.
Valid history is reused with its timestamp and **No daily candles were downloaded**.
Existing running work is attached; an identity race stops for another check. Explicit
fresh download still bypasses reuse. No arbitrary five-minute expiry, installation,
mode change or financial instruction is added.

Validation: 1,411 Python tests pass (49.70 seconds), eleven native unit tests and
eleven simulated UI tests pass. UI tests ran in a separate no-Internet demo package
on Moto g52 and were removed afterward. Cases cover repeated recent-data reuse with
a visible message, first acquisition, changed hashes/universe and intentional fresh
download. A synthetic API test independently reopens SQLite, verifies exact ₹25,000.00
cash/full logical contents and unchanged saved files/provider-call counts after audits.
Real read-only source audit confirms the user's saved Nifty 100 download is valid;
live production-button/provider acceptance remains separate from simulated tests.
The exact compiled production reuse predicate also accepted that live audit and
rejected its unaudited equivalent without submitting a download. The original saved
job `a1b0a119d53032599137ff00212cf76c` and 16:55:08 UTC snapshot remained unchanged.

Signed 1.0.4 / code 5 was installed in place on Moto g52, preserving its pairing.
Deployed/verified `v0.20.4-20261028T171417-775c61599b3d`, Trader PID 29643;
public/local health, installed/source hashes and published APK match. APK SHA-256:
`26f4ad9613151456295d1a415c649b226711d73bb4ef382f4cd3ab87c42b6e35`.
Both full account DB/config hashes unchanged; Advisor/Monitor PIDs 1193/1194 unchanged.
Private evidence:
`/var/backups/trading-services-v0.20.4-20261028T171417-775c61599b3d/acceptance.json`.

## 28 October 2026 — backend 0.20.3 / Android 1.0.3 supplied app icon

Selected the user's wordless `images/Futuristic Fintech Growth Icon.png` for clear
small-size recognition. Added five legacy and five adaptive foreground densities,
navy adaptive background/padding and normal/round manifest resources. The transparent
white notification glyph is separate from the full-color launcher. Source images
are preserved. macOS `scripts/build_android_icons.py` documents reproducible packaging.
No financial or authentication policy change; updates retain the same signing identity.

Before this icon update, actual 1.0.2 fingerprint login was verified with authenticated
controls, loaded account values and no network/auth error. Later idle locking hid
private values as intended. This is device access evidence, not broker acceptance.
Validation: ten PNG dimensions independently checked, 192 px preview visually
inspected, seven native unit tests and 42 focused API/public-path/deployment tests
passed. Release lint: zero errors / 36 advisories (including legacy icon shape and
optional monochrome support). APK v3 signature/manifest verified. Actual Moto install
confirms 1.0.3 / version code 4, successful cold launch and retained authenticated
controls without network/auth errors. No fresh enrollment was submitted.

Deployed `v0.20.3-20261028T164611-8df9aa2528da`, Trader PID 28798. Public/local
health, source/installed hashes and public 1.0.3 APK match; SHA-256
`a5dfb86a902fc184a783bf9fd8d56e142b55c1665a3f04c08edf418c2fbb413b`.
Both account DB/configuration comparisons unchanged; Advisor/Monitor PIDs 1193/1194
unchanged. Private evidence:
`/var/backups/trading-services-v0.20.3-20261028T164611-8df9aa2528da/acceptance.json`.

## 28 October 2026 — backend 0.20.2 / Android 1.0.2 background-lock fix

Actual Moto logs exposed a second issue: closing a Conscrypt TLS socket during
locking/cancellation could send network records on the UI thread and crash with
`NetworkOnMainThreadException`. Cleanup now runs on a dedicated background worker,
while local token/UI clearing remains immediate. The retiring client is swapped out
first, so late cleanup cannot cancel a new unlock. The 1.0.1 idle-socket and paired-
state fixes remain; there is no automatic financial retry or disabled TLS/StrictMode.

Seven native unit tests pass, including idle socket retirement/single submission
and background cleanup surviving an injected closing failure. Added an explicit
opt-in production device test using only public release GETs, a 6.5-second idle wait,
UI-thread cancellation, completed cleanup and a fresh-client read. No credential or
account instruction is sent by that test. The opt-in test passed on the actual Moto
g52 in a temporary package compiling the exact transport/test sources (7.066 seconds).
The temporary package was removed. Full validation: 1,410 Python (61.33 seconds),
244 Node UI, seven native unit tests, Ruff/format/mypy/secret/whitespace checks and
release lint (zero errors). Signed 1.0.2 / version code 3 updated the Moto in place;
its existing encrypted pairing remained available. No new device enrollment occurred.

Deployed `v0.20.2-20261028T163249-8e5e7ba037e2`, Trader PID 28144. Public/local
health, source/installed hashes and public 1.0.2 APK bytes verified; SHA-256
`4279b34a2000860a571d9a958c5dd33521f066ee7da3011052cf1cf6512167ed`.
Both full account databases/configuration hashes were unchanged; Advisor/Monitor
PIDs 1193/1194 unchanged. Private evidence is under
`/var/backups/trading-services-v0.20.2-20261028T163249-8e5e7ba037e2`.
Actual 1.0.2 user biometric login loaded account values without network/auth errors;
later idle locking hid private values. Broker/history and biometric enrollment-change
acceptance remain separate.

## 28 October 2026 — backend 0.20.1 / Android 1.0.1 connection recovery

Actual Moto g52 pairing saved its encrypted credential, but a subsequent request
reported an unknown result. A separate credential-free probe reproduced OkHttp's
`unexpected end of stream` after 6.5 seconds idle against the public server. The
client now retires idle connections after one second, ahead of the upstream close;
automatic network retries remain disabled. After biometric encryption succeeds,
paired UI state is retained even if the session request fails, so unlock is offered
instead of fresh enrollment. Existing encrypted pairings survive signed in-place updates.

Validation: 1,410 Python tests and six Android unit tests pass; the new socket-level
regression verifies two fresh connections and exactly one submission of an invented
instruction after idle. Release lint has zero errors. Signed APK 1.0.1 (version code 2)
uses the existing certificate and verifies its manifest/signature. Actual handset
network/update checks and publication are recorded below when completed; this does
not establish real broker/history acceptance or authorize any account action.

## 28 October 2026 — backend 0.20.0 / native Android 1.0.0

Subsequent device check: installed the signed 1.0.0 APK on the user's connected
Moto g52 (Android 13 / API 33). Package/version and successful cold launch verified;
biometric pairing, broker login and update acceptance remain pending. No credential
was supplied and no account action was performed.

Added a native Kotlin/Compose light-mode Android app with sixteen destinations:
account/readiness, discovery, candle/indicator research, preparation/reviews, paper
proposals/modes, holdings/purchases/SIP, history/fills, complete policy draft editing,
backtest jobs/reports/comparison, risk controls, broker setup, settings/security/help.
Home's preparation action checks profile/catalog and acquires current history,
resuming after system-browser Zerodha login and biometric unlock. Source/calendar/
policy reviews and consequential account actions retain explicit confirmations.

Phone access pairs once using owner authority, then encrypts a separate revocable
credential with a hardware-backed strong-biometric-bound Keystore key. Short-lived
memory-only API sessions use scoped routes; hashed private pairing storage is separate
from the ledger. Added nonce/phone-bound one-time broker callbacks, public installer
integrity checks and versioned APK bundling. Production disables cleartext, backup,
screenshots and background account access. Durable outcome markers prevent silent
resubmission after timeout/background cancellation; stale reads disable actions.
Android offset timestamp parsing, exact decimal display and unsaved policy recovery
are covered by native tests. Optional generic proposal alerts are foreground-only.

Validation: **1,410 Python, 244 Node browser UI, five Android unit, seven offline
Android workflow and two production negative-security tests passed**. Release lint
has zero errors (28 dependency/style advisories); Ruff/format, mypy and whitespace
checks pass. Actual signed/minified 3.3 MiB APK signature/manifest verified, installed
and launched on the isolated API 33 ARM64 emulator. Synthetic tests independently
verify exact purchase fees/debits, replay idempotency and persisted SQLite state.
Emulator evidence does not establish positive hardware biometrics, actual phone
installation/update, real broker login or history entitlement.

Deployed `v0.20.0-20261028T152359-e41c1fc957f7`, Trader PID **26277**, with public
health/version/source/installed hashes and downloaded Android **1.0.0** bytes verified.
APK SHA-256 `65cf75cb2735dc78eafaec50d88b2fb8d965373c1b42380b5bb34225c5745c79`.
Full independent logical comparisons found both account DBs unchanged; private config
hashes matched and Advisor/Monitor retained PIDs **1193/1194**. Previous 0.19.2 code
is retained. Private acceptance/rollback evidence is in
`/var/backups/trading-services-v0.20.0-20261028T152359-e41c1fc957f7`.

See [Android installation/use/recovery](android-app.md) and [native access component](mobile-api.md).
Android 11+, strong hardware-backed biometrics and actual handset acceptance remain
requirements. RPi backtest isolation can remain unavailable; no background push or
new investment-engine milestone is claimed. Private signing identity stays locally
under ignored `android/.signing`; retain a private backup for compatible updates.

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

## 2026-10-24 — Issue-report corrections and reliability fixes

Re-audited the 0.14.0 report against current 0.19.0 code and added a
[finding-by-finding disposition matrix](../PROJECT_ISSUES_GAPS_AND_IMPROVEMENTS.md).
Corrected obsolete claims about daily delivery replay, adjusted daily/weekly/monthly
research, investment-policy drafts and manual SIP templates. Genuine product gaps
remain labelled rather than reported complete.

Manual broker-feed frames now share one financial commit without dropping accepted
quote events or per-quote risk/fill checks. Live processing time is sampled per quote;
failed frames roll back financial changes and revoke symbol trust. Independent
query-only WAL snapshots remove writer reservation from selected operator reads.
Candle commits and the automated controller retain their documented separate behavior;
engine serialization and journal growth remain limitations.

Added `stream_limit` (default ten, range 1–3,000), bounded full-mode frames/subscription
batches and expanded feed/history bounds while preserving financial fingerprints.
Setup API/status, accessible labels/input capacity and confirmation now reflect the
configured ceiling; only symbol-selection requests get the bounded larger body budget.
Replaced regex TOML rewriting with `tomlkit` while retaining schema/policy validation
and private atomic replacement. A shared nonblocking lock helper selects POSIX or
Windows APIs across account/auxiliary stores.

An indexed read-only proposal-alert endpoint supports a cross-section workspace banner,
count/deadline/title and opt-in desktop notifications. Expiry/stale/failure/Lock states
stay explicit, countdowns avoid repeated live-region announcements and known price-gap/
calendar/review errors give actionable guidance. Alerts do not approve trades or extend
deadlines. See [usage/recovery](how-to-use.md) and [persistence limits](quote-persistence.md).

Validation: **1,292 Python tests and 202 Node UI tests passed**; **91.98% statement
coverage** (11,106/12,075), Ruff lint/format, mypy on 125 source files, offline dependency
lock validation and whitespace checks passed. New tests independently check exact cash,
fees/delivery-DP, persisted sequential/batch equivalence, protective exits/partial fills,
rollback/freshness, committed reads, configuration/ownership failures, expanded selection
and alert authority. The suite emitted 63 SQLite ResourceWarnings in existing test paths;
these were not treated as evidence of fault-free resource lifecycle.

Disposable Firefox desktop/320×480 checks verified proposal visibility across sections,
readable controls and Lock cleanup; independent SQLite reads showed ₹25,000 cash,
zero orders/fills/positions and the unchanged awaiting proposal. These were invented
local fixtures, not operator/broker acceptance. No user account or broker action was
performed. Native Windows operation, real-feed scale, physical-device notification
visibility and full multi-year investment/rebalance/fundamental/security migrations
remain open. See [validation scope](test-plan.md).

## 2026-10-23 — Daily reports, independent supervision and guarded acquisition

Implemented observation/acquisition/evidence recommendations from the
[checklist review](agentic-trader-checklist-review-and-findings.html). Added authenticated
`/api/operations` and `daily-report` with reason-coded prerequisites, source-date/hash/
session coverage, independent exact accounting verification, bounded order lifecycle
details, pending exits and actual current authority. Broker profile success now has
a separate timestamp without asserting continuing token validity.

Added `operations-watch` and `scripts/start_operations.sh` for independent local alert/
recovery transitions, five-minute audits and observed daily snapshots. Explicit opt-in
schedules one current-IST-date acquisition attempt through existing preparation with
session/account/order/catalog/broker gates and durable receipts. Unknown outcomes are
inspected rather than replayed. No source/basis attestation, installation, connection
or mode change is performed. Added inactive launchd/systemd templates.

`operations-backup` / `operations-restore-drill` privately preserve and verify the
stopped ledger/config/calendar/installed strategy/data/model set without order recovery.
Drill success verifies isolated artifacts/accounting, not path rebinding/service startup.
See [usage, limits and recovery](operations-automation.md). **1,248 Python / 193 UI
tests passed**, with Ruff lint/format, mypy, shell/plist checks. External broker/market/
device acceptance, remote alerts, encrypted off-device retention and full deployment
restoration remain separate work; explicit trading authority is preserved.

## 2026-10-23 — Daily manual-operation and strategy-data guide

Added [daily-operator-checklist.md](daily-operator-checklist.md) with the contents and
purpose of strategy downloads, per-trading-day guided refresh, current IST source-date
checks, same-day reuse and after-close refresh behavior. Documents each manual step,
why it is required, expected results and recovery, from startup/broker access through
source/basis review, activation, order supervision and end-of-day reports/backups.
Distinguishes initial setup, conditional tasks, long-term holdings and intraday exits;
clarifies that downloads do not update themselves, train ML or authorize trades.
Linked from how-to-use, strategy preparation and runbook; clarified the usage guide's
intraday flatness instruction for long-term operators.

Validation: reviewed against current launcher/controllers/CLI and existing component
guides; **128 local Markdown links across six files passed**, and official Kite
authentication/candle references were checked. `git diff --check` passed.
Documentation only; no new runtime tests or financial changes. No broker downloads,
operator attestations, order activity or external acceptance performed.

## 2026-10-23 — Workspace usability and local icons (0.19.0)

Added a same-origin SVG icon sprite for all twelve labelled navigation destinations
and selected access, refresh and section headings. Icons remain decorative; text,
keyboard focus, active-destination semantics and confirmations carry their meaning.
The compact header preserves paper identity and lock access. Setup keeps its next
step visible while its longer explanation starts collapsed after unlock. Removed
the repeated general unsaved-form notice; actual draft/request/navigation guards remain.

Shortened routine saved-view feedback without changing observation timestamps or stale
states. Portfolio keeps valuation coverage visible and groups scope/formulas in details;
Stock Analysis groups chart help/legend. Policy drafts present their existing four
groups as steps with progress, Previous group/Next group, unit-aware help and field-linked errors.
Step navigation has no persistence or financial defaults; exact preview and explicit
acknowledged save remain unchanged. Shared responsive styles retain readable exact
tables, visible focus and labelled touch targets. No financial or broker behavior changes.

Backtest evidence tables are individually expandable, with bounded scrolling; bundle
labels lead job cards and full job identity remains available. Risk actions are split
into emergency and entry fieldsets. Analysis distinguishes an empty stock inventory
from an unmatched search and disables Open chart without a result. Corrected policy
previews clear obsolete error feedback.

Validation: **1,216 Python / 193 UI tests**, **92.13% statement coverage**, Ruff lint,
source/test formatting and mypy pass. Disposable desktop Firefox checked rendering,
policy step/validation/dialog/Escape, Portfolio warnings and Risk grouping; independent
SQL showed unchanged empty-account accounting. No user account or broker action.

See [usage, component behavior and recovery](ui-experience.md). Validation scope is
recorded in [test-plan.md](test-plan.md); rendered checks must use a disposable account.
Full Phase 5, native-worker, investment execution/rebalance and external broker/device
acceptance remain open; this usability pass does not close those gates.

## 2026-10-23 — V2 Phase 5 investment-policy drafts and date previews (0.18.0)

Added a separate nullable schema-1 investment-policy draft family with months/years
horizons, monthly/quarterly reviews and explicit screening/allocation/exit choices.
No investment value is preselected. Strict exact decimal strings normalize to four
places (turnover two), invalid types/precision/choices fail, and allocation caps must
agree. Semantic identity excludes names/time/storage; only fully specified drafts gain
a proposed policy-version hash, with activation/backtesting still unsupported.

Strategies now links to `#strategies/investment-policy`: four labelled parameter groups,
incomplete drafts, exact preview/acknowledgement, immutable saved snapshots and **Edit
a copy**. Separate owner-private `.investment-policies` storage revalidates identities,
bounds and permissions; an identical reviewed save returns its existing snapshot.
Unsaved edits guard navigation, and uncertain saves require refresh/reconciliation
before an explicitly confirmed same-content retry. No automatic save/retry is performed.
Existing strategy preparation, legacy anchors and account controls remain available.
Unsaved/request/review state also triggers the browser's standard unload warning;
explicit lock clears local choices. Malformed preview responses cannot leave an
invisible pending dialog or block recovery.

Added pure calendar-month/year review-date previews and stdout-only `investment-policy`
CLI inspection. Dates use explicit original-day clamping, exclusive anniversary end,
full calendar-month/quarter coverage and an aware knowledge clock. Calendar completeness
is an unverified operator assertion. Missing/future-known evidence stays unavailable;
out-of-horizon reviews are skipped, empty covered periods never invent weekdays, and
the 400-cycle budget returns unavailability rather than hidden truncation.

See [commands, schemas, persistence and recovery](investment-policy-drafts.md) and
[validation record](test-plan.md). This remains a partial Phase 5 delivery: draft policy
execution/backtest adapters, connected parity, target/rebalance, OOS/walk-forward and
real-market/platform/device acceptance are unfinished. The 0.17 browser-job runtime gate
remains unavailable on the implementation Mac. No active policy, paper mode, account
cash/holding, broker credential or order is changed by creating these research drafts.
Validation: **1,213 Python / 186 UI tests**, **92.13% statement coverage**,
Ruff/format/mypy passed. A disposable Firefox workflow saved and reopened a draft;
independent file/SQL checks preserved its virtual cash, fees, orders and holdings.
Corrected accidental dependency-version edits; all 66 dependency lock records retain
their original pins, with only the project release version changed.

## 2026-10-22 — V2 Phase 5 registered jobs and portfolio analytics slice (0.17.0)

Added `research_jobs/`: CLI-only immutable input registration, one-worker/one-queue
admission, resource/hash-bound idempotency, durable job/cancel/restart states and verified
bounded report publication. `/api/backtests/*` authenticates existing local operator
access; browser mutations require explicit acknowledgement, with no path/upload/model
execution input. Workers get a separate scratch ledger, an allowlisted environment,
Darwin OS sandbox and verified hard budgets. The UI reviews policy/source/holding cap,
retains failed/cancelled/interrupted states, reconciles uncertain submissions using the
same request key and compares only identical registered resources/methods.
Resource identity also binds the Python implementation hash and complete observed fee
schedule. Changed code/costs require registration/review again before admission; reports
must retain the reviewed runtime identity as well as passing independent financial checks.

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
validation is recorded in [test-plan.md](test-plan.md): **958 Python / 172 UI tests**,
**91.87% statement coverage**, Ruff/mypy passed. A disposable synthetic Firefox smoke
check passed input/unavailable-launch/allocation rendering; broader rendered/mobile,
sustained broker/device, source licensing and profitability acceptance remain separate.

## 2026-10-22 — V2 Phase 4 causal price research (0.16.0)

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


## 2026-10-22 — V2 Phase 3 shared frontend and saved-state workspace (0.15.0)

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


## 2026-10-22 — V2 Phase 2 architecture and UX contracts

- Completed the approved design phase in [phase-2/README.md](phase-2/README.md):
  architecture/authority/migration, twelve grouped screens/aliases, screen/component
  and light-theme specifications, exact financial/provenance/null definitions,
  data/indicator/policy parity, API/idempotency/job/error/recovery contracts.
- Added a clearly nonconnected offline prototype, navigation manifest, synthetic
  arithmetic fixtures, 15 proposed strategy acceptance vectors and reproducible
  design validators. No application code, risk default, account, route, credential,
  policy or runtime version changed; Phases 3–6 remain implementation work.
- Actual checks passed: 6 prototype DOM tests, design/route/link/HTML/offline checks,
  11 palette contrast pairs and 129 independent arithmetic/contract comparisons
  across 7 invented ledger cases/2 return paths; Ruff/format/whitespace passed.
  Strategy scenarios are specified, not executed financial workflows. The runtime
  suite was not rerun for documentation-only work. Rendered browser, broker/device,
  source licensing and empirical strategy acceptance remain separate future gates.
- Updated main/component usage references, the V2 proposal and historical delivery
  record. Next implementation slice is shared confirmation reliability and navigation.


## 2026-10-22 — V2 Phase 1 audit and approval plan

- Added architecture and UX audits, requirements gap matrix, phased implementation
  proposal and deferred intraday roadmap from `improvements.txt`. Audited baseline
  commit `2d5c208`/0.14.0; no application code or operator account changes in this phase.
- Verified existing CLI research/backtesting, paper execution and exact accounting
  instead of labelling those modules absent. Identified product gaps, early-year
  calendar failure, strategy-parity differences, legacy intraday repeat false-pause,
  broker recovery/provenance/audit gaps and rendered modal/browser acceptance needs.
- Fresh tests: 660 Python passed with 92.13% statement coverage, 117 Node UI tests,
  Ruff and mypy (98 source files) passed. Limited project secret scan clean. Test
  SQLite ResourceWarnings recorded; no full production security/device acceptance claim.
  A disposable setup-controller geometry check passed, without a feed/connect mutation.
- Documentation links point to the V2 proposal; implementation requires the user's
  explicit post-audit approval. No framework migration, real order or risk relaxation.


## 2026-10-22 — 0.14.0 light workspace and saved-data analysis

- Replace the dark tab strip with a responsive light sidebar: Dashboard, Market &
  Analysis, Strategies, Paper Trading, Risk Center and Broker & Settings. Keep
  Purchases & SIP as a subordinate workflow and Help/onboarding outside the main areas.
- Lead Dashboard with exact account equity/cash, dated daily P&L, position count,
  stale/incomplete valuation notices, market status and next action. Separate strategy
  preparation/shortlist at `/strategies`; preserve existing preview/confirmation and
  legacy desk fragments. Activity counts state their page/window scope.
- Guide broker setup with actual connection/session/calendar/subscription state and
  six keyboard-accessible disclosure steps. Open the relevant first step once;
  preserve operator edits/open steps on refresh. Navigation does not save settings.
- Add authenticated read-only `/api/analysis` and the Market & Analysis screen: saved
  completed daily/1m/5m OHLC, volume, SMA 20/50, exact table, quote status and prior
  screening context. No broker download, subscription, strategy evaluation or trade
  occurs on viewing. Preserve raw basis, data gaps/integrity/availability checks and
  explicit unknown minute-bar provenance. See [market-analysis.md](market-analysis.md).
- Keep in-memory unlock, origin/window checks, financial gates and operator action
  contracts. No new strategy builder, graphical backtest or performance promise is
  supplied. Version alignment prevents the launcher silently reusing an older server.
- Validation: 660 Python and 117 UI tests, Ruff lint/format and mypy (98 source files)
  passed; details and limits are recorded in [test-plan.md](test-plan.md).
  The running operator account was not restarted or used for test orders. Firefox
  capture did not reliably render the disposable preview; visual/device acceptance
  remains outstanding.


## 2026-10-22 — Prevent false quote-order pauses and explain cancelled signals

- Fix live whole-second Kite handling: ignore unchanged repeats without refreshing
  freshness, and accept changed tied books only in strict receipt order with valid
  identity/source/volume. Update marks/protection/candles while skipping repeated fill
  processing at that exchange timestamp. Replay/backward/ambiguous and financial guards
  remain; no timestamp or liquidity is invented.
- Persist specific pause causes and previous-mode events; distinguish cancelled
  unapproved proposals from orders and display both proposal/update times. Explain
  daily signals already handled, preserving terminal history and no automatic replay
  when switching to Automatic. No trade, mode activation or retry was introduced.
- Validation: 650 Python and 99 UI tests; Ruff and mypy passed. Independent exact
  ledger, tied-book/fill/protection/candle, authority-revocation and raw-callback tests
  passed. A separate isolated eight-second real-feed engine accepted 68 quotes with
  20 changed tied books, zero quality failures/faults and no orders; sustained/device
  acceptance is still separate. The running operator account was not restarted/rearmed.
- Updated usage, trading desk, feed, risk, API, architecture, implementation and test
  guides. A real backend restart is required to load these Python changes; existing
  cancelled daily proposals remain terminal after the upgrade.

## 2026-10-22 — Make pending daily review directly actionable

- Add **Review today’s setup** beside next-step/quote warnings and readiness cards.
  Reuse the existing guided summary, unchecked acknowledgement and explicit confirmation.
  Retain an installed policy without a first-policy default or ML fallback. Require
  same-day source data/Manual/supported setup; show stale/unavailable recovery guidance.
- Hide the shortcut after resolution and clear it on lock; cancel/preview/restart do
  not approve reviews. Updated usage, strategy, workspace and validation documentation.
- Validation: 97 UI tests and 17 guided unit/API workflow tests passed; Ruff passed.
  New independent persisted-state checks cover the preview/confirmation boundary.
- Distinct actual observation: today's 65-stock/60-session download and preview completed;
  later read-only status showed seven current-day reviews, accepted quote timestamps
  and zero blockers in Manual, with ₹25,000 cash, zero fees and no trades. No review
  confirmation was submitted by this assistant; sustained/device acceptance remains open.

## 2026-10-22 — Explain blocked live quotes and repair shortlist navigation

- Confirmed from the existing journal that incoming quotes for eight selected symbols
  were blocked by missing current-day price-basis reviews. Yesterday's reviews do not
  cover today; no review or quote-acceptance safeguard was relaxed.
- Replaced generic stale/missing labels with shared read-only basis/feed/quality/clock
  explanations. Show the reviewed session's current open/closed state and specific
  next actions, instead of always telling an open-session operator to wait for opening.
- Preserve readiness-link fragments through the workspace; reveal/focus shortlist and
  quote details after unlock/render, expand details and scroll below sticky navigation.
  Legacy `/desk#apply-shortlist` opens the containing review section. Opening links
  does not apply a shortlist; feed/Manual/no-pending and explicit confirmation remain.
- Validation: 637 Python and 90 JavaScript tests, Ruff and mypy passed. Independent
  persisted financial-state equality, daily rollover/new-quote requirements, navigation,
  focus, responsive offsets and origin checks are covered with simulated workflows.
  Actual account inspection was read-only; broker/device execution acceptance remains
  pending. Reload workspace assets; restart an older Python server for new diagnostics.

## 2026-10-22 — Explain feed symbols and default session hours

- Explain catalog lookup versus the saved live-feed watchlist, the application limit
  of ten subscriptions, token/tick meanings and broader Trading desk screening. Label
  saved subscriptions/count separately from unsaved symbol input.
- Default editable session times to 09:15 AM / 03:30 PM IST on unlock. Refresh keeps
  edits; date/source review and explicit confirmation are required before any save.
  No account selection, existing session or financial policy is changed by loading.
- Updated main/detailed usage, workspace and implementation docs. Validation: 28
  setup/workspace JavaScript and 24 setup unit/API tests passed, including independent
  persisted calendar and exact financial-state checks. Broker responses are simulated;
  interactive desktop/mobile acceptance of these changes remains pending.

## 2026-10-22 — Visible saved broker session checks

- Show step-3 progress and success/failure beside the broker session buttons, with
  a pending check label, duplicate prevention and explicit timeout/retry/login recovery.
  Failed rechecks clear the page's stale verification claim. Login/exchange requests
  also show inline progress/results; lock/auth failures clear private feedback.
- Updated usage, setup, workspace and implementation documentation. UI-only assets
  load on section re-entry or workspace reload; no server restart is required.
- Validation: 25 setup/workspace JavaScript tests and 23 setup unit/API Python tests
  passed, including exact cash and independent persisted database/config/credential
  preservation through mocked profile success, failure and retry. Firefox subsequently
  displayed “Profile verified this run”; no independent broker/streaming acceptance is
  claimed. Coordinate automation returned `noWindowsAvailable`, limiting browser QA.

## 2026-10-21 — One combined paper setup review (0.13.1)

- Replaced the normal CSV/notes/multiple-review workflow with policy selection and one
  source/calendar/stock summary and acknowledgement. Advanced individual controls remain.
- Coordinated disconnect, strategy/calendar installation, held-preserving ranked shortlist,
  explicitly listed eligible reviews for today and feed reconnection. Setup stays Manual;
  Approval/Automatic still need separate confirmation after actual readiness passes.
- Added two-minute account/source-bound previews, durable phase/outcome reporting,
  completed-retry idempotence and interruption recovery without replay. Pending orders,
  used-calendar conflicts, faults and unqualified stocks cannot be bypassed. Held-position
  basis, quarantines and uncovered histories keep their separate review requirements.
- Added visible-parent viewport sizing/positioning for embedded setup and mode/trade confirmation dialogs, private
  summary clearing on lock, navigation/poll guards and specific timeout recovery messaging.
- Corrected Nifty 100 source links; updated main/detailed usage, component, API, architecture,
  implementation and validation guides. No actual account review, mode or trade was activated.


- Validation: 630 Python and 77 JavaScript tests, 92% coverage; lint/format/types, frozen
  offline environment, build, secrets and isolated desktop/mobile browser flow passed.

## 2026-10-21 — Genuine-data strategy preparation and clearer readiness (0.13.0)

- Added in-app Nifty 100/500 source/history acquisition, cancellable background progress,
  official source snapshots/hashes, action/catalog/coverage exclusions and shared historical
  read pacing. Added read-only daily candles without an order-capable broker transport.
- Added explicit calendar/basis/policy reviews, editable session CSV, experimental rules
  choice or separately supplied validated ML, immutable profile installation and hashed
  restart selection. Installation stays Manual and requires disconnected/no-pending state.
- Distinguished prospective current constituent snapshots from historical point-in-time
  membership; retrospective daily execution/ML refuses the former. Retrieval and review
  clocks are not backdated.
- Added per-prerequisite actions, current IST/entry/session information, quote age/basis,
  missing-profile guidance directly beside disabled modes and preserved review form edits.
- Updated main/detailed usage, source/provenance, test, component and implementation guides.
  A real read-only probe verified official sources and one full 60-session broker response;
  no user strategy, review, mode or order was activated by that check.
- Completed a separate genuine Nifty 100 download into private pending-review artifacts:
  65 × 60 completed daily rows, 35 conservative action exclusions. Used a read-only
  catalog connection; no account/configuration writes or review/mode activation.
- Validation: 614 Python tests, 71 JavaScript tests, 92% coverage; Ruff, mypy, frozen
  offline environment, build and secret checks. Isolated synthetic desktop/mobile browser
  checks verified the review/installation flow and shared unlock without exceptions.
- Show saved/proposed session conflicts and allow a separately acknowledged correction
  only for an unused account. Quote/review/execution/instruction usage protects history,
  rechecked after validation. Explain 15:30 exchange close versus 15:15 strategy flatten.
  Block arming during installation and reject mixed-date source downloads.
- Handle temporary index constituents above the named count; explicitly exclude REIT/
  trade-to-trade/dummy rows. Real Nifty 500 parsing retained 495 supported shares from
  501 source rows; no unsupported class is promoted to an equity share.

## 2026-10-21 — Trading desk, approval modes and explainable activity (0.12.0)

Added a default Trading desk with actual mode/activation, clear data blockers,
proposal-first layout and separate Buy / sell activity. Manual, per-trade approval
and automatic paper modes work with reviewed intraday and long-term profiles; legacy
bound intraday can route through the same approval workflow. Protective exits remain
independent. Browser section changes retain one unlock; mobile uses a horizontally
scrollable menu with accessible header Lock. Fixed a misleading initial locked
message after successful desk unlock. No real-order capability was added.

Broader discovery reads reviewed real daily bundles for up to 500 symbols, separates
share classification from catalog EQ, excludes unsupported/unmatched candidates and
previews a held-preserving catalog shortlist of at most ten. Current quotes and
completed intraday/prior-daily rules drive proposals. Rules-plus-ML requires a matching
independently validated model; no synthetic model/data or silent fallback is permitted
in connected profile loading. This does not supply a real bundle/model, automatic
broad-data acquisition or empirically qualified expected-profit ranking. The existing
five-symbol account, capital, mode, reviews and broker session were not changed.

Approval previews enforce expiry, profile/mode generation, live price/signal gaps,
quantity/cash/price/risk bounds, and fresh independent broker checks. BUY authority is
journaled before submission and fingerprint-verified/journaled in the broker transaction;
recovery links a matching committed order or cancels unsubmitted authority without
replay. A second clock check after durable authorization prevents stale execution
through a slow write, clock regression, session/expiry or model-age rollover. Manual
feed callbacks also measure freshness after acquiring the risk lock, so queued stale
quotes cannot fill another pending order using a clock captured before lock wait. SELL linkage is atomic. Mode/data/risk pauses revoke memory authority before
I/O and cancel unfilled desk buys. Short feed disconnects notify the desk immediately,
so reconnecting before the watchdog poll cannot restore authority. Activity retains
manual/legacy/protective origins, actual fills/fees, declined/expired/blocked proposals
and exact cash flow with bounded order/fill cursor pages.

Validation: **582 Python tests**, **62 JavaScript tests**, **92% Python coverage**;
lint/types/secrets, frozen offline environment and source/wheel build checks passed.
Tests include both signal pipelines, real rule evaluation with mocked history, model
threshold revalidation, quote/holding/mode changes, approval quantity bounds, immediate
feed revocation, protective exits without approval, loss-response/restart recovery,
journal corruption, exact independent ledger checks, held shortlist preservation,
more than 100 partial fills and nonblocking risk controls during slow history I/O.
An isolated headless browser verified desktop/390-pixel layouts, no page overflow,
shared unlock, explicit preview/confirmation and ACCEPTED with zero fills in activity.
Synthetic small-fixture loopback p99: desk **0.9474 ms**, activity **0.7265 ms**;
[benchmark scope](benchmark-desk-macos.json) excludes external acquisition, broad-market
load, real-market profit acceptance and Pi/physical-phone evidence. All browser/demo
orders used separate temporary synthetic accounts. User-owned services were not restarted.

## 2026-10-21 — Keep after-hours empty books from disconnecting the feed (0.11.1)

Fixed the verified full-packet parser failure when the broker sends an empty bid/ask
or zero side quantity. Ignore these observations without emitting an executable quote
or disconnecting; preserve valid packets elsewhere in the batch and strict framing,
identity and remaining Quote validation. No financial policy or order capability changes.
Earlier executable depth for an affected symbol immediately loses freshness; manual
candle builders reset and intraday applies its existing stale-data safeguards. A later
valid quote cannot silently rearm automation. Conflicting same-symbol packets in one
batch cannot restore freshness past an observed empty book.
Setup now reports credential-free connection state, bounded retry progress/exhaustion,
fixed failure categories, last transport receipt time and ignored-book count, with
clear recovery instructions. Raw broker messages/authenticated URLs stay private.

Validation: **547 Python tests**, **56 JavaScript tests**, **93% Python coverage**;
Ruff/mypy passed. Unit cases cover each empty side/quantity, mixed packets, unknown
tokens/trailing corruption and retry exhaustion/redaction. A functional pending-order
case keeps the socket connected while proving exact unchanged cash/fees/reservations,
orders/positions and no fill. Unit/service checks also prove prior fresh depth cannot
authorize a new entry, valid data restores freshness, and automation disarms without
losing the transport or rearming. Actual isolated read-only worker check remained connected
for 15 seconds with five ignored books and no usable quotes/orders. User-owned server
and persisted account were left untouched. Port 8004 was no longer listening at the
final check; start the launcher to load the fix and explicitly reconnect. Fresh
market/full-session, sustained device and actual paper-fill acceptance remain pending.

## 2026-10-21 — Shared menu, one workspace unlock and next-step guidance (0.11.0)

Added `/workspace` with Start here, Trading console, Broker & feed setup and Purchases
& SIP. One local in-memory unlock now covers menu navigation. Explicit lock, reload/
new workspace tabs and authorization failures require a new unlock; browser-tab
visibility alone does not log out. Late messages/responses cannot restore cleared
access. Fixed-route same-origin section handoff checks origin, frame window and active
view; only the three section routes permit same-origin framing, while outer/API
routes retain framing denial. Active mutations/dialogs/Setup login windows block
navigation. Changing sections clears unsaved forms/previews, not confirmed server work.

Added authenticated read-only workspace metadata and an actionable guide explaining
feed startup, genuine calendar/basis review, actual entry hours, manual long-term
entries, separately configured five-minute intraday signals and monitoring intervals.
Preserved manual CLI callback capture and the guarded broker popup handoff. Startup
opens the workspace directly and refuses reuse of older UI versions. No new dependency,
financial policy, automatic selector or trading scheduler was added. Updated relevant
usage, API, architecture, security, test and implementation documents.

Validation: **539 Python tests** and **54 JavaScript tests** passed, **93% Python
coverage**; Ruff/mypy, secret checks, frozen offline lock/sync and source/wheel build
passed. Package inspection includes the workspace assets and excludes private
account configs/data. HTTP/DOM checks cover frame policy, actual account cadence,
shared-token integration, pending-action guards, global lock and late responses.
Local read-only account inspection preserves ₹25,000.00, zero fees/positions/pending
orders and matching risk policy. The operator-owned 8004 process was left running;
one manual restart is needed to load the new backend routes. No broker login,
connection change, attestation, arming or order was performed during this change.
Physical-browser/phone/pixel and actual popup acceptance remain distinct pending checks.

## 2026-10-21 — Clarified profit-oriented discovery scope and data gap

Recorded the operator's selection goal for both intraday and long-term paper trading:
broader candidates evaluated for potential net profit rather than a fixed five-symbol
watchlist. Added `stock-selection-plan.md` with data/universe acquisition, chronological
cost-aware validation, independent horizon rankings, explainable UI, execution approval
separation and prospective paper acceptance. This is pending work, not a stock-pick
or profitability claim. Read-only inspection found 5,184 catalog rows, no accepted
quotes/candles, six synthetic daily and sixteen synthetic intraday bundles, and no
declared-real input bundles of those inspected formats. No feed/account change or
order was performed. Linked main usage/implementation status and clarified that
Setup's disabled login requires disconnect only when replacing a session.
Validation: Markdown links, secret-pattern and whitespace checks; documentation-only,
so financial/unit/functional suites were not rerun.

## 2026-10-21 — Browser broker setup and repeatable UI startup (0.10.0)

Clarified all local unlock screens/errors: `TRADING_OPERATOR_TOKEN` is the local
credential, while the Zerodha redirect value is a short-lived request token for
broker exchange. Added `/setup` for authenticated manual-account credentials,
official login popup, origin/window/state-bound token handoff, explicit exchange
and profile verification, catalog import, exact selected-symbol/token/tick validation,
reviewed current/future calendar additions and feed connect/disconnect. Setup cannot
submit/arm, override risk, omit held symbols, change economic policy or rewrite
existing session definitions. Confirmations disclose resumed pending fills/exits.

UI broker values persist in a private atomic server-side file, not browser storage.
Secret request bodies are bounded and errors do not echo credentials. Login states
expire and are consumed before external exchange. Manual CLI redirects remain
supported. Calendar snapshots are written before config replacement; failures leave
the prior live/configured definition intact. The manual feed uses explicit server
credentials without mutating process environment; supervised automation stays separate.

Added executable `scripts/start_ui.sh`, safe authenticated reuse of a matching local
server, and `serve --open`. The shortcut loads trusted private environment files,
defaults to the workspace's existing first-session config, starts without a feed and
opens a browser. Existing server checks reject redirects, proxies and mismatched
account identity. No new dependency was added. Updated main/detailed usage, API,
operator, architecture, security, test and plan documents. External registration,
subscription payment and login/2FA still happen on Zerodha; policy/bootstrap,
complex corporate actions and research/model workflows are not all browser actions.

Validation: **535 Python tests passed**, **45 JavaScript tests passed**, **93% overall
Python coverage**; Ruff, mypy, secret-pattern/whitespace/shell checks, frozen offline
lock verification/environment sync and source/wheel build passed. No dependency was
added. The updated 8004 service returns 200 for console, portfolio, Setup/assets and
health; unauthenticated setup returns 401 and the correct local operator token works.
The selected five-symbol read-only stream reconnects, while calendar/basis gates
correctly leave readiness 503. Exact account reconciliation preserves ₹25,000.00,
zero fees/orders/positions and economic identity. The private `.env` selector was
corrected from the old 8001 config to the existing 8004 account. Actual shortcut reuse
preserved the running PID and opened the browser without another account process.
Private `config/*-session.toml` copies are now ignored by Git/source packaging.
Browser popup/2FA and physical phone/pixel acceptance remain operator-run; simulated
callback/DOM tests do not establish those checks. No actual token exchange, calendar
attestation, price-basis clearance, arming or order was submitted during this upgrade.

## 2026-10-21 — Operator-selected first read-only feed connection

Validated the operator's five supplied symbols/tokens/tick sizes against the local
downloaded NSE catalog and updated only the private first-session feed selection.
Checked actual Kite profile authentication without displaying personal fields or
credentials. Restarted the previously offline 8004 service with read-only streaming;
the authenticated console reports a connected feed and exactly the five selected
symbols. API state and read-only reconciliation preserve ₹25,000.00, zero fees,
no positions and no orders. Saved a separate private connection observation beside
preflight evidence; no account config, credentials or private evidence is committed.

Documented this partial external evidence separately from completed acceptance:
current calendar/long-term basis reviews are missing, full quotes are not accepted
for execution and readiness stays 503. No order, basis approval or calendar change
was performed. Found that a selected instrument is a gold ETF; documented the
existing equity-share fee assumption and missing ETF-specific policy/exclusion.
Instrument-class accounting is now an explicit prerequisite for ETF paper execution
claims. Updated usage, long-term, acceptance and plan guides. No application source
or economic policy changed; validation comprises actual profile/connection/API
observations, read-only accounting, Markdown links, secret scan and whitespace.

## 2026-10-21 — First-session dashboard startup diagnosis

Diagnosed the local first-session config retaining the long-term template's 8001
port and an empty stream selection. Corrected its local listener to 8004 without
changing financial identity or the existing account/database path. Started the
manual console without a feed while the operator selects instruments; an unrelated
older preview on 8001 remains running. Local loopback HTTP verification returned
200 for `/`, `/portfolio`, `/health` and authenticated `/api/status`; `/ready` is
correctly 503 without market/session prerequisites. Pre-start read-only accounting
reconciled ₹25,000.00, zero fees, no pending orders and no positions.

Expanded usage/first-session recovery instructions: preflight is not a server,
its limitations are informational, copied ports must match the browser URL, and
streaming requires an actual nonempty catalog selection. No broker login, market
session review, universe choice or order was performed. The operator's local config
and private credentials are not included in the documentation commit. Documentation
checks cover local links, secret patterns and whitespace; no application source or
financial behavior changed, so unit/functional suites were not rerun.

## 2026-10-21 — First live-data paper-session instructions

Added `first-paper-session.md`, linked from the main usage and horizon/feed guides.
Checked official developer registration, ₹500/month market-data plan, loopback
redirect and daily authentication lifecycle. Documented hidden token exchange,
private environment load order, fresh isolated account/catalog/calendar, manual
intraday API versus long-term portfolio UI, fill verification and daily recovery.
Distinguished the local simulator with production read-only data from the separately
documented, unintegrated Kite sandbox. Corrected older long-term wording that still
said additions/SIP were unavailable. No execution/account behavior changed; no
broker credentials, subscription, login or live-market acceptance was exercised.
Validation: 217 local Markdown targets, documented command help, secret-pattern scan
and whitespace checks passed. A fresh isolated synthetic `portfolio-demo` reconciled
₹25,273.45 cash, ₹22.35 fees and four acquisition lots; it made no broker requests.
Read-only default-account preflight preserved ₹25,000.00, zero fees/positions/orders
and the original policy identity. It correctly remains blocked by the unloaded
operator token, unreviewed current session and unselected catalog; broker entitlement
is unverified. Unit/functional suites were not rerun for documentation only.

## 2026-10-21 — LT3c1 reviewed contributions, acquisition history and SIP (0.9.0)

Started the next portfolio-management dependency after LT3b. Split LT3c into
contribution/SIP foundations, reviewed rebalance proposals and then aggregate
capital coordination, documenting which part is delivered. Added exact cash-budget
purchases and holding additions through read-only previews and explicit confirmation.
Preview hashes bind quote, holding/protections, cash/exposure/risk and plan context.
Existing-plus-new position capacity, fee-inclusive cash budget and shared broker risk
remain enforced. Ordinary manual intents still reject duplicate holdings; additions
cannot loosen stops/targets or override pending/latched exits.

Added immutable explicitly sourced-session SIP schedules, deterministic occurrence
identity and one confirmed attempt/date, due/upcoming/missed/cancelled states,
idempotent retries and atomic cancellation of pending plan residue. Filled shares
remain protected. No automatic deposits, holiday roll-forward, catch-up or unattended
purchase is inferred. Historical acquisition lots group original BUY fills/costs/fees;
current adjusted pooled holdings remain distinct from tax/FIFO ownership.

Added compatible empty tables/indexes, durable approval/plan events/schema, independent
authority/hash/order reconstruction, first-fill holding basis and later cap/clock
checks. Shared sizing was extracted without changing normal intraday economics or
legacy risk hashes. Restart cancels pending entry residue and returns existing intent
state on retry. Existing delivery/action/claim/DP and pooled capital P&L remain shared.
The security import check now parses AST across execution/portfolio/risk/action modules
instead of treating a table name containing `requests` as a network import.

Added authenticated responsive `/portfolio` UI, shared exact money formatter, concrete
preview/dialog, due-plan review, stale/lock/unknown-response handling, spent/reserved
cash, recent purchase orders, current holdings and original acquisition history.
Private values remain in memory/text DOM. Main console links to the new page.
Added deterministic `portfolio-demo` with separate frozen evidence and mutable UI
working copy/config/calendar, leaving configured accounts unopened.

Validation: **511 Python + 36 JavaScript tests, 92% Python coverage**. New cases cover
cash/protections/addition room, partial/restart/idempotency, stale/changed previews,
concurrency/atomic rollback, damaged proof, SIP authority/calendar/missed/cancel,
split→addition→partial sale→DP reconstruction, deterministic journal, isolated CLI,
authenticated/origin/typed API and UI preview/confirmation/lock/staleness/no-retry.
The invented lifecycle independently reconciles six shares sold, four acquisition
lots, ₹22.35 fees and ₹25,273.45 final cash = seed + ₹273.45 capital P&L.
Populated Mac benchmark: preview p99 **0.1784 ms** (1,000 calls), durable reviewed
addition plus next fill p99 **1.5532 ms** (twenty calls), retaining WAL/FULL. Network,
browser, warmup and actual Pi are excluded. Full usage/component/spec/plan docs updated.

Only LT3c1 is complete. Reviewed rebalance proposals, cross-account capital enforcement,
per-lot current/FIFO/tax attribution, funding/withdrawals, custody/settlement, actual
market/device acceptance and all live phases remain pending.

Final local checks: Ruff lint/format, mypy, frozen offline lock/sync and installed
package consistency pass. Sdist/wheel build and all shared/new console resources
load outside the repository. Secret checks and local links in 23 Markdown files pass;
online advisory audit reports no known vulnerabilities. Read-only preflight preserves
the original account at ₹25,000, zero fees/events/positions/orders and its original
risk hash; operator/calendar/broker/device readiness remains explicitly incomplete.
The separate demo copy runs at localhost:8003/portfolio; actual HTTP asset/CSP/auth/
four-lot checks pass and frozen source hashes remain intact while it runs. The page
was opened; browser pixel/physical-phone acceptance remains pending permissions.

## 2026-10-21 — LT3b daily quote execution and separate chronological ML (0.8.0)

Implemented the next long-term dependency after completed daily screening. Added
`daily-backtest`, `daily-labels`, `daily-train` and `daily-execution-demo --with-ml`,
using matching raw daily/quote bundles, reviewed sourced calendars, strict clocks,
current PIT membership and applied corporate-action reference basis. Prior daily
features advance once by availability with bounded windows and rare late-row rebuilds.
Daily decisions rank only simultaneous candidates and retain session-limit/screen exits.

Portfolio execution reuses the exact Decimal transactional delivery broker, risk,
latency/depth/adverse ticks, fees/DP, action and cash ledger. Fresh later quotes drive
fills; unfinished positions/orders/claims and missing coverage are preserved. Calendar
source definitions are retained for corporate-action review. Independent label trials
retain favorable/adverse completed full-entry outcomes and explicit unfilled, partial,
interrupted, stale/gap, capacity and unresolved exclusions. Cash-specific dividends/
receipts censor counterfactual trials rather than guessing different account deductions.

Added separate daily feature/model identity with whole-session interval purge/embargo,
train-only scaling, separate sigmoid calibration, fixed logistic baseline and frozen
final holdout. Coefficients freeze before holdout diagnostics; unsuccessful evidence
is retained but loading fails. Model availability follows source/label/session-close
evidence plus embargo, with a strictly later independent scored replay. JSON-only
pure Python scoring, context/hash/audit/cash checks, synthetic provenance/override and
existing independent risk remain enforced. Shared numerical helpers gained structural
types; intraday feature/model authorization and long-term service guards are unchanged.

Added responsive private self-contained portfolio/label/validation/scored dashboards:
exact money, IST clocks, search/view/clear, incomplete exposure, explicit label-vs-
portfolio meaning, chronological checks and useful failure/next-step guidance. Updated
main usage, detailed daily execution guide, plan/specification and corresponding
component docs. Standing documentation requirement remains in root AGENTS.md.

Validation: **479 Python + 29 JavaScript tests, 92% Python coverage**; financial
reconstruction/later fills, overnight/session-limit exits, sourced split replay,
dividend routing, exclusions, chronology/purge, audit/model tampering, failed gates,
no training imports during scoring, isolated CLI and UI exact-money/search/empty/
incomplete/failed-model cases. Full synthetic workflow produces 150 labels (100
positive, 50 adverse) and a distinct ten-session scored replay; no market edge is implied.
Twenty-run Mac durable replay p50 **35.4865 ms**, p99 **47.7677 ms**, including
219 daily bars/36 quotes/nine trades, validation/hashes/report writes. Warmed screen
p99 **0.0074 ms** over 1,000 observations. Network, training/label trials and Pi excluded.

LT3c lot/SIP/rebalance/aggregate capital mechanics are next. Actual source/model
acceptance, historical fee matching, custody/settlement and device/browser pixel
acceptance remain pending. No live route or connected long-term automation was added.

Final checks: Ruff lint/format and mypy pass; frozen offline lock/sync and installed
dependency consistency pass; source distribution and wheel build, with all three UI
asset groups loaded/rendered from the wheel outside the repository. Secret-pattern
and 22 Markdown-file local-link checks pass. Online `pip-audit --skip-editable`
reports no known vulnerabilities. No dependency was added. Read-only preflight
preserves the original intraday account at ₹25,000, zero fees, zero journal events,
no positions/orders and the unchanged legacy risk hash. Missing operator/session/
broker/device prerequisites remain disclosed; local trading readiness is not claimed.
The generated offline portfolio HTML was opened. Browser pixel/phone verification
remains pending the previously unavailable computer-use permissions.

## 2026-10-21 — LT3a daily research and explanatory dashboard (0.7.0)

Continued after LT2 into the next dependency of the long-term roadmap. Added
`daily-research-demo` and `daily-analyze`, strict bounded raw daily bundles with
explicit price/basis availability, share factors/distributions in previous-share
units and point-in-time universe inclusion/exclusion/re-entry. Missing, late or
excluded data cannot be forward-filled into a candidate; gaps/re-entry reset windows.
Explicit historical as-of clocks prevent future valid prices/benefits changing
features/ranks. Membership must be knowable before its effective session opens.

Added streaming Decimal gross-return/trend/volatility/turnover screening with bounded
rolling state, binary-search membership and deterministic qualified-candidate ranks.
The gross index assumes same-close distribution reinvestment before costs, tax or
payment delays; it is not an execution backtest or the LT2 cash ledger. No account,
broker, trading endpoint, model approval or risk-policy change was added.

Added a self-contained responsive offline research dashboard with provenance/IST
analysis clock, candidate/data summary cards, searchable/filterable/sortable results,
plain-language reasons, metric definitions and useful empty/incomplete states.
Accessible labels, column scopes, keyboard scrolling/focus and touch-sized controls
support inspection. Untrusted values render as text; escaped embedded JSON and
hash-bound CSP need no network dependencies. Analytical display rounding is disclosed;
raw Decimal values remain in JSON. Private report files/source/Python hashes and a
last-written artifact manifest support reproducible review and mutation detection.

Added an invented six-symbol ninety-session fixture retaining an unfavorable trend,
illiquidity, missing data, re-entry and historical exclusion beside one candidate.
Added detailed daily usage and updated main/long-term usage, roadmap/specification,
API, architecture, research/model, console, risk, operations, threat, acceptance,
performance and test documentation. LT3b quote-executed daily strategy/ML and LT3c
portfolio/lot/SIP/rebalance/allocation remain pending; no original live phase advanced.

Validation:

- **420 Python tests and 23 JavaScript tests passed**, **92% Python coverage**.
  Daily analysis **97%**, strict input **93%**, renderer/demo **100%**. New cases
  exercise future-prefix invariance, late basis/price, corporate benefit math,
  membership/gaps, malformed/ambiguous input, source mutation, artifacts and CLI
  isolation; UI cases verify text safety, filtering/sorting/reset/focus and empty states.
- Thirty-run 538-bar/six-symbol Mac benchmark: p50 **8.0033 ms**, p95 **15.2105 ms**,
  maximum/p99 **20.4069 ms**, including loading/validation/analysis/input/Python hashes.
  Fixture creation, HTML writing, network/history, execution and actual Pi are excluded.
- Ruff lint/format, mypy, secret-pattern/Markdown-link checks, frozen offline lock,
  unchanged-dependency audit, wheel/source builds and extracted report assets passed.
- The offline dashboard is generated for review. Pixel-level browser/handset checks
  remain blocked by pending computer-use permissions; no visual acceptance is claimed.

## 2026-10-21 — LT2 reviewed paper corporate actions (0.6.0)

Added exclusive offline `apply-corporate-actions`, `record-corporate-cash` and
isolated `corporate-actions-demo` commands. Strict bounded UTF-8 input rejects
ambiguous/duplicate fields, extra fields, nonfinite/subpaisa money, invalid ratios,
naive/future dates and unsupported context. Batches bind the current quarantine
hash, explicit complete coverage, stable issuer/batch IDs and sourced ex-date sessions.
Accepted ex-date quotes/fills and retroactive/same-date follow-up batches are refused.

Added increasing split/bonus quantities with original holding identity, total cost
conservation, tick-rounded protective levels and affected-order cancellation while
retaining durable exits. Exact rational fractional claims retain allocated basis
rounded down to paise, with the holding retaining the exact residual. Unknown
fraction values pause new entries/portfolio marks without erasing claims on sale.
Fraction chains and unsupported issuer events remain blocked rather than guessed.

Added frozen gross/deduction/net dividend receivables, nonspendable until an exact
reviewed net receipt, plus separate cash-in-lieu settlement and received investment
income. Atomic additive financial tables and journal/materialized changes preserve
original orders/fills. Independent ordered reconstruction verifies quantities, cash,
cost, adjusted protections, claims, receipts, basis boundaries and primary-key
receivable caches. Canonical retries write nothing; an already paid claim cannot
be credited with another payment ID. Backups preserve all evidence.

Updated report schema to 2 with full batches/claims/quarantine hashes, separate
income/fraction P&L and adjusted whole-share capital metrics. Console claim cards
explain spendability, incomplete valuations and the next required action; quarantine
confirmation points to the offline workflow. Values/guidance clear on Lock.
Added the detailed corporate-action usage guide and updated main/long-term usage,
plan/specification, architecture, API, risk, runbook, threat, acceptance, research,
performance and testing Markdown. `AGENTS.md` records the user's standing
usage/component-documentation, financial-test and clear accessible UI requirements.

Validation:

- **387 Python tests and 19 JavaScript tests passed**, **92% Python coverage**.
  New action contracts **95%**, accounting reconstruction **90%**, offline service
  **92%**, direct lifecycle drill **100%**; legacy suites remain passing.
- Invented split/dividend/bonus/fraction/exit/receipt drill: final cash **₹25,029.42**,
  realized capital P&L **−₹20.98**, received dividend income **₹50.40**, no holdings or
  claims left. These are software fixtures, not market-return evidence.
- 2,000-quote Mac benchmark with fourteen held shares/₹14 unpaid dividend:
  p50 **0.2003 ms**, p95 **0.2297 ms**, p99 **0.2564 ms**. SQLite WAL/FULL unchanged;
  parsing/network/contention/history/action replay/Pi are excluded.
- Ruff lint/format, mypy, secret-pattern/Markdown-link checks, frozen offline lock,
  dependency audit (no known vulnerabilities), wheel/source builds and extracted
  package imports/assets passed. No dependency was added.
- Original account read-only preflight still reconciles **₹25,000.00**, zero fees,
  no positions/pending orders and matching legacy policy/horizon. No recovery ran.
- Isolated responsive LT2 preview runs locally with invented unpaid/fraction claims.
  Browser visual inspection was blocked by pending Accessibility/Screen Recording
  permission; JavaScript workflow checks passed. Actual handset acceptance remains open.

Real custody/settlement, bank verification, statutory tax lots, complex actions,
corrections/reversals/deposits and validated daily strategies remain excluded.
Version 0.6.0 does not deliver the original live-adapter phase. The next engineering
item is LT3 daily research/portfolio management, with all external/live gates retained.

## 2026-10-20 — LT1 long-term paper foundations (0.5.0)

Expanded the user-requested plan to include long-term NSE cash-equity paper holdings.
Added a separately bound `investment_horizon`, dedicated config/database/8001 listener,
portfolio drawdown limit and separate delivery charge schedule. Legacy intraday
policy hash `642c1e1c9fabdd41278868d4e66108e201e7c1b15ddb888ed5ad9704afd1cbaa`
and existing intraday defaults/model artifacts remain unchanged. Horizon/policy
changes fail before pending recovery; a selected feed cannot omit a held symbol.
Each account has independent virtual capital, not a shared cross-account budget.

Added composed overnight day-roll/watch behavior: regular closes/weekends/restarts
preserve long-term holdings, entry residuals still expire, prior trusted portfolio
observations anchor the new day's P&L before opening quotes, and observed peak/
drawdown persist across dates. Protective stop/target/operator/kill exits remain
latched per holding until closure, including cancelled/restarted partial residuals.
Waiting for a new date cannot reset a breached long-term drawdown limit.

Added typed, authenticated current-session price-basis review and individual-holding
exit routes with console controls/confirmation. Missing review blocks raw quote
replacement and fills. Reviews pin the used calendar and prior quote basis; reported
corporate actions persistently quarantine symbols and cancel pending buys. Another
review cannot clear quarantine. No split/dividend/cash/share adjustment is invented.
Existing intraday automatic rules/ML/research are refused on long-term configs.

Delivery estimates include both-side STT, delivery stamp, variable taxes/fees and
atomic DP once per sold symbol/IST day across partial fills and replacement orders.
An entry cash buffer protects ordinary exit-fee capacity. Actual fee shortfall blocks
the fill without charging an unfilled DP amount, creating negative cash or deleting
the holding. Startup independently reconstructs delivery fees/day allocation,
review authority, quarantine, fill journal and durable exit evidence.

Added source-preserving `long-term-report`, three independent invented lifecycle
scenarios, an isolated populated benchmark and CI commands. Added the detailed
long-term guide and updated all corresponding plan/specification, usage, API,
architecture/risk, threat/operations, acceptance, research/model, performance/test
Markdown. The extended roadmap names LT2 corporate-action accounting, LT3 daily
research/portfolio management and LT4 actual custody/settlement acceptance. This
package version is not the original future live infrastructure Phase 5.

### LT1 validation and measured limits

- **328 Python tests and 17 JavaScript tests passed**; **92% Python coverage**.
  Forty-four new Python cases include financial outcomes, fault rollback, corruption,
  horizon/coverage rejection, API/CLI/report flows and lifecycle drills. Long-term
  policy **96%**, delivery verification **93%**, charges **100%**, independent broker
  **93%**, long-term demo **90%**, report **92%**, API **91%**.
- Ruff lint/format, mypy, secret-pattern/Markdown-link checks, frozen offline lock,
  dependency audit (no known vulnerabilities) and wheel/source builds passed.
  Packaged long-term modules and console assets load outside the repository.
- Populated 2,000-observation Mac benchmark: p50 **0.1843 ms**, p95 **0.2147 ms**,
  p99 **0.3288 ms**, fourteen held shares, WAL/FULL unchanged. Parsing, network,
  callback contention, history and actual Pi behavior are excluded.
- Invented independent outcomes: overnight/restart cash **₹25,379.54**, opening-gap
  cash **₹24,261.40**, quarantine account cash **₹17,986.78** plus fourteen retained
  shares. These are software fixtures, not market-return or profitability evidence.
- Original-account read-only preflight reconciled **₹25,000.00**, zero fees, no
  pending orders/positions, matching legacy intraday policy/charges. Missing operator
  token in the unconfigured shell remains correctly blocked. No source recovery ran.
- Desktop Safari visually displayed the isolated long-term account, horizon, fee
  buffer and review form. No Kite session, real order or custody action occurred.
  Mobile/actual-device checks remain pending.

LT1 does not implement corporate-action adjustments, actual custody/sellable holdings/
settlement, daily long-term strategies/ML, SIP/rebalancing/tax lots or aggregate capital
allocation. Virtual same-day protective exits/immediate sale cash are simulation
simplifications. Real-feed/model/strategy/device acceptance and all live phases
remain pending under the documented gates.

## 2026-10-20 — Responsive console and local acceptance tooling (0.4.1)

Continued Phase 4 acceptance support with a responsive packaged HTML/CSS/JavaScript
operator console: account cards, readiness reasons, observed quotes, positions,
latest orders and raw details. Added authenticated `/api/console` for engine-serialized
state capture with a 200-order/ten-quote bound. Existing order/control/risk contracts
remain in force. CSS stacks panels and touch-sized controls for narrow viewports;
there is no native mobile app or public listener.

Added memory-only unlock/lock, clearing of private values, rejection of late/older
poll responses, visible-tab polling, overlapping-request suppression, six-second
stale display protection and request timeouts. Arm/reset ask for confirmation and
stale data blocks them; emergency kill/flatten/disarm remain direct requests. Actions
are serialized with no automatic retry. Timeout messages disclose unknown outcomes,
and queued exits are not represented as fills. Dynamic rendering uses text nodes,
fetches reject redirects/omit cookies, and same-origin static CSS permits a tighter CSP.

Added `preflight [--strict] [--output NEW_PATH]` before the owning CLI startup path:
read-only WAL-aware ledger/integrity and stored-identity checks plus runtime, SQLite
fix branches, calendar, permissions, token presence, disk and catalog diagnostics.
It does not create missing accounts, construct a broker, take ownership, recover or
cancel pending work, call Kite, validate an external model or arm anything. Queries
have cooperative budgets and retain normal locking; heavy integrity scans stay out
of UI/feed processing. Private JSON/Markdown reports have a final hash manifest.
Strict exit 2 identifies blocked required local checks; external/live acceptance
always remains false. Full controller identity is still verified at actual startup.

Added console/acceptance usage guides and updated corresponding plan/specification,
architecture/API, performance, threat model, runbook, tests and paper-feed documents.
Added Node 24 JavaScript checks to CI; no Python or browser runtime dependency was
added. Package/version/lock now identify 0.4.1.

### Validation

- **284 Python cases and 13 JavaScript cases passed**; Python coverage **92%** overall,
  preflight **97%**, console view **93%**, API **90%**, paper broker **93%**.
- Ruff lint/format, mypy, secret-pattern/Markdown-link checks, frozen offline lock/sync,
  dependency audit (no known vulnerabilities) and wheel/source builds passed. Packaged UI assets load outside the repository.
- Desktop Safari account/readiness and lock/unlock/kill/reset behavior checked in an
  isolated virtual preview. Its balance remains ₹25,000, flat, kill inactive.
- Original account read-only preflight reconciles ₹25,000.00 with no pending orders
  or positions; missing operator-token configuration is correctly reported blocked.
- Local Python **3.13.16**, SQLite **3.53.1**, macOS ARM64. Real broker, hardware,
  sustained-session, fill/model acceptance and mobile visual/handset checks remain
  pending. Browser tooling did not provide reliable mobile visual verification.

## 2026-10-20 — Phase 4 supervised paper-feed engineering (0.4.0)

Added explicitly enabled supervised paper automation, authenticated arm/disarm and
universe-wide readiness to the private console/API. Startup, restart, reconnect and
new sessions remain disarmed. Backfill warms features with entries disabled and
does not replay missed signals. Manual entry intents are disabled on dedicated
automated services; existing protective controls and independent risk remain active.

Added `paper-init` for exclusive creation and read-only catalog/profile checking,
binding the selected model/rule policy before any manual model identity is assigned.
Accounts pin runtime/rule/strategy/feed policy, universe, model and synthetic mode;
used calendar definitions are pinned by date. Removed/changed automation is rejected
before pending-entry recovery. Controller-free submissions fail at the broker.
Durable proposal counts survive history reload and restart, including rejected orders.

Added a separate history worker with monotonic request spacing, bounded retry cadence,
completed-session response checks and connection-generation invalidation. HTTP waits
release the quote/risk lock. The worker uses authoritative completed historical 5m
bars, avoiding unknown initial streamed volume/partial-bar mixing; slow or missing
history skips entries. Default 400 ms request spacing respects the documented
historical request budget. No network operation was added to the execution adapter.

Disconnect/staleness disarms and cancels pending buys before resumed data can fill
them. Stale holdings or disconnects queue durable kill exits; unavailable data never
fabricates liquidation. Reconnect/reset does not rearm. Models retain Phase 3 loader
gates and additionally require non-synthetic provenance, current availability and
the configured validation age, including cancellation before pending buys fill after
expiry. No synthetic override exists on the connected service.

Added bounded timing rings and cumulative counts/maxima/budget exceedances, periodic
journal telemetry and observed per-run equity/drawdown. Added source-preserving
`paper-report` with reconciliation, net trades, incidents, clean-run/sample/model/
latency gates and explicit measurement limits. Recent windows are not represented
as global quantiles; crash losses in telemetry and incomplete coverage are disclosed.
External acceptance and live readiness always remain false.

Added `paper-demo` with independent partial-fill, disconnect-with-holdings, silent-feed
and unclean-restart accounts/evidence. Added a populated durable pipeline benchmark,
CI commands and complete corresponding plan/specification/usage/architecture/API/
risk/security/runbook/performance/testing Markdown. Added the compatible schema-v1
event-kind/time index for fast durable proposal-cap lookups. Economic hashes, money
semantics and WAL/FULL durability are preserved; no dependency was added.

### Phase 4 validation

- **259 tests passed**, including all 215 previous regressions and 44 new unit,
  integration/concurrency and functional cases. Coverage: **92% overall**, paper
  runtime **91%**, service **90%**, reports/demo **93%**, metrics **100%** and
  independent paper broker **93%**.
- Ruff lint/format, mypy, secret-pattern and Markdown-link checks, frozen lock
  verification and wheel/source builds passed. Dependency audit found no known
  vulnerabilities; no advisory was ignored.
- Synthetic partial-fill cash reconciled to ₹25,023.24; disconnected/silent recovery
  accounts to ₹24,959.48; cancelled unclean-restart account stayed ₹25,000. Each starts
  independently at ₹25,000. These invented outcomes have no market interpretation.
- The 2,000-observation populated Mac benchmark measured p99 **0.4791 ms**, including
  nineteen partial buys, a nineteen-share holding, risk/accounting/performance and
  periodic durable telemetry. Network, parsing, callback contention, history I/O and
  Pi behavior are excluded. No durability setting was weakened.
- Original service-account integrity/accounting checks passed; it remains flat at
  **₹25,000.00**, with zero fees/reservations and no feed connection.

No real broker connection, order, deployment or funds transfer was attempted.
Supervised-source research exports preserve first observed candle availability and
recorded connection changes. Missing observation clocks or external unclocked candle
overrides are refused, preventing backfills from being treated as known at close.
Actual entitlement/feed duration, fill/cost calibration, market/model acceptance,
target-device latency and physical recovery drills remain pending. Future live
infrastructure still requires separate explicit approval.

## 2026-10-20 — Phase 3 chronological ML research (0.3.0)

Added a versioned twelve-feature causal schema with finite values, completed-time
and instrument checks, and a normalized fingerprint binding economic candidate
identity. Labels use independent standalone paper accounts with existing fee-aware
risk sizing, depth, partial fills, tick rounding and later-quote latency. Predeclared
time barriers queue exits before reading subsequent prices; intervals end at actual
last fills. Unfilled, unresolved, interrupted and bad/gapped paths are censored and
audited rather than converted into negative targets or forced closes.

Added hash-verified sample bundles preserving source manifests, full strategy and
economic settings, label policy, sessions, code identity, counts and execution audit.
Readers validate bounded local paths/records, uniqueness, universe/session context,
outcome-count consistency and immutable inputs. Completion manifests are written
last. Labeling uses temporary independent accounts plus a retained quote observer;
it never opens or changes the configured service account.

Added whole-session expanding walk-forward splits with timestamp-interval purging
and strict embargo, train-only scaling/logistic fitting, disjoint later regularized
sigmoid calibration, and a final holdout inspected after coefficients freeze. Fixed
settings replace parameter search. Diagnostics include ROC-AUC, Brier/log loss,
training-prevalence baseline, reliability/ECE, selected counts and net counterfactual
P&L. Insufficient fitting data fails; failed evaluation models retain diagnostics
and cannot load. Model availability follows the latest final validation label,
declared session close or source observation, plus embargo.

Added bounded JSON-only artifacts and a lightweight pure-Python loader/scorer.
The loader checks hashes, schema/order/dimensions, finite math, report identities,
split windows, reliability consistency, derived acceptance gates and contextual
strategy/policy/fee matching. No pickle or joblib is loaded. Synthetic override
relaxes provenance only, requires all metric gates, and only scores synthetic data.
Integrity hashes do not authenticate a maliciously rewritten local bundle.

Added same-availability-time probability ranking before independent risk admission.
The paper broker rechecks feature/candidate/model context, availability and threshold;
all previous sizing, cash, loss, position, freshness and kill gates remain in force.
Vector changes conflict under an existing intent. Model version/schema metadata
prevents silent gate removal on restart; missing metadata fails before cancelling
pending orders. The original economic-policy hash encoding is preserved. No database
schema migration, live route, network execution adapter or connected automation was added.

Added `ml-build`, `ml-train`, `ml-demo` and `backtest --model`, separate real/synthetic
training policies, optional locked training dependencies, CI steps and a scoring/ranking
benchmark. The Pi setup now installs only broker/runtime extras. Updated the supplied
specification, implementation plan and corresponding architecture, risk, security,
API, runbook, performance, test and usage Markdown; added the detailed ML usage guide.

### Phase 3 validation

- **215 tests passed**, including all 159 previous regressions and 56 added unit,
  integration and functional cases. Reported coverage: **93% overall**, features/schema
  **100%**, training/samples **99%**, inference **97%**, labeling **94%**,
  validation diagnostics **91%** and independent paper execution **93%**.
- Ruff lint/format, mypy, working-tree secret-pattern checks, local Markdown links,
  frozen lock verification and offline wheel/source builds for **0.3.0** passed.
- Current installed dependency audit: **no known vulnerabilities**, no ignored
  advisory. Optional NumPy 2.5.4 / scikit-learn 1.9.1 dependencies are hashed in the
  lock. A fresh-process test confirms loading imports no heavy training/persistence stack.
- The synthetic functional workflow labels sixty candidates (30 per class), passes
  invented walk-forward/holdout diagnostics, and correctly fails `non_synthetic`.
  Ten subsequent sessions remain outside training and validation. Their rule/scored
  portfolio results are reproducible and documented as invented software fixtures.
- The original service account passed integrity/accounting checks and remains flat
  at **₹25,000.00**, with zero fees, zero reservations and no feed connection.
- The 10,000-observation Mac benchmark measured score p99 **0.0012 ms** and ten-candidate
  score/rank p99 **0.0144 ms**. These exclude feature creation, parsing, artifact I/O,
  risk/commit, training and network. Durable quote-path recheck measured p99 **0.156 ms**
  in the existing empty-portfolio fixture; no durability setting was weakened.

No model has been empirically accepted on real market data. Quote density, exclusions,
historical fees, corporate actions, selection bias, actual broker access, Pi operations
and connected paper-feed validation remain external acceptance work. Synthetic passes
and small local latency measurements do not establish profitability or live readiness.

## 2026-10-20 — Phase 2 strategy research (0.2.0)

Added immutable, versioned ORB and VWAP-continuation rule settings and independent
per-symbol/session state. Signals use completed contiguous 5m candles, session VWAP,
rising EMA, Wilder ATR, prior-only relative volume, turnover/price/spread/freshness
filters, ATR stops/targets and a per-session candidate cap. Candidates still pass
the existing cost-aware risk engine; connected-feed strategy automation is deferred.

Added streaming typed raw-price dataset bundles with reviewed sessions, provenance,
availability/chronology checks, restricted paths, bounded reads, synthetic labels,
input hashes and post-run mutation checks. Added a source-preserving exporter that
retains calendar references, accepts verified candle overrides and never runs source
order recovery. Failed exports leave no loadable manifest.

Added isolated quote-driven backtesting and `backtest`, `research-demo`,
`export-research` commands. No OHLC tick path or signal-close fill is invented.
Even zero latency requires a strictly later exchange quote. Research accounts retain
unfinished positions/orders and report gaps/stale valuations as incomplete. Outputs
include decision explanations, equity CSV, completed net-trade statistics, observed
drawdown, fill/accounting journals, reproducibility hashes and runtime versions.

The synthetic two-session fixture contains a winner and loser: final cash ₹24,974.03,
estimated fees ₹20.27 and net P&L −₹25.97 under defaults. It does not establish
profitability. Historical fee matching, queue/impact effects, sparse observations
and incomplete connection history remain disclosed research limitations.

Added leakage, metric, provenance, failed-input/export and source-order isolation
tests, CLI functional checks, a constant-work strategy benchmark, CI coverage of that
benchmark and detailed corresponding architecture/API/risk/security/runbook/usage
documentation. Updated the specification/implementation plan and package to 0.2.0.
No runtime dependency or schema migration was introduced.

### Phase 2 validation

- **159 tests passed**, including the entire Phase 1 regression suite and 51 added
  strategy/data/export/metrics/CLI/causality cases. Reported coverage is **91% overall**,
  **95% rule strategies**, **94% dataset validation**, **95% export**, and **99% metrics/reporting**.
- Ruff lint/format, mypy, working-tree secret-pattern check and local Markdown links
  passed. Wheel and source distribution builds for **0.2.0** succeeded offline.
- Final installed dependency audit found **no known vulnerabilities**; no advisories
  were suppressed and runtime dependencies did not change.
- The functional research demo completed both net-positive and net-negative trades.
  The service paper account remained flat at **₹25,000.00** and passed integrity and
  accounting verification.

The 2,000-evaluation benchmark measured p99 ORB **0.0177 ms**, VWAP **0.0168 ms** on
this Mac. It excludes input construction/decoding, disk, network and execution.
Real-market performance, actual Kite access, Pi deployment and ML remain unverified.

## 2026-10-20 — Initial paper platform

Initialized Git on `main` and implemented the Phase 1 paper-only plan from the supplied
specification. Added Python 3.13.16 environment metadata, exact hashed dependency lock,
package entry point, safe config/secret examples, local private runtime, setup scripts
and Git exclusions for credentials, environments, logs and trading artifacts.

Added validated domain types, Decimal money, UTC/IST separation, reviewed session
calendar, read-only HTTP authentication/profile/catalog/history, strict full-mode
equity WebSocket decoder and bounded reconnection. Removed the initially evaluated
official SDK after its pinned transport failed the vulnerability scan; implemented
the limited official protocol with audited transports and documented the deviation.

Added SQLite schema v1, WAL/FULL durability, exclusive ownership, atomic journal,
idempotent intent fingerprints, accounting reconstruction, paper cash/positions,
cost-aware risk sizing/reservations, latency/depth/partial fills, cumulative fees,
daily/streak/stop/target/session risk gates, persistent kill and conservative restart
recovery. Added credential-free health, entry readiness, authenticated operator API,
Origin/Host/security headers, local dashboard and redacted rotating diagnostics.

Added incremental candle/feature infrastructure, explicit unavailable ML stub,
deterministic replay/demo reports, backup verification, deployment templates, CI,
unit/integration/functional/replay/security checks, secret-pattern check and benchmark.
Updated the specification and corresponding architecture, risk, security, API, test,
performance, usage and operator documentation. Later strategy/ML/live phases remain
gated as described in the implementation plan.

### Local validation record

- **108 tests passed**, including unit, integration, functional CLI/API, replay,
  security, real process-death recovery and seeded partial-execution sequences.
- Coverage reported **90% overall**, **93% paper execution**, and **100% costs/sizing**.
- Ruff lint/format, mypy, project secret-pattern check, shell syntax and launchd plist
  validation passed. All local Markdown links resolve.
- Final dependency scan: **no known vulnerabilities**; the editable local project
  itself is not a PyPI advisory target. No advisories were suppressed.
- Frozen/offline environment sync, source distribution and wheel build succeeded;
  the build backend is pinned to Hatchling 1.32.4.
- The real default paper database was initialized at exactly **₹25,000.00** and
  passed integrity/accounting verification. It is ignored by Git and has no holdings.
- The committed 2,000-event Mac benchmark records p99 indicator update **0.0028 ms**
  and quote ingestion/journal/risk/durable commit **0.153 ms**. Typed model construction,
  network, populated-account execution and ML are outside these timer boundaries.

The final pass also normalized financial/time formatting in idempotency fingerprints,
added durable sequence numbers to same-time exit reissues, strengthened persisted
reservation/fee/policy validation, and checked generic error redaction for headers
and JSON-shaped messages. Corresponding regression tests and component docs were updated.

No actual Kite credentials, broker subscription purchase, live order, host-wide
service installation or Raspberry Pi hardware test was performed. Functional broker
tests use controlled transport responses. Configured remote CI has not executed here.
