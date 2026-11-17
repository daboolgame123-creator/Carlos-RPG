"""PLAY49-I isolated save-version gate: genuine Rules70 vs new Rules71.

Separate-process tests use a frozen pre-G reader/writer. Never migrate,
rewrite, or silently reinterpret a historical saved world.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import sys

from carlos_sim import DomainEvent, NPCMarketService, SQLiteEventStore, TimeEngine
from carlos_sim.domain import SCHEMA_VERSION, RULES_VERSION
from carlos_sim.store import UnsupportedVersion


def version(db, world):
    return db.db.execute(
        "SELECT schema_version,rules_version FROM worlds WHERE id=?", (world,)
    ).fetchone()


def current_write(path: Path):
    from test_market_02c import _rev
    from test_play49_fruit_stall_contract import WORLD, copper
    from test_play49_site_funded_procurement import (
        _setup, _first_real_plate, _second_authentic_goods,
    )
    assert (SCHEMA_VERSION, RULES_VERSION) == (45, 71)
    with SQLiteEventStore(path) as db:
        _setup(db)
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        market = NPCMarketService(db, clock)
        opening = db.load(WORLD)
        _first_real_plate(db, clock, market)
        _second_authentic_goods(db, clock, market)
        for label, cost in (("fruit", 2), ("cheese", 3)):
            market.buy_for_site(
                WORLD, "tavern_host", "tavern",
                "rules71-real-site-" + label, "second-tavern-" + label,
                1, cost, expected_revision=_rev(db),
            )
        state = db.load(WORLD)
        assert version(db, WORLD) == (45, 71)
        assert state.market_trades["rules71-real-site-fruit"]["business_keeper_id"] == "tavern_host"
        assert state.market_trades["rules71-real-site-cheese"]["business_keeper_id"] == "tavern_host"
        assert state.resources["tavern"]["fruit"] == state.resources["tavern"]["cheese"] == 1
        assert copper(state) == copper(opening) == 22
        db.snapshot(WORLD)
        assert db.verify(WORLD).to_dict() == state.to_dict()
        clock.close_session(WORLD)
    print("CURRENT_RULES71_GENUINE_TRADE_SAVE_REPLAY_OK")


def old_read_new(path: Path):
    # The old real reader must refuse on version mismatch, not attempt to
    # decode the new business receipt and label valid events as corruption.
    assert (SCHEMA_VERSION, RULES_VERSION) == (45, 70)
    before = sha256(path.read_bytes()).hexdigest()
    with SQLiteEventStore(path) as db:
        assert version(db, "village") == (45, 71)
        for method in (db.load, db.verify):
            try:
                method("village")
            except UnsupportedVersion as exc:
                assert "schema/rules mismatch" in str(exc)
            else:
                raise AssertionError("old Rules70 reader did not reject Rules71")
        assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    assert sha256(path.read_bytes()).hexdigest() == before
    print("RULES70_REJECTS_71_VERSION_NOT_CORRUPTION_NO_MUTATION")


def old_write(path: Path):
    assert (SCHEMA_VERSION, RULES_VERSION) == (45, 70)
    with SQLiteEventStore(path) as db:
        db.create_world("historic")
        state = db.append(
            "historic", "old-real-writer", 0, [
                DomainEvent("LocationCreated", None, "genuine Rules70", 0,
                            {"id": "square", "name": "Square"})
            ]
        )
        db.snapshot("historic")
        assert db.verify("historic").to_dict() == state.to_dict()
        assert version(db, "historic") == (45, 70)
    print("FROZEN_RULES70_SNAPSHOT_CREATED")


def current_read_old(path: Path):
    assert (SCHEMA_VERSION, RULES_VERSION) == (45, 71)
    before = sha256(path.read_bytes()).hexdigest()
    with SQLiteEventStore(path) as db:
        assert version(db, "historic") == (45, 70)
        for method in (db.load, db.verify):
            try:
                method("historic")
            except UnsupportedVersion as exc:
                assert "schema/rules mismatch" in str(exc)
            else:
                raise AssertionError("Rules71 reader silently reinterpreted Rules70 save")
        assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    assert sha256(path.read_bytes()).hexdigest() == before
    print("RULES71_REJECTS_70_WITHOUT_MIGRATION_OR_MUTATION")


if __name__ == "__main__":
    assert len(sys.argv) == 3, "usage: gate.py MODE file.sqlite"
    mode, path = sys.argv[1], Path(sys.argv[2])
    table = {
        "current-write": current_write,
        "old-read-new": old_read_new,
        "old-write": old_write,
        "current-read-old": current_read_old,
    }
    table[mode](path)
