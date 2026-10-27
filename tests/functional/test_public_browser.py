"""HTTPS subpath hosting retains operator authority and exact accounting."""

import re
import sqlite3
import subprocess
from contextlib import closing
from decimal import Decimal
from importlib.resources import files

import pytest
from conftest import NOW, TOKEN
from fastapi.testclient import TestClient

from trading_agent.api.app import create_app
from trading_agent.api.public_path import PublicAssets
from trading_agent.risk.policy import policy_fingerprint
from trading_agent.settings import Settings

PREFIX = "/agentic-trader"
ORIGIN = "https://shanmukhan.com"
AUTH = {"Authorization": "Bearer " + TOKEN, "Origin": ORIGIN}


def public_engine(engine):
    engine.settings = engine.settings.model_copy(
        update={"public_origin": ORIGIN, "public_path": PREFIX}
    )
    return engine


@pytest.mark.parametrize(
    "origin",
    [
        "http://shanmukhan.com",
        "https://shanmukhan.com/",
        "https://shanmukhan.com:443",
        "https://user:secret@shanmukhan.com",
        "https://*.shanmukhan.com",
        "https://host/path",
        "https://host?query=1",
        "https://host#fragment",
        "https://host\nname",
    ],
)
def test_public_origin_requires_exact_https_host(origin):
    with pytest.raises(ValueError):
        Settings(public_origin=origin)


@pytest.mark.parametrize("path", ["/", "//outside", "/../", "/a/b", "/a?query", '/a"bad'])
def test_public_path_rejects_ambiguous_prefixes(path):
    with pytest.raises(ValueError):
        Settings(public_origin=ORIGIN, public_path=path)


def test_deployment_settings_do_not_change_economic_identity():
    local = Settings()
    public = Settings(public_origin=ORIGIN, public_path=PREFIX)
    assert policy_fingerprint(public) == policy_fingerprint(local)
    with pytest.raises(ValueError, match="requires"):
        Settings(public_path=PREFIX)


def test_prefixed_workspace_assets_and_frame_security(engine):
    app = create_app(public_engine(engine), clock=lambda: NOW, background=False)
    with TestClient(app, base_url=ORIGIN) as client:
        page = client.get(PREFIX + "/workspace")
        assert page.status_code == 200
        assert "Operator token for this server" in page.text
        assert "/etc/agentic-trader.env" in page.text
        assert "explicit synchronization" in page.text
        assert f'src="{PREFIX}/workspace.js"' in page.text
        assert f'href="{PREFIX}/dashboard.css"' in page.text
        for asset in set(re.findall(r'(?:src|href)="(/agentic-trader/[^"#]+)', page.text)):
            assert client.get(asset).status_code == 200, asset
        for view in ["/dashboard", "/analysis", "/setup", "/paper", "/holdings", "/backtesting"]:
            result = client.get(PREFIX + view)
            assert result.status_code == 200
            assert result.headers["x-frame-options"] == "SAMEORIGIN"
            assert "frame-ancestors 'self'" in result.headers["content-security-policy"]
        workspace = client.get(PREFIX + "/workspace.js").text
        assert "'/agentic-trader/api/workspace'" in workspace
        assert "'/agentic-trader/console'" in workspace
        bridge = client.get(PREFIX + "/workspace-bridge.js").text
        assert "'/agentic-trader/analysis'" in bridge
        setup = client.get(PREFIX + "/setup.js").text
        assert "win.location.origin + '/agentic-trader/'" in setup
        assert "call('/credentials', body)" in setup
        assert "request('/agentic-trader/api/setup' + path" in setup
        assert client.get(PREFIX + "/health").json()["mode"] == "paper"
        assert client.get("/health").status_code == 200  # deployment health remains local
        assert client.get(PREFIX + "/api/status").status_code == 401
        assert client.get(PREFIX + "/api/status", headers=AUTH).status_code == 200


def test_public_mutations_require_token_and_exact_origin_and_preserve_cash(engine):
    app = create_app(public_engine(engine), clock=lambda: NOW, background=False)
    with TestClient(app, base_url=ORIGIN) as client:
        for headers, status in [
            ({}, 401),
            ({**AUTH, "Origin": "https://evil.example"}, 403),
            ({**AUTH, "Host": "evil.example"}, 400),
        ]:
            assert client.post(PREFIX + "/api/control/kill", headers=headers).status_code == status
        with closing(sqlite3.connect(engine.settings.database)) as db:
            before = dict(db.execute("SELECT key,value FROM meta"))
            assert Decimal(before["cash"]) == Decimal("25000.00")
        assert client.post(PREFIX + "/api/control/kill", headers=AUTH).json()["kill"]
        with closing(sqlite3.connect(engine.settings.database)) as db:
            after = dict(db.execute("SELECT key,value FROM meta"))
            assert Decimal(after["cash"]) == Decimal(before["cash"])
            assert db.execute("SELECT count(*) FROM orders").fetchone()[0] == 0
            assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_prefixed_bundled_scripts_remain_valid_javascript(tmp_path):
    root = files("trading_agent.api").joinpath("static")
    assets = PublicAssets(root, PREFIX)
    for source in root.iterdir():
        if source.name.endswith(".js"):
            path = tmp_path / source.name
            path.write_text(assets.joinpath(source.name).read_text())
            subprocess.run(["node", "--check", str(path)], check=True, capture_output=True)
    # The actual controller keeps URL dictionaries and iframe postMessage paths aligned.
    code = assets.joinpath("workspace.js").read_text()
    assert "split('/')." in code or "split('/'" in code
    assert "https://" not in code or "https://" in root.joinpath("workspace.js").read_text()


def test_local_assets_are_unchanged_and_environment_is_explicit(tmp_path, monkeypatch):
    root = files("trading_agent.api").joinpath("static")
    assert (
        PublicAssets(root, "").joinpath("workspace.js").read_text()
        == root.joinpath("workspace.js").read_text()
    )
    config = tmp_path / "config.toml"
    config.write_text('mode="paper"\n')
    monkeypatch.setenv("TRADING_PUBLIC_ORIGIN", ORIGIN)
    monkeypatch.setenv("TRADING_PUBLIC_PATH", PREFIX)
    settings = Settings.load(config)
    assert (settings.public_origin, settings.public_path) == (ORIGIN, PREFIX)
