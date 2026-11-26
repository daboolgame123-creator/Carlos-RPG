"""Storage authority and replay provenance for explicit player needs/rest."""
from __future__ import annotations

import pytest

from carlos_sim import DomainEvent, SQLiteEventStore, TimeEngine, canonical_hash
from carlos_sim.domain import canonical
from carlos_sim.player_needs import REST_SECONDS
from carlos_sim.store import IntegrityError, InvalidEvent


def event(kind, data, *, time=0):
    return DomainEvent(kind, None, "player needs storage test", time, data)


def seed(db):
    db.create_world("needs")
    return db.append("needs", "setup", 0, [
        event("LocationCreated", {"id": "home", "name": "Home"}),
        event("EntityCreated", {"id": "carlos", "name": "Carlos",
              "location_id": "home", "controller": "player"}),
        event("PlayerNeedsInitialized", {"player_id": "carlos",
              "hunger": 40, "fatigue": 50}),
    ], bootstrap=True)


def rest(state):
    return event("ScheduledEventCreated", {
        "id": "player-rest:carlos:storage", "due": state.time + REST_SECONDS,
        "order": state.next_schedule_order, "kind": "signal", "interrupt": False,
        "payload": {"__player_rest": {"player_id": "carlos", "site_id": "home",
                                     "started_at": state.time}},
    }, time=state.time)


def test_needs_initialization_requires_recorded_bootstrap(tmp_path):
    with SQLiteEventStore(tmp_path / "setup.sqlite") as db:
        db.create_world("needs")
        before = db.load("needs")
        with pytest.raises(InvalidEvent, match="recorded trusted bootstrap"):
            db.append("needs", "untrusted", before.revision, [
                event("PlayerNeedsInitialized", {
                    "player_id": "carlos", "hunger": 0, "fatigue": 0})])
        assert db.verify("needs").to_dict() == before.to_dict()


@pytest.mark.parametrize("case", [
    "no_action", "no_movement", "no_session", "bootstrap", "nonplayer_command", "batch",
])
def test_rest_requires_one_explicit_active_authorized_command(tmp_path, case):
    with SQLiteEventStore(tmp_path / "rest.sqlite") as db:
        before = seed(db)
        if case != "no_session":
            TimeEngine(db).open_session("needs")
        flags = {"action_authorized": case != "no_action",
                 "movement_authorized": case != "no_movement",
                 "bootstrap": case == "bootstrap"}
        events = [rest(before)]
        if case == "batch":
            events.append(event("LocationCreated", {"id": "extra", "name": "Extra"}))
        cid = "ordinary-command" if case == "nonplayer_command" else "player-rest:storage"
        with pytest.raises(InvalidEvent, match="one explicit active player action"):
            db.append("needs", cid, before.revision, events, **flags)
        assert db.verify("needs").to_dict() == before.to_dict()


def test_rest_authority_survives_snapshot_closed_session_and_reopen(tmp_path):
    path = tmp_path / "reopen.sqlite"
    with SQLiteEventStore(path) as db:
        before = seed(db)
        TimeEngine(db).open_session("needs")
        saved = db.append("needs", "player-rest:storage", before.revision, [rest(before)],
                          action_authorized=True, movement_authorized=True)
        db.snapshot("needs")
    with SQLiteEventStore(path) as db:
        assert not db._active_worlds
        assert db.verify("needs").to_dict() == saved.to_dict()
        assert db.load("needs").player_needs["carlos"]["fatigue"] == 50


@pytest.mark.parametrize("column,value", [
    ("bootstrap", 1), ("action_authorized", 0), ("movement_authorized", 0),
    ("first_revision", 0), ("last_revision", 99),
])
def test_rest_replay_rejects_forged_capabilities_or_command_span(tmp_path, column, value):
    with SQLiteEventStore(tmp_path / "provenance.sqlite") as db:
        before = seed(db)
        TimeEngine(db).open_session("needs")
        db.append("needs", "player-rest:storage", before.revision, [rest(before)],
                  action_authorized=True, movement_authorized=True)
        # The parameterized column names are a fixed test-owned allowlist.
        db.db.execute(f"UPDATE commands SET {column}=? WHERE command_id=?",
                      (value, "player-rest:storage"))
        with pytest.raises(IntegrityError, match="explicit command provenance"):
            db.verify("needs")


def test_rest_replay_rejects_renaming_as_an_autonomous_command(tmp_path):
    with SQLiteEventStore(tmp_path / "command.sqlite") as db:
        before = seed(db)
        TimeEngine(db).open_session("needs")
        db.append("needs", "player-rest:storage", before.revision, [rest(before)],
                  action_authorized=True, movement_authorized=True)
        db.db.execute("BEGIN")
        db.db.execute("PRAGMA defer_foreign_keys=ON")
        db.db.execute("UPDATE commands SET command_id='npc-autonomy' WHERE command_id='player-rest:storage'")
        db.db.execute("UPDATE events SET command_id='npc-autonomy' WHERE command_id='player-rest:storage'")
        db.db.execute("COMMIT")
        assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
        with pytest.raises(IntegrityError, match="explicit command provenance"):
            db.verify("needs")


def test_genesis_cannot_inject_needs_without_an_initialization_event(tmp_path):
    with SQLiteEventStore(tmp_path / "genesis.sqlite") as db:
        state = seed(db).to_dict()
        state["revision"] = 0
        db.db.execute("UPDATE worlds SET initial_state=?, initial_hash=? WHERE id='needs'",
                      (canonical(state), canonical_hash(state)))
        with pytest.raises(IntegrityError, match="require recorded events"):
            db.verify("needs")
