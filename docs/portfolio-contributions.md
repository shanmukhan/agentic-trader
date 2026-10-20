# Reviewed paper purchases, holding additions and SIP plans

Version 0.9.0 delivers **LT3c1**, the contribution foundation of LT3c. It adds
cash-budget purchases/additions, original acquisition history, explicit-session SIP
plans and a responsive authenticated review UI. Python 3.13.16 and the existing
`.venv` remain recommended; no dependency was added.

LT3c is split into auditable dependencies: contributions/SIP first, reviewed
rebalancing proposals next, then shared capital coordination across accounts.
Only LT3c1 is complete here. Rebalancing, cross-account spending enforcement,
deposits/withdrawals, FIFO/tax-lot ownership and live orders remain unavailable.

## 1. Run the isolated lifecycle

From the repository root:

```sh
uv sync --frozen --all-extras
.venv/bin/trading-agent portfolio-demo --directory data/portfolio-first
```

Choose a new output directory. The example uses invented 20–21 October 2025
sessions/quotes and its own account. It explicitly confirms two SIP occurrences,
adds to a holding, partially fills another purchase, restarts/cancels its residue,
then exits six shares on a later quote. Four original acquisition lots remain.
Expected cash is **₹25,273.45**, fees **₹22.35**, net capital P&L **₹273.45**.
These numbers verify deterministic software/accounting, not an investment edge or
historical fee accuracy. No configured service account or broker session is opened.

Artifacts: private `paper.sqlite3`, `report.json`, `report.md`, `sessions.csv`,
`preview.toml` and last-written `manifest.json` with hashes. A separate private
`preview.sqlite3` working copy is deliberately excluded from the frozen evidence
manifest. Serving it can change recovery/checkpoint metadata without rewriting the
original evidence. There is no automatic overwrite or experiment resume.
If the prepared workspace preview includes `data/portfolio-preview/operator.env`,
that mode-0600 file contains its private local UI token. Copy its token into the
unlock field or source it in your own shell; keep it private. It is ignored by Git
and excluded from frozen financial evidence. `portfolio-demo` itself never creates
an operator credential or starts a service.

To inspect the new UI using the working copy, set a private operator token of at
least 32 characters using the main guide, then run:

```sh
.venv/bin/trading-agent --config data/portfolio-first/preview.toml serve
```

Open <http://127.0.0.1:8003/portfolio> and unlock with that token. Its invented
historical calendar/feed intentionally provides no current entry readiness. You can
inspect orders, original acquisition costs and the cancelled plan. Do not present
those replay prices as current market data. Stop the process before reusing its
working DB from another command. Generated absolute config paths need updating if
the directory moves. The frozen source account should stay untouched.

## 2. Open the account contribution page

For a separately configured manual long-term account:

```sh
.venv/bin/trading-agent --config config/long-term.toml serve
```

Open <http://127.0.0.1:8001/portfolio>, or use the link in the main console's
long-term safeguards panel. With an existing read-only feed, retain its normal
`serve --stream` setup. The page uses the same private bearer token, held only in
that tab's memory. Locking clears the token, private values/forms, preview/dialog
and pending response authority. No token is placed in a URL, cookie or browser storage.

This is responsive **desktop/mobile browser UI**, not a native app. It has keyboard
labels/focus, touch-sized controls, explicit dialogs and exact decimal money display.
The main console retains safeguards, reviews, kill/flatten and full-holding exits.
Intraday/automated/model-bound accounts cannot use the contribution endpoints.
Physical-phone and pixel acceptance remain pending; automated UI behavior is tested.

## 3. Preview and confirm one purchase

Ensure the registered instrument, current sourced session, clear corporate-action
review, fresh accepted quotes, cash and risk prerequisites from
[long-term.md](long-term.md). A page refresh alone cannot make an old quote fresh.

1. Enter the symbol, maximum cash debit and review reference. The budget includes
   buy fees; whole-share sizing may use less. It spends existing virtual cash.
2. For a **new holding**, enter reviewed stop and target prices. For an **addition**,
   leave them blank to retain the existing holding's stop/target. Providing different
   levels is rejected. No stop is loosened or target changed by adding shares.
3. Select **Calculate server preview**. It reserves nothing and shows quantity,
   maximum debit, per-share price cap, planned risk and stop/target. Blocked previews
   list reasons and create no order. Resolve those conditions and preview again.
4. Review the values and select **Review and confirm paper purchase**. The dialog
   repeats the quantity/symbol/debit and execution conditions. Confirm explicitly.
5. Inspect **Purchase orders** for accepted/partial/filled/cancelled state, actual
   debit and reserved remainder. Acceptance is a reservation; fills need a later
   exchange quote, latency, usable depth and all continuing checks.

The preview hash binds the quote, protections, holding, cash/exposure/risk, policy
and SIP context. A changed or stale preview cannot execute. Quotes typically expire
within five seconds under the default account policy; the page's six-second display
age limit is an additional UI gate, not an extension of quote validity. Refresh and
review when necessary. The page does no client-side sizing or financial approval.

Each request has a stable intent ID. A successful retry with the same request and
original approval returns the current original order even after fill, cancellation
or restart. Changed instructions under the same ID fail. Double confirmation never
creates another order. If the response is uncertain, refresh and inspect the intent
in **Purchase orders** or the main console before starting a different purchase.
There is no automatic retry. An explicit rejected/expired preview can be reviewed
again; **Start a different purchase** deliberately begins a new instruction.

Risk still limits aggregate existing-plus-added position value, total exposure,
available cash after reservations/DP buffer, remaining daily capacity, per-trade
risk and maximum positions. Buy fees fit inside the cash cap. Existing holding
value consumes position room; this is not a fresh position allowance for each lot.
Quotes/capacity are checked again during fills. A changed capacity can cancel the
remaining contribution rather than overspend. Kill, drawdown/loss, stale/quarantined
basis, a pending buy, a pending sell or a latched holding exit blocks additions.
The ordinary manual-intent route still rejects entries into an existing position.

## 4. Save and review recurring SIP occurrences

Expand **Create a plan with reviewed exchange dates**. Enter a unique plan ID,
symbol, cash budget per occurrence, protection percentages for a future new holding,
increasing comma-separated session dates and a source/review reference. Review the
save dialog. Supported bounds: 1–120 unique dates, 32 active plans, 1,000 retained
plans per account; budgets are positive paise values up to ₹10 million, subject to
the account's smaller actual limits. Dates must be current/future on creation.

Every date must explicitly exist in the sourced account calendar. There is no
monthly holiday roll-forward, inference that an absent date is a holiday, or future
funding assumption. Choose the reviewed dates yourself. Frequency may be monthly
or another explicitly reviewed sequence. A plan is a saved instruction template;
it neither reserves future cash nor authorizes unattended purchases.

On a due IST date, select **Preview due [date]**. The server supplies the occurrence
ID and fixed plan budget. Its form fields stay read-only; use **Start a different
purchase** for an unrelated manual instruction. A new holding's stop/target derive
from the current ask and the saved reviewed percentages, conservatively tick rounded.
An existing holding keeps its current levels, including applied share adjustments.
Inspect the exact preview and confirm that occurrence separately.

Only one confirmed purchase attempt per plan/date is permitted. A preview that is
blocked consumes nothing and can be reconsidered that day. A recorded accepted
order consumes the occurrence even if it later partially fills, expires, is cancelled
or is recovered after restart. No automatic remainder retry or catch-up occurs.
Unattempted past dates show **MISSED**; future dates show **UPCOMING**. There is no
backdated occurrence execution. Each occurrence can spend less than its budget.

**Cancel plan and pending buys** requires confirmation. Cancellation atomically
cancels its still-pending buys and releases their residual reservations; filled
shares retain their existing protections. Unattempted occurrences show cancelled.
Cancellation is permanent; saving the same ID cannot reactivate it. Use a new
reviewed plan ID for changed instructions. Already-used IDs are idempotent only
for identical plan values. Historical filled attempts remain visible.

Active plan session definitions are checked on restart. To revise a future calendar
definition, cancel the affected plan while its original calendar is available,
update/review the calendar and save a new plan. Used account sessions remain pinned
by the existing long-term ledger even after plan cancellation.

## 5. Read current holdings and acquisition history correctly

**Current aggregate holdings** shows current shares, pooled cost basis, protection
levels and estimated unrealized P&L. **Acquisition history** groups original BUY
fills by purchase order, including ordinary older entries, contribution additions,
SIP occurrences and partially filled/cancelled orders. Original cost includes actual
buy fees; actual debit and remaining reservations are separate. The latest 100
orders/lots and at most 64 plans display with truncation notices where applicable.
All records remain in the private ledger.

Original purchase quantities/prices do not change when later sales or corporate
actions change current holdings. A split can make current shares exceed original
acquired units; a sale can leave fewer. These historical records are not active
per-lot ownership, sellable custody quantities or FIFO/tax gains. The shared ledger
continues pooled proportional basis allocation for partial sales, with the final
sale taking the exact residual. Dividends and fractional claims remain separate
LT2 entitlements. See [corporate-actions.md](corporate-actions.md).

## 6. API contracts

All routes use authenticated loopback/origin checks and no-cache responses from
[api-contracts.md](api-contracts.md). HTTP 409 reports incompatible accounts, stale/
changed approval or plan conflict; HTTP 422 reports invalid typed inputs. No public
account data is embedded in either static HTML shell.

| Route | Input / result |
|---|---|
| `GET /portfolio`, `/portfolio.js`, `/money.js` | Static local page/assets; no account values |
| `GET /api/paper/portfolio` | Current account, bounded original lots/orders and plan occurrence states |
| `POST /api/paper/portfolio/preview` | `Contribution`; read-only proposal, reasons, decision and SHA-256 |
| `POST /api/paper/portfolio/contributions` | `Approval` with exact request and reviewed preview hash; atomic paper order |
| `POST /api/paper/portfolio/plans` | `SIPPlan`; immutable idempotent schedule |
| `POST /api/paper/portfolio/plans/cancel` | `plan_id`, review `reference`; permanent cancellation |

Example manual request (fictional symbol/prices, not a recommendation):

```json
{"intent_id":"reviewed-purchase-1","symbol":"NSE:DEMO","budget":"2000.00","stop":"490.00","target":"600.00","reference":"private reviewed experiment"}
```

For an addition, omit stop/target. Post the request to `/preview`, inspect the
returned exact decision, then submit:

```json
{"request":{"intent_id":"reviewed-purchase-1","symbol":"NSE:DEMO","budget":"2000.00","stop":"490.00","target":"600.00","reference":"private reviewed experiment"},"preview_sha256":"REPLACE_WITH_THE_REVIEWED_64_HEX_HASH"}
```

Plan example: `plan_id`, `symbol`, `budget`, `sessions` as increasing ISO-date array,
`stop_pct`, `target_pct` as decimal strings, and `reference`. An occurrence request
also includes its plan ID/date and deterministic server-issued intent ID; use the
request returned in the due-plan view. Mutated budgets, dates or reserved IDs fail.

## 7. Persistence, recovery, speed and limits

Orders, contribution proof and occurrence identity commit in one writer transaction.
Additive tables `portfolio_requests` / `sip_plans` and `portfolio_schema=1` retain
immutable source instructions, reviewed economic previews, created/cancelled events
and a unique plan/date constraint. Startup and `verify-db` independently reconstruct
authority, hash/economic/order linkage, acquisition basis before first addition fill,
later fill clocks/price caps, fees, pooled positions, cash, actions and claims.
Deleting/corrupting proof or silently adding via an unreviewed new BUY order fails.
Read-only preflight also verifies these records without recovery or table creation.

Existing accounts gain compatible empty tables/indexes on their next owning open;
cash, policy limits and intraday risk hashes are not reset. Restart cancels pending
entry residue and preserves filled shares and existing exit latches. It never resumes
SIP authority or changes an occurrence ID. Keep verified backups and source reports.
After a consistency failure, preserve the damaged evidence and restore a verified
backup; do not delete proof, adjust cash or clear accounting metadata to force startup.

[Captured Mac timing](benchmark-portfolio-macos.json), after 1,000 journaled quotes:
1,000 exact preview calls p50 **0.1388 ms**, p99 **0.1784 ms**; twenty reviewed
holding additions plus next quote/fill p50 **1.3517 ms**, p99 **1.5532 ms**. FULL WAL
durability stays enabled. Initialization, baseline buys/exits, network/browser/Pi
are excluded. Reproduce with `python scripts/benchmark_portfolio.py --samples 1000`.
The quote path performs indexed contribution lookup only for pending buy processing;
plan/history reconstruction stays outside routine quote polling.

No new broker client, signal model, deposit/funds transfer, automatic monthly service,
tax-lot valuation, rebalance execution or cross-account pool is introduced. Each
account still owns its independently seeded virtual cash. Real custody/settlement,
historical fee applicability, market profitability and device acceptance remain open.
Next: LT3c2 reviewed rebalance proposals, then LT3c3 aggregate capital coordination.
See [implementation-plan.md](implementation-plan.md).
