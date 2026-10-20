# Long-term paper investing: LT1 engineering and usage

Version 0.5.0 added a separate **long-term, long-only NSE cash-equity paper account**;
version 0.6.0 extends it with [reviewed corporate-action accounting](corporate-actions.md).
Holdings persist across closes, weekends and restarts. Entries remain explicit
operator hypotheses; the existing intraday rule/ML pipeline cannot automatically
trade this account. No real order, custody, withdrawal or settlement capability exists.
This is LT1 in the [extended plan](implementation-plan.md), not the original future
live-trading Phase 5. Further long-term milestones remain open.

## Supported behavior and boundaries

| Feature | LT1 behavior |
|---|---|
| Account separation | `investment_horizon = "long_term"`, separate database and port; no horizon conversion |
| Capital | Own virtual seed, unleveraged shares, exact Decimal accounting |
| Holding period | No 15:15 forced exit and no ordinary overnight kill |
| Entry | Manual candidate with stop/target, fresh quotes, reviewed session/raw basis and independent sizing |
| Position model | One open holding per symbol; partial fills, no averaging/SIP or tax-lot selection |
| Protective exits | Stop, target, operator holding exit, kill, daily loss and portfolio drawdown |
| Restart | Reconcile first, cancel old pending orders, restore persistent requested exits on polling |
| Delivery costs | Separate observed schedule, cumulative order fees, DP once per symbol/IST date |
| Corporate actions | Review/quarantine, offline reviewed split/bonus/dividend batch, separate net receipts and retained fractional claims |
| Portfolio risk | Durable observed peak, drawdown kill and opening-gap-aware daily reference |
| Automation/model | Existing intraday automation/research refused; no approved long-term strategy/model yet |
| Reports | Source-preserving ledger/DP/quarantine evidence, explicit past valuation and acceptance limits |

The supplied intraday and long-term configs each seed **their own** ₹25,000 virtual
account. Running both is not a shared ₹25,000 portfolio and does not implement a
combined capital/exposure cap. No inference about a real-money allocation follows.

## 1. Install and run the invented lifecycle drills

Use the existing Python 3.13.16 environment and frozen lock from
[how-to-use.md](how-to-use.md). No new dependency or frontend build is needed.

```sh
.venv/bin/trading-agent long-term-demo --directory data/long-term-first
```

Use a new directory. The command creates three independent invented accounts,
calendars, configs and private evidence folders:

- `overnight_restart`: holds through Friday/weekend, partially exits on Monday,
  restarts, restores the exit request and completes it without a second same-day DP fee.
- `opening_gap`: the first next-session price breaches daily loss; a later quote
  supplies the actual virtual liquidation. The loss is not hidden by rebasing.
- `corporate_action`: a reported action blocks a changed raw price, preserves the
  original cost/quantity and retains unresolved exposure in the report.

The independent final cash values are ₹25,379.54, ₹24,261.40 and ₹17,986.78 respectively.
The third account still holds fourteen shares; cash is not its total equity. These
values are deterministic software assertions from invented prices, not returns or
profitability evidence. Demo calendars/reviews must never be used for actual sessions.

## 2. Configure a dedicated account

Copy `config/long-term.toml` to a private working config, such as
`config/long-term-session.toml`. Set a new database path, reviewed calendar and up to
ten distinct actual instrument tokens. Keep all held symbols in the selected feed.
A nonempty selection omitting an existing holding is refused before restart cancellation.
The default listener is **127.0.0.1:8001**, beside intraday's 8000.

Engineering defaults: ₹250 planned per-trade risk, ₹500 daily loss, ₹2,500 observed
portfolio drawdown, ₹7,500 position notional, ₹20,000 total notional and five positions.
These are not investment recommendations. Size all related limits consistently when
changing capital. The common `flatten_at` field remains syntactically required but
never forces an exit for this horizon. Entry hours remain 09:30–14:30 IST and stop
fifteen minutes before an earlier reviewed close. Protective exits can fill during
any supported reviewed open session when usable quotes/liquidity arrive.

Load the private operator/Kite environment as described in the main guide. Initialize
and import the read-only instrument catalog before starting the feed:

```sh
.venv/bin/trading-agent --config config/long-term-session.toml init-db
.venv/bin/trading-agent --config config/long-term-session.toml instruments
.venv/bin/trading-agent --config config/long-term-session.toml preflight --strict
.venv/bin/trading-agent --config config/long-term-session.toml serve --stream
```

No `--automate`, `--rule-only` or `--model` flag belongs on this long-term service.
These intraday combinations are refused. Without `--stream` the console runs offline,
with entries blocked. Broker entitlement/access still require actual external checks.
Owning commands such as `status`, `verify-db` and `backup` require the service stopped
and perform restart cancellation. `preflight` uses read-only inspection instead.

Legacy accounts without a horizon marker are recognized as intraday only. Their
original policy-hash encoding remains unchanged. New long-term accounts bind horizon,
charge version, policy/schema, observed equity checkpoints and used calendar definitions.
A changed horizon/risk policy requires a new account; never edit metadata to convert it.

## 3. Review the price basis before processing each session

Open <http://127.0.0.1:8001>, unlock with the operator token and inspect the horizon
badge. The long-term panel shows observed peak/drawdown, a delivery fee buffer and
quarantined symbols. Select a registered symbol, current IST date and a review
source/reference. Check the confirmation only after reviewing splits, bonuses,
dividends, mergers, symbol changes and other intervening corporate actions since
the symbol's **last accepted quote**, including dates when the service was offline.
The audit captures that previous quote's timestamp and the used session definition.
A reference is evidence supplied by the operator, not automatic verification.
Do not enter broker credentials or personal account details in a reference.

A clear review is required separately for each symbol/date. New-session quotes are
rejected before replacing the last raw price or processing fills until this review
exists. Missing review leaves held valuations stale and blocks new entries. A fresh
accepted quote is still required after review; cached quotes do not regain trust.
Identical reviews are idempotent. Valid same-day source updates remain audited.

If an action is present or unresolved, leave the confirmation unchecked and record
the quarantine. The dialog explains that it persists across sessions. It cancels
pending buys, blocks new raw-price acceptance/fills and preserves holdings and exit
requests. A later clear review cannot remove it. **Do not attest “no action” to bypass
this block.** Preserve evidence and stop the service, then follow
[corporate-actions.md](corporate-actions.md) to apply a supported complete reviewed
batch and record separate cash receipts. Unsupported actions remain quarantined.
No split quantities, cash-in-lieu, dividend payment, deductions or raw price are inferred.

Equivalent authenticated request, replacing the placeholders before use:

```sh
curl --fail-with-body http://127.0.0.1:8001/api/paper/long-term/reviews \
  -H "Authorization: Bearer $TRADING_OPERATOR_TOKEN" \
  -H 'Content-Type: application/json' \
  --data '{"symbol":"NSE:REVIEWED_SYMBOL","session_date":"YYYY-MM-DD","no_corporate_action":true,"reference":"reviewed notice/evidence reference"}'
```

The boolean is strict; numeric/string substitutes and unknown fields return 422.
Wrong dates, unknown symbols, closed/unreviewed calendar dates, changed used sessions,
intraday accounts or attempts to clear quarantine return 409 without overriding risk.

## 4. Enter, supervise and exit virtual holdings

Use the existing `/api/paper/intents` schema from [api-contracts.md](api-contracts.md)
with a current aware decision time and reviewed symbol/stop/target. The operator
proposes the hypothesis; the engine chooses quantity and reserves fee-aware cash/risk.
No client quantity, short, leverage, position addition or cross-account transfer exists.
A pending entry expires after thirty seconds by default or at the entry/session cutoff.
An accepted order still needs a strictly later, adverse tick/depth-aware quote to fill.

Regular session closure, feed disconnect and startup do not themselves sell a
long-term holding. Monitor all held symbols: stale quotes block entries, mark values
as estimates and cannot execute exits. A stop/target can gap past its level overnight;
loss limits are triggers, not guaranteed loss caps. The server's watchdog remains
active while the browser is locked/closed. Locking the UI is not an exit request.

Use **Queue full paper exit** on an individual holding and confirm its symbol. The
request remains latched until that holding is closed, including across partial fills,
cancellation/replacement and restarts. Cancelling an exit order does not revoke this
protective intent; polling requeues its residual. Existing kill/flatten cover the
whole account. Queued exit is not completed liquidation.

```sh
curl --fail-with-body http://127.0.0.1:8001/api/paper/long-term/exit \
  -H "Authorization: Bearer $TRADING_OPERATOR_TOKEN" \
  -H 'Content-Type: application/json' --data '{"symbol":"NSE:REVIEWED_SYMBOL"}'
```

Repeated requests while held return the current pending order. Unknown/closed holdings
return 404. Quantity fields are refused. Actual fills require fresh reviewed quotes,
an open session, liquidity and sufficient virtual cash for incremental exit fees.

## 5. Costs, daily references and drawdown

The observed delivery schedule is `nse-delivery-observed-2026-10-20-v1`. It uses the
resident retail-individual NSE assumptions: zero brokerage, STT 0.1% each side,
buy stamp 0.015%, NSE transaction 0.00307%, SEBI ₹10/crore, IPFT ₹0.01/crore and GST
18% on taxable fees. The higher published DP amount, ₹15.34 including GST, is used
conservatively once per sold symbol/IST day. Rates were reviewed against
[Zerodha charges](https://zerodha.com/charges/) and its
[DP calculation guide](https://support.zerodha.com/category/account-opening/resident-individual/ri-charges/articles/what-do-dp-charges-mean)
on 20 October 2026. These are observed estimates, not effective-date guarantees or
contract-note reconciliation. Holder discounts, account-specific brokerage, auction/
settlement exceptions, personal taxes, AMC and other account-level charges are not modeled.

Variable charges accumulate per order with conservative paisa rounding. The first
sell fill books the day's DP charge atomically with cash, cost allocation, fill and
journal; additional same-day fills/orders do not book it again. A later day's partial
sale books another DP charge. Startup rederives delivery fill fees/day markers and
review/exit/quarantine evidence from the ledger/journal and refuses inconsistencies.

Available cash additionally keeps `max_positions × ₹15.34` as an entry-sizing fee
buffer (₹76.70 by default). This buffer is not a fee already paid. It reduces capacity
but does not change actual cash or double-count charged fees. Liquidation estimates
exclude a second same-day DP charge once paid. Extreme illiquid, low-price exits
spanning many days can exhaust cash for new DP fees: the fill remains blocked with
`INSUFFICIENT_EXIT_FEE_CASH`; no fake sale or negative cash is manufactured.

Each new reviewed session anchors daily P&L to the last fully trusted portfolio
observation before new quotes. Opening gaps remain included. This is an observed
reference, not an official exchange close. Only fully fresh portfolio observations update these checkpoints/loss gates; stale
or quarantined holdings block entries and delay portfolio marks. Individual reviewed
position stops/exits remain active. Peak equity persists across days/restarts;
long-term drawdown cannot be reset by waiting for another date. A breached drawdown
account remains preserved/killed for review. New policies/capital experiments use
separate accounts. No deposits/dividend adjustments are invented to reset a limit.

## 6. Reports, recovery and performance

Stop the owning service and preserve source evidence, then:

```sh
.venv/bin/trading-agent --config config/long-term-session.toml long-term-report \
  --output data/long-term-evidence-first
```

The source-preserving command does not construct PaperBroker or cancel pending
orders. A new private folder contains report JSON/Markdown, completed trades and a
last-written hash manifest. It records cash/fees/holdings, pending exposure, DP days,
quarantines, quote sources and last observed trusted equity. It does not call old
marks current. External/live/settlement flags always remain false. Follow the
[runbook](runbook.md) for verified backup/restore with this exact long-term config.

The 2,000-observation populated Mac benchmark held fourteen shares and measured
p99 **0.3288 ms**, with WAL/FULL durability, reviews, risk/valuation, clock/equity and
quote journaling. It excludes object construction, parsing, callback contention,
network/history and actual Pi behavior. Reproduce with:

```sh
.venv/bin/python scripts/benchmark_long_term.py --samples 2000
```

## Remaining long-term work

LT2 now provides reviewed split/bonus/dividend accounting, retained fractional
claims, separate receipts, atomic idempotency and independent reconstruction. Its
[detailed guide](corporate-actions.md) defines supported dates/ratios and exclusions.
LT3a now adds [completed daily data and causal screening](daily-research.md) with an
offline explanatory dashboard. LT3b now supplies [offline daily quote execution/ML](daily-execution.md)
with independent labels, chronological validation and later scored replays. This does
not enable connected long-term automation. LT3c portfolio allocation/SIP/rebalancing
remains pending. LT4 requires actual
read-only custody/sellable-holdings/settlement reconciliation and supervised evidence.
Corporate-action quarantine, custody and cash settlement are not automatically solved
by surviving a restart. Same-day protective virtual exits and immediately credited
paper sale cash are simulation simplifications, not actual product netting or T+1
settlement behavior. Original live phases remain separate after empirical acceptance.

## LT3c1 reviewed additions and SIP now available (0.9.0)

The new `/portfolio` page previews/explicitly confirms cash-budget buys and additions
on manual long-term accounts. Shared risk/cash/fees/DP and review authority still
apply; existing stop/target/opening identity cannot change. Original filled purchase
lots/costs appear separately from current adjusted pooled holdings. There is no
FIFO/tax or active per-lot attribution. Ordinary manual intents still reject duplicates.

SIP plans save explicit sourced session dates and a budget; each occurrence needs
its own review and confirmation, with no catch-up, deposit or automatic purchase.
Cancelled/partial/restarted attempts retain original IDs and consumed dates. Follow
[portfolio-contributions.md](portfolio-contributions.md) for UI, schemas, recovery,
calendar changes and the isolated `portfolio-demo`. Remaining LT3c work is reviewed
rebalance proposals and aggregate cross-account capital; LT4 custody/live gates remain.
