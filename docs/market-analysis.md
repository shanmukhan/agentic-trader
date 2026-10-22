# Market & Analysis

Version **0.16.0** implements the Phase 4 price-research scope. **Stock Analysis**
now reads a separate immutable research series for Daily, Weekly and Monthly candles,
with 15 fixed-precision indicators, explicit warmup/gap states, share-action-adjusted
OHLC/volume, price drawdown and an optional traceable local benchmark comparison.
The chart range selector changes only displayed candles; indicator seeds retain the
full eligible history. **Stock Discovery** explains the existing screen's actual
observations, thresholds, missing evidence and deterministic ties without changing ranks.

Weekly/monthly completion requires a hash-bound calendar-completeness review;
no missing dates, prices or fundamentals are invented. The current preparation wizard
still downloads at most 60 completed sessions: SMA200 and longer-period indicators
need a separately reviewed longer bundle and otherwise show warmup. Benchmarks need
an explicitly supplied compatible artifact; fundamentals remain unavailable pending a
licensed source. New investment policies, browser backtest jobs and allocation/return
engines remain future work. Existing strategy/ML/risk identities and account authority
are unchanged. See [the research guide](investment-research.md) for commands, metadata,
coverage, failure/recovery and limitations.


The sidebar now names this screen **Stock Analysis** (`#analysis`). **Stock Discovery** (`#discovery`) separately filters and compares the existing saved research evidence; it does not alter feed subscriptions or provide unavailable fundamentals.

Market & Analysis displays saved price history and the prior-daily screening context
for the current account. It is read-only: opening a chart does not call Zerodha,
download data, change subscriptions, approve a review, activate a trading mode,
reserve cash or submit an order.

## Open a chart

1. Start the local UI with `./scripts/start_ui.sh`, open
   `http://127.0.0.1:8004/workspace` using the port shown by the launcher, and unlock
   with the local operator token. Select **Stock Analysis** in the sidebar.
2. Search for a stock in saved research or the subscribed shortlist. This is a
   bounded list, rather than a search of every catalog instrument. The research
   dataset can declare up to 500 symbols; the ordinary execution shortlist can
   add up to ten. A research stock need not have a live-feed subscription.
3. Select **Daily**, **Weekly**, **Monthly**, **1 minute** or **5 minutes**, then **Open chart**. Changing an
   existing stock or interval also loads that saved selection. **Refresh saved
   data** rereads local records; it does not fetch missing history. The page does
   not automatically poll the broker or server.
4. Inspect **Quote status** separately from the historical chart. A saved chart
   can remain visible while a quote is stale, disconnected, awaiting a current
   price-basis review or absent because that research stock is not subscribed.
   The displayed reviewed exchange session alone cannot prove quote usability.
   Quote usability is explicitly labeled **at last refresh**, rather than a live
   assertion. It grants no trading authority; execution rechecks its own current
   quote, review and risk requirements.

The standalone `/analysis` address opens the shared workspace. The operator token
stays in memory and is handed only to the same-origin section. Locking clears the
selection, prices, chart, table and research context; a late response cannot
restore the locked content. This page has no purchase or approval controls.

## Research intervals and source compatibility

The browser uses `GET /api/research/series` for Daily/Weekly/Monthly, and the
unchanged `GET /api/analysis` for 1/5 minute candles. The legacy API's daily raw
OHLC/SMA response remains available for compatible clients. Research adjusts each
contiguous segment to its last known share units, before aggregation; dividends
only enter its separate gross total-return index. Do not compare raw and adjusted
absolute levels without their basis. See [exact formulas and calendar/benchmark
artifacts](investment-research.md). Minute behavior and trading features are unchanged.

**Chart range** selects the latest 50, 100 or all returned candles, without a request,
new calculation or changed seed. The drawing uses approximate coordinates; exact
decimal values and availability are in the accessible table. Overlay lines break
at missing-history segments. No research value is a trade signal or fill price.

## Legacy saved history and indicators

The following describes the retained raw-price `/api/analysis` resource, rather than
the new browser research series.


**Daily** uses the currently installed reviewed `DailyDataset`. Bars appear only
when their declared exchange session has completed and both the price availability
and basis-review timestamps are at or before the server observation time. The input
files must retain their installed hashes before and after reading. Missing history
and changed or invalid files produce an explicit empty/unavailable state.

**1 minute / 5 minutes** use the existing account's saved completed candle records.
They do not synthesize an unfinished candle from the latest quote. The read examines
at most 600 recent rows for the selected interval and returns at most 300 candles.
Incomplete candles, future interval ends, gaps and unknown initial cumulative volume
are excluded. Exclusions within that bounded read are counted. It does not fill
missing intervals or assume that an excluded zero-volume record means no trading
occurred. Malformed saved chart records show an unavailable state without repairing
the data or changing the paper account.

The candlestick drawing shows raw open, high, low and close, with saved volume below.
Teal means close at or above open; red means close below open. The blue SMA 20 and
amber SMA 50 average the available raw closes. An average stays absent until its
full number of available bars is present. They can span missing intervals and do
not certify a continuous exchange history. The bounded intraday read can also
leave an early moving average unavailable. A chart is not adjusted by inventing
prices for splits, dividends or other corporate actions.

Drawing coordinates use approximate browser numbers. Expand **Accessible candle
data and moving averages** for the exact saved decimal OHLC and SMA values, volume
in shares and timestamps displayed in IST. This table is the accessible alternative
to the SVG chart. At most 300 candles appear, newest first in the table.

**Screening context** shows the existing prior-daily research result, its last
completed session and calculation time: rank/status, configured momentum-period
gross return, volatility, average turnover and exclusion reasons. These are separate
from the raw-price chart and current quote. Gross analytical total returns may
include explicitly reviewed period benefits, whereas chart SMAs use raw closes.
A candidate is not a buy signal, order, backtest, expected return or ML validation.
No score or performance series is invented when a screen is unavailable.

## Recovery and limitations

- **No stocks configured:** finish broker setup and strategy preparation. Importing
  the full instrument catalog alone does not select stocks for this view.
- **No daily history:** prepare genuine history in **Strategies**, review the source,
  calendar and policy, then explicitly install it. Yesterday's installed download
  is not refreshed merely by opening this screen.
- **No completed minute candles:** connect market data in **Broker & Data** and
  wait for complete, quality-checked intervals. A connected feed is not proof of
  usable quotes or historical-data entitlement.
- **Unavailable saved data:** inspect the local source records and prepare/review
  replacement data through the existing setup workflow. The chart will not repair,
  bypass review or silently download a substitute.
- **Display stale / read timeout:** the quote snapshot is marked stale after six
  seconds without a successful refresh, and a failed read marks the display stale.
  Historical candles remain visible. Quote labels always refer to the last
  refresh, and the timer additionally marks that snapshot stale. The displayed
  values are retained as stale;
  select **Refresh saved data** to retry. Authorization failure clears private
  content and requires a new unlock. There is no automatic action retry.
- **Route unavailable after an update:** stop the old server in its owning terminal
  with Ctrl+C, then run `./scripts/start_ui.sh`. Reloading a page cannot load a new
  Python endpoint into an existing process.

Daily source and synthetic flags are declarations in the reviewed dataset, not
independent market acceptance. Stored minute candles have no per-candle broker or
replay provenance field: the API returns `source.synthetic: null` and the page says
that provenance is not certified. A chart cannot establish that those bars came
from a real broker session. Simulated tests of this screen do not constitute
real-market, broker, device or execution acceptance.

## Read-only API

`GET /api/analysis?symbol=NSE:INFY&timeframe=1d` requires the existing bearer operator
authorization. `timeframe` accepts `1d`, `1m` or `5m`. Omit `symbol` to use the first
saved subscribed symbol, then the alphabetically first saved research symbol if no
subscription exists. Only the server's saved research/subscribed symbol whitelist
is accepted; an unknown symbol returns 404 and malformed input returns 422. No
request accepts a filesystem path, broker credential, custom price or write action.

The response includes `schema_version`, `observed_at`, selected `symbol`/`timeframe`,
bounded `symbols`, separate `quote` status/prices/subscription, `bars`, `bar_limit`,
`truncated`, `excluded_candles`, `data_state` (`available`, `missing`, `unavailable`),
recovery `message`, declared `source`, prior daily `screen`/`screen_as_of`/`policy`,
`market_session_open` and `limitations`. OHLC/SMA prices are decimal strings; unavailable
averages are null. Daily bars additionally expose `available_at`. Intraday source
kind is `stored_completed_candles`; daily kind is `installed_reviewed_daily`.

Validation uses invented saved datasets and candles. Unit/functional coverage checks
availability and completion filtering, exact decimal SMA arithmetic, bounded reads,
quality exclusions, integrity/malformed-data recovery, authorization/whitelisting,
and independent full SQLite dumps proving GETs preserve cash, orders, fills,
holdings and pending approvals. UI checks cover safe text rendering, exact table
values, real empty/stale/provenance states, search, timeout, lock and late responses.
