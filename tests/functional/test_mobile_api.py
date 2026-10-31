"""Synthetic native-phone access and callback tests; no device or broker acceptance."""

import json
import sqlite3
from contextlib import closing
from datetime import timedelta

from conftest import TOKEN
from fastapi.testclient import TestClient

from trading_agent.api.app import create_app

OWNER = {"Authorization": "Bearer " + TOKEN}


def pair(client, label="INVENTED Android phone"):
    response = client.post("/api/mobile/devices", headers=OWNER, json={"label": label})
    assert response.status_code == 200, response.text
    credential = response.json()
    response = client.post("/api/mobile/session", json=credential)
    assert response.status_code == 200, response.text
    return (
        credential,
        response.json(),
        {"Authorization": "Bearer " + response.json()["access_token"]},
    )


def persisted(engine):
    with closing(sqlite3.connect(engine.settings.database)) as db:
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        return list(db.iterdump())


def test_device_pair_unlock_scope_logout_and_revocation_preserve_entire_ledger(preparation_factory):
    s = preparation_factory()
    app = create_app(
        s.engine, setup=s.setup, desk=s.desk, clock=lambda: s.clock[0], background=False
    )
    with TestClient(app, base_url="http://127.0.0.1") as client:
        before = persisted(s.engine)
        assert client.post("/api/mobile/devices", json={"label": "phone"}).status_code == 401
        credential, session, phone = pair(client)
        assert client.get("/api/setup", headers=phone).status_code == 200
        assert client.get("/api/desk", headers=phone).status_code == 200
        assert (
            client.post("/api/mobile/devices", headers=phone, json={"label": "other"}).status_code
            == 403
        )
        other, _, _ = pair(client, "Second invented phone")
        assert (
            client.delete("/api/mobile/devices/" + other["device_id"], headers=phone).status_code
            == 403
        )
        listing = client.get("/api/mobile/devices", headers=phone).json()["devices"]
        assert len(listing) == 1 and listing[0]["id"] == credential["device_id"]
        assert "secret" not in json.dumps(listing)
        path = s.engine.settings.database.with_suffix(".mobile.json")
        content = path.read_text()
        assert credential["device_secret"] not in content and session["access_token"] not in content
        assert path.stat().st_mode & 0o777 == 0o600
        assert client.delete("/api/mobile/session", headers=phone).status_code == 200
        assert client.get("/api/setup", headers=phone).status_code == 401
        fresh = client.post("/api/mobile/session", json=credential).json()
        headers = {"Authorization": "Bearer " + fresh["access_token"]}
        assert (
            client.delete(
                "/api/mobile/devices/" + credential["device_id"], headers=headers
            ).status_code
            == 200
        )
        assert client.get("/api/setup", headers=headers).status_code == 401
        assert client.post("/api/mobile/session", json=credential).status_code == 401
        assert persisted(s.engine) == before


def test_session_expiration_restart_and_operator_rotation_revoke_access(preparation_factory):
    from pydantic import SecretStr

    s = preparation_factory()
    app = create_app(
        s.engine, setup=s.setup, desk=s.desk, clock=lambda: s.clock[0], background=False
    )
    with TestClient(app, base_url="http://127.0.0.1") as client:
        credential, _, phone = pair(client)
        s.clock[0] += timedelta(seconds=901)
        assert client.get("/api/setup", headers=phone).status_code == 401
        session = client.post("/api/mobile/session", json=credential).json()
        phone = {"Authorization": "Bearer " + session["access_token"]}
    restarted = create_app(
        s.engine, setup=s.setup, desk=s.desk, clock=lambda: s.clock[0], background=False
    )
    with TestClient(restarted, base_url="http://127.0.0.1") as other:
        assert other.get("/api/setup", headers=phone).status_code == 401
        assert other.post("/api/mobile/session", json=credential).status_code == 200
        s.engine.settings = s.engine.settings.model_copy(
            update={"operator_token": SecretStr("rotated-" + "z" * 40)}
        )
        assert other.post("/api/mobile/session", json=credential).status_code == 401


def test_mobile_secret_validation_origin_and_attempt_limits_never_echo_values(preparation_factory):
    s = preparation_factory()
    app = create_app(
        s.engine, setup=s.setup, desk=s.desk, clock=lambda: s.clock[0], background=False
    )
    with TestClient(app, base_url="http://127.0.0.1") as client:
        private = "PRIVATE-invalid-mobile-secret"
        invalid = client.post(
            "/api/mobile/session", json={"device_id": "a" * 32, "device_secret": private}
        )
        assert invalid.status_code == 422 and private not in invalid.text
        assert client.post("/api/mobile/session", content="x" * 4097).status_code == 413
        credential, _, _ = pair(client)
        assert (
            client.post(
                "/api/mobile/session", json=credential, headers={"Origin": "https://evil.test"}
            ).status_code
            == 403
        )
        bad = {**credential, "device_secret": "0" * 64}
        for _ in range(5):
            assert client.post("/api/mobile/session", json=bad).status_code == 401
        assert client.post("/api/mobile/session", json=credential).status_code == 429
        s.clock[0] += timedelta(minutes=1)
        assert client.post("/api/mobile/session", json=credential).status_code == 200


def test_mobile_broker_callback_is_nonce_bound_one_time_and_contains_no_tokens(
    preparation_factory, monkeypatch
):
    from urllib.parse import parse_qs, urlsplit

    s = preparation_factory()
    app = create_app(
        s.engine, setup=s.setup, desk=s.desk, clock=lambda: s.clock[0], background=False
    )
    calls = []
    original = s.setup.exchange

    def exchange(body):
        calls.append(dict(body))
        assert s.setup.nonce and body["state"] == s.setup.nonce[0]
        s.setup.nonce = None
        s.setup.verified, s.setup.verified_at = True, s.clock[0]

    monkeypatch.setattr(s.setup, "exchange", exchange)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        before = persisted(s.engine)
        _, _, phone = pair(client)
        login = client.post("/api/mobile/broker/login", headers=phone, json={}).json()
        query = parse_qs(urlsplit(login["login_url"]).query)
        params = parse_qs(query["redirect_params"][0])
        nonce = params["setup_state"][0]
        key = params["mobile_attempt"][0]
        assert key == login["attempt_id"]
        callback = {
            "mobile_attempt": key,
            "setup_state": "wrong",
            "request_token": "PRIVATE-onetime",
        }
        response = client.get("/", params=callback)
        assert "needs attention" in response.text and not calls
        callback["setup_state"] = nonce
        response = client.get("/", params=callback)
        assert "sign-in complete" in response.text and "PRIVATE-onetime" not in response.text
        assert response.headers["Cache-Control"] == "no-store"
        assert (
            client.get("/api/mobile/broker/login/" + key, headers=phone).json()["state"]
            == "verified"
        )
        client.get("/", params=callback)
        assert len(calls) == 1
        assert persisted(s.engine) == before
    monkeypatch.setattr(s.setup, "exchange", original)


def test_phone_purchase_preview_fill_and_replay_use_exact_persisted_accounting(long_term_factory):
    from decimal import Decimal as D

    from conftest import NOW, quote

    from trading_agent.execution.delivery import HoldingReview

    engine = long_term_factory()
    engine.review_holding(
        HoldingReview(
            symbol="NSE:DEMO",
            session_date=NOW.date(),
            no_corporate_action=True,
            reference="INVENTED mobile flow",
        ),
        NOW,
    )
    engine.ingest(quote(), NOW)
    now = [NOW]
    app = create_app(engine, clock=lambda: now[0], background=False)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        _, _, phone = pair(client)
        before = persisted(engine)
        request = {
            "intent_id": "mobile-contribution",
            "symbol": "NSE:DEMO",
            "budget": "2000.00",
            "stop": "490.00",
            "target": "600.00",
            "reference": "INVENTED mobile preview",
        }
        preview = client.post("/api/paper/portfolio/preview", headers=phone, json=request)
        assert preview.status_code == 200 and preview.json()["decision"]["quantity"] == 3
        assert persisted(engine) == before
        body = {"request": request, "preview_sha256": preview.json()["preview_sha256"]}
        result = client.post("/api/paper/portfolio/contributions", headers=phone, json=body)
        assert result.status_code == 200 and result.json()["state"] == "ACCEPTED"
        now[0] += timedelta(seconds=1)
        engine.ingest(quote(1), now[0])
        filled = persisted(engine)
        replay = client.post("/api/paper/portfolio/contributions", headers=phone, json=body)
        assert replay.status_code == 200 and replay.json()["filled"] == 3
        assert persisted(engine) == filled
    with closing(sqlite3.connect(engine.settings.database)) as db:
        db.row_factory = sqlite3.Row
        fills = list(db.execute("SELECT * FROM fills"))
        assert len(fills) == 1 and fills[0]["quantity"] == 3
        debit = sum((D(f["price"]) * f["quantity"] + D(f["fees"]) for f in fills), D(0))
        cash = D(db.execute("SELECT value FROM meta WHERE key='cash'").fetchone()[0])
        assert cash == D("25000.00") - debit
        assert db.execute("SELECT count(*) FROM orders").fetchone()[0] == 1
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_mobile_manual_broker_fallback_is_bound_to_original_phone(preparation_factory, monkeypatch):
    s = preparation_factory()
    app = create_app(s.engine, setup=s.setup, clock=lambda: s.clock[0], background=False)
    calls = []

    def exchange(value):
        calls.append(dict(value))
        assert value["state"] == s.setup.nonce[0]

    monkeypatch.setattr(s.setup, "exchange", exchange)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        _, _, first = pair(client)
        _, _, second = pair(client, "Other invented phone")
        login = client.post("/api/mobile/broker/login", headers=first, json={}).json()
        path = "/api/mobile/broker/login/" + login["attempt_id"] + "/exchange"
        token = {"request_token": "INVENTED-onetime"}
        assert client.post(path, headers=second, json=token).status_code == 404
        assert not calls
        assert client.post(path, headers=first, json=token).json()["state"] == "verified"
        assert client.post(path, headers=first, json=token).status_code == 200
        assert len(calls) == 1
        assert token["request_token"] not in client.get("/mobile-return.js").text


def test_missing_broker_credentials_show_prerequisite_without_faulting_account(preparation_factory):
    s = preparation_factory()
    s.setup.values["api_secret"] = ""
    app = create_app(s.engine, setup=s.setup, clock=lambda: s.clock[0], background=False)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        before = persisted(s.engine)
        _, _, phone = pair(client)
        result = client.post("/api/mobile/broker/login", headers=phone, json={})
        assert (
            result.status_code == 409 and "Save your Kite API key and secret first" in result.text
        )
        assert not s.engine.faulted and persisted(s.engine) == before


def test_pairing_storage_failure_does_not_fault_ledger_and_revocation_fails_closed(
    preparation_factory, monkeypatch
):
    import trading_agent.mobile.auth as auth

    s = preparation_factory()
    app = create_app(s.engine, clock=lambda: s.clock[0], background=False)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        before = persisted(s.engine)
        credential, _, phone = pair(client)

        def failed_write(*args):
            raise OSError("INVENTED private filesystem failure")

        monkeypatch.setattr(auth, "private_write", failed_write)
        result = client.post("/api/mobile/devices", headers=OWNER, json={"label": "new phone"})
        assert result.status_code == 503 and "private filesystem" not in result.text
        assert len(app.state.mobile_access.devices) == 1
        result = client.delete("/api/mobile/devices/" + credential["device_id"], headers=phone)
        assert result.status_code == 503 and "uncertain" in result.text
        assert client.get("/api/desk", headers=phone).status_code == 401
        assert client.post("/api/mobile/session", json=credential).status_code == 401
        assert not s.engine.faulted and persisted(s.engine) == before


def test_installer_routes_verify_bytes_and_prefix_without_publishing_private_state(
    preparation_factory, tmp_path
):
    import hashlib

    s = preparation_factory()
    s.engine.settings = s.engine.settings.model_copy(update={"public_path": "/agentic-trader"})
    apk = tmp_path / "agentic-trader.apk"
    # Packaging fixture only: this is not a signed APK acceptance test.
    apk.write_bytes(b"INVENTED APK fixture")
    metadata = {
        "package_name": "com.shanmukhan.agentictrader",
        "version": "1.0.0",
        "version_code": 1,
        "sha256": hashlib.sha256(apk.read_bytes()).hexdigest(),
        "certificate_sha256": "a" * 64,
        "build_type": "productionRelease",
    }
    (tmp_path / "android-release.json").write_text(json.dumps(metadata))
    app = create_app(
        s.engine, clock=lambda: s.clock[0], background=False, android_release_dir=tmp_path
    )
    with TestClient(app, base_url="http://127.0.0.1") as client:
        before = persisted(s.engine)
        prefix = "/agentic-trader"
        page = client.get(prefix + "/android")
        assert page.status_code == 200 and prefix + "/downloads/agentic-trader.apk" in page.text
        response = client.get(prefix + "/downloads/agentic-trader.apk")
        assert response.status_code == 200 and response.content == apk.read_bytes()
        assert response.headers["Cache-Control"] == "no-store"
        assert client.get(prefix + "/api/mobile/release").json()["sha256"] == metadata["sha256"]
        credential = client.post(
            prefix + "/api/mobile/devices", headers=OWNER, json={"label": "Prefix phone"}
        ).json()
        session = client.post(prefix + "/api/mobile/session", json=credential).json()
        phone = {"Authorization": "Bearer " + session["access_token"]}
        assert client.get(prefix + "/api/desk", headers=phone).status_code == 200
        apk.write_bytes(b"tampered")
        assert client.get(prefix + "/downloads/agentic-trader.apk").status_code == 503
        assert client.get(prefix + "/api/mobile/release").status_code == 503
        apk.unlink()
        assert "not available yet" in client.get(prefix + "/android").text
        assert client.get(prefix + "/api/mobile/release").status_code == 404
        assert persisted(s.engine) == before


def test_environment_is_authenticated_read_only_and_preserves_exact_account(preparation_factory):
    from decimal import Decimal

    import pytest
    from pydantic import ValidationError

    from trading_agent.settings import Settings

    s = preparation_factory()
    app = create_app(
        s.engine, setup=s.setup, desk=s.desk, clock=lambda: s.clock[0], background=False
    )
    with TestClient(app, base_url="http://127.0.0.1") as client:
        before = persisted(s.engine)
        assert client.get("/api/trading-environment").status_code == 401
        _, _, phone = pair(client)
        for headers in (OWNER, phone):
            response = client.get("/api/trading-environment", headers=headers)
            assert response.status_code == 200
            capability = response.json()
            assert capability["active"] == "paper"
            assert capability["switching_available"] is False
            options = {row["id"]: row for row in capability["environments"]}
            assert options["paper"]["available"] is True
            assert options["real"]["available"] is False
            assert options["real"]["reason_code"] == "LIVE_EXECUTION_NOT_IMPLEMENTED"
            for environment in ("real", "paper"):
                assert (
                    client.post(
                        "/api/trading-environment",
                        headers=headers,
                        json={"environment": environment},
                    ).status_code
                    == 405
                )
        desk = client.get("/api/desk", headers=phone).json()
        assert desk["account"]["mode"] == "paper"
        assert desk["mode"] == "manual"
        assert persisted(s.engine) == before
        with closing(sqlite3.connect(s.engine.settings.database)) as db:
            assert Decimal(
                db.execute("SELECT value FROM meta WHERE key='cash'").fetchone()[0]
            ) == Decimal("25000.00")
    with pytest.raises(ValidationError):
        Settings(mode="real")
