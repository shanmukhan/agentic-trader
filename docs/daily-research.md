# Completed daily research and dashboard: LT3a usage

Version 0.7.0 adds an **offline research screen**, reviewed completed daily data and
point-in-time universe membership. It does not open a trading account, place orders,
simulate fills, validate a model or change paper risk policy. LT3a is the first
dependency of LT3; daily execution research/ML and portfolio/lot management remain
later work in [the plan](implementation-plan.md).

## 1. Generate the invented example

```sh
.venv/bin/trading-agent daily-research-demo --directory data/daily-research-first
```

Use a new directory. Open `data/daily-research-first/report/index.html` in a browser.
The report is self-contained; it needs local JavaScript but no network, server,
token or frontend build. `report.json` and `report.md` remain readable without JS.
The demo creates its own `dataset/`, `report/` and summary; it never opens the
configured service database. Its ninety weekday sessions and 538 bars are invented,
including holiday assumptions, splits, distributions and membership notices.

The six-symbol fixture deliberately displays different results:

| Invented symbol | Expected explanation |
|---|---|
| `NSE:TREND` | One research candidate; reviewed split/dividend do not create artificial raw-price losses |
| `NSE:DECLINE` | Screened out for nonpositive trailing return/below trend |
| `NSE:THIN` | Screened out for insufficient average turnover |
| `NSE:GAPPED` | Latest session missing; needs data |
| `NSE:REENTRY` | Re-entered universe; fifteen consecutive observations cannot satisfy the default history |
| `NSE:EXITED` | Outside the historical universe rather than silently deleted |

No return forecast or actual investment success is implied by these invented data.

## 2. Read and use the dashboard

The header states provenance, the explicit analysis clock in IST and the latest
**declared** completed session. The screen never labels an old dataset current just
because analysis ran today. Summary cards count candidates, symbols and data gaps.
Every result shows its status and the actual rule/data reason. Candidates have a
deterministic research rank; unqualified/missing/excluded symbols remain unranked.

Use **Find a symbol**, **Show status** and **Sort results** to inspect the table.
**Clear filters** restores all rows and keyboard focus to search. Empty results
explain whether filters hid rows or no reviewed session had completed. The table
has semantic column headers and a keyboard-focusable horizontal scroll region on
small screens. Controls have accessible labels, visible focus and touch-sized targets.
Source/policy/coverage and limitations expand beneath the results. No buy/arm/control
button exists in this research artifact. It has no live refresh or connection to
the operator console. Keep private source references out of reports you share.

Displayed analytical values round to two decimals using browser number formatting;
`report.json` preserves full Decimal strings. Very large values retain their string
representation instead of being shown as Infinity. This formatting is separate from
the execution console's exact-money display. Browser logic renders untrusted values
as text; embedded JSON is escaped and scripts/styles use a restrictive hash CSP.

## 3. Prepare a reviewed dataset

A bundle contains exactly named `manifest.json` and `daily.jsonl` inputs. Input files
and the bundle directory cannot be symlinks. The manifest is bounded to 2 MB; bars
to 256 MB, with 64 KiB maximum JSONL records. Duplicate JSON keys, extra fields,
nonfinite values, unordered/duplicate rows, unknown dates/symbols and invalid OHLC
are rejected. Daily bars are **unadjusted raw prices**, with explicit reviewed period
benefits. Do not supply an already future-adjusted close and then apply benefits again.

Example manifest structure (one session is valid but insufficient for default
twenty/fifty-session windows; provide the complete reviewed history):

```json
{
  "schema_version": 1,
  "source": "reviewed daily data source/version reference",
  "notes": "reviewed completeness, availability, universe and price-basis assumptions",
  "synthetic": false,
  "price_basis": "raw-with-explicit-period-benefits",
  "bars_file": "daily.jsonl",
  "sessions": [
    {"day":"2026-10-20","open":"09:15","close":"15:30","source":"reviewed exchange session reference"}
  ],
  "universe": [
    {"symbol":"NSE:REVIEWED_SYMBOL","effective_session":"2026-10-20","included":true,
     "known_at":"2026-10-19T12:00:00+05:30","reference":"reviewed historical membership notice"}
  ]
}
```

Sessions must be unique and chronological, with valid local IST open/close times.
Up to 5,000 sessions, 500 distinct symbols and 10,000 membership transitions are
supported. Each symbol's membership must start with inclusion and then alternate
include/exclude on strictly increasing reviewed session dates. Every notice must
be knowable before its effective session opens. Include historical removals and
re-entries; a list of today's survivors is not point-in-time evidence. Historical
membership/exclusion applies per bar, and re-entry restarts the history window.

Each JSONL line has the following shape; write it as one line:

```json
{"symbol":"NSE:REVIEWED_SYMBOL","session":"2026-10-20","open":"500.00","high":"510.00","low":"495.00","close":"505.00","volume":100000,"price_available_at":"2026-10-20T15:40:00+05:30","basis_reviewed_at":"2026-10-20T15:35:00+05:30","basis_reference":"complete reviewed intervening benefits reference","share_numerator":1,"share_denominator":1,"cash_per_previous_share":"0"}
```

Rows must increase by `(session date, symbol)`. Prices are positive finite Decimal
values, up to four decimal places; volume is a strict nonnegative integer. Ratios
are explicit positive integers up to 10,000; numerator cannot be below denominator
in this schema. Cash distribution is a nonnegative finite Decimal, up to four
places. Each of these benefit fields is required even when its value is 1/1 or 0.
Both clocks must be aware. `price_available_at` cannot precede the reviewed close.
Effective availability is the later of price receipt and basis review; the row is
unavailable before then. A source claiming `synthetic:false` is still an operator
assertion, not verified provenance. Incomplete benefit review must not be passed as
a clear 1/1, zero-distribution period.

`share_numerator/share_denominator` is the **total new share factor** across the
preceding-to-current daily period, not an additional-bonus ratio. A one-for-three
bonus is factor `4/3`; a two-for-one split is `2/1`. Cash is specified **per previous
period share**, including any same-period action sequence conversion. Review this
unit carefully. Mergers, rights, reverse splits, symbol transformations and ambiguous
benefit chains are not represented by this schema. Reject/reconstruct those inputs
outside this tool. LT2 account action records are not automatically daily research data.

## 4. Choose an explicit historical clock and fixed policy

```sh
.venv/bin/trading-agent daily-analyze /absolute/path/reviewed-daily-bundle \
  --as-of 2026-10-20T16:00:00+05:30 \
  --policy config/daily-research.toml \
  --output data/reviewed-daily-first
```

The output must be a new directory outside the source bundle. No source database,
broker environment or operator token is required. Invalid inputs/naive clocks fail
without a completed output manifest. Existing directories are refused. Failed output
can be retained for investigation; it must not be treated as finished evidence.

The supplied fixed research policy uses twenty-session momentum/volatility/turnover,
fifty-session trend mean, ₹1 crore minimum mean turnover and 5% maximum observed
daily volatility. These are unvalidated screening hypotheses, not optimized strategy
parameters or recommendations. Policy windows accept 2–252 sessions; requirements
are `max(momentum_sessions + 1, trend_sessions)` consecutive included observations.
Different policies require a new output so unfavorable experiments remain visible.

Only declared completed sessions and records knowable by `--as-of` are used. Future
rows cannot alter those features/ranks, although full input validation/hashes still
describe the supplied bundle. Missing or unavailable sessions break a symbol's
window; no forward-fill, skipped-session comparison or imputed price is inserted.
If the latest declared completed session is missing, that symbol needs data. Review
`calendar_age_days` and calendar completeness; the tool cannot discover omitted
exchange sessions/holidays or independently verify availability clocks.

## 5. Interpret the analytical calculations

For a consecutive period, with raw closes `C_previous`, `C_current`, reviewed total
share factor `F` and reviewed cash per previous share `D`:

`gross wealth factor = (C_current × F + D) / C_previous`

An index beginning at 100 compounds those factors. This analytical total-return
index assumes distributions are reinvested at that same close, ignoring payment
delay, fractional execution, withholding, brokerage and other costs. It is **not**
the LT2 paper account's cash/settlement behavior or realized investment return.
The first bar anchors the index and has no invented preceding return.

- Trailing gross total return is the index change over the momentum window.
- Trend is the trailing arithmetic mean of the index, including the completed bar.
- Daily volatility is population standard deviation of the observed gross daily
  returns in the momentum window; it is not annualized or a guaranteed risk bound.
- Average turnover is mean raw `close × volume` in that window, a liquidity proxy.

A research candidate must have positive trailing return, index at/above trend mean,
adequate average turnover and observed volatility within policy. Only candidates
rank, descending by trailing return with symbol ties. A candidate is not an approved
signal. OHLC cannot reconstruct order path, bid/ask depth or an executable fill.

## 6. Evidence, speed and remaining work

Outputs are private `report.json`, self-contained `index.html`, `report.md` and a
last-written hash `manifest.json`. Inputs are hashed and checked for changes before
the manifest is written. The report includes source notes, policy, Python code digest,
data-quality counts, statuses/reasons and permanent false live/model/execution flags.
The artifact manifest also protects the generated UI contents against inconsistency.

```sh
.venv/bin/python scripts/benchmark_daily.py --samples 30
```

The captured Mac sample processes 538 bars/six symbols/ninety sessions with loading,
validation, rolling calculations, ranking and input/Python hashes: p50 **8.0033 ms**,
p95 **15.2105 ms**, maximum/p99 **20.4069 ms** over thirty runs. Input creation,
HTML writing, network/history, execution and actual Pi are excluded. Windows have
bounded state; membership lookups use binary search. Analysis remains outside the
connected quote process, and this small fixture is not a large-universe guarantee.

LT3b still needs quote-executed daily strategy research and separate chronological
ML validation. LT3c needs lots/SIP additions, reviewed rebalancing and aggregate
capital controls. Real data acquisition, empirical acceptance, custody and all live
phases remain open. See [implementation-plan.md](implementation-plan.md).
