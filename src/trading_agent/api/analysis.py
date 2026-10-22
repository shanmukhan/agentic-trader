"""Read-only, bounded chart views of saved reviewed data; never fetch or trade."""

from collections import deque
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Literal

from fastapi import Depends, HTTPException, Query
from fastapi.responses import HTMLResponse

from trading_agent.execution.quote_status import quote_status
from trading_agent.market_data.calendar import IST
from trading_agent.models import Candle, stamp, utc

BAR_LIMIT = 300
CANDLE_READ_LIMIT = 600
Timeframe = Literal["1d", "1m", "5m"]


class UnknownAnalysisSymbol(ValueError):
    pass


def _averages(bars: list[dict[str, Any]]) -> list[dict[str, Any]]:
    windows: dict[int, deque[Decimal]] = {20: deque(), 50: deque()}
    totals = {period: Decimal(0) for period in windows}
    for bar in bars:
        for period, window in windows.items():
            close = Decimal(bar["close"])
            window.append(close)
            totals[period] += close
            if len(window) > period:
                totals[period] -= window.popleft()
            bar["sma" + str(period)] = (
                str(totals[period] / period) if len(window) == period else None
            )
    return bars


def _daily_bars(research: Any, symbol: str, now: datetime) -> list[dict[str, Any]]:
    dataset = research.dataset
    if dataset.fingerprints() != dataset.hashes:
        raise ValueError("reviewed chart input changed")
    sessions = {session.day: session for session in dataset.manifest.sessions}
    bars: list[dict[str, Any]] = []
    for bar in dataset.bars():
        session = sessions[bar.session]
        end = datetime.combine(session.day, session.close, IST)
        if bar.symbol != symbol or end > now or bar.available_at > now:
            continue
        bars.append(
            {
                "time": stamp(end),
                "session": bar.session.isoformat(),
                "open": str(bar.open),
                "high": str(bar.high),
                "low": str(bar.low),
                "close": str(bar.close),
                "volume": bar.volume,
                "available_at": stamp(bar.available_at),
                "quality": "reviewed_raw_daily",
            }
        )
    if dataset.fingerprints() != dataset.hashes:
        raise ValueError("reviewed chart input changed while reading")
    return _averages(bars)


def analysis_snapshot(
    desk: Any,
    now: datetime,
    *,
    symbol: str | None = None,
    timeframe: Timeframe = "1d",
    include_history: bool = True,
) -> dict[str, Any]:
    """Read existing source records without polling engines, refreshing or granting authority."""
    now = utc(now)
    e = desk.engine
    with e.lock, e.db.transaction() as tx:
        research = desk.research
        result = research.result if research else None
        tokens = desk.execution_tokens
        selected = (
            {
                row[0]
                for row in tx.execute(
                    "SELECT symbol FROM instruments WHERE token IN ("
                    + ",".join("?" for _ in tokens)
                    + ")",
                    tokens,
                )
            }
            if tokens
            else set()
        )
        research_symbols = (
            {member.symbol for member in research.dataset.manifest.universe} if research else set()
        )
        # The validated dataset declares at most 500 symbols; execution adds at most ten.
        allowed = selected | research_symbols
        options: list[dict[str, Any]] = [
            {
                "symbol": item,
                "subscribed": item in selected,
                "daily_history": item in research_symbols,
            }
            for item in sorted(allowed, key=lambda item: (item not in selected, item))
        ]
        symbol = symbol or (options[0]["symbol"] if options else None)
        if symbol is not None and symbol not in allowed:
            raise UnknownAnalysisSymbol("Choose a stock from the saved shortlist or research data.")
        current_quote = None
        minute_bars: list[dict[str, Any]] = []
        excluded = 0
        candle_error = False
        if symbol is not None:
            quote = e._quote(tx, symbol)
            current_quote = {
                **quote_status(e, tx, symbol, now),
                "subscribed": symbol in selected,
                "last": str(quote.last) if quote else None,
                "bid": str(quote.bid) if quote else None,
                "ask": str(quote.ask) if quote else None,
                "source": quote.source if quote else None,
            }
        if symbol is not None and timeframe in {"1m", "5m"}:
            minutes = 1 if timeframe == "1m" else 5
            cutoff = now - timedelta(minutes=minutes)
            rows = tx.execute(
                "SELECT payload FROM candles WHERE symbol=? AND minutes=? AND start<=? "
                "ORDER BY start DESC LIMIT ?",
                (symbol, minutes, stamp(cutoff), CANDLE_READ_LIMIT),
            ).fetchall()
            for row in reversed(rows):
                try:
                    candle = Candle.model_validate_json(row[0])
                except ValueError:
                    candle_error = True
                    minute_bars = []
                    break
                if (
                    candle.symbol != symbol
                    or candle.minutes != minutes
                    or not candle.completed
                    or candle.start + timedelta(minutes=minutes) > now
                    or candle.quality != "ok"
                ):
                    excluded += 1
                    continue
                minute_bars.append(
                    {
                        "time": stamp(candle.start),
                        "session": candle.start.astimezone(IST).date().isoformat(),
                        "open": str(candle.open),
                        "high": str(candle.high),
                        "low": str(candle.low),
                        "close": str(candle.close),
                        "volume": candle.volume,
                        "quality": candle.quality,
                    }
                )
    bars: list[dict[str, Any]] = []
    data_state = "missing"
    message = "No saved history for this stock. Prepare and review strategy data in Strategies."
    if symbol is None:
        message = "No stocks are configured. Connect a broker and prepare strategy data first."
    elif include_history and timeframe == "1d" and research and symbol in research_symbols:
        try:
            bars = _daily_bars(research, symbol, now)
        except (OSError, ValueError, RuntimeError):
            data_state = "unavailable"
            message = (
                "Saved daily history failed local integrity or validation checks. "
                "Prepare and review a new dataset in Strategies. No account state changed."
            )
    elif timeframe != "1d":
        bars = _averages(minute_bars)
        message = (
            "No completed, quality-checked candles are saved for this interval. "
            "Connect market data and allow complete intervals to arrive. "
            "Gaps and candles with unknown initial volume are excluded."
        )
        if candle_error:
            data_state = "unavailable"
            message = (
                "Saved intraday candles failed local validation. Inspect the local data "
                "before using it; no account state changed and no replacement was downloaded."
            )
    if bars:
        data_state = "available"
        message = (
            "Saved completed daily candles; these are historical prices, not live quotes."
            if timeframe == "1d"
            else "Saved local completed candles. Missing intervals are not filled in; "
            "gaps and unknown initial volume are excluded. "
            "Per-candle broker/replay provenance is not recorded."
        )
    truncated = len(bars) > BAR_LIMIT
    bars = bars[-BAR_LIMIT:]
    screen = (
        next((row for row in result["rows"] if row["symbol"] == symbol), None) if result else None
    )
    return {
        "schema_version": 1,
        "observed_at": stamp(now),
        "symbol": symbol,
        "timeframe": timeframe,
        "symbols": options,
        "quote": current_quote,
        "bars": bars,
        "bar_limit": BAR_LIMIT,
        "truncated": truncated,
        "excluded_candles": excluded,
        "data_state": data_state,
        "message": message,
        "source": {
            "kind": "installed_reviewed_daily" if timeframe == "1d" else "stored_completed_candles",
            "description": research.dataset.manifest.source
            if timeframe == "1d" and research
            else "Saved local completed candles; broker/replay provenance is not certified",
            "synthetic": research.dataset.manifest.synthetic
            if timeframe == "1d" and research
            else None,
            "price_basis": "Raw OHLC; no invented or inferred corporate-action adjustment",
            "latest_declared_completed_session": result.get("latest_reviewed_completed_session")
            if result and timeframe == "1d"
            else None,
        },
        "screen": screen,
        "screen_as_of": result["as_of"] if result else None,
        "policy": result["policy"] if result else None,
        "market_session_open": e.calendar.is_open(now),
        "limitations": [
            "Viewing analysis never downloads data, changes the shortlist or submits an order.",
            "SMA 20 and SMA 50 average available raw closing prices; they are not trade signals.",
            "Chart history and the current quote have separate freshness and review requirements.",
            "The daily screen is prior completed-session research, not a forecast or backtest.",
            *(
                [
                    "Stored minute candles do not record per-candle broker/replay provenance; "
                    "a chart is not broker acceptance evidence."
                ]
                if timeframe != "1d"
                else ["Daily source and synthetic labels are dataset declarations, not an audit."]
            ),
        ],
    }


def investment_snapshot(
    desk: Any,
    now: datetime,
    *,
    symbol: str | None = None,
    timeframe: Literal["1d", "1w", "1mo"] = "1d",
) -> dict[str, Any]:
    from trading_agent.investment_research.series import series_snapshot

    now = utc(now)
    with desk.engine.lock:
        research = desk.research
        base = analysis_snapshot(desk, now, symbol=symbol, include_history=False)
    chosen = base["symbol"]
    base["timeframe"] = timeframe
    if not research or chosen not in {m.symbol for m in research.dataset.manifest.universe}:
        base["message"] = (
            "No reviewed daily research history for this stock. Prepare data in Strategies."
        )
        base["research"] = {
            "indicator_status": {},
            "partial_periods": [],
            "coverage": {
                "calendar_verified": False,
                "detail": "Daily source data is not installed.",
            },
            "benchmark": {"state": "unavailable", "reason": "BENCHMARK_NOT_CONFIGURED"},
            "fundamentals": {"state": "unavailable", "reason": "LICENSED_SOURCE_NOT_CONFIGURED"},
            "explanations": ["Opening research does not download data or authorize trading."],
        }
        return base
    result = series_snapshot(research.dataset, chosen, now, timeframe=timeframe)
    bars = result["bars"]
    base.update(result)
    base["bars"] = bars[-BAR_LIMIT:]
    base["bar_limit"] = BAR_LIMIT
    base["truncated"] = len(bars) > BAR_LIMIT
    base["research"]["coverage"]["displayed_bars"] = len(base["bars"])
    partial = base["research"]["partial_periods"]
    base["research"]["partial_periods"] = partial[-24:]
    base["research"]["partial_period_limit"] = 24
    base["research"]["partial_periods_truncated"] = len(partial) > 24
    base["message"] = (
        "Saved completed share-adjusted research candles; historical evidence, not live quotes. "
        "Incomplete periods are excluded. Indicators use full eligible history "
        "before display slicing."
        if bars
        else "No complete research candles are available for this interval. "
        "Inspect calendar coverage, missing history and warmup details below; no data was invented."
    )
    return base


def mount_analysis(app: Any, desk: Any, authorized: Any, assets: Any, clock: Any) -> None:
    @app.get("/analysis", response_class=HTMLResponse)
    def page() -> str:
        return assets.joinpath("analysis.html").read_text(encoding="utf-8")

    @app.get("/analysis.js")
    def script() -> HTMLResponse:
        return HTMLResponse(
            assets.joinpath("analysis.js").read_text(encoding="utf-8"),
            media_type="application/javascript",
        )

    @app.get("/api/analysis", dependencies=[Depends(authorized)])
    def status(
        symbol: str | None = Query(default=None, pattern=r"^NSE:[A-Z0-9&_.-]{1,30}$"),
        timeframe: Timeframe = "1d",
    ) -> dict[str, Any]:
        try:
            return analysis_snapshot(desk, clock(), symbol=symbol, timeframe=timeframe)
        except UnknownAnalysisSymbol as error:
            raise HTTPException(404, str(error)) from None

    @app.get("/api/research/series", dependencies=[Depends(authorized)])
    def investment_status(
        symbol: str | None = Query(default=None, pattern=r"^NSE:[A-Z0-9&_.-]{1,30}$"),
        timeframe: Literal["1d", "1w", "1mo"] = "1d",
    ) -> dict[str, Any]:
        try:
            return investment_snapshot(desk, clock(), symbol=symbol, timeframe=timeframe)
        except UnknownAnalysisSymbol as error:
            raise HTTPException(404, str(error)) from None
        except Exception:
            # Data-read failures must not invoke the mutation-fault handler or revoke authority.
            raise HTTPException(
                503,
                "Saved research failed validation or integrity checks. "
                "Review source files and refresh; no account state changed.",
            ) from None
