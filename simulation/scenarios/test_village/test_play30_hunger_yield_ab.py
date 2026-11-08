"""PLAY-30: observe real three-day hunger when only physical crop yield differs.

A PASS means that the simulation is causally/replay safe, NOT that seven NPCs
remain fed. These worlds have no automatic rain and only two finite waters.
"""
from __future__ import annotations

from carlos_sim import SQLiteEventStore, TimeEngine, LivingWorldEngine, DomainEvent
from carlos_sim.food_security_audit import audit_food_security
from play_physical_supply import WORLD, DAY, PEOPLE, seed_physical_supply, audit_physical_supply

DAYS = 3
PERSONAL_PROVISIONS = 6


def run_three_day_village(path, harvest_yield, *,
                          personal_provisions=PERSONAL_PROVISIONS,
                          market_wallets=False):
    with SQLiteEventStore(path) as db:
        seed_physical_supply(db, personal_food=personal_provisions,
                             harvest_yield=harvest_yield,
                             market_wallets=market_wallets)
        first = db.load(WORLD)
        configured = db.append(
            WORLD, "play30-frozen-survival-configuration", first.revision,
            [DomainEvent("MetabolismPolicyConfigured", None,
                         "trusted three-day comparison; no extra provisions", 0,
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
        timeline = []
        try:
            for day in range(DAYS):
                start = db.load(WORLD)
                for quarter in range(4):
                    before = db.load(WORLD)
                    state = engine.advance(
                        WORLD, seconds=DAY // 4,
                        command_id=f"yield-{harvest_yield}:{day}:{quarter}",
                        expected_revision=before.revision,
                    ).state
                    assert state.time == (4 * day + quarter + 1) * (DAY // 4)
                    conserved = audit_physical_supply(
                        state, seed=1, water=2, buyer_copper=2,
                        personal_food=personal_provisions,
                    )
                    assert conserved["harvest_yield"] == harvest_yield
                state = db.verify(WORLD)
                audit = audit_food_security(state)
                actions = sum(a["start"] >= start.time
                              for a in state.actions.values())
                assert actions > 0
                timeline.append({
                    "day": day + 1,
                    "completed_actions": actions,
                    "hunger_at_100": len(audit.hunger_at_cap),
                    "high_risk": len(audit.high_risk),
                    "personal_food": audit.personal_food_units,
                    "known_site_food": audit.known_site_food_units,
                    "meals": audit.consumed_meals,
                    "matured_crops": state.farm_plots["farm"]["matured"],
                    "baked": sum(job["status"] == "completed"
                                 and job["recipe_id"] == "grain-to-bread"
                                 for job in state.production_jobs.values()),
                    "deliveries": state.supply_circuits["huda"]["deliveries"],
                    "trades": len(state.market_trades),
                    "market_stock": state.resources["market"]["food"],
                })
            last = db.load(WORLD)
            assert last.time == DAYS * DAY
            assert last.metabolism_policy == {
                "hunger_seconds_per_point": 3600,
                "activity_hunger_percent": 20,
            }
            assert db.verify(WORLD).to_dict() == last.to_dict()
            db.snapshot(WORLD)
            assert db.verify(WORLD).to_dict() == last.to_dict()
            return {"yield": harvest_yield, "timeline": timeline,
                    "hunger": {ident: last.npcs[ident]["needs"]["hunger"]
                               for ident, *_ in PEOPLE},
                    "matured": last.farm_plots["farm"]["matured"],
                    "deliveries": last.supply_circuits["huda"]["deliveries"],
                    "wallets": {who: last.resources[who].get("coin_copper")
                                for who in ("carlos", "adel", "omar", "layla")},
                    "total_coins": sum(x["coin_copper"] for x in last.resources.values()
                                       if "coin_copper" in x)}
        finally:
            clock.close_session(WORLD)


def test_real_activity_hunger_three_day_physical_yield_ab(tmp_path):
    original = run_three_day_village(tmp_path / "one-grain.sqlite", 1)
    improved = run_three_day_village(tmp_path / "three-grain.sqlite", 3)
    assert len(original["timeline"]) == len(improved["timeline"]) == DAYS
    assert original["matured"] == improved["matured"] == 2
    for case in (original, improved):
        assert all(0 <= entry["hunger_at_100"] <= 7
                   and 0 <= entry["high_risk"] <= 7
                   and entry["completed_actions"] > 0
                   for entry in case["timeline"])
    # Capture actual nourishment separately from *potential* harvest volume.
    # No assertion that larger yields prevent starvation: market access,
    # courier throughput, personal cash, and retained bakery stock all matter.
    print("PLAY30_REAL_72H_YIELD_HUNGER_AB", {
        "one_grain": original,
        "three_grain": improved,
    })
