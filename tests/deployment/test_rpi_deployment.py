"""Deployment contract tests: code-only packages and least-privilege monitor merge."""

import hashlib
import importlib.util
import json
import os
import sqlite3
import subprocess
import sys
import tarfile
import tomllib
import types
from contextlib import closing
from decimal import Decimal
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_backend_release_version_matches_project_and_lock():
    from trading_agent import __version__

    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    lock = tomllib.loads((ROOT / "uv.lock").read_text())
    locked = next(p for p in lock["package"] if p["name"] == "agentic-trader")
    assert project["project"]["version"] == locked["version"] == __version__


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
            "pyproject.toml": '[project]\nversion="0.19.1"\n',
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
            "pyproject.toml": '[project]\nversion="1.0.0"\n',
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
        assert manifest["versions"] == {"trader": "0.19.1", "advisor": "1.0.0"}
        for name, expected in manifest["sha256"].items():
            assert hashlib.sha256(archive.extractfile(name).read()).hexdigest() == expected
    # Working-tree changes to tracked source are packaged and identified by their hash.
    (advisor / "app.py").write_text("updated code")
    assert Path("app.py") in module("bundle").sources(advisor, "advisor")


def test_trader_only_versioned_bundle_excludes_advisor_and_rejects_unsafe_version(tmp_path):
    trader = tmp_path / "trader"
    tracked_project(
        trader,
        {
            "pyproject.toml": '[project]\nversion="0.19.1"\n',
            "uv.lock": "locked",
            "src/trading_agent/__init__.py": '__version__="0.19.1"\n',
        },
    )
    output = tmp_path / "trader.tar.gz"
    module("bundle").build(trader, None, output)
    with tarfile.open(output) as archive:
        manifest = json.load(archive.extractfile("manifest.json"))
        assert set(manifest["projects"]) == {"trader"}
        assert manifest["versions"] == {"trader": "0.19.1"}
        assert not any(name.startswith("advisor/") for name in archive.getnames())
        for name, expected in manifest["sha256"].items():
            assert hashlib.sha256(archive.extractfile(name).read()).hexdigest() == expected
    (trader / "pyproject.toml").write_text('[project]\nversion="../../unsafe"\n')
    with pytest.raises(ValueError, match="release version"):
        module("bundle").build(trader, None, output)


def test_android_bundle_includes_only_verified_public_installer_and_metadata(tmp_path):
    from fastapi import HTTPException

    project, release = tmp_path / "project", tmp_path / "release"
    tracked_project(
        project,
        {
            "pyproject.toml": '[project]\nversion="0.20.0"\n',
            "uv.lock": "locked",
            "src/trading_agent/main.py": "code",
        },
    )
    release.mkdir()
    apk = release / "agentic-trader.apk"
    apk.write_bytes(b"INVENTED packaging fixture; not a signed APK")
    value = {
        "version": "1.0.0",
        "version_code": 1,
        "package_name": "com.shanmukhan.agentictrader",
        "build_type": "productionRelease",
        "sha256": hashlib.sha256(apk.read_bytes()).hexdigest(),
        "certificate_sha256": "a" * 64,
    }
    metadata = release / "android-release.json"
    metadata.write_text(json.dumps(value))
    (release / "private-signing-key.p12").write_text("INVENTED private fixture")
    (release / "identity.json").write_text("INVENTED private fixture")
    output = tmp_path / "signed-bundle.tar.gz"
    module("bundle").build(project, None, output, apk)
    with tarfile.open(output) as archive:
        names = archive.getnames()
        assert {n for n in names if n.startswith("trader/downloads/")} == {
            "trader/downloads/agentic-trader.apk",
            "trader/downloads/android-release.json",
        }
        assert not any("signing" in n or "identity.json" in n for n in names)
        manifest = json.load(archive.extractfile("manifest.json"))
        assert manifest["android"]["sha256"] == value["sha256"]
        for name, expected in manifest["sha256"].items():
            assert hashlib.sha256(archive.extractfile(name).read()).hexdigest() == expected
    apk.write_bytes(b"tampered")
    with pytest.raises(HTTPException) as error:
        module("bundle").build(project, None, output, apk)
    assert error.value.status_code == 503
    metadata.unlink()
    metadata.symlink_to(release / "identity.json")
    with pytest.raises(HTTPException):
        module("bundle").build(project, None, output, apk)


def test_trader_only_deploy_cli_sends_only_versioned_trader_bundle(tmp_path):
    project = tmp_path / "project"
    tracked_project(
        project,
        {
            "pyproject.toml": '[project]\nversion="0.19.1"\n',
            "uv.lock": "locked",
            "src/trading_agent/__init__.py": '__version__="0.19.1"\n',
        },
    )
    deployment = project / "deployment/rpi"
    deployment.mkdir(parents=True)
    for name in ("bundle.py", "deploy.sh", "install.sh"):
        (deployment / name).write_bytes((ROOT / "deployment/rpi" / name).read_bytes())
    commands = tmp_path / "commands"
    commands.mkdir()
    log, captured = tmp_path / "commands.jsonl", tmp_path / "sent.tar.gz"
    for name in ("ssh", "scp"):
        path = commands / name
        path.write_text(
            f"#!{sys.executable}\n"
            "import json,os,pathlib,shutil,sys\n"
            "with open(os.environ['DEPLOY_TEST_LOG'],'a') as out:\n"
            " out.write(json.dumps([pathlib.Path(sys.argv[0]).name,*sys.argv[1:]])+'\\n')\n"
            "if pathlib.Path(sys.argv[0]).name=='scp':\n"
            " shutil.copyfile(sys.argv[-2],os.environ['DEPLOY_TEST_CAPTURE'])\n"
            "elif 'mktemp -d' in sys.argv[-1]:\n"
            " print('/tmp/trading-services.TEST123')\n"
        )
        path.chmod(0o700)
    subprocess.run(
        ["bash", str(deployment / "deploy.sh"), "test@invented.invalid", "--trader-only"],
        check=True,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "PATH": str(commands) + os.pathsep + os.environ["PATH"],
            "DEPLOY_PYTHON": sys.executable,
            "DEPLOY_TEST_LOG": str(log),
            "DEPLOY_TEST_CAPTURE": str(captured),
        },
    )
    with tarfile.open(captured) as archive:
        manifest = json.load(archive.extractfile("manifest.json"))
        assert manifest["versions"] == {"trader": "0.19.1"}
        assert set(manifest["projects"]) == {"trader"}
    calls = [json.loads(line) for line in log.read_text().splitlines()]
    assert sum(call[0] == "scp" for call in calls) == 1
    assert any("sudo -n bash" in call[-1] for call in calls)
    assert calls[-1][-1] == "rm -rf '/tmp/trading-services.TEST123'"


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
