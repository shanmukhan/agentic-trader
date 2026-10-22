"""Authenticated synthetic draft workflows with independently verified account isolation."""

import json
import sqlite3
from contextlib import closing
from datetime import timedelta
from decimal import Decimal as D

import pytest
from conftest import NOW, TOKEN, candidate, quote
from fastapi.testclient import TestClient

from trading_agent.api.app import create_app
from trading_agent.investment_research import policy_store
from trading_agent.investment_research.policy_store import InvestmentPolicyStore

AUTH = {"Authorization": "Bearer " + TOKEN}
PATH = "/api/investment-policies"


def draft(label="Research only", *, cadence="monthly"):
    return {
        "label": label,
        "parameters": {
            "horizon_unit": "months",
            "horizon_count": 18,
            "review_cadence": cadence,
        },
    }


def account_state(desk):
    with closing(sqlite3.connect(desk.engine.settings.database)) as connection:
        connection.row_factory = sqlite3.Row
        fills = connection.execute("SELECT quantity,price,fees FROM fills").fetchall()
        quantity = sum(fill["quantity"] for fill in fills)
        cost = sum((D(fill["price"]) * fill["quantity"] + D(fill["fees"]) for fill in fills), D(0))
        fees = sum((D(fill["fees"]) for fill in fills), D(0))
        cash = D(connection.execute("SELECT value FROM meta WHERE key='cash'").fetchone()[0])
        held = connection.execute("SELECT quantity,cost FROM positions").fetchone()
        assert quantity == held["quantity"] == 3
        assert cost == D(held["cost"]) and cash == D("25000") - cost
        assert fees == D(
            connection.execute("SELECT value FROM meta WHERE key='fees'").fetchone()[0]
        )
        return list(connection.iterdump()), (
            desk.mode,
            desk.revision,
            desk.reason,
            desk.engine.connected,
            desk.engine.faulted,
        )


@pytest.fixture
def drafts_api(tmp_path, desk_factory, monkeypatch):
    desk, _, _ = desk_factory()
    desk.engine.submit(candidate(), NOW)
    desk.engine.ingest(quote(1, ask_size=3), NOW + timedelta(seconds=1))
    desk.set_mode("approval", NOW + timedelta(seconds=1), desk.revision)
    store = InvestmentPolicyStore(tmp_path / "private-investment-drafts")
    app = create_app(
        desk.engine,
        desk=desk,
        investment_policies=store,
        clock=lambda: NOW + timedelta(seconds=1),
        background=False,
    )
    with TestClient(app, base_url="http://127.0.0.1") as client:

        def prohibited(*args, **kwargs):
            raise AssertionError("Draft evidence must not call account or feed workflows")

        with monkeypatch.context() as guard:
            for name in ("set_mode", "tick", "offer"):
                guard.setattr(desk, name, prohibited)
            for name in ("submit", "ingest", "set_connected", "poll"):
                guard.setattr(desk.engine, name, prohibited)
            yield client, store, desk


def preview(client, value=None):
    value = draft() if value is None else value
    response = client.post(PATH + "/preview", headers=AUTH, json={"draft": value})
    assert response.status_code == 200
    return response.json()


def saved_body(client, value=None):
    value = draft() if value is None else value
    inspected = preview(client, value)
    return {"draft": value, "preview_sha256": inspected["preview_sha256"], "acknowledged": True}


def test_reads_preview_and_saved_snapshots_do_not_change_partial_fill_cash_fees_or_authority(
    drafts_api,
):
    client, store, desk = drafts_api
    before = account_state(desk)
    response = client.get(PATH, headers=AUTH)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.json()["drafts"] == []
    assert response.json()["activation_supported"] is False
    assert response.json()["backtest_supported"] is False
    assert len(response.json()["field_definitions"]) == 25
    inspected = preview(client)
    assert inspected["draft"]["parameters"]["review_cadence"] == "monthly"
    assert inspected["draft"]["parameters"]["stop_pct"] is None
    assert inspected["draft"]["state"] == "incomplete"
    assert inspected["draft"]["policy_version_id"] is None
    assert not store.root.exists()
    body = saved_body(client)
    saved = client.post(PATH, headers=AUTH, json=body)
    assert saved.status_code == 201
    snapshot = saved.json()["draft"]
    assert snapshot["draft_id"] == "draft-" + body["preview_sha256"]
    assert client.post(PATH, headers=AUTH, json=body).status_code == 200
    fetched = client.get(PATH + "/" + snapshot["draft_id"], headers=AUTH)
    assert fetched.json()["draft"] == snapshot
    assert client.get(PATH, headers=AUTH).json()["drafts"] == [snapshot]
    for private in (TOKEN, str(store.root), str(desk.engine.settings.database)):
        assert private not in fetched.text
    assert account_state(desk) == before


def test_authentication_origin_and_route_limits_reject_without_creating_storage(drafts_api):
    client, store, desk = drafts_api
    before = account_state(desk)
    for path in (PATH, PATH + "/draft-" + "a" * 64):
        assert client.get(path).status_code == 401
    body = saved_body(client)
    for path, value in ((PATH + "/preview", {"draft": draft()}), (PATH, body)):
        assert client.post(path, json=value).status_code == 401
        denied = client.post(
            path, headers={**AUTH, "Origin": "https://foreign.invalid"}, json=value
        )
        assert denied.status_code == 403
    assert client.get(PATH + "/draft-" + "a" * 64, headers=AUTH).status_code == 404
    assert client.post(PATH + "/activate", headers=AUTH, json=body).status_code == 405
    assert client.delete(PATH + "/draft-" + "a" * 64, headers=AUTH).status_code == 405
    assert not store.root.exists()
    assert account_state(desk) == before


@pytest.mark.parametrize(
    "value",
    [
        {"draft": None},
        {"draft": []},
        {"draft": {"source_url": "https://private.invalid"}},
        {"draft": {"parameters": {"command": "touch /operator/account"}}},
        {"draft": {"parameters": {"horizon_count": True}}},
        {"draft": {"parameters": {"horizon_count": 1.5}}},
        {"draft": {"parameters": {"cash_reserve_pct": 20.0}}},
        {"draft": draft(), "source_path": "/operator/account.sqlite3"},
    ],
)
def test_invalid_or_operator_capability_fields_rejected_without_storage(drafts_api, value):
    client, store, desk = drafts_api
    before = account_state(desk)
    response = client.post(PATH + "/preview", headers=AUTH, json=value)
    assert response.status_code == 422
    assert not store.root.exists()
    assert account_state(desk) == before


def test_strict_json_body_budget_and_true_acknowledgement_are_enforced(drafts_api):
    client, store, desk = drafts_api
    before = account_state(desk)
    for content in (
        b"\xff",
        b'{"draft":{},"draft":{}}',
        b'{"draft":{"parameters":{"horizon_count":NaN}}}',
        b'{"draft":{"parameters":{"horizon_count":1e999}}}',
        b'{"draft":' + b"[" * 1200 + b"0" + b"]" * 1200 + b"}",
    ):
        assert client.post(PATH + "/preview", headers=AUTH, content=content).status_code == 422
    assert client.post(PATH + "/preview", headers=AUTH, content=" " * 16385).status_code == 413
    body = saved_body(client)
    for acknowledgement in (False, 1, "true", None):
        assert (
            client.post(
                PATH, headers=AUTH, json={**body, "acknowledged": acknowledgement}
            ).status_code
            == 422
        )
    assert client.post(PATH, headers=AUTH, json={**body, "activation": True}).status_code == 422
    assert (
        client.post(PATH, headers=AUTH, json={**body, "preview_sha256": "f" * 63}).status_code
        == 422
    )
    duplicate = json.dumps(body)[:-1] + ',"acknowledged":false}'
    assert client.post(PATH, headers=AUTH, content=duplicate).status_code == 422
    assert not store.root.exists()
    assert account_state(desk) == before


def test_review_hash_binds_label_and_all_choices_and_semantic_hash_excludes_label(drafts_api):
    client, store, desk = drafts_api
    before = account_state(desk)
    body = saved_body(client)
    for value in (draft("Edited label"), draft(cadence="quarterly")):
        response = client.post(PATH, headers=AUTH, json={**body, "draft": value})
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "DRAFT_PREVIEW_CHANGED"
    assert not store.root.exists()
    first = client.post(PATH, headers=AUTH, json=body).json()["draft"]
    changed = draft("Separate scenario", cadence="quarterly")
    second = client.post(PATH, headers=AUTH, json=saved_body(client, changed)).json()["draft"]
    assert second["draft_id"] != first["draft_id"]
    assert second["draft_sha256"] != first["draft_sha256"]
    assert len(client.get(PATH, headers=AUTH).json()["drafts"]) == 2
    assert account_state(desk) == before


def test_storage_tampering_failures_are_sanitized_without_fault_or_mode_change(
    drafts_api, monkeypatch
):
    client, store, desk = drafts_api
    before = account_state(desk)
    snapshot = client.post(PATH, headers=AUTH, json=saved_body(client)).json()["draft"]
    path = store.root / (snapshot["draft_id"] + ".json")
    content = json.loads(path.read_text())
    content["draft"]["label"] = "PRIVATE tampered evidence " + TOKEN
    path.write_text(json.dumps(content))
    for endpoint in (PATH, PATH + "/" + snapshot["draft_id"]):
        response = client.get(endpoint, headers=AUTH)
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "DRAFT_STORAGE_UNAVAILABLE"
        assert "PRIVATE" not in response.text and TOKEN not in response.text

    def broken():
        raise OSError("PRIVATE disk path " + str(store.root) + " " + TOKEN)

    monkeypatch.setattr(store, "list", broken)
    response = client.get(PATH, headers=AUTH)
    assert (
        response.status_code == 503
        and "PRIVATE" not in response.text
        and TOKEN not in response.text
    )
    assert account_state(desk) == before


def test_bounded_save_admission_preserves_existing_evidence_and_account(drafts_api, monkeypatch):
    client, _, desk = drafts_api
    before = account_state(desk)
    body = saved_body(client)
    first = client.post(PATH, headers=AUTH, json=body).json()["draft"]
    monkeypatch.setattr(policy_store, "MAX_DRAFTS", 1)
    assert client.post(PATH, headers=AUTH, json=body).status_code == 200
    another = saved_body(client, draft("Second scenario"))
    blocked = client.post(PATH, headers=AUTH, json=another)
    assert blocked.status_code == 429 and blocked.json()["error"]["code"] == "DRAFT_STORAGE_FULL"
    assert client.get(PATH, headers=AUTH).json()["drafts"] == [first]
    assert account_state(desk) == before
