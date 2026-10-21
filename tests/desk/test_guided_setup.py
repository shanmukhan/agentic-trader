"""Invented source/broker evidence; no assertion of real market acceptance."""

from datetime import timedelta

import pytest
from preparation_support import download

from trading_agent.api.setup import SetupError
from trading_agent.desk.guided import GuidedConfirm, GuidedPreview, GuidedSetup


def preview(s, guide):
    return guide.preview(GuidedPreview(revision=s.desk.revision, strategy_mode="rules"))


def confirm(plan):
    return GuidedConfirm(preview_sha256=plan["preview_sha256"], acknowledged=True)


def test_preview_is_read_only_and_confirmation_coordinates_existing_controls_once(
    preparation_factory,
    monkeypatch,
):
    s = preparation_factory("long_term")
    download(s)
    e = s.engine
    before = e.snapshot(s.clock[0])
    config = s.setup.config.read_bytes()
    guide = GuidedSetup(s.prep)
    result = preview(s, guide)
    assert result["plan"]["symbols"] == ["NSE:A000", *[f"NSE:A{i:03}" for i in range(3, 12)]]
    assert result["plan"]["basis_reviews"] == result["plan"]["symbols"]
    assert "binding" not in result and not s.desk.research
    assert e.snapshot(s.clock[0]) == before and s.setup.config.read_bytes() == config
    assert not (s.prep.root / "active.json").exists()
    calls = []
    monkeypatch.setattr(s.setup, "connect", lambda: calls.append("connect"))
    completed = guide.confirm(confirm(result))
    assert completed["state"] == "complete" and calls == ["connect"]
    assert s.desk.mode == "manual" and not s.desk.installing and not e.orders()
    assert e.snapshot(s.clock[0])["cash"] == before["cash"]
    with e.db.transaction() as tx:
        assert all(
            e.long_term.reviewed(tx, symbol, s.clock[0]) for symbol in result["plan"]["symbols"]
        )
        assert (
            tx.execute("SELECT COUNT(*) FROM events WHERE kind='long_term_review'").fetchone()[0]
            == 10
        )
    assert guide.confirm(confirm(result)) == completed
    assert calls == ["connect"]
    restarted = GuidedSetup(s.prep)
    assert restarted.confirm(confirm(result)) == completed and calls == ["connect"]


@pytest.mark.parametrize("change", ["expired", "revision", "cash", "source", "date", "kill"])
def test_changed_or_expired_review_does_not_disconnect_or_install(
    preparation_factory,
    monkeypatch,
    change,
):
    s = preparation_factory("long_term")
    download(s)
    guide = GuidedSetup(s.prep)
    plan = preview(s, guide)
    calls = []
    monkeypatch.setattr(s.setup, "disconnect", lambda: calls.append("disconnect"))
    if change == "expired":
        s.clock[0] += timedelta(seconds=120)
    elif change == "revision":
        s.desk.pause(s.clock[0], "TEST_OTHER_TAB")
    elif change == "source":
        (s.prep.root / s.prep.state["job_id"] / "actions.json").write_text("[]")
    elif change == "date":
        s.clock[0] += timedelta(days=1)
    else:
        with s.engine.db.transaction() as tx:
            s.engine.db.set(
                tx, "cash" if change == "cash" else "kill", "24999" if change == "cash" else "true"
            )
    with pytest.raises(SetupError):
        guide.confirm(confirm(plan))
    assert not calls and not s.desk.research and not s.engine.orders()
    assert not s.desk.installing


def test_unused_calendar_correction_is_listed_and_applied_only_after_confirmation(
    preparation_factory,
    monkeypatch,
):
    from datetime import time

    s = preparation_factory("long_term")
    day = s.clock[0].date()
    s.engine.calendar.sessions[day] = (time(9, 15), time(15, 15))
    download(s)
    guide = GuidedSetup(s.prep)
    plan = preview(s, guide)
    assert plan["plan"]["calendar_conflicts"] == [
        {"date": day.isoformat(), "existing": "09:15–15:15", "proposed": "09:15–15:30"}
    ]
    assert s.engine.calendar.sessions[day][1] == time(15, 15)
    monkeypatch.setattr(s.setup, "connect", lambda: None)
    guide.confirm(confirm(plan))
    assert s.engine.calendar.sessions[day][1] == time(15, 30)


def test_connection_failure_preserves_saved_steps_and_never_retries_implicitly(
    preparation_factory,
    monkeypatch,
):
    s = preparation_factory("long_term")
    download(s)
    guide = GuidedSetup(s.prep)
    plan = preview(s, guide)
    calls = []

    def fail():
        calls.append(1)
        raise SetupError("INVENTED entitlement failure")

    monkeypatch.setattr(s.setup, "connect", fail)
    with pytest.raises(SetupError, match="entitlement failure"):
        guide.confirm(confirm(plan))
    assert guide.view()["state"] == "stopped" and s.desk.research
    assert s.desk.mode == "manual" and not s.desk.installing and not s.engine.orders()
    with pytest.raises(SetupError, match="already stopped"):
        guide.confirm(confirm(plan))
    assert calls == [1]
    monkeypatch.setattr(s.setup, "connect", lambda: calls.append(2))
    fresh = preview(s, guide)
    assert fresh["plan"]["basis_reviews"] == []
    assert guide.confirm(confirm(fresh))["state"] == "complete" and calls == [1, 2]


def test_quarantine_is_never_cleared_and_unconfigured_ml_never_falls_back(
    preparation_factory,
    monkeypatch,
):
    s = preparation_factory("long_term")
    download(s)
    with s.engine.db.transaction() as tx:
        s.engine.db.set(tx, "lt_quarantine:NSE:A000", "INVENTED blocked source")
    guide = GuidedSetup(s.prep)
    plan = preview(s, guide)
    assert plan["plan"]["manual_basis_reviews"] == ["NSE:A000"]
    assert "NSE:A000" not in plan["plan"]["basis_reviews"]
    with pytest.raises(SetupError, match="No validated ML"):
        guide.preview(GuidedPreview(revision=s.desk.revision, strategy_mode="rules_ml"))
    monkeypatch.setattr(s.setup, "connect", lambda: None)
    guide.confirm(confirm(plan))
    with s.engine.db.transaction() as tx:
        assert not s.engine.long_term.reviewed(tx, "NSE:A000", s.clock[0])
        assert (
            tx.execute("SELECT value FROM meta WHERE key='lt_quarantine:NSE:A000'").fetchone()[0]
            == "INVENTED blocked source"
        )


def test_interrupted_attempt_and_unacknowledged_confirmation_cannot_replay(preparation_factory):
    from pydantic import ValidationError

    s = preparation_factory()
    download(s)
    guide = GuidedSetup(s.prep)
    plan = preview(s, guide)
    with pytest.raises(ValidationError):
        GuidedConfirm(preview_sha256=plan["preview_sha256"], acknowledged=False)
    guide._save(state="applying", phase="INVENTED crash")
    recovered = GuidedSetup(s.prep)
    assert recovered.view()["state"] == "interrupted"
    with pytest.raises(SetupError, match="interrupted"):
        recovered.confirm(confirm(plan))
    assert not s.desk.research and not s.engine.orders()


def test_pending_order_cannot_be_cancelled_or_abandoned_by_guided_setup(preparation_factory):
    from conftest import candidate, quote

    s = preparation_factory()
    download(s)
    s.engine.ingest(quote(base=s.clock[0], symbol="NSE:A000", token=257), s.clock[0])
    order = s.engine.submit(
        candidate("INVENTED-pending", now=s.clock[0], symbol="NSE:A000"), s.clock[0]
    )
    assert order["state"] == "ACCEPTED"
    before = s.engine.snapshot(s.clock[0])
    with pytest.raises(SetupError, match="pending paper orders"):
        preview(s, GuidedSetup(s.prep))
    assert s.engine.orders()[0]["state"] == "ACCEPTED"
    assert s.engine.snapshot(s.clock[0]) == before and not s.desk.research


def test_existing_supported_holding_is_retained_without_changed_money_or_review(
    preparation_factory,
    monkeypatch,
):
    from conftest import candidate, quote

    from trading_agent.execution.delivery import HoldingReview
    from trading_agent.persistence.database import Database

    s = preparation_factory("long_term")
    symbol, token = "NSE:A050", 257 + 50 * 256
    s.engine.settings = s.engine.settings.model_copy(update={"stream_tokens": (token,)})
    s.engine.review_holding(
        HoldingReview(
            symbol=symbol,
            session_date=s.clock[0].date(),
            no_corporate_action=True,
            reference="INVENTED independently reviewed holding basis",
        ),
        s.clock[0],
    )
    s.engine.ingest(quote(base=s.clock[0], symbol=symbol, token=token), s.clock[0])
    order = s.engine.submit(candidate("INVENTED-held", now=s.clock[0], symbol=symbol), s.clock[0])
    assert order["state"] == "ACCEPTED"
    s.clock[0] += timedelta(seconds=1)
    s.engine.ingest(quote(base=s.clock[0], symbol=symbol, token=token), s.clock[0])
    # Keep the config writer's unchanged-policy check consistent with the selected feed.
    s.setup.select_symbols({"symbols": [symbol]})
    download(s)
    guide = GuidedSetup(s.prep)
    plan = preview(s, guide)
    assert plan["plan"]["held_symbols"] == [symbol]
    assert plan["plan"]["symbols"][0] == symbol and symbol not in plan["plan"]["basis_reviews"]
    with s.engine.db.transaction() as tx:
        position = dict(tx.execute("SELECT * FROM positions WHERE symbol=?", (symbol,)).fetchone())
        cash = s.engine.db.get(tx, "cash")
        original_review = tx.execute(
            "SELECT value FROM meta WHERE key=?",
            ("lt_review:" + s.clock[0].date().isoformat() + ":" + symbol,),
        ).fetchone()[0]
    monkeypatch.setattr(s.setup, "connect", lambda: None)
    guide.confirm(confirm(plan))
    with s.engine.db.transaction() as tx:
        assert (
            dict(tx.execute("SELECT * FROM positions WHERE symbol=?", (symbol,)).fetchone())
            == position
        )
        assert s.engine.db.get(tx, "cash") == cash
        assert (
            tx.execute(
                "SELECT value FROM meta WHERE key=?",
                ("lt_review:" + s.clock[0].date().isoformat() + ":" + symbol,),
            ).fetchone()[0]
            == original_review
        )
        Database.reconcile(tx)
