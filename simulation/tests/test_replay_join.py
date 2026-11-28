"""Phase 01-O: replay SQL batching must not weaken event-store integrity."""
from __future__ import annotations

import threading

import pytest

from carlos_sim import DomainEvent, SQLiteEventStore, TimeEngine
from carlos_sim.store import IntegrityError


def location_event(number: int) -> DomainEvent:
    return DomainEvent(
        "LocationCreated", None, "replay query regression fixture", 0,
        {"id": f"site-{number:02d}", "name": f"Site {number}"}
    )


def test_replay_uses_bounded_sql_selects_without_per_event_command_query(tmp_path):
    with SQLiteEventStore(tmp_path / "joined.sqlite") as store:
        store.create_world("test")
        batch = [location_event(i) for i in range(40)]
        saved = store.append("test", "setup", 0, batch, bootstrap=True)
        sql: list[str] = []
        store.db.set_trace_callback(sql.append)
        try:
            restored = store.load("test", use_snapshot=False)
        finally:
            store.db.set_trace_callback(None)
        selects = [q for q in sql if q.lstrip().upper().startswith("SELECT ")]
        assert len(selects) == 2  # world metadata + one joined replay stream
        assert restored.revision == 40
        assert restored.to_dict() == saved.to_dict()
        assert store.verify("test").to_dict() == saved.to_dict()


def test_mixed_command_provenance_and_snapshot_replay_stay_equal(tmp_path):
    with SQLiteEventStore(tmp_path / "mixed.sqlite") as store:
        store.create_world("test")
        store.append("test", "setup", 0,
                     [location_event(1), location_event(2)], bootstrap=True)
        store.snapshot("test")
        clock = TimeEngine(store)
        clock.open_session("test")
        advanced = clock.advance(
            "test", seconds=60, command_id="advance-time",
            expected_revision=store.load("test").revision)
        assert advanced.state.time == 60
        store.snapshot("test")
        restored = store.load("test", use_snapshot=False)
        assert restored.to_dict() == advanced.state.to_dict()
        assert store.verify("test").to_dict() == advanced.state.to_dict()
        clock.close_session("test")


def test_missing_command_is_detected_by_left_join_replay(tmp_path):
    with SQLiteEventStore(tmp_path / "missing.sqlite") as store:
        store.create_world("test")
        store.append("test", "setup", 0, [location_event(1)])
        # Simulate a physically corrupted database; never bypass FK in
        # application code. LEFT JOIN must expose this as missing provenance.
        store.db.execute("PRAGMA foreign_keys=OFF")
        store.db.execute("DELETE FROM commands WHERE world_id=? AND command_id=?",
                         ("test", "setup"))
        with pytest.raises(IntegrityError, match="command is missing"):
            store.load("test", use_snapshot=False)


def test_load_keeps_one_sqlite_read_view_during_concurrent_append(tmp_path):
    filename = tmp_path / "concurrent-read.sqlite"
    with SQLiteEventStore(filename) as seed:
        seed.create_world("test")

    head_read = threading.Event()
    writer_commit_attempt = threading.Event()
    loaded: list[object] = []
    errors: list[BaseException] = []

    def read_world() -> None:
        try:
            with SQLiteEventStore(filename) as reader:
                original_world_row = reader._world_row

                def pause_after_head(world_id: str):
                    row = original_world_row(world_id)
                    head_read.set()
                    assert writer_commit_attempt.wait(5)
                    return row

                reader._world_row = pause_after_head
                loaded.append(reader.load("test"))
        except BaseException as exc:  # surfaced in the owning test thread
            errors.append(exc)

    def append_time() -> None:
        try:
            assert head_read.wait(5)
            with SQLiteEventStore(filename) as writer:
                clock = TimeEngine(writer)
                clock.open_session("test")

                def trace_writer(sql: str) -> None:
                    if sql.strip().upper() == "COMMIT":
                        writer_commit_attempt.set()

                writer.db.set_trace_callback(trace_writer)
                clock.advance("test", seconds=60, command_id="writer-time",
                              expected_revision=0)
        except BaseException as exc:
            errors.append(exc)

    read_thread = threading.Thread(target=read_world)
    write_thread = threading.Thread(target=append_time)
    read_thread.start()
    write_thread.start()
    read_thread.join(10)
    write_thread.join(10)
    assert not read_thread.is_alive()
    assert not write_thread.is_alive()
    assert not errors
    assert len(loaded) == 1
    assert loaded[0].revision == 0
    with SQLiteEventStore(filename) as store:
        assert store.load("test").revision == 1
        assert store.verify("test").revision == 1
