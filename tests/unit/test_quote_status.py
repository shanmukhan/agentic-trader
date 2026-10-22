import sqlite3
from datetime import timedelta
from decimal import Decimal

from conftest import NOW, quote

from trading_agent.execution.delivery import HoldingReview
from trading_agent.execution.quote_status import quote_status


def status(engine, now=NOW):
    with engine.lock, engine.db.transaction() as tx:
        return quote_status(engine, tx, "NSE:DEMO", now)


def persisted(engine):
    with sqlite3.connect(engine.settings.database) as db:
        assert Decimal(
            db.execute("SELECT value FROM meta WHERE key='cash'").fetchone()[0]
        ) == Decimal("25000")
        return list(db.iterdump())


def test_incoming_quote_blocked_by_daily_review_is_not_described_as_a_missing_feed(
    long_term_factory,
):
    e = long_term_factory(stream_tokens=(1,))
    assert not e.ingest(quote(), NOW)
    before = persisted(e)
    result = status(e)
    assert result["status"] == "PRICE_BASIS_REVIEW_REQUIRED"
    assert not result["usable"] and result["exchange_time"] is None
    assert "does not mean the broker has stopped" in result["detail"]
    assert not result["basis_reviewed"]
    assert persisted(e) == before
    with sqlite3.connect(e.settings.database) as db:
        assert db.execute("SELECT count(*) FROM quotes").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM fills").fetchone()[0] == 0
        assert db.execute("SELECT kind FROM events ORDER BY seq DESC LIMIT 1").fetchone()[0] == (
            "long_term_quote_blocked"
        )


def test_review_requires_new_quote_and_status_distinguishes_age_reconnect_and_disconnect(
    long_term_factory,
):
    e = long_term_factory(stream_tokens=(1,))
    e.ingest(quote(), NOW)
    e.review_holding(
        HoldingReview(
            symbol="NSE:DEMO",
            session_date=NOW.date(),
            no_corporate_action=True,
            reference="invented current basis review",
        ),
        NOW,
    )
    assert status(e)["status"] == "NO_ACCEPTED_QUOTE"
    assert e.ingest(quote(1), NOW + timedelta(seconds=1))
    assert status(e, NOW + timedelta(seconds=1))["usable"]
    assert status(e, NOW + timedelta(seconds=7))["status"] == "STALE_QUOTE"
    before = persisted(e)
    e.invalidate_quote("NSE:DEMO")
    assert status(e, NOW + timedelta(seconds=1))["status"] == "QUOTE_REJECTED"
    assert persisted(e) == before
    assert e.ingest(quote(2), NOW + timedelta(seconds=2))
    before = persisted(e)
    e.set_connected(False)
    assert status(e)["status"] == "FEED_DISCONNECTED"
    e.set_connected(True)
    assert status(e)["status"] == "AWAITING_NEW_QUOTE"
    assert persisted(e) == before


def test_next_day_review_requirement_takes_priority_over_yesterdays_stored_quote(long_term_factory):
    e = long_term_factory(stream_tokens=(1,))
    e.review_holding(
        HoldingReview(
            symbol="NSE:DEMO",
            session_date=NOW.date(),
            no_corporate_action=True,
            reference="invented previous day review",
        ),
        NOW,
    )
    e.ingest(quote(), NOW)
    result = status(e, NOW + timedelta(days=1))
    assert result["status"] == "PRICE_BASIS_REVIEW_REQUIRED"
    assert not result["usable"] and result["exchange_time"] is not None
