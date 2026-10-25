# Dashboard, strategies, approval modes and paper activity

Version **0.15.0** separates the saved summary at **Dashboard** (`#dashboard`)
from **Paper Trading** (`#paper`, page `/paper`), which contains readiness, quote
warnings, modes and proposals. **Strategies** retains preparation and shortlist
review. **Trade History** (`#history`, page `/activity`) retains recorded orders,
fills and proposals without an order. These destinations share the same in-memory
workspace unlock. Legacy `/desk` opens Dashboard; its strategy/shortlist anchors
still open Strategies. Use Paper Trading for mode activation and approval controls.

Mode and trade confirmations use the shared visible-viewport dialog helper, including
cancel/escape cleanup, focus restoration and parent navigation guards. A late response
after pagehide/Lock cannot restore private desk data. The new Dashboard reads saved
state without running proposal expiry or strategy refresh. See
[frontend modernization](frontend-modernization.md) for freshness and missing features.

Version **0.13.1** simplifies the normal setup to **Download strategy data → choose a
policy → Review and finish setup → one acknowledgement and Confirm and prepare**.
The combined summary shows exact stocks, source links, all session dates, calendar
corrections and reviews included for today. The server handles installation, shortlist,
eligible reviews and feed reconnection. No freeform notes or manual CSV copying are needed.
Advanced calendar/individual controls remain available. The outcome stays Manual; check
readiness before separately choosing Approval or Automatic. Existing holdings/quarantines
and uncovered price histories are never auto-cleared. See the updated
[preparation guide](strategy-preparation.md) for failure/retry and closed-hour behavior.


Calendar differences now show saved/proposed hours. Only a separately acknowledged
unused-account correction can change existing hours; quotes, pinned reviews and
execution/instruction usage block it. Mode activation waits throughout installation.

Version **0.13.0** adds [in-app genuine-data preparation](strategy-preparation.md).
Use **Prepare a paper strategy** to download Nifty 100/500 sources and completed Kite
daily history, review calendar/basis coverage, explicitly select rules-only or a matching
validated ML policy, and install without editing a profile by hand. Installation keeps
Manual selected. The **Your next step** cards explain strategy/data, feed, quotes, hours,
shortlist, model and long-term basis checks before either mode can start.

Version 0.12.0 adds a decision workflow for intraday and long-term **paper** accounts.
It does not enable real broker orders. The existing account is not automatically
switched, re-funded or assigned a new universe/model by an upgrade.

## Cancelled proposals and idle Automatic mode

In Approval mode, a proposal is only an invitation to review a trade. Before your
explicit approval it creates no order, fill or cash reservation. The activity heading
now says **proposal cancelled · no order created** for these records, and shows both
the proposal time and last-update time, its mode, outcome and recorded pause triggers.
Older records retain their original generic outcome; missing historical triggers are
not invented. New watchdog cancellations include specific causes such as
`NO_FRESH_EXECUTION_QUOTES`, with a durable `desk_pause` event.

A session/feed/risk pause revokes pending proposals and changes the mode to Manual.
Fresh quotes returning does not automatically reactivate Approval or Automatic. Hard
fault/disconnect/date/controller revocation does not first depend on a snapshot read.
Inspect the current mode and reasons, then explicitly choose a mode when ready.

The original live parser supplied whole-second Kite exchange times. Multiple book
updates within that second, including unchanged repeats with different receipt times,
were incorrectly treated as bad ordering. This could invalidate the entire shortlist
between updates and trip the watchdog. The broker/candle path now accepts changed
Kite books tied at a whole-second exchange time only with strictly later receipt
time, matching symbol/token/source and nonregressing volume. Unchanged repeats are
ignored without renewing freshness; genuine backward/ambiguous data remains blocked.
Tied updates preserve actual marks, protection and candle volume, but cannot process
another fill or replenish liquidity at that exchange timestamp. Replay inputs keep
strict exchange-time ordering. See [the feed details](paper-feed.md#whole-second-kite-updates).

Automatic can also be idle because today's daily signals were already handled.
The desk now shows matching current-day/profile outcomes from its latest 100 records.
For example, **6 cancelled** means those six daily signals remain terminal. Switching
modes or receiving new prices does not replay a cancelled/expired/declined/submitted
signal. Any remaining selected stock still needs its own eligible entry signal,
price-gap bounds and all risk checks. Starting Automatic is not an instruction to buy
every selected stock, and a screened candidate is not automatically an order.

Load the Python fix once: inspect holdings/pending orders, Ctrl+C in the owning server
terminal, run `./scripts/start_ui.sh`, reload/unlock, then connect/review and explicitly
select the intended mode. The launcher otherwise reopens an existing process. Restart
cancels unfilled recovery residue, retains held shares and starts the normal profile
desk in Manual. It does not reset daily signal history or automatically retry a trade.

## Open session with no usable quotes

An open reviewed session and a connected socket are separate from quote acceptance.
For long-term accounts, today's explicit corporate-action/price-basis review is required
before incoming quotes can be stored, marked or used for fills. A review saved yesterday
does not cover today. Consequently, **no accepted quote** can coexist with a working
live feed. Read the per-symbol explanation in Paper Trading's **Inspect quote details**
or Risk Management, rather than interpreting every missing quote as a network failure.

When today's source/history data is ready, **Review today’s setup** appears beside the
warning and in quote/basis readiness cards. It opens the existing combined source,
calendar and stock summary with an unchecked acknowledgement. The existing installed
policy can be reused; you must choose a policy explicitly for a first installation.
Inspect the included daily reviews and separate manual requirements, then select
**Confirm and prepare** to apply the shown changes. Pending reviews remain pending
after a restart; a restart only loads code. Old data requires a fresh current-day
download through the displayed preparation link. The shortcut disappears once resolved.

The shared read-only diagnostic distinguishes required/blocked basis reviews, feed
disconnection, no stored quote, rejected newer observations, waiting for a post-connection
quote, stale timestamps and usable quotes. Its labels never authorize a trade. The
header shows whether the reviewed session is open now separately from the next opening.

If **Supported execution shortlist** needs attention, select **Review the ranked
shortlist**. It opens/focuses **Review the execution shortlist**, showing the exact
proposal and held-symbol retention. The old `/desk#apply-shortlist` link is preserved
through `/workspace#strategies/apply-shortlist`; the current destination is
`/workspace#strategies/execution-shortlist`. Merely opening either link changes no account data.
To apply, select Manual, disconnect the requested feed in **Broker & Data → step 6**,
resolve pending orders, then inspect and confirm **Use reviewed ranked shortlist**.
Held symbols remain required. The review section links directly to feed controls.

Next, review each supported selected symbol's current-day action/price basis in
**Risk Management**, with an actual source/reference and explicit confirmation.
Quarantine needs the offline action workflow and cannot be cleared by a normal review.
Reconnect explicitly if disconnected, then wait for a new valid quote. Neither a review
nor a stored historical candle invents a live quote, arms a mode or submits an order.

Reload the workspace to load the navigation changes. Restart an older Python service
to load the new diagnostic API: review pending orders/holdings, stop its owning terminal
with Ctrl+C, run `./scripts/start_ui.sh`, unlock, then explicitly connect if needed.
Restart cancels pending residue under existing recovery rules; disconnected holdings
cannot fill exits. No session, review, shortlist or trading mode is approved by this upgrade.

## What the current five stocks mean

BEL, EXIDEIND, GOLDCASE, HDFCBANK and MAZDOCK were operator-selected feed subscriptions.
They were not selected as the most profitable stocks. Without a reviewed analysis
profile, the desk explicitly says **Your selected watchlist**, shows the actual
symbols and blocks strategy-mode activation with an explanation. There is no hidden
ML filter or broad-market selector running on that manual account.

A configured profile can screen up to 500 declared symbols from reviewed raw daily
history. Supported equity-share classification is separately required; a catalog EQ
row is not enough. In particular, GOLDCASE is an ETF, and this release does not add
ETF charges/accounting. Unreviewed classes are excluded from the strategy shortlist;
held unsupported classes prevent activation until that accounting/review gap is resolved.

The daily rank measures completed momentum/trend/liquidity/volatility screen strength,
not calibrated expected profit. A matching validated ML model filters individual entry
proposals at trade time. No stock, ranking, high score or historical result guarantees
profit. [Opt-in scheduled acquisition](operations-automation.md) is available, but
unattended strategy installation/review, current-market net-expectancy validation
and unattended corporate-action source integration remain separate work.

## Start and navigate

From the repository root:

```sh
./scripts/start_ui.sh
```

For the existing 8004 account, open <http://127.0.0.1:8004/workspace#desk>. Stop an
older owning server gracefully first if the launcher reports a version mismatch;
keep the new terminal running. Unlock once with your private `TRADING_OPERATOR_TOKEN`.
The sidebar contains twelve grouped destinations; see the [complete route table](workspace.md#menu-and-unlock-behavior).
Dashboard summarizes saved state; **Paper Trading** owns readiness, modes and proposals;
**Trade History** owns orders/fills. **Portfolio → Purchases & SIP** preserves explicit
purchase and recurring-instruction workflows. **Learning Center** includes setup guidance.
Broker & Data retains the connection overview and six expandable reviewed setup steps.
Opening a step changes no saved configuration. Read the [broker guide](ui-setup.md)
and [saved-chart limitations](market-analysis.md).

Desktop uses a sidebar; narrow screens adapt navigation while keeping Lock accessible.
Changing sections retains the same local
unlock. Reload/new workspace tabs require a new unlock. Locking/closing a browser
**does not pause a running strategy or stop the server**. Choose Manual or use the
independent kill/flatten controls as appropriate.

## Operating modes

| Mode | New strategy buys | Discretionary strategy sells | Protective/risk exits |
|---|---|---|---|
| Manual | No strategy-generated orders; explicit operator purchase workflows remain available | Explicit operator instruction | Continue independently |
| Approval / semi-autonomous | Strategy queues a proposal; operator reviews and approves or declines | Operator approval required | Never delayed for approval |
| Automatic / autonomous paper trades | Eligible strategy proposals are risk-checked and submitted without individual approval | Eligible rule exit is queued automatically | Continue independently |

The mode card distinguishes selected mode from actual activation. Blocked/paused is
not running. Starting either strategy mode requires explicit confirmation, a current
reviewed open session, an entry window, connected usable data, appropriate source
coverage, no account/kill fault and the configured model's availability/age checks.
Missing prerequisites are shown in plain language; disabled buttons do not manufacture
missing data or approve calendar/corporate-action reviews.

Changing mode cancels outstanding proposals and this desk's unfilled BUY remainder.
Already filled shares retain their protections. A legacy bound intraday controller
uses its existing disarm/cancel policy. Protective SELL orders are not cancelled by a
mode change. A new session, lost connection, loss of all usable execution quotes,
expired model or risk stop pauses decision authority. Fresh data does not silently
reactivate it. Strategy mode is not restored after restart; the legacy bound intraday
controller may display its selected automatic mode but remains disarmed until explicitly
armed. Intraday and long-term accounts still use separate databases and virtual capital.

## Review and approve a proposal

1. Read the proposal's symbol, BUY/SELL direction, original rule reason, signal time,
   expiry and source evidence. A proposal holds no shares and reserves no cash.
2. Choose **Review buy proposal** or **Review sell proposal**. The server calculates a
   current preview. If blocked, read the reasons; no order was submitted.
3. For a BUY, inspect maximum quantity, adverse price cap, maximum cash debit including
   buy fees, risk ceiling, stop and target. These are execution bounds and scenarios,
   not a promise of gain. For a SELL, review the holding and the rule for its market
   exit; subsequent quotes determine actual sale prices.
4. Confirm explicitly, or cancel. The server checks mode generation, profile/model,
   expiry, symbol/class, fresh quote, signal/price gap, holdings, capital, costs and
   risk again. A default two-minute approval window and 20-basis-point movement limit
   are predeclared in the analysis profile. An accepted BUY cannot grow above the
   approved quantity or exceed reviewed cash/price/risk bounds if the quote changes.
5. Read **Paper Trading**. ACCEPTED reserves capacity; PARTIAL/FILLED comes only
   from later observed usable quotes and simulated depth. Rejection/cancellation is
   retained with its reason. An identical confirmation retry returns the original
   terminal result, including after a lost response; it does not submit another order.

The signal remains original evidence. Approval is a new current execution decision;
quote-dependent ML features are recomputed using the original completed candle/daily
context and current causal quote. The profile's approval delay is an experimental
paper execution policy, not separate empirical validation of delayed trading profits.
A missed/declined/expired signal is not automatically recreated. Profile-driven
proposals are conservatively limited to one per symbol/direction/session. Intraday
still requires a completed five-minute signal after warmup; long-term uses prior
completed daily information and may hold overnight. Maximum-holding-session exits
require the reviewed calendar to cover the original opening date; unavailable history
is not treated as an invented age or a reason to liquidate. There is no trade-every-poll promise.

Stop, target, stale-held-price risk, kill switch and required session exits remain
independent. A discretionary sell cannot duplicate an already queued protective exit.
A queued sale is not a completed liquidation.

## Install an actual analysis profile

For the UI-managed prospective workflow, follow [Strategy preparation](strategy-preparation.md).
The manual custom-bundle steps below remain available for cross-year data, point-in-time
history and specialized reviews. No ML model is created by the new downloader.

This is an operator data/evidence task. Copying a template or marking invented data
as real is not valid setup. Genuine sources can now be downloaded in the UI, while
source/calendar/basis review and matching real ML validation remain separate evidence.
Installing code alone does not start profit-oriented autonomous selection.

1. Prepare an immutable [daily bundle](daily-research.md) with `manifest.json` and
   `daily.jsonl`: genuine raw completed bars, source/availability clocks, reviewed
   session calendar, point-in-time membership (including removals) and explicit
   period benefit/basis reviews. Default screening needs at least 50 consecutive
   reviewed sessions. Include today's reviewed session definition even before today's
   daily bar is complete, matching the execution account's calendar.
2. Prepare actual supported equity-share classification reviews for each eligible
   discovery symbol. Review timestamps cannot be in the future. Classification and
   historical basis reviews are distinct from today's execution-account basis review.
3. For `strategy_mode = "rules_ml"`, provide a matching finished independently
   validated model. Intraday uses [intraday model artifacts](ml-research.md), long-term
   uses [daily model artifacts](daily-execution.md). Horizon, strategy, financial
   policy, charges, chronology, hashes, validation/holdout gates and synthetic status
   must match. Model score is not shown as a guaranteed profit probability.
4. Copy and edit the [profile template](../config/analysis.example.toml):

   ```sh
   cp config/analysis.example.toml config/analysis.local.toml
   chmod 600 config/analysis.local.toml
   ```

   Replace example paths, symbols, references and review times with genuine inputs.
   Keep `rules_ml` when ML is required. Choosing `rules` explicitly opts into a
   rules-only experimental paper policy; there is no automatic fallback from failed ML.
   `config/*.local.toml` and data are ignored and excluded from normal packages.
5. Add this **path only** to your private `.env`:

   ```sh
   TRADING_ANALYSIS_PROFILE=config/analysis.local.toml
   ```

   Restart the owning server with `./scripts/start_ui.sh`. Use one profile for the
   selected account/horizon. The profile is server-selected; HTTP clients cannot
   provide arbitrary filesystem paths or upload executable model objects.
6. Open **Strategies**. Inspect real/synthetic provenance, latest completed session,
   candidate count, exclusions and the proposed execution shortlist. A connected
   production desk refuses synthetic inputs/models; test-only overrides are not
   exposed by the CLI/browser.
7. To replace the old five-symbol feed, choose Manual, disconnect in Broker & Data,
   resolve pending orders, then return and confirm **Use reviewed ranked shortlist**.
   It preserves every held symbol and selects at most ten catalog-matched NSE tokens.
   The approval hash binds the reviewed plan; changed plans require a new review.
   It does not arm a strategy or reconnect automatically. Reconnect in Setup, complete
   genuine current-session reviews and wait for fresh quotes.
8. Select Approval or Automatic and confirm. Inspect proposals/activity prospectively,
   including rejected, absent and losing decisions. Review costs, outages and unfinished
   holdings rather than selecting only favorable runs.

Profiles/data/model identities are frozen in memory for a run. Changing source files
is not a supported incremental-data update: hash checks reject changed inputs and
pause analysis. Install a new reviewed immutable bundle/profile and restart explicitly.
Network data subscriptions and login/2FA remain external prerequisites. Version 0.13
adds operator-requested constituent/calendar/action-source reads and genuine daily
history acquisition with manual coverage/basis approval. Unattended daily refresh,
fundamentals ingestion and automatic corporate-action accounting remain separate work.

## Activity, exact money and unknown outcomes

Activity shows up to 50 orders per page, newest first, with stable **Earlier orders**
cursors. Buy/sell filtering applies to the current page. Expand a record to see exact
order fields, source proposal/manual reason, authorization mode, fills, prices, fees,
stop/target/caps and retained model/context evidence. Orders without desk proposals
retain their explicit manual, legacy automation or protective-control origin.
More than 100 fills per order have additional cursor pages. **Refresh latest** returns
to the newest orders; activity does not re-render itself while you read expanded data.
The latest 100 decision records also show waiting/declined/expired/blocked proposals
without implying a fill. Older durable decision evidence remains in the journal and
linked order records; the UI's no-order decision list is bounded, not a complete export.

Cash debit is `BUY turnover + buy fees`, or negative `SELL turnover - sell fees`.
It is cash flow, not net trade profit. Partial holdings and acquisitions remain in the
existing portfolio/account views. Money remains Decimal on the server and decimal
strings in the browser; model features/scores and timing measurements are analytical
floats, not money. P&L accounting is not reconstructed from UI average prices.

After timeout/auth loss, refresh activity before retrying. A committed order can exist
even when its response was lost. Authorization is durable before BUY submission and
is independently bound to its exact candidate/features/quantity cap in the broker's
transactional journal. The production clock is checked again after durable BUY
authorization, so disk-write delay, clock regression, expiry or model-age rollover
cannot reuse a stale approval time. Broker submission checks quotes/session/risk at
that observed execution time. Restart links a committed matching order or cancels unsubmitted
authority; it never replays an interrupted approval. SELL linkage is atomic with the
exit queue. Decision rows must reconcile with their journal and authorization proofs.
Never edit SQLite to clear a blocked state.

## Performance and acceptance limits

Broad daily parsing/ranking and historical HTTP reads run in a separate analysis
worker outside quote/risk locks. Daily screening is cached between 60-second refreshes;
only the execution shortlist's daily timeline is retained. Intraday history requests
are serialized with at least 400 ms spacing and evaluated only at completed boundaries;
missed/unusable bars are not invented. Features/model inference are bounded. Indexed
order/decision/fill cursors keep UI reads bounded. Historical network latency can
still prevent a timely signal; local screen timings exclude external acquisition.
The desk polls every five seconds; the existing risk watchdog runs about once a second.
These intervals are not promises to buy or sell on a fixed schedule.

Tests and an isolated headless desktop/390-pixel layout check exercise synthetic
proposals, shared unlock, confirmations and activity. They are engineering acceptance,
not profitable-stock evidence, real-feed/fill acceptance or physical-phone testing.
Current-market data acquisition and prospective net-of-cost strategy/model evaluation
remain required before claiming a qualified profit-seeking operating shortlist.


## Proposal alerts across workspace sections

After running `./scripts/start_ui.sh`, reload `/workspace` and unlock with the local
operator token. The workspace checks authenticated persisted proposal metadata every
five seconds, including while you use Stock Analysis, Strategies or another browser
tab. It shows a proposal banner, a browser-title count and the earliest deadline in
seconds. Before the first response, the banner says **Checking for paper proposals**.
The changing countdown sits outside the polite live-status announcement; assistive
technology receives count/state changes without a repeated announcement each second.
The read is bounded to 100 records, prioritizing awaiting proposals; it does
not evaluate strategies, expire records, reserve cash, approve or submit an order.
Open **Review paper proposals** to use the existing review and confirmation flow.

For desktop notifications, select **Enable desktop alerts** in the banner and choose
the browser permission explicitly. No permission is requested merely by opening or
unlocking the workspace. New pending proposal identities notify once per workspace
unlock; refreshes do not repeat the same alert. Notification text contains no symbol,
price, token or account balance. Selecting an alert opens Paper Trading; it never
approves a trade. Use **Disable desktop alerts** to stop notifications. Lock or page
close clears the alert display, notification handles and in-memory preference.

If permission is blocked or unsupported, the banner and browser-title count remain
available. If a proposal's deadline passes locally or its saved outcome becomes
expired, the banner directs you to Trade History; a local countdown does not claim
that the server has changed its record. Failed checks or more than 15 seconds without
a successful response show stale/unavailable guidance. Open Paper Trading and refresh
before acting. Authorization rejection locks the workspace. Late responses after
Lock cannot restore proposal details.

This is best-effort polling while the workspace remains open and unlocked. Browser
sleep, background throttling, network outages and a closed/locked workspace can delay
or prevent alerts. It is not server push, a background service or a guarantee that a
120-second approval deadline will be seen. Expired/cancelled signals still require
inspection; the alert does not retry them. Automated DOM tests cover alert permission,
route and hidden-tab checks, deduplication, stale reads, expiry, guards and Lock cleanup.
The functional endpoint test independently inspects SQLite to verify unchanged exact
cash and absent orders/fills; it does not prove desktop/mobile notification delivery.

Price-gap blockers now explain that the quote lies outside the policy's entry bound
and require a usable in-bound quote or new reviewed signal. Calendar blockers direct
you to Strategies for fresh data and a reviewed exchange calendar. Startup and delayed
authorization outcomes explain the next action without changing any safeguard.
