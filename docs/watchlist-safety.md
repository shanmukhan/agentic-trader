# NSE watchlist and account safety

Backend 0.21.0 and Android 1.1.0 add a persistent permission list and operator safety
overlay to connected paper accounts. These restrictions apply to manual intents,
strategy proposals, contributions and SIP purchases, including revalidation at fill.
They do not place real broker orders.

## Choose permitted stocks

1. Unlock the browser workspace and open **Watchlist**, or use the native Android
   **Watchlist** bottom tab. Stock Discovery remains under **More** in Android.
2. In **Broker & Data**, sign in to the read-only Kite service and import the NSE
   catalog if it is missing or old. Catalog import requires a disconnected feed.
   The picker searches saved NSE cash-market instruments with supported feed tokens;
   it is not a real-time exchange listing or an equity-share classification review.
3. Search a trading symbol, such as `RELIANCE`, and add/remove catalog results.
   Searches show at most 100 matches; narrow the query to find other symbols.
   Up to 3,000 distinct symbols may be saved. This does not raise the feed limit.
4. Review the exact replacement list and acknowledge its effects. Saving cancels
   **all pending buys**, releases their unfilled reservations and returns desk
   strategy decisions to manual mode. Existing filled quantities remain held.
5. Ensure the feed selection contains the permitted symbols you want to trade and
   every held symbol needed for valuation/protective exits. Apply the reviewed
   shortlist or change feed selection in Broker & Data while disconnected, then
   reconnect explicitly. Watchlist membership does not subscribe a stock, download
   its history, pass a research screen or start trading.
6. Review Paper Trading readiness and explicitly start Approval/Automatic if wanted.

The first connected CLI/API startup enables these restrictions with an **empty
watchlist**. Existing feed tokens and the official Nifty basket do not grant
purchase permission. After an upgrade, select permitted stocks before entering
new trades. Removing a held symbol makes it exit only: keep its feed subscription.
An empty list blocks every new purchase. Historical discovery can still show stocks
outside the list; runtime strategy buys and reviewed feed shortlist candidates are
restricted to permitted stocks. Held stocks are retained for exits.

Unsaved edits prevent navigation until discarded or reviewed. Cancel/Escape closes
a review without saving. A timeout/lost response never triggers an automatic retry:
refresh saved state and inspect the outcome. A stale revision returns HTTP 409;
refresh and review the current list again. Failed searches keep your edits. Locking
clears private browser/phone state. Neither unlocking nor resetting safety can arm
trading automatically.

## Entry safety rules

- **Order size:** the maximum purchase cash debit, including buy fees, is the
  lesser of available cash, 25% of current net liquidation equity (rounded down
  to paise), and existing position/exposure/risk budgets. No borrowing or short
  selling is supported. Pending buys are cancelled if their total paid plus
  remaining reserved cost exceeds a quarter of current equity before a later fill.
- **Five daily entries:** at most five accepted BUY intents per IST calendar day,
  across manual, strategy and contribution/SIP entry paths. A cancelled accepted
  intent still consumes its slot. Rejected intents, idempotent replays and partial
  fills do not add slots. Pending fifth entries may still fill. Protective and
  operator SELL exits are exempt from entry quotas, watchlist membership and the
  entry size cap; otherwise safety controls could prevent reducing exposure.
- **Drawdown:** fresh trusted valuations update a durable observed equity peak.
  Equity at or below 75% of that peak latches a pause and cancels pending buys.
  Price recovery, restart, a new IST day and ordinary kill-switch reset do not
  clear it. In manual mode, **Review drawdown pause reset** acknowledges the loss
  and establishes current positive reconciled equity as the new peak. Reset
  requires a current complete valuation. Existing kill-switch/daily-loss gates
  and the data lockout remain; select a trading mode separately afterwards.
- **Price integrity:** invalid instrument mapping/tick-size frames, conflicting
  duplicate/out-of-order updates and same-session volume regressions block new
  entries for the rest of that IST day. Invalid frames roll back their financial
  writes before the lockout is persisted separately. Valid later prices and
  restart cannot clear it. The next IST day removes only this daily entry block;
  all other checks still apply. Ordinary unchanged broker repeats are ignored;
  stale/missing prices and empty depth remain subject to existing freshness and
  liquidity gates. This is deterministic validation, not a general price-anomaly
  detector.
- **Ledger:** SQLite/accounting failures fail closed through the existing faulted
  account boundary. Preserve the database and investigate/reconcile it; do not
  edit or restore financial state to clear a safeguard. Drawdown reset independently
  reconciles the ledger before changing the reference.

External deposits and withdrawals are **not supported** by this application.
Contributions/SIPs buy from existing cash, and corporate-action income is investment
performance. There is consequently no external funding event to misclassify as a
loss in supported workflows. Do not simulate funding by editing SQLite. Adding
funding later requires an audited cash-flow ledger and flow-adjusted high-water
accounting before that workflow can be enabled; this release does not claim it.

The activation reference is at least starting cash and any existing trusted
long-term peak, plus current equity if its valuation is fresh. Earlier intraday
peaks cannot be reconstructed from missing historical observations. Peaks are
observed when runtime quotes/watchdog polling run, not continuously at the exchange.
These are additional conservative restrictions; earlier loss/position limits can
pause or liquidate the account sooner. A safety drawdown pause itself does not
force a sale; existing stop, kill-switch and session exits remain active.

## Authenticated API

The following example reads saved state only:

```sh
curl --fail --silent --show-error \
  -H "Authorization: Bearer $TRADING_OPERATOR_TOKEN" \
  http://127.0.0.1:8000/api/desk/watchlist
```

Use the configured port/public prefix for your server. GET
`/api/desk/watchlist/catalog?q=RELIANCE&limit=100` performs a literal,
case-insensitive symbol substring search. `%` and `_` are not wildcards.

After reviewing consequences, POST `/api/desk/watchlist` with
`{"symbols":["NSE:RELIANCE"],"revision":CURRENT_INTEGER,"acknowledged":true}`.
The revision comes from `safety.revision` in the GET response. Empty arrays are
valid. Symbols must be canonical imported `NSE:` identifiers with supported tokens;
unknown/duplicate/unsupported symbols are rejected without changing permissions.

POST `/api/desk/safety/resume` with
`{"revision":CURRENT_INTEGER,"acknowledged":true}` only after reviewing a latched
pause in manual mode. All mutations require authentication, an allowed browser
Origin when supplied, explicit boolean acknowledgement and the current revision.
Phone sessions use the same authenticated `/api/desk` controls. Responses report
saved permissions, feed-selection gaps, exit-only holdings, catalog import time,
entry count, reference equity, drawdown, valuation freshness and daily lockout.
GETs do not update peaks, expire proposals, save permissions or resume trading.

## Validation and acceptance

Unit, API/workflow, browser-controller and native UI regression checks were added.
**No test cases were run**, as explicitly requested on 31 October 2026. Only static
lint/format, syntax/type checks and compilation where recorded in the change log
are validation evidence. Invented fixtures are separate from real-market, broker,
phone-biometric and device acceptance. No deployment or APK publication is part
of this change. Isolated historical replay/backtests retain their declared input
universes and original bound research policies; the connected-account operator
overlay is not evidence that old research results simulated these new restrictions.
