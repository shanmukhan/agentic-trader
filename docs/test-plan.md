# Test and validation plan

## 31 October 2026 — watchlist and safety regression sources

Added, **not run** at explicit user request:

- Unit: empty/unknown permitted lists, durable recovery/corruption, exact quarter-
  equity cash debit including fees, independent SQLite cash/cost/fill checks,
  five accepted daily intents with idempotent retries/fifth fill, exact 25% pause
  boundary, explicit reset, daily integrity lockout across a rolled-back frame.
- Functional: authenticated/literal catalog reads preserve financial tables,
  Origin/acknowledgement/revision gates, unknown/duplicate symbols, manual API
  bypass rejection, reservation cancellation with no fill, contribution restrictions,
  exit-only holdings and strategy proposal suppression.
- Browser: acknowledged frozen payload, visible consequences, missing feed selection,
  private locking/late-read suppression, uncertain save recovery without retry,
  labels and workspace navigation.
- Native: Watchlist destination/guidance, offline fixtures, confirmed list payload,
  cancellation and unsaved navigation; existing cross-destination checks include it.

Static checks do not establish test success, real-market/broker acceptance, signed
APK publication or biometric/device acceptance. See [watchlist-safety.md](watchlist-safety.md).

## 0.20.9 timeout and browser daily regression checks

Functional tests prove source-only auth, current Nifty 50 identity/flags, altered-file
rejection, no ledger audit/broker reads, exact persisted SQLite equality and bounded
basket resolution independent of catalog size. Existing full operations accounting tests
remain. Native UI simulates a blocked automatic audit without global busy/progress or
missing account values; cancellation permits a later check, and a failed source read
recovers without downloading/trading or marking a fresh account stale. A blocked Discover
refresh keeps cached research visible without the top progress bar or global busy state.

Browser tests cover audited-data reuse, no ledger calls, one Nifty 50 download and one
completion review, first explicit policy/ML reuse, locked late replies, failed-read recovery,
one connection confirmation/failure without retries, proposed-close invalidation and quiet
polling with enabled controls. Browser visual QA uses local invented snapshots at desktop
and narrow widths; it cannot establish broker/market acceptance. Production deployment
must independently compare both databases/configuration and measure public/local source,
account and full-report timings after restart. Private token values must never be logged.

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

## Android 1.0.8 daily journey checks

Native unit coverage derives four-step progress from positive evidence, rejects missing/
changed audit flags and job identities, invalidates at server IST day/reviewed or proposed close/source
changes, keeps partial guided installation incomplete and never chooses an unconfigured
policy. Offline Compose workflows cover cached-data skip, one guided preview, cancellation
without reopening, download → review → connection transitions on Home, acknowledgment
before confirmation, no mode/purchase side effect, exact invented account preservation,
required first policy choice and retained advanced controls. Repeated read-only audits are
bounded; crossing a reviewed close triggers another check. Existing quiet-refresh, unknown
write recovery, mode readiness and every-native-destination regressions remain applicable.

Run from the repository root:

```sh
JAVA_HOME=/Library/Java/JavaVirtualMachines/jdk-21.jdk/Contents/Home \
GRADLE_USER_HOME=/private/tmp/agentic-android-gradle \
/opt/gradle/gradle-9.7.0/bin/gradle -p android --no-daemon \
  testDemoDebugUnitTest assembleDemoDebug assembleDemoDebugAndroidTest lintProductionRelease
adb -s ZD2225M4V2 install -r android/app/build/outputs/apk/demo/debug/app-demo-debug.apk
adb -s ZD2225M4V2 install -r android/app/build/outputs/apk/androidTest/demo/debug/app-demo-debug-androidTest.apk
adb -s ZD2225M4V2 shell am instrument -w -r \
  com.shanmukhan.agentictrader.demo.test/androidx.test.runner.AndroidJUnitRunner
```

The separate offline package has no Internet permission. Remove demo/test packages after
QA. Production install is in-place with the existing signing certificate; preserved pairing
and real authenticated acceptance must be recorded separately. A release version change
also runs backend/browser/deployment tests. Production deployment independently compares
persisted SQLite/configuration and verifies version/hash/installer identity.

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

## 29 October 2026 — automatic Nifty 50 / live signal pipeline (0.20.7)

New synthetic source/API workflows verify a full 50-member guided basket, explicit
history exclusions, legacy capacity migration without manual names, authenticated/
acknowledged scope changes and unchanged exact financial state/policy. A 50-stock
signal cycle evaluates every stock without another REST batch, accepts only purchases
within unchanged position limits and independently verifies persisted fills/fees/cash.
Source-labeled quotes in this test are invented Kite-shaped protocol fixtures, not
real broker acceptance. One-symbol tests verify delayed warm-up, no historical replay,
new live-bar submission/later fill, stale-candle rejection, Manual/late-result safety,
gap resynchronization and bounded retries on incomplete history with no ledger writes.

Native checks cover whole-basket coverage, hidden manual-name fields and one confirmed
official-basket request without a symbols payload. Nifty 50 naming/reuse is independent
of Nifty 100/500. Live official CSV verification found 50 members, SHA-256
`f5ba4027d935ae72879d5c24bbebf0e8439ec8ed504ffdf4175fde69206244b3`, 15:52 IST.
The 6.442-second real read-only timing diagnostic is distinct from simulated signal/
fill tests. Production next-cycle signal/fill acceptance is not established by fixtures.
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

The basket POST succeeded on the first attempt. A verification helper then used GET
for the POST-only profile check and received 405; saved membership/configuration was
inspected before continuing with the correct POST. Selection was not repeated. This
was an administrative helper correction, not an application route change or order.

## 29 October 2026 — proactive Trade readiness, 1.0.6 / 0.20.6

New pure server cases cover pre-open/between-open-and-entry, exact entry/cutoff,
special/empty session intersections, missing future reviews, open-session quote waits,
action mappings and unknown blockers. A synthetic HTTP flow moves the server clock
through waiting and readiness, rejects blocked mode POSTs and independently reopens
SQLite to compare full contents, exact cash and zero orders/fills; GET never arms a mode.
Native unit cases cover missing/contradictory readiness, old-server fallback and action
routing. Offline UI cases cover a tappable blocked Approval explanation, time/next-step
content, quiet readiness transition without activation, setup navigation, failed fresh
reads and changed-readiness rejection without retry. Existing mode acknowledgement,
duplicate-tap, cancellation and exact invented balances remain covered.

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
The first full Python run encountered the existing 1 GiB workstation disk-headroom
check after retaining synthetic fixtures. Removed only completed task fixtures and
reran with `-o tmp_path_retention_policy=failed`: all nineteen preflight tests and the
full 1,421 pass; no safety threshold, test or financial check was skipped/relaxed.

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

## 29 October 2026 — Android 1.0.5 / backend 0.20.5 checks

Added synthetic authenticated environment tests: owner/phone GET, unauthorized denial,
Real disabled, switching POST rejected for both authorities, Settings rejects real,
independent full SQLite comparison and exact ₹25,000.00 saved cash unchanged.

New offline Compose cases exercise delayed quiet reads without busy/progress/button
movement, complete snapshot publication, review cancellation of quiet work, explicit
Paper/disabled Real without a write, branded lock/loading pages, initial delayed account
read and rejected unexpected real account response. These use invented balances and
a separate no-Internet demo package; they do not establish real broker or biometric
acceptance. Release build/signature, native unit/lint, full Python and deployment
verification results follow.

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

## 28 October 2026 — Android 1.0.4 history reuse

- Full Python suite: **1,411 passed**, 49.70 seconds. New read-only audit regression
  compares lightweight null validation with explicit audited validity five minutes
  after a synthetic download, twice. Independent SQLite reopen verifies exact cash
  ₹25,000.00 and full logical contents; source files and provider-call counts unchanged.
- Native unit tests: **11 passed**. Reuse requires audited boolean freshness flags,
  a ready/installed job, exact requested universe and unchanged job identity. Missing,
  stale, changed, incomplete, wrong-universe and changed/running job cases reject reuse.
- Offline Compose workflows: **11 passed**, 33.927 seconds on Moto g52 in the separate
  no-Internet demo/test packages, removed after completion. Repeated five-minute-old
  reuse sends no download POST and displays the reuse notice. First acquisition,
  invalid hashes, another universe and explicit force still download once in fixtures.
  These simulated actions do not contact Kite or modify the production phone account.
- Release lint: zero errors / 36 advisories. Ruff/format/mypy/secret/whitespace pass.
  Actual read-only source audit confirms the saved Nifty 100 job remains valid.
  Compiled production `PreparationReuse` accepted filtered live audit/job metadata
  and rejected null/unaudited metadata, with no download or account command. Saved
  job `a1b0a119d53032599137ff00212cf76c` and snapshot remain unchanged.
- Signed Android 1.0.4 / code 5 installed in place on Moto g52; pairing retained.
  Backend `v0.20.4-20261028T171417-775c61599b3d`, PID 29643: local/public health,
  source/installed and published APK hashes verified. Both logical account DB/config
  hashes and Advisor/Monitor PIDs 1193/1194 unchanged. Private evidence:
  `/var/backups/trading-services-v0.20.4-20261028T171417-775c61599b3d/acceptance.json`.
  Real production-button/provider acceptance is distinct from the simulated fixtures.

## 28 October 2026 — Android 1.0.3 supplied launcher artwork

Compared the supplied wordless and text-bearing app artwork; selected the wordless
blue/teal symbol for small-size recognition. Preserved source PNG; generated five
legacy and five adaptive foreground densities with macOS `sips`. Independently
decoded PNG headers to verify all ten expected dimensions, visually inspected the
192 px resource, and built adaptive/round manifest resources with protected foreground
padding. Notification icon remains a separate transparent white glyph.

Seven Android unit tests and 42 focused mobile/public-path/deployment tests pass.
Release lint: zero errors / 36 advisories, including legacy shape/optional monochrome
icons; Ruff/format/mypy/secret/whitespace checks pass. Signed APK v3/manifest verified.
Actual Moto g52 confirms version 1.0.3 / code 4, successful cold launch (331 ms),
preserved pairing and authenticated controls with no network/auth error. No balance
or credential was printed; no financial instruction or new enrollment was submitted.

Pi `v0.20.3-20261028T164611-8df9aa2528da`, PID 28798: public/local health,
installed/source and downloaded APK hashes match. Independent full logical account
DB/configuration hashes unchanged; Advisor/Monitor retained PIDs 1193/1194. Evidence:
`/var/backups/trading-services-v0.20.3-20261028T164611-8df9aa2528da/acceptance.json`.
Themed monochrome launcher artwork was not added; the supplied full-color icon is used.

## 28 October 2026 — Android 1.0.2 background cancellation

Moto logs show Conscrypt socket close sending TLS records on the UI thread during
locking, causing `NetworkOnMainThreadException`. Cleanup is now asynchronous; the
client is swapped before cleanup, preserving immediate privacy and later unlocks.
Seven native unit tests pass, including a cleanup failure followed by a completed
background task and the socket-level idle/single-instruction regression.
`ProductionNetworkTest` requires instrumentation argument `allow_public_network=true`;
it uses only public release GETs, a 6.5-second idle interval, cancellation on Android's
main thread, completed background cleanup and a fresh-client GET. The normal demo
tests remain offline. The opt-in test passed on actual Moto g52 / Android 13 in a
temporary package built from the exact `Api.kt` and `ProductionNetworkTest.kt` sources
(7.066 seconds). It verified public reads after idle, UI-thread cancellation without
the prior crash, completed cleanup and a fresh-client read. The temporary package
was removed. Signed production 1.0.2 / code 3 updated in place; pairing was retained.
Actual 1.0.2 biometric login loaded account values with no network/auth error; later
idle locking hid private values. No private balance was printed.

Full checks: 1,410 Python passed (61.33 seconds), 244 Node UI, seven Android unit;
release lint zero errors / 28 advisories; Ruff/format/mypy/secrets/whitespace pass.
Pi `v0.20.2-20261028T163249-8e5e7ba037e2`, PID 28144: health, installed/source
hashes and public APK bytes matched; both logical account databases/config hashes
and Advisor/Monitor PIDs 1193/1194 unchanged. Private evidence:
`/var/backups/trading-services-v0.20.2-20261028T163249-8e5e7ba037e2/acceptance.json`.

## 28 October 2026 — Android 1.0.1 idle connection regression

A temporary, separate Moto g52 diagnostic using the same OkHttp 5.5.1 settings
passed immediate public HTTPS requests, then failed with `unexpected end of stream`
after 6.5 seconds idle. Requests used only public release/health and invalid empty
session JSON (422); no owner/device credential or financial data was provided.
The app now evicts idle pooled connections after one second and retains paired UI
state as soon as biometric encryption is saved. Financial retries remain disabled.
Six Android unit tests pass; the new local socket fixture keeps the old socket open
and independently verifies a new connection and exactly one invented POST instruction.
Python suite: 1,410 passed (55.59 seconds). Release lint: zero errors. Actual fixed
Moto/update and RPi publication results will be recorded after completing those checks.

## 28 October 2026 — actual Moto installation

User-authorized ADB installation targeted only the connected Moto g52 running
Android 13 / API 33. The production APK's SHA-256 and v3 signing certificate matched
the published 1.0.0 artifact. Installation succeeded; independent Package Manager
inspection confirmed `versionName=1.0.0`, `versionCode=1`, installed/non-debug flags.
Cold launch completed successfully (1,159 ms), and the process remained running.
No credential was supplied. Hardware biometric pairing/unlock, broker login and
update acceptance remain pending; this is separate from the emulator test evidence.

## 28 October 2026 — backend 0.20.0 / Android 1.0.0 evidence

- `.venv/bin/pytest -q`: **1,410 passed**, 49.52 seconds. New native-access flows
  cover private pairing/scoping/revocation, expiry/restart/token rotation, bounded
  sanitized authentication, rate limits, nonce/phone-bound callback/fallback,
  missing prerequisites without account faults, storage-failure fail-closed behavior
  and public installer tamper/prefix handling. An invented purchase verifies exact
  persisted cash/fees/quantity and replay; other security tests compare full DB dumps.
- `node --test tests/ui/*.test.cjs`: **244 passed**. Callback query removal is tested
  without retaining/broadcasting secrets, alongside existing browser workflows.
- Android `testProductionDebugUnitTest`: **5 passed**, exact INR/decimal policy/null
  behavior, fixed-origin paths and request classification. **7 offline Compose tests**
  pass on isolated API 33 ARM64: all 16 destinations, exact invented balance, one-action
  preparation, mandatory acknowledgement/single submission, uncertain outcome recovery,
  cancelled-write/recreation marker, unsaved policy navigation and Android IST parsing.
- **2 production negative-security instrumentation tests passed**: locked initial UI,
  secure-window flag and refusal without enrolled strong biometrics. No credential
  supplied. These are negative tests, not positive hardware-biometric acceptance.
- Release lint: **0 errors / 28 dependency-version and style advisories**. Ruff lint/
  format, mypy, secret scan and whitespace checks pass. Gradle wrapper/distribution
  and dependency checksums retained. Synthetic light-mode screenshots inspected for
  Home, strategy, research, portfolio, policy and broker screens.
- Actual signed/minified production APK v3 signature/certificate and security manifest
  verified; 3.3 MiB artifact installs and cold-launches on the isolated emulator.
  Demo package is distinct and has **no Internet permission**. Signed production
  APK contains no offline demo asset. No real broker/device acceptance follows from this.
- Pi `v0.20.0-20261028T152359-e41c1fc957f7`: local/public health, installed/source
  hashes and public APK SHA-256 match. Independent full logical DB/config comparisons
  match the private preflight baseline; Advisor/Monitor unchanged. Private evidence:
  `/var/backups/trading-services-v0.20.0-20261028T152359-e41c1fc957f7/acceptance.json`.

Actual phone pairing/biometric lifecycle/update and actual broker/history acceptance
remain external. Existing Pi runner-isolation limits and absence of background push
are documented in [Android usage](android-app.md), not treated as completed milestones.

## 25 October 2026 audit validation

Final integrated commands:

```sh
.venv/bin/pytest -q --cov=trading_agent --cov-report=json:/private/tmp/audit-2026-10-25-coverage.json --cov-report=term:skip-covered
node --test tests/ui/*.test.cjs
.venv/bin/ruff check src tests
.venv/bin/ruff format --check src tests
.venv/bin/mypy src/trading_agent
.venv/bin/python scripts/check_secrets.py
git diff --check
```

**1,335 Python / 232 Node tests passed**. Statement coverage is **92.06%**
(11,151 / 12,113). Ruff and formatting cover 222 Python files; mypy passes on
125 source files. The full Python run emitted 52 SQLite ResourceWarnings in existing
paths; this is not evidence of fault-free resource lifecycle.

New evidence includes independent exact fee/cash/gap-exit persistence; 800 generated
intraday/delivery sizing cases against exhaustive Decimal oracles; safe request
rejections without engine fault; no-ledger feed health and rollback/reconnect/clock
observations; bounded retry/authentication exclusions; full supervisor iterations
through real ASGI handlers with independent SQLite reads; cross-horizon exact buffer
serialization/no double deduction; ML loaded inference [0,1] and coefficient/artifact
agreement. UI checks cover chart coordinates/gaps/warmup and keyboard/pointer controls,
compatible comparisons, exact scientific decimal signs/sorting, numeric ranks, invalid
or stale chart evidence, loading, feedback identity/privacy, confirmation revocation,
shortcut no-approval, static HTML labels and responsive/theme rule ordering.

A real disposable loopback app used invented 240-bar daily sources, three held stocks
and genuine offline synthetic replay reports. Desktop Firefox verified the Dashboard
and Portfolio accessibility tree and desktop layout. Independent mode=ro full SQLite
dump comparison retained cash **₹20,495.23**, three orders, three fills, three positions,
27 events and no pending orders. No read created orders, fills or account events.
The fixture server was stopped. Complete rendered dark/narrow/chart interactions were
not accepted in this pass (the shared native browser was in active use); automated
checks do not substitute for physical-device, broker, licensed-source, native worker or
sustained feed-scale acceptance. No user account or broker action was performed.

See [each audit disposition](audit-2026-10-25-resolution.md) and [open gates](ROADMAP.md).

## Issue-report remediation (24 October 2026)

Integrated commands executed after the final code changes:

```sh
.venv/bin/pytest --cov=trading_agent --cov-report=json:/private/tmp/agentic-issues-coverage.json --cov-report=term:skip-covered -q
node --test tests/ui/*.test.cjs
.venv/bin/ruff check src tests
.venv/bin/ruff format --check src tests
.venv/bin/mypy src/trading_agent
.venv/bin/uv lock --check --offline --cache-dir /private/tmp/agentic-trader-uv-cache
git diff --check
```

**1,292 Python / 202 JavaScript tests passed.** Python completed in 54.95 seconds;
statement coverage was **91.98%** (11,106/12,075). Ruff lint/format and mypy on
125 source files passed, as did offline lock validation. The Python suite emitted
63 SQLite connection ResourceWarnings in existing test paths. Newly added independent
accounting readers use explicit connection closure; broader fixture cleanup remains
separate from this validation result.

New `test_quote_batches`, `test_database_snapshots`, `test_delivery_quote_batches` and
`test_quote_frame_persistence` suites compare durable sequential/frame state, count
actual commits, independently reconstruct exact virtual cash/fees/DP charges, exercise
partial fills/protective exits and rollback including trusted long-term equity clocks.
They also cover same-second depth, processing delays/backwards clocks, mapping/SQL
failure, completed candle preservation, read-only SQL rejection and consistent committed
WAL reads during an active writer. Updated corporate-action query instrumentation
traces the real independent snapshot connection and retains its no-history-scan check.

Capacity/settings/broker tests cover configured/default bounds, strict malformed and
large frames, subscription batches and financial-policy identity stability. A fake-socket
50-symbol lifecycle independently verifies 1,500 saved candles. Setup functional tests
save 3,000 maximum-length catalog symbols beyond the old request budget, preserving
financial/event state; oversized/over-count/secret-bearing requests fail without echo,
configuration replacement or authority change. TOML and lock suites cover structured
comments/values, invalid/external policy edits, replacement failures, process contention
and a simulated Windows adapter.

Proposal tests verify authenticated bounded pending-priority metadata without expiry,
orders, fills or cash changes; query-plan checks rule out sorting the full history.
DOM checks cover route/hidden-tab monitoring, deduped opt-in notifications, stale/auth/
lock/late-response cleanup, modal guards, expired guidance, dynamic feed capacity and
accessible countdowns that do not continuously announce through a live region.

Rendered Firefox validation used a separately created invented account on localhost
port 8766, with no market-data connection or background watchdog. Desktop and 320×480
responsive checks showed proposal count/banner/deadline, route persistence and readable
controls; Lock removed details and restored the base title. Independent SQLite checks
before shutdown confirmed exact ₹25,000 cash, no orders/fills/positions and the same
awaiting proposal. The disposable server/tab were stopped/closed. Countdown live-region
and dynamic-capacity follow-ups have automated DOM coverage; native desktop notification
permission/delivery was not exercised.

These checks establish local simulated engineering evidence. They do not establish
3,000-symbol real-feed throughput, native Windows deployment, physical-device or OS
notification delivery, power-failure durability, licensed source acceptance or new
multi-year strategy profitability. The remaining capabilities are tracked in the
[current-code issue matrix](../PROJECT_ISSUES_GAPS_AND_IMPROVEMENTS.md).

## Daily operations automation (23 October 2026)

**Integrated validation: 1,248 Python and 193 JavaScript tests passed.** Ruff lint,
source/test format checks and mypy passed; `sh -n scripts/start_operations.sh` and
`plutil -lint deployment/launchd/com.example.trading-operations.plist` passed.
The new 32 unit/functional cases in `tests/test_operations_unit.py` and
`tests/functional/test_operations.py` use invented local accounts/provider responses.

Covered authenticated/origin-protected operations, strict acknowledgement and forbidden
authority inputs; read-only account/decision rows; distinct broker/source/session clocks;
source/draft tampering, duplicate/missing/future candles and symlink rejection; same-day
repeated downloads and interrupted/unknown claims without replay; pending-order refusal
without cancellation; unavailable/stale service, feed/quote/basis/fault/ledger/exit alerts,
closed-market versus intraday residual exposure, recovery transition and deduplication.
Before-open reports are separately identified so they cannot suppress after-close evidence.

Backup checks independently reconstruct exact fill debit/fees with Decimal, compare
original/restored SQLite rows for accepted/partial/full/cancelled/rejected orders,
preserve pending reservations/holdings, check installed source/data inclusion and all
manifest hashes/permissions, refuse running ownership/existing destinations, and reject
corruption/disk-write failure without a success marker. Isolated restore verifies copied
ledger/accounting without financial recovery, path rebinding or service startup.

The complete suite also retains existing guided confirmation/expiry/restart, model,
order, corporate-action and risk checks. These are engineering/simulated evidence;
no user broker login/download/attestation/mode/order action was performed. Actual
launchd/systemd operation, host crash/power failure, handset notification visibility,
real feed/entitlement, remote delivery and complete relocated service restoration are
unverified. See [the implementation review and usage limits](operations-automation.md).

## Workspace usability validation scope (0.19.0, 23 October 2026)

Check that the local SVG sprite is served with the expected static content type, and
that every navigation destination retains visible text and active-page semantics.
Decorative icons must be hidden from assistive technology and must not add duplicate
accessible names. Refresh/access/section icons must retain their existing labels and
handlers. Verify the mobile menu, visible focus, 44-pixel primary touch targets, exact
numeric strings and scrollable labelled evidence regions without external icon/CDN calls.

Setup disclosure must start collapsed after unlock, keep its current next step
visible and preserve its reason when expanded. Routine feedback can shorten; actual
observation timestamps, stale/error states, unavailable metrics and recovery must stay
explicit. Portfolio state must remain visible when definitions are closed; Analysis
must retain source/legend/help access without changing its history requests or seeds.

Policy checks cover four-step progress and Previous group/Next group, blank/null defaults,
conditional unit help, linked validation/focus, reviewing incomplete drafts, and no
POST/save on step navigation. Existing Cancel/Escape, acknowledged save, copy/edit,
uncertain-save reconciliation, unsaved navigation/unload guards and lock/pagehide/late
response clearing remain required. Account and broker logic is outside this change.

Record actual automated counts and any disposable Firefox check separately from these
acceptance criteria. A DOM harness is not browser layout evidence. Rendered checks must
exercise a disposable account and separately record desktop/mobile widths, focus and
confirmation behavior; broader touch/zoom/second-engine/device and real-market acceptance
remain open. See [the interface guide](ui-experience.md).


Final automated checks: **1,216 Python tests passed**, **10,540 / 11,440 statements
(92.13%)** covered; **193 Node UI tests passed**. Ruff lint, formatting of **201 source
and test files**, mypy (**118 source files**) and whitespace checks pass. The coverage
run emitted **55 warnings**, including test-workflow SQLite ResourceWarnings. A
repository-wide formatting probe additionally flags pre-existing Python examples in
`BACKEND_IMPROVEMENTS_AND_ROADMAP.md`; that unrelated document was not reformatted.

Desktop Firefox at a 1920 × 1080 window was checked using localhost:8767 with a new
disposable database and an invented operator token. Evidence covers rendered local
icons, labelled navigation, collapsed setup, Dashboard, Portfolio valuation warnings
with definitions closed, Risk fieldsets, empty Analysis and four-group policy
progress/focus. The policy review rejected 80.0001% invested plus 20% reserve, then
showed exact 80.0000% / 20.0000% in a visible deep-scroll native dialog after
correction. Escape cancelled; edits were discarded, reload locked the view and
private content cleared. An independent SQL read retained cash **25000**, fees **0**,
zero orders/fills/positions/events/quotes/decisions/portfolio requests, and no saved
policy files. No actual broker, feed, user account or financial action was used.

The populated backtest report, phone/touch, narrow-browser/zoom, second-engine and
assistive-device layouts were not rendered in this pass; their automated structural
and controller checks do not establish device acceptance. Full Phase 5 and actual
worker/broker acceptance remain open.

## V2 Phase 5 draft-policy validation scope (0.18.0, 23 October 2026)

The pure contract suite has **132 passing cases**: no financial/schedule defaults,
both horizon units/cadences, independent canonical semantic hashes, display-name
independence, strict extras/types, exact decimal scale/bounds/nonfinite rejection,
coupled allocation limits, immutable inputs/models and independence from a hostile
host Decimal context. A specified draft must continue to report activation/backtest
support false. Legacy strategy identities are not reused for this new family.

Schedule checks use declared synthetic calendars to verify original-day month/leap-year
clamping, exclusive horizon boundaries, full calendar-month/quarter coverage, aware
knowledge time, missing parameters, skipped/no-session periods and bounded cycles.
No weekday, session or catch-up date may be invented. Source completeness remains an
explicitly unverified operator claim; preview availability is not execution authority.

Store/API checks cover no files on read/preview, owner-private immutable records,
independently reproducible snapshot/semantic identities, exact same-content idempotency,
changed-preview conflict, acknowledgement and strict body/schema budgets, corrupt/unsafe
storage, bounded counts/bytes and independent persisted-account equality. CLI checks
must prove stdout-only inspection/scheduling, no account/lock/WAL/report creation,
clock/calendar failure behavior and no downloads. UI checks cover labelled metadata
forms with null defaults, exact strings, incomplete-save confirmation, copy/edit identity,
unsaved navigation guards, explicit uncertain-save reconciliation, no automatic POST
retry, Cancel/Escape and lock/pagehide/late-response private-content clearing.

Full integrated run: **1,213 Python tests passed**, **10,537 / 11,437 statements
(92.13%)** covered; **186 Node UI tests passed**. Ruff, formatting (**200 files**),
mypy (**118 source files**) and whitespace checks pass. The coverage run emitted
**56 warnings**, including remaining test-workflow SQLite ResourceWarnings; these
are not evidence of a production connection leak. Earlier release counts remain historical.

Desktop Firefox was checked with a disposable private account: blank inputs, explicit
months/quarterly selection, deep-scroll confirmation, unchecked acknowledgement,
Escape cancellation, confirmed incomplete save, reload/lock privacy, saved-snapshot
survival and navigation back to the existing Strategies setup. The saved JSON was read
independently and its selections checked; the disposable SQL ledger retained cash
₹25,000, zero fees, zero orders and zero held positions. Its server and tab were closed.
Broader keyboard, mobile/touch, zoom and second-engine acceptance remain open.

The lockfile's 66 dependency records match the baseline exactly; 64 installed package
versions match their pins (two platform/optional records are absent). Only the local
project version changes. `uv` was unavailable, so a fresh frozen `uv sync` was not run.

These checks are local/synthetic evidence. They do not establish genuine future exchange calendars,
native worker isolation, investment-policy execution, broker/device acceptance or
strategy profitability. The existing implementation-Mac runtime gate remains unavailable.
See [the usage and failure/recovery contract](investment-policy-drafts.md).

## V2 Phase 5 validation scope (0.17.0, 22 October 2026)

The new suites target private resource registration/integrity, strict API admission and
idempotency, single-worker/queue bounds, cancellation/publication races, restart
interruption, artifact hashes and independent read-only persisted accounting. Synthetic
launcher/lifecycle tests must remain labelled simulated; they cannot establish native
sandbox or hard-budget enforcement. Portfolio checks independently reconstruct exact
cash/held bid values and prove reservations/claim exclusions and whole-ledger/mode
invariance. Pure metric tests use independent arithmetic references for endpoint/CAGR,
daily paths, sample variance/downside formulas, primary/provisional/flow gates and
complete/partial months, including immutable inputs and private Decimal context.

New DOM checks cover resource/limit/holding-cap review, no POST on open/cancel/Escape,
secure stable request keys, uncertain-submit reconciliation without automatic retry,
job outcomes, exact report values, compatible-resource comparison, bounded disclosures,
read polling/backoff and lock/pagehide/late-response privacy. Portfolio allocation checks
cover exact values, missing/stale unavailability and private-content clearing.

Final integrated run: `.venv/bin/pytest -q --cov=trading_agent` **958 passed**;
**10,040 / 10,929 statements (91.87%)**. `node --test tests/ui/*.test.cjs`
**172 passed**. Ruff and mypy (**113 source files**) pass, as do whitespace checks.
The coverage run emitted **56 warnings**, including SQLite connection ResourceWarnings
in remaining test workflows; warning attribution is not a production-leak diagnosis.
New connection reads in the allocation/job test suites explicitly close their handles.
Runtime-version regressions reject a changed code hash/fee definition before admission
and reject rehashed report code/charge identities that differ from the reviewed resource.

A disposable synthetic account was served on localhost and inspected in desktop
Firefox: memory-token handoff, registered input selection, unavailable launch, collapsed
budget disclosure, sidebar navigation and exact all-cash allocation rendered correctly.
The temporary server/tab were stopped/closed. No operator account or broker was used.
This limited smoke check does not certify populated report rendering, native worker
launch, modal/device/keyboard/zoom acceptance or sustained operation.

Previous releases' results below remain historical. On the implementation Mac,
`RLIMIT_AS` failed with `ValueError` and the Codex environment denied the Darwin sandbox
probe. Actual isolated-worker launch is unavailable, not passed. No Linux/Pi browser
sandbox backend exists. Real OS allowed/denied reads/writes/network and budgets,
broader Firefox/second-engine/mobile/touch/zoom, sustained broker/source entitlement,
target-device and profitable-strategy acceptance remain open. This slice does not
complete Phase 5's new strategy/parity/OOS/benchmark/rebalance gates.

## V2 Phase 4 checks (0.16.0, 22 October 2026)

Executed `.venv/bin/pytest -q --cov=trading_agent --cov-report=term-missing:skip-covered`:
**828 passed**, 9,066/9,814 statements (92.38%). `node --test tests/ui/*.test.cjs`:
**157 passed**. Ruff, changed-Python formatting, mypy (104 files), limited project
secret scan and whitespace checks passed. The coverage run emitted 76 warnings,
including SQLite connection ResourceWarnings in test workflows; cleanup is still
open and warning attribution is not a production-leak diagnosis.

New regression tests: 26 exact indicator/reference cases; 34 independent eligible-series/
corporate-action/period/schema/report cases; 59 strict local benchmark cases; 23 exact
legacy ranking explanation cases; 16 authenticated API/isolated CLI functional cases.
References independently check Fraction arithmetic, warmup indices/seed rules, flat RSI,
ATR15, MACD26/signal34, prior-only support/resistance, price-vs-TRI drawdown and 20 matched
daily relative wealth growth rather than percent-point spread. Future perturbation,
late review/price/membership, missing dates, cross-year/holiday/early-close inputs,
strict hash-bound completeness declarations, partial periods, gaps and coherent split/
volume/dividend clocks are covered. Source and final report bytes are independently hashed.

API tests forbid desk.view/tick, research refresh and engine polling, then prove whole
SQLite dumps and independent exact partial-fill cash/cost/fees/reservations unchanged
past proposal expiry/account-day boundaries. Invalid evidence and unexpected failures
return sanitized 503 without fault/revocation. They preserve legacy raw split bars,
validate query scope, and prove 350-bar warmup precedes the 300-bar display slice.
Subprocess CLI tests deny networking, prove absent account/lock/WAL files remain absent,
verify private output hashes and manifest-last/no-overwrite/input-output separation,
and reject ambiguous clocks or invalid context without a successful artifact.

UI tests cover intervals, 15 exact indicator fields, warmup/unavailable reasons,
source/volume/calendar context, matched/missing/simulated benchmark labels, legacy
rank evidence, gap-safe overlays, range changes without GET/reseeding, and clearing
private content on lock/pagehide/late JSON. These are simulated DOM checks. Full
rendered Firefox/second-engine/mobile/touch/zoom, licensed source validity, real broker/
device performance and strategy profitability remain external acceptance gates.


## V2 Phase 3 runtime checks (0.15.0, 22 October 2026)

Executed `.venv/bin/pytest -q --cov=trading_agent --cov-report=term-missing:skip-covered`:
**670 passed**, 8,405/9,116 statements (92.20%). `node --test tests/ui/*.test.cjs`:
**148 passed**. Ruff and mypy (99 modules) passed. The coverage run emitted 41 warnings,
including SQLite connection ResourceWarnings in existing test workflows; cleanup is
still an audit task. Full logs were kept only in temporary local files.

New read-model unit/HTTP tests independently reconstruct exact persisted partial-fill
cash/fees/basis/reservations, stale prices and a real simulated fractional corporate
claim. Whole SQLite dumps, proposal states, mode/revision and in-memory authority are
unchanged by reads across expiry/day boundaries; accidental writes fail on `mode=ro`;
sanitized read failure returns 503 without invoking mutation-fault recovery. No broker
network or operator account is used. Functional checks cover the twelve served pages,
static helpers, no-store/framing and balanced accessible labels.

New DOM/controller tests cover six saved-state destinations, exact large decimals,
filter/sort/comparison bounds/coverage/empty/error states, unavailable capabilities,
private-state clearing and late JSON. Shell tests cover twelve routes, legacy aliases,
actual child path/origin/source handshake, guarded anchor/purchase-subview changes,
mobile menu and inert parent navigation during confirmation. Shared helper/controller
tests cover modal focus-before-open, Escape/cancel/noPOST, single submission, pagehide,
deep scroll, visual viewport/keyboard/zoom offsets, scaled bordered frames, long content,
offscreen refusal, native delayed close and cleanup, including 360/768/1440px scenarios.
These are simulated DOM and geometry inputs, not browser screenshots.

A disposable local read-only preview opened the locked shell in Firefox. User changes
to the active Firefox window interrupted interactive checking. Full rendered desktop/
mobile, keyboard/touch, 200% zoom, Firefox plus a second engine, sustained broker feed
and target-device acceptance remain open. See [the implementation guide](frontend-modernization.md)
and [Phase 2 acceptance matrix](phase-2/acceptance-plan.md) for remaining gates.


## Phase 2 design validation (22 October 2026)

Run the [reproducible design checks](phase-2/acceptance-plan.md#design-checks-that-can-run-now):
`validate_design.py` passed routes/aliases, 15 proposed vectors, document links, unique
HTML identifiers/labels/structure, offline boundary and 11 required contrast pairs;
`validate_financial_examples.py` passed **129 independent comparisons** for 7 synthetic
ledger cases and 2 return paths; `node --test docs/phase-2/validate-prototype.cjs`
passed **6 tests**, including all twelve screens × four example states, local dialog
cancel/confirm and mobile-menu state. Ruff, helper formatting and whitespace passed.

These are design/simulated-DOM/arithmetic checks, not rendered-browser, persisted-ledger,
market, strategy-performance or device acceptance. No new runtime behavior was written,
so the financial application suite was not rerun. The [acceptance matrix](phase-2/acceptance-plan.md)
defines the real implementation gates; named future strategy scenarios have not run.


## V2 Phase 1 audit baseline (22 October 2026)

Fresh run on commit `2d5c208`/0.14.0: **660 Python tests passed** with **92.13%**
statement coverage (8,322/9,033), and **117 UI DOM tests passed**. Ruff, mypy on 98
source files and the limited `scripts/check_secrets.py` pattern scan passed. Python
3.13.16/Node 22.14.0 were used. Coverage produced unclosed SQLite connection
ResourceWarnings during test workflows; the audit does not infer a production leak
from warning locations, but explicit test connection cleanup needs investigation.

A temporary harness instantiated the real Setup controller with an invented account
response and frame geometry. It verified positioning before modal focus, deep scroll,
parent resize, visual viewport/keyboard bounds, cancellation cleanup and zero mutation
requests. This ad hoc probe is not a checked-in regression suite, CSS rendering or
Firefox acceptance. Existing committed UI tests do not cover all rendered dialogs.

Additional disposable audit probes reproduced early-year calendar preparation failure,
a benign-repeat false-pause in the dedicated intraday controller, and indistinguishable
403/429/503 broker recovery guidance. They used synthetic/mock inputs and no authenticated
broker session or operator database. Proposed differential strategy tests, real browser
layout/keyboard/zoom tests and source/benchmark/fundamentals acceptance gates are in
[IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md). No application fixes are made in the
Phase 1 audit; approval is required before implementation.


## Light workspace and saved-data analysis (0.14.0, 22 October 2026)

Final validation: `.venv/bin/pytest -q` **660 passed**;
`node --test tests/ui/*.test.cjs` **117 passed**. Ruff lint, changed-Python format
checks, mypy on **98** source files and `git diff --check` passed.

New checks cover the real served light-page markup, unique IDs, structural balance
and label/ARIA targets; same-origin framing on Strategies/Analysis; route migration,
shared-token origin/window boundaries, lock/late responses, contextual onboarding
and navigation without mutation. Broker checks verify relevant first-step selection,
keyboard-native summaries, step navigation without API calls, edit/open-state
preservation, inline failure recovery and private overview clearing. Dashboard/UI
checks retain exact huge/fractional server money, account P&L date, stale/incomplete
valuation disclosure, missing values, separate strategies and scoped activity counts.

Invented local chart datasets/candles validate daily availability/completion and
fingerprints, exact Decimal SMA arithmetic, bounded minute reads, exclusions/gaps,
malformed input recovery, symbol/interval validation and credential-free public shells.
Independent SQLite connections compare full dumps before/after authenticated analysis
reads, including exact ₹25,000 cash and zero orders/fills/positions. A read beyond a
pending proposal's expiry neither expires it nor changes Approval mode. The chart
frontend tests preserve source decimals in tables, show real missing/provenance/stale
states, label usable quotes as snapshots, filter saved symbols, abort timeouts and
clear late/locked data. These checks use explicitly invented inputs; they do not
contact a broker or place test orders in the operator account.

Interactive acceptance is separate. A disposable empty-account local preview server
was started with no broker connection and then stopped. Firefox's native capture
returned mismatched/stale images rather than a reliable preview rendering, and no
supported isolated browser was available. Desktop/mobile visual layout, touch,
keyboard operation, screen-reader usability and real broker/device acceptance are
therefore **not claimed** by the automated DOM/HTTP tests. The operator process was
not restarted, its mode was not changed and no setup/trade confirmation was sent.


## Live quote ties and cancellation/idle-mode evidence (22 October 2026)

Full suite: **650 Python**, **99 JavaScript** tests passed; Ruff lint/format, mypy and
diff whitespace checks passed. New synthetic tests validate unchanged-repeat no-ops
without clock/depth renewal, strict receipt-ordered live ties, backward/ambiguous/source
and volume failures, replay strictness, candle OHLC/volume deltas and exact independent
persisted cash/fill reconciliation. Tied books cannot reuse a fill budget; a tied stop
can cancel residual buys/queue protection, but its sale waits for a newer exchange
timestamp. Raw full-mode packets through Setup callbacks no longer cancel Approval
on normal ties; a true backward packet still pauses with a concrete recorded cause.
Hard fault/disconnect tests ensure snapshot failure cannot precede memory revocation.
UI cases distinguish proposal/order cancellation, creation/update times, pause causes
and daily no-replay summaries. A cancelled signal remains cancelled after mode changes.

Separate real observations: the account journal contained six Approval proposals
cancelled five seconds after creation, no orders and repeated quote-order failures.
An eight-second raw broker probe saw 44 quotes with eight same-second ties (three
unchanged receipts, five changed books). A later isolated corrected-engine probe saw
68 quotes, 20 changed ties, no quality failure/fault and no order. These are different
short live windows, not a controlled performance comparison or sustained acceptance.
The operator account's mode, history and orders were not modified by those probes.

## Direct daily-review shortcut (22 October 2026)

97 JavaScript tests pass, including same-day IST readiness, stale data, Manual and
custom-route restrictions, installed/first/ML policy handling without fallback, preview
only until unchecked acknowledgement is explicitly changed, cancel/lock/late responses,
readiness-card wiring and hiding after resolution. The 17 guided unit/HTTP tests pass;
the new HTTP case independently compares persisted SQLite, exact ₹25,000 cash and
config before/after preview and rejected acknowledgement, with no reviews/orders/fills
or feed request. Ruff lint and changed-test formatting pass. Tests use invented sources.

Separately, the current local server serves all new button/script assets (HTTP 200).
The genuine-data preparation completed 65 stocks × 60 sessions for a review only.
A later actual read-only status/database inspection found today's seven reviews,
incoming accepted quote times, zero API blockers, Manual, unchanged cash/fees and no
orders/holdings. This assistant did not submit the confirmation. This bounded evidence
does not establish sustained feed continuity, strategy returns or interactive/device QA.

## Quote review blockers and workspace fragment recovery (22 October 2026)

Full validation: `./.venv/bin/pytest -q` **637 passed**; `node --test tests/ui/*.test.cjs`
**90 passed**. Ruff lint/changed-Python formatting, mypy on all source modules and
`git diff --check` passed. Unit/functional tests independently read SQLite to retain
exact cash and persisted state across diagnostic reads, reject next-day quotes until
today's review, and require a new accepted quote after review. Desk and console report
the same cause; stale/empty/reconnect observations remain unusable under existing gates.

JavaScript checks cover direct legacy redirects, same/cross-section fragments,
unlock/render deferral, details expansion, height-before-scroll ordering, sticky versus
static navigation offsets, focus, repeated-link handling and matching origin/source.
No reveal issues a POST or auto-applies a shortlist. Modified text is rendered safely.
Live journal inspection found review-blocked incoming quotes and only prior-day reviews;
this is distinct from simulated checks and does not attest corporate-action clearance,
fresh-market fills, broker entitlement, interactive desktop/mobile or target-device
acceptance. The operator-owned account/service/selection/reviews/mode were not changed.

## Combined guided setup (0.13.1)

New invented-data unit and HTTP tests cover read-only previews, exact ranked shortlist,
listed current-day basis reviews, unused-calendar correction, strict acknowledgement,
authorization/origin/extra-field rejection, expiry/date/revision/cash/source/kill changes,
quarantine preservation, ML refusal without fallback, connection partial failure/recovery,
interrupted attempts, no repeat on a completed retry and Manual throughout setup.
HTTP tests proceed through the one-confirmation flow, then independently choose Approval
or Automatic, ingest later invented quotes and reconcile exact persisted cash against
sum(fill price × quantity + fees) using Decimal and the existing ledger reconstruction.

Browser-controller checks cover hidden advanced forms, explicit policy, an initially
unchecked combined review, summary/correction text, cancellation, exact hash-only confirm
payload, duplicate click suppression, partial outcome, locks and late private responses.
Desktop/mobile visual evidence uses an isolated invented-data account, separate Chrome
profile and port 8016. It is not broker, actual-market or device acceptance.


Validation completed locally: **630 Python tests**, **77 JavaScript tests**, **92%**
overall Python coverage; Ruff lint/format (152 files), mypy (96 source files), frozen
offline lock/sync, sdist/wheel build and project secret checks passed. Isolated Chrome
checks at 1440 × 1100 and 390 × 844 verified no horizontal overflow, visible bounded
review dialog, initially unchecked acknowledgement, consolidated confirmation, Manual
outcome, current-day review persistence and shared unlock into activity, with no browser
exceptions. The embedded-parent resize/scroll listeners are removed on close/lock/unload. A separate
controller case verifies visible-parent sizing and listener cleanup for the existing
mode/trade confirmation as well.
No actual account reviews, strategy or mode were applied during validation.

## Genuine-data preparation and readiness (0.13.0)

Full local validation: **614 Python tests / 71 JavaScript tests**, **92% Python coverage**.
Ruff, formatting, mypy (95 source files), frozen offline lock/sync, wheel/sdist build and
project secret scanning pass. New financial workflow tests exercise the full mocked-provider
download → source/calendar/policy review → install → current-day basis review → Approval
and Automatic decisions → later quote-driven fills. Exact fill turnover/fees/cash debit
are checked independently against persisted account cash and journal reconciliation.

Unit/HTTP tests cover strict review booleans, no GET/download financial writes, request
idempotence, no ML fallback, current constituent observation clocks, historical execution/
ML rejection, ETF/ISIN and catalog restrictions, action/coverage exclusions, changed hashes,
private files, cancellation, restart without replay, stale dates, mode/connection/date
changes during validation, no arbitrary path/source URLs, redirect/size/credential controls,
global history read spacing and authenticated same-origin installation. CRLF source bytes
retain their original hashes through bounded reads. Corrupt or changed profile/data pointers
cannot select a different policy. Existing point-in-time and financial regression tests pass.
Additional checks cover mode activation during validation, acquisition across midnight,
explicit empty-account calendar correction, refusal after quotes/pinned reviews and
concurrent review usage preventing a previously eligible correction.
The official Nifty 500 file's temporary 501-row shape is supported conservatively:
495 regular INE equity-share rows retained, six REIT/trade-to-trade/dummy entries excluded.
This source parsing check is separate from the completed 65-stock Nifty 100 history run.

UI tests verify no auto-download/approval, blank explicit policy selection, unavailable ML
explanation, preserved edited reviews across refreshes, exact confirmation payloads, locking,
progress/failure recovery, server restart guidance and actionable reasons even when the
socket is connected. A separate headless browser with synthetic temporary data verified
1440px desktop and 390px mobile widths without horizontal overflow, real DOM form
preservation across polling, source/policy installation confirmation, retention of Manual,
remaining current-basis blockers and shared unlock into activity; zero browser exceptions.
Review checkboxes and their full labels remain accessible touch/click targets.

**Real read-only evidence, 21 October 2026:** official Nifty 100 CSV returned 100 members;
NSE holiday/action sources produced 60 proposed completed dates and excluded 35 members
with actions in that interval. All **65** catalog-matched remaining shares returned all
60 expected daily candles (**3,900 rows**). Saved original source snapshots and the
unreviewed draft in the private account analysis directory using a read-only SQLite catalog
adapter; no trading-account/config writes, source-review acknowledgements, strategy/mode
activation or orders were performed. This is acquisition/coverage evidence, not independent
calendar completeness, model validation, expected profit, installed-run or device acceptance.

Current-year/normal-hours proposal limits, conservative action exclusions, unavailable
real-market ML validation, manual refresh and separate execution-basis review are documented
in [strategy-preparation.md](strategy-preparation.md). No synthetic fixture is real-market
acceptance evidence.

## Trading desk / paper mode coverage (0.12.0)

Full local validation: **582 Python tests / 62 JS tests**, **92% coverage**.
New tests exercise default watchlist/no-profile behavior, broader daily screening and
unsupported class exclusion, approval-only proposals, automatic paper submission,
preview/repricing bounds, all stale/expired/drift/mode/hash/risk refusals, declined
signals, mode/feed/all-quote-loss cancellation and no silent reactivation. A journal
write fault revokes memory authority first. An injected post-authorization clock
advance proves durable-write delay cannot submit using an older quote time. A
concurrent manual-feed test holds the engine lock while time advances and verifies
the waiting callback cannot fill a pending order with its now-stale quote. The bound intraday controller cannot
approve after disarm, and the manual-profile worker emits actual completed-bar rule
signals or prior-daily long-term proposals. Synthetic fixtures and missing/failed ML
profiles cannot activate connected production analysis.

Functional HTTP checks cover bearer/Origin/strict acknowledgement, stale revision,
preview → approve → later observed fill, terminal retry idempotence, exact independent
cash/fee reconstruction, linked reasons, unchanged state on reads, cursor pages,
101 partial fills and held-preserving hash-bound shortlist application. Recovery
faults are injected before submission and after order commit/before linkage; no
interrupted authority is replayed. Removing authorization evidence is detected.
Discretionary SELL approval and independent protective stop paths both reconcile.
History waits are held on another thread while pause/kill completes, proving network
work does not own the risk lock. A short feed disconnect revokes mode even with the
watchdog disabled, preventing transient reconnect from silently resuming it.

JS checks cover no fetch before unlock, truthful manual-watchlist/model status,
explicit mode confirmation, reviewed money bounds, safe rendering, cancellation,
late-response lock handling, authorization failure and activity semantics/cursors.
An isolated headless Chrome with a separate profile/database exercised the actual
workspace/iframe shared unlock, desktop and 390-pixel responsive rendering, proposal
review/confirmation and accepted-order activity with zero fills. No root/child page
horizontal overflow was observed; mobile menu scrolling is intentional. These are
synthetic browser checks, not physical-phone, real-feed or profitability acceptance.

The [small synthetic loopback benchmark](benchmark-desk-macos.json) has 100 warm
requests per endpoint with a three-symbol profile/one execution symbol/one unfilled
order. p99 desk 0.9474 ms, activity 0.7265 ms includes HTTP serialization/DB views,
not history acquisition, a 500-symbol workload or target-device latency.

## After-hours transport regression coverage (0.11.1)

Unit cases independently zero best bid/ask prices and quantities, preserve a second
usable instrument in a mixed batch, and retain rejection of unknown tokens/trailing
corruption. Bounded retry tests verify ten failures/nine waits, final failed/stopped
states, snapshot isolation and fixed timeout codes without exception details. Existing
invalid-packet/broker-error tests verify safe failure classification. Functional HTTP
coverage runs the actual worker against a mocked full packet while an order is pending:
connection stays online, ignored-book count advances, no symbol becomes fresh, and
persisted order/cash/fee/reservation/position state remains unchanged. UI tests distinguish
connected transport from usable depth and give retry-exhaustion recovery without exposing
unknown error text. Prior-depth invalidation/recovery tests prove a new entry is rejected
immediately despite the earlier quote's age, then permitted only after accepted valid
data. Service tests prove immediate intraday disarm while remaining connected and no
automatic rearm after recovery. Full validation: **547 Python / 56 JS tests**, **93% coverage**.

Separately, an actual diagnostic-only broker check after market hours verified HTTP 200
profile, successful WebSocket handshake and the original zero-sided packet failure.
The corrected worker stayed connected for 15 seconds with five ignored books and zero
usable quotes. No callback entered the user's account; no order, review or arming occurred.
This brief observation does not establish fresh-market/fill or full-session acceptance.

## Shared menu coverage (0.11.0)

Functional checks cover authenticated read-only workspace metadata, actual manual
versus bound intraday cadence, public shell privacy, explicit framing allowlist and
unchanged account state. Launcher tests refuse older UI versions as well as mismatched
accounts. UI tests verify no private fetch before unlock, one unlock across menu
changes, exact origin/window/active-view token handoff, hostile hash rejection,
mutation/dialog navigation guards, global lock/authorization-failure propagation,
late-response suppression and preserved broker callback behavior. An integration
test uses the real Setup controller with the workspace bridge to prove shared unlock
does not falsely lock the parent. Physical-browser layout/phone acceptance remains
distinct from these DOM and HTTP checks.

## Browser setup coverage (0.10.0)

Unit and functional tests cover operator/Origin authorization, bounded secret bodies
without validation echoes, redacted upstream failures, private atomic credential
files and symlink/permission refusal, login state expiry/replay, persisted catalog
selection, pending-order/held-symbol guards, unchanged economic identity and exact
cash/fees/orders/positions. Calendar tests require strict review, preserve existing
definitions, verify idempotence and keep live/configured calendars unchanged on a
save failure. Feed callback tests receive synthetic quotes without creating orders
and latch candle-storage faults. The launcher probes only the correct account,
rejects redirects/mismatches and starts another process only after connection refusal.

JavaScript tests exercise locked/private state, credential clearing before awaits,
late-response suppression, callback origin/window/state binding, one-time explicit
exchange, safe text rendering and confirmation/cancellation for symbols, calendar
and feed changes. Legacy manual callback capture remains covered. Real broker login
and 2FA are not automated, and no phone/pixel acceptance is inferred from DOM tests.

All automated tests use virtual capital and synthetic or mocked market data.
No broker credentials, real orders or funds are used. Run from the repository root:

Phase 1 local result (20 October 2026): **108 passed; 90% reported coverage**.
The latest combined validation is recorded in [CHANGELOG.md](CHANGELOG.md).

```sh
.venv/bin/pytest --cov=trading_agent --cov-report=term-missing
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy src/trading_agent
.venv/bin/python scripts/check_secrets.py
.venv/bin/pip-audit --skip-editable
.venv/bin/python scripts/benchmark.py
.venv/bin/python scripts/benchmark_strategy.py
.venv/bin/python scripts/benchmark_ml.py --model data/ml-first/model --allow-synthetic-model
```

## Coverage matrix

| Suite | Evidence required |
|---|---|
| Unit models/config | Non-paper modes, public listener, invalid times/prices/size, NaN, unknown fields, naive timestamps |
| Unit costs/sizing | Independently calculated fees, adverse tick rounding, fee-inclusive maximum size, zero capacity, unattractive targets |
| Unit candles/features | Cumulative-volume deltas, incomplete/initial/gapped candles, monotonic data, VWAP/EMA/ATR hand calculations, session reset |
| Unit broker | Sanitized profiles, cash catalog filtering, completed history/gaps, auth checksum and route allowlist, binary depth/UTC decoding |
| Integration execution | Cash/risk reservations, partial fills, cumulative fees, cancel/stop/target/gap behavior, liquidity consumption, duplicate intents/quotes |
| Integration risk | Session/early-close boundaries, spread/stale/feed/model rejection, notional/position limits, daily mark-to-market loss and streak gates |
| Integration persistence | Exclusive account owner, rollback after fill on disk-full, policy mismatch, startup reconciliation, missing/corrupt state, private backup/restore |
| Functional API/CLI | Credential-free startup, authenticated entry→fill→kill→exit→reset, CSRF/Host boundaries, no live route, demo artifacts and mode guard |
| Replay | Identical events/config produce identical fills, balances and journal digest; invalid clocks/types fail |
| Security | Forbidden broker operations never reach transport, secret redaction, limited working-tree secret patterns, audited locked dependencies |
| Performance | Reproducible indicator and quote/journal/risk timings, preserving FULL durability |

`.github/workflows/ci.yml` repeats checks on Ubuntu with patched Python and the frozen
lock. CI is configured but has not been run on a remote service in this workspace.
Ruff and mypy cover application code. Tests exercise financial outcomes rather than
only checking implementation-shaped return values. Coverage reports expose untested
deployment/broker branches; no external acceptance is inferred from coverage alone.

The persistence suite includes actual child-process death before commit, not only
an exception mock. A seeded thirty-round-trip sequence combines partial buys,
residual cancellations, partial sells, same-time exit reissues and reconciliation
after each completed position to exercise monetary conservation across operations.

## Phase 2 automated acceptance

The added suite tests ORB/VWAP triggers and their distinct pullback requirements;
completed-candle warmup; prior-only volume/range features; session resets and missing
opening data; stale/missing/wide/empty quotes; independent risk rejection; future
quote prefix invariance; strict later-tick execution with zero latency; and absence
of fabricated OHLC fills or end-of-data closes.

Dataset tests cover chronological and availability clocks, restricted raw basis and
paths, input mutation, bounded reads, schema/field errors and rejected symlinks.
Export tests verify original orders/journal are unchanged, calendar provenance and
synthetic classification survive, overrides work and failed exports lack manifests.
Metric tests verify observed peak drawdown, net fees, null no-trade/no-loss ratios
and one completed trade across partial fills. Functional CLI tests generate/re-run
reports deterministically and preserve source orders during export. The strategy
benchmark records analysis-only latency separately from the existing ingestion path.

No real-market profitability or walk-forward ML acceptance is inferred from these
tests. Reports retain incomplete exposure and research evidence gaps.

## Phase 3 automated acceptance

The ML unit/integration suite covers finite fixed-schema feature construction,
candidate identity, future/incomplete/missing input rejection, actual fee-inclusive
labels, later-tick fills, stops/targets, partial quantities, horizon exits and
separate censor outcomes for interruptions, quote gaps/quality, flagged candles,
unfilled entries and unresolved exposure. Failed builds lack completion manifests.

Split tests exercise whole-session grouping across simultaneous symbols, expanding
windows, final holdout exclusion from all fits, crossing label intervals and strict
embargo equality. Model tests prove scaling/base coefficients use training only,
calibration labels affect only the calibrator, holdout changes cannot affect fitting,
and final coefficients exist before holdout metrics are computed. Insufficient or
single-class samples fail, and reliability/gate diagnostics remain inspectable.

Artifact tests reject corruption, missing manifests, NaN, wrong dimensions/scales,
feature schema changes, inconsistent reports, oversized files, symlinks, failed
metrics, wrong config/fees and future validation cutoffs. A fresh-process check
proves model loading imports no NumPy, SciPy, sklearn, joblib or pickle.

Scored research tests verify deterministic results and same-time ranking before
independent position gates; later prices cannot change earlier scores. Risk tests
exercise missing/unscored/wrong-model/changed-candidate vectors, idempotency conflicts,
unchanged sizing, kill/position gates, durable model binding and missing metadata
failure before pending-order recovery. Functional CLI tests run label→train→score,
check artifacts and confirm the service database is never opened. Wrong mode and
invalid command/override failures remain sanitized.

CI includes the synthetic workflow and inference/ranking benchmark. All performance
timers state their excluded work. Real-market model performance and full Pi/feed
acceptance remain unverified; a synthetic diagnostic pass cannot establish either.

Final combined local result on 20 October 2026: **215 passed; 93% overall coverage**.
There are 56 added Phase 3 cases. Feature/schema modules reached 100%, training and
sample validation 99%, inference 97%, labeling 94% and report validation 91% statement
coverage. Ruff, formatting, mypy, secret-pattern/Markdown-link checks, frozen lock,
offline builds and dependency audit passed. See [CHANGELOG.md](CHANGELOG.md).
Availability tests also cover the complete validation session and delayed source
observations after the last labeled trade.

## Manual external acceptance

Before claiming deployed Phase 1 readiness, complete a real manual login and read-only
profile/history/stream check, inspect the current NSE calendar and broker entitlement,
install the service under a dedicated user, reboot, exercise network interruption,
measure target-device latency with positions, and rehearse backup/power recovery.
Record dates, OS/architecture, policy/code revision, fee version and artifacts.
These checks need real hardware/account access and remain explicitly unverified.

The final local command results and any limitations are recorded in
[CHANGELOG.md](CHANGELOG.md). A dependency scan is checked at implementation time;
repeat it before deployment and every dependency update.

## Phase 4 automated acceptance

Added supervised startup/arming/history readiness, disabled-entry backfill, causal
later-quote fills, history deduplication, independent risk rejection, manual-controller
bypass refusal and ranked multi-symbol position admission tests. Interruption cases
cover disconnect, watchdog silence, first resumed quote without an intervening tick,
conflicting/volume-regressed data and stale exchanges. Holdings stay open until valid
liquidation data returns; kills persist.

History tests cover missing/flagged/future/revised/foreign-symbol candles, model age,
synthetic connected-model rejection, calendar/cutoff changes, clock regression and
storage failure. Restart tests preserve pending entries during identity rejection,
then verify cancellation and disarmed rewarm under the correct controller. Concurrency,
connection generations, retry cadence, first-bar request ranges, monotonic rate pacing
and worker shutdown are tested.

Functional API cases verify authenticated arm/disarm, Origin protections, readiness
without nested transactions, manual-intent rejection, kill/reset independence and
background stale-feed disarming. CLI cases exercise model-bound initialization,
option requirements, source-preserving reports and all four synthetic fault drills.
Metrics tests verify bounded windows and cumulative budget counts. Reports reconcile
money and retain unfinished exposure and crash limitations.

Combined local result: **259 tests passed; 92% coverage**. Paper runtime reached 91%,
service 90%, reports/demo 93%, metrics 100%, independent execution 93%. These use
invented data or mocked read-only broker responses and do not establish feed access,
empirical fills, full-session coverage, hardware recovery or live readiness. CI runs
the drills and populated-account benchmark.
Additional cases preserve observed candle receipt/connection clocks on export,
reject missing clocks/overrides, and cancel pending buys at model-age expiry.

## Version 0.4.1 console and acceptance tooling

Combined local result: **284 Python cases and 13 JavaScript cases passed**. Python
statement coverage is **92% overall**, preflight **97%**, combined console view **93%**,
API **90%** and independent execution **93%**. There are 25 new Python cases covering
running WAL account inspection without cancellation/events, missing source paths,
unknown sessions, official SQLite fix branches, policy/permission/low-disk failures,
corrupt/missing state, schema refusal, query budgets, symlinks, private/exclusive
hashed artifacts and failed output without a finished manifest. Functional API/CLI
cases exercise authentication, bounded history, feed/kill/stale diagnostics, disarmed
polling, security headers/assets, missing-account diagnostics and strict exit codes.

Run the dependency-free browser logic suite with Node 24:

```sh
node --test tests/ui/console.test.cjs
```

It tests exact decimal/rupee display, locked shell and text-only injection handling,
late responses after lock, six-second display staleness, arm/reset confirmations,
post-action/poll ordering, auth failures, visible-tab polling, overlap suppression,
immediate kill messaging, unknown timeout outcomes and server reset rejection.
These tests execute application JavaScript using a minimal DOM harness; they are
not browser rendering, accessibility certification or physical touch acceptance.
Node is for tests only and is not a runtime frontend dependency. CI includes the
same Node suite alongside Python checks; remote CI was not run here.

Desktop Safari was visually checked with an isolated virtual account: account/readiness
cards, lock/unlock and kill/reset dialog behavior. The preview returned flat at
₹25,000 with kill inactive. Small-screen visual/real handset verification remains
pending: browser automation did not yield reliable mobile evidence. The source/wheel
build contains all three UI assets and loads them outside the repository. Original
account read-only preflight reconciled cash ₹25,000.00 with no holdings/pending orders;
operator-token configuration is correctly blocked in the unconfigured shell.

## Long-term LT1 automated and local acceptance (0.5.0)

Combined local result: **328 Python tests and 17 JavaScript tests passed**; **92% Python
coverage**. The 44 added Python cases cover overnight/weekend retention, required and
strict/idempotent reviews, persistent quarantine, changed price rejection, opening-gap
loss accounting, cross-day high-water/drawdown, same-day and cross-day partial DP,
exit cancellation/restart latches, horizon/config/model refusal before recovery,
fee cash shortfall, rollback, corruption/missing metadata/journal, held feed coverage,
current API/Origin/auth behavior, source-preserving private hashed reports, horizon/
cost preflight and isolated CLI drills/refusals. Intraday and ML regressions pass.

Long-term policy coverage: **96%**; delivery reconstruction **93%**; charges **100%**;
independent paper broker **93%**; long-term demo **90%**, report **92%**; API **91%**.
The JavaScript suite adds four cases for horizon/review fields and clearing, explicit
quarantine confirmation, typed symbol-only holding exits and stale-review blocking.
A populated 2,000-quote Mac benchmark measured long-term p99 **0.3288 ms**, excluding
network/parsing/contention/history/Pi, with WAL/FULL preserved.

Desktop Safari displayed the long-term horizon, virtual account/buffer, blocked
readiness and review form in an isolated flat/no-feed account. No market-data session,
real order or custody action was attempted. Mobile/actual-device acceptance remains
pending. Original-account read-only checks and final quality/build/audit results are
recorded in [CHANGELOG.md](CHANGELOG.md). See [long-term.md](long-term.md) for exact
supported behavior and the still-missing adjustment/research/settlement milestones.

## LT2 corporate-action validation (0.6.0)

Current combined result: **387 Python tests, 19 JavaScript tests, 92% Python coverage**.
New tests cover integral split/bonus and conservative tick levels, unchanged basis,
ordered split/bonus/dividend quantities, nonspendable net entitlements, exact and
zero receipts, whole-share sale before payment, retained rational fractional claims,
separate income/capital P&L and idempotent retries. Failure cases include ambiguous/
oversized/symlink input, strict flags/ratios, future dates, conflicting IDs, duplicate
payment, accepted ex-date quotes, fractional chains and changed used calendar.

Fault tests roll back action and receipt mutations after journal write; corruption
checks cover tables/events/claims/caches/receipts/cash/holding protections. Restart
requeues latched exits for adjusted shares; backup reopens with claims intact.
Functional CLI tests exercise isolated lifecycle, offline ownership, adjustment/
receipt/report flow and source preservation. JavaScript adds separate claim display
and updated quarantine confirmation. The direct and CLI invented lifecycle verifies
₹25,029.42 final cash = seed + capital realized P&L + received dividend income.

The populated unpaid-dividend benchmark records p99 **0.2564 ms** on this Mac;
network, callback contention and actual Pi/mobile/custody acceptance remain excluded.
See [corporate-actions.md](corporate-actions.md) and the change log for final checks.

## LT3a daily research validation (0.7.0)

Current combined result: **420 Python tests and 23 JavaScript tests**, **92% Python
coverage**. Daily analysis **97%**, input validation **93%**, report renderer/demo
**100%**. Thirty-three new Python cases include strict clocks/OHLC/ratios/volume/input
bounds, future-prefix invariance, split/dividend gross wealth, late price/basis,
universe removal/re-entry, gaps, missing/latest/empty states, source mutation,
private hashed artifacts, symlink rejection and isolated CLI behavior. Four new
JavaScript cases cover explanatory rendering, safe text, filter/sort/clear/focus,
empty states and large-value display. CI executes all UI tests, daily demo and benchmark.

Actual browser pixel/handset acceptance is pending computer-use permissions. The
synthetic screen is not a daily fill/backtest/model validation or real-market result.

## LT3b quote execution and daily ML validation (0.8.0)

Current combined evidence: **479 Python tests, 29 JavaScript tests, 92% Python
coverage**. Fifty-nine new Python cases include exact fees/cash/reconstruction,
later fills/private artifacts, adverse independent labels, source exhaustion,
partial/unfilled/interruption/stale/gap exclusions, input identity/paths/clocks,
closed-hour coverage, unavailable/late daily review and rebuild invariance,
premarket membership availability, overnight session-limit exits,
capacity/rank, contradictory basis/OHLC, sourced split-before-entry, dividend/payment
routing and counterfactual cash censoring. Model cases check separate namespace,
whole-session interval purge/embargo, disjoint training/scaling, after-validation
availability, matching audit/candidate/cash evidence, corrupt/rehashed artifacts,
failed holdout refusal, synthetic/context gates and no heavy training imports in scoring.
Functional CLI exercises isolated replay/labels/train and fail-closed intraday config.

Six new JavaScript cases cover exact large money, incomplete exposure, explicit
label/portfolio meaning, view/search/clear/focus, failed validation, 200-row disclosure,
empty states and exponents. CI runs daily end-to-end ML demo and separate benchmark.
Ruff/mypy/frozen lock/build/resource/dependency/secret checks supplement behavioral
validation. Browser pixel/physical-phone and actual broker/Pi evidence remain pending.
See [daily-execution.md](daily-execution.md) and [implementation-plan.md](implementation-plan.md).

Final local checks: Ruff lint/format, mypy, frozen offline `uv` lock/sync and installed
dependency consistency pass. Sdist/wheel builds pass; wheel-loaded console/daily/
execution resources and escaped CSP rendering work outside the repository. Secret
patterns and all local links in 22 Markdown files pass. Online advisory scan reports
no known vulnerabilities. Read-only preflight leaves the original account at exactly
₹25,000, zero fees, flat/no orders and its legacy risk hash; operator/calendar/broker/
device readiness remains explicitly incomplete. No new dependency or broker action.

## LT3c1 contribution/SIP verification (0.9.0)

Current combined evidence: **511 Python and 36 JavaScript tests**, **92% coverage**.
Thirty-two new Python cases cover budget/protection/position capacity, concrete
approval and stale contexts, partial/restart/idempotency, damaged/missing proof,
concurrent confirmations and transactional fault rollback, explicit SIP schedules/
missed/cancelled occurrences and pinned calendar changes. Split→addition→partial/
final sale checks exact pooled cost/P&L and one DP charge. A deterministic two-run
lifecycle compares financial journal digests; functional CLI preserves its configured
account and verifies private finished artifacts. API tests cover bearer/origin,
manual-long-term guards, typed payloads and preview→confirmation→actual later fills.

Seven new UI cases exercise exact money/text safety, locks/late responses, preview/
explicit single confirmation, blocked reasons, stale/cancelled dialogs, due-plan IDs/
save/cancel and unknown outcomes without retries. Full existing intraday/long-term/
ML/security tests remain. AST import checks cover execution/portfolio/risk/actions.
CI adds `portfolio-demo` and populated benchmark; full [usage](portfolio-contributions.md)
distinguishes original acquisitions from current/FIFO ownership. Actual broker/Pi/
phone/pixel and portfolio rebalance/cross-account acceptance remain pending.

Ruff lint/format, mypy, frozen lock/sync, installed package consistency, sdist/wheel,
outside-repository shared/new UI resources, secret scan and links in 23 Markdown
files pass. Online `pip-audit --skip-editable` reports no known vulnerabilities.
Actual localhost:8003 asset/CSP/bearer/four-lot checks pass on the separate preview
copy; the original demo artifact hashes remain unchanged. Original account read-only
preflight retains ₹25,000, zero fees/events/orders/holdings and the legacy risk hash.
Missing operator/calendar/broker/device readiness is still disclosed.
