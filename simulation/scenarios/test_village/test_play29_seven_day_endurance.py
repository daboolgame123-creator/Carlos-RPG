"""PLAY-29: seven real NPC days of finite food and water, no happy-ending assumption."""
from __future__ import annotations

from carlos_sim import SQLiteEventStore, TimeEngine, LivingWorldEngine, DomainEvent
from carlos_sim.food_security_audit import audit_food_security
from play_physical_supply import (
    WORLD, DAY, PEOPLE, seed_physical_supply, audit_physical_supply,
)

DAYS = 7
INITIAL_PERSONAL_FOOD = 6


def test_actual_seven_day_optimistic_calibration_still_audits_every_resource(tmp_path):
    with SQLiteEventStore(tmp_path / "seven-day-real-village.sqlite") as db:
        seed_physical_supply(db, personal_food=INITIAL_PERSONAL_FOOD)
        initial = db.load(WORLD)
        configured = db.append(
            WORLD, "seven-day-frozen-life-policy", initial.revision,
            [DomainEvent("MetabolismPolicyConfigured", None,
                         "world-scope seven-day test, no item injection", 0,
                         {"hunger_seconds_per_point": 3600,
                          "activity_hunger_percent": 20})],
            bootstrap=True,
        )
        assert len(configured.npcs) == len(PEOPLE) == 7
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        engine = LivingWorldEngine(
            db, clock, max_events_per_advance=5000, decision_cooldown=3600,
            navigation_enabled=True, routines_enabled=True,
            survival_enabled=True, consumption_enabled=True,
            supply_enabled=True, economic_enabled=True,
            agriculture_enabled=True, economy_only_enabled=False,
        )
        days = []
        try:
            for day in range(DAYS):
                before_day = db.load(WORLD)
                for quarter in range(4):
                    prior = db.load(WORLD)
                    after = engine.advance(
                        WORLD, seconds=DAY // 4,
                        command_id=f"seven-days:{day}:{quarter}",
                        expected_revision=prior.revision,
                    ).state
                    assert after.time == (day * 4 + quarter + 1) * (DAY // 4)
                    audit_physical_supply(
                        after, seed=1, water=2, buyer_copper=2,
                        personal_food=INITIAL_PERSONAL_FOOD,
                    )
                saved = db.verify(WORLD)
                assert saved.to_dict() == db.load(WORLD).to_dict()
                audit = audit_food_security(saved)
                actions = sum(a["start"] >= before_day.time
                              for a in saved.actions.values())
                assert actions > 0
                days.append({
                    "day": day + 1,
                    "actions": actions,
                    "hunger_at_100": len(audit.hunger_at_cap),
                    "high_risk_npcs": len(audit.high_risk),
                    "meals": audit.consumed_meals,
                    "personal_food": audit.personal_food_units,
                    "known_site_food": audit.known_site_food_units,
                    "matured_crops": saved.farm_plots["farm"]["matured"],
                    "courier_deliveries": saved.supply_circuits["huda"]["deliveries"],
                })
            final = db.load(WORLD)
            assert final.time == DAYS * DAY
            assert len(final.npcs) == 7
            assert final.metabolism_policy == {
                "activity_hunger_percent": 20,
                "hunger_seconds_per_point": 3600,
            }
            assert len(days) == DAYS
            assert all(0 <= d["hunger_at_100"] <= 7 for d in days)
            assert all(d["personal_food"] >= 0 for d in days)
            db.snapshot(WORLD)
            assert db.verify(WORLD).to_dict() == final.to_dict()
            print("PLAY29_SEVEN_DAY_FINITE_FOOD_OBSERVATION", days)
        finally:
            clock.close_session(WORLD)
