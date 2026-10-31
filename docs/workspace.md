# One workspace, one unlock, clear next steps

## Watchlist destination (0.21.0)

The Research menu includes **Watchlist** (`/workspace#watchlist`). It uses the existing
private frame handoff, locking, accessible controls and guarded confirmation dialog.
Search the saved NSE catalog, review exact replacement permissions, and explicitly
acknowledge changes. Unsaved edits guard navigation; requests/confirmations prevent
section changes. A lost mutation response requires reading saved state without an
automatic retry. Lock clears private list and safety values; late reads are ignored.
Catalog timestamps, unmonitored selected stocks, exit-only holdings, stale valuation,
entry slots, drawdown and daily lockouts are explained. See [the usage guide](watchlist-safety.md).
Browser/native checks were added but not run on this change.

Backend **0.20.0** also supports the native Android **1.0.0** companion. The workspace
links to `/android` for its signed installer. Pair once, unlock with strong biometrics
and use native research/policy/backtest/account screens. The browser remains available;
phone access has a separate revocable credential. See [Android guide](android-app.md)
and [API authority, callback and installer component](mobile-api.md).

Version **0.19.2** lets the unlock field use your phone/browser password manager.
Save an entry for the hosted workspace with username **operator** and the full server
operator token as its password; autofill it to unlock. Token access in the app remains
in tab memory and Lock/reload still clears it. Save prompts depend on your browser;
manual password-manager entry is supported. See [mobile unlock and redirect setup](ui-setup.md#mobile-unlock-and-the-hosted-kite-redirect).
Broker & Data's connection result now updates automatically while its visible,
unlocked page has a requested feed, with stale-state and failure recovery beside the
buttons. Download prerequisites in Strategies also display before its disabled action.

Broker & Data → step 5 suggests the official NSE holidays/notices reference on unlock.
The editable suggestion follows the existing session-hour defaults and never ticks
the review checkbox, saves a calendar or enables trading. Edits/clearing survive
status refresh; Lock clears them and re-unlock restores the default. See
[review/save and failure behavior](ui-setup.md).

Version **0.19.0** adds consistent local icons beside all twelve menu labels and
selected actions/headings. Text labels and visible keyboard focus remain; color and
icons do not carry action meaning alone. The compact header retains paper identity,
current destination, lock state and **Lock workspace**. The setup note starts collapsed
after unlock with its current next step visible; expand it for the reason and guidance.
Shorter routine refresh feedback retains the actual observation timestamp/stale state.
Portfolio valuation formulas and Stock Analysis help/legend use expandable details.
Policy drafts use four explicit steps, with no autosave or preselected financial values.
See [the full interface and recovery guide](ui-experience.md).

Version **0.18.0** adds the Strategies subview
`#strategies/investment-policy` for [investment policy drafts](investment-policy-drafts.md).
The four parameter groups begin blank and can be saved incomplete after an exact preview
and explicit confirmation. Saved snapshots are immutable; **Edit a copy** creates an
unsaved alternative. **Specified** is a draft state, never installed/active authority.
An unsaved or uncertain draft blocks menu navigation until saved/discarded or reconciled;
Lock/page exit clears private in-memory edits. No draft action changes the current account.

The earlier **0.17.0** Phase 5 slice remains: **Backtesting** has registered
inputs, confirmed isolated-job admission, saved lifecycle/cancellation and verified
bounded report views. Launch requires verified OS isolation and hard limits; it is
**unavailable on the implementation Mac**, and the browser-job backend currently
supports only Darwin sandboxing. Registration and saved reads remain available.
See [browser backtesting](browser-backtesting.md) for commands, limits and recovery.

**Portfolio** adds exact cash/held-share allocation at current accepted bids, with
claims and pending commitments shown separately. Missing/stale held prices disable
weights. A pure daily-performance calculator is implemented, but accounts and legacy
replays lack accepted daily valuation/flow history: CAGR, Sharpe, Sortino and monthly
portfolio returns stay unavailable there. See [portfolio analytics](portfolio-analytics.md).

The existing offline replay retains its actual strategy/holding-session cap (default
20); connected parity, out-of-sample/walk-forward browser orchestration, executable
months-to-years strategies, target allocation and rebalancing remain unfinished Phase 5
work. Separate drafts support the user's months/multi-year and monthly/quarterly options;
no active account policy or duration is selected by saving one.

Phase 4 price research remains available: Daily/Weekly/Monthly charts, 15 causal
fixed-precision indicators, explicit warmup/gap states, known share-action-adjusted
OHLC/volume, price drawdown and optional traceable local benchmarks. Range controls
change display only; Discovery explains existing predicates without reranking.
Weekly/monthly completeness requires a hash-bound review. Preparation still supplies
at most 60 completed sessions from its supported current-year source, so long warmup
needs separately reviewed history. Licensed fundamentals remain unavailable.
See [investment research](investment-research.md).

The twelve-destination light workspace retains existing paper authorization, risk,
setup, purchases/SIP and shared confirmations. No upgrade activates an account or
changes credentials/watchlists/holdings. Automated synthetic/local evidence is distinct
from rendered browser/mobile, real OS, broker, source-license and device acceptance;
those external gates remain open. See [the frontend component guide](frontend-modernization.md)
and [validation record](test-plan.md).

If your connection remains offline after requesting a feed, inspect Broker & Data
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

| Group | Destination | Workspace route | Actual behavior |
|---|---|---|---|
| Overview | Dashboard | `#dashboard` | Exact saved portfolio values, market/account status, next action, saved candidates and recent decisions |
| Research | Stock Discovery | `#discovery` | Filter/sort saved research, inspect evidence and compare two to four stocks |
| Research | Stock Analysis | `#analysis` | Existing actual saved candle charts and indicators |
| Plan & simulate | Strategies | `#strategies` | Existing preparation, source/strategy review and execution shortlist; separate investment-policy draft subview |
| Plan & simulate | Backtesting | `#backtesting` | Registered isolated jobs, capability status, cancellation and verified report views |
| Plan & simulate | Paper Trading | `#paper` | Current readiness, modes and proposal authorization |
| My investments | Portfolio | `#portfolio` | Holdings, exact saved cash/basis/net valuation, coverage and accepted-bid allocation |
| My investments | Trade History | `#history` | Existing order/fill history and proposal outcomes |
| Controls | Risk Management | `#risk` | Existing current-basis, readiness, exposure and emergency controls |
| Controls | Broker & Data | `#broker` | Existing guided login, subscriptions, reviewed calendar and feed controls |
| Controls | Settings | `#settings` | Safe read-only active configuration; no secrets or financial edits |
| Help | Learning Center | `#learn` | Search application concepts and use the setup checklist |

Prefix hashes above with `http://127.0.0.1:8004/workspace` (use the launcher's port).
**Portfolio → Purchases & SIP** opens `#portfolio/purchases`, preserving the existing
preview/confirmation workflow. `#portfolio/holdings-heading` opens its aggregate
holdings/exit review. The default Portfolio uses a separate read-only summary.
The setup checklist is `#learn/setup-checklist`; the contextual setup note keeps the
next needed step visible and expands for its explanation. It only links to a needed
step. At 767 CSS pixels and below, **Menu · current screen**
opens all twelve destinations and closes after navigation. Lock remains available.

**Strategies → Create or inspect investment policy drafts** opens
`#strategies/investment-policy` (child `/investment-policy`). The current strategy and
preparation remain at `#strategies`; legacy setup/shortlist anchors are preserved. The
new planning screen does not add another main destination or replace account setup.

The saved account summaries explicitly refresh saved data through a read-only endpoint;
after six seconds they label the display stale. They do not start downloads,
subscribe, poll fills, expire proposals, approve reviews or change account authority.
The saved proposal state may await the existing execution workflow's next update.
See [financial definitions and limits](frontend-modernization.md). Stock Analysis
continues to read saved history. Strategies, Paper Trading, Trade History, Risk,
Broker and Purchases retain their existing operator workflows and risk checks.

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
request/login popup. Investment policy drafts additionally block menu navigation for
unsaved changes or an uncertain save: save/discard or refresh/reconcile first. Other
section changes clear their unsaved forms, previews and local login state; confirmed
orders/plans and saved policy snapshots remain server-side. The server's normal
freshness/idempotency checks remain authoritative after navigation.

Readiness links now preserve their destination within a section: for example,
legacy `/desk#apply-shortlist`, `/desk#execution-shortlist` and `/desk#strategy-setup`
links route into Strategies; the shortlist destination is
`/workspace#strategies/execution-shortlist`. Ordinary `/desk` continues to open
Dashboard. `/setup#feed-connection` opens Broker & Data with its connection step
expanded. After unlock/render, the
target section receives keyboard focus and the outer page scrolls it into view below
navigation. Quote-details links also expand their closed details panel. Repeated
links work without a section reload or repeated scrolling on polling. Section-change
guards, origin/window checks and shared in-memory access remain in force. Navigation
does not apply a shortlist or submit a mutation. Reload the full workspace to update
the parent navigation script; changing only the embedded section is insufficient.

Daily price-basis warnings now expose **Review today’s setup** directly, including
inside expanded Paper Trading quote details, when same-day data is ready. The button opens the
existing summary/unchecked confirmation; it does not navigate away, approve a review
or change a mode. Cancel preserves the blocker. Successful resolution hides the shortcut
on the next status update. Load this child-page addition by visiting another section
and returning to Paper Trading. Upgrade an older server to 0.15.0 as described above.

## Confirmations and compatibility

A shared native dialog positions its content in the visible portion of the iframe
before autofocus, and follows parent scrolling, resizing and visual viewport changes.
Long reviews scroll inside the dialog with the heading and actions visible. Initial
focus is on Cancel. Escape/Cancel clears the pending action and restores focus;
opening or cancelling never submits. The outer menu is inert during a confirmation.
If no usable visible intersection can be obtained, the review closes without submission;
return to the section and review again. If a submitted action times out, inspect saved
status/activity before retrying: closing or locking cannot undo a server-received action.

Old workspace hashes `desk`, `activity`, `console`, `setup` and `overview` resolve to
Dashboard, Trade History, Risk Management, Broker & Data and Learning Center. Old
`/desk` strategy/shortlist anchors resolve to Strategies. `/portfolio` still opens
Purchases & SIP, including `#purchase` and `#holdings-heading`; `/holdings` opens the
new read-only summary. Anchor changes and the two Portfolio subviews respect pending
request/dialog guards. Full reload is needed for a changed shell script. Restart an
older Python server with the launcher because 0.15.0 also adds routes/API code.

## What to do after unlocking

1. Read **Dashboard** for saved portfolio values, market/account status and the next
   action. Use **Paper Trading** for full readiness and mode controls. The contextual onboarding banner and **Learning Center** provide setup
   guidance. The launcher starts the UI without requesting a feed.
2. Open **Broker & Data**. Its overview distinguishes connected, requested and
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
6. During the relevant IST date, use **Risk Management** to review long-term symbols'
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

## Lightweight connection observation and feedback

The unlocked, visible workspace polls authenticated `/api/feed/status` every ten seconds, displays its observation time/accepted receipt age and labels connection status stale after missed checks. It does not load account tables or infer per-stock usability. Open Paper Trading to inspect complete readiness and Broker & Data for connection recovery. Errors/outcomes from the current same-origin section are bounded literal text in a dismissible action-feedback bar; Lock aborts the health request and clears late/private responses. Charts, loading, system theme and keyboard controls are described in [the UI guide](ui-experience.md).
