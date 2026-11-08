"""PLAY-39 — physically accounted rain/drought, two full-day fields, 9 NPCs.

This is a controlled causal experiment.  Every extra unit of water is backed
by an authorized, immutable rain receipt at a specific logical time; no
weather simulation, scripted NPC sale, or guaranteed survival.
"""
from __future__ import annotations

import json

import pytest

from carlos_sim import DomainEvent, InvalidEvent, LivingWorldEngine, SQLiteEventStore, TimeEngine
from carlos_sim.hydrology import FiniteWaterService
from test_play38_multi_farm_couriers import EAST, COURIER, WORLD, seed_two_field_world

DAY = 86400
PEOPLE = 9
START_FOOD = 3
START_WATER = 2
CROP_YIELD = {"farm": 3, EAST: 7}
CLOCKS = (0, 3600, DAY, DAY + 3600, 2 * DAY, 3 * DAY)


def _bound_ledger(state, *, rain_units):
    """Check all actual physical resources plus transforms and water receipts."""
    stock = state.resources
    assert len(state.npcs) == PEOPLE
    assert len(state.farm_plots) == len(state.supply_circuits) == 2
    assert state.hydrology_sources["well"]["received_total"] == rain_units
    observations = state.hydrology_sources["well"]["observations"]
    assert sum(row["units"] for row in observations.values()) == rain_units
    assert len(observations) == rain_units // 2
    remaining_water = sum(stock[who]["water"] for who in (
        "well", "farm", EAST, "huda", COURIER
    ))
    # Each started growth cycle consumes one unit, permanently. Even if the
    # crop is still growing, seed and water must remain in the local ledger.
    used_water = sum(plot["started"] for plot in state.farm_plots.values())
    assert remaining_water + used_water == START_WATER + rain_units

    for field in CROP_YIELD:
        plot = state.farm_plots[field]
        planting = sum(
            job["status"] == "running"
            and state.production_recipes[job["recipe_id"]]["site_id"] == field
            and state.production_recipes[job["recipe_id"]]["input_resource"] == "seed"
            for job in state.production_jobs.values()
        )
        assert (stock[field]["seed"] + stock[field]["crop_seeded"]
                + planting + int(plot["status"] == "growing")) == 1

    actual_food = sum(bal.get("food", 0) for bal in stock.values())
    actual_grain = sum(bal.get("grain", 0) for bal in stock.values())
    consumed = sum(meal["quantity"] for meal in state.consumptions.values())
    pending_bakes = sum(
        state.production_recipes[job["recipe_id"]]["input_amount"]
        for job in state.production_jobs.values()
        if job["status"] == "running"
        and state.production_recipes[job["recipe_id"]]["output_resource"] == "food"
    )
    reserved_harvest_grain = sum(
        CROP_YIELD[job["site_id"]]
        for job in state.production_jobs.values()
        if job["status"] == "running"
        and state.production_recipes[job["recipe_id"]]["input_resource"] == "crop_ready"
    )
    physically_ripe = sum(
        stock[field]["crop_ready"] * CROP_YIELD[field]
        for field in CROP_YIELD
    )
    output_earned = sum(
        plot["matured"] * CROP_YIELD[field]
        for field, plot in state.farm_plots.items()
    )
    # During baking, grain becomes reserved input until the scheduled baked
    # food exists. These counts never treat offers as extra physical food.
    assert (actual_food + actual_grain + consumed + pending_bakes
            + reserved_harvest_grain + physically_ripe
            == START_FOOD + output_earned)
    assert sum(bal.get("coin_copper", 0) for bal in stock.values()) == 12
    assert all(value >= 0 for bal in stock.values()
               for value in bal.values() if type(value) is int)
    return {
        "time": state.time,
        "rain_units": rain_units,
        "stored_water": remaining_water,
        "water_used_for_growth": used_water,
        "matured": {f: state.farm_plots[f]["matured"] for f in CROP_YIELD},
        "ripe_food_equivalent": physically_ripe,
        "grain": actual_grain,
        "baked": sum(
            job["status"] == "completed"
            and state.production_recipes[job["recipe_id"]]["output_resource"] == "food"
            for job in state.production_jobs.values()
        ),
        "owned_food": actual_food,
        "eaten": consumed,
        "market_sales": len(state.market_trades),
        "courier_deliveries": {
            c: state.supply_circuits[c]["deliveries"] for c in ("huda", COURIER)
        },
        "full_npc_rests": sum(
            a["status"] == "completed" and a["action"] == "rest"
            for a in state.actions.values()
        ),
        "npc_hunger_cap": sum(
            p["needs"]["hunger"] == 100 for p in state.npcs.values()
        ),
        "unsafe_workers": tuple(sorted(
            who for who in ("basim", "nora", "huda", "farid", COURIER)
            if state.npcs[who]["needs"]["hunger"] >= 90
        )),
    }


def _run(path, *, measured_rain):
    with SQLiteEventStore(path) as db:
        seed_two_field_world(
            db, east_growth_seconds=DAY, east_grain_yield=7,
            initial_water=START_WATER,
            initial_market_food=START_FOOD,
            market_wallets=True,
            hungry_market_buyers=True,
        )
        previous = db.load(WORLD)
        db.append(
            WORLD, "play39-trusted-world-policy", previous.revision,
            [
                DomainEvent(
                    "WaterSourceConfigured", None, "finite measured source", 0,
                    {"site_id": "well", "capacity": 8},
                ),
                DomainEvent(
                    "MetabolismPolicyConfigured", None,
                    "time-zero controlled world policy", 0,
                    {"hunger_seconds_per_point": 3600,
                     "activity_hunger_percent": 20},
                ),
            ], bootstrap=True,
        )
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            hydrology = FiniteWaterService(db, clock)
            engine = LivingWorldEngine(
                db, clock, max_events_per_advance=5000,
                decision_cooldown=3600, navigation_enabled=True,
                routines_enabled=True, survival_enabled=True,
                consumption_enabled=True, supply_enabled=True,
                economic_enabled=True, adaptive_market_enabled=True,
                agriculture_enabled=True, economy_only_enabled=False,
            )
            observations = [_bound_ledger(db.verify(WORLD), rain_units=0)]
            assert len(db.load(WORLD).npcs) == PEOPLE
            for target in CLOCKS[1:]:
                while db.load(WORLD).time < target:
                    old = db.load(WORLD)
                    step = min(6 * 3600, target - old.time)
                    advanced = engine.advance(
                        WORLD, seconds=step,
                        command_id=f"play39:{measured_rain}:{target}:{old.time}",
                        expected_revision=old.revision,
                    ).state
                    assert advanced.time == old.time + step
                    _bound_ledger(
                        advanced,
                        rain_units=advanced.hydrology_sources["well"]["received_total"],
                    )
                if measured_rain and target in (DAY, 2 * DAY):
                    pre = db.load(WORLD)
                    observed = hydrology.record(
                        WORLD, "well", f"rain-gauge-at-{target}", 2,
                        command_id=f"play39-rain:{target}",
                        expected_revision=pre.revision,
                    )
                    assert observed.state.time == target
                checkpoint = db.load(WORLD)
                observed_water = checkpoint.hydrology_sources["well"]["received_total"]
                observations.append(
                    _bound_ledger(checkpoint, rain_units=observed_water)
                )
                assert db.verify(WORLD).to_dict() == checkpoint.to_dict()
                db.snapshot(WORLD)
                assert db.verify(WORLD).to_dict() == checkpoint.to_dict()
            return observations, db.load(WORLD).to_dict()
        finally:
            clock.close_session(WORLD)


def test_real_day_two_fields_with_receipted_rain_vs_drought(tmp_path):
    dry, dry_world = _run(tmp_path / "dry.sqlite", measured_rain=False)
    wet, wet_world = _run(tmp_path / "wet.sqlite", measured_rain=True)
    assert [x["time"] for x in dry] == list(CLOCKS)
    assert [x["time"] for x in wet] == list(CLOCKS)
    assert dry[0] == wet[0]
    assert dry[-1]["rain_units"] == 0
    assert wet[-1]["rain_units"] == 4
    assert all(x["rain_units"] == 0 for x in dry)
    assert all(x["rain_units"] in (0, 2, 4) for x in wet)
    assert len(dry_world["npcs"]) == len(wet_world["npcs"]) == PEOPLE
    for series in (dry, wet):
        assert all(row["npc_hunger_cap"] <= PEOPLE for row in series)
        assert all(row["owned_food"] >= 0 and row["grain"] >= 0 for row in series)
        assert all(row["eaten"] <= START_FOOD
                   + row["matured"]["farm"] * 3 + row["matured"][EAST] * 7
                   for row in series)
    print("PLAY39_TWO_FARM_REAL_DAY_RAIN_DROUGHT",
          json.dumps({"drought": dry, "measured_rain": wet}, sort_keys=True))


def test_rain_source_rejects_forged_or_duplicate_receipt_and_replays(tmp_path):
    with SQLiteEventStore(tmp_path / "source.sqlite") as db:
        seed_two_field_world(db)
        current = db.load(WORLD)
        db.append(
            WORLD, "physical-water-source", current.revision,
            [DomainEvent("WaterSourceConfigured", None, "finite site", 0,
                         {"site_id": "well", "capacity": 8})],
            bootstrap=True,
        )
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            # Without an active explicit authority, a world command can
            # never declare weather by impersonating the observation system.
            old = db.load(WORLD)
            with pytest.raises(InvalidEvent) as failure:
                db.append(
                    WORLD, "rain-forgery", old.revision,
                    [DomainEvent("RainWaterRecorded", None, "forged", 0,
                                 {"source_id": "well",
                                  "observation_id": "forged", "units": 2})],
                )
            assert failure.value
            assert db.verify(WORLD).to_dict() == old.to_dict()
            water = FiniteWaterService(db, clock)
            first = water.record(
                WORLD, "well", "gauge-0", 2,
                command_id="real-attested-rain",
                expected_revision=old.revision,
            ).state
            with pytest.raises(InvalidEvent):
                water.record(
                    WORLD, "well", "gauge-0", 2,
                    command_id="replay-same-rain-with-different-command",
                    expected_revision=first.revision,
                )
            assert db.verify(WORLD).to_dict() == first.to_dict()
        finally:
            clock.close_session(WORLD)
