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


@pytest.fixture
def corporate_account(long_term_factory):
    from trading_agent.execution.delivery import HoldingReview

    engine = long_term_factory()
    engine.calendar.sources = {
        day: "invented corporate-action session" for day in engine.calendar.sessions
    }
    engine.review_holding(
        HoldingReview(
            symbol="NSE:DEMO",
            session_date=NOW.date(),
            no_corporate_action=True,
            reference="invented pre-action basis",
        ),
        NOW,
    )
    engine.ingest(quote(), NOW)
    order = engine.submit(candidate(stop="490", target="600"), NOW)
    engine.ingest(quote(1), NOW + timedelta(seconds=1))
    assert order["quantity"] == 14
    tomorrow = NOW + timedelta(days=1)
    engine.review_holding(
        HoldingReview(
            symbol="NSE:DEMO",
            session_date=tomorrow.date(),
            no_corporate_action=False,
            reference="invented action notice; awaiting reviewed adjustment",
        ),
        tomorrow,
    )
    return engine


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

    def make(*, model=None, **overrides):
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
        engine = PaperBroker(db, settings, calendar, model=model)
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


@pytest.fixture(scope="session")
def ml_demo(tmp_path_factory):
    from pathlib import Path

    from trading_agent.ml.demo import run_ml_demo
    from trading_agent.ml.schema import TrainingSettings
    from trading_agent.strategy.rules import StrategySettings

    directory = tmp_path_factory.mktemp("ml") / "demo"
    summary = run_ml_demo(
        directory,
        strategy=StrategySettings(),
        training=TrainingSettings.load(Path("config/ml-demo.toml")),
        policy=Settings(),
    )
    return directory, summary


@pytest.fixture
def research_model(ml_demo):
    from trading_agent.execution.costs import Charges
    from trading_agent.ml.inference import load_model
    from trading_agent.risk.policy import policy_fingerprint
    from trading_agent.strategy.rules import StrategySettings

    return load_model(
        ml_demo[0] / "model",
        strategy_sha256=StrategySettings().digest(),
        policy_sha256=policy_fingerprint(Settings()),
        charges_version=Charges().version,
        allow_synthetic=True,
    )


@pytest.fixture
def paper_factory(tmp_path):
    from trading_agent.paper.config import FeedSettings, feed_identity
    from trading_agent.paper.demo import INSTRUMENT, WARM
    from trading_agent.paper.runtime import PaperFeed
    from trading_agent.strategy.rules import StrategySettings

    databases = []

    def make(
        *,
        strategy=None,
        config=None,
        model=None,
        synthetic=True,
        instruments=None,
        now=WARM,
        **overrides,
    ):
        settings = Settings(
            database=tmp_path / f"paper-{len(databases)}.sqlite3",
            operator_token=SecretStr(TOKEN),
            **overrides,
        )
        strategy, config = strategy or StrategySettings(), config or FeedSettings()
        catalog = instruments or [INSTRUMENT]
        _, signature = feed_identity(
            catalog, strategy, config, model.version if model else None, synthetic
        )
        db = Database(settings.database, settings.starting_cash)
        databases.append(db)
        calendar = SessionCalendar(
            {
                date(2026, 10, 20): (time(9, 15), time(15, 30)),
                date(2026, 10, 21): (time(9, 15), time(15, 30)),
            }
        )
        engine = PaperBroker(
            db, settings, calendar, recovery_time=now, model=model, automation=signature
        )
        engine.register(catalog)
        return PaperFeed(
            engine,
            instruments=catalog,
            strategy=strategy,
            settings=config,
            now=now,
            synthetic=synthetic,
        )

    yield make
    for db in databases:
        db.close()


@pytest.fixture
def long_term_factory(tmp_path):
    opened = []

    def make(*, now=NOW, **overrides):
        values = dict(
            investment_horizon="long_term",
            max_trade_risk=D("250"),
            daily_loss_limit=D("500"),
            max_position_notional=D("7500"),
            max_positions=5,
        )
        values.update(overrides)
        settings = Settings(
            database=tmp_path / f"long-term-{len(opened)}.sqlite3",
            operator_token=SecretStr(TOKEN),
            **values,
        )
        days = [NOW.date() + timedelta(days=n) for n in (0, 1, 2, 3, 6, 7)]
        calendar = SessionCalendar(
            {day: (time(9, 15), time(15, 30)) for day in days},
            {day: "invented long-term test calendar" for day in days},
        )
        db = Database(settings.database, settings.starting_cash)
        opened.append(db)
        engine = PaperBroker(db, settings, calendar, recovery_time=now)
        engine.register(
            [
                Instrument(symbol="NSE:DEMO", token=1, tick_size=D("0.05")),
                Instrument(symbol="NSE:SECOND", token=2, tick_size=D("0.05")),
            ]
        )
        engine.set_connected(True)
        return engine

    yield make
    for db in opened:
        db.close()


@pytest.fixture
def execution_inputs(tmp_path):
    from trading_agent.daily_execution.demo import create_execution_demo

    daily, execution, future = create_execution_demo(tmp_path / "inputs", sessions=3)
    return daily, execution, future


@pytest.fixture
def daily_policy():
    return Settings.load("config/long-term.toml")


@pytest.fixture
def daily_strategy():
    from pathlib import Path

    from trading_agent.daily_execution.contracts import DailyStrategy

    return DailyStrategy.load(Path("config/daily-strategy.toml"))


@pytest.fixture
def execution_source(execution_inputs):
    from trading_agent.daily_execution.dataset import ExecutionDataset
    from trading_agent.daily_research.dataset import DailyDataset

    daily, execution, _ = execution_inputs
    return ExecutionDataset(execution, DailyDataset(daily))


@pytest.fixture(scope="session")
def daily_ml_demo(tmp_path_factory):
    from trading_agent.daily_execution.demo import execution_demo

    directory = tmp_path_factory.mktemp("daily-ml") / "demo"
    result = execution_demo(directory, with_ml=True)
    return directory, result


@pytest.fixture
def desk_factory(tmp_path, engine_factory, long_term_factory):
    import json

    from trading_agent.desk.service import TradingDesk
    from trading_agent.execution.delivery import HoldingReview

    def make(*, horizon="intraday", mode="rules", synthetic=True, reviewed=True):
        e = (
            long_term_factory(stream_tokens=(1,))
            if horizon == "long_term"
            else engine_factory(stream_tokens=(1,))
        )
        for symbol, token in [("NSE:BROAD", 257), ("NSE:ETF", 513)]:
            e.register([Instrument(symbol=symbol, token=token, tick_size=D(".05"))])
        if e.long_term:
            e.review_holding(
                HoldingReview(
                    symbol="NSE:DEMO",
                    session_date=NOW.date(),
                    no_corporate_action=True,
                    reference="INVENTED basis review",
                ),
                NOW,
            )
            e.ingest(quote(), NOW)
        directory = tmp_path / ("daily-" + str(len(list(tmp_path.glob("daily-*")))))
        directory.mkdir()
        days = [NOW.date() - timedelta(days=i) for i in range(4, -1, -1)]
        manifest = {
            "schema_version": 1,
            "source": "INVENTED test data",
            "notes": "Synthetic chronology, not market evidence",
            "synthetic": synthetic,
            "sessions": [
                {"day": str(day), "open": "09:15", "close": "15:30", "source": "INVENTED calendar"}
                for day in days
            ],
            "universe": [
                {
                    "symbol": symbol,
                    "effective_session": str(days[0]),
                    "included": True,
                    "known_at": (NOW - timedelta(days=6)).isoformat(),
                    "reference": "INVENTED membership",
                }
                for symbol in ["NSE:DEMO", "NSE:BROAD", "NSE:ETF"]
            ],
        }
        (directory / "manifest.json").write_text(json.dumps(manifest))
        bars = []
        for i, day in enumerate(days[:-1]):
            for symbol in sorted(["NSE:DEMO", "NSE:BROAD", "NSE:ETF"]):
                price = 497 + i if symbol == "NSE:DEMO" else 100 + i * 2
                available = (NOW - timedelta(days=4 - i)).replace(hour=11)
                bars.append(
                    {
                        "symbol": symbol,
                        "session": str(day),
                        "open": str(price),
                        "high": str(price),
                        "low": str(price),
                        "close": str(price),
                        "volume": 100000,
                        "price_available_at": available.isoformat(),
                        "basis_reviewed_at": available.isoformat(),
                        "basis_reference": "INVENTED no-action review",
                        "share_numerator": 1,
                        "share_denominator": 1,
                        "cash_per_previous_share": "0",
                    }
                )
        (directory / "daily.jsonl").write_text("".join(json.dumps(b) + "\n" for b in bars))
        profile = tmp_path / (directory.name + ".toml")
        profile.write_text(
            'name = "Synthetic unit profile"\ndaily_dataset = '
            + json.dumps(str(directory))
            + "\nstrategy_mode = "
            + json.dumps(mode)
            + "\n"
            + "[long_term.screen]\nmomentum_sessions = 2\ntrend_sessions = 2\n"
            + 'min_average_turnover = "0"\n'
            + "".join(
                "\n[[shares]]\nsymbol = "
                + json.dumps(s)
                + '\nkind = "equity_share"\nreviewed_at = '
                + json.dumps((NOW - timedelta(days=7)).isoformat())
                + '\nreference = "INVENTED share class"\n'
                for s in (["NSE:DEMO", "NSE:BROAD"] if reviewed else ["NSE:BROAD"])
            )
        )
        desk = TradingDesk(e, NOW, profile=profile, synthetic=True)
        return desk, profile, directory

    return make
