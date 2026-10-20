import json
import threading
from datetime import timedelta
from decimal import Decimal as D
from unittest.mock import Mock

import pytest

from trading_agent.paper.demo import SIGNAL, WARM, demo_quote, prepare_signal, warmup
from trading_agent.paper.metrics import Timings
from trading_agent.paper.report import paper_report
from trading_agent.paper.service import PaperService


def service(feed, monkeypatch, current=None):
    monkeypatch.setattr("trading_agent.paper.service.QuoteStream", Mock())
    current = current or [WARM]
    broker = Mock()
    broker.get_historical_candles.return_value = warmup()
    controller = PaperService(feed, broker, lambda: current[0])
    controller.connection(True)
    controller.quote(demo_quote(current[0]))
    return controller, broker, current


def test_history_only_once_per_completed_boundary_and_before_arm(paper_factory, monkeypatch):
    feed = paper_factory()
    controller, broker, current = service(feed, monkeypatch)
    assert controller.refresh_history()
    assert not controller.refresh_history()
    broker.get_historical_candles.assert_called_once()
    args = broker.get_historical_candles.call_args.args
    assert args[2] == WARM and args[3] == 5 and args[4] == WARM
    assert not feed.armed and feed.arm(WARM)["armed"]
    controller.close()
    assert feed.closed and not feed.armed
    before = feed.engine.orders()
    controller.quote(demo_quote(WARM + timedelta(seconds=1)))
    controller.connection(True)
    assert feed.engine.orders() == before and not feed.engine.connected


def test_network_history_wait_does_not_block_quote_processing(paper_factory, monkeypatch):
    feed = paper_factory()
    controller, broker, current = service(feed, monkeypatch)
    entered, release, received = threading.Event(), threading.Event(), threading.Event()

    def slow_history(*args):
        entered.set()
        assert release.wait(3)
        return warmup()

    broker.get_historical_candles.side_effect = slow_history
    worker = threading.Thread(target=controller.refresh_history)
    worker.start()
    try:
        assert entered.wait(3)
        current[0] += timedelta(seconds=1)

        def quote():
            controller.quote(demo_quote(current[0], volume=28100))
            received.set()

        quote_worker = threading.Thread(target=quote)
        quote_worker.start()
        assert received.wait(2), "history HTTP held the execution lock"
        quote_worker.join(2)
    finally:
        release.set()
        worker.join(3)
    assert not worker.is_alive() and feed.counts["quotes_accepted"] == 2


@pytest.mark.parametrize("mode", ["missing", "error", "reconnect", "stop"])
def test_partial_failed_or_obsolete_history_never_arms(paper_factory, monkeypatch, mode):
    feed = paper_factory()
    controller, broker, current = service(feed, monkeypatch)

    def response(*args):
        if mode == "missing":
            return warmup()[:-1]
        if mode == "error":
            raise RuntimeError("private-authenticated-url")
        if mode == "reconnect":
            controller.connection(False)
            controller.connection(True)
        else:
            controller.stop.set()
        return warmup()

    broker.get_historical_candles.side_effect = response
    assert not controller.refresh_history()
    assert not feed.armed and not feed.last_bar
    if mode in {"missing", "error"}:
        assert feed.reason == "HISTORY_UNAVAILABLE"
        assert feed.counts["history_failures"] == 1
        assert not controller.refresh_history()  # Bounded retry cadence.
        current[0] += timedelta(seconds=5)
        controller.quote(demo_quote(current[0], volume=28500))
        broker.get_historical_candles.side_effect = None
        broker.get_historical_candles.return_value = warmup()
        assert controller.refresh_history()
        assert not feed.armed


def test_worker_lifecycle_and_graceful_shutdown_do_not_report_an_outage(paper_factory, monkeypatch):
    feed = paper_factory()
    controller, broker, current = service(feed, monkeypatch)
    controller.stream.close.side_effect = lambda: controller.connection(False)
    controller.start()
    with pytest.raises(RuntimeError, match="already"):
        controller.start()
    controller.close()
    assert controller.thread and not controller.thread.is_alive()
    assert feed.closed and not feed.armed
    with feed.engine.db.transaction() as tx:
        reasons = [
            json.loads(row[0])["reason"]
            for row in tx.execute("SELECT payload FROM events WHERE kind='automation_state'")
        ]
    assert "FEED_DISCONNECTED" not in reasons and reasons[-1] == "SHUTDOWN"


def test_metrics_are_bounded_and_do_not_present_window_quantiles_as_global():
    timings = Timings(50)
    for number in range(1000):
        timings.observe("quote", float(number))
    result = timings.snapshot()["quote"]
    assert result["total_count"] == 1000 and result["window_count"] == 512
    assert result["over_budget_count"] == 949 and result["maximum_ms"] == 999
    assert result["p50_ms"] >= 488 and result["p99_ms"] >= 990
    for bad in (float("nan"), float("inf"), -1.0):
        with pytest.raises(ValueError):
            timings.observe("quote", bad)


def test_report_reconciles_without_cancelling_pending_or_altering_source(paper_factory, tmp_path):
    feed = paper_factory()
    prepare_signal(feed)
    source_orders = feed.engine.orders()
    with feed.engine.db.transaction() as tx:
        before = [tuple(row) for row in tx.execute("SELECT * FROM events ORDER BY seq")]
    report = paper_report(feed.engine.db, tmp_path / "report")
    with feed.engine.db.transaction() as tx:
        after = [tuple(row) for row in tx.execute("SELECT * FROM events ORDER BY seq")]
    assert before == after and feed.engine.orders() == source_orders
    assert not report["gates"]["flat"] and report["metrics"]["pending_orders"] == 1
    assert not report["gates"]["non_synthetic"] and not report["ready_for_live"]
    assert not report["external_acceptance_verified"] and not report["preliminary_gates_passed"]
    assert report["cash"] == "25000" and report["fees"] == "0"
    assert (tmp_path / "report/report.md").is_file()
    with pytest.raises(FileExistsError):
        paper_report(feed.engine.db, tmp_path / "report")


def test_report_records_stale_exposure_and_net_fees_after_recovery(paper_factory, tmp_path):
    feed = paper_factory()
    prepare_signal(feed)
    now = SIGNAL + timedelta(seconds=1)
    feed.on_quote(demo_quote(now, bid="501", volume=33100), now)
    feed.tick(now + timedelta(seconds=6), force_telemetry=True)
    feed.close(now + timedelta(seconds=7))
    report = paper_report(feed.engine.db, tmp_path / "report")
    assert not report["gates"]["no_stale_observed_valuations"]
    assert report["open_positions"] and not report["gates"]["flat"]
    assert D(report["fees"]) > 0 and report["metrics"]["completed_trades"] == 0


def test_full_synthetic_drills_reconcile_every_scenario(tmp_path):
    from trading_agent.paper.demo import run_paper_demo

    result = run_paper_demo(tmp_path / "drills")
    assert not result["ready_for_live"] and result["synthetic"]
    assert result["scenarios"]["partial_fills"]["cash"] == "25023.24"
    assert result["scenarios"]["disconnect"]["cash"] == "24959.48"
    assert result["scenarios"]["silence"]["cash"] == "24959.48"
    assert result["scenarios"]["restart"]["cash"] == "25000"
    for scenario in result["scenarios"].values():
        assert scenario["gates"]["flat"]
        assert not scenario["gates"]["non_synthetic"]
    assert not result["scenarios"]["restart"]["gates"]["clean_shutdowns"]


def test_history_requests_are_paced_and_single_first_bar_range_is_valid(paper_factory, monkeypatch):
    from trading_agent.models import Instrument
    from trading_agent.paper.demo import INSTRUMENT

    second = Instrument(symbol="NSE:SECOND", token=2, tick_size=D(".05"))
    feed = paper_factory(instruments=[INSTRUMENT, second])
    controller, broker, _ = service(feed, monkeypatch)
    observed, steady = [], [10.0]
    monkeypatch.setattr("trading_agent.paper.service.perf_counter", lambda: steady[0])

    def wait(delay):
        observed.append(delay)
        steady[0] += delay
        return False

    monkeypatch.setattr(controller.stop, "wait", wait)

    def response(instrument, start, end, minutes, asof):
        assert start < end <= asof
        steady[0] += 0.05
        return [candle.model_copy(update={"symbol": instrument.symbol}) for candle in warmup()]

    broker.get_historical_candles.side_effect = response
    assert controller.refresh_history()
    assert len(observed) == 2 and observed[1] == pytest.approx(0.35)
    assert not feed.armed


def test_first_completed_candle_uses_a_nonempty_time_range(paper_factory, monkeypatch):
    from trading_agent.paper.demo import OPEN

    first = OPEN + timedelta(minutes=5)
    feed = paper_factory(now=first)
    controller, broker, _ = service(feed, monkeypatch, current=[first])
    broker.get_historical_candles.return_value = warmup()[:1]
    assert controller.refresh_history()
    args = broker.get_historical_candles.call_args.args
    assert args[1] == OPEN and args[2] == first and args[1] < args[2]
    assert feed.counts["history_failures"] == 0 and not feed.armed
