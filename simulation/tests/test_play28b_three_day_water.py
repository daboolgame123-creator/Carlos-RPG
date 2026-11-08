"""PLAY-28B: seven actual NPCs, 72 hours, one measured well refill.

This is a disposable, opt-in experiment on a fork. Both the new source and
all established crop, courier, and food conservation rules are checked.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scenarios" / "test_village"))

from carlos_sim import SQLiteEventStore, TimeEngine, LivingWorldEngine, DomainEvent
from carlos_sim.hydrology import FiniteWaterService
from play_physical_supply import (
    WORLD, DAY, PEOPLE, seed_physical_supply, audit_physical_supply,
)


def test_three_real_days_full_metabolism_one_explicit_rain_after_first_quarter(tmp_path):
    with SQLiteEventStore(tmp_path / "wet-72hours.sqlite") as db:
        seed_physical_supply(db, personal_food=18)
        initial = db.load(WORLD)
        configured = db.append(
            WORLD, "water-source-bootstrap", initial.revision,
            [DomainEvent("WaterSourceConfigured", None, "finite well at time zero", 0,
                         {"site_id": "well", "capacity": 3})],
            bootstrap=True,
        )
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        svc = FiniteWaterService(db, clock)
        engine = LivingWorldEngine(
            db, clock, max_events_per_advance=5000, decision_cooldown=3600,
            navigation_enabled=True, routines_enabled=True,
            survival_enabled=True, consumption_enabled=True,
            supply_enabled=True, economic_enabled=True,
            agriculture_enabled=True, economy_only_enabled=False,
        )
        assert len(configured.npcs) == len(PEOPLE) == 7
        assert configured.hydrology_sources["well"]["initial"] == 2
        assert configured.hydrology_sources["well"]["received_total"] == 0
        daily_actions = []
        try:
            for day in range(3):
                before_day = db.load(WORLD)
                for quarter in range(4):
                    before = db.load(WORLD)
                    actual = engine.advance(
                        WORLD, seconds=DAY // 4,
                        command_id=f"wet-real-day-{day}-quarter-{quarter}",
                        expected_revision=before.revision,
                    ).state
                    assert actual.time == (day * 4 + quarter + 1) * (DAY // 4)
                    # One external rain-gauge observation; it does NOT generate
                    # any future forecasts or automatically refill the well.
                    if day == 0 and quarter == 0:
                        assert actual.resources["well"]["water"] <= 2
                        actual = svc.record(
                            WORLD, "well", "rain-gauge-day-one", 1,
                            command_id="attested-rain-day-one",
                            expected_revision=actual.revision,
                        ).state
                        assert actual.resources["farm"]["water"] <= 1
                        assert actual.hydrology_sources["well"]["received_total"] == 1
                    audit_physical_supply(
                        actual, seed=1,
                        water=2 + actual.hydrology_sources["well"]["received_total"],
                        buyer_copper=2, personal_food=18,
                    )
                    assert db.verify(WORLD).to_dict() == actual.to_dict()
                after_day = db.load(WORLD)
                n = sum(a["start"] >= before_day.time
                        for a in after_day.actions.values())
                assert n > 0, "NPC everyday activity was disabled"
                daily_actions.append(n)
            final = db.load(WORLD)
            assert final.time == 259200
            assert final.hydrology_sources["well"]["received_total"] == 1
            assert final.hydrology_sources["well"]["observations"]["rain-gauge-day-one"] == {
                "units": 1, "at": 21600}
            assert len(final.npcs) == 7
            assert final.farm_plots["farm"]["matured"] >= 1
            assert sum(m["quantity"] for m in final.consumptions.values()) > 0
            assert final.supply_circuits["huda"]["deliveries"] > 0
            db.snapshot(WORLD)
            assert db.verify(WORLD).to_dict() == final.to_dict()
            print("PLAY28B_WET_3DAY", dict(
                seconds=final.time, actions=daily_actions,
                rain=final.hydrology_sources["well"]["received_total"],
                crop_matured=final.farm_plots["farm"]["matured"],
                meals=sum(m["quantity"] for m in final.consumptions.values()),
                deliveries=final.supply_circuits["huda"]["deliveries"],
                max_hunger=max(n["needs"]["hunger"] for n in final.npcs.values()),
            ))
        finally:
            clock.close_session(WORLD)
