"""READ-01: short read scopes pin and reuse one verified event projection."""
from __future__ import annotations

import pytest

from carlos_sim import DomainEvent, SQLiteEventStore
from carlos_sim.store import InvalidEvent


def test_read_scope_reuses_verified_state_is_read_only_and_expires(tmp_path):
    with SQLiteEventStore(tmp_path / "read-scope.sqlite") as store:
        store.create_world("test")
        statements: list[str] = []
        store.db.set_trace_callback(statements.append)
        try:
            with store.read_consistent("test") as state:
                after_entry = len(statements)
                assert store.load("test") is state
                assert store.verify("test") is state
                assert len(statements) == after_entry
                with pytest.raises(InvalidEvent, match="writes are forbidden"):
                    store.append("test", "forbidden", 0,
                                 [DomainEvent("LocationCreated", None, "test", 0,
                                              {"id": "site", "name": "Site"})],
                                 bootstrap=True)
                with pytest.raises(InvalidEvent, match="snapshots are forbidden"):
                    store.snapshot("test")
                assert store.load("test").revision == 0
        finally:
            store.db.set_trace_callback(None)

        saved = store.append(
            "test", "after-read", 0,
            [DomainEvent("LocationCreated", None, "test", 0,
                         {"id": "site", "name": "Site"})],
            bootstrap=True,
        )
        assert saved.revision == 1
        assert store.load("test").revision == 1
        assert store.verify("test").to_dict() == saved.to_dict()
