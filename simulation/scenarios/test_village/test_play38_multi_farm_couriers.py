"""PLAY-38: second real field + second independent courier over real roads.

An independently loaded real world gets a second farm with a real plot,
harvesting tools, an employed NPC and a distinct courier. The original
well-farm-bakery-market route, stock balances and code remain valid.
"""
from __future__ import annotations

import pytest

from carlos_sim import DomainEvent, InvalidEvent, LivingWorldEngine, SQLiteEventStore, TimeEngine
from play_physical_supply import WORLD, seed_physical_supply

EAST = "farm_east"
COURIER = "hana"
FARMER = "farid"
STOPS = ["well", EAST, "bakery", "market", "bakery", EAST, "well"]
ROUTES = ["well-east", "east-bakery", "bakery-market",
          "bakery-market", "east-bakery", "well-east"]


def _event(kind, data):
    return DomainEvent(kind, None, "trusted second-field bootstrap only", 0, data)


def seed_two_field_world(db, *, unsafe_stops=None, unsafe_route=None):
    seed_physical_supply(
        db, water=2, seed=1, initial_market_food=0,
        harvest_yield=3, personal_food=0,
    )
    extra = [
        _event("LocationCreated", {"id": EAST, "name": "East field"}),
        _event("RouteCreated", {
            "id": "well-east", "a": "well", "b": EAST, "seconds": 50,
        }),
        _event("RouteCreated", {
            "id": "east-bakery", "a": EAST, "b": "bakery", "seconds": 60,
        }),
        _event("EntityCreated", {
            "id": FARMER, "name": "Farid",
            "location_id": EAST, "controller": "npc",
        }),
        _event("EntityCreated", {
            "id": COURIER, "name": "Hana",
            "location_id": "well", "controller": "npc",
        }),
    ]
    for who, role, hunger, fatigue in (
        (FARMER, "farmer", 20, 5),
        (COURIER, "courier", 20, 5),
    ):
        extra.append(_event("NPCConfigured", {
            "npc_id": who, "role": role,
            "needs": {"hunger": hunger, "fatigue": fatigue, "safety": 0},
            "goals": {"earn": 10, "explore": 10, "survive": 30},
        }))
        for resource in ("labor_units", "investigation_attempts", "food"):
            extra.append(_event("ResourceChanged", {
                "owner_id": who, "resource": resource,
                "previous": None, "current": 0,
                "source": "initialization",
            }))
    for owner, resource, value in (
        (EAST, "water", 0), (EAST, "seed", 1), (EAST, "crop_seeded", 0),
        (EAST, "crop_ready", 0), (EAST, "grain", 0),
        (EAST, "hoe", 1), (EAST, "sickle", 1),
        (COURIER, "water", 0), (COURIER, "grain", 0),
    ):
        extra.append(_event("ResourceChanged", {
            "owner_id": owner, "resource": resource,
            "previous": None, "current": value,
            "source": "initialization",
        }))
    extra.extend([
        _event("NPCRoutineConfigured", {
            "npc_id": FARMER, "home_id": "home",
            "workplace_id": EAST, "work_start": 0, "work_end": 30000,
        }),
        _event("ProductionRecipeConfigured", {
            "id": "east-seed-planting", "site_id": EAST, "role": "farmer",
            "input_resource": "seed", "input_amount": 1,
            "output_resource": "crop_seeded", "output_amount": 1,
            "tool_resource": "hoe", "duration_seconds": 60,
        }),
        _event("ProductionRecipeConfigured", {
            "id": "east-finite-harvest", "site_id": EAST, "role": "farmer",
            "input_resource": "crop_ready", "input_amount": 1,
            "output_resource": "grain", "output_amount": 3,
            "tool_resource": "sickle", "duration_seconds": 60,
        }),
        _event("FarmPlotConfigured", {
            "site_id": EAST, "growth_seconds": 3600, "capacity": 1,
        }),
        _event("SupplyCircuitConfigured", {
            "courier_id": COURIER,
            "stops": STOPS if unsafe_stops is None else unsafe_stops,
            "route_ids": ROUTES if unsafe_route is None else unsafe_route,
            "period_seconds": 1800,
        }),
    ])
    db.append(WORLD, "play38-second-field", db.load(WORLD).revision,
              extra, bootstrap=True)


def _conserve(state):
    resource = state.resources
    plots = state.farm_plots
    couriers = state.supply_circuits
    assert len(plots) == 2
    assert len(couriers) == 2
    assert state.resources["well"]["water"] + sum(
        state.resources[owner]["water"]
        for owner in ("farm", EAST, "huda", COURIER)
    ) + sum(p["matured"] + (p["status"] == "growing")
            for p in plots.values()) == 2
    for field in ("farm", EAST):
        p = plots[field]
        planting = sum(
            j["status"] == "running"
            and state.production_recipes[j["recipe_id"]]["site_id"] == field
            and state.production_recipes[j["recipe_id"]]["input_resource"] == "seed"
            for j in state.production_jobs.values()
        )
        assert (resource[field]["seed"] + resource[field]["crop_seeded"]
                + planting + (p["status"] == "growing")) == 1
    assert all(amount >= 0 for bal in resource.values()
               for amount in bal.values() if type(amount) is int)
    assert sum(bal.get("coin_copper", 0) for bal in resource.values()) == 12
    # Seed/water remain conserved across *both* independent field plots.
    # Finished production converts exactly 1 crop_ready -> 3 grain.
    harvests = sum(
        j["status"] == "completed"
        and state.production_recipes[j["recipe_id"]]["output_resource"] == "grain"
        for j in state.production_jobs.values())
    grain = sum(bal.get("grain", 0) for bal in resource.values())
    food = sum(bal.get("food", 0) for bal in resource.values())
    consumed = sum(m["quantity"] for m in state.consumptions.values())
    maturing = sum(resource[field]["crop_ready"] for field in ("farm", EAST))
    pending = sum(
        j["status"] == "running"
        and state.production_recipes[j["recipe_id"]]["input_resource"] == "crop_ready"
        for j in state.production_jobs.values()
    )
    assert grain + food + consumed + (maturing + pending) * 3 == (
        3 * sum(p["matured"] for p in plots.values()))


def test_two_real_farms_and_independent_couriers_complete_physical_supply(
        tmp_path):
    with SQLiteEventStore(tmp_path / "two-farms.sqlite") as db:
        seed_two_field_world(db)
        state = db.verify(WORLD)
        assert len(state.npcs) == 9
        assert set(state.farm_plots) == {"farm", EAST}
        assert tuple(state.supply_circuits["huda"]["stops"][1:2]) == ("farm",)
        assert tuple(state.supply_circuits[COURIER]["stops"][1:2]) == (EAST,)
        _conserve(state)
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            engine = LivingWorldEngine(
                db, clock, max_events_per_advance=5000,
                decision_cooldown=3600, navigation_enabled=True,
                routines_enabled=True, survival_enabled=True,
                consumption_enabled=True, supply_enabled=True,
                economic_enabled=True, agriculture_enabled=True,
                economy_only_enabled=True,
            )
            snapshots = []
            for target in (120, 400, 1800, 3900, 5700, 8500):
                before = db.load(WORLD)
                state = engine.advance(
                    WORLD, seconds=target - before.time,
                    command_id=f"play38:advance:{target}",
                    expected_revision=before.revision,
                ).state
                _conserve(state)
                assert db.verify(WORLD).to_dict() == state.to_dict()
                db.snapshot(WORLD)
                assert db.verify(WORLD).to_dict() == state.to_dict()
                snapshots.append({
                    "t": state.time,
                    "east_mature": state.farm_plots[EAST]["matured"],
                    "east_harvests": sum(
                        j["status"] == "completed"
                        and j["recipe_id"] == "east-finite-harvest"
                        for j in state.production_jobs.values()
                    ),
                    "east_deliveries": state.supply_circuits[COURIER]["deliveries"],
                    "original_deliveries": state.supply_circuits["huda"]["deliveries"],
                    "bakery_grain": state.resources["bakery"]["grain"],
                    "bakery_food": state.resources["bakery"]["food"],
                    "market_food": state.resources["market"]["food"],
                })
            assert snapshots[0]["east_deliveries"] >= 1
            assert snapshots[-1]["east_mature"] >= 1
            assert snapshots[-1]["east_harvests"] >= 1
            assert snapshots[-1]["east_deliveries"] >= 2
            assert snapshots[-1]["original_deliveries"] >= 1
            print("PLAY38_PHYSICAL_MULTI_FARM", snapshots)
        finally:
            clock.close_session(WORLD)


@pytest.mark.parametrize("bad_stops", [
    ["well", "bakery", "bakery", "market", "bakery", "bakery", "well"],
    ["well", "farm_east", "bakery", "market", "farm", "farm_east", "well"],
    ["well", "farm_east", "bakery", "market", "bakery", "farm_east", "market"],
    ["well", "farm_east", "bakery", "market", "bakery", "farm_east"],
])
def test_courier_rejects_nonphysical_route_shape_without_committing(
        tmp_path, bad_stops):
    with SQLiteEventStore(tmp_path / "invalid.sqlite") as db:
        with pytest.raises((ValueError, InvalidEvent)):
            seed_two_field_world(db, unsafe_stops=bad_stops)
        state = db.verify(WORLD)
        assert EAST not in state.locations
        assert COURIER not in state.supply_circuits
        assert len(state.supply_circuits) == 1


def test_courier_rejects_route_to_wrong_field_without_committing(tmp_path):
    wrong = ROUTES.copy()
    wrong[0] = "well-farm"
    with SQLiteEventStore(tmp_path / "wrong-road.sqlite") as db:
        with pytest.raises((ValueError, InvalidEvent)):
            seed_two_field_world(db, unsafe_route=wrong)
        state = db.verify(WORLD)
        assert EAST not in state.locations
        assert COURIER not in state.supply_circuits
