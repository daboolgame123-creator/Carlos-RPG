"""PLAY-28-A: fatigued workers must not bypass their physical work/travel gate."""
from __future__ import annotations

from carlos_sim import SQLiteEventStore, TimeEngine, LivingWorldEngine
from carlos_sim.routines import work_allowed_at, choose_routine_route
from test_routines_02f import scenario, ev


def test_shift_gate_rejects_exhaustion_but_allows_recovery(tmp_path):
    with SQLiteEventStore(tmp_path / "gate.sqlite") as db:
        scenario(db)
        state = db.load("test")
        state.entities["basim"]["location_id"] = "smithy"
        state.npcs["basim"]["needs"]["fatigue"] = 85
        assert not work_allowed_at(state.entities, state.npcs, state.npc_routines,
                                   100, "basim")
        state.npcs["basim"]["needs"]["fatigue"] = 84
        assert work_allowed_at(state.entities, state.npcs, state.npc_routines,
                               100, "basim")
        # Worlds without configured shifts retain their previous work policy.
        state.npcs["nora"]["needs"]["fatigue"] = 100
        assert work_allowed_at(state.entities, state.npcs, state.npc_routines,
                               100, "nora")


def test_exhausted_routine_npc_does_not_fallback_to_random_travel(tmp_path):
    with SQLiteEventStore(tmp_path / "fatigue.sqlite") as db:
        scenario(db)
        clock = TimeEngine(db)
        clock.open_session("test")
        initial = db.load("test")
        changed = db.append("test", "fatigued", initial.revision, [
            ev("NPCNeedChanged", {"npc_id": "basim", "need": "fatigue",
                                  "previous": 10, "current": 90}, who="basim")
        ])
        assert choose_routine_route(changed, "basim") is None
        engine = LivingWorldEngine(db, clock, navigation_enabled=True,
                                   routines_enabled=True)
        advanced = engine.advance("test", seconds=1, command_id="fatigued-tick",
                                  expected_revision=changed.revision).state
        assert not [t for t in advanced.travels.values() if t["npc_id"] == "basim"]
        assert db.verify("test").to_dict() == advanced.to_dict()


def test_rest_uses_clock_time_and_reduces_fatigue_without_teleport(tmp_path):
    with SQLiteEventStore(tmp_path / "rest.sqlite") as db:
        scenario(db)
        clock = TimeEngine(db)
        clock.open_session("test")
        initial = db.load("test")
        tired = db.append("test", "tired-for-rest", initial.revision, [
            ev("NPCNeedChanged", {"npc_id": "basim", "need": "fatigue",
                                  "previous": 10, "current": 90}, who="basim")
        ])
        engine = LivingWorldEngine(db, clock, navigation_enabled=True,
                                   routines_enabled=True, survival_enabled=True)
        first = engine.advance("test", seconds=1, command_id="rest-start",
                               expected_revision=tired.revision).state
        active = [a for a in first.actions.values()
                  if a["npc_id"] == "basim" and a["action"] == "rest"]
        assert len(active) == 1 and active[0]["status"] == "running"
        assert first.npcs["basim"]["needs"]["fatigue"] == 90
        assert first.entities["basim"]["location_id"] == "square"
        completed = engine.advance("test", seconds=119, command_id="rest-finish",
                                   expected_revision=first.revision).state
        assert completed.time == 120
        assert completed.actions[active[0]["schedule_id"].replace("npc-action:", "")]["status"] == "completed"
        assert completed.npcs["basim"]["needs"]["fatigue"] == 70
        assert completed.entities["basim"]["location_id"] == "square"
        assert db.verify("test").to_dict() == completed.to_dict()
