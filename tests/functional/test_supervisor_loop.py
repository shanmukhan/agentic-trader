"""Full monitor loop against real ASGI routes and SQLite; no external broker/device."""

import json
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta
from decimal import Decimal

from conftest import TOKEN
from fastapi.testclient import TestClient
from preparation_support import TEST_NOW

from trading_agent.api.app import create_app
from trading_agent.operations import supervisor


def test_supervisor_loop_audits_real_ledger_and_persists_alert_recovery(
    preparation_factory, monkeypatch, tmp_path
):
    s = preparation_factory()
    engine = s.engine
    engine.set_connected(False)

    def persisted():
        with closing(sqlite3.connect(engine.settings.database)) as tx:
            return {
                name: tx.execute(f"SELECT * FROM {name} ORDER BY rowid").fetchall()
                for name in ("meta", "events", "orders", "fills", "positions", "desk_decisions")
            }

    before = persisted()
    app = create_app(engine, clock=lambda: s.clock[0], setup=s.setup, desk=s.desk, background=False)
    calls = []
    with TestClient(app, base_url="http://127.0.0.1") as client:

        def request(settings, method, path, body=None):
            # Replace only HTTP transport: collect(), identity checks, reporting,
            # independent SQLite audit, transitions and durable publication all run.
            calls.append((method, path))
            response = client.request(
                method, path, json=body, headers={"Authorization": "Bearer " + TOKEN}
            )
            response.raise_for_status()
            return response.json()

        monkeypatch.setattr(supervisor, "request", request)

        class ThreeIterations:
            waits = 0

            def wait(self, interval):
                assert interval == 5
                self.waits += 1
                if self.waits == 1:
                    engine.set_connected(True)
                s.clock[0] += timedelta(seconds=5)
                return self.waits == 3

        output = tmp_path / "monitor"
        state = supervisor.supervise(
            engine.settings, output, lambda: s.clock[0], interval=5, stop=ThreeIterations()
        )
    assert calls == [
        ("GET", "/api/operations?audit=false"),
        ("GET", "/api/operations?audit=true"),
        ("GET", "/api/operations?audit=false"),
        ("GET", "/api/operations?audit=false"),
    ]
    assert "FEED_DISCONNECTED" not in state["alerts"]
    events = [json.loads(path.read_text()) for path in sorted(output.glob("alert-*.json"))]
    assert len(events) == 2
    assert "FEED_DISCONNECTED" in events[0]["alerts"]
    assert "FEED_DISCONNECTED" in events[1]["cleared"]
    audit = json.loads((output / "audit.json").read_text())
    assert datetime.fromisoformat(audit["observed_at"]) == TEST_NOW
    assert audit["ledger_audit"]["cash"] == "25000"
    assert Decimal(audit["account"]["cash"]) == Decimal("25000")
    assert next(c for c in audit["checks"] if c["id"] == "ledger")["status"] == "PASS"
    report_dirs = list(output.glob("daily-*/manifest.json"))
    assert len(report_dirs) == 1
    assert json.loads(report_dirs[0].read_text())["state"] == "finished"
    assert json.loads((output / "state.json").read_text()) == state
    assert persisted() == before
    assert s.desk.mode == "manual" and not engine.faulted
