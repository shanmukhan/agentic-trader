"""Authenticated synthetic lifecycle checks; simulated launch is not OS/broker acceptance."""

import json
import sqlite3
import threading
from contextlib import closing
from pathlib import Path

import pytest
from conftest import NOW, TOKEN
from fastapi.testclient import TestClient

from trading_agent.api.app import create_app
from trading_agent.research_jobs import BacktestJobs, isolation, register_bundle

AUTH = {"Authorization": "Bearer " + TOKEN}


@pytest.fixture
def research_api(tmp_path, execution_inputs, desk_factory, monkeypatch):
    daily, execution, _ = execution_inputs
    root = tmp_path / "isolated-research"
    public = register_bundle(
        root,
        daily,
        execution,
        Path("config/daily-strategy.toml"),
        Path("config/long-term.toml"),
        "INVENTED API lifecycle",
    )
    entered, release = threading.Event(), threading.Event()
    monkeypatch.setattr(
        isolation,
        "capability",
        lambda _: {
            "available": True,
            "reason": "SIMULATED test capability, not platform acceptance",
        },
    )

    def hold(self, state):
        entered.set()
        assert release.wait(5), "test did not release simulated research worker"
        raise RuntimeError("PRIVATE diagnostic: " + TOKEN)

    monkeypatch.setattr(BacktestJobs, "_run", hold)
    manager = BacktestJobs(root)
    desk, _, _ = desk_factory()
    desk.set_mode("approval", NOW, desk.revision)
    app = create_app(desk.engine, desk=desk, backtests=manager, clock=lambda: NOW, background=False)
    try:
        with TestClient(app, base_url="http://127.0.0.1") as client:
            yield client, manager, public, desk, entered
            release.set()
    finally:
        release.set()
        manager.close()


def body(public, key="a" * 32):
    return {
        "resource_id": public["resource_id"],
        "resource_sha256": public["resource_sha256"],
        "request_key": key,
        "acknowledged": True,
    }


def account_state(desk):
    """Compare complete persisted state independently of the application snapshot."""
    with closing(sqlite3.connect(desk.engine.settings.database)) as connection:
        persisted = list(connection.iterdump())
    return persisted, (
        desk.mode,
        desk.revision,
        desk.reason,
        desk.engine.connected,
        desk.engine.faulted,
    )


def test_resources_and_job_reads_require_auth_and_never_change_account_or_start_work(research_api):
    client, manager, public, desk, _ = research_api
    before = account_state(desk)
    for path in ("/api/backtests/resources", "/api/backtests/jobs"):
        assert client.get(path).status_code == 401
        response = client.get(path, headers=AUTH)
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["x-frame-options"] == "DENY"
        assert TOKEN not in response.text
        assert str(manager.root) not in response.text
    resources = client.get("/api/backtests/resources", headers=AUTH).json()
    assert resources["resources"] == [public]
    assert resources["limits"]["worker_slots"] == resources["limits"]["queue_slots"] == 1
    assert client.get("/api/backtests/jobs", headers=AUTH).json()["jobs"] == []
    for kind in ("jobs", "reports"):
        assert client.get(f"/api/backtests/{kind}/{'f' * 32}", headers=AUTH).status_code == 404
    assert account_state(desk) == before


def test_post_requires_auth_same_origin_and_strict_bounded_acknowledged_schema(research_api):
    client, manager, public, desk, _ = research_api
    before = account_state(desk)
    path = "/api/backtests/jobs"
    assert client.post(path, json=body(public)).status_code == 401
    assert (
        client.post(
            path, headers={**AUTH, "Origin": "https://foreign.invalid"}, json=body(public)
        ).status_code
        == 403
    )
    invalid = [
        {**body(public), "acknowledged": False},
        {**body(public), "acknowledged": 1},
        {**body(public), "acknowledged": "true"},
        {**body(public), "source_path": "/operator/account.sqlite3"},
        {**body(public), "resource_id": "../../operator"},
        {**body(public), "request_key": "short"},
        {**body(public), "resource_sha256": "g" * 64},
    ]
    for value in invalid:
        assert client.post(path, headers=AUTH, json=value).status_code == 422
    duplicate = json.dumps(body(public))[:-1] + ',"acknowledged":false}'
    assert client.post(path, headers=AUTH, content=duplicate).status_code == 422
    assert client.post(path, headers=AUTH, content="x" * 4097).status_code == 413
    assert client.post(path, headers=AUTH, content=b"\xff").status_code == 422
    assert manager.jobs() == []
    assert account_state(desk) == before


def test_http_idempotency_queue_cancellation_and_report_absence_preserve_account(research_api):
    client, manager, public, desk, entered = research_api
    before = account_state(desk)
    path = "/api/backtests/jobs"
    first = client.post(path, headers=AUTH, json=body(public))
    assert first.status_code == 202 and entered.wait(3)
    first_id = first.json()["job"]["job_id"]
    duplicate = client.post(path, headers=AUTH, json=body(public))
    assert duplicate.status_code == 200 and duplicate.json()["job"]["job_id"] == first_id
    conflict = client.post(path, headers=AUTH, json={**body(public), "resource_sha256": "0" * 64})
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"
    second = client.post(path, headers=AUTH, json=body(public, "b" * 32))
    assert second.status_code == 202 and second.json()["job"]["state"] == "queued"
    full = client.post(path, headers=AUTH, json=body(public, "c" * 32))
    assert full.status_code == 429 and full.headers["retry-after"] == "5"
    assert full.json()["error"]["code"] == "JOB_QUEUE_FULL"
    for job_id in (second.json()["job"]["job_id"], first_id):
        cancel_path = path + "/" + job_id + "/cancel"
        assert client.post(cancel_path, json={"acknowledged": True}).status_code == 401
        assert (
            client.post(cancel_path, headers=AUTH, json={"acknowledged": False}).status_code == 422
        )
        cancelled = client.post(cancel_path, headers=AUTH, json={"acknowledged": True})
        assert cancelled.status_code == 200 and cancelled.json()["job"]["state"] == "cancelled"
        assert client.get(path + "/" + job_id, headers=AUTH).json()["job"]["report_id"] is None
        assert client.get("/api/backtests/reports/" + job_id, headers=AUTH).status_code == 404
    assert len(manager.jobs()) == 2
    assert account_state(desk) == before


def test_integrity_and_storage_failures_are_sanitized_without_faulting_operator(
    research_api, monkeypatch
):
    client, manager, public, desk, _ = research_api
    before = account_state(desk)
    resource = manager.root / "resources" / public["resource_id"] / "daily" / "daily.jsonl"
    with resource.open("a") as stream:
        stream.write("\n")
    response = client.post("/api/backtests/jobs", headers=AUTH, json=body(public))
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INPUT_INTEGRITY_FAILED"
    assert manager.jobs() == []

    def broken_read():
        raise OSError("PRIVATE /operator/account: " + TOKEN)

    monkeypatch.setattr(manager, "jobs", broken_read)
    response = client.get("/api/backtests/jobs", headers=AUTH)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "RESEARCH_STORAGE_UNAVAILABLE"
    assert TOKEN not in response.text and "PRIVATE" not in response.text
    assert account_state(desk) == before


def test_missing_resource_and_disabled_runtime_do_not_admit_jobs_or_mutate_account(research_api):
    client, manager, public, desk, _ = research_api
    before = account_state(desk)
    absent = {**body(public), "resource_id": "bundle-" + "f" * 24}
    missing = client.post("/api/backtests/jobs", headers=AUTH, json=absent)
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "RESOURCE_NOT_FOUND"
    manager.capability = {"available": False, "reason": "Unverified hard resource limit"}
    resources = client.get("/api/backtests/resources", headers=AUTH)
    assert resources.status_code == 200
    assert resources.json()["capability"]["available"] is False
    disabled = client.post("/api/backtests/jobs", headers=AUTH, json=body(public))
    assert disabled.status_code == 503
    assert disabled.json()["error"]["code"] == "JOB_ISOLATION_UNAVAILABLE"
    assert manager.jobs() == []
    assert account_state(desk) == before
