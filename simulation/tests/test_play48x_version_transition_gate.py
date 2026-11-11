"""PLAY-48X: old saves fail closed; new Schema45 Rules60 worlds stay replayable.

This synthetic header downgrade is a deliberate rejection test, NOT a
migration or proof of compatibility with every historical save. The separate
dual-Python workflow checks a real 43/58 world created by its frozen code SHA.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3

import pytest

from carlos_sim import SQLiteEventStore
from carlos_sim.domain import SCHEMA_VERSION, RULES_VERSION, canonical, canonical_hash
from carlos_sim.store import UnsupportedVersion


def test_new_schema45_world_roundtrip_with_unchanged_resources(tmp_path):
    assert (SCHEMA_VERSION, RULES_VERSION) == (45, 61)
    path = tmp_path / "current-world.sqlite"
    with SQLiteEventStore(path) as db:
        initial = db.create_world("current")
        assert (initial.schema_version, initial.rules_version) == (45, 61)
        assert initial.courier_provisions == {}
        assert db.verify("current").to_dict() == initial.to_dict()
        assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)


def test_synthetic_legacy_version_fails_closed_without_rewriting_sqlite(tmp_path):
    path = tmp_path / "old-world-marker.sqlite"
    with SQLiteEventStore(path) as db:
        db.create_world("legacy")
        original = db.verify("legacy").to_dict()
        assert (original["schema_version"], original["rules_version"]) == (45, 61)
    # An otherwise hash-consistent fixture marking an old 43/58 save. This
    # ensures the error is due to the version boundary and does not imply
    # old events have been silently transformed to 44/59.
    older = dict(original, schema_version=43, rules_version=58)
    with sqlite3.connect(path) as raw:
        raw.execute(
            "UPDATE worlds SET schema_version=?, rules_version=?, "
            "initial_state=?, initial_hash=? WHERE id=?",
            (43, 58, canonical(older), canonical_hash(older), "legacy"),
        )
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    with SQLiteEventStore(path) as db:
        with pytest.raises(UnsupportedVersion, match="schema/rules mismatch"):
            db.load("legacy")
        with pytest.raises(UnsupportedVersion, match="schema/rules mismatch"):
            db.verify("legacy")
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
    with sqlite3.connect(path) as raw:
        assert raw.execute(
            "SELECT schema_version, rules_version FROM worlds WHERE id='legacy'"
        ).fetchone() == (43, 58)
        assert raw.execute("PRAGMA integrity_check").fetchone() == ("ok",)
