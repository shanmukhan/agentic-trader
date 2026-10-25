import sqlite3

import pytest


def test_reader_observes_committed_state_during_uncommitted_writer_without_writer_lock(engine):
    db = engine.db
    with db.transaction() as writer:
        db.set(writer, "snapshot_probe", "uncommitted")
        with db.read_snapshot() as reader:
            assert (
                reader.execute("SELECT value FROM meta WHERE key='cash'").fetchone()[0] == "25000"
            )
            assert (
                reader.execute("SELECT value FROM meta WHERE key='snapshot_probe'").fetchone()
                is None
            )
            with pytest.raises(sqlite3.OperationalError, match="readonly"):
                db.set(reader, "cash", "0")
    with db.read_snapshot() as reader:
        assert db.get(reader, "snapshot_probe") == "uncommitted"
        assert db.get(reader, "cash") == "25000"


def test_read_transaction_keeps_a_consistent_snapshot_across_writer_commit(engine):
    db = engine.db
    with db.read_snapshot() as reader:
        before = reader.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        with db.transaction() as writer:
            db.event(writer, "2026-10-20T04:30:00+00:00", "snapshot_probe", "test", {})
        assert reader.execute("SELECT COUNT(*) FROM events").fetchone()[0] == before
    with db.read_snapshot() as reader:
        assert reader.execute("SELECT COUNT(*) FROM events").fetchone()[0] == before + 1
