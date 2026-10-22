# Prepare a genuine-data paper strategy in the UI

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
2. In **Broker & Settings**, check the saved broker session and import the NSE catalog.
   Expired broker access requires normal login/2FA and request-token exchange. The
   local operator token is different from broker request/access tokens. Your broker
   data plan must actually permit historical candles; profile/socket success alone
   does not prove that entitlement.
3. Choose **Manual** in Dashboard before preparation. In **Strategies**, open
   **Prepare a paper strategy**. Preparation is available on the manual service with read-only broker setup;
   an existing bound legacy controller retains its original workflow.

The light sidebar also provides Market & Analysis for [actual saved-candle charts](market-analysis.md),
Paper Trading for execution/history, Purchases & SIP as its secondary workflow,
Risk Center for basis and emergency/entry controls, and Broker & Settings for broker
administration. Contextual onboarding links here when setup is incomplete; the
full guide remains in **Help & onboarding** at the sidebar bottom. Navigation
retains the local token in memory and never authorizes a setup or financial action.

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
Held positions, quarantines and gaps still require separate Risk Center review. Nothing is attested
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
5. Disconnect market data in Broker & Settings and resolve pending paper orders first.
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
   price-basis review per supported selected stock in Risk Center. Historical basis review at installation
   and a calendar review do not approve the current execution basis. Intervening actions,
   including after a weekend/outage, remain subject to the existing quarantine workflow.
4. Reconnect explicitly in Broker & Settings and wait for new usable quotes. A connected
   socket with empty/zero-depth books can remain connected after hours, but cannot fill
   orders or enable modes. Quote cards show exchange time, age, freshness and basis review.
5. Return to **Dashboard** and read **Your next step**, market/entry hours, next reviewed opening and remaining blockers.
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
