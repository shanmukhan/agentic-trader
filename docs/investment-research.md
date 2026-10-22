# Saved investment price research

Version 0.16.0 adds causal daily, weekly and monthly price research. It reads a saved
daily bundle; it does not download history, open an account database, connect a
broker, install a strategy, change selected stocks or authorize an order. The
existing strategy, rank, holding cap, risk, ML and execution identities are unchanged.

This is the implemented price-analysis portion of Phase 4. Licensed fundamentals,
new investment policies, portfolio construction and a new backtesting engine remain
separate work. Indicators describe evidence; they are not profit probabilities.

## Run an isolated report

Use an existing [reviewed daily bundle](daily-research.md) containing
`manifest.json` and `daily.jsonl`. Choose a symbol declared by its universe and an
explicit timezone-aware observation clock. The directory after `--output` must be
new and outside the input bundle:

```sh
.venv/bin/trading-agent investment-analyze /absolute/path/reviewed-daily-bundle \
  --symbol NSE:INFY \
  --as-of 2026-10-22T16:00:00+05:30 \
  --timeframe 1d \
  --output /absolute/path/new-investment-report
```

`--timeframe` accepts `1d`, `1w` or `1mo`, defaulting to `1d`. The clock is an input,
not a request to acquire prices for that date. Saved prices, membership and basis
reviews unavailable at that clock are excluded. A naive clock, unknown symbol,
invalid or changed input, existing output or output inside the source is refused.
The CLI exits unsuccessfully and prints a sanitized failure message; fix the source
or arguments and retry with a new output directory. It never repairs source files.

The optional inputs are local evidence files:

```sh
.venv/bin/trading-agent investment-analyze /absolute/path/reviewed-daily-bundle \
  --symbol NSE:INFY \
  --as-of 2026-10-22T16:00:00+05:30 \
  --timeframe 1w \
  --context /absolute/path/investment-context.json \
  --benchmark /absolute/path/investment-benchmark.json \
  --output /absolute/path/new-weekly-report
```

The CLI accepts explicit paths. Without them, it discovers `investment-context.json`
inside the bundle; that context can bind the fixed `investment-benchmark.json`
sidecar. An unbound benchmark is not downloaded or guessed. If a context declares a
benchmark hash, an explicit benchmark must match it too. A context whose review is
not yet available cannot activate its benchmark configuration.

Success writes `report.json` with the complete calculation and metadata, a brief
`report.md` describing its scope, and `manifest.json` containing exact SHA-256 hashes
of both report files. The snapshot identity binds source/context/benchmark hashes,
calculation file hashes, versions, symbol, interval and as-of clock. The new output
directory is private; report files use private permissions. The finished manifest
is written last after source integrity is checked again. Failure can leave a partial
output directory: without a finished manifest it is not a completed report. Preserve
it for diagnosis or remove it yourself, and retry under a new directory name.

## Read it in Stock Analysis

Open **Stock Analysis**, select a saved stock and choose daily, weekly or monthly
research. Source, basis, completed-history coverage, warmup and unavailable
dependencies are part of the result. A historical candle is not a live executable
quote. Read the latest included session and missing-session count before using an
apparently populated chart.

The keyboard-accessible candle table includes exact SMA200 and historical price/segment
drawdowns. Missing legacy/minute values are explicitly unavailable. The chart range
selector changes only displayed rows and never requests data or recalculates seeds.

The authenticated `GET /api/research/series?symbol=NSE:INFY&timeframe=1w` reads the
installed daily research bundle using the server clock. It accepts no filesystem
paths or arbitrary as-of clock; browser evidence uses only the fixed sidecars above.
It cannot acquire data or change account/authority/order state. It calculates the
entire eligible series before clipping displayed history, so changing the visible
range does not restart EMA or other seeds. Metadata reports computed/displayed bar
counts and truncation. With no installed history, prepare data in **Strategies**;
the page does not create history on opening. Invalid saved evidence returns a
sanitized HTTP 503; review the files and refresh. Unknown stocks return HTTP 404 and
unsupported query intervals are rejected.

The existing `GET /api/analysis` remains the legacy raw-history/quote analysis
contract. Its raw prices and older analysis conventions are not relabelled as this
adjusted series. This read-only research endpoint does not replace quote freshness,
current-day price-basis review or independent execution risk checks.

## Price and availability conventions

Daily input is raw OHLCV with explicit reviewed share and cash benefits. For each
consecutive eligible segment, known supported share actions convert earlier OHLC
into the segment's latest share units: all four prices are divided by the cumulative
new-shares/old-share factor, and volume is multiplied by that factor. Original
`raw_open/high/low/close` and `raw_volume` remain available on daily rows. Cash
dividends do not change adjusted OHLC or volume.

A separate gross analytical total-return index starts at 100 in each segment:
`I[t] = I[t-1] * (share_factor[t] * raw_close[t] + cash_per_previous_share[t]) /
raw_close[t-1]`. It assumes same-close reinvestment before fees, investor tax or
payment delays. It is neither a tradable price nor credited account cash. A split
or cash benefit assertion in a source bundle is not proof that an account received
that benefit. Missing/unsupported action evidence requires source review, not a
guessed adjustment.

Earlier adjusted bars inherit the availability of later share actions used in that
as-of calculation. Their original gross-return history retains its separate
`tri_available_at` dependency clock. `indicator_available_at` includes every input
since the current segment seed. Later eligible actions can therefore restate an
earlier adjusted chart at a later as-of; they cannot become earlier executable
prices. Future or unavailable rows do not affect an earlier snapshot's bars.

Missing/unavailable reviewed sessions, membership exclusion/re-entry and other
segment breaks reset every rolling window, recursive seed and segment drawdown.
Missing evidence stays missing; no price, return or holiday is forward-filled.
Prospective constituent snapshots retain their survivorship limitation and do not
establish historical point-in-time membership.

## Calendar coverage and complete periods

Weekly periods run Monday–Sunday; monthly periods use calendar months in IST. OHLCV
is first open, maximum high, minimum low, last close and summed volume, after share
adjustment. A label/time is the last actual included session, including a reviewed
early close. Weekly/monthly warmup counts completed aggregate bars, not daily bars.

Completion requires every declared reviewed session in that period, eligible input
availability and explicit calendar coverage from period start through period end.
Holidays, cross-year coverage and early closes come from the reviewed input; no
weekday or Friday/month-end assumption supplies a missing session. A current period
with future reviewed closes is partial. Missing input makes a period incomplete;
unverified coverage makes it unavailable. These periods are listed with reasons and
excluded from completed research candles and indicator warmup. A first week/month
whose start is outside reviewed coverage is excluded too.

Optional `investment-context.json` is bounded to 128,000 bytes. Its exact schema is:

```json
{
  "schema_version": 1,
  "dataset_sha256": {
    "manifest.json": "<64 lowercase hex characters for the exact manifest bytes>",
    "daily.jsonl": "<64 lowercase hex characters for the exact daily bytes>"
  },
  "calendar": {
    "start": "2026-01-01",
    "end": "2026-12-31",
    "available_at": "2026-01-01T08:00:00+05:30",
    "reference": "Your actual reviewed calendar source and coverage reference",
    "completeness_reviewed": true
  }
}
```

Replace the hash placeholders with SHA-256s of the unchanged files; do not copy the
illustrative coverage or clocks as evidence. For example, inspect exact hashes with
`shasum -a 256 /absolute/path/bundle/manifest.json /absolute/path/bundle/daily.jsonl`.
Coverage must describe the actual reviewed range and when that assertion was
available. `completeness_reviewed` requires boolean `true`, not a string or number.
To bind a benchmark, add top-level `"benchmark_file": "investment-benchmark.json"`
and `"benchmark_sha256": "<its exact 64-character SHA-256>"` together.

A hash binds an assertion to files; it does not certify the assertion. If both the
manifest and prices omit a session, matching dates alone cannot establish a holiday
or externally complete history. Incorrect calendar declarations require corrected,
reviewed evidence and a new snapshot, not invented rows. Duplicate JSON fields,
nonfinite values, invalid context bindings, symlink inputs and source mutation are
refused.

## Indicator definitions and warmup

Formula identity is `investment-indicators-v2.1`. Calculations use a private
34-significant-digit Decimal context with `ROUND_HALF_EVEN`; display rounding does
not feed execution. Each latest indicator includes its definition, basis,
availability, value, state and reason. Unavailable/warming values are `null`, never
zero. Percent fields use `1` for one percent and volatility is not annualized.

| Fields | Definition | First valid consecutive bar |
| --- | --- | --- |
| `sma20`, `sma50`, `sma200` | Arithmetic mean of the last 20/50/200 closes | 20/50/200 |
| `ema12`, `ema26` | Seed with the first 12/26-close SMA; then `alpha=2/(n+1)` | 12/26 |
| `rsi14` | Wilder arithmetic seed of 14 close gains/losses, then Wilder updates | 15 |
| `macd` | SMA-seeded EMA12 minus EMA26 | 26 |
| `macd_signal`, `macd_histogram` | SMA-seeded EMA9 of MACD; histogram is line minus signal | 34 |
| `atr14` | Wilder mean of max(high−low, abs(high−previous close), abs(low−previous close)) | 15 |
| `support20`, `resistance20` | Minimum low/maximum high of the prior 20 bars; current bar excluded | 21 |
| `drawdown_pct`, `max_drawdown_pct` | `100*(close/segment peak−1)`; most negative segment value | 1 |
| `volatility20_pct` | Population standard deviation of 20 simple close returns, multiplied by 100 | 21 |

RSI is 50 for flat gains/losses, 100 when only loss is zero and 0 when only gain is
zero. ATR requires a previous close for every true range; no first-bar substitute
shortens its warmup. These drawdowns and volatility use share-adjusted closing
prices, excluding cash dividends, and are not account-return or TRI metrics.

The existing preparation flow's 60-session history is insufficient for SMA200.
Monthly SMA200 needs 200 completed months, potentially many years of explicitly
reviewed history. Selecting monthly does not acquire that history. Short bundles
retain visible warmup limits; changing a chart range cannot manufacture a seed.

## Optional benchmark declaration

The local benchmark JSON accepts exactly these top-level fields and row fields:

```json
{
  "schema_version": 1,
  "series_id": "invented-gross-index-v1",
  "title": "Invented schema example; not market evidence",
  "provider": "Synthetic fixture author",
  "source_url": "https://data.example.org/invented-benchmark",
  "license_reference": "Fixture-only declaration; not a provider entitlement",
  "currency": "INR",
  "return_type": "gross_total_return",
  "synthetic": true,
  "published_at": "2026-10-21T16:00:00+05:30",
  "available_at": "2026-10-21T16:01:00+05:30",
  "rows": [
    {
      "session": "2026-10-21",
      "level": "100.000000000000",
      "close_at": "2026-10-21T15:30:00+05:30",
      "available_at": "2026-10-21T16:01:00+05:30"
    }
  ]
}
```

This invented one-row example illustrates syntax only and cannot supply a
20-interval comparison. Real evidence needs an identified source and permitted use;
the adapter does not verify entitlement, provider authenticity, publication history
or storage/redistribution rights. `source_url` must be a public HTTPS provenance URL
without credentials, query, fragment or IP-literal host; it is never fetched.

Files are limited to 8,000,000 bytes and 1–10,000 unique chronological rows. Levels
are positive plain decimal strings, at most 28 significant digits and 12 decimal
places; numeric JSON values, exponent notation, nonfinite or zero levels are
invalid. All clocks must be aware; declaration availability cannot precede
publication, and each row availability cannot precede its actual close. The close's
IST date must match its session. Future rows remain excluded. Reads refuse
symlinks/nonregular files, duplicate keys and concurrent mutation.

The comparison requires compatible gross total-return INR series, matching source
synthetic/real declarations and 21 complete matched daily levels for 20 intervals,
even when viewing weekly/monthly candles. It uses
`100 * ((stock_last/stock_first)/(benchmark_last/benchmark_first) - 1)`, with final
percentage display rounded to 12 decimal places. This is relative wealth growth,
not subtraction of the two percentage returns. A price or net-return benchmark is
recognized as a declaration but unavailable for this gross-return comparison.
Missing/mismatched dates, segment breaks, unavailable configuration or insufficient
history produce a reason and `null` relative strength. No missing benchmark is
replaced with a synthetic Nifty series or a zero return.

## Validation scope

The indicator suite has 26 synthetic arithmetic/validation tests; the independent
series suite has 34 tests. Fixtures cover exact warmups, independent Fraction
references, split/dividend effects, raw/adjusted separation, causal clocks and
future-input perturbation, gaps/membership, reviewed periods, early closes and
cross-year boundaries, hash/schema/symlink refusal, immutable sources, ambient
Decimal isolation and independently checked persisted report hashes. The full release passed **828 Python tests**, **157 UI tests**, Ruff and mypy
(104 source files), with **92.38%** statement coverage. The change also includes
benchmark, authenticated API/CLI and UI checks; see the
[test plan](test-plan.md) and [changelog](CHANGELOG.md) for recorded final results.

Synthetic tests establish implementation behavior, not source licensing,
historical availability, real broker/device/browser acceptance, investment
performance or future profitability. No real order or market-data acceptance is
implied by a completed research report.
