# Phase 2: strategy research and backtesting

Version 0.2 adds two deterministic long-only rule hypotheses and an isolated,
quote-driven backtester. These are research tools. The connected service continues
to use operator paper intents. ML and automatic strategy use on the feed are later
milestones; there is no live execution adapter.

## Quick start

```sh
.venv/bin/trading-agent research-demo --directory data/research-first
.venv/bin/trading-agent backtest data/research-first/dataset \
  --strategy config/strategy.toml --output data/research-second
```

The demo needs no network or broker credentials. It creates a synthetic dataset and
an independent virtual account. Two invented sessions produce one winning and one
losing round trip: default final cash **₹24,974.03**, charged estimated fees **₹20.27**,
net P&L **−₹25.97**. This tests both outcomes and is not empirical strategy evidence.
The synthetic/sample gates remain false, and `ready_for_live` is always false.
Use new output directories; existing ones are never overwritten.

`backtest` and `research-demo` never open or modify the service paper account. Global
`--config PATH`, placed before the command, supplies the risk policy; the account
database is replaced by a new path under the research output. The dataset supplies
its own explicit calendar and universe.

## Predeclare a hypothesis

Copy `config/strategy.toml`, choose parameters before inspecting results, and pass
the copy with `--strategy`. This release does not search parameters, choose winners
or select stocks using future returns. Every configuration is hashed in the report.

Both rules require completed, contiguous five-minute candles starting at the declared
session open; session-local VWAP; rising EMA; Wilder ATR; prior-bar relative volume;
turnover/price/volatility controls; and fresh bid/ask depth. The default EMA/ATR period
is 14 and volume lookback is five **prior** candles. Active candles and future bars
never enter the features. A default limit of one candidate per symbol/session counts
even a risk-rejected candidate, preventing automatic repeated attempts.

| Hypothesis | Additional trigger |
|---|---|
| `opening_range_breakout` | Previous completed close ≤ the first fifteen minutes' high, then completed close > that high after the opening interval |
| `vwap_continuation` | Previous candle low ≤ its EMA (pullback), followed by completed close above the previous high, above VWAP and with rising EMA |

Defaults include volume ≥1,000, close×volume turnover ≥₹1,000,000, relative volume
≥1.2, price ₹10–₹10,000, ATR 5–300 bps, spread ≤30 bps and quote-to-close distance
≤50 bps. These are illustrative engineering assumptions, not tuned parameters or
investment recommendations. The full configuration is included in each report.

Stop is completed close minus 1.5×ATR, rounded down to instrument tick. Target is
close plus 2×(close−stop), rounded up. The paper risk engine then accepts/rejects
and sizes the candidate, including costs. Rules supply no quantity and cannot
override kill, cash, exposure, session, freshness, daily loss or streak limits.
The candidate's existing `model_version` field identifies the rule/config version;
it does not indicate an ML model.

A missing opening candle, skipped interval or quality flag disables the symbol for
the remaining session. The next declared session resets VWAP, range, warmup and
candidate count. There is no silent rewarm using truncated session history. Unknown
sessions, premature/duplicate candles and off-grid prices fail explicitly. Each
symbol has independent bounded state.

## Dataset format and causality

A bundle contains `manifest.json` and `events.jsonl`. No executable model, pickle,
Python expression, archive or remote URL is loaded. The manifest includes schema
version, source/data notes, strict boolean synthetic label, raw **unadjusted** price
basis, one to ten unique cash instruments and reviewed session dates/times/sources.
The synthetic label is a producer declaration, not authenticity verification.

```json
{
  "schema_version": 1,
  "source": "operator-reviewed capture reference",
  "data_notes": "Raw price basis and coverage reviewed; exclusions recorded",
  "synthetic": false,
  "price_basis": "unadjusted",
  "instruments": [{"symbol":"NSE:EXAMPLE","token":1,"tick_size":"0.05"}],
  "sessions": [{"day":"2026-10-20","open":"09:15:00","close":"15:30:00",
                "source":"reviewed calendar reference"}],
  "events_file": "events.jsonl"
}
```

The instrument/date are schema examples, not confirmed exchange data. Use the demo
for complete synthetic records or export reviewed observations. The manifest is
limited to 1 MB; individual lines are read with a 64 KiB bound. Symlinked manifest
and event files, arbitrary event paths, malformed/unknown fields, manual candidate
events, unknown symbols/tokens, unreviewed dates and naive clocks are rejected.

Every record has an aware `time`: when information becomes available to the agent.
Records must be chronological; equal-time events retain file order. Both completed
candle and quote records are required. Supported types:

| Type | Payload and time |
|---|---|
| `connection` | Strict boolean `connected`; clears strategy quote cache |
| `quote` | Domain Quote with symbol/token, exchange/receipt time, last, bid/ask, sizes, cumulative volume, source; availability cannot precede exchange or receipt |
| `candle` | Completed 5m domain Candle; availability ≥`start+5m` |
| `clock` | Time passage; watchdog can cancel/request exits but cannot fill |
| `kill` | Persistent virtual kill; no automatic reset event |

See demo JSONL for all fields. At each candle event only already-processed quotes
and past completed candles are accessible. The default signal-age limit is five
seconds after candle close. A candidate can fill only on a **strictly later exchange
quote**, even with zero configured latency. Tests verify that future quote changes
cannot change prior signal decisions.

Historical OHLCV does not specify executable spread/depth or the order of intrabar
highs/lows. The backtester therefore refuses candle-only input and never invents
tick paths, fills at the signal close or assumes which barrier won. Only observed
quote events trigger/fill stops and targets. Held-position quote gaps, stale
valuations and bad candle continuity make results incomplete. Missing intratick
moves remain unknown. Do not mix split-adjusted candles and raw quotes; review or
exclude corporate-action sessions and record point-in-time universe selection.

The official [Kite history contract](https://kite.trade/docs/connect/v3/historical/)
defines OHLCV; the [quote contract](https://kite.trade/docs/connect/v3/market-quotes/)
includes depth and exchange timestamps. Exported history assumes candles were
available at their close, not at their later download time. This is a research
assumption and does not reproduce publication delay or later data revisions.

## Export local observations

Stop the service to release its exclusive database ownership. The exporter opens the
database without constructing an execution engine, so it never cancels source
orders or changes balances. It exports market data, not earlier manual trades.

```sh
.venv/bin/trading-agent export-research \
  --start 2026-10-20T09:15:00+05:30 --end 2026-10-20T15:30:00+05:30 \
  --symbols NSE:INFY --source 'reviewed local capture reference' \
  --output data/dataset-reviewed
```

Replace the illustrative date/symbol with reviewed captured data. The range is
`[start,end)` and a final clock event is appended at `end`. Quote journal entries
merge with stored 5m candles. Quotes precede candles at equal times; original quote
order and calendar references are retained. Replay/mixed/unknown quote origins
remain synthetic; only exclusively `kite`-labelled quotes permit a non-synthetic
declaration. The exporter does not independently authenticate that provenance.

For legacy manual-source stream candles with initial-volume/gap flags, provide a separately verified raw
historical Candle JSONL file with `--candles PATH`. Do not clear quality flags or
overwrite ledger tables. The override must be sorted/unique by `start,symbol` and
completed; it is copied into the bundle. Produce it through the existing read-only
historical adapter after manual login, serializing each candle's `model_dump_json()`.
Respect current API entitlements/rate limits and the documented request ranges.

Supervised Phase 4 sources instead preserve first recorded candle receipt times
and connection events, including late backfill and outages. Missing observation
records fail rather than assuming close availability. External candle overrides
are refused for these accounts. Offline export sorts delayed bars by availability,
then bar time/symbol within ties; source orders and journal remain unchanged.

A mid-session feed capture cannot establish full-session strategy history. The
exporter cannot recover absent quotes or feed connection events, validate corporate
actions, or remove selection bias. These assumptions are in manifest notes. A failed
export leaves no loadable manifest; inspect the partial folder and choose a new path.

## Read the results

| Artifact | Contents |
|---|---|
| `report.md` | Human summary, observed results and limitations |
| `report.json` | Exact metrics, gates, runtime, strategy/policy/code/input/journal hashes |
| `decisions.jsonl` | Candle features, filter reasons, generated candidate and risk result |
| `trades.jsonl` | Completed position round trips, quantity, turnover, fees, net P&L |
| `equity.csv` | Event-by-event estimated liquidation equity, cash/reservations and freshness |
| `paper.sqlite3` | Independent durable fills, accounting and strategy-evaluation journal |
| `run.json` | Finished research status or failed run with sanitized error class |

Maximum drawdown uses the running **observed** liquidation-equity peak, initialized
at starting cash. Expectancy, win rate and profit factor use completed net round
trips after fees. No-loss profit factor is `null` with an explicit status; no-trade
ratios are also `null`. Partial exits count once when the position completes. Open
trades remain in the snapshot and are excluded from completed-trade statistics.

`complete` means flat at end without detected candle/quote-quality problems. It
does not imply profitability or sufficient evidence. The provisional sample gate
requires twenty observed sessions and thirty completed trades. Passing it or a
non-synthetic declaration is not out-of-sample validation. Rule-only runs contain no
optimizer, training split, annualized Sharpe or live approval. Phase 3 adds a separate
[chronological ML workflow](ml-research.md), including held-out validation and
optional `backtest --model` scoring on a later dataset.

The current observed charge schedule applies to all simulated dates; historical fee
matching is explicitly **not verified**. Results are estimates, not reconstructed
contract notes. Queue competition, price impact and unobserved extremes remain
unknown. Compare explicit assumptions in new output directories and retain adverse
results as well as favorable ones. Input/config hashes distinguish experiments.

Kill state persists within a run and is never reset automatically between sessions.
Dataset exhaustion never fabricates liquidation; unresolved positions/orders remain
recorded and make the run incomplete. Invalid/changed input fails the run without a
success report. Input hashes are rechecked after processing.

## Checks and performance

```sh
.venv/bin/pytest tests/backtesting tests/functional/test_research_commands.py
.venv/bin/python scripts/benchmark_strategy.py --output benchmark.json
```

Rule analysis retains bounded per-symbol indicator/volume windows and performs
constant work per candle. The [Mac baseline](benchmark-strategy-macos.json) measured
approximately **0.018 ms p99** over 2,000 evaluations per hypothesis. Object
construction, file decoding, disk, network and execution/risk transactions are
outside that timer. See [performance.md](performance.md) and [test-plan.md](test-plan.md).

With `--model`, candidates at the same availability timestamp are ranked by score,
then symbol/intent as deterministic tie breaks, before the next timestamp's data is
processed. The independent broker rechecks model context and risk. Model/feature
hashes, probabilities, ranks and risk reasons extend `decisions.jsonl`. Data must
start after completion of the model's validation data/session plus embargo. The full model usage
and artifact contracts are in [ml-research.md](ml-research.md).

For later supervised feed validation, use a separate dedicated account and the
[Phase 4 guide](paper-feed.md). Backtest output is not automatically attached to a
connected service or treated as operational approval.

## Long-term scope boundary (0.5.0)

The existing backtester/rules describe intraday hypotheses. They reject a long-term
policy before creating output; the connected intraday controller/model is likewise
unavailable for delivery accounts. Overnight paper lifecycle drills are not validated
investment strategies. Completed daily/total-return data, corporate-action-aware
labels, portfolio allocation and long-term ML/research are later extended milestones.
See [long-term.md](long-term.md) and [implementation-plan.md](implementation-plan.md).
