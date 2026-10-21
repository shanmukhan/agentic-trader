import json
import threading
from datetime import timedelta

import pytest
from preparation_support import TEST_NOW, download, installation
from pydantic import ValidationError

from trading_agent.api.setup import SetupError
from trading_agent.daily_execution.dataset import ExecutionDataset
from trading_agent.daily_research.analysis import analyze
from trading_agent.desk import sources
from trading_agent.desk.preparation import DownloadRequest, Preparation, saved_profile
from trading_agent.desk.service import TradingDesk
from trading_agent.persistence.database import Database


def test_download_records_real_source_shapes_exclusions_and_leaves_account_untouched(
    preparation_factory,
):
    s = preparation_factory()
    e = s.engine
    before = e.snapshot(TEST_NOW)
    request = download(s)
    job = s.prep.view()["job"]
    assert job["state"] == "ready_for_review" and job["eligible"] == 97
    assert job["total"] == 98 and job["completed"] == 98
    assert {r["reason"] for r in job["excluded"]} == {
        "CORPORATE_ACTION_IN_HISTORY",
        "CATALOG_MATCH_MISSING",
        "INCOMPLETE_DAILY_HISTORY",
    }
    assert "NSE:A001" not in s.broker.calls  # No paid history read for a known action exclusion.
    assert len(s.requests) == 3 and len(s.broker.calls) == 98
    s.prep.start(request)
    assert len(s.broker.calls) == 98  # Exact uncertain-response retry is idempotent.
    assert s.desk.mode == "manual" and s.desk.research is None
    assert e.snapshot(TEST_NOW) == before and not e.orders()
    for path in s.prep.root.rglob("*"):
        if path.is_file():
            assert path.stat().st_mode & 0o077 == 0
            assert "INVENTED-token" not in path.read_text()


def test_review_installs_prospective_rules_profile_without_arming_or_manufacturing_ml(
    preparation_factory,
):
    s = preparation_factory()
    download(s)
    e = s.engine
    before = e.snapshot(TEST_NOW)
    body = installation(s)
    s.prep.install(body)
    data = s.desk.view(TEST_NOW)
    assert data["mode"] == "manual" and data["strategy_mode"] == "rules"
    assert not data["model_available"] and data["discovery"]["candidate_count"] == 97
    assert "NO_ANALYSIS_PROFILE" not in data["blockers"]
    assert data["discovery"]["universe_kind"] == "prospective_snapshot"
    assert data["shortlist"]["symbols"][:2] == ["NSE:A000", "NSE:A003"]
    assert e.settings.stream_tokens == (257,) and e.snapshot(TEST_NOW) == before
    loaded = saved_profile(e)
    assert loaded and loaded.is_file()
    fresh = TradingDesk(e, TEST_NOW, profile=loaded, clock=lambda: TEST_NOW)
    assert fresh.mode == "manual" and fresh.research.identity == s.desk.research.identity
    assert s.prep.install(body)["job"]["state"] == "installed"
    assert not e.orders()
    with e.db.transaction() as tx:
        Database.reconcile(tx)


def test_snapshot_is_unavailable_before_actual_observation_and_rejected_as_historical_ml_evidence(
    preparation_factory, tmp_path
):
    s = preparation_factory()
    download(s)
    s.prep.install(installation(s))
    r = s.desk.research
    earlier = analyze(r.dataset, r.profile.long_term.screen, TEST_NOW - timedelta(seconds=1))
    assert not earlier["rows"] and earlier["candidate_count"] == 0
    timeline = r.timeline
    timeline.advance(TEST_NOW - timedelta(seconds=1))
    assert (
        timeline.screen("NSE:A000", TEST_NOW - timedelta(seconds=1))["status"] == "outside_universe"
    )
    assert timeline.screen("NSE:A000", TEST_NOW)["status"] == "research_candidate"
    with pytest.raises(ValueError, match="historical execution/ML"):
        ExecutionDataset(tmp_path / "not-even-read", r.dataset)


@pytest.mark.parametrize("field", ["calendar_reviewed", "basis_reviewed", "policy_reviewed"])
def test_reviews_are_strict_and_not_pre_approved(preparation_factory, field):
    s = preparation_factory()
    download(s)
    for value in (False, 1, "true"):
        with pytest.raises(ValidationError):
            installation(s, **{field: value})
    assert s.desk.problem == "NO_ANALYSIS_PROFILE"


def test_ml_selection_never_falls_back_to_rules(preparation_factory):
    s = preparation_factory()
    download(s)
    with pytest.raises(SetupError, match="No validated model"):
        s.prep.install(installation(s, strategy_mode="rules_ml"))
    s.prep.model_path = "/nonexistent/INVENTED-model"
    with pytest.raises(SetupError, match="failed validation"):
        s.prep.install(installation(s, strategy_mode="rules_ml"))
    assert s.desk.research is None and not (s.prep.root / "active.json").exists()
    assert s.desk.mode == "manual" and not s.engine.orders()


def test_changed_sources_or_review_hash_are_not_installed(preparation_factory):
    s = preparation_factory()
    download(s)
    with pytest.raises(SetupError, match="source plan changed"):
        s.prep.install(installation(s, preview_sha256="f" * 64))
    path = s.prep.root / s.prep.state["job_id"] / "actions.json"
    path.write_text("[]")
    with pytest.raises(SetupError, match="source evidence changed"):
        s.prep.install(installation(s))
    assert s.desk.research is None and not s.engine.orders()


def test_saved_pointer_cannot_select_arbitrary_path_or_changed_profile(preparation_factory):
    s = preparation_factory()
    download(s)
    s.prep.install(installation(s))
    path = saved_profile(s.engine)
    path.write_text(path.read_text() + "\n# changed\n")
    with pytest.raises(SetupError, match="inputs changed"):
        saved_profile(s.engine)
    (s.prep.root / "active.json").write_text(
        json.dumps({"job_id": "../../etc", "profile_sha256": "a" * 64})
    )
    with pytest.raises(SetupError, match="Invalid saved"):
        saved_profile(s.engine)


def test_install_rejects_evening_calendar_changed_mode_feed_and_pending_orders(preparation_factory):
    from conftest import candidate

    s = preparation_factory()
    download(s)
    bad = s.prep.state["calendar_csv"].replace("15:30", "20:57")
    with pytest.raises(SetupError, match="09:15"):
        s.prep.install(installation(s, calendar_csv=bad))
    original = s.desk.revision
    s.desk.set_mode("manual", TEST_NOW, original)
    with pytest.raises(SetupError, match="Choose Manual and refresh"):
        s.prep.install(installation(s, revision=original))
    s.setup.stream = object()
    with pytest.raises(SetupError, match="Disconnect market data"):
        s.prep.install(installation(s))
    s.setup.stream = None
    # Reserved accepted orders cannot be abandoned by swapping strategy sources.
    from conftest import quote

    s.engine.ingest(quote(base=TEST_NOW, symbol="NSE:A000", token=257), TEST_NOW)
    order = s.engine.submit(candidate("pending", now=TEST_NOW, symbol="NSE:A000"), TEST_NOW)
    assert order["state"] == "ACCEPTED"
    with pytest.raises(SetupError, match="pending paper orders"):
        s.prep.install(installation(s))
    assert s.engine.orders()[0]["state"] == "ACCEPTED" and s.desk.research is None


def test_download_cancellation_and_restart_do_not_replay_partial_jobs(
    preparation_factory, monkeypatch
):
    s = preparation_factory()
    entered, release = threading.Event(), threading.Event()
    original = s.broker.get_daily_history

    def blocked(*args):
        entered.set()
        assert release.wait(3)
        return original(*args)

    monkeypatch.setattr(s.broker, "get_daily_history", blocked)
    request = DownloadRequest(
        universe="nifty100", request_id="a" * 32, revision=s.desk.revision, acknowledged=True
    )
    s.prep.start(request)
    assert entered.wait(3)
    s.prep.cancel()
    # Acquisition never holds the execution lock while a provider is blocked.
    with s.engine.lock:
        assert not s.engine.orders()
    release.set()
    s.prep.thread.join(3)
    assert s.prep.state["state"] == "cancelled" and s.desk.research is None
    path = s.prep.root / "latest.json"
    value = json.loads(path.read_text())
    value["state"] = "downloading"
    path.write_text(json.dumps(value))
    restarted = Preparation(s.desk, s.setup, lambda: TEST_NOW)
    assert restarted.view()["job"]["state"] == "interrupted" and restarted.thread is None


def test_external_errors_are_sanitized_and_never_authorize_a_mode(preparation_factory, monkeypatch):
    s = preparation_factory()

    def fail(*args, **kwargs):
        raise RuntimeError("SECRET_SESSION and provider details")

    monkeypatch.setattr(sources, "public_read", fail)
    request = DownloadRequest(
        universe="nifty100", request_id="a" * 32, revision=s.desk.revision, acknowledged=True
    )
    s.prep.start(request)
    s.prep.thread.join(3)
    view = s.prep.view()
    assert view["job"]["state"] == "failed" and "SECRET" not in json.dumps(view)
    assert s.desk.mode == "manual" and not s.engine.orders()


def test_daily_history_strict_completion_duplicates_and_no_early_availability(monkeypatch):
    from unittest.mock import Mock

    from trading_agent.broker.readonly_kite import BrokerUnavailable, ReadOnlyKite
    from trading_agent.models import Instrument

    client = Mock()
    monkeypatch.setattr("trading_agent.broker.readonly_kite.make_client", lambda *args: client)
    broker = ReadOnlyKite("INVENTED", "INVENTED")
    instrument = Instrument(symbol="NSE:DEMO", token=1, tick_size="0.05")
    rows = [
        dict(date=TEST_NOW + timedelta(days=i), open=500, high=501, low=499, close=500, volume=1000)
        for i in (-1, 0)
    ]
    client.historical_data.return_value = rows
    result = broker.get_daily_history(instrument, TEST_NOW - timedelta(days=2), TEST_NOW, TEST_NOW)
    from datetime import datetime

    assert len(result) == 1 and datetime.fromisoformat(result[0]["price_available_at"]) == TEST_NOW
    client.historical_data.return_value = [rows[0], rows[0]]
    with pytest.raises(BrokerUnavailable, match="malformed"):
        broker.get_daily_history(instrument, TEST_NOW - timedelta(days=2), TEST_NOW, TEST_NOW)


def test_official_inputs_reject_wrong_year_empty_actions_etf_and_duplicates():
    with pytest.raises(sources.SourceUnavailable):
        sources.action_symbols(b"[]", TEST_NOW.date() - timedelta(days=120), TEST_NOW.date())
    raw = json.dumps({"CM": [{"tradingDate": "26-Jan-2025"}] * 6}).encode()
    with pytest.raises(sources.SourceUnavailable):
        sources.proposed_sessions(raw, TEST_NOW.date())
    raw = (
        b"Company Name,Industry,Symbol,Series,ISIN Code\n"
        + b"INVENTED,test,DEMO,EQ,INF000000000\n" * 100
    )
    with pytest.raises(sources.SourceUnavailable):
        sources.constituents(raw, "nifty100")


def test_stale_day_and_symlink_selection_are_refused(preparation_factory, tmp_path):
    s = preparation_factory()
    download(s)
    s.clock[0] += timedelta(days=1)
    with pytest.raises(SetupError, match="another IST date"):
        s.prep.install(installation(s))
    target = tmp_path / "elsewhere"
    target.mkdir()
    (s.prep.root / "active.json").symlink_to(target / "active.json")
    with pytest.raises((SetupError, FileNotFoundError)):
        saved_profile(s.engine)


def test_data_change_and_custom_profile_override_cannot_silently_select_another_policy(
    preparation_factory,
):
    s = preparation_factory()
    download(s)
    s.prep.profile_override = True
    with pytest.raises(SetupError, match="TRADING_ANALYSIS_PROFILE"):
        s.prep.install(installation(s))
    s.prep.profile_override = False
    s.prep.install(installation(s))
    path = saved_profile(s.engine).parent / "daily" / "daily.jsonl"
    path.write_text(path.read_text() + "\n")
    with pytest.raises(SetupError, match="data changed"):
        saved_profile(s.engine)
    assert s.desk.mode == "manual" and not s.engine.orders()


@pytest.mark.parametrize("change", ["connection", "revision", "date"])
def test_install_rechecks_state_after_out_of_lock_validation(
    preparation_factory, monkeypatch, change
):
    import trading_agent.desk.preparation as module

    s = preparation_factory()
    download(s)
    body = installation(s)
    original = module.Research

    def validate(*args, **kwargs):
        # Another operator request can change authority while slower data/model loading runs.
        result = original(*args, **kwargs)
        if change == "connection":
            s.setup.stream = object()
        elif change == "revision":
            s.desk.set_mode("manual", TEST_NOW, s.desk.revision)
        else:
            s.clock[0] += timedelta(days=1)
        return result

    monkeypatch.setattr(module, "Research", validate)
    with pytest.raises(SetupError, match="changed|Choose Manual"):
        s.prep.install(body)
    s.setup.stream = None
    assert not (s.prep.root / "active.json").exists() and s.desk.research is None
    assert not s.engine.orders()


def test_official_source_reads_do_not_redirect_send_credentials_or_accept_unbounded_payload(
    monkeypatch,
):
    import httpx

    original = httpx.Client
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(302, headers={"Location": "https://untrusted.test/"})

    monkeypatch.setattr(
        httpx, "Client", lambda **kwargs: original(**kwargs, transport=httpx.MockTransport(handler))
    )
    with pytest.raises(sources.SourceUnavailable):
        sources.public_read(sources.HOLIDAYS)
    assert len(requests) == 1 and "Authorization" not in requests[0].headers
    with pytest.raises(sources.SourceUnavailable, match="SOURCE_NOT_ALLOWED"):
        sources.public_read("http://127.0.0.1/private")
    assert len(requests) == 1
    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kwargs: original(
            **kwargs,
            transport=httpx.MockTransport(lambda r: httpx.Response(200, content=b"x" * 5_000_001)),
        ),
    )
    with pytest.raises(sources.SourceUnavailable):
        sources.public_read(sources.HOLIDAYS)


def test_historical_limiter_reserves_shared_slots_without_risk_lock(monkeypatch):
    import trading_agent.broker.readonly_kite as module

    clock = [10.0]
    slept = []
    monkeypatch.setattr(module, "_history_next", 0.0)
    monkeypatch.setattr(module.time, "monotonic", lambda: clock[0])

    def sleep(delay):
        slept.append(delay)
        clock[0] += delay

    monkeypatch.setattr(module.time, "sleep", sleep)
    for _ in range(3):
        module.history_slot()
    assert slept == pytest.approx([0.4, 0.4]) and clock[0] == pytest.approx(10.8)


def test_existing_strategy_cannot_be_armed_during_new_profile_validation(
    preparation_factory, monkeypatch
):
    import trading_agent.desk.preparation as module
    from trading_agent.desk.service import DeskError

    s = preparation_factory()
    download(s)
    original = module.Research
    seen = []

    def validate(*args, **kwargs):
        result = original(*args, **kwargs)
        # Simulate a previously installed policy being present while a new one validates.
        s.desk.research = result
        s.desk.problem = ""
        with pytest.raises(DeskError, match="STRATEGY_INSTALLING"):
            s.desk.set_mode("automatic", TEST_NOW, s.desk.revision)
        seen.append(s.desk.installing)
        return result

    monkeypatch.setattr(module, "Research", validate)
    s.prep.install(installation(s))
    assert seen == [True] and not s.desk.installing and s.desk.mode == "manual"
    assert not s.engine.orders()


def test_empty_account_calendar_correction_is_explicit_and_keeps_cash_unchanged(
    preparation_factory,
):
    from datetime import time

    s = preparation_factory("long_term")
    s.engine.calendar.sessions[TEST_NOW.date()] = (time(9, 15), time(15, 15))
    download(s)
    view = s.prep.view()
    assert (
        view["can_correct_unused_calendar"]
        and view["calendar_conflicts"][0]["existing"] == "09:15–15:15"
    )
    with pytest.raises(SetupError, match="explicit correction"):
        s.prep.install(installation(s))
    s.prep.install(installation(s, correct_unused_calendar=True))
    assert s.engine.calendar.sessions[TEST_NOW.date()][1] == time(15, 30)
    assert not s.engine.orders() and s.engine.snapshot(TEST_NOW)["cash"] == "25000"
    assert s.desk.mode == "manual"


@pytest.mark.parametrize("usage", ["quote", "review"])
def test_used_account_calendar_cannot_be_corrected_by_acknowledgement(preparation_factory, usage):
    from datetime import time

    from trading_agent.execution.delivery import HoldingReview

    s = preparation_factory("intraday" if usage == "quote" else "long_term")
    s.engine.calendar.sessions[TEST_NOW.date()] = (time(9, 15), time(15, 15))
    if usage == "review":
        s.engine.review_holding(
            HoldingReview(
                symbol="NSE:A000",
                session_date=TEST_NOW.date(),
                no_corporate_action=True,
                reference="INVENTED used basis review",
            ),
            TEST_NOW,
        )
    download(s)
    assert not s.prep.view()["can_correct_unused_calendar"]
    with pytest.raises(SetupError, match="unused account"):
        s.prep.install(installation(s, correct_unused_calendar=True))
    assert s.engine.calendar.sessions[TEST_NOW.date()][1] == time(15, 15)
    assert s.desk.research is None and not s.engine.orders()


def test_calendar_usage_during_validation_prevents_correction(preparation_factory, monkeypatch):
    from datetime import time

    import trading_agent.desk.preparation as module
    from trading_agent.execution.delivery import HoldingReview

    s = preparation_factory("long_term")
    s.engine.calendar.sessions[TEST_NOW.date()] = (time(9, 15), time(15, 15))
    download(s)
    original = module.Research

    def validate(*args, **kwargs):
        result = original(*args, **kwargs)
        s.engine.review_holding(
            HoldingReview(
                symbol="NSE:A000",
                session_date=TEST_NOW.date(),
                no_corporate_action=True,
                reference="INVENTED concurrent basis review",
            ),
            TEST_NOW,
        )
        return result

    monkeypatch.setattr(module, "Research", validate)
    with pytest.raises(SetupError, match="was used"):
        s.prep.install(installation(s, correct_unused_calendar=True))
    assert s.engine.calendar.sessions[TEST_NOW.date()][1] == time(15, 15)
    assert not s.desk.installing and s.desk.research is None


def test_midnight_during_download_requires_fresh_sources(preparation_factory, monkeypatch):
    s = preparation_factory()
    original = s.broker.get_daily_history

    def history(*args, **kwargs):
        rows = original(*args, **kwargs)
        s.clock[0] += timedelta(days=1)
        return rows

    monkeypatch.setattr(s.broker, "get_daily_history", history)
    s.prep.start(
        DownloadRequest(
            universe="nifty100", request_id="e" * 32, revision=s.desk.revision, acknowledged=True
        )
    )
    s.prep.thread.join(3)
    assert s.prep.state["error"] == "DOWNLOAD_DATE_CHANGED" and s.prep.state["state"] == "failed"
    assert len(s.broker.calls) == 1 and s.desk.research is None


def test_extended_constituent_file_excludes_reits_trade_to_trade_and_dummy_rows_explicitly():
    import csv
    import io

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(("Company Name", "Industry", "Symbol", "Series", "ISIN Code"))
    for i in range(501):
        series = "RR" if i in (0, 1, 2) else "BE" if i in (3, 4) else "EQ"
        isin = "DUMMY" if i == 5 else f"INE{i:09}"
        writer.writerow((f"INVENTED {i}", "TEST", f"A{i:03}", series, isin))
    excluded = []
    result = sources.constituents(output.getvalue().encode(), "nifty500", exclusions=excluded)
    assert len(result) == 495 and len(excluded) == 6
    assert {r["reason"] for r in excluded} == {
        "UNSUPPORTED_SHARE_SERIES",
        "UNSUPPORTED_SHARE_IDENTIFIER",
    }
    assert result[0]["symbol"] == "NSE:A006"
