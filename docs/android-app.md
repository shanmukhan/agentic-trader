# Agentic Trader for Android

## Android source 1.1.0 / code 11 — Watchlist

The bottom navigation now offers Watchlist; Stock Discovery remains in More and
via Watchlist. Search saved NSE catalog symbols, add/remove permitted stocks, and
review/acknowledge the exact list before saving. Unsaved edits are guarded before
navigation; lock removes private state. The same backend gates apply to all native
purchases, including contributions/SIPs. The screen explains feed-selection gaps,
25% order costs, daily slots, drawdown pause, stale valuations and data lockouts.
Drawdown-reference reset uses a separate acknowledged review in manual mode and
cannot rearm trading. Unknown mutation outcomes route inspection to Watchlist with
no automatic retry. See [watchlist-safety.md](watchlist-safety.md).

Invented offline fixtures and native regression cases were updated. No test cases
were run at the user's request; no APK is published and no biometric/device/market
acceptance is asserted for this source revision. Android compilation was attempted
without tests: the wrapper distribution download timed out; the installed Gradle
9.7.1 offline fallback lacks Android Gradle plugin 9.4.1. It did not compile the app.

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

## 1.0.9: account loads before automatic checks

Discover and other already-loaded daily tabs now display saved results immediately and
refresh quietly, without the top loading bar or disabled navigation. Their source/check
timestamps remain visible; a real refresh failure still marks data stale. Pages without
saved content keep an explicit initial loading state. Financial actions still revalidate
server state and require the existing confirmations.

Backend **0.20.9**, Android **1.0.9 / code 10**. The top indeterminate bar is the
foreground-request indicator. 1.0.8 accidentally made its first daily check depend on
`GET /api/operations?audit=true`. With a full Nifty 50 setup, that report repeatedly
resolved the basket for every catalog instrument while holding shared locks. Live
measurement exceeded 55 seconds and the phone timed out at 50 seconds; subsequent
account reads could also queue behind the report. Healthy basic reads initially took
0.007–0.172 seconds. Public health remained reachable, so the message alone did not
establish an Internet outage.

Account opening now completes independently of automatic checks. Those checks run in
quiet polling and use `GET /api/desk/preparation/audit`: source hashes, IST date, current
job/universe and completed-session coverage, without catalog scans, a ledger audit or
the quote/risk lock. The full operations report also resolves the basket once. Accounting
checks and trading authority remain unchanged. Source-read failure shows an inline retry
message, invalidates data reuse and preserves separately fresh account values. Recovery
never starts a download/trade. Cancelling a quiet audit clears its attempted-key marker
so later checks can run again. Genuine account/network failures still mark values stale;
401 still requires authentication. No transport mutation retries are enabled.

The browser now offers the same daily stages; see the browser guide. Test/publication
results are recorded in CHANGELOG and implementation-plan. Simulated timeout/recovery
checks remain separate from production biometric and broker acceptance.

## Guided daily Home (Android 1.0.8 / code 9)

Open **Home** after biometric unlock. **Your day, step by step** shows **Access →
Data → Review → Trade**, highlights the current step and skips completed work. The
paper account's exact virtual INR values remain below it. **Setup details & completed
checks** expands access/data/install/mode status and links to recovery and advanced
controls. Strategy uses the same daily card; **Advanced preparation & sources** retains
Nifty 100/500 research, forced refresh, cancellation, separate install and source details.
Research, policy editing, backtests and all other native destinations remain available.

1. **Access:** saved Kite profile verification runs automatically once per unlock/day
   when needed, using the read-only profile endpoint. Verified current access is reused.
   If it fails, the card names the unmet prerequisite. **Continue with Kite** checks
   again and opens secure Zerodha login only when access remains unverified. Login/2FA
   stays in the system browser. Return and unlock: a preparation started from Home
   resumes there. Initial Kite app registration still needs credentials in Broker & data.
2. **Data:** **Prepare & continue** imports a missing catalog, attaches an existing
   download, or downloads missing/current Nifty 50 evidence. Sources, IST date, per-stock
   completed-session coverage and exact job identity are audited automatically. Current
   audited data is reused. Audit evidence is held only in memory and invalidated by a
   changed job/source/policy, IST date or crossing today's reviewed or proposed session close. It is
   not re-audited on every five-second status poll. If neither saved nor proposed calendar
   has a close, reuse is bounded to five server-clock minutes. No phone clock or assumed hours
   establishes freshness. Replacing data still requires Manual; the app offers its mode
   review instead of silently changing mode.
3. **Review:** first policy selection is explicit. The installed policy or last confirmed
   daily policy is reused visibly. A download started/continued here opens this single
   guided review when ready, while Home/Strategy is active. It does not interrupt other
   pages or unsaved edits. Acknowledge the displayed stocks/sources/calendar/eligible
   basis/policy/feed effects and **Confirm and prepare**. Cancelled/failed previews do
   not reopen in a polling loop. A partial guided receipt remains in Review, even if the
   strategy-install phase already succeeded. No review or financial safeguard is inferred.
4. **Trade:** a reviewed setup advances to the connection/readiness step. Connecting
   updates automatically to success/failure. If only reconnection is needed, one connection
   review explains that pending fills/protective exits can resume. No strategy reinstall
   is required. Once fresh server readiness allows it, choose Approval or Automatic here,
   review its effects and confirm. Outside entry hours the actual next reviewed entry and
   remaining checks are shown. Waiting never queues activation for a future time.

Automatic work consists of bounded read-only checks and the preparation already
requested with Continue. It does not bypass biometrics/2FA, choose an unconfigured
policy, acknowledge setup, change modes, place a purchase or retry an uncertain write.
Stale/offline status pauses actions and quiet checks recover automatically. A lost write
response still requires inspection of saved state. Failed source coverage keeps Data
incomplete; broker profile success alone cannot prove history/stream entitlement. Readiness
can change at confirmation and the backend remains authoritative. Background push and
real-order execution remain unavailable. Lock clears private snapshots and audit evidence;
the policy is reused from the server and existing recovery/pairing metadata persists.

Validation/publication for this release is recorded in CHANGELOG and implementation-plan.
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

Offline UI evidence uses invented values in a separate package without Internet permission;
it does not establish production biometric, broker or market-fill acceptance.

## Automatic Nifty 50 and live signal checks

Android **1.0.7 / code 8**, backend **0.20.7**. Home preparation defaults to official
Nifty 50 constituents and guided setup subscribes to the entire supported basket.
The old hard-coded ten-name cuts in both guided setup and the live shortlist are
removed. Constituents come from NSE Indices' fixed official CSV, never a phone-supplied
URL or manually selected ten names. Temporary extra official constituents and outside-
index holdings are retained rather than silently dropped. Feed capacity rises to fit
the basket; financial cash/exposure/position limits remain unchanged.

**Broker & data → Automatic Nifty 50 basket** shows current subscription and reviewed
history counts. **Use / refresh official Nifty 50** fetches the current list automatically
and has one overall confirmation. It requires Manual, a disconnected feed, a complete
catalog and no pending orders. The server rechecks the desk revision after fetching.
A missing catalog member or unsupported class stops the change. Advanced custom feed
subscriptions remain available, explicitly ending automatic-basket following.

**Trade → Automatic stock coverage** shows every monitored member and how many have
usable reviewed history. The active discovery view is scoped to the basket. A member
with corporate-action exclusions, missing history or failed screening remains visible;
it cannot be forced into execution. Existing broader reviewed history can supply covered
members during migration without fabricating missing data. Future daily preparation
uses the Nifty 50 source by default; Nifty 100/500 remain optional broader research.
All source/calendar/basis/policy reviews and explicit mode confirmation remain.

Production intraday analysis now warms indicators in one bounded background history
reader while using completed live-feed candles for new signals. It can warm read-only
state in Manual. A history request or 50-stock batch cannot delay the new-candle path.
Warm-up has entries disabled, never replays old buys and requires complete contiguous
coverage. A gap, reconnect partial bar or invalid source triggers resynchronization;
failed/incomplete history retries after a bounded delay. The original five-second
candle/quote checks, current clock/revision/session checks and risk limits still apply.
**Latest strategy checks** shows readiness counts and per-stock plain waiting/filter
explanations. Lack of a signal still does not guarantee a later purchase.

If setup fails, keep Manual and inspect the displayed source/catalog/pending-order
reason. A network/persistence result marked unknown requires inspection before retry.
Do not edit SQLite or erase holdings to fit a basket. A successfully saved source scope
survives backend restart; pairing and saved broker credentials are retained, while mode
and feed authority follow the existing restart and daily re-arming rules.

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

## Trade tells you what is pending

Android **1.0.6 / code 7**, backend **0.20.6**. Open **Trade**: its mode card explains
the current readiness and next reviewed entry start. **Your next step** lists the
configured entry window, completed checks, remaining reasons, last server-check time
and direct links to Broker & data, strategy preparation or risk/basis reviews.

Approval/Automatic remain tappable when business readiness is blocked. A tap fetches
fresh server state; it does not submit a mode instruction. The **Before choosing
Approval** (or Automatic) dialog explains waiting versus work to do. Before a reviewed
09:15 open and configured 09:30 entry start, for example, it names the 09:30 start and
fresh-quote wait. It does not ask for another login/download just to clear a time check.
Special sessions use the intersection of reviewed hours and configured entry times;
after cutoff it uses the next reviewed date. It does not invent tomorrow's session.
Missing calendar coverage points to review rather than assuming a normal trading day.

The summary/dialog updates with quiet polls while unlocked. Once blockers clear it
offers **Review Approval mode**; choose it, review/acknowledge effects and **Confirm**.
Waiting or dismissing a dialog never arms a mode. The mode endpoint rechecks all gates
and the revision. If readiness changes during confirmation, the app shows the new
explanation without retrying the rejected instruction. Network failure/stale status or
an uncertain prior action prevents confirmation; inspect the saved result if requested.
Manual remains available through its own explicit confirmation.

Older backends show their existing failed-check details without inventing timing.
Current next-entry times come from reviewed server sessions and configured windows,
not the phone clock or an assumed exchange schedule. A predicted start is informational:
fresh usable quotes and every other check must still clear. No guaranteed proposal/fill,
real execution, background push or automatic future activation is introduced.

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

## Branding, startup and quiet status updates — 1.0.5

The launcher, native light splash and biometric lock page share the chosen wordless
blue/teal logo. **Agentic Trader** is the app name. Android's native splash transitions
into the lock page with a short fade (or immediately when system animations are off).
It introduces no artificial wait or network dependency. Pairing, fingerprint policy,
secure screenshots and automatic locking are unchanged.

After unlocking, **Opening your workspace** remains until the complete initial read
arrives. Empty cash/portfolio values are not presented as an account. If loading fails,
the error is visible; retry with **Refresh displayed status** or lock the app.

Unlocked pages check status about every five seconds. Background GETs do not show a
loading bar, disable controls or shift content. Desk/setup/page data are staged and
published together after successful reads; unchanged JSON objects retain their identity.
A failed read preserves the previous complete snapshot and marks it stale. An explicit
refresh or foreground action can replace a quiet read; late/cancelled responses cannot
replace the newer state. Reviews, unsaved-navigation dialogs and environment selection
pause polling. Foreground requests retain visible progress in a fixed-height slot.
Refreshes are read-only: failed financial instructions are never automatically repeated.

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

## Paper and Real environments

Tap the **Paper** chip below any page title. **Paper · active** means virtual funds and
simulated execution, with real market data when configured. **Real · unavailable**
remains visibly disabled: this server lacks real-order execution and broker-account
reconciliation. **Done** or selecting the already-active Paper closes the dialog;
no account setting, balance, holding, session or Manual/Approval/Automatic mode changes.
Those modes govern decisions within Paper and cannot turn virtual funds into real ones.

The server's authenticated `GET /api/trading-environment` publishes these capabilities;
there is no switching/write route. An older server without this route remains Paper
only, provided its desk explicitly identifies a paper account. An unexpected non-paper
account is rejected, old data marked stale and account actions blocked. This release
cannot enable Real even if a future server offers it; a separately reviewed implementation
would be required. The browser remains paper-only.

Native Kotlin/Jetpack Compose app **1.0.7**, companion backend **0.20.7**.
It connects to `https://shanmukhan.com/agentic-trader`, uses the same paper account
and server safeguards as the browser, and presents every screen in light mode.

**Actual device installation — 28 October 2026:** signed production 1.0.0 was
installed on the user's connected **Moto g52, Android 13 / API 33**. Android Package
Manager confirmed version code 1 and installation; cold launch succeeded and the
app remained running. Pairing, hardware biometric unlock, broker login and app-update
acceptance are still pending. No credential or account action was supplied by this check.

Subsequently, user-authorized pairing and biometric encryption/unlock were observed.
Signed **1.0.2 / code 3** updated the same phone in place and retained its encrypted
pairing. An exact-source, credential-free device test verified idle reads and safe
UI-thread cancellation/cleanup; its temporary package was removed. Actual 1.0.2
biometric login loaded the account without a network/auth error; later idle locking
hid private values. Actual broker callback/profile success was verified on 29 October
2026; history/streaming entitlement and changed-enrollment behavior remain unverified. Rotating the owner token later requires re-pairing.

## Install and pair once

The launcher uses the supplied wordless blue/teal growth icon, selected for small-size
readability. Version 1.0.3 adds adaptive/round launcher resources and density-specific
PNGs. The foreground is inset to protect the arrow under Android launcher masks;
notifications retain a separate transparent white glyph. No app economics or login
policy changes. Signed in-place updates preserve your existing encrypted pairing.
Actual Moto g52 update to 1.0.3 / code 4 and cold launch were verified; authenticated
controls remained available without a network/auth error. The public installer and
backend 0.20.3 hashes match the signed build. The supplied artwork remains full color;
a themed monochrome launcher variant is not provided.

To regenerate the packaged image sizes on macOS:

```sh
.venv/bin/python scripts/build_android_icons.py \
  --source "images/Futuristic Fintech Growth Icon.png"
```

This requires macOS `sips` and a square PNG at least 432 pixels wide. It produces
five legacy launcher sizes (48–192 px) and five adaptive foreground sizes (108–432 px)
without changing the supplied source. Adaptive XML provides the navy background and
padding. Invalid/missing input fails before replacing generated files; no network is
used. Generated resources are included as source assets for builds on other operating systems.

1. On Android, open <https://shanmukhan.com/agentic-trader/android>. Download the
   signed production APK and use Android's installer. If Android asks, allow this
   browser to install this APK, then turn that permission off again. Distribution
   is direct, not through Play.
2. Set up a screen lock and a strong fingerprint or supported Class 3 face biometric.
   Android **11+** and hardware-backed biometric key authorization are required.
   Unsupported or unenrolled phones are refused before enrollment is sent.
3. Open Agentic Trader. Enter a recognizable phone name and the **server operator
   token once**, select **Pair and protect this phone**, then authenticate.
   Use the Pi's token, not an independent local token. The owner token is not saved.
4. Later, choose **Unlock with biometrics**. Android keeps biometric data; the app
   receives cryptographic authorization, not a fingerprint. No shared PIN fallback
   is provided. Reinstallation, app-data deletion, screen-lock reset or changed
   biometric enrollment can require pairing again.

Browser access remains available with password-manager autofill, username `operator`.
The native app avoids repeatedly typing that long token.

## Daily routine

**1.0.4 saved-history reuse:** **Check & prepare today** and Home's preparation
action request `/api/operations?audit=true`. Lightweight status intentionally omits
source validation; earlier Android releases mistook that omission for stale data and
downloaded again. The explicit audit checks saved source hashes, current IST date
and every eligible stock's completed-session coverage. Valid data is reused only
for the requested universe and the same ready/installed job still present after
the audit. The visible message includes its download time and **No daily candles
were downloaded**. Repeated taps do not fetch candles again; no five-minute expiry
or other arbitrary cache timer is used.

Another download remains appropriate for a different universe, a new IST date,
newly completed sessions not covered by the data, missing/changed/invalid sources,
or the explicit **Download fresh sources & history** action. That explicit action
skips reuse. An already-running download is shown rather than duplicated. If the
saved job changes during validation, recheck it; the app does not overwrite it
automatically. Failed HTTP requests stop the action; a completed audit reporting
stale, missing or invalid evidence causes fresh acquisition. Broker profile/catalog
checks and all source/calendar/policy confirmations
remain separate. Reusing history does not activate a strategy or trading mode.

**1.0.2 background locking:** cancelling a call or closing a pooled TLS socket can
send network records, so cleanup runs on a dedicated background worker. Lock still
clears the token/private UI immediately. The old HTTP client is retired and replaced
before cleanup, protecting a new unlock from late cancellation. This fixes the actual
Moto `NetworkOnMainThreadException` observed when backgrounding earlier releases.
No TLS/StrictMode safeguards are disabled and no financial request is retried.

**1.0.1 connection recovery:** the client retires idle sockets after one second,
before this deployment's upstream idle close. This prevents the reproduced
`unexpected end of stream` after waiting at the biometric prompt or between status
refreshes. Automatic request retries remain disabled, including all financial writes.
Once the encrypted credential is saved, the UI retains paired state even if obtaining
a session fails: unlock again rather than re-enrolling. Existing 1.0.0 installations
can update in place with the same signing identity and keep their pairing. Do not
uninstall or clear app data. If the older form shows an unknown result after biometric
enrollment, reopen it and use Unlock when available; inspect server devices before
attempting fresh enrollment. Owner-token rotation deliberately invalidates pairings.

Choose **Prepare today's account** on Home. The app checks the saved Kite profile,
imports a missing NSE catalog and starts completed daily-history acquisition. When
login is needed, it opens Zerodha in the system browser. Finish login/2FA, return
and unlock; the app checks the callback result and resumes preparation. Progress
and connection status update automatically while unlocked.

Today's evidence is reused only when server hashes, IST date and coverage are valid.
**Download fresh sources & history** explicitly starts a new download. Failed
entitlement, source and network checks stay visible. Profile success alone does not
prove history entitlement. If an expired session has a requested feed, review the
disconnect first: existing fills and protective exits can depend on that feed.

Choose a decision policy explicitly, then **Review and finish setup**. Inspect the
actual stocks, sources, calendar and basis reviews; acknowledge and confirm. This
installs the reviewed selection and requests data while retaining **Manual** mode.
Choose Approval/Automatic separately when readiness permits it. Login, downloads and
saved drafts never activate a trading mode. Zerodha 2FA and factual reviews remain
explicit user actions.

## Native coverage

Use the five bottom tabs; **More** opens the other destinations. No WebView embeds
the browser. Details use native disclosures, selectable values and pagination.

| Screen | Available workflow |
|---|---|
| Home | Exact cash/equity/P&L, preparation, quote/readiness checks, pending proposals |
| Discover | Saved-universe search, eligibility/watchlist filters, ranked evidence/exclusions |
| Stock analysis | Native candles, volume, seven overlays, fifteen indicator series, exact accessible candle history, minute/5-minute/daily/weekly/monthly selection and coverage/benchmark/fundamentals information |
| Your strategy | Prerequisites, preparation progress/cancel/retry, guided confirmation, advanced installation/source/calendar reviews and shortlist application |
| Paper trading | Reviewed Manual/Approval/Automatic changes, proposal deadlines, preview/approve/reject |
| Portfolio | Holdings/basis, exact values, stale/missing marks, allocation and commitments |
| Purchases & SIP | Exact server purchase previews, confirmation, orders/lots, explicit-date SIP creation, due-occurrence previews, plan/pending-buy cancellation |
| Trade history | Side filter, older pages, individual order fills and fill pagination |
| Investment policies | All server-defined fields, unresolved blanks, exact decimals, immutable preview/save/inspect/copy, unsaved-edit navigation protection |
| Backtesting | Registered resources/capability, reviewed launch/cancel, jobs/reports/comparison and original-request recovery |
| Risk & safeguards | Kill/entry controls, queued exits/reset, long-term basis review/quarantine/exit and bound-controller arm/disarm |
| Broker & data | Credentials, session check, system-browser login/fallback exchange, catalog/subscriptions/held coverage/calendar, connect/disconnect and automatic status |
| Settings / Security / Learning | Light UI, versions, read-only economics, optional alerts, paired-phone revocation, searchable help and source references |

Financial sizing and validation stay on the server. Money uses exact decimal
display; unavailable values remain unavailable. Charts never reseed server indicators.
Backtesting requires registered validated inputs and supported OS isolation. The
existing RPi can report its runner unavailable; the app shows the reason. Arbitrary
server-local bundle registration, offline corporate-action processing and investment
engine milestones retain the existing server/browser limitations.

## Security and recovery

- A random revocable phone credential is encrypted with AES-256-GCM. Its Android
  Keystore key requires a fresh strong-biometric cryptographic operation, with
  TEE/StrongBox residency and hardware authentication enforcement checked. Owner
  tokens, decrypted credentials and account snapshots are not intentionally persisted
  in preferences. Recovery storage contains only state/opaque IDs and research
  resource hashes/request keys.
- Production fixes the HTTPS origin, prohibits cleartext/redirects, trusts system
  CAs, disables backup/device transfer/screenshots/recents, rejects obscured touches
  and has no analytics or embedded browser. No remote attestation or certificate
  pinning is claimed. A compromised/rooted unlocked phone remains a risk.
- Backgrounding or two idle minutes locks access. API sessions last fifteen minutes
  and live in memory. Lock clears private state, cancels reads and attempts logout
  without waiting; offline/process-death sessions expire on the server. A server
  restart also clears sessions. Lock does not stop the server or undo accepted actions.
- Consequential requests have no automatic network retry. A durable inspection marker
  is written before sending. Timeout/background cancellation/process loss can mean
  the server completed it. Unlock, inspect the indicated saved outcome, wait for a
  current read, then acknowledge inspection before creating another instruction.
  Backtest retries explicitly reuse the original key. A known saved policy hash
  resolves an uncertain save without another draft. Reviews freeze values and require
  acknowledgement; server revisions, hashes and request identities remain enforced.
- Stale/incomplete account responses disable actions until a successful read.
  Cancelling pairing after enrollment can leave a registration: inspect/revoke it
  with owner authorization before repeated attempts. Eight active phones are allowed.
  Revoke a lost phone using Security and temporary owner authorization. Rotating the
  owner token invalidates all pairings. A storage failure reports uncertain revocation
  persistence; retry with owner authorization before restarting the server.
- Broker callbacks are five-minute, nonce-bound, phone-bound and exchanged once.
  Callback HTML contains no token and removes the query from browser history. The
  app can exchange a one-time request token for its original attempt if needed.
- Optional proposal notifications request Android permission only when enabled.
  Content is generic, hidden on the lock screen and cleared on locking. Alerts run
  only while unlocked: **no background push service or guaranteed deadline alert**.

Keep Android updated and revoke lost phones promptly. A stolen decrypted phone
credential can be replayed until revocation. These protections are not a security
certification. Moto installation/update and initial positive biometric access were
observed; enrollment changes and broker acceptance still require separate checking.

## Build and deploy

Use JDK 21, Android SDK platform 37 and build tools 36.1.0. Minimum runtime API 30.
The Gradle 9.7.0 wrapper includes its official distribution SHA-256; AGP 9.4.1,
Kotlin 2.2.10 and Compose BOM 2026.09.00 are pinned. Dependency checksum metadata
is retained in `android/gradle/verification-metadata.xml`.

```sh
.venv/bin/python scripts/build_android.py \
  --java-home /Library/Java/JavaVirtualMachines/jdk-21.jdk/Contents/Home
```

First build creates owner-only `android/.signing/release.p12` and `identity.json`.
**Back up that entire directory privately**. Updates need the same identity and
an increased app `versionCode`. Losing the key prevents compatible updates. Signing
files are excluded from Git, deployment and downloads; never publish them.
`--gradle PATH`, `--sdk PATH`, `--output PATH` select explicit local tools.

The script builds a minified production APK, verifies its v3 signature/certificate
and manifest (package, debugging/backup/cleartext disabled, permission allowlist),
and writes `dist/android/agentic-trader.apk`, `android-release.json` and
`build-validation.json`. Metadata contains only public hashes and validation status.

```sh
cd android
./gradlew :app:lintProductionRelease :app:testProductionDebugUnitTest \
  :app:assembleDemoDebug :app:assembleDemoDebugAndroidTest \
  :app:assembleProductionDebug :app:assembleProductionDebugAndroidTest
```

Run instrumentation only on an explicitly selected isolated emulator. The demo has
invented data, a separate package and **no Internet permission**. Production negative
tests launch locked and check secure-window/unsupported-biometric refusal without
credentials. Neither proves positive handset biometrics or broker entitlement.
See [test evidence](test-plan.md) and [API implementation](mobile-api.md).

```sh
bash deployment/rpi/deploy.sh lipi@192.168.1.13 --trader-only \
  --android-apk dist/android/agentic-trader.apk
```

The versioned backend bundles only the fixed APK/metadata filenames. Verify `/health`,
`/api/mobile/release`, `/android` and the downloaded APK hash. Corrupt installer bytes
return 503; missing metadata/downloads return 404 and the installation page explains
unavailability. Include the APK in later backend deployments to retain its download.
The previous backend remains available for code rollback; never automatically restore
financial databases.

References: [Android biometrics](https://developer.android.com/identity/sign-in/biometric-auth),
[Keystore](https://developer.android.com/privacy-and-security/keystore),
[APK signing](https://developer.android.com/studio/publish/app-signing).

## Successful Zerodha sign-in and the empty fallback field

**Zerodha sign-in completed but the token field is empty:** the automatic callback
exchanges and stores the access token on the Pi; the app never fills the manual
one-time request-token fallback with saved credentials. Return to the app and unlock.
A verified Kite-session status means no token copying is needed. The fallback is only
for an incomplete callback started by this app. If verification is needed, use
**Check saved broker session**; if it fails, begin a fresh **Sign in to Zerodha**.
Market-data connection/readiness and history entitlement remain separate checks.
