# One workspace, one unlock, clear next steps

Version **0.14.0**, 22 October 2026, reorganizes the existing paper workflows into a
light workspace with a persistent sidebar, white cards, readable dark text and teal
navigation accents. Dashboard puts portfolio values, market status and the next
required action first. Green/red communicate financial or readiness status. No
account balance, trading rule, saved strategy, broker credential or confirmation is
changed by the redesign.

If your connection remains offline after requesting a feed, inspect Broker & Settings
step 6 for safe
failure/retry details and follow the [restart/recovery guide](ui-setup.md#after-hours-feed-offline-fix-0111).
Connected with stale/missing quotes after hours is a valid distinct state: missing
executable depth is ignored rather than invented, and trading stays blocked.

The [decision and activity workflow](trading-desk.md) includes
profile-driven broad screening and explicit approval/automatic paper modes for both
horizons. They require genuine reviewed inputs; existing accounts are not activated
or assigned a new shortlist automatically.

## Load the new version

If your own Terminal is already running the older service, stop it there with
**Ctrl+C**, then from the project directory run:

```sh
./scripts/start_ui.sh
```

The current workspace uses port 8004. The launcher opens `/workspace`, checks both
account identity and UI version before reusing an existing process, and refuses to
silently reuse an older server. A process you started remains yours to restart;
this upgrade does not silently replace it. Wait for graceful shutdown before starting
another owner of the same account. Inspect holdings/pending work before any stop,
because restart recovery and quote outages retain their existing consequences.

Direct Console/Setup/Portfolio links route to the corresponding workspace section.
The ordinary root URL and an empty/unknown workspace hash route to **Dashboard**. Legacy CLI callback URLs containing
a request token remain available for manual capture; handled UI login popups retain
their guarded callback handoff instead of becoming a navigation request.

## Menu and unlock behavior

| Main area | Route | Purpose |
|---|---|---|
| Dashboard | `/workspace#desk` | Portfolio summary, actual market/readiness status, next action, operating modes and proposals |
| Market & Analysis | `/workspace#analysis` | Search saved symbols and inspect actual stored daily/minute candles and technical indicators |
| Strategies | `/workspace#strategies` | Guided data/policy setup, screening evidence, source exclusions and execution-shortlist review |
| Paper Trading | `/workspace#activity` | Recorded orders, fills, fees and proposals without an order; separate status and execution evidence |
| Risk Center | `/workspace#console` | Detailed readiness, current-session long-term basis review, exposure and emergency/entry controls |
| Broker & Settings | `/workspace#setup` | Connection overview, guided broker login, catalog, subscriptions, reviewed calendar and feed settings |

**Purchases & SIP** is a secondary item under Paper Trading at
`/workspace#portfolio`; its explicit purchase, contribution and recurring-plan
workflows remain available. **Help & onboarding** sits at the sidebar bottom at
`/workspace#overview`. A contextual setup banner appears when strategy, reviewed
calendar or requested-feed setup is incomplete. It links to the next setup task;
it does not install, approve or connect anything. Onboarding is not a seventh main
area. On narrow screens the navigation adapts to the viewport and the account lock
remains available.

[Market & Analysis](market-analysis.md) reads saved candles when viewed; opening a
chart never requests a broker download or creates market data. Missing history,
stale quotes and insufficient indicator inputs remain visible limitations. Strategies
uses the existing preparation/decision controllers on its separate `/strategies`
page; moving those controls does not create backtests or enable new trading behavior.

Unlock once with `TRADING_OPERATOR_TOKEN` from your private `.env`. Menu navigation
keeps that token only in the workspace and active section's memory. It never writes
the token to a URL, cookie, local storage or session storage. Sections receive it
only after matching the workspace's exact origin/window and active section. There
is no server login cookie or cross-tab credential synchronization.

Merely switching to another browser tab does not intentionally lock the workspace.
Reloading, closing/leaving the workspace, opening a separate workspace tab or a
section authorization failure requires unlocking again. **Lock workspace** clears
access, destroys the active view and ignores late responses/messages. It does not
stop the server/feed, cancel an already received action, disarm automation or close
holdings. Refresh after an uncertain action before retrying.

Navigation blocks while a section has an active mutation/confirmation or a Setup
request/login popup. Finish/cancel it first. Changing sections clears unsaved forms,
previews and local login state; confirmed orders/plans remain server-side. The
server's normal freshness/idempotency checks remain authoritative after navigation.

Readiness links now preserve their destination within a section: for example,
legacy `/desk#apply-shortlist`, `/desk#execution-shortlist` and `/desk#strategy-setup`
links route into Strategies; the shortlist destination is
`/workspace#strategies/execution-shortlist`. Ordinary `/desk` continues to open
Dashboard. `/setup#feed-connection` opens Broker & Settings with its connection step
expanded. After unlock/render, the
target section receives keyboard focus and the outer page scrolls it into view below
navigation. Quote-details links also expand their closed details panel. Repeated
links work without a section reload or repeated scrolling on polling. Section-change
guards, origin/window checks and shared in-memory access remain in force. Navigation
does not apply a shortlist or submit a mutation. Reload the full workspace to update
the parent navigation script; changing only the embedded section is insufficient.

Daily price-basis warnings now expose **Review today’s setup** directly, including
inside expanded quote details, when same-day data is ready. The button opens the
existing summary/unchecked confirmation; it does not navigate away, approve a review
or change a mode. Cancel preserves the blocker. Successful resolution hides the shortcut
on the next status update. Load this child-page addition by visiting another section
and returning to Dashboard. Upgrade an older server to 0.14.0 as described above.

## What to do after unlocking

1. Read **Dashboard** for portfolio values, actual market/readiness state and the next
   action. The contextual onboarding banner and **Help & onboarding** provide setup
   guidance. The launcher starts the UI without requesting a feed.
2. Open **Broker & Settings**. Its overview distinguishes connected, requested and
   disconnected data and recommends a step. Only the first unlocked status chooses a
   default open step; refresh preserves your open step and edits. Expand any numbered
   step or use **Back**/**Continue**; navigation never saves settings. In step 3,
   **Check saved broker session**. An available
   token can be expired. Progress and the final result appear directly under the
   login/check buttons; the check button stays disabled while waiting. A failed
   recheck clears the earlier verification claim; a timeout allows a manual retry.
   If renewal is required, disconnect a requested feed in
   step 6, open Zerodha login/2FA, then explicitly exchange the returned request token.
3. Step 4 shows the imported catalog and selected symbols. These are subscriptions,
   not profitable-stock recommendations. No need to reimport/resave an unchanged
   selection merely to connect. Preserve all held symbols; ETF costs remain unsupported.
   The catalog is a reference lookup; the saved list streams at most ten symbols under
   the app's current limit. Unsaved edits do not change **Saved feed subscriptions**.
   Use **Strategies** → **Prepare a paper strategy** for broader Nifty 100/500 research.
4. In step 5, add the next confirmed NSE session with its reviewed date, opening/closing
   times and notice/reference. Ordinary cash-equity hours are 09:15–15:30 IST, but
   holidays/special sessions require their actual notices. Adding a future date does
   not open today's market. The form requires explicit review and confirmation.
   Opening/closing fields now start at **09:15 AM / 03:30 PM IST** on unlock. Edit
   them for a supported reviewed session; refresh preserves edits. Defaults never
   precheck the review or save a date, and existing saved hours stay unchanged.
5. In step 6, **Connect paper market data**, review the confirmation and refresh status.
   Connecting can resume existing pending fills/protective exits; it creates no new
   intent. A connected socket alone does not establish accepted quote freshness.
6. During the relevant IST date, use **Risk Center** to review long-term symbols'
   current price basis, including intervening corporate actions since the last accepted
   quote. Do not attest clear merely to remove a warning. Await new accepted quotes
   after review; quarantines need the supported action workflow.
7. During an open reviewed session and the configured entry window, inspect all
   readiness reasons. Use **Purchases & SIP** only for an explicit supported manual
   hypothesis: preview, review costs/risk/quantity, confirm, then inspect later fills.

At **17:54 IST on 21 October 2026**, as shown in the operator's screenshot, the time
is beyond ordinary NSE cash-equity hours and this account's 09:30–14:30 entry window.
Stale/missing quotes and blocked entries after the close are expected; reconnection
cannot create a new executable open session. Prepare the next reviewed session,
renew credentials when necessary, and return during its configured entry hours.
See [NSE market timings](https://www.nseindia.com/static/market-data/market-timings)
and the [NSE holiday/notices page](https://www.nseindia.com/resources/exchange-communication-holidays).

## Trading frequency is different from monitoring frequency

| Mode | Actual behavior |
|---|---|
| Current manual long-term account | No automatic entry schedule. A purchase or SIP occurrence needs explicit operator confirmation, risk approval and later usable quote fills. Holdings persist overnight; supported stop/target/loss/kill/operator exits can trigger while supervised by the running server. |
| Separate supervised intraday account | Only after its dedicated configuration, valid data/model policy, warmup and explicit arming. It evaluates eligible completed five-minute bars; a bar is not a trade. The default proposal cap is one per symbol/session, including risk-rejected proposals; the UI reports the actual bound cap when automation exists. |
| Console refresh | Every three seconds while visible. This only refreshes displayed information. |
| Watchdog | Approximately every second. It checks risk/time controls; actual fills still need later usable quotes and liquidity. |

The current entry window is **09:30–14:30 IST**, with earlier-close cutoffs. Long-term
holdings have no 15:15 forced sale. Intraday's ordinary 15:15 exit is a request, not
a guaranteed fill. The default fourteen-bar intraday warmup normally finishes no
earlier than 10:25 for a 09:15 open; missing history or absent signals can mean no
trade all day. The coding assistant does not continuously trade in the background.

Reviewed profile-driven Approval/Automatic paper execution is available only after
its genuine source, policy, model and readiness requirements pass; empirical
profit-oriented qualification remains separate. See [stock-selection-plan.md](stock-selection-plan.md). Do not interpret a
connected feed, a completed bar or an offline synthetic research rank as trading
approval or proof of profit.
