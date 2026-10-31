"""Synthetic official membership, broker history and cash; no market acceptance."""

import csv
import io
import sqlite3
from contextlib import closing
from decimal import Decimal

import pytest
from conftest import TOKEN
from fastapi.testclient import TestClient

from trading_agent.api.app import create_app
from trading_agent.desk import sources
from trading_agent.desk.guided import GuidedConfirm, GuidedPreview, GuidedSetup
from trading_agent.desk.preparation import DownloadRequest
from trading_agent.risk.policy import policy_fingerprint

AUTH = {"Authorization": "Bearer " + TOKEN}


def fifty_sources(monkeypatch):
    original = sources.public_read

    def read(url, params=None):
        raw = original(url, params)
        if url != sources.UNIVERSES["nifty50"]:
            return raw
        reader = csv.DictReader(io.StringIO(raw.decode()))
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=reader.fieldnames)
        writer.writeheader()
        writer.writerows(list(reader)[:50])
        return output.getvalue().encode()

    monkeypatch.setattr(sources, "public_read", read)


def financial_state(engine):
    with closing(sqlite3.connect(engine.settings.database)) as db:
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert Decimal(
            db.execute("SELECT value FROM meta WHERE key='cash'").fetchone()[0]
        ) == Decimal("25000.00")
        return {
            table: db.execute('SELECT * FROM "' + table + '"').fetchall()
            for table in ("orders", "fills", "positions", "meta")
        }


def test_nifty50_guided_setup_monitors_every_member_including_explicit_data_exclusions(
    preparation_factory, monkeypatch
):
    s = preparation_factory()
    fifty_sources(monkeypatch)
    s.setup.check_profile()
    before = financial_state(s.engine)
    policy = policy_fingerprint(s.engine.settings)
    s.prep.start(
        DownloadRequest(
            universe="nifty50", request_id="9" * 32, revision=s.desk.revision, acknowledged=True
        )
    )
    s.prep.thread.join(5)
    assert s.prep.state["state"] == "ready_for_review"
    assert s.prep.state["constituent_rows"] == 50
    guide = GuidedSetup(s.prep)
    plan = guide.preview(GuidedPreview(revision=s.desk.revision, strategy_mode="rules"))
    assert plan["plan"]["symbols"] == [f"NSE:A{i:03}" for i in range(50)]
    monkeypatch.setattr(s.setup, "connect", lambda: None)
    result = guide.confirm(GuidedConfirm(preview_sha256=plan["preview_sha256"], acknowledged=True))
    assert result["state"] == "complete"
    view = s.desk.view(s.clock[0])
    assert len(s.engine.settings.stream_tokens) == 50
    assert view["monitoring"]["monitored_count"] == 50
    assert view["monitoring"]["execution_covered_count"] == 48
    assert len(s.desk.research.result["rows"]) == 50
    with s.engine.db.read_snapshot() as tx:
        assert len(s.desk.shortlist(tx)["symbols"]) == 50
    assert s.desk.mode == "manual"
    assert policy_fingerprint(s.engine.settings) == policy
    assert financial_state(s.engine) == before


def test_official_selector_raises_legacy_capacity_without_requesting_manual_names(
    preparation_factory, monkeypatch
):
    from preparation_support import download, installation

    s = preparation_factory()
    download(s)
    s.prep.install(installation(s))
    s.engine.settings = s.engine.settings.model_copy(update={"stream_limit": 10})
    # Mirror the legacy capacity in its private config, without changing its financial policy.
    s.setup._persist_config(stream_limit=10)
    fifty_sources(monkeypatch)
    official_read = sources.public_read
    monkeypatch.setattr(
        sources,
        "public_read",
        lambda url, params=None: (
            (b"\xef\xbb\xbf" if url == sources.UNIVERSES["nifty50"] else b"")
            + official_read(url, params)
        ),
    )
    before = financial_state(s.engine)
    policy = policy_fingerprint(s.engine.settings)
    app = create_app(
        s.engine, setup=s.setup, desk=s.desk, clock=lambda: s.clock[0], background=False
    )
    with TestClient(app, base_url="http://127.0.0.1") as client:
        path = "/api/desk/universe/nifty50"
        body = {"revision": s.desk.revision, "acknowledged": True}
        assert client.post(path, json=body).status_code == 401
        assert (
            client.post(path, headers=AUTH, json={**body, "acknowledged": False}).status_code == 422
        )
        response = client.post(path, headers=AUTH, json=body)
        assert response.status_code == 200, response.text
        assert response.json()["selection"]["members"] == 50
        import hashlib

        saved_source = s.setup.path.with_suffix(".nifty50.csv").read_bytes()
        assert saved_source.startswith(b"\xef\xbb\xbf")
        assert (
            hashlib.sha256(saved_source).hexdigest()
            == response.json()["selection"]["source_sha256"]
        )
        assert len(s.engine.settings.stream_tokens) == 50
        assert s.engine.settings.stream_limit == 50
        assert s.engine.settings.automatic_universe == "nifty50"
        assert len(response.json()["desk"]["discovery"]["rows"]) == 50
        assert client.get("/api/setup", headers=AUTH).json()["automatic_universe"] == "nifty50"
        assert financial_state(s.engine) == before
        assert policy_fingerprint(s.engine.settings) == policy
        assert s.engine.settings.max_positions == 2


@pytest.mark.parametrize("universe", ["nifty50", "nifty100", "nifty500"])
def test_universe_sizes_are_verified_not_silently_reduced_to_ten(universe):
    limit = sources.UNIVERSE_SIZES[universe]
    raw = "Company Name,Industry,Symbol,Series,ISIN Code\n" + "".join(
        f"Test {i},TEST,T{i},EQ,INE{i:09}\n" for i in range(limit)
    )
    assert len(sources.constituents(raw.encode(), universe)) == limit
    with pytest.raises(sources.SourceUnavailable):
        sources.constituents(("\n".join(raw.splitlines()[:11]) + "\n").encode(), universe)


def test_all_fifty_live_signals_are_checked_without_rest_delay_and_existing_risk_caps_still_apply(
    preparation_factory, monkeypatch
):
    import json
    import time
    from datetime import timedelta
    from types import SimpleNamespace

    from preparation_support import download

    from trading_agent.desk.signals import AnalysisWorker
    from trading_agent.market_data.repository import store_candles
    from trading_agent.paper.demo import SIGNAL, WARM, demo_quote, signal_candle, warmup

    s = preparation_factory()
    original = sources.public_read

    def source(url, params=None):
        raw = original(url, params)
        if url == sources.ACTIONS:
            rows = json.loads(raw)
            for row in rows:
                row["symbol"] = "OUTSIDE50"
            return json.dumps(rows).encode()
        return raw

    monkeypatch.setattr(sources, "public_read", source)
    original_history = s.broker.get_daily_history

    def full_history(item, *args):
        if item.symbol == "NSE:A002":
            other = item.model_copy(update={"symbol": "NSE:A003", "token": 257 + 3 * 256})
            return [{**row, "symbol": item.symbol} for row in original_history(other, *args)]
        return original_history(item, *args)

    monkeypatch.setattr(s.broker, "get_daily_history", full_history)
    download(s, "nifty50")
    guide = GuidedSetup(s.prep)
    preview = guide.preview(GuidedPreview(revision=s.desk.revision, strategy_mode="rules"))
    monkeypatch.setattr(s.setup, "connect", lambda: None)
    guide.confirm(GuidedConfirm(preview_sha256=preview["preview_sha256"], acknowledged=True))
    e = s.engine
    offset = s.clock[0].date() - WARM.date()
    shift = timedelta(days=offset.days)
    clock = s.clock
    clock[0] = WARM + shift
    e.set_connected(True)  # Invented connected feed for this simulated execution test.
    with e.db.read_snapshot() as tx:
        instruments = list(
            tx.execute(
                "SELECT symbol,token FROM instruments WHERE token IN ("
                + ",".join("?" for _ in e.settings.stream_tokens)
                + ")",
                e.settings.stream_tokens,
            )
        )
    assert len(instruments) == 50 and len(s.desk.execution_tokens) == 50
    # Invented Kite-shaped quotes exercise the production source guard; no broker acceptance.
    for item in instruments:
        e.ingest(
            demo_quote(clock[0]).model_copy(
                update={"symbol": item[0], "token": item[1], "source": "kite"}
            ),
            clock[0],
        )
    s.desk.set_mode("automatic", clock[0], s.desk.revision)
    reads = []

    def seed(item, *args):
        reads.append(item.symbol)
        return [
            bar.model_copy(update={"symbol": item.symbol, "start": bar.start + shift})
            for bar in warmup()
        ]

    setup = SimpleNamespace(
        uses_persisted_candles=True,
        profile_revision=1,
        broker=lambda: SimpleNamespace(get_historical_candles=seed),
    )
    worker = AnalysisWorker(s.desk, setup, lambda: clock[0])
    try:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            worker.evaluate(clock[0])
            if getattr(s.desk, "intraday_status", {}).get("seeded") == 50:
                break
            time.sleep(0.01)
        assert s.desk.intraday_status["seeded"] == 50
        assert len(reads) == 50
        assert not e.orders()
        clock[0] = SIGNAL + shift
        bars = []
        for item in instruments:
            e.ingest(
                demo_quote(clock[0], bid="501", volume=33000).model_copy(
                    update={"symbol": item[0], "token": item[1], "source": "kite"}
                ),
                clock[0],
            )
            bars.append(
                signal_candle().model_copy(
                    update={"symbol": item[0], "start": signal_candle().start + shift}
                )
            )
        store_candles(e.db, bars, clock[0])
        worker.evaluate(clock[0])
        assert len(reads) == 50, "Completed live bars must not trigger another REST batch"
        assert len(s.desk.intraday_status["symbols"]) == 50
        assert all(row["state"] == "evaluated" for row in s.desk.intraday_status["symbols"])
        decisions = s.desk.view(clock[0])["decisions"]
        assert len(decisions) == 50
        assert (
            0 < sum(r["state"] == "submitted" for r in decisions) <= e.settings.max_positions == 2
        ), [(r.get("state"), r.get("outcome"), r.get("review")) for r in decisions[:3]]
        worker.evaluate(clock[0])
        assert len(s.desk.view(clock[0])["decisions"]) == 50
        later = clock[0] + timedelta(seconds=1)
        for item in instruments:
            e.ingest(
                demo_quote(later, bid="501", volume=34000).model_copy(
                    update={"symbol": item[0], "token": item[1], "source": "kite"}
                ),
                later,
            )
        with closing(sqlite3.connect(e.settings.database)) as db:
            fills = db.execute("SELECT price,quantity,fees FROM fills").fetchall()
            assert fills
            debit = sum((Decimal(p) * q + Decimal(f) for p, q, f in fills), Decimal(0))
            cash = Decimal(db.execute("SELECT value FROM meta WHERE key='cash'").fetchone()[0])
            assert cash == Decimal("25000") - debit
            assert db.execute("SELECT COUNT(*) FROM positions").fetchone()[0] <= 2
            assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    finally:
        worker.close()
