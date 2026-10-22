"""Private immutable draft evidence; no active policy or execution is exercised."""

import concurrent.futures
import fcntl
import hashlib
import json
import os

import pytest

from trading_agent.investment_research import policy_store
from trading_agent.investment_research.policy_store import (
    InvestmentPolicyStore,
    PolicyStoreError,
    preview_draft,
    strict_json,
)


def payload(label="Research draft", *, cadence="monthly"):
    return {
        "label": label,
        "parameters": {
            "horizon_unit": "years",
            "horizon_count": 3,
            "review_cadence": cadence,
        },
    }


def save(store, value=None):
    value = payload() if value is None else value
    preview = store.preview(value)
    return store.save(value, preview["preview_sha256"], True)


def test_preview_and_reads_are_pure_lazy_and_show_unset_parameters(tmp_path):
    root = tmp_path / "private-drafts"
    store = InvestmentPolicyStore(root)
    inspected = store.preview(payload())
    assert inspected["draft"]["state"] == "incomplete"
    assert inspected["draft"]["policy_version_id"] is None
    assert inspected["draft"]["activation_supported"] is False
    assert inspected["draft"]["backtest_supported"] is False
    assert inspected["draft"]["parameters"]["stop_pct"] is None
    assert "stop_pct" in inspected["draft"]["missing_fields"]
    assert len(inspected["preview_sha256"]) == 64
    result = store.list()
    assert result["drafts"] == []
    assert result["activation_supported"] is result["backtest_supported"] is False
    result["field_definitions"][0]["label"] = "mutated caller copy"
    assert store.list()["field_definitions"][0]["label"] != "mutated caller copy"
    with pytest.raises(PolicyStoreError, match="not found"):
        store.get("draft-" + "f" * 64)
    assert not root.exists()


def test_save_private_immutable_content_identity_survives_restart_and_label_is_reviewed(tmp_path):
    root = tmp_path / "private-drafts"
    first, created = save(InvestmentPolicyStore(root))
    assert created is True
    assert len(first["draft_id"]) == 70
    records = list(root.glob("draft-*.json"))
    assert len(records) == 1
    assert root.stat().st_mode & 0o777 == 0o700
    assert records[0].stat().st_mode & 0o777 == 0o600
    original, before = records[0].read_bytes(), records[0].stat().st_mtime_ns
    reopened = InvestmentPolicyStore(root)
    duplicate, created = save(reopened)
    assert created is False and duplicate == first
    assert records[0].read_bytes() == original and records[0].stat().st_mtime_ns == before
    assert reopened.get(first["draft_id"]) == first
    assert reopened.list()["drafts"] == [first]
    another, created = save(reopened, payload("Distinct label"))
    assert created is True and another["draft_id"] != first["draft_id"]
    assert another["draft_sha256"] == first["draft_sha256"]
    independent = json.dumps(
        {key: value for key, value in first.items() if key != "draft_id"},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode()
    assert first["draft_id"] == "draft-" + hashlib.sha256(independent).hexdigest()


@pytest.mark.parametrize("acknowledgement", [False, 1, "true", None])
def test_save_requires_explicit_true_before_creating_storage(tmp_path, acknowledgement):
    root = tmp_path / "drafts"
    store = InvestmentPolicyStore(root)
    with pytest.raises(PolicyStoreError) as error:
        store.save(payload(), preview_draft(payload())["preview_sha256"], acknowledgement)
    assert error.value.code == "DRAFT_ACKNOWLEDGEMENT_REQUIRED"
    assert not root.exists()


def test_save_changed_label_or_choices_requires_new_preview_without_write(tmp_path):
    root = tmp_path / "drafts"
    store = InvestmentPolicyStore(root)
    preview = store.preview(payload())
    for changed in (payload("Changed label"), payload(cadence="quarterly")):
        with pytest.raises(PolicyStoreError) as error:
            store.save(changed, preview["preview_sha256"], True)
        assert error.value.status == 409 and error.value.code == "DRAFT_PREVIEW_CHANGED"
    assert not root.exists()


@pytest.mark.parametrize("alter", ["label", "semantics", "parameter", "boolean_schema", "extra"])
def test_reads_detect_tampered_persisted_canonical_content(tmp_path, alter):
    store = InvestmentPolicyStore(tmp_path / "drafts")
    record, _ = save(store)
    path = store.root / (record["draft_id"] + ".json")
    data = json.loads(path.read_text())
    if alter == "label":
        data["draft"]["label"] = "Changed evidence"
    elif alter == "semantics":
        data["draft"]["decision_semantics"] = "different-runtime"
    elif alter == "parameter":
        data["draft"]["parameters"]["horizon_count"] = 4
    elif alter == "boolean_schema":
        data["draft"]["schema_version"] = True
    else:
        data["secret"] = "unexpected"
    path.write_text(json.dumps(data))
    for read in (lambda: store.get(record["draft_id"]), store.list, lambda: save(store)):
        with pytest.raises(ValueError):
            read()


@pytest.mark.parametrize(
    "content", [b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}', b'{"x":1e999}', b"\xff"]
)
def test_strict_json_rejects_ambiguous_or_nonfinite_input(content):
    with pytest.raises((ValueError, UnicodeError)):
        strict_json(content)


def test_duplicate_fields_in_saved_json_are_rejected(tmp_path):
    store = InvestmentPolicyStore(tmp_path / "drafts")
    record, _ = save(store)
    path = store.root / (record["draft_id"] + ".json")
    path.write_text(path.read_text().rstrip()[:-1] + ',"draft":{}}')
    with pytest.raises(ValueError, match="duplicate"):
        store.list()


@pytest.mark.parametrize("location", ["root", "parent", "record", "lock"])
def test_symlinks_never_followed_for_read_or_save(tmp_path, location):
    real = tmp_path / "real"
    real.mkdir(mode=0o700)
    store = InvestmentPolicyStore(real / "drafts")
    if location in {"root", "parent"}:
        link = tmp_path / "link"
        link.symlink_to(real, target_is_directory=True)
        with pytest.raises(ValueError, match="symlink"):
            InvestmentPolicyStore(link if location == "root" else link / "drafts")
    else:
        record, _ = save(store)
        target = tmp_path / "unrelated"
        target.write_text("PRIVATE unrelated operator data")
        path = store.root / ((record["draft_id"] + ".json") if location == "record" else ".lock")
        path.unlink()
        path.symlink_to(target)
        with pytest.raises((ValueError, OSError)):
            store.list() if location == "record" else save(store, payload("Different"))
        assert target.read_text() == "PRIVATE unrelated operator data"


def test_private_permissions_are_required_not_silently_changed(tmp_path):
    root = tmp_path / "public"
    root.mkdir(mode=0o755)
    with pytest.raises(ValueError, match="owner-only"):
        InvestmentPolicyStore(root)
    root.chmod(0o700)
    store = InvestmentPolicyStore(root)
    record, _ = save(store)
    path = root / (record["draft_id"] + ".json")
    path.chmod(0o644)
    with pytest.raises(ValueError, match="owner-only"):
        store.get(record["draft_id"])
    assert path.stat().st_mode & 0o777 == 0o644


def test_bounded_record_count_combined_size_and_duplicate_at_capacity(tmp_path, monkeypatch):
    store = InvestmentPolicyStore(tmp_path / "drafts")
    first, _ = save(store)
    monkeypatch.setattr(policy_store, "MAX_DRAFTS", 1)
    assert save(store) == (first, False)
    with pytest.raises(PolicyStoreError) as error:
        save(store, payload("Another"))
    assert error.value.status == 429
    monkeypatch.setattr(policy_store, "MAX_DRAFTS", 100)
    size = sum(path.stat().st_size for path in store.root.glob("draft-*.json"))
    monkeypatch.setattr(policy_store, "MAX_COMBINED_BYTES", size + 10)
    with pytest.raises(PolicyStoreError, match="budget"):
        save(store, payload("Another"))
    monkeypatch.setattr(policy_store, "MAX_COMBINED_BYTES", size - 1)
    with pytest.raises(ValueError, match="combined"):
        store.list()


def test_oversized_record_rejected_before_save_and_read(tmp_path, monkeypatch):
    store = InvestmentPolicyStore(tmp_path / "drafts")
    monkeypatch.setattr(policy_store, "MAX_RECORD_BYTES", 100)
    with pytest.raises(PolicyStoreError, match="record limit"):
        save(store)
    assert not store.root.exists()
    monkeypatch.setattr(policy_store, "MAX_RECORD_BYTES", 32768)
    record, _ = save(store)
    path = store.root / (record["draft_id"] + ".json")
    path.write_bytes(b" " * 32769)
    with pytest.raises(ValueError, match="budget"):
        store.get(record["draft_id"])


def test_invalid_identifiers_and_nonregular_files_fail_without_disclosing_other_content(tmp_path):
    store = InvestmentPolicyStore(tmp_path / "drafts")
    for identifier in ("../../operator.sqlite3", "draft-" + "f" * 63, "draft-" + "F" * 64):
        with pytest.raises(PolicyStoreError) as error:
            store.get(identifier)
        assert error.value.status == 404
    record, _ = save(store)
    path = store.root / (record["draft_id"] + ".json")
    path.unlink()
    os.mkfifo(path, mode=0o600)
    with pytest.raises(ValueError, match="regular"):
        store.get(record["draft_id"])


def test_concurrent_identical_saves_create_one_immutable_record(tmp_path):
    root = tmp_path / "drafts"
    stores = [InvestmentPolicyStore(root) for _ in range(8)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        outcomes = list(executor.map(save, stores))
    assert sum(created for _, created in outcomes) == 1
    assert len({result["draft_id"] for result, _ in outcomes}) == 1
    assert len(list(root.glob("draft-*.json"))) == 1
    assert not list(root.glob(".pending-*"))


def test_nonregular_lock_and_cross_process_lock_contention_do_not_block_or_publish(tmp_path):
    store = InvestmentPolicyStore(tmp_path / "drafts")
    first, _ = save(store)
    lock = store.root / ".lock"
    with lock.open("rb") as held:
        fcntl.flock(held.fileno(), fcntl.LOCK_EX)
        with pytest.raises(PolicyStoreError) as error:
            save(store, payload("Another"))
        assert error.value.status == 409 and error.value.code == "DRAFT_STORAGE_BUSY"
    assert store.list()["drafts"] == [first]
    lock.unlink()
    os.mkfifo(lock, mode=0o600)
    with pytest.raises(ValueError, match="regular"):
        save(store, payload("Another"))
    assert store.list()["drafts"] == [first]
