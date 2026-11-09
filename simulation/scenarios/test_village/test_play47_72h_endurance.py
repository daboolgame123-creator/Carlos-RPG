"""PLAY-47 actual 72-hour autonomous joined-world observation.

No player orders, manual trade, forced NPC movement or post-start supply.
This is a *scarcity* endurance experiment, NOT survival success or release.
Two separately initialized SQLite worlds use existing trusted hunger policies.
"""
from __future__ import annotations

import json

import pytest

from carlos_sim import DomainEvent, SQLiteEventStore, TimeEngine
from carlos_sim.economic_diagnostics import audit_npc_economy
from play_physical_supply import DAY, WORLD
from test_play47_joined_professions import _joined_bootstrap, _engine


@pytest.mark.parametrize("hunger_period_seconds", [300, 3600])
def test_one_real_eleven_npc_world_72_hours_with_finite_food(
    tmp_path, hunger_period_seconds,
):
    with SQLiteEventStore(
        tmp_path / f"joined-72h-{hunger_period_seconds}.sqlite"
    ) as db:
        state = _joined_bootstrap(db)
        if hunger_period_seconds == 3600:
            state = db.append(
                WORLD, "play47:72h:slower-physiology", state.revision,
                [DomainEvent(
                    "MetabolismPolicyConfigured", None,
                    "trusted time-zero existing physiology counterfactual", 0,
                    {"hunger_seconds_per_point": 3600,
                     "activity_hunger_percent": 20},
                )],
                bootstrap=True,
            )
        assert len(state.npcs) == 11
        initial = audit_npc_economy(state)
        assert initial["copper_scope_complete"]
        assert initial["copper_known_total"] == 12
        assert initial["trades"] == 0
        assert initial["completed_jobs"] == 0
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            engine = _engine(db, clock)
            measures = []
            known_water_at_start = sum(
                entry["water"] for entry in state.resources.values()
                if "water" in entry and entry["water"] is not None
            )
            previous_counts = (0, 0, 0)
            for tick in range(DAY // 4, 3 * DAY + 1, DAY // 4):
                state = engine.advance(
                    WORLD, seconds=tick - state.time,
                    command_id=f"play47:72h:{hunger_period_seconds}:{tick}",
                    expected_revision=state.revision,
                ).state
                assert state.time == tick
                current = audit_npc_economy(state)
                assert current["copper_scope_complete"]
                assert current["copper_known_total"] == 12
                assert len(current["npc_hunger"]) == 11
                assert all(
                    type(h) is int and 0 <= h <= 100
                    for h in current["npc_hunger"].values()
                )
                current_counts = (
                    current["trades"],
                    current["completed_jobs"],
                    current["wage_receipts"],
                )
                assert all(a >= b for a, b in zip(current_counts, previous_counts))
                previous_counts = current_counts
                known_water_now = sum(
                    entry["water"] for entry in state.resources.values()
                    if "water" in entry and entry["water"] is not None
                )
                # This closed-world fixture has no authorized rainfall
                # observations. Water is physically carried or consumed,
                # never credited by the test or recreated for free.
                assert known_water_now <= known_water_at_start
                assert not any(
                    type(value) is not int or value < 0
                    for entry in state.resources.values()
                    for value in entry.values() if value is not None
                )
                if tick in (DAY, 2 * DAY, 3 * DAY):
                    db.snapshot(WORLD)
                    assert db.verify(WORLD).to_dict() == state.to_dict()
                    measures.append({
                        "day": tick // DAY,
                        "hunger_at_100": sum(
                            value == 100 for value in current["npc_hunger"].values()
                        ),
                        "trades": current["trades"],
                        "jobs": current["completed_jobs"],
                        "wages": current["wage_receipts"],
                        "copper": current["copper_known_total"],
                        "known_water": known_water_now,
                    })
            assert state.time == 3 * DAY
            assert current["trades"] >= 6
            assert current["completed_jobs"] >= 2
            assert current["wage_receipts"] >= 1
            if hunger_period_seconds == 300:
                assert measures[0]["hunger_at_100"] == 11
            assert db.db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            print("PLAY47_REAL_JOINED_72H", json.dumps(
                {"hunger_seconds_per_point": hunger_period_seconds,
                 "checkpoints": measures}, sort_keys=True,
            ))
        finally:
            clock.close_session(WORLD)
