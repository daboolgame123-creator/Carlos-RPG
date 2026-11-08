"""PLAY-28: real three-day NPC lifecycle, with metabolism and all activities on.

The two independent disposable worlds start with the SAME water, seed, tools,
copper, roads, and seven named NPCs. Only finite personally owned food differs.
No economy-only shortcut, no wall clock and no hidden replenishment.
"""
from __future__ import annotations

import pytest

from carlos_sim import SQLiteEventStore, TimeEngine, LivingWorldEngine
from play_physical_supply import WORLD, DAY, PEOPLE, seed_physical_supply, audit_physical_supply


@pytest.mark.parametrize("personal_food", [0, 18], ids=["shortage", "finite-provisions"])
def test_real_three_day_endurance_and_conservation(tmp_path, personal_food):
    with SQLiteEventStore(tmp_path / f"three-days-{personal_food}.sqlite") as db:
        seed_physical_supply(db, personal_food=personal_food)
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        initial = db.load(WORLD)
        assert len(initial.npcs) == len(PEOPLE) == 7
        assert all(initial.resources[who]["food"] == personal_food for who, *_ in PEOPLE)
        engine = LivingWorldEngine(
            db, clock, decision_cooldown=3600,
            max_events_per_advance=5000,
            navigation_enabled=True, routines_enabled=True,
            survival_enabled=True, consumption_enabled=True,
            supply_enabled=True, economic_enabled=True,
            agriculture_enabled=True,
            economy_only_enabled=False,
        )
        activity_by_day = []
        try:
            for day in range(3):
                daily_before = db.load(WORLD)
                for quarter in range(4):
                    now = db.load(WORLD)
                    arrived = engine.advance(
                        WORLD, seconds=DAY // 4,
                        command_id=f"real-full-day-{day}-quarter-{quarter}",
                        expected_revision=now.revision,
                    ).state
                    assert arrived.time == (day * 4 + quarter + 1) * (DAY // 4)
                    audit_physical_supply(
                        arrived, seed=1, water=2, buyer_copper=2,
                        personal_food=personal_food,
                    )
                state = db.load(WORLD)
                daily_actions = sum(
                    action["start"] >= daily_before.time
                    for action in state.actions.values()
                )
                activity_by_day.append(daily_actions)
                assert daily_actions > 0, "daily NPC decision/action activity disabled"
                assert state.time == (day + 1) * DAY
                assert len(state.npcs) == 7
                assert all(0 <= p["needs"]["hunger"] <= 100 and
                           0 <= p["needs"]["fatigue"] <= 100
                           for p in state.npcs.values())
            final = db.load(WORLD)
            assert final.time == 3 * DAY
            assert min(activity_by_day) > 0
            audit_physical_supply(final, seed=1, water=2, buyer_copper=2,
                                  personal_food=personal_food)
            consumed = sum(m["quantity"] for m in final.consumptions.values())
            if personal_food == 0:
                assert consumed <= final.farm_plots["farm"]["matured"]
                assert max(x["needs"]["hunger"] for x in final.npcs.values()) >= 90
            else:
                assert consumed > 0
                assert sum(final.resources[who]["food"] for who, *_ in PEOPLE) < 7 * personal_food
            assert db.verify(WORLD).to_dict() == final.to_dict()
            db.snapshot(WORLD)
            assert db.verify(WORLD).to_dict() == final.to_dict()
            print("PLAY28_3DAY", dict(personal_food=personal_food,
                  seconds=final.time, daily_actions=activity_by_day,
                  consumed=consumed,
                  meals=len(final.consumptions),
                  max_hunger=max(x["needs"]["hunger"] for x in final.npcs.values()),
                  max_fatigue=max(x["needs"]["fatigue"] for x in final.npcs.values()),
                  growth=final.farm_plots["farm"]["matured"],
                  cargo_deliveries=final.supply_circuits["huda"]["deliveries"]))
        finally:
            clock.close_session(WORLD)
