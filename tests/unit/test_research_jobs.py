"""Synthetic lifecycle evidence; mocked launchers do not establish OS isolation."""

import json
import stat
import threading
import time
from pathlib import Path

import pytest

from trading_agent.research_jobs import BacktestJobs, JobError, isolation, register_bundle
from trading_agent.research_jobs.registry import load_resource, private_json


@pytest.fixture
def registered(tmp_path, execution_inputs):
    daily, execution, _ = execution_inputs
    root = tmp_path / "research"
    public = register_bundle(
        root,
        daily,
        execution,
        Path("config/daily-strategy.toml"),
        Path("config/long-term.toml"),
        "INVENTED lifecycle inputs",
    )
    return root, public


def submit(manager, public, key="a" * 32):
    return manager.submit(public["resource_id"], public["resource_sha256"], key, True)


def wait_for(manager, job_id, state):
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        result = manager.job(job_id)
        if result["state"] == state:
            return result
        time.sleep(0.01)
    pytest.fail(f"job did not reach {state}: {manager.job(job_id)}")


@pytest.fixture
def held_manager(registered, monkeypatch):
    """Simulate an admitted worker without starting any subprocess."""
    root, public = registered
    entered, release = threading.Event(), threading.Event()
    monkeypatch.setattr(
        isolation,
        "capability",
        lambda _: {
            "available": True,
            "reason": "SIMULATED test capability; not OS acceptance",
        },
    )

    def hold(self, state):
        entered.set()
        assert release.wait(5), "test did not release simulated worker"
        raise RuntimeError("PRIVATE worker diagnostic must never be public")

    monkeypatch.setattr(BacktestJobs, "_run", hold)
    manager = BacktestJobs(root)
    yield manager, public, entered, release
    release.set()
    manager.close()


def test_registration_copies_validated_inputs_privately_and_excludes_operator_secrets(
    tmp_path,
    execution_inputs,
):
    daily, execution, _ = execution_inputs
    secret = "operator-credential-" + "p" * 40
    private_path = "/operator/private/live-account.sqlite3"
    policy = tmp_path / "private-policy.toml"
    policy.write_text(
        'investment_horizon = "long_term"\n'
        f'database = "{private_path}"\noperator_token = "{secret}"\n'
    )
    root = tmp_path / "research"
    public = register_bundle(
        root,
        daily,
        execution,
        Path("config/daily-strategy.toml"),
        policy,
        "  Synthetic  ",
    )
    stored = root / "resources" / public["resource_id"]
    assert public["label"] == "Synthetic"
    assert public["synthetic"] is True
    assert public["coverage"]["execution_sessions"] == 3
    assert public["provenance"]["out_of_sample"] == "not_declared"
    assert public["provenance"]["connected_parity"] == "not_established"
    assert public["runtime"]["charges"]["dp_sell"] == "15.34"
    assert public["runtime"]["charges"]["observed_on"] == "2026-10-20"
    assert len(public["runtime"]["code_sha256"]) == 64
    assert not (stored / "policy.toml").exists()
    assert not (stored / "strategy.toml").exists()
    for path in [root, stored, *stored.rglob("*")]:
        assert stat.S_IMODE(path.stat().st_mode) & 0o077 == 0
        if path.is_file():
            assert secret.encode() not in path.read_bytes()
            assert private_path.encode() not in path.read_bytes()
    assert "database" not in public["policy"] and "operator_token" not in public["policy"]
    original = (stored / "daily" / "daily.jsonl").read_bytes()
    (daily / "daily.jsonl").write_text("source changed after immutable registration")
    assert (stored / "daily" / "daily.jsonl").read_bytes() == original
    assert load_resource(root, public["resource_id"])["public"] == public


@pytest.mark.parametrize("target", ["daily/daily.jsonl", "execution/events.jsonl", "public"])
def test_registered_data_and_public_definitions_are_hash_bound(registered, target):
    root, public = registered
    resource = root / "resources" / public["resource_id"]
    if target == "public":
        path = resource / "resource.json"
        record = json.loads(path.read_text())
        record["public"]["policy"]["starting_cash"] = "999999"
        private_json(path, record)
    else:
        with (resource / target).open("a") as stream:
            stream.write("\n")
    with pytest.raises(ValueError):
        load_resource(root, public["resource_id"])


def test_registry_rejects_symlinked_inputs_and_private_directory_symlink(
    tmp_path,
    execution_inputs,
):
    daily, execution, _ = execution_inputs
    alias = tmp_path / "daily-alias"
    alias.symlink_to(daily, target_is_directory=True)
    with pytest.raises(ValueError):
        register_bundle(
            tmp_path / "research",
            alias,
            execution,
            Path("config/daily-strategy.toml"),
            Path("config/long-term.toml"),
            "Synthetic",
        )
    owner = tmp_path / "actual"
    owner.mkdir(mode=0o700)
    root_alias = tmp_path / "research-alias"
    root_alias.symlink_to(owner, target_is_directory=True)
    with pytest.raises(ValueError):
        BacktestJobs(root_alias)


def test_unverified_runtime_refuses_admission_and_never_launches(registered, monkeypatch):
    root, public = registered
    monkeypatch.setattr(
        isolation,
        "capability",
        lambda _: {
            "available": False,
            "reason": "Hard limits could not be verified",
        },
    )

    def forbidden(*args, **kwargs):
        pytest.fail("a disabled capability must not launch a subprocess")

    monkeypatch.setattr("trading_agent.research_jobs.jobs.subprocess.Popen", forbidden)
    manager = BacktestJobs(root)
    try:
        assert manager.resources()["capability"]["available"] is False
        with pytest.raises(JobError) as raised:
            submit(manager, public)
        assert (raised.value.code, raised.value.status) == ("JOB_ISOLATION_UNAVAILABLE", 503)
        assert manager.jobs() == []
        assert list((root / "jobs").iterdir()) == []
    finally:
        manager.close()


def test_single_running_single_queued_idempotency_and_durable_cancellation(held_manager):
    manager, public, entered, _ = held_manager
    first, created = submit(manager, public)
    assert created and entered.wait(3)
    assert manager.job(first["job_id"])["state"] == "running"
    duplicate, created = submit(manager, public)
    assert not created and duplicate["job_id"] == first["job_id"]
    with pytest.raises(JobError) as conflict:
        manager.submit(public["resource_id"], "0" * 64, "a" * 32, True)
    assert conflict.value.code == "IDEMPOTENCY_CONFLICT"
    second, created = submit(manager, public, "b" * 32)
    assert created and second["state"] == "queued"
    with pytest.raises(JobError) as full:
        submit(manager, public, "c" * 32)
    assert (full.value.code, full.value.status) == ("JOB_QUEUE_FULL", 429)
    for job in (second, first):
        cancelled = manager.cancel(job["job_id"])
        assert cancelled["state"] == "cancelled" and cancelled["report_id"] is None
        assert manager.cancel(job["job_id"]) == cancelled
        stored = json.loads((manager.root / "jobs" / job["job_id"] / "job.json").read_text())
        assert stored["state"] == "cancelled"
        with pytest.raises(JobError) as report:
            manager.report(job["job_id"])
        assert (report.value.code, report.value.status) == ("REPORT_NOT_AVAILABLE", 404)
    assert len(manager.jobs()) == 2


def test_worker_failure_is_terminal_sanitized_and_does_not_publish(held_manager):
    manager, public, entered, release = held_manager
    job, _ = submit(manager, public)
    assert entered.wait(3)
    release.set()
    failed = wait_for(manager, job["job_id"], "failed")
    assert failed["error"]["code"] == "JOB_FAILED"
    assert "PRIVATE" not in json.dumps(failed)
    assert failed["report_id"] is None
    assert not (manager.root / "jobs" / job["job_id"] / "published.json").exists()
    duplicate, created = submit(manager, public)
    assert not created and duplicate == failed


def test_changed_code_or_costs_require_new_registration_before_admission(held_manager, monkeypatch):
    manager, public, _, _ = held_manager
    changed = {**public["runtime"], "code_sha256": "0" * 64}
    monkeypatch.setattr("trading_agent.research_jobs.jobs.runtime_definition", lambda _: changed)
    with pytest.raises(JobError) as error:
        submit(manager, public)
    assert error.value.code == "RESEARCH_VERSION_CHANGED"
    assert manager.jobs() == []
    assert list((manager.root / "jobs").iterdir()) == []


def test_restart_interrupts_saved_work_without_resuming_and_preserves_idempotency(
    held_manager,
    monkeypatch,
):
    manager, public, entered, release = held_manager
    first, _ = submit(manager, public)
    assert entered.wait(3)
    second, _ = submit(manager, public, "b" * 32)
    release.set()
    manager.close()
    # Model an abrupt stop with durable queued/running records, rather than a clean shutdown.
    for job, state in ((first, "running"), (second, "queued")):
        path = manager.root / "jobs" / job["job_id"] / "job.json"
        saved = json.loads(path.read_text())
        saved.update(state=state, error=None, report_id=None)
        private_json(path, saved)

    def forbidden(*args, **kwargs):
        pytest.fail("restart must not resume a prior job")

    monkeypatch.setattr(BacktestJobs, "_run", forbidden)
    restarted = BacktestJobs(manager.root)
    try:
        assert len(restarted.jobs()) == 2
        for job in (first, second):
            restored = restarted.job(job["job_id"])
            assert restored["state"] == "interrupted"
            assert restored["error"]["code"] == "JOB_INTERRUPTED"
            assert restored["report_id"] is None
            assert (
                json.loads((manager.root / "jobs" / job["job_id"] / "job.json").read_text())[
                    "state"
                ]
                == "interrupted"
            )
        restored, created = submit(restarted, public)
        assert not created and restored["job_id"] == first["job_id"]
    finally:
        restarted.close()


def test_one_directory_has_one_owner_and_corrupt_saved_state_fails_closed(registered, monkeypatch):
    root, _ = registered
    monkeypatch.setattr(isolation, "capability", lambda _: {"available": False, "reason": "test"})
    manager = BacktestJobs(root)
    try:
        with pytest.raises(RuntimeError, match="already owned"):
            BacktestJobs(root)
    finally:
        manager.close()
    directory = root / "jobs" / ("f" * 32)
    directory.mkdir(mode=0o700)
    private_json(directory / "job.json", {"state": "succeeded", "report_id": "forged"})
    with pytest.raises(RuntimeError, match="unreadable"):
        BacktestJobs(root)


def test_cancellation_during_verification_wins_over_publication(registered, monkeypatch):
    root, public = registered
    verifying, release = threading.Event(), threading.Event()
    monkeypatch.setattr(
        isolation,
        "capability",
        lambda _: {
            "available": True,
            "reason": "SIMULATED; not OS acceptance",
        },
    )

    class CompletedWorker:
        """Only tests serialization; no worker or financial verifier is exercised here."""

        returncode = 0

        def __init__(self, *args, **kwargs):
            pass

        def poll(self):
            return 0

        def wait(self, timeout):
            return 0

    def paused_verifier(output, record, job_id):
        verifying.set()
        assert release.wait(5)
        return {"report_id": job_id, "synthetic": True}

    monkeypatch.setattr("trading_agent.research_jobs.jobs.subprocess.Popen", CompletedWorker)
    monkeypatch.setattr("trading_agent.research_jobs.jobs.verify_report", paused_verifier)
    manager = BacktestJobs(root)
    try:
        job, _ = submit(manager, public)
        assert verifying.wait(3)
        assert manager.job(job["job_id"])["stage"] == "verifying"
        manager.cancel(job["job_id"])
        release.set()
        wait_for(manager, job["job_id"], "cancelled")
        # Synchronize with the worker finalizer before checking absence of publication.
        deadline = time.monotonic() + 3
        while getattr(manager, "_active_id", None) is not None and time.monotonic() < deadline:
            time.sleep(0.01)
        assert not (root / "jobs" / job["job_id"] / "published.json").exists()
        assert manager.job(job["job_id"])["report_id"] is None
    finally:
        release.set()
        manager.close()


def test_worker_environment_is_an_explicit_secret_free_allowlist(tmp_path, monkeypatch):
    monkeypatch.setenv("TRADING_OPERATOR_TOKEN", "should never reach child")
    monkeypatch.setenv("HTTP_PROXY", "http://operator-proxy.invalid")
    monkeypatch.setenv("PYTHONPATH", "/operator/injected-code")
    environment = isolation.environment(tmp_path)
    assert set(environment) == {
        "PATH",
        "HOME",
        "TMPDIR",
        "LANG",
        "OPENBLAS_NUM_THREADS",
        "OMP_NUM_THREADS",
    }
    assert environment["HOME"] == str(tmp_path)
    assert environment["TMPDIR"] == str(tmp_path / "tmp")
    assert "should never reach child" not in json.dumps(environment)


def test_verified_publication_is_durable_and_each_report_read_reverifies(registered, monkeypatch):
    """Test publication protocol with a stub verifier, not the financial verifier's correctness."""
    root, public = registered
    verified = []
    monkeypatch.setattr(
        isolation,
        "capability",
        lambda _: {
            "available": True,
            "reason": "SIMULATED test capability; not OS acceptance",
        },
    )

    class CompletedWorker:
        returncode = 0

        def __init__(self, *args, **kwargs):
            pass

        def poll(self):
            return 0

        def wait(self, timeout):
            return 0

    def simulated_verifier(output, record, job_id):
        verified.append(job_id)
        return {
            "report_id": job_id,
            "resource_sha256": public["resource_sha256"],
            "synthetic": True,
        }

    monkeypatch.setattr("trading_agent.research_jobs.jobs.subprocess.Popen", CompletedWorker)
    monkeypatch.setattr("trading_agent.research_jobs.jobs.verify_report", simulated_verifier)
    manager = BacktestJobs(root)
    try:
        job, _ = submit(manager, public)
        succeeded = wait_for(manager, job["job_id"], "succeeded")
        assert succeeded["progress"] == 100
        assert succeeded["report_id"] == job["job_id"] and succeeded["error"] is None
        stored_job = json.loads((root / "jobs" / job["job_id"] / "job.json").read_text())
        assert stored_job == succeeded
        published = root / "jobs" / job["job_id"] / "published.json"
        assert manager.report(job["job_id"]) == json.loads(published.read_text())
        assert verified == [job["job_id"], job["job_id"]]
        changed = json.loads(published.read_text())
        changed["synthetic"] = False
        private_json(published, changed)
        with pytest.raises(JobError) as rejected:
            manager.report(job["job_id"])
        assert (rejected.value.code, rejected.value.status) == ("REPORT_INTEGRITY_FAILED", 503)
        assert len(verified) == 3
        assert manager.job(job["job_id"])["state"] == "succeeded"
    finally:
        manager.close()


def test_unsupported_platform_capability_never_probes_or_launches(tmp_path, monkeypatch):
    monkeypatch.setattr(isolation.platform, "system", lambda: "Unsupported test OS")

    def forbidden(*args, **kwargs):
        pytest.fail("unsupported platform must not launch a capability probe")

    monkeypatch.setattr(isolation.subprocess, "run", forbidden)
    result = isolation.capability(tmp_path)
    assert result["available"] is False
    assert "verified OS" in result["reason"]
