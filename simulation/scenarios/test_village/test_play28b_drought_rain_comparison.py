"""PLAY-28B A/B experiment: same seven-NPC village, drought vs one real rain.

Both worlds have the same finite seed, copper, roads, tools, personal meals
and initial one-unit well. Rain is the ONLY differing external input. Fully
active NPC metabolism/routines/production/logistics remain enabled.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from carlos_sim import SQLiteEventStore, DomainEvent, TimeEngine, LivingWorldEngine
from carlos_sim.hydrology import FiniteWaterService
from play_physical_supply import (
    WORLD, DAY, PEOPLE, seed_physical_supply, audit_physical_supply,
)


def simulate(path, *, measured_rain: bool):
    with SQLiteEventStore(path) as db:
        seed_physical_supply(db, water=1, personal_food=18)
        before = db.load(WORLD)
        configured = db.append(
            WORLD, "finite-source-config", before.revision,
            [DomainEvent("WaterSourceConfigured", None,
                         "same finite baseline for both worlds", 0,
                         {"site_id": "well", "capacity": 2})],
            bootstrap=True,
        )
        assert len(configured.npcs) == len(PEOPLE) == 7
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        rain = FiniteWaterService(db, clock)
        engine = LivingWorldEngine(
            db, clock, decision_cooldown=3600, max_events_per_advance=5000,
            navigation_enabled=True, routines_enabled=True,
            survival_enabled=True, consumption_enabled=True,
            supply_enabled=True, economic_enabled=True,
            agriculture_enabled=True, economy_only_enabled=False,
        )
        daily = []
        try:
            for day in range(3):
                start = db.load(WORLD)
                for quarter in range(4):
                    before = db.load(WORLD)
                    after = engine.advance(
                        WORLD, seconds=DAY // 4,
                        command_id=f"ab-3days-{day}-{quarter}",
                        expected_revision=before.revision,
                    ).state
                    assert after.time == (4 * day + quarter + 1) * (DAY // 4)
                    if day == 0 and quarter == 0 and measured_rain:
                        after = rain.record(
                            WORLD, "well", "measured-day1", 1,
                            command_id="measured-external-rain",
                            expected_revision=after.revision,
                        ).state
                    water_budget = 1 + after.hydrology_sources["well"]["received_total"]
                    audit_physical_supply(
                        after, seed=1, water=water_budget,
                        buyer_copper=2, personal_food=18,
                    )
                end = db.load(WORLD)
                daily_actions = sum(a["start"] >= start.time
                                    for a in end.actions.values())
                assert daily_actions > 0
                daily.append(daily_actions)
            final = db.load(WORLD)
            db.snapshot(WORLD)
            assert db.verify(WORLD).to_dict() == final.to_dict()
            src = final.hydrology_sources["well"]
            assert src["initial"] == 1
            assert src["received_total"] == int(measured_rain)
            assert len(src["observations"]) == int(measured_rain)
            return dict(
                rainy=measured_rain, days=final.time // DAY,
                daily_actions=daily, water_origin=src["initial"],
                rain_received=src["received_total"],
                crop_matured=final.farm_plots["farm"]["matured"],
                crop_in_progress=int(final.farm_plots["farm"]["status"] == "growing"),
                meals=sum(m["quantity"] for m in final.consumptions.values()),
                deliveries=final.supply_circuits["huda"]["deliveries"],
                well_remaining=final.resources["well"]["water"],
                farm_remaining=final.resources["farm"]["water"],
                courier_cargo=final.resources["huda"]["water"],
                max_hunger=max(n["needs"]["hunger"] for n in final.npcs.values()),
            )
        finally:
            clock.close_session(WORLD)


def test_counterfactual_three_days_only_rainfall_input_differs(tmp_path):
    dry = simulate(tmp_path / "drought.sqlite", measured_rain=False)
    wet = simulate(tmp_path / "rain.sqlite", measured_rain=True)
    assert dry["days"] == wet["days"] == 3
    assert dry["water_origin"] == wet["water_origin"] == 1
    assert dry["rain_received"] == 0
    assert wet["rain_received"] == 1
    assert all(x > 0 for x in dry["daily_actions"] + wet["daily_actions"])
    assert dry["crop_matured"] >= 0 and wet["crop_matured"] >= 0
    assert dry["max_hunger"] <= 100 and wet["max_hunger"] <= 100
    print("PLAY28B_DROUGHT_VS_RAIN", {"drought": dry, "rain": wet})
