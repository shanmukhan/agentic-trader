from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal

import pytest
from pydantic import SecretStr

from trading_agent.execution.paper_broker import PaperBroker
from trading_agent.market_data.calendar import SessionCalendar
from trading_agent.models import Candidate, Instrument, Quote
from trading_agent.persistence.database import Database
from trading_agent.settings import Settings

D = Decimal
NOW = datetime(2026, 10, 20, 4, 30, tzinfo=UTC)  # 10:00 IST
TOKEN = "test-operator-credential-" + "a" * 32


def quote(
    second=0,
    *,
    symbol="NSE:DEMO",
    token=1,
    bid="499.95",
    ask="500",
    bid_size=100,
    ask_size=100,
    volume=None,
    base=NOW,
):
    now = base + timedelta(seconds=second)
    return Quote(
        symbol=symbol,
        token=token,
        exchange_time=now,
        received_time=now,
        last=D(ask),
        bid=D(bid),
        ask=D(ask),
        bid_size=bid_size,
        ask_size=ask_size,
        volume=1000 + second * 100 if volume is None else volume,
    )


def candidate(identity="entry", *, now=NOW, symbol="NSE:DEMO", stop="495", target="510", **kwargs):
    return Candidate(
        intent_id=identity,
        symbol=symbol,
        stop=D(stop),
        target=D(target),
        decision_time=now,
        reason="test hypothesis",
        **kwargs,
    )


@pytest.fixture
def engine_factory(tmp_path):
    opened = []

    def make(**overrides):
        settings = Settings(
            database=tmp_path / f"account-{len(opened)}.db",
            operator_token=SecretStr(TOKEN),
            **overrides,
        )
        db = Database(settings.database, settings.starting_cash)
        opened.append(db)
        calendar = SessionCalendar(
            {
                date(2026, 10, 20): (time(9, 15), time(15, 30)),
                date(2026, 10, 21): (time(9, 15), time(15, 30)),
            }
        )
        engine = PaperBroker(db, settings, calendar)
        engine.register(
            [
                Instrument(symbol="NSE:DEMO", token=1, tick_size=D("0.05")),
                Instrument(symbol="NSE:SECOND", token=2, tick_size=D("0.05")),
                Instrument(symbol="NSE:THIRD", token=3, tick_size=D("0.05")),
            ]
        )
        engine.set_connected(True)
        engine.ingest(quote(), NOW)
        return engine

    yield make
    for db in opened:
        db.close()


@pytest.fixture
def engine(engine_factory):
    return engine_factory()


@pytest.fixture
def research_dataset(tmp_path):
    from trading_agent.backtesting.dataset import Dataset
    from trading_agent.backtesting.demo import create_demo_dataset
    from trading_agent.strategy.rules import StrategySettings

    path = tmp_path / "dataset"
    create_demo_dataset(path, StrategySettings())
    return Dataset(path)


def changed_dataset(dataset, directory, transform):
    from trading_agent.backtesting.dataset import Dataset, write_bundle

    events = list(dataset.events())
    write_bundle(directory, dataset.manifest, iter(transform(events)))
    return Dataset(directory)
