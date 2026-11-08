"""PLAY-29: two real 72h seven-NPC worlds; hunger clock is the ONLY input change.

The original 300s profile and the separately configured 3600s profile keep
identical finite food, crop seed, water, tools, money, roads and schedules.
This experiment does not silently change the canonical existing game world.
"""
from __future__ import annotations

from carlos_sim import SQLiteEventStore, TimeEngine, LivingWorldEngine, DomainEvent
from carlos_sim.food_security_audit import audit_food_security
from play_physical_supply import WORLD, DAY, PEOPLE, seed_physical_supply, audit_physical_supply

PERSONAL_PROVISIONS = 6


def real_three_days(path, *, opt_in: bool):
    with SQLiteEventStore(path) as db:
        seed_physical_supply(db, personal_food=PERSONAL_PROVISIONS)
        state = db.load(WORLD)
        if opt_in:
            state = db.append(WORLD, "experimental-rate-once", state.revision,
                              [DomainEvent("MetabolismPolicyConfigured", None,
                                           "trusted independent test-only choice", 0,
                                           {"hunger_seconds_per_point": 3600})],
                              bootstrap=True)
        assert len(state.npcs) == len(PEOPLE) == 7
        assert state.time == 0
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        engine = LivingWorldEngine(
            db, clock, decision_cooldown=3600, max_events_per_advance=5000,
            navigation_enabled=True, routines_enabled=True, survival_enabled=True,
            consumption_enabled=True, supply_enabled=True, economic_enabled=True,
            agriculture_enabled=True, economy_only_enabled=False,
        )
        daily_actions=[]
        hunger_trajectory=[]
        try:
            for day in range(3):
                before_day = db.load(WORLD)
                for quarter in range(4):
                    before = db.load(WORLD)
                    after = engine.advance(
                        WORLD, seconds=DAY//4,
                        command_id=f"world-{day}-{quarter}",
                        expected_revision=before.revision,
                    ).state
                    assert after.time == (day*4+quarter+1)*(DAY//4)
                    audit_physical_supply(after, seed=1, water=2, buyer_copper=2,
                                          personal_food=PERSONAL_PROVISIONS)
                    # Capture every 6 hours: final hunger can saturate at
                    # 100 in BOTH worlds despite different earlier rates.
                    hunger_trajectory.append({
                        who: after.npcs[who]["needs"]["hunger"]
                        for who, *_ in PEOPLE
                    })
                today = db.load(WORLD)
                n = sum(a["start"]>=before_day.time for a in today.actions.values())
                assert n>0
                daily_actions.append(n)
                assert db.verify(WORLD).to_dict() == today.to_dict()
            final=db.load(WORLD)
            assert final.time==259200
            db.snapshot(WORLD)
            assert db.verify(WORLD).to_dict()==final.to_dict()
            report=audit_food_security(final)
            assert report.npc_count==7
            return {
                "seconds":final.time,
                "policy":dict(final.metabolism_policy),
                "daily_actions":daily_actions,
                "hunger_trajectory":hunger_trajectory,
                "hunger":{n: final.npcs[n]["needs"]["hunger"] for n,*_ in PEOPLE},
                "high_risk":len(report.high_risk),
                "hunger_cap_count":len(report.hunger_at_cap),
                "meals":sum(m["quantity"] for m in final.consumptions.values()),
                "remaining_owned_food":report.personal_food_units,
                "growth":final.farm_plots["farm"]["matured"],
                "deliveries":final.supply_circuits["huda"]["deliveries"],
            }
        finally:
            clock.close_session(WORLD)


def test_finite_provisions_with_normal_and_experimental_metabolism(tmp_path):
    original=real_three_days(tmp_path/"ordinary.sqlite", opt_in=False)
    calibrated=real_three_days(tmp_path/"calibrated.sqlite", opt_in=True)
    assert original["seconds"]==calibrated["seconds"]==3*DAY
    assert original["policy"]=={}
    assert calibrated["policy"]=={"hunger_seconds_per_point":3600}
    assert all(a>0 for a in original["daily_actions"]+calibrated["daily_actions"])
    assert all(0<=v<=100 for v in original["hunger"].values())
    assert all(0<=v<=100 for v in calibrated["hunger"].values())
    assert len(original["hunger_trajectory"]) == len(calibrated["hunger_trajectory"]) == 12
    assert original["hunger_trajectory"][0] != calibrated["hunger_trajectory"][0], (
        "the frozen per-world rate must change early NPC needs even if starvation "
        "eventually pushes both worlds to the same 100-hunger ceiling"
    )
    print("PLAY29_REAL_3DAY_METABOLISM_AB",{
        "original": original, "calibrated": calibrated,
    })
