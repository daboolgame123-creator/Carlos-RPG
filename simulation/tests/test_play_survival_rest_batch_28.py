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
