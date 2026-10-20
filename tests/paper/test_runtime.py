import json
from datetime import time, timedelta
from decimal import Decimal as D

import pytest
from conftest import candidate

from trading_agent.execution.paper_broker import PaperBroker
from trading_agent.market_data.calendar import IST
from trading_agent.paper.config import FeedSettings
from trading_agent.paper.demo import SIGNAL, WARM, demo_quote, prepare_signal, signal_candle, warmup
from trading_agent.persistence.database import Database


def ready(feed, *, arm=False):
    feed.connection(True, WARM)
    feed.on_quote(demo_quote(WARM), WARM)
    feed.on_candles(warmup(), WARM)
    if arm:
        feed.arm(WARM)
    return feed


def test_start_disarmed_and_history_is_observed_without_trading(paper_factory):
    feed = paper_factory()
    with pytest.raises(ValueError, match="FEED_DISCONNECTED"):
        feed.arm(WARM)
    ready(feed)
    assert not feed.armed and feed.readiness(WARM) == ()
    assert not feed.engine.orders()
    with feed.engine.db.transaction() as tx:
        last = json.loads(
            tx.execute(
                "SELECT payload FROM events WHERE kind='feed_evaluation' ORDER BY seq DESC LIMIT 1"
            ).fetchone()[0]
        )
    assert "ENTRIES_DISABLED" in last["reasons"] and "FEED_DISCONNECTED" not in last["reasons"]
    assert feed.arm(WARM)["armed"]
    assert "HISTORY_NOT_READY" in feed.readiness(WARM + timedelta(minutes=5))


def test_rules_submit_once_through_risk_and_strictly_later_quote(paper_factory):
    feed = paper_factory()
    prepare_signal(feed)
    orders = feed.engine.orders()
    assert len(orders) == 1 and orders[0]["state"] == "ACCEPTED"
    assert not feed.engine.snapshot(SIGNAL)["positions"]
    feed.on_candles(warmup() + [signal_candle()], SIGNAL)
    assert len(feed.engine.orders()) == 1
    now = SIGNAL + timedelta(seconds=1)
    feed.on_quote(demo_quote(now, bid="501", volume=33100), now)
    snapshot = feed.engine.snapshot(now)
    assert snapshot["positions"] and D(snapshot["cash"]) < 25000
    with feed.engine.db.transaction() as tx:
        feed.engine.db.reconcile(tx)
        payload = json.loads(
            tx.execute("SELECT payload FROM events WHERE kind='automation_candidate'").fetchone()[0]
        )
    assert payload["rank"] == 1 and payload["probability"] is None
    assert snapshot["reserved_cash"] == "0"


def test_risk_rejection_and_manual_bypass_remain_blocked(paper_factory):
    feed = paper_factory(max_trade_risk=D(".10"))
    prepare_signal(feed)
    assert feed.engine.orders()[0]["reason"] == "ZERO_QUANTITY"
    result = feed.engine.submit(candidate(now=SIGNAL), SIGNAL)
    assert "AUTOMATION_CONTROLLER_REQUIRED" in result["reason"]
    assert feed.engine.snapshot(SIGNAL)["cash"] == "25000"


@pytest.mark.parametrize(
    "mode", ["disconnect", "silence", "resume_without_tick", "bad_quote", "stale_exchange"]
)
def test_outage_disarms_cancels_pending_and_never_revives_entry(paper_factory, mode):
    feed = paper_factory()
    prepare_signal(feed)
    if mode == "disconnect":
        feed.connection(False, SIGNAL + timedelta(seconds=1))
        feed.connection(True, SIGNAL + timedelta(seconds=2))
        now = SIGNAL + timedelta(seconds=3)
        feed.on_quote(demo_quote(now, bid="501", volume=33300), now)
    elif mode == "silence":
        feed.tick(SIGNAL + timedelta(seconds=6))
    elif mode == "bad_quote":
        now = SIGNAL + timedelta(seconds=1)
        feed.on_quote(demo_quote(now, bid="501", volume=1), now)
    elif mode == "stale_exchange":
        now = SIGNAL + timedelta(seconds=1)
        q = demo_quote(now, bid="501", volume=33100).model_copy(
            update={"exchange_time": SIGNAL - timedelta(seconds=6)}
        )
        feed.on_quote(q, now)
    else:
        now = SIGNAL + timedelta(seconds=6)
        feed.on_quote(demo_quote(now, bid="501", volume=33600), now)
    assert not feed.armed
    assert feed.engine.orders()[0]["state"] == "CANCELLED"
    assert not feed.engine.snapshot(feed.last_time)["positions"]
    assert feed.engine.snapshot(feed.last_time)["cash"] == "25000"


def test_holdings_stay_open_on_silence_until_fresh_liquidation(paper_factory):
    feed = paper_factory()
    prepare_signal(feed)
    now = SIGNAL + timedelta(seconds=1)
    feed.on_quote(demo_quote(now, bid="501", volume=33100), now)
    cash = feed.engine.snapshot(now)["cash"]
    stale = SIGNAL + timedelta(seconds=7)
    feed.tick(stale, force_telemetry=True)
    assert feed.engine.snapshot(stale)["positions"] and feed.engine.snapshot(stale)["cash"] == cash
    assert feed.engine.snapshot(stale)["kill"] and not feed.armed
    assert feed.status(stale)["performance"]["stale_valuations"] > 0
    resumed = stale + timedelta(seconds=1)
    feed.on_quote(demo_quote(resumed, bid="500", volume=34000), resumed)
    assert not feed.engine.snapshot(resumed)["positions"]
    assert feed.engine.snapshot(resumed)["kill"] and not feed.armed


def test_clock_regression_and_storage_failure_latch_fault(paper_factory, monkeypatch):
    feed = ready(paper_factory(), arm=True)
    with pytest.raises(ValueError, match="backward"):
        feed.tick(WARM - timedelta(seconds=1))
    assert not feed.armed and feed.engine.faulted and not feed.engine.connected
    other = ready(paper_factory(), arm=True)
    import sqlite3

    def fail(*args):
        raise sqlite3.OperationalError("private-path-or-credential")

    monkeypatch.setattr(other.engine.db, "event", fail)
    with pytest.raises(sqlite3.OperationalError):
        other.on_quote(
            demo_quote(WARM + timedelta(seconds=1), volume=28100), WARM + timedelta(seconds=1)
        )
    assert not other.armed and other.engine.faulted and not other.engine.connected


@pytest.mark.parametrize("mode", ["gap", "quality", "revision", "universe", "future"])
def test_bad_history_prevents_arming_or_faults(paper_factory, mode):
    feed = paper_factory()
    feed.connection(True, WARM)
    feed.on_quote(demo_quote(WARM), WARM)
    candles = warmup()
    if mode == "gap":
        candles.pop(3)
    elif mode == "quality":
        candles[3] = candles[3].model_copy(update={"quality": "gap"})
    elif mode == "universe":
        candles[3] = candles[3].model_copy(update={"symbol": "NSE:UNKNOWN"})
    elif mode == "future":
        candles.append(signal_candle())
    else:
        feed.on_candles(candles, WARM)
        candles[3] = candles[3].model_copy(update={"volume": 3000})
    if mode in {"revision", "universe", "future"}:
        with pytest.raises(ValueError):
            feed.on_candles(candles, WARM)
        assert feed.engine.faulted
    else:
        feed.on_candles(candles, WARM)
        with pytest.raises(ValueError, match="HISTORY_NOT_READY"):
            feed.arm(WARM)
    assert not feed.armed and not feed.engine.orders()


def test_unclean_restart_requires_identity_and_cancels_pending_before_disarmed_warmup(
    paper_factory,
):
    feed = paper_factory()
    prepare_signal(feed)
    policy, calendar = feed.engine.settings, feed.engine.calendar
    signature = feed.digest
    feed.engine.db.close()
    db = Database(policy.database, policy.starting_cash)
    try:
        with pytest.raises(ValueError, match="automation changed"):
            PaperBroker(db, policy, calendar)
        with pytest.raises(ValueError, match="automation changed"):
            PaperBroker(db, policy, calendar, automation="changed")
        with db.transaction() as tx:
            assert tx.execute("SELECT state FROM orders").fetchone()[0] == "ACCEPTED"
        engine = PaperBroker(
            db, policy, calendar, automation=signature, recovery_time=SIGNAL + timedelta(seconds=1)
        )
        assert engine.orders()[0]["state"] == "CANCELLED"
        from trading_agent.paper.runtime import PaperFeed

        resumed = PaperFeed(
            engine,
            instruments=list(feed.catalog.values()),
            strategy=feed.strategy,
            settings=feed.settings,
            now=SIGNAL + timedelta(seconds=1),
            synthetic=True,
        )
        resumed.connection(True, SIGNAL + timedelta(seconds=1))
        now = SIGNAL + timedelta(seconds=2)
        resumed.on_quote(demo_quote(now, bid="501", volume=33200), now)
        resumed.on_candles(warmup() + [signal_candle()], now)
        assert not resumed.armed and len(engine.orders()) == 1
        assert not engine.snapshot(now)["positions"]
        assert resumed.arm(now)["armed"]
    finally:
        db.close()


def test_model_gate_on_connected_pipeline_and_age_limit(paper_factory, research_model):
    old = ready(paper_factory(model=research_model))
    with pytest.raises(ValueError, match="MODEL_TOO_OLD"):
        old.arm(WARM)
    feed = paper_factory(model=research_model, config=FeedSettings(max_model_age_days=365))
    prepare_signal(
        feed,
        candle=signal_candle().model_copy(
            update={"close": D("501.50"), "high": D(502), "volume": 6000}
        ),
    )
    order = feed.engine.orders()[0]
    assert order["state"] == "ACCEPTED"
    with feed.engine.db.transaction() as tx:
        payload = json.loads(
            tx.execute("SELECT payload FROM events WHERE kind='automation_candidate'").fetchone()[0]
        )
    assert (
        payload["candidate"]["requires_ml"]
        and payload["probability"] >= research_model.artifact.threshold
    )
    with pytest.raises(ValueError, match="synthetic models"):
        paper_factory(model=research_model, synthetic=False)


def test_early_close_next_session_and_disarm_are_fail_closed(paper_factory):
    feed = ready(paper_factory(), arm=True)
    feed.disarm(WARM)
    assert not feed.armed
    feed.engine.calendar.sessions[WARM.astimezone(IST).date()] = (time(9, 15), time(10, 40))
    assert "EARLY_CLOSE_CUTOFF" in feed.readiness(WARM)
    other = ready(paper_factory(), arm=True)
    other.tick(WARM + timedelta(days=1))
    assert not other.armed and other.reason == "SESSION_CHANGED"


def test_shared_history_batch_ranks_symbols_before_position_admission(
    paper_factory, research_model
):
    from trading_agent.ml.features import FEATURE_NAMES
    from trading_agent.ml.inference import Coefficients, ResearchModel
    from trading_agent.models import Instrument
    from trading_agent.paper.demo import INSTRUMENT
    from trading_agent.risk.policy import policy_fingerprint
    from trading_agent.settings import Settings

    coefficients = Coefficients(
        means=(0.0,) * 12,
        scales=(1.0,) * 12,
        weights=tuple(1.0 if name == "relative_volume" else 0.0 for name in FEATURE_NAMES),
        intercept=0.0,
        calibration_slope=1.0,
        calibration_intercept=0.0,
    )
    model = ResearchModel(
        research_model.artifact.model_copy(
            update={
                "coefficients": coefficients,
                "policy_sha256": policy_fingerprint(Settings(max_positions=1)),
            }
        ),
        "f" * 64,
    )
    second = Instrument(symbol="NSE:SECOND", token=2, tick_size=D(".05"))
    feed = paper_factory(
        instruments=[INSTRUMENT, second],
        model=model,
        max_positions=1,
        config=FeedSettings(max_model_age_days=365),
    )
    feed.connection(True, WARM)
    for instrument in (INSTRUMENT, second):
        feed.on_quote(
            demo_quote(WARM).model_copy(
                update={"symbol": instrument.symbol, "token": instrument.token}
            ),
            WARM,
        )
    feed.on_candles(
        [
            candle.model_copy(update={"symbol": instrument.symbol})
            for instrument in (INSTRUMENT, second)
            for candle in warmup()
        ],
        WARM,
    )
    feed.arm(WARM)
    for index in range(1, 301):
        now = WARM + timedelta(seconds=index)
        for instrument in (INSTRUMENT, second):
            feed.on_quote(
                demo_quote(
                    now, bid="501" if index == 300 else "500", volume=28000 + 10000 * index // 300
                ).model_copy(update={"symbol": instrument.symbol, "token": instrument.token}),
                now,
            )
    feed.on_candles(
        [
            signal_candle(),
            signal_candle().model_copy(update={"symbol": second.symbol, "volume": 10000}),
        ],
        SIGNAL,
    )
    with feed.engine.db.transaction() as tx:
        proposals = [
            json.loads(row[0])
            for row in tx.execute(
                "SELECT payload FROM events WHERE kind='automation_candidate' ORDER BY seq"
            )
        ]
    assert [p["symbol"] for p in proposals] == [second.symbol, INSTRUMENT.symbol]
    assert [p["rank"] for p in proposals] == [1, 2]
    orders = {row["symbol"]: row for row in feed.engine.orders()}
    assert orders[second.symbol]["state"] == "ACCEPTED"
    assert orders[INSTRUMENT.symbol]["reason"] == "POSITION_LIMIT"
    assert not feed.engine.snapshot(SIGNAL)["positions"]


def test_model_age_expiry_cancels_pending_buy_before_it_can_fill(paper_factory, research_model):
    from trading_agent.ml.inference import Artifact, ResearchModel

    through = SIGNAL - timedelta(days=30) + timedelta(seconds=2)
    artifact = Artifact(
        **(
            research_model.artifact.model_dump()
            | {"validated_through": through, "available_after": through + timedelta(minutes=30)}
        )
    )
    model = ResearchModel(artifact, research_model.version)
    feed = paper_factory(model=model)
    prepare_signal(
        feed,
        candle=signal_candle().model_copy(
            update={"close": D("501.50"), "high": D(502), "volume": 6000}
        ),
    )
    assert feed.engine.orders()[0]["state"] == "ACCEPTED"
    now = SIGNAL + timedelta(seconds=3)
    feed.on_quote(demo_quote(now, bid="501.50", volume=34300), now)
    assert not feed.armed and feed.reason == "MODEL_TOO_OLD"
    assert feed.engine.orders()[0]["state"] == "CANCELLED"
    assert (
        not feed.engine.snapshot(now)["positions"] and feed.engine.snapshot(now)["cash"] == "25000"
    )
