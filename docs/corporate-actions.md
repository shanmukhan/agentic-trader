# Reviewed corporate actions: LT2 engineering and usage

Version 0.6.0 adds **offline paper-account adjustments** for increasing stock splits,
bonus shares, dividend entitlements and explicitly reviewed net cash receipts. It
extends [long-term holdings](long-term.md). The command does not contact a broker,
registrar, bank or depository. Operator assertions are not verified real custody.

## 1. Try the complete invented lifecycle

```sh
.venv/bin/trading-agent corporate-actions-demo --directory data/corporate-actions-first
```

Use a new directory. This isolated fixture starts with fourteen virtual shares,
applies a two-for-one split, freezes a dividend on the resulting twenty-eight shares,
and later applies a one-for-three bonus. The final entitlement is thirty-seven whole
shares plus a **1/3-share claim**. The fixture restarts the account between actions,
exits the whole shares, records separate dividend/fraction receipts and retries each
operation to verify idempotency. Its final cash is **₹25,029.42**, realized capital
P&L **−₹20.98**, including **−₹0.11** from the fractional claim, and received net
dividend income **₹50.40**. All claims are resolved and no holding remains. These are
invented software assertions, not observed returns or profitability evidence.

The directory contains the account config/calendar/database, example action and
receipt JSON files, a summary and a private hashed `evidence/` report. Its dates,
notices, deductions and receipts must not be used for an actual account/session.

## 2. Establish the quarantine and preserve evidence

Before accepting the first ex-date quote, use the console's existing current-session
review with the checkbox **unchecked** and cite the known/unresolved action. The
symbol remains quarantined until a matching complete reviewed batch succeeds.
Another clear review cannot bypass quarantine. Keep the symbol in the feed universe.

Stop the service, preserve its database/WAL/sidecars according to the
[runbook](runbook.md), and generate a new evidence report:

```sh
.venv/bin/trading-agent --config config/long-term-session.toml long-term-report \
  --output data/before-actions-first
```

The report JSON includes `quarantines` and `quarantine_sha256` indexed by symbol.
Copy the **current symbol's hash** into the reviewed action batch. This binds the
batch to that unresolved review; it is not a signature or proof from the exchange.
Do not edit database metadata to clear quarantine, alter capital or fix mistakes.

The action and receipt commands require exclusive account ownership. A running
service prevents them from opening the database. They do not construct PaperBroker
or run its global restart cancellation. A rejected request leaves its journal,
positions, orders, claims and cash unchanged. Successful share/dividend batches
cancel pending orders for the affected symbol and release their reservations; other
symbols are preserved. Protective exit intent remains latched to the original
holding and requeues for its adjusted quantity after restart/polling.

## 3. Prepare one complete ordered batch per symbol and affected dates

Input is a regular, nonsymlinked UTF-8 JSON file of at most 64 KiB. Duplicate JSON
keys, extra fields, nonfinite values, naive timestamps and ambiguous numeric flags
are refused. Use decimal strings for cash. Use a new stable identifier for each
issuer action and batch; keep the same file for retries. There is no auto-retry or
automatic issuer-action downloader.

Template below: **replace every placeholder and all invented dates/amounts** with
reviewed values before applying it. This example combines a split followed by a
dividend quoted **per post-split share**:

```json
{
  "batch_id": "reviewed-batch-unique-id",
  "symbol": "NSE:REVIEWED_SYMBOL",
  "quarantine_sha256": "COPY_CURRENT_64_CHARACTER_HASH_FROM_REPORT",
  "reviewed_at": "2026-10-21T08:00:00+05:30",
  "reference": "reviewed complete issuer/exchange/credit evidence references",
  "covers_all_actions": true,
  "actions": [
    {
      "action_id": "reviewed-split-unique-id",
      "kind": "split",
      "ex_date": "2026-10-21",
      "record_date": "2026-10-21",
      "announced_at": "2026-10-19T12:00:00+05:30",
      "reference": "reviewed issuer split notice and credited shares",
      "numerator": 2,
      "denominator": 1,
      "credit_date": "2026-10-21"
    },
    {
      "action_id": "reviewed-dividend-unique-id",
      "kind": "dividend",
      "ex_date": "2026-10-21",
      "record_date": "2026-10-21",
      "announced_at": "2026-10-19T12:00:00+05:30",
      "reference": "reviewed dividend notice and total deduction evidence",
      "per_share": "2.00",
      "withholding": "0.00",
      "payment_date": "2026-10-28"
    }
  ]
}
```

`covers_all_actions` must literally be `true` after checking **all changes since the
last accepted price basis**, including offline days. At most twenty actions are
accepted in a batch. Actions must be in chronological ex-date order. Same-date order
is explicit: the engine applies each action to the quantity resulting from previous
ones. Verify whether an issuer's dividend/bonus ratio refers to pre- or post-split
shares. If that cannot be represented by this ordered workflow, retain quarantine.

For **split**, `numerator/denominator` means total new shares per old share and must
exceed one. For **bonus**, it means additional shares per existing share: `1/3`
means one new share for every three held, producing a total factor of `4/3`.
Ratios are strict positive integers, individually bounded to 10,000. Consolidations,
reverse splits, mergers/demergers, rights, symbol/token changes, spin-offs, elections
and external transfers are unsupported and must remain quarantined.

Ex-dates require sourced reviewed sessions in the configured calendar. Record date
must be on/after ex-date; share credit must be on/after record date. Applying share
actions waits until their reviewed credit date. Record/credit dates must already
have arrived when reviewed and applied; announcement must precede the review and
cannot be on a later IST date than ex-date. Future dividend payment dates are allowed
because they create receivables. Payment/credit dates are explicit reviewed inputs,
not dates guessed from a fixed settlement offset.

The paper entitlement comes from the unchanged virtual holding **before the first
ex-date**. It is not a reconstruction of settled demat eligibility. If the account
accepted an ex-date or later raw quote or fill for the symbol before adjustment,
the batch is refused. Preserve the source and reconstruct reviewed history in a
new account; do not retroactively alter past trades. Later batches must have a
strictly later ex-date than the symbol's previous batch. All same-date actions
therefore belong in the same ordered batch.

Run while the service is stopped:

```sh
.venv/bin/trading-agent --config config/long-term-session.toml apply-corporate-actions \
  --file /absolute/private/path/reviewed-actions.json
```

Success returns `paper_only: true`, `idempotent: false`, the complete reviewed input,
pinned sessions and before/after holdings/claims. An identical canonical input with
the same ID returns `idempotent: true` without writing another event. Decimal scale
differences such as `2` versus `2.00` do not create a new economic request. Reusing an
ID with changed input or reusing an issuer action ID in another batch is refused.

## 4. Understand share quantities, cost basis and fractional entitlements

Integral split/bonus changes preserve total capital cost and original holding
identity. Stops divide by the share factor and round **down** to the registered
tick; targets divide and round **up**. Zero/unrepresentable protective levels or
more than 2,147,483,647 resulting whole shares are refused. Dividend actions leave
stop/target prices unchanged; this is an explicit protective-policy choice.

A nonintegral entitlement credits only whole shares and creates an exact rational
fractional claim. Pro-rata capital basis allocated to that claim rounds down to
paise, with the **entire exact residual basis retained by the whole holding**. The
claim is not discarded, rounded into a tradable share, valued at a made-up market
price or credited as cash. Its unknown value makes portfolio valuation stale and
blocks new entries/portfolio peak and daily-loss updates. Individual usable-quote
stops/exits still protect whole shares. The claim survives selling all whole shares.

A fractional entitlement must be the final action in a batch. An unresolved
fraction for the same symbol blocks another batch until its cash receipt is reviewed
and recorded. This avoids inventing later benefits or transformations of a fraction.
Keep unsupported combined/fractional cases quarantined rather than dropping them.
Cost allocation is paper performance accounting, not statutory tax-lot treatment.

## 5. Understand dividends and record actual reviewed paper receipts

Dividend gross entitlement is `per_share × current reviewed paper quantity`.
`withholding` is the reviewed **total deduction for this account's entitlement**,
not a percentage or an automatic tax calculation. Both inputs use at most two
decimal places. Deduction cannot exceed gross. Net entitlement is an unpaid claim
and contributes to estimated equity, but **never available cash**. This keeps the
known dividend receivable visible across the ex-date price change. Peak/daily
references are not rebased or reset by applying actions.

Record each net dividend or fractional cash-in-lieu receipt separately, even if
the whole holding has already been sold:

```json
{
  "payment_id": "reviewed-receipt-unique-id",
  "claim_id": "reviewed-dividend-unique-id",
  "paid_date": "2026-10-28",
  "net_amount": "REPLACE_WITH_REVIEWED_EXACT_NET_AMOUNT",
  "reviewed_at": "2026-10-28T18:00:00+05:30",
  "reference": "reviewed net payment evidence; no credentials or private account numbers"
}
```

```sh
.venv/bin/trading-agent --config config/long-term-session.toml record-corporate-cash \
  --file /absolute/private/path/reviewed-cash-receipt.json
```

`claim_id` is the issuer `action_id`, not the batch ID. The dividend receipt must
equal its frozen net amount. A fraction receipt uses the explicitly reviewed net
cash-in-lieu proceeds; no price is inferred. A zero receipt is permitted only as
an explicit reviewed settlement (for example a fully withheld dividend); it is
never automatically assumed. Paid date must be on/after the claim's payment/credit
date and cannot follow the review or current IST date. Cash is booked when this
command runs; there is no retroactive daily-equity rewrite.

Dividend receipt moves known receivable to cash and records `income_received`
separately from trading capital P&L. Fraction receipt records net cash less its
transferred basis in `fraction_realized_pnl`, included in `realized_pnl`. Fees/DP
are not charged again for an issuer cash receipt. The same claim cannot be paid
twice with a new receipt ID. Identical receipt retries are read-only; changed input
with an existing ID is refused. If reviewed deduction/receipt assumptions prove
wrong, retain evidence and rebuild a corrected separate paper account; no arbitrary
cash override, reversal or deposit endpoint exists in this release.

## 6. Resume and inspect the account

After a successful batch, old symbol quotes/candles are invalidated. Restart the
service with the exact account config/calendar, record a **new current-session clear
review covering the applied batch**, and wait for a new usable quote whose exchange
time is strictly after the batch's application clock. No adjusted quote is invented.
Historical fills, original orders, action/receipt tables and audit events are retained.
Used session definitions cannot later change before startup recovery.

The console shows unpaid dividends, the number of unvalued fractions and received
dividend income separately from available cash. Corporate-action application and
cash recording are offline CLI operations; there is no action-upload browser form.
The ordinary review/holding-exit API remains authenticated as before.

Generate `long-term-report --output NEW_DIRECTORY` after stopping the service.
Report schema **2** includes full action batches, all claims, quarantine hashes,
known receivables, unknown-fraction counts, received dividend income and fractional
realized P&L. Completed-trade metrics include adjusted whole-share capital results;
dividend income and fraction receipts remain separately reported. Old marks are
still explicitly past observations. Startup/preflight/report independently replay
fills/actions/receipts and verify cash, quantities, basis, protections, fees, claims,
price boundaries, caches and journal/table agreement. Backup/restore preserves all
tables and metadata; use version 0.6.0 or later for an account containing LT2 evidence.

Reference behavior was reviewed on 21 October 2026 against
[NSE corporate-action filings](https://www.nseindia.com/companies-listing/corporate-filings-actions?symbol=NAZARA),
[Zerodha's ex/record-date explanation](https://support.zerodha.com/category/console/corporate-actions/ca-others/articles/what-does-ex-date-and-record-date-mean)
and [Zerodha's split/bonus explanation](https://zerodha.com/varsity/wp-content/uploads/2015/04/module1.pdf).
Issuer-specific notices and actual credit/payment evidence remain required. This
paper workflow does not implement real settlement, bank reconciliation, tax returns,
tax lots, automatically adjusted research history or a validated long-term strategy.

## Daily execution research integration (0.8.0)

LT3b reuses these exact action/receipt contracts in offline execution JSONL (`action`
with `batch`, `receipt` with `receipt`). Sourced calendars must match the daily data;
quarantine, complete reviewed batch/hash, post-application clear review and a new
quote remain mandatory. Portfolio replay retains original reviewed cash deductions
and actual receipt amounts, with independent reconstruction. Raw daily period
share/cash benefits must agree with applied effects; contradictory source bundles
cannot produce a finished artifact.

Independent labeling has a different quantity/account per candidate. Dividend or
payment events therefore censor affected active trials instead of copying a portfolio's
total deduction/payment; supported pure share actions can proceed, with unresolved
fractional claims excluding completion. The observer has no entitlement and is not
a traded portfolio. See [daily-execution.md](daily-execution.md) for full input/usage
and the remaining custody, historical costs and tax limitations.
