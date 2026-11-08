"""PLAY-29 controlled 72h A/B: identical metabolism, different action hunger.

Two identical, physically constrained real seven-NPC worlds; only the
trusted time-zero `activity_hunger_percent` differs: 100% vs 20%.
Records intermediate hunger to avoid mistaking cap saturation for equality.
"""
from __future__ import annotations

from carlos_sim import SQLiteEventStore, TimeEngine, LivingWorldEngine, DomainEvent
from carlos_sim.food_security_audit import audit_food_security
from play_physical_supply import WORLD, DAY, PEOPLE, seed_physical_supply, audit_physical_supply

PERSONAL_PROVISIONS = 6


def run_three_day_village(path, *, activity_percent: int):
    with SQLiteEventStore(path) as db:
        seed_physical_supply(db, personal_food=PERSONAL_PROVISIONS)
        state = db.load(WORLD)
        state = db.append(WORLD, "calibrate-initial-action-costs", state.revision,
            [DomainEvent("MetabolismPolicyConfigured", None,
                         "test-world frozen policy, no additional food", 0,
                         {"hunger_seconds_per_point": 3600,
                          "activity_hunger_percent": activity_percent})],
            bootstrap=True)
        assert len(state.npcs) == len(PEOPLE) == 7
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        engine = LivingWorldEngine(
            db, clock, decision_cooldown=3600, max_events_per_advance=5000,
            navigation_enabled=True, routines_enabled=True,
            survival_enabled=True, consumption_enabled=True,
            supply_enabled=True, economic_enabled=True,
            agriculture_enabled=True, economy_only_enabled=False,
        )
        trajectory=[]
        days=[]
        try:
            for d in range(3):
                before_day = db.load(WORLD)
                for quarter in range(4):
                    before = db.load(WORLD)
                    after = engine.advance(
                        WORLD, seconds=DAY // 4, command_id=f"controlled-day{d}-q{quarter}",
                        expected_revision=before.revision).state
                    assert after.time == (d * 4 + quarter + 1) * (DAY // 4)
                    audit_physical_supply(after, seed=1, water=2, buyer_copper=2,
                                          personal_food=PERSONAL_PROVISIONS)
                    trajectory.append({
                        who: after.npcs[who]["needs"]["hunger"] for who,*_ in PEOPLE
                    })
                today = db.load(WORLD)
                count = sum(a["start"]>=before_day.time for a in today.actions.values())
                days.append(count)
                assert count > 0
                assert db.verify(WORLD).to_dict() == today.to_dict()
            final = db.load(WORLD)
            assert final.time == 259200
            assert len(trajectory) == 12
            assert len(final.npcs) == 7
            assert final.metabolism_policy["hunger_seconds_per_point"] == 3600
            assert final.metabolism_policy["activity_hunger_percent"] == activity_percent
            report = audit_food_security(final)
            db.snapshot(WORLD)
            assert db.verify(WORLD).to_dict() == final.to_dict()
            real_actions=[
                a for a in final.actions.values() if a["status"]=="completed"
            ]
            return {
                "activity_percent":activity_percent,
                "daily_actions":days,
                "trajectory":trajectory,
                "completed_actions":len(real_actions),
                "actual_action_hunger_added":sum(
                    max(0, int(a["result"]["needs"].get("hunger", (0,0))[1])
                            - int(a["result"]["needs"].get("hunger", (0,0))[0]))
                    for a in real_actions),
                "hunger_cap_count":len(report.hunger_at_cap),
                "high_risk":len(report.high_risk),
                "meals":report.consumed_meals,
                "remaining_owned_food":report.personal_food_units,
                "matured":final.farm_plots["farm"]["matured"],
                "deliveries":final.supply_circuits["huda"]["deliveries"],
            }
        finally:
            clock.close_session(WORLD)


def test_real_three_day_action_cost_only_ab(tmp_path):
    ordinary=run_three_day_village(tmp_path/"legacy-cost.sqlite",activity_percent=100)
    adjusted=run_three_day_village(tmp_path/"reduced-cost.sqlite",activity_percent=20)
    assert ordinary["activity_percent"]==100 and adjusted["activity_percent"]==20
    assert len(ordinary["trajectory"])==len(adjusted["trajectory"])==12
    assert ordinary["trajectory"] != adjusted["trajectory"], (
        "real NPC hunger must respond when completed action costs change"
    )
    assert ordinary["completed_actions"]>0 and adjusted["completed_actions"]>0
    assert all(0 <= h <= 100 for snap in ordinary["trajectory"]+adjusted["trajectory"]
               for h in snap.values())
    # No food created in either world; finished hunger is not a substitute
    # for real bread or long-run survival.
    print("PLAY29_72H_ACTIVITY_COST_AB", {"legacy":ordinary,"adjusted":adjusted})
