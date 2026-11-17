"""Nonrelease PLAY49-I probe: genuine pre-G reader vs persisted site-trade receipts.

Run each mode in a separate interpreter with its OWN pinned PYTHONPATH.
This is a historical acceptance probe; it neither migrates nor rewrites saves.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import sqlite3
import sys

from carlos_sim import DomainEvent, NPCMarketService, SQLiteEventStore, TimeEngine
from carlos_sim.domain import SCHEMA_VERSION, RULES_VERSION


def _version(db: SQLiteEventStore, world: str):
    return db.db.execute(
        "SELECT schema_version, rules_version FROM worlds WHERE id=?",
        (world,),
    ).fetchone()


def create_current(path: Path):
    from test_market_02c import _rev
    from test_play49_fruit_stall_contract import WORLD, copper
    from test_play49_site_funded_procurement import (
        _setup, _first_real_plate, _second_authentic_goods,
    )

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
                "compat-real-site-" + label, "second-tavern-" + label,
                1, cost, expected_revision=_rev(db),
            )
        state = db.load(WORLD)
        assert _version(db, WORLD) == (45, 70) == (SCHEMA_VERSION, RULES_VERSION)
        assert state.market_trades["compat-real-site-fruit"]["business_keeper_id"] == "tavern_host"
        assert state.market_trades["compat-real-site-cheese"]["business_keeper_id"] == "tavern_host"
        assert state.resources["tavern"]["fruit"] == state.resources["tavern"]["cheese"] == 1
        assert copper(state) == copper(opening) == 22
        db.snapshot(WORLD)
        assert db.verify(WORLD).to_dict() == state.to_dict()
        clock.close_session(WORLD)
        print("CURRENT_WRITER_FINITE_TRADE_VALIDATED")


def old_read(path: Path):
    # THE OLD READER IS ALLOWED TO REJECT but not corrupt or silently accept
    # the changed trade record under an unchanged Rules 70 marker.
    before = sha256(path.read_bytes()).hexdigest()
    with SQLiteEventStore(path) as db:
        assert _version(db, "village") == (45, 70) == (SCHEMA_VERSION, RULES_VERSION)
        try:
            db.verify("village")
        except (ValueError, TypeError, KeyError) as exc:
            print("PRE_G_OLD_READER_REJECTS_SAME_VERSION_RECEIPT:", type(exc).__name__, str(exc)[:180])
        else:
            raise AssertionError("Pre-G reader silently accepted new same-version trade receipt")
    assert sha256(path.read_bytes()).hexdigest() == before, "old reader mutated protected save"
    print("PRE_G_REFUSAL_NONDESTRUCTIVE")


def create_old(path: Path):
    with SQLiteEventStore(path) as db:
        db.create_world("historic")
        state = db.append(
            "historic", "old-writer-location", 0, [
                DomainEvent("LocationCreated", None, "genuine pre-G writer", 0,
                            {"id": "square", "name": "Square"})
            ]
        )
        db.snapshot("historic")
        assert db.verify("historic").to_dict() == state.to_dict()
        assert _version(db, "historic") == (45, 70)
        print("PRE_G_SAVE_CREATED")


def new_read_old(path: Path):
    before = sha256(path.read_bytes()).hexdigest()
    with SQLiteEventStore(path) as db:
        state = db.load("historic")
        assert _version(db, "historic") == (45, 70)
        assert state.locations["square"] == {"name": "Square"}
        assert db.verify("historic").to_dict() == state.to_dict()
        assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    assert sha256(path.read_bytes()).hexdigest() == before
    print("CURRENT_READER_READS_GENUINE_PRE_G_SNAPSHOT")


if __name__ == "__main__":
    assert len(sys.argv) == 3, "usage: script.py new-write|old-read|old-write|new-read <file>"
    mode, filepath = sys.argv[1], Path(sys.argv[2])
    assert mode in {"new-write", "old-read", "old-write", "new-read"}
    if mode == "new-write":
        create_current(filepath)
    elif mode == "old-read":
        old_read(filepath)
    elif mode == "old-write":
        create_old(filepath)
    else:
        new_read_old(filepath)
