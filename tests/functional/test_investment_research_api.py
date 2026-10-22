"""Invented saved-data HTTP evidence; no broker, real-market or device acceptance."""

import copy
import json
import sqlite3
from datetime import timedelta
from decimal import Decimal as D

import pytest
from conftest import NOW, TOKEN, candidate, quote
from fastapi.testclient import TestClient

from trading_agent.api.app import create_app
from trading_agent.daily_research.dataset import DailyDataset
from trading_agent.daily_research.demo import create_daily_demo

AUTH = {"Authorization": "Bearer " + TOKEN}


def dump(engine):
    with sqlite3.connect(engine.settings.database) as db:
        return list(db.iterdump())


def authority(desk):
    return copy.deepcopy(
        (
            desk.mode,
            desk.mode_day,
            desk.reason,
            desk.revision,
            desk.last_analysis,
            desk.analysis_error,
            desk.engine.connected,
            desk.engine.faulted,
            desk.engine.bad_symbols,
            desk.engine.seen_symbols,
        )
    )


def test_http_auth_no_store_symbol_interval_whitelist_and_no_client_selected_paths(
    desk_factory,
    tmp_path,
):
    desk, profile, directory = desk_factory()
    engine = desk.engine
    trap = tmp_path / "client-selected.json"
    trap.write_text("deliberately invalid input; never selected by an HTTP query")
    with TestClient(
        create_app(engine, clock=lambda: NOW, background=False, desk=desk),
        base_url="http://127.0.0.1",
    ) as client:
        before, memory = dump(engine), authority(desk)
        assert client.get("/api/research/series").status_code == 401
        assert client.get("/api/research/series", params={"token": TOKEN}).status_code == 401
        response = client.get("/api/research/series", headers=AUTH)
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["x-frame-options"] == "DENY"
        data = response.json()
        assert data["symbol"] == "NSE:DEMO" and data["timeframe"] == "1d"
        assert len(data["bars"]) == 4 and data["quote"]["usable"]
        assert data["research"]["indicator_status"]["rsi14"]["value"] is None
        assert data["research"]["indicator_status"]["rsi14"]["state"] == "warming_up"
        assert data["research"]["benchmark"]["state"] == "unavailable"
        assert data["research"]["fundamentals"]["state"] == "unavailable"
        for private in (TOKEN, str(profile), str(directory), str(engine.settings.database)):
            assert private not in response.text
        # Extra path-like keys have no authority to choose the server's saved inputs.
        trapped = client.get(
            "/api/research/series",
            headers=AUTH,
            params={key: str(trap) for key in ("dataset", "context", "benchmark", "path")},
        )
        assert trapped.status_code == 200 and trapped.json() == data
        assert str(trap) not in trapped.text
        assert (
            client.get(
                "/api/research/series", headers=AUTH, params={"symbol": "NSE:SECOND"}
            ).status_code
            == 404
        )
        for query in (
            {"symbol": "../../private"},
            {"symbol": "NSE:demo"},
            {"timeframe": "1m"},
            {"timeframe": "5m"},
            {"timeframe": "1y"},
        ):
            assert client.get("/api/research/series", headers=AUTH, params=query).status_code == 422
        assert client.post("/api/research/series", headers=AUTH, json={}).status_code == 405
        assert dump(engine) == before and authority(desk) == memory


def test_all_intervals_are_pure_reads_beyond_approval_expiry_and_day_rollover(
    desk_factory,
    monkeypatch,
):
    desk, _, _ = desk_factory()
    engine = desk.engine
    desk.set_mode("approval", NOW, desk.revision)
    decision = desk.offer(candidate("pending-approval"), NOW, {"kind": "invented-screen"})
    assert decision["state"] == "awaiting_approval"
    order = engine.submit(candidate("partial-direct-order"), NOW)
    engine.ingest(quote(1, ask_size=3), NOW + timedelta(seconds=1))
    with sqlite3.connect(engine.settings.database) as db:
        fills = db.execute("SELECT quantity,price,fees FROM fills").fetchall()
        assert sum(row[0] for row in fills) == 3 < order["quantity"]
        cost = sum((D(price) * quantity + D(fees) for quantity, price, fees in fills), D(0))
        expected_cash = D("25000") - cost
        assert (
            D(db.execute("SELECT value FROM meta WHERE key='cash'").fetchone()[0]) == expected_cash
        )
        reserved, state = db.execute("SELECT reserved_cash,state FROM orders").fetchone()
        assert D(reserved) > 0 and state == "PARTIAL"
        assert D(db.execute("SELECT cost FROM positions").fetchone()[0]) == cost

    current = [NOW + timedelta(minutes=10)]
    with TestClient(
        create_app(engine, clock=lambda: current[0], background=False, desk=desk),
        base_url="http://127.0.0.1",
    ) as client:
        before, memory = dump(engine), authority(desk)

        def prohibited(*args, **kwargs):
            raise AssertionError("Research GET must not run account or strategy workflows")

        monkeypatch.setattr(desk, "view", prohibited)
        monkeypatch.setattr(desk, "tick", prohibited)
        monkeypatch.setattr(desk.research, "refresh", prohibited)
        monkeypatch.setattr(engine, "poll", prohibited)
        for moment in (NOW + timedelta(minutes=10), NOW + timedelta(days=1)):
            current[0] = moment
            for interval in ("1d", "1w", "1mo"):
                response = client.get(
                    "/api/research/series",
                    headers=AUTH,
                    params={"timeframe": interval},
                )
                assert response.status_code == 200 and not response.json()["quote"]["usable"]
                assert response.json()["timeframe"] == interval
                if interval != "1d":
                    view = response.json()
                    assert not view["bars"] and view["data_state"] == "missing"
                    assert not view["research"]["coverage"]["calendar_verified"]
                    assert all(
                        row["reason"] == "CALENDAR_COVERAGE_UNVERIFIED"
                        for row in view["research"]["partial_periods"]
                    )
                assert authority(desk) == memory and dump(engine) == before
        with sqlite3.connect(engine.settings.database) as db:
            assert (
                db.execute(
                    "SELECT state FROM desk_decisions WHERE id=?", (decision["id"],)
                ).fetchone()[0]
                == "awaiting_approval"
            )
            assert (
                D(db.execute("SELECT value FROM meta WHERE key='cash'").fetchone()[0])
                == expected_cash
            )
            assert db.execute("SELECT reserved_cash,state FROM orders").fetchone() == (
                reserved,
                state,
            )
            assert db.execute("SELECT quantity,price,fees FROM fills").fetchall() == fills


@pytest.mark.parametrize("failure", ["malformed_context", "changed_daily_input", "unexpected_read"])
def test_read_validation_errors_are_sanitized_without_fault_or_authority_revocation(
    desk_factory,
    monkeypatch,
    failure,
):
    desk, _, directory = desk_factory()
    desk.set_mode("approval", NOW, desk.revision)
    engine = desk.engine
    with TestClient(
        create_app(engine, clock=lambda: NOW, background=False, desk=desk),
        base_url="http://127.0.0.1",
    ) as client:
        before, memory = dump(engine), authority(desk)
        secret = "private local path and credential " + TOKEN
        if failure == "malformed_context":
            (directory / "investment-context.json").write_text(json.dumps({"private": secret}))
        elif failure == "changed_daily_input":
            with (directory / "daily.jsonl").open("a") as file:
                file.write("\n")
        else:

            def broken_read():
                raise OSError(secret)

            monkeypatch.setattr(desk.research.dataset, "fingerprints", broken_read)
        response = client.get("/api/research/series", headers=AUTH)
        assert response.status_code == 503 and response.headers["cache-control"] == "no-store"
        assert "failed validation or integrity" in response.json()["detail"]
        for private in (secret, TOKEN, str(directory), str(engine.settings.database)):
            assert private not in response.text
        assert authority(desk) == memory and dump(engine) == before
        assert not engine.faulted and engine.connected and desk.mode == "approval"


def test_legacy_raw_split_history_is_preserved_while_new_research_adjusts_with_known_action(
    desk_factory,
):
    desk, _, directory = desk_factory()
    path = directory / "daily.jsonl"
    records = [json.loads(line) for line in path.read_text().splitlines()]
    selected = [row for row in records if row["symbol"] == "NSE:DEMO"]
    for index, row in enumerate(selected):
        if index >= 2:
            for field in ("open", "high", "low", "close"):
                row[field] = str(D(row[field]) / 2)
        if index == 2:
            row["share_numerator"] = 2
    path.write_text("".join(json.dumps(row) + "\n" for row in records))
    desk.research.dataset = DailyDataset(directory)
    engine = desk.engine
    before, memory = dump(engine), authority(desk)
    with TestClient(
        create_app(engine, clock=lambda: NOW, background=False, desk=desk),
        base_url="http://127.0.0.1",
    ) as client:
        legacy = client.get("/api/analysis", headers=AUTH).json()
        fresh = client.get("/api/research/series", headers=AUTH).json()
        assert [D(row["close"]) for row in legacy["bars"]] == [
            D("497"),
            D("498"),
            D("249.5"),
            D("250"),
        ]
        assert [D(row["close"]) for row in fresh["bars"]] == [
            D("248.5"),
            D("249"),
            D("249.5"),
            D("250"),
        ]
        assert all(row["quality"] == "reviewed_raw_daily" for row in legacy["bars"])
        assert fresh["bars"][0]["raw_close"] == "497"
        assert D(fresh["bars"][0]["volume"]) == 200000
        assert legacy["bars"][0]["volume"] == 100000
        assert fresh["bars"][0]["available_at"] == fresh["bars"][2]["available_at"]
        assert fresh["bars"][0]["available_at"] > legacy["bars"][0]["available_at"]
        assert "share-adjusted" in fresh["source"]["price_basis"]
        assert (
            client.get("/api/analysis", headers=AUTH, params={"timeframe": "1m"}).status_code == 200
        )
        assert (
            client.get("/api/analysis", headers=AUTH, params={"timeframe": "1w"}).status_code == 422
        )
        assert authority(desk) == memory and dump(engine) == before


def test_api_clips_display_after_full_350_session_indicator_warmup(desk_factory, tmp_path):
    desk, _, _ = desk_factory()
    directory = tmp_path / "long-invented-daily-history"
    now = create_daily_demo(directory, sessions=350)
    desk.research.dataset = DailyDataset(directory)
    records = [
        json.loads(line)
        for line in (directory / "daily.jsonl").read_text().splitlines()
        if json.loads(line)["symbol"] == "NSE:THIN"
    ]
    expected_first_sma50 = sum((D(row["close"]) for row in records[1:51]), D(0)) / 50
    engine = desk.engine
    before, memory = dump(engine), authority(desk)
    with TestClient(
        create_app(engine, clock=lambda: now, background=False, desk=desk),
        base_url="http://127.0.0.1",
    ) as client:
        response = client.get(
            "/api/research/series",
            headers=AUTH,
            params={"symbol": "NSE:THIN"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["truncated"] and data["bar_limit"] == len(data["bars"]) == 300
        assert data["research"]["coverage"]["computed_bars"] == 350
        assert data["research"]["coverage"]["displayed_bars"] == 300
        assert data["bars"][0]["session"] == records[50]["session"]
        assert D(data["bars"][0]["sma50"]) == expected_first_sma50
        assert data["bars"][0]["rsi14"] is not None
        assert data["bars"][0]["macd_signal"] is not None
        assert data["bars"][148]["sma200"] is None
        assert data["bars"][149]["sma200"] is not None
        assert authority(desk) == memory and dump(engine) == before
