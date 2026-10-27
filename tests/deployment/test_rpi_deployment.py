"""Deployment contract tests: code-only packages and least-privilege monitor merge."""

import hashlib
import importlib.util
import json
import os
import sqlite3
import subprocess
import sys
import tarfile
import types
from contextlib import closing
from decimal import Decimal
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"deployment/rpi/{name}.py")
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def test_monitor_merge_preserves_existing_services_and_private_lines():
    register = module("register_monitor")
    previous = {"apache2": "apache2.service", "netrava": "phonewatch.service"}
    text = "AUTH_PASSWORD_HASH=private-hash\nHOST_POWER_ENABLED=true\nALLOWED_SERVICES_JSON={}\n"
    settings = {"ALLOWED_SERVICES_JSON": json.dumps(previous)}
    merged = register.merge(text, settings)
    assert merged.startswith("AUTH_PASSWORD_HASH=private-hash\nHOST_POWER_ENABLED=true\n")
    raw = merged.split("ALLOWED_SERVICES_JSON='", 1)[1].split("'", 1)[0]
    assert json.loads(raw) == {**previous, **register.SERVICES}
    assert register.merge(merged, {"ALLOWED_SERVICES_JSON": raw}) == merged


def test_monitor_conflicts_and_duplicate_declarations_fail_before_edit():
    register = module("register_monitor")
    with pytest.raises(ValueError, match="Conflicting"):
        register.merge("", {"ALLOWED_SERVICES_JSON": '{"agentic-trader":"other.service"}'})
    with pytest.raises(ValueError, match="Duplicate"):
        register.merge("ALLOWED_SERVICES_JSON={}\nALLOWED_SERVICES_JSON={}\n", {})
    with pytest.raises(ValueError, match="object"):
        register.merge("", {"ALLOWED_SERVICES_JSON": "[]"})


def test_private_replacement_preserves_access_and_is_readable_after_reopen(tmp_path):
    register = module("register_monitor")
    path = tmp_path / ".env"
    path.write_text("old")
    path.chmod(0o640)
    before = path.stat()
    register.private_replace(path, "new\n")
    after = path.stat()
    assert path.read_text() == "new\n"
    assert (after.st_mode, after.st_uid, after.st_gid) == (
        before.st_mode,
        before.st_uid,
        before.st_gid,
    )
    assert list(tmp_path.iterdir()) == [path]


def tracked_project(path, files):
    path.mkdir()
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    for name, content in files.items():
        target = path / name
        target.parent.mkdir(exist_ok=True, parents=True)
        target.write_text(content)
    subprocess.run(["git", "-C", str(path), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(path),
            "-c",
            "user.name=Deployment Test",
            "-c",
            "user.email=deployment@example.invalid",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-qm",
            "fixture",
        ],
        check=True,
    )


def test_bundle_contains_reviewable_hashes_but_no_private_state(tmp_path):
    trader, advisor = tmp_path / "trader", tmp_path / "advisor"
    tracked_project(
        trader,
        {
            "uv.lock": "locked",
            "src/trading_agent/main.py": "code",
            "config/paper.toml": 'mode="paper"',
            "config/private-session.toml": "private",
            "config/.env": "tracked-secret",
            "data/account.sqlite3": "private",
        },
    )
    tracked_project(
        advisor,
        {
            "app.py": "code",
            "advisor/config.py": "code",
            "data/demo_holdings.csv": "demo",
            "advisor/.env": "tracked-secret",
            "data/account.sqlite3": "private",
        },
    )
    (advisor / "data/unknown.csv").write_text("untracked private portfolio")
    new_module = trader / "src/trading_agent/public_support.py"
    new_module.write_text("reviewed new runtime code")
    output = tmp_path / "bundle.tar.gz"
    module("bundle").build(trader, advisor, output)
    with tarfile.open(output) as archive:
        names = archive.getnames()
        assert "trader/config/paper.toml" in names
        assert "trader/src/trading_agent/public_support.py" in names
        assert "advisor/data/demo_holdings.csv" in names
        assert not any(
            ".env" in name
            or ".sqlite" in name
            or "private-session" in name
            or "unknown.csv" in name
            for name in names
        )
        manifest = json.load(archive.extractfile("manifest.json"))
        for name, expected in manifest["sha256"].items():
            assert hashlib.sha256(archive.extractfile(name).read()).hexdigest() == expected
    # Working-tree changes to tracked source are packaged and identified by their hash.
    (advisor / "app.py").write_text("updated code")
    assert Path("app.py") in module("bundle").sources(advisor, "advisor")


def test_bundle_rejects_symlink_to_private_file(tmp_path):
    project = tmp_path / "project"
    tracked_project(project, {"uv.lock": "lock", "src/link.py": "old"})
    target = project / "src/link.py"
    target.unlink()
    target.symlink_to("/etc/passwd")
    with pytest.raises(ValueError, match="regular project file"):
        module("bundle").sources(project, "trader")


def test_systemd_units_keep_accounts_private_and_preserve_manual_authority():
    trader = (ROOT / "deployment/rpi/agentic-trader.service").read_text()
    advisor = (ROOT / "deployment/rpi/portfolio-advisor.service").read_text()
    assert "User=trading-agent" in trader
    assert " serve\n" in trader and "--stream" not in trader and "--automate" not in trader
    assert "EnvironmentFile=/etc/agentic-trader.env" in trader
    assert "ADVISOR_ENV_FILE=/var/lib/portfolio-advisor/config/.env" in advisor
    assert "--server.address=127.0.0.1" in advisor
    assert "--server.enableXsrfProtection=true" in advisor
    for app, unit in [("agentic-trader", trader), ("portfolio-advisor", advisor)]:
        assert f"ReadWritePaths=/var/lib/{app}\n" in unit
        assert "ProtectSystem=strict" in unit and "ProtectHome=true" in unit
    for script in ["install.sh", "deploy.sh"]:
        subprocess.run(["bash", "-n", str(ROOT / "deployment/rpi" / script)], check=True)


def test_deploy_rejects_missing_target():
    result = subprocess.run(
        ["bash", str(ROOT / "deployment/rpi/deploy.sh")],
        capture_output=True,
        text=True,
        env=os.environ,
    )
    assert result.returncode == 2
    assert "Usage:" in result.stderr


def test_service_config_survives_separate_account_processes(tmp_path):
    import tomlkit

    settings = tomlkit.parse((ROOT / "config/paper.toml").read_text())
    database = tmp_path / "data/paper.sqlite3"
    database.parent.mkdir()
    calendar = tmp_path / "sessions.csv"
    calendar.write_text("date,open,close,source\n")
    settings.update(database=str(database), calendar=str(calendar), port=8010)
    config = tmp_path / "paper.toml"
    config.write_text(tomlkit.dumps(settings))
    env = {**os.environ, "TRADING_CONFIG": str(config), "TRADING_MODE": "paper"}
    for command in ["init-db", "status", "verify-db"]:
        subprocess.run(
            [sys.executable, "-m", "trading_agent.main", command],
            check=True,
            capture_output=True,
            env=env,
        )
    with closing(sqlite3.connect(f"file:{database}?mode=ro", uri=True)) as db:
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        meta = dict(db.execute("SELECT key,value FROM meta"))
        assert Decimal(meta["cash"]) == Decimal(meta["initial_cash"]) == Decimal("25000.00")
        assert all(
            db.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == 0
            for table in ["orders", "fills", "positions"]
        )


def test_monitor_registration_rolls_back_partial_write(tmp_path, monkeypatch):
    register = module("register_monitor")
    root = tmp_path / "monitor"
    (root / "deploy").mkdir(parents=True)
    env_path, rule_path = root / ".env", tmp_path / "rule"
    env_path.write_text("AUTH_PASSWORD_HASH=untouched\nALLOWED_SERVICES_JSON={}\n")
    rule_path.write_text("old-rule")
    (root / "deploy/10-rpi-monitor-systemctl.rules").write_text("template")
    (root / "deploy/render_polkit_rule.py").write_text(
        'def render(template, env):\n    return "new-rule"\n'
    )
    # Parsing is exercised with real python-dotenv on the Pi; isolate write recovery here.
    dotenv = types.ModuleType("dotenv")
    dotenv.dotenv_values = lambda *args, **kwargs: {}
    monkeypatch.setitem(sys.modules, "dotenv", dotenv)
    original = register.private_replace
    calls = []

    def fail_second(path, content):
        calls.append(path)
        if len(calls) == 2:
            raise OSError("injected environment write failure")
        original(path, content)

    monkeypatch.setattr(register, "private_replace", fail_second)
    with pytest.raises(OSError, match="injected"):
        register.register(root, rule_path)
    assert rule_path.read_text() == "old-rule"
    assert env_path.read_text() == "AUTH_PASSWORD_HASH=untouched\nALLOWED_SERVICES_JSON={}\n"
