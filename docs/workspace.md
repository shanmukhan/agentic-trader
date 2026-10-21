# One workspace, one unlock, clear next steps

Version 0.11.0 adds a shared menu and an in-memory local unlock across its sections.
This is navigation/setup usability work; it does not add automatic stock selection
or automatic long-term entries.

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
The ordinary root URL routes to **Start here**. Legacy CLI callback URLs containing
a request token remain available for manual capture; handled UI login popups retain
their guarded callback handoff instead of becoming a navigation request.

## Menu and unlock behavior

| Menu | Purpose |
|---|---|
| Start here | Actual account mode, feed-request state, configured hours and quote-age limit; next steps and trading-frequency explanation |
| Trading console | Freshness/readiness, current-session long-term basis review, paper risk/exit controls and orders |
| Broker & feed setup | Broker session/login, catalog, symbol selection, reviewed calendar and explicit feed connection |
| Purchases & SIP | Manual long-term purchase previews/confirmations, recurring plan occurrences, holdings and original acquisition history |

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

## What to do after unlocking

1. Read **Start here**. It distinguishes *feed not started* from *requested but
   disconnected*, and shows the actual account horizon/automation state and hours.
   The launcher starts the UI without requesting a feed.
2. Open **Broker & feed setup**. In step 3, **Check saved broker session**. An available
   token can be expired. If renewal is required, disconnect a requested feed in
   step 6, open Zerodha login/2FA, then explicitly exchange the returned request token.
3. Step 4 shows the imported catalog and selected symbols. These are subscriptions,
   not profitable-stock recommendations. No need to reimport/resave an unchanged
   selection merely to connect. Preserve all held symbols; ETF costs remain unsupported.
4. In step 5, add the next confirmed NSE session with its reviewed date, opening/closing
   times and notice/reference. Ordinary cash-equity hours are 09:15–15:30 IST, but
   holidays/special sessions require their actual notices. Adding a future date does
   not open today's market. The form requires explicit review and confirmation.
5. In step 6, **Connect paper market data**, review the confirmation and refresh status.
   Connecting can resume existing pending fills/protective exits; it creates no new
   intent. A connected socket alone does not establish accepted quote freshness.
6. During the relevant IST date, use **Trading console** to review long-term symbols'
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

Long-term automatic model execution and broad profit-oriented stock discovery remain
pending; see [stock-selection-plan.md](stock-selection-plan.md). Do not interpret a
connected feed, a completed bar or an offline synthetic research rank as trading
approval or proof of profit.
