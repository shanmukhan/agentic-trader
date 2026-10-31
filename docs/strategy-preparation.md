# Prepare a genuine-data paper strategy in the UI

## Fast source checks and the browser daily path (0.20.9)

Android and browser daily flows use `GET /api/desk/preparation/audit` for read-only
source/job/date/coverage validation. Full accounting reports are no longer in the normal
daily UI path. Account snapshots, source freshness and trading permission are separate.
A failed source read pauses reuse and retries; it cannot trigger a new download. Exact
current job/universe and all source flags are required to skip downloading. Full audits
and every installation/readiness/risk guard remain available and unchanged.

Browser Dashboard/Strategies now share the four-stage card. Continue imports a missing
catalog, attaches a running Nifty 50 preparation or starts needed evidence acquisition.
With a saved policy, completion opens one explicit guided review; first policy choice
stays explicit. Completed installation skips repeated install steps. Sources, force-
download and separate calendar/install controls remain in collapsed Advanced preparation.
Broker 2FA, source/basis/calendar acknowledgments, feed effects and mode selection are
not automatically approved. A lost write reply blocks follow-through pending inspection.

## Android daily steps (1.0.8)

Home and Your strategy show one guided **Access → Data → Review → Trade** card.
Saved access/current-source checks are automatic. **Prepare & continue** follows an
existing download or prepares current official Nifty 50 history, keeping Home visible.
With a previously selected policy, the combined review opens when the requested download
finishes. First policy choice and every setup acknowledgment remain explicit. A valid
installed setup skips directly to connection/readiness; an incomplete guided receipt
continues to require review. Reconnection does not reinstall the strategy. Manual must
still be reviewed before replacing data. Dates/close boundaries come from the server's
reviewed sessions; after close, newly completed missing history invalidates reuse.

Expand **Advanced preparation & sources** for other research universes, forced fresh
downloads, cancellation, source/exclusion inspection and separate installation. Daily
progress does not override any source/calendar/basis/model/risk gate. Cancelled previews
stay closed until requested again; uncertain writes require saved-outcome inspection.
See [Android daily guide](android-app.md#guided-daily-home-android-108--code-9) for the
complete inputs, expected results and recovery path.

## Automatic Nifty 50 basket — 0.20.7 / Android 1.0.7

Nifty 50 is the default acquisition universe, using
<https://www.niftyindices.com/IndexConstituent/ind_nifty50list.csv>. Constituent count,
unique NSE names, EQ class/ISIN and catalog coverage are checked; the server does not
truncate the list to ten. Guided Nifty 50 setup uses all supported official members
and retains held symbols. Reviewed history controls execution eligibility separately
from monitoring, so action/history exclusions remain explicit. The dataset may contain
members with no eligible bars; those rows show missing data and cannot produce entries.

Nifty 100/500 are still available for broader research. Their shortlist uses reviewed
configured capacity instead of a hard-coded ten; the automatic Nifty 50 path preserves
the full basket even when migrating an old ten-slot configuration. Default capacity is
50, automatically expanded for supported index additions/retained holdings. This does
not change position, capital, spread, loss or exposure limits. Capacity/universe flags
are operational and excluded from the existing financial-policy fingerprint.

Existing same-day source audit/reuse is universe-bound, including Nifty 50. No source,
calendar, policy, corporate-action or price-basis review is inferred from an index name.
A missing catalog member stops automatic setup instead of silently subscribing to 49.
See [phone flow](android-app.md#automatic-nifty-50-and-live-signal-checks).

Android **1.0.4** fixes unnecessary repeats from **Check & prepare today**. It requests
the explicit read-only source audit and reuses a valid same-day, same-universe
ready/installed download, with a visible **No daily candles were downloaded** message.
The job identity is checked again after the audit. New dates/completed-session gaps,
changed/missing evidence, another universe or **Download fresh sources & history**
require fresh acquisition; ongoing downloads are shown rather than duplicated.
There is no five-minute expiry. Review/installation/trading authority remain explicit.
See [Android reuse details](android-app.md#daily-routine).

The [operations supervisor](operations-automation.md) can now acquire this bundle
once per reviewed IST session date with explicit scheduling opt-in. It checks Manual,
account/order/catalog/held-symbol and broker preconditions, deduplicates attempts and
stops at downloaded evidence. It does not install, attest basis/source reviews, connect
the feed or activate a mode. Failed or ambiguous attempts need inspection and an
explicit manual recovery; ordinary preparation controls below remain available.

See the [daily operator checklist](daily-operator-checklist.md) for what strategy
data contains and the complete daily sequence. In the normal guided workflow,
download on the current IST date: yesterday evening's run cannot authorize today's
combined setup, even if no new price session has completed. Reuse valid same-day
data until a newly completed session or changed evidence requires another run.
An installed snapshot remains saved but is not incrementally updated by live quotes.

Version 0.16.0's [research engine](investment-research.md) is separate from this
installation/authority workflow. Preparation still takes the latest **60** completed
sessions from its supported current-year source; it does not acquire 200-session or
multi-year history. SMA200/long weekly-monthly warmup remains unavailable until a
separately reviewed longer daily bundle and full calendar coverage are supplied.
Early-year/cross-year acquisition remains a reliability/data-source gate; the new
engine can analyze explicit reviewed cross-year inputs but does not repair this
acquisition source. No new investment strategy, model or calendar is installed by
viewing research or running `investment-analyze`.

In 0.15.0, **Strategies** retains this preparation workflow; **Paper Trading** now contains mode activation and full readiness. Guided reviews use the shared visible-viewport confirmation, initial Cancel focus and Escape cleanup. Navigation does not approve or start setup.

## Phase 2 future strategy/data contract

[phase-2/strategy-and-data-contracts.md](phase-2/strategy-and-data-contracts.md) separates
existing 20-session behavior from a proposed versioned months-to-years policy and
specifies causal data/indicator/connected-replay acceptance. No existing profile,
preparation input, holding/exit rule, model identity or authority is changed by this
design phase. Proposed investment parameters remain activation blockers until reviewed;
current instructions below continue to apply.


Version **0.14.0**, 22 October 2026. **Strategies** is now a separate sidebar area at
`/strategies` (workspace route `/workspace#strategies`). It uses the existing
preparation and decision controllers: the presentation change does not install a
policy, replace subscriptions or activate a mode. Legacy `/desk#strategy-setup`,
`/desk#execution-shortlist` and `/desk#apply-shortlist` links open the matching
Strategies section. Ordinary `/desk` now displays Dashboard.

This workflow fills the missing data/profile setup
between a connected market-data socket and the Approval/Automatic paper controls.
It does not enable real-money orders or establish profitable expected returns.

## Start here

1. Start the current application from the repository root:

   ```sh
   ./scripts/start_ui.sh
   ```

   For the existing account open <http://127.0.0.1:8004/workspace#strategies>. If an older
   server already owns that port, stop it in its owning terminal with Ctrl+C and run
   the command again. Do not run two copies against the same account. Restart clears
   browser access and mode authority; unlock again with `TRADING_OPERATOR_TOKEN`.
2. In **Broker & Data**, check the saved broker session and import the NSE catalog.
   Expired broker access requires normal login/2FA and request-token exchange. The
   local operator token is different from broker request/access tokens. Your broker
   data plan must actually permit historical candles; profile/socket success alone
   does not prove that entitlement.
3. Choose **Manual** in Paper Trading before preparation. In **Strategies**, open
   **Prepare a paper strategy**. Preparation is available on the manual service with read-only broker setup;
   an existing bound legacy controller retains its original workflow.

Use **Stock Analysis** for [actual saved-candle charts](market-analysis.md),
**Stock Discovery** for saved screening comparison, **Paper Trading** for readiness,
modes and proposals, **Trade History** for orders/fills and **Portfolio** for the
Purchases & SIP link. **Risk Management** retains basis/emergency controls and
**Broker & Data** retains broker administration. Contextual onboarding and the
**Learning Center** checklist link to unfinished setup. Navigation retains access
in memory and never authorizes a setup or financial action.

## Recommended: one combined setup review

For a new day's **LONG_TERM_REVIEW_REQUIRED** warning, Dashboard offers
**Review today’s setup** in the next-step panel, quote details and relevant readiness
cards when the current-day download is ready. It opens this same summary directly,
using your currently installed rules/rules-plus-ML policy if no new policy was chosen.
There is no ML-to-rules fallback and no implicit first-time policy choice. Review the
displayed policy, dates, stock changes and included/manual reviews before acknowledging.
Opening the summary, refreshing or restarting never approves today's price basis.

Stale/missing downloads, active download, non-Manual mode, custom profile overrides and
unavailable guided routes keep the shortcut disabled with preparation/manual guidance.
The UI compares source snapshot and server observation dates in IST; the server still
performs its full date, source, policy and account-binding validation. The shortcut and
warning hide when the blocker clears. Changing workspace sections and returning to
Dashboard reloads the section. Upgrade an older server to 0.14.0 using the command above.

After a same-day download reaches **Ready for review**, choose the decision policy and
select **Review and finish setup**. Already downloaded data can be reused; this action
only previews the setup and saves a private review record. It does not install a profile,
change the feed/configuration, attest a source review, place orders or change money.

The review shows the exact at-most-ten ranked execution symbols, retained held symbols,
policy, history coverage, source links, complete proposed calendar, saved/proposed hours,
entry hours, virtual cash and current-day basis reviews included or left for manual review.
Open the dates/source links and review notices, special sessions and action exclusions.
The displayed normal-hours proposal is not proof of market opening. A source snapshot
is not historical membership evidence, an ML validation or a profit forecast.

Check the single unchecked acknowledgement and select **Confirm and prepare** within
two minutes. This explicitly authorizes the displayed calendar, source/basis and policy
reviews and any shown unused-calendar correction. The server performs these existing
controls in order:

1. Disconnect market data and recheck the account/source/shortlist binding.
2. Install the reviewed immutable strategy/calendar if this run is not already installed.
3. Apply exactly the previewed shortlist, retaining all held symbols.
4. Save only the listed eligible reviews for the **current IST date** on long-term accounts.
5. Request a new market-data connection. A socket request is not usable quote evidence.

No freeform review reference is required: the server generates a reference bound to the
summary hash and retains its private evidence in `<database stem>.analysis/guided.json`.
Historical/source reviews and current execution reviews remain separate records, covered
by the same explicit acknowledgement. Current reviews are eligible only for supported,
source-covered, unheld symbols without quarantine or an uncovered earlier quote basis.
Held positions, quarantines and gaps still require separate Risk Management review. Nothing is attested
for future dates, and the following session requires new current-day reviews.

Setup stays **Manual**. Reconnection can resume independent protective exits on holdings;
review that consequence before confirming. Choose Approval or Automatic separately when
the readiness checks pass. Closed markets, stale/empty depth, entry windows, validated
model age/embargo, cash/fees and risk gates are never relaxed. No deferred activation is
scheduled. Intraday still needs completed five-minute warmup/signals; daily setup alone
does not produce an intraday signal. Long-term uses prior completed daily information.

Pending orders, account/kill faults, unsupported held assets, no qualifying candidates,
used calendar conflicts, stale downloads, changed evidence or a mismatching model stop
the combined flow. Changes to revision, selection, catalog, holdings, cash, order states,
source inputs, calendar or basis reviews invalidate the preview. Ordinary changing quote
prices do not invalidate it; source coverage is checked again before current reviews.
If a daily session closes while the review is open, get fresh completed history first.

A failed step leaves prior saved steps in place and reports the phase. Inspect readiness
and activity, correct the issue and obtain a new summary to continue. No automatic retry
or rollback of account history is attempted. Identical completed confirmation retries
return the saved outcome without another connection or review. A server restart marks
pending reviews/attempts interrupted; it never resumes them. Keep the terminal running.

**Advanced: edit dates and install separately** retains the original CSV, notes, three
review checkboxes and individual controls below. Use it for necessary session edits;
those edits are not used by the combined summary until separately installed. Additional
sessions require complete fresh source data. Do not change hours to allow evening trades.

## Download prerequisites

Before **Download strategy data** can be enabled, its prerequisite panel must show:

- **Kite session: verified today in this server run.** Follow **Verify Kite session →**
  to Broker & Data step 3, then select **Check saved broker session**, or complete login/
  token exchange if required. A saved token, a prior-day check or a pre-restart check
  is insufficient. Verification is explicit; viewing/polling this panel never contacts
  the broker. Server restart requires another saved-session check.
- **NSE catalog: supported instruments available.** Follow **Import NSE catalog →** to
  step 4 and select **Download / validate catalog** if missing. This is a symbol/token
  lookup, not a feed subscription or a history download.

Unknown, failed-to-refresh or missing prerequisite status disables the button and
explains the next action above it. Refreshes restore it only after both requirements
are met. The API enforces the same gate before starting a worker or saving a new run.
A lost response retried with the same request identity still returns its prior outcome.

The worker checks the frozen session again because access can fail after verification.
A profile-check failure revokes that run's verification, blocks retry and displays the
existing failure alert. A newer successful check is retained if an older worker fails.
History entitlement remains separate: even a verified profile can lack historical-data
access. Calendar/source/policy review is still required after a successful download.

## Download, inspect, review

Choose **Nifty 100** for a smaller initial run or **Nifty 500** for broader discovery,
then confirm **Download strategy data**. This selects an official current constituent
universe, not your previously typed five symbols. It neither changes the live feed
selection nor creates proposals, orders, holdings or cash entries.

The background worker:

- Verifies the frozen saved broker read session.
- Reads the fixed official NSE Indices constituent CSV, the NSE capital-market holiday
  list and the NSE equity corporate-action response. Stores source snapshots and hashes.
- Validates distinct equity-series symbols, INE-format ISINs and expected universe bounds;
  requires actual supported NSE catalog tokens. An EQ catalog row alone is insufficient.
  Temporary constituents can exceed the index's named count. Unsupported non-EQ series
  (including REIT/trade-to-trade) and dummy/non-share identifiers are individually excluded
  with reasons. Duplicates/malformed files fail; the supported discovery set cannot exceed
  500. The real Nifty 500 file checked here had 501 rows: 495 supported, six excluded.
- Proposes normal weekday sessions from that year's holiday source and 09:15–15:30
  normal cash-equity hours. These are **unreviewed proposals**, not automatically
  approved market sessions. The operator must check special closures/session notices.
- Selects up to 60 completed sessions from at most 120 calendar days in the current year,
  plus proposed sessions through seven calendar days ahead within that same year.
- Excludes a stock if the action response contains **any action kind** in its full
  historical interval through the download date. Dividends, splits, bonuses, rights and
  other actions are not guessed, parsed into benefits or silently treated as zero.
- Downloads the remaining stocks' completed `day` OHLCV from Kite. Today's unfinished
  candle is excluded. Each eligible stock must cover exactly the expected completed
  sessions; missing/unexpected dates exclude that stock, rather than creating candles.
- Stops on the first provider/history error instead of repeatedly issuing up to 500
  failures. No automatic authentication retry or alternative source/model is used.

Requests use a shared in-process historical-read limiter, spaced at least 400 ms apart,
including concurrent intraday-history reads. Provider quotas across other applications
or multiple server processes are outside this limiter. Discovery/network I/O and broad
screening run outside the broker's quote/risk lock. Network time is separate from local
screen timing; a 500-stock run can take minutes. Progress shows completed reads, eligible
history, source period, elapsed seconds and excluded symbols/reasons.

**Cancel download** requests cancellation after the current bounded network operation.
Closing/locking the browser does not cancel the worker. A server restart marks an
unfinished download Interrupted and does not replay it. Start a new run explicitly.
The browser refreshes status without clearing your edited review form.

## Download failure and retry

A **Download failed — action needed** alert appears immediately below the download
buttons, with a red border, tinted background, reason and recovery instructions. It
is announced as an alert to assistive technology; the small header badge is only a
summary. No active progress bar or “Reading official sources” message remains on
failed/cancelled/interrupted jobs. Partial stock counts and elapsed duration remain
visible. Before stock counts are known, an active download uses indeterminate progress
and says whether it is checking the Kite session or reading official sources.

For **BROKER_SESSION_UNAVAILABLE**, nothing reached official sources or stock history:

1. Follow **Check saved broker session in Broker & Data →** to step 3 (workspace
   destination `#broker/setup-step-3`). Select **Check saved broker session**.
2. Check connectivity and retry verification. A failed profile read alone cannot
   establish that the token expired. If expired, disconnect any requested feed in
   step 6, complete Zerodha login/2FA and exchange a fresh request token in step 3.
3. Return to Strategies, keep Manual selected, choose Nifty 100/500 and confirm
   **Retry strategy data download**. A new confirmed retry creates a new run; repeated
   delivery of the same request returns the saved original outcome.

For a daily-history failure, the same link helps check the saved session; also check
historical-data entitlement. Profile verification or a working stream does not prove
history access. For official-source failures, follow the displayed reason and retry
later; no alternate sources/prices are assumed. Failure and retry do not install a
strategy, change virtual cash, or approve any review. A broker login is never silently
refreshed. Lock hides the alert/private status; unlocking reloads the saved result.

Load updated HTML/JS/CSS by reloading after deployment. The new `broker_session` worker
stage also needs the updated Python service loaded (`./scripts/start_ui.sh` after
stopping the owning local server with Ctrl+C); old failed jobs still display correctly.
A reload cannot repair broker credentials or deploy local source to the Pi.

## Advanced: install the policy separately

After **Review required** appears:

1. Expand **Downloaded sources and stock exclusions**. Check the official constituent,
   holiday/hour and action pages. Download success is not proof those sources cover every
   special notice or instrument basis change. Empty/invalid action data is rejected.
2. Review the entire proposed `date,open,close` CSV. Correct supported hours as needed;
   rows must remain unique and chronological, within 09:15–15:30 IST. Every downloaded
   session must remain represented. Additional/special/missing sessions need fresh complete
   inputs through the existing reviewed-bundle workflow; this form cannot invent their data.
   Normal weekend/holiday/Muhurat trading is never assumed from an absent holiday row.
   If saved hours differ, each date's saved/proposed hours are displayed. A separate,
   initially unchecked correction acknowledgement appears only for an unused account.
   It requires no quotes, candles, orders, fills, positions, pinned long-term reviews,
   action/payment records, portfolio requests, SIP plans or desk decisions. The gate
   is rechecked after validation; concurrent usage blocks correction. Used definitions
   are preserved. Normal exchange close is 15:30; strategy flatten at 15:15 is separate.
3. Select a decision policy yourself; the initial field is blank:

   | Policy | Behavior and evidence |
   |---|---|
   | Rules only | Explicit experimental paper hypothesis. Daily screen: positive 20-session momentum, 50-session trend, average daily turnover at least ₹1 crore, daily volatility at most 5%. Long-term entries use 2% stop/4% target, at most 1% quote-to-prior-close gap and a 20-session holding limit. Intraday uses the existing completed five-minute opening-range-breakout rule and warmup. These rules have no claim of current-market profitability. |
   | Rules + independently validated ML | Requires a server-selected finished compatible model and all existing horizon, strategy, fee/policy, hash, chronology/embargo, age and validation gates. A missing or failed model never falls back to rules. |

   No validated model is manufactured from this data download. The optional private
   environment entry below selects an already validated matching model directory:

   ```sh
   TRADING_PREPARATION_MODEL=data/your-independently-validated-model
   ```

   Restart the server after changing this environment setting. See the existing
   [intraday ML](ml-research.md) and [daily execution/model](daily-execution.md) workflows.
   A current constituent snapshot cannot substitute for their historical input evidence.
4. Enter your real review reference/notes, then check the calendar, historical
   action/basis/classification and selected-policy acknowledgements. None is prechecked.
5. Disconnect market data in Broker & Data and resolve pending paper orders first.
   Return to Strategies and confirm **Review strategy installation**. Review text includes
   the universe count, policy, source reference and consequences. The server binds the
   exact source hash, edited CSV, policy, reviews and current mode revision.

Installation saves private generated data/profile/calendar files and loads the profile
in the running process. It does not require another restart, replace the feed list,
approve today's execution price basis, submit an order or activate a mode. Manual stays
selected. Already used calendar hours cannot be overwritten; existing source references
are retained. Conflicting definitions or unreferenced existing sessions require local
review. No financial policy/capital is changed by the setup writer. Installation blocks
mode activation even when an older valid strategy exists. Failure releases that temporary
block and leaves Manual selected. Crossing midnight during acquisition/installation
requires fresh source coverage for the new IST date.

## Reach Approval or Automatic

If the combined setup completed, shortlist selection, the listed eligible basis reviews
and connection request are already done. Skip the corresponding separate controls below;
inspect readiness and activate your mode only when it permits.

1. Inspect the screen, candidate exclusions and proposed **execution shortlist** in
   **Strategies**. Rank describes observed momentum/screen strength, not calibrated expected profit.
   There may be no qualified stocks; do not loosen evidence or force an order to get activity.
2. For the separate Advanced flow, confirm **Use reviewed ranked shortlist** while in
   Manual, disconnected, with no pending orders. Every held symbol is retained, and execution remains limited to ten symbols.
   Unsupported held assets remain blockers; this does not make ETFs supported equity shares.
3. If not included in a combined confirmed review, complete **today's** corporate-action/
   price-basis review per supported selected stock in Risk Management. Historical basis review at installation
   and a calendar review do not approve the current execution basis. Intervening actions,
   including after a weekend/outage, remain subject to the existing quarantine workflow.
4. Reconnect explicitly in Broker & Data and wait for new usable quotes. A connected
   socket with empty/zero-depth books can remain connected after hours, but cannot fill
   orders or enable modes. Quote cards show exchange time, age, freshness and basis review.
5. Return to **Paper Trading** and read **Your next step**, market/entry hours, next reviewed opening and remaining blockers.
   Once all pass, select **Start approval mode** or **Start automatic paper mode** and
   confirm. Mode selection is deliberately independent from download/installation.
6. Approval queues eligible buys and discretionary sells for your review; Automatic submits
   eligible paper orders without per-trade approval. Protective exits never wait for a
   discretionary approval. Inspect **Paper Trading** for reasons, order acceptance,
   actual later fills and fees. A polling interval, screen or accepted order is not a fill.

## Persistence, refresh and recovery

Artifacts are stored in `<account database stem>.analysis/<random run id>/`: original
official source snapshots, `draft.json`, generated `daily/{manifest.json,daily.jsonl}`,
`profile.toml` and `sessions.csv`. Files are private from creation. The root contains
bounded `latest.json` progress and `active.json`, whose job/profile/data hashes select
only a server-owned installed profile. Browser requests cannot provide local paths,
broker URLs or executable model uploads.

On restart the saved profile is revalidated and restored **in Manual mode**. An explicit
`TRADING_ANALYSIS_PROFILE` environment override takes precedence; remove that override
when choosing the UI-managed strategy instead. Source/profile/data changes or invalid
saved pointers cannot silently install another policy. An exact repeated installation
returns its prior result; changing a completed run requires a new immutable download.

Snapshots are not incrementally edited while a strategy runs. To refresh after a new
completed day, membership/action change or coverage issue: choose Manual, download a
new run, inspect/review sources and use **Review and finish setup** again (or the separate
advanced installation controls in Strategies). Reactivate explicitly when readiness permits. Today's prepared but
uninstalled snapshot expires for installation at the next IST date; get fresh sources.

| Problem | Recovery |
|---|---|
| Official source unavailable/changed | Retry later. There is no invented calendar, empty-action fallback or alternate unofficial universe. |
| Early-year or wrong-year calendar | This downloader requires at least 51 prior reviewed-session proposals in the current year. Supply a genuine reviewed cross-year bundle using the existing profile workflow. |
| Kite history unavailable | Verify the saved broker session and history subscription separately from the socket; retry a new download after fixing access. |
| No eligible history | Inspect corporate-action, catalog and missing-session exclusions; wider discovery may help, but never establishes profit. |
| Install blocked by connection/orders | Disconnect explicitly, inspect/resolve pending orders, refresh, then review again. Holdings are retained. |
| Existing calendar conflict | Review saved/proposed hours. Only a separately acknowledged unused-account correction can change them; otherwise preserve used definitions and review locally. |
| Timeout during installation | Refresh desk/preparation status before retrying. Manual remains selected; an identical confirmed retry does not create another installation/order. |
| Partial disk/pointer failure | Account configuration may already reference the reviewed calendar, while strategy installation is incomplete. Stay Manual, inspect the private files/status and repeat the reviewed installation or restore the prior configuration. Never claim a trade from an install response. |
| ML unavailable or invalid | Install actual matching validation evidence, or explicitly choose the experimental rules-only policy. No silent fallback. |

## Provenance and limits

`universe_kind = "prospective_snapshot"` records current constituents at the actual
observation time. Prior prices may inform a **current/future** screen; that does not
claim today's constituents were historical members. Price availability is no earlier
than retrieval, and historical basis approval is no earlier than the operator's review.
Analysis before that availability cannot see the snapshot. Offline daily execution/ML
datasets reject these snapshots; existing point-in-time bundles retain their old semantics.

The corporate-action filter is conservative and can exclude many otherwise tradable
stocks. Source availability/completeness, late notices, symbol mappings, subscription,
network failures and prospective profitability remain real external concerns. No
fundamentals, valuation model, automatic action accounting, automatic daily retraining
or guaranteed-profitable selector is added. Each horizon retains a separate account,
database, capital and matching model/policy.

Official protocol/source references checked 21 October 2026:

- [Kite historical candles](https://kite.trade/docs/connect/v3/historical/).
- [Nifty 100](https://www.niftyindices.com/indices/equity/broad-based-indices/nifty-100),
  [Nifty 500](https://www.niftyindices.com/indices/equity/broad-based-indices/nifty-500).
- [NSE holidays](https://www.nseindia.com/resources/exchange-communication-holidays),
  [normal equity hours](https://www.nseindia.com/static/market-data/market-timings),
  [equity corporate actions](https://www.nseindia.com/companies-listing/corporate-filings-actions).
