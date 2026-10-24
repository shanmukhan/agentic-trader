# Daily operator checklist and strategy-data explanation

Checked against the current repository on **23 October 2026**. All times below are
**IST**. This guide covers the existing local **paper** application, especially the
long-term account opened by `./scripts/start_ui.sh`. Check the account's horizon and
configuration: a separate intraday account has different closing and warmup rules.
Nothing here enables real broker orders or establishes strategy profitability.

Optional [operations automation](operations-automation.md) now covers independent
local monitoring, daily reports, scheduled data acquisition and stopped-account
artifact backups/drills. Start `./scripts/start_operations.sh` for observation; the
guide explains explicit acquisition opt-in. It does not perform human reviews or
activate trading. Use its `operations-backup` command when you need a verified
artifact package that preserves pending orders without the recovery side effects
of the older `verify-db`/`backup` sequence below.

## 1. Do I need to download strategy data freshly every day?

**For the normal Strategies → reviewed strategy → Approval/Automatic workflow, run a
fresh download on each trading day you intend to use it.** Do it on that day's IST
date, after renewing broker access if necessary, and before reviewing/activating the
strategy. An opted-in operations supervisor can start that download for you. There
is still no unattended installation or incremental update of an installed download.

There are two separate reasons:

- After another session completes, the saved daily-price history no longer contains
  the latest completed session needed for the current screen. Receiving live quotes
  does not append daily candles to this saved bundle.
- The combined **Review and finish setup** / **Review today’s setup** flow requires
  source snapshots downloaded on the **current IST date**, even if the last completed
  price candle is unchanged after a weekend or holiday. Long-term execution also needs
  today's explicit action/price-basis reviews.

You do **not** need to download again every few minutes. Reuse a successful same-day
run while its source/history evidence remains valid. Download again if a new session
has completed, evidence changed, or the app reports that fresh history is required.
If the market closes while a morning download's review is still open, that review
may require a new download containing the newly completed day.

**Yesterday evening's download is useful for inspection, but it cannot be used for
tomorrow's combined confirmation.** The IST date check requires tomorrow's sources.
A morning run uses the previous completed trading session; today's unfinished candle
is excluded. On the next trading morning after a weekend, prices may still end on
Friday, but current-day source checks and reviews are still needed. Always use the
actual reviewed calendar rather than assuming these example weekdays are open.

You can skip broad strategy preparation when only reading saved reports/charts or
using the separate explicit manual purchase workflow. Existing holdings remain saved
without a new strategy download. However, supervising long-term holdings with accepted
current quotes still requires a valid broker/feed, reviewed session and current-day
price-basis reviews. A download is not a substitute for those controls. A separately
managed reviewed profile follows its own coverage requirements; this guide describes
the built-in preparation flow.

### What exactly is “strategy data”?

It is a saved research input bundle, not a new strategy program or a trained model.

| Part | Where it comes from | Why the app needs it |
|---|---|---|
| Current Nifty 100 or Nifty 500 constituents | Official NSE Indices CSV | Defines the broad stock universe to examine, with symbols and share identifiers. It is a current snapshot, not proof of past membership. |
| Proposed exchange-session calendar | NSE capital-market holiday response, with normal hours proposed by the app | Determines expected completed sessions and proposes dates for your review. Special notices still need human checking. |
| Corporate-action source snapshot | NSE equity corporate-action response | Excludes stocks with any returned action in the historical interval through the download date, avoiding unreviewed raw-price comparisons. It does not apply splits, dividends or other adjustments to holdings. |
| Completed daily OHLCV | Kite historical API for eligible, catalog-matched shares | Supplies each day's open, high, low, close and traded volume for screening. A daily candle summarizes one completed session. |
| Provenance and generated setup artifacts | Local preparation worker and your later confirmation | Retains hashes, exclusions, dates and, after installation, the reviewed data/profile/calendar needed to reproduce the selected setup. |

The downloader takes **up to 60 completed sessions**, drawn from at most 120 calendar
days in the current year. It needs at least 51 prior session proposals in that year;
early-year/cross-year preparation may therefore fail and need the separately reviewed
bundle workflow in [strategy preparation](strategy-preparation.md). Missing sessions
exclude a stock; the app does not invent prices. Official files can contain temporary
extra constituents, and classification/action/history exclusions reduce the usable set.

The daily rules screen checks 20-session momentum, a 50-session trend, average daily
turnover and volatility. The current thresholds are positive momentum, at least
₹1 crore average daily turnover and at most 5% daily volatility. Qualifying stocks
are ranked by observed historical gross return, with deterministic symbol ties.
Ranking is not a forecast. The execution shortlist is limited to **ten symbols** and
must retain all held symbols; account risk limits can permit fewer actual positions.

These are separate things you will see in the interface:

| Item | Meaning | How it becomes current |
|---|---|---|
| Instrument catalog | Lookup from stock names to broker tokens/tick sizes | Import initially; update when missing or changed mappings require it. It is not price history. |
| Saved feed subscriptions | At most ten selected instruments receiving streamed quotes | Explicitly apply a reviewed shortlist or save a manually reviewed selection. |
| Strategy-data download | Broad-universe completed daily prices and source evidence | Start a new preparation run; it does not update itself. |
| Installed strategy profile | Reviewed rules/policy bound to saved data and calendar | Explicitly confirm setup. Downloading alone does not install it. |
| Live feed | Current quotes and available bid/ask depth for selected instruments | Explicitly connect with valid broker access and await usable quotes. A socket can be connected with unusable data. |
| Price-basis review | Your current-session check that raw prices can be compared safely across corporate actions | Explicitly confirm eligible reviews in combined setup, or review each remaining symbol in Risk Management. |
| ML model | Separately trained and independently validated compatible artifact | Separate research/validation workflow. A strategy download neither trains nor refreshes a model. |
| Investment policy draft | Saved months/years planning choices under Strategies | Optional planning; a saved draft does not install or execute a strategy. |

The download itself changes no live subscriptions, trading mode, cash, holdings or
orders. Files are private under `<account database stem>.analysis/<run id>/`;
`active.json` identifies the installed run. Opening Stock Analysis reads saved candles
and does not fetch new broker history. The built-in 60-session bundle is insufficient
for SMA200 and many longer weekly/monthly indicators; their warmup states are expected.

## 2. What is one-time, daily, or conditional?

| Task | Frequency |
|---|---|
| Install Python/dependencies; configure operator token; register Kite app/callback; save app credentials; create the intended account | Initial setup, then only when intentionally changing it. See [how to use](how-to-use.md) and [broker setup](ui-setup.md). |
| Start/check the owning service, unlock, inspect holdings/orders/risk and today's market notices | Each operating day. Start only if the service is not already running. |
| Check the saved broker session; renew expired access with normal login/2FA | Check daily; renew when invalid/expired, normally each new trading morning. |
| Import instrument catalog or manually edit subscriptions | Initial setup or when required by missing/changed mappings or an intentional selection change. No need to resave unchanged subscriptions just to connect. |
| Download/review/install current strategy data and inspect shortlist | Each trading day using the normal guided strategy workflow. Reuse valid same-day work. |
| Confirm calendar entries | When dates are missing or need supported review; already reviewed unchanged dates persist. Combined setup can include the proposed calendar. |
| Long-term action/price-basis review | Each current session for selected/held supported symbols; include intervening offline days. Combined setup includes only the eligible symbols it lists. |
| Feed connection and mode activation | Explicitly when required; after restart/pause inspect and reactivate only when ready. |
| Review trade proposals | Per proposal in Approval mode; Automatic has no per-trade approval. Manual purchases/SIP occurrences remain explicit. |
| Monitor fills/risk and close-day state; preserve evidence/backup | Each day you operate, with backup/report commands after stopping ownership as described below. |
| Retrain ML, run backtests, edit investment policy drafts, create a new account or reset capital | Separate deliberate work, not routine daily setup. |

## 3. Before the session: follow these steps in order

### Step 1 — Open the intended account and keep its server available

**Do:** From the repository root, run:

```sh
./scripts/start_ui.sh
```

The launcher loads the private environment and opens an existing matching server or
starts one. Its default uses `config/first-paper-session.toml` when present unless
your configuration overrides that choice. You can select a particular account:

```sh
./scripts/start_ui.sh config/first-paper-session.toml
```

For the existing first-session account, open
<http://127.0.0.1:8004/workspace>. Other configs can use other ports. Keep the owning
terminal running and the computer awake with working internet and an accurate clock.

**Why:** Quotes, protection and paper fills run in the server process. The chat and
browser are not a background trading service.

**Check:** The intended account/horizon opens. If a version mismatch requires a
restart, inspect current exposure, stop the owning terminal with Ctrl+C, let it shut
down, then launch again. Do not start two owners or delete an account lock. Restart
retains holdings but cancels unfilled recovery residue and restores the normal desk
in Manual; it does not complete any pending sale.

### Step 2 — Unlock and inspect yesterday's actual state

**Do:** Unlock with your local `TRADING_OPERATOR_TOKEN`. Read Dashboard, Portfolio,
Paper Trading, Trade History and Risk Management. Check held quantities, pending or
partially filled orders, available/reserved cash, fees, stale valuations, quarantine,
kill/account faults and any outstanding protective exits. Record unresolved items.

**Why:** The previous session may have ended with partial fills or an outage. An order
request and a completed fill have different financial consequences. New setup cannot
erase those obligations.

**Check:** You understand each remaining holding/order and any cash reservation.
Available cash excludes pending entry reservations; virtual equity includes estimated
liquidation costs and can be stale. Never interpret yesterday's price as a current
executable value. Leave entries blocked while investigating an unexplained mismatch.

### Step 3 — Read today's exchange notices and confirm the date

**Do:** Check the official links shown by the app for holidays, special sessions and
corporate actions. Decide whether today is actually a supported trading session.
Review intervening dates since the last accepted quote, including weekends/outages.

**Why:** A weekday and default hours do not prove the exchange is open. An action can
change a stock's raw-price basis even while your computer is offline.

**Check:** Today's session and source references are understood. The app's normal
session proposal is 09:15–15:30 and the current account's ordinary entry window is
09:30–14:30, with earlier-close restrictions. Follow displayed configured hours.
Unsupported evening/special hours cannot be enabled by entering invented normal hours.
On a closed day, stop at research/account maintenance; do not activate entries.

### Step 4 — Select Manual while preparing the day

**Do:** In Paper Trading, choose **Manual** if another mode is selected. Read current
pending work; resolve pending orders through their supported controls/status before
confirming setup. Manual cancels pending strategy proposals but does not imply every
existing order has disappeared.

**Why:** Installation and shortlist changes require Manual and no pending orders.
Manual stops strategy-generated discretionary orders while protective exits remain
independent. It is not an instruction to sell every holding.

**Check:** The current mode is Manual. Any open-position protective handling is still
understood. Do not reset a kill or discard state merely to make setup pass.

### Step 5 — Check the broker session; log in again if required

**Do:** Open **Broker & Data → step 3 → Check saved broker session**. If valid, continue.
If expired/invalid, first disconnect a requested feed in step 6, then open Zerodha
login, complete normal login/2FA, return to the originating setup page and select
**Exchange and verify session** promptly. If popup capture fails, follow the labeled
manual request-token path in [broker setup](ui-setup.md).

**Why:** Broker authentication expires independently from the local dashboard unlock.
Kite documents next-day 6 AM access-token expiry, with earlier invalidation possible.
The request token is short-lived and single-use. See the
[official authentication documentation](https://kite.trade/docs/connect/v3/user/).

**Check:** A new successful check/exchange result appears. The running manual service
saves the access token privately; routine UI renewal needs no `.env` copy or restart.
A valid profile does not prove historical-data or streaming entitlement. For a network
timeout, check connectivity and retry the read; for an uncertain exchange, refresh
status first and use a fresh login if another exchange is necessary. Keep the local
operator token, request token and broker access token in their distinct labeled uses.

### Step 6 — Check the catalog and preserve subscriptions for holdings

**Do:** In **Broker & Data → step 4**, inspect the imported catalog and **Saved feed
subscriptions**. Import/validate the catalog if absent or required to resolve current
instruments. Check that every held symbol remains monitored. Do not manually replace
the list if you are about to use the combined ranked-shortlist setup.

**Why:** Historical/streaming reads need actual broker instrument mappings. Removing
a held stock would remove its quote/protection coverage.

**Check:** Required symbols resolve to the correct supported shares. An EQ catalog
row alone is insufficient equity-share classification; ETF-specific accounting remains
unsupported. Missing mappings need correction, not invented tokens. Catalog/import
conflicts and unsupported held assets need investigation before mode activation.

### Step 7 — Download today's strategy bundle

**Do:** Open **Strategies → Prepare a paper strategy**. Choose **Nifty 100** or
**Nifty 500**, then confirm **Download strategy data**. Allow time before the entry
window: historical requests are paced at least 400 ms apart, so broad runs can take
minutes. Keep the server running and inspect progress, source dates and exclusions.

If the opted-in supervisor already acquired valid current-day data, inspect and
reuse that run instead of starting another. Failed/unknown scheduled attempts need
status inspection before an explicitly requested new download.

**Why:** This obtains the completed-price history and current source evidence used
by the screen and today's guided review. Live quotes do not refresh this bundle.

**Check:** The run reaches **Ready for review** / **Review required**, has today's
IST snapshot date and covers the latest completed reviewed session. Examine exclusions
rather than assuming every index constituent is usable. A stock with an action in
the downloaded interval is conservatively excluded, not automatically adjusted.
On failure, resolve the stated source/access/history problem before starting a new run.
Cancel takes effect after the current bounded network operation. Closing the browser
does not cancel; restart marks unfinished work Interrupted and never resumes it.

### Step 8 — Preview the policy, calendar and exact shortlist

**Do:** Choose **Rules only** or **Rules + independently validated ML** explicitly for
first setup. With a valid installed policy, **Review today’s setup** can reuse it.
Select **Review and finish setup** (or that Dashboard shortcut) to open the summary.

Read every part: policy, history coverage, official sources, all proposed dates/hours,
saved-calendar differences, exact proposed execution symbols, retained holdings,
virtual cash, current-day basis reviews included and symbols left for manual review.

**Why:** The download is evidence, not authorization. You are approving a specific
policy/calendar/list and source review. A broader universe is not a promise of more
profitable trades. Current rules-only is an experimental paper hypothesis; ML requires
a separately validated matching model and never silently falls back to rules.

**Check:** The summary matches your intended account and reviewed notices. If no
candidate qualifies, accept a no-entry day. If hours need edits, use **Advanced: edit
dates and install separately** in [strategy preparation](strategy-preparation.md);
editing the advanced form alone does not change the combined summary. Additional
sessions need complete reviewed inputs. Used calendar definitions cannot be casually
overwritten. A policy draft elsewhere in Strategies is not the installed strategy.

### Step 9 — Explicitly confirm and prepare

**Do:** Once satisfied, check the initially unchecked acknowledgement and select
**Confirm and prepare** within the summary's two-minute validity period. If it expires
or relevant account/source state changes, get a new summary and read it again.

**Why:** This is the explicit authorization boundary for the displayed setup changes.

**Check:** The combined flow disconnects the feed, installs the reviewed immutable
data/profile/calendar if needed, applies the exact shortlist retaining holdings,
saves only listed eligible current-day long-term reviews, and requests reconnection.
**It leaves Manual selected.** Reconnection can resume independent protective exits.
Do not separately reapply a shortlist/review already completed by this confirmation.

If a phase fails, earlier saved phases can remain applied. Read status/activity,
correct the reported issue and obtain a fresh review; there is no automatic rollback.
After a timeout, refresh and inspect before deciding to retry. A restart interrupts
pending setup instead of completing it. No setup response proves an order fill.

### Step 10 — Complete outstanding calendar and price-basis reviews

**Do:** Inspect Paper Trading's remaining blockers and the summary's manual-review
list. For a missing supported session, use **Broker & Data → step 5** to review and
confirm its actual date, hours and source reference. Skip this if the unchanged date
was already correctly installed. For each remaining supported long-term symbol, use
**Risk Management** to review today's action/price basis with a genuine reference.

**Why:** Calendar review and price-basis review address different risks. Historical
source review, yesterday's review and installation alone do not authorize today's
raw-price acceptance. Held symbols or gaps in prior quote coverage can require
separate attention even after combined setup.

**Check:** Each necessary current-day review is actually saved and the calendar
contains the intended session. If an action occurred or coverage is uncertain, preserve
the quarantine/blocker and use the reviewed offline
[corporate-action workflow](corporate-actions.md). Another no-action review cannot
clear a persistent quarantine. Supported adjustments/receipts need their own evidence
and stopped-service workflow; do not attest clear just to remove a warning.

### Step 11 — Confirm usable live quotes, not just a connected socket

**Do:** If combined setup did not already request a connection, use **Broker & Data →
step 6 → Connect paper market data** and confirm. Then open **Paper Trading → Inspect
quote details** and inspect selected stocks, especially holdings.

**Why:** Simulated execution uses new accepted quotes and available depth. Historical
candles, a connection request and a socket's Connected label cannot fill an order.

**Check:** New post-connection quotes are accepted with correct exchange time, age,
price-basis state and usable bid/ask depth. Reviews can unblock incoming long-term
quotes; wait for a new quote afterward. After hours, a socket with empty depth or old
prices is expected to remain unusable. If blocked, follow the specific basis, stale,
rejected-observation, session or connection explanation rather than repeatedly logging in.

### Step 12 — Choose the intended paper mode when readiness passes

**Do:** Read **Paper Trading → Your next step**, the current market/entry hours and
every remaining blocker. During the supported open entry window, select **Start
approval mode** or **Start automatic paper mode** and confirm if that is your intent.
Otherwise keep Manual for explicit purchases or monitoring.

**Why:** Setup, connection and trade authority are separate. Starting a mode requests
strategy operation subject to independent data/model/cash/fee/risk checks.

**Check:** The displayed mode is actually active, not blocked/paused. Approval requires
your review of each eligible discretionary proposal; Automatic can submit eligible
paper orders without per-trade confirmation. Protective exits do not wait for Approval.
Neither mode promises a trade. Intraday additionally needs complete five-minute bars
and warmup; the default fourteen-bar warmup is no earlier than 10:25 after a 09:15 open.
The current long-term rule uses prior completed daily information and a 20-session
holding limit; a months/years draft does not change that executable rule.

## 4. During the session

### Step 13 — Review proposals or explicit purchase/SIP occurrences

**Do:** In Approval mode, inspect each proposal's symbol, side, quantity, price/risk,
costs, reason and expiry before approving or declining. In Automatic, supervise actual
decisions/orders. In Manual, use **Portfolio → Purchases & SIP** only when you intend
an explicit purchase: preview, inspect server-computed quantity/cost/cash/risk, then
confirm. Review any due SIP occurrence there; a saved SIP plan is not an unattended buy.

**Why:** A ranked candidate or proposal is not ownership. Manual/SIP intent and
Approval decisions require your instruction, then risk approval and later fills.

**Check:** Inspect the resulting intent/order ID, filled quantity, actual debit/fees
and remaining quantity in Trade History/Portfolio. “Accepted” or “queued” does not
mean fully filled. A cancelled proposal labeled **no order created** bought nothing.
An uncertain request needs a status read before any deliberate retry. Cancelled,
expired, declined or submitted daily signals are not replayed by switching to Automatic;
an idle mode can simply have no new eligible signal.

### Step 14 — Supervise freshness, risk, partial fills and pauses

**Do:** Keep checking quote age, feed, positions, pending exits, cash/reservations,
P&L and fault/kill reasons while the paper session runs. Display polling happens
about every three seconds while visible; hidden tabs stop polling. Maintain the
running computer/feed if you expect protection and fills.

**Why:** Automatic mode automates eligible submissions, not source review, recovery or
operator supervision. Stops/targets and emergency requests still need usable quotes
and liquidity. A browser lock does not stop the server or a running strategy.

**Check:** Following a safety pause, the desk returns to Manual and cancels pending
approval authority. Fix the stated problem, inspect outstanding exposure, then
explicitly reactivate only when readiness permits. Restored quotes do not rearm it.
If you intend to block entries, choose Manual/disarm as applicable. If you intend
protective liquidation, use the appropriate holding exit/kill/flatten control and
verify later fills. These actions have different consequences; do not use a kill as
a routine navigation or logout action.

## 5. At the end of the session

### Step 15 — Stop new discretionary activity and reconcile the day

**Do:** Choose Manual when ending discretionary strategy activity, then inspect Trade
History and Portfolio. Record filled and residual quantities, fees, realized/unrealized
values, pending orders, cash reservations, unresolved actions/claims and stale marks.
Confirm whether every intended exit actually filled.

**Why:** The next day must start from persisted financial state. A queued sell is
still exposure, and an unrealized estimate is not received cash.

**Check:** For **long-term**, intentionally retained holdings persist overnight;
there is no ordinary 15:15 forced sale. For **intraday**, the ordinary 15:15 flatten
is an exit request: monitor residual positions and real paper fills before stopping.
Special/early-close cutoffs follow the configured reviewed session. If the market
has closed with an unresolved exit, preserve it and investigate; do not fabricate a
fill or change hours. Overnight long-term holdings have no executable protection
while the service/feed is unavailable, and gaps can exceed intended stops.

### Step 16 — Stop ownership deliberately and preserve reports/backups

**Do:** If shutting down, stop the owning terminal with Ctrl+C and allow cleanup.
Closing or locking the browser alone is insufficient. After ownership stops, use the
**same account config** for evidence and backup commands. For the existing long-term
first-session config, this example uses new output names; replace the date and choose
a new suffix if a destination already exists:

```sh
account_config=config/first-paper-session.toml
.venv/bin/trading-agent --config "$account_config" long-term-report \
  --output data/daily-evidence-YYYY-MM-DD-first
.venv/bin/trading-agent --config "$account_config" verify-db
.venv/bin/trading-agent --config "$account_config" backup \
  backups/paper-YYYY-MM-DD-first.sqlite3
```

If your service uses another config, change `account_config` accordingly. These
commands need the same private environment as the service; unlike the launcher,
direct CLI commands do not source your shell `.env` for you. The documented
[environment loading instructions](how-to-use.md#4-configure-a-paper-account) apply.
For a dedicated automated intraday account, use its own config and the
[paper-report procedure](paper-feed.md), not `long-term-report`.

**Why:** The source-preserving long-term report captures cash, fees, positions and
pending state before owning recovery commands. `verify-db` checks integrity/accounting;
`backup` creates and verifies a consistent SQLite backup including committed WAL data.
Both owning commands can cancel pending order residue during recovery, so report first
when preserving that state matters. Exit latches survive; cancellations are not sales.

**Check:** Read the report and command results; an integrity/accounting failure means
preserve the account and investigate before resuming. Do not overwrite old backups or
copy only the active main SQLite file. Preserve the referenced private config,
calendar, strategy/data/model artifacts as well as the ledger under your backup policy:
the database backup alone is not a full installation backup. See the
[backup/restore runbook](runbook.md#backup-and-restore-rehearsal) for a new-path restore
and encrypted off-device retention. Do not delete downloaded runs referenced by the
active profile. Starting tomorrow does not create a new ₹25,000 account or erase P&L.

## 6. Quick daily checklist

- [ ] Open the correct account; keep its owning server/computer available.
- [ ] Unlock and inspect persisted holdings, orders, cash, fees, faults and exits.
- [ ] Check today's IST exchange notices/session and intervening corporate actions.
- [ ] Select Manual for setup; resolve pending-order blockers.
- [ ] Check broker access; disconnect and complete fresh login/2FA/exchange if expired.
- [ ] Verify catalog mappings and retention of all held feed symbols.
- [ ] For strategy modes, download today's bundle and inspect dates/exclusions.
- [ ] Review the policy, full calendar, exact shortlist and included/manual reviews.
- [ ] Acknowledge and Confirm and prepare; inspect the actual completed phases.
- [ ] Complete remaining supported session and current-day price-basis reviews.
- [ ] Connect if necessary; await new usable quotes and inspect all readiness reasons.
- [ ] Explicitly activate the intended mode in its allowed window, or remain Manual.
- [ ] Review Approval proposals/manual purchases/SIP occurrences when applicable.
- [ ] Supervise actual fills, freshness, exposure, risk and any pause/recovery.
- [ ] End discretionary activity; reconcile fills, holdings, fees and pending exits.
- [ ] Stop ownership deliberately if shutting down; report, verify and back up.

No automatic daily scheduler currently performs this full checklist. Source review,
authentication/2FA, confirmation, exception handling and deliberate mode activation
remain operator responsibilities. Engineering tests and synthetic demos do not certify
real-market returns, broker entitlement, all-day reliability or target-device acceptance.

## References and validation scope

App behavior was cross-checked with `scripts/start_ui.sh`, the preparation/guided
controllers, desk readiness/mode handling and the usage guides linked above. Broker
authentication and candle format were checked against the official
[Kite user API](https://kite.trade/docs/connect/v3/user/) and
[historical-candle API](https://kite.trade/docs/connect/v3/historical/) on 23 October
2026. Exact daily OHLCV coverage and same-day freshness limits described here are
application rules, not a claim that Kite only offers 60 sessions of history.

This is documentation of the implemented workflow. Creating this guide does not run
broker login/downloads, attest reviews, switch modes, place orders or validate a real
operator session. Detailed exceptions remain in [strategy preparation](strategy-preparation.md),
[broker setup](ui-setup.md), [trading desk](trading-desk.md),
[long-term operation](long-term.md) and the [runbook](runbook.md).
