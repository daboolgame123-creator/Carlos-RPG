"""P9: hunter's finite owned food may reach well through learned roads.

P8 fisher-only default is untouched. No magic Huda navigation: visited
frontiers must be *personally surveyed* in existing movement history.
"""
from __future__ import annotations
import pytest
from carlos_sim.domain import WorldState
from carlos_sim.voluntary_well_food import (
    hunter_can_seek_well, choose_hunter_well_visit, choose_local_well_request,
    choose_local_well_settlement, volunteer_waits_to_offer,
)
from carlos_sim import DomainEvent, SQLiteEventStore
from test_play38_multi_farm_couriers import seed_two_field_world, WORLD
from test_play47_closure_endurance import DAY
from test_play48_finite_hunt_fish_roads import _ecology_bootstrap


def hunter(tmp_path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    # Reuse the genuine finite-ecology genesis without the older standalone
    # test's obsolete rules_version==63 assertion: current world rules are 71.
    with SQLiteEventStore(tmp_path / "real-finite-hunter-genesis.sqlite") as db:
        seed_two_field_world(
            db, east_growth_seconds=DAY, east_grain_yield=12,
            initial_water=2, initial_market_food=3,
            market_wallets=True, hungry_market_buyers=True,
            cash_return=True, waged_harvest=True,
            harvest_wage_copper=2, bootstrap=_ecology_bootstrap,
        )
        original = db.load(WORLD)
        s = db.append(WORLD, "real-finite-ecology-initial-facts",
            original.revision, [
                DomainEvent("WaterSourceConfigured", None, "finite water", 0,
                            {"site_id": "well", "capacity": 8}),
                DomainEvent("MetabolismPolicyConfigured", None, "finite hunger", 0,
                            {"hunger_seconds_per_point": 3600,
                             "activity_hunger_percent": 20}),
            ], bootstrap=True)
        d = s.to_dict()
    assert "omar" in d["npcs"] and len(d["npcs"]) == 13
    d["time"] = 3600
    d["npcs"]["hana"]["needs"].update(hunger=55, fatigue=20, safety=0)
    d["npcs"]["huda"]["needs"].update(hunger=100, fatigue=20, safety=0)
    d["resources"]["hana"]["food"] = 0
    d["resources"]["huda"]["food"] = 0
    d["entities"]["hana"]["location_id"] = "well"
    d["entities"]["huda"]["location_id"] = "well"
    d["npcs"]["omar"]["needs"].update(hunger=30, fatigue=20, safety=0)
    d["resources"]["omar"]["food"] = 1
    d["entities"]["omar"]["location_id"] = "hunting_woods"
    d["navigation"]["omar"]["target"] = None
    d["navigation"]["omar"]["known_routes"] = [
        "bakery-market", "market-watch-post", "market-woods",
    ]
    d["navigation"]["omar"]["visited"] = ["hunting_woods", "market"]
    return d


def test_real_known_frontier_and_no_remote_resident_oracle(tmp_path):
    d = hunter(tmp_path)
    proposal = choose_hunter_well_visit(WorldState(**d), "omar")
    assert proposal and proposal.route_id == "market-woods"
    assert not choose_hunter_well_visit(WorldState(**d), "layla")
    d["entities"]["hana"]["location_id"] = "farm"
    d["entities"]["huda"]["location_id"] = "farm_east"
    assert choose_hunter_well_visit(WorldState(**d), "omar") == proposal


def test_first_woods_journey_then_study_real_bakery_farm_road_then_well(tmp_path):
    d = hunter(tmp_path)
    d["travels"]["well-neighbor:omar:3600"] = {
        "npc_id": "omar", "route_id": "market-woods",
        "origin": "hunting_woods", "destination": "market",
        "start": 3600, "due": 3840, "schedule_id": "npc-travel:well-neighbor:omar:3600",
        "status": "arrived", "arrived_at": 3840,
    }
    d["time"] = 4000
    d["entities"]["omar"]["location_id"] = "market"
    assert choose_hunter_well_visit(WorldState(**d), "omar").route_id == "bakery-market"
    # Personally reached bakery, surveyed adjacent roads (existing Surveyed reducer).
    d["time"] = 4070
    d["entities"]["omar"]["location_id"] = "bakery"
    nav = d["navigation"]["omar"]
    nav["visited"].append("bakery")
    nav["known_routes"] += ["bakery-smithy", "farm-bakery", "east-bakery"]
    assert choose_hunter_well_visit(WorldState(**d), "omar").route_id == "farm-bakery"
    d["time"] = 4140
    d["entities"]["omar"]["location_id"] = "farm"
    nav["visited"].append("farm")
    nav["known_routes"].append("well-farm")
    assert choose_hunter_well_visit(WorldState(**d), "omar").route_id == "well-farm"
    # Thirty-minute cap forbids aimless continued wandering.
    d["time"] = 5400
    assert not hunter_can_seek_well(WorldState(**d), "omar")


@pytest.mark.parametrize("mutate", [
    lambda d: d["resources"]["omar"].update(food=0),
    lambda d: d["npcs"]["omar"]["needs"].update(hunger=75),
    lambda d: d["npcs"]["omar"]["needs"].update(fatigue=70),
    lambda d: d["npcs"]["omar"]["needs"].update(safety=75),
    lambda d: d["navigation"]["omar"].update(target="market"),
    lambda d: d["npcs"]["omar"].update(role="merchant"),
    lambda d: d["navigation"]["omar"].update(known_routes=[]),
])
def test_no_unsafe_unfed_unknown_or_changed_role_hunter_well_journey(tmp_path, mutate):
    d = hunter(tmp_path)
    mutate(d)
    assert choose_hunter_well_visit(WorldState(**d), "omar") is None


def test_huda_can_request_hunters_own_food_only_with_explicit_optin(tmp_path):
    d = hunter(tmp_path)
    d["entities"]["omar"]["location_id"] = "well"
    d["npcs"]["hana"]["needs"]["hunger"] = 55
    assert choose_local_well_request(WorldState(**d)) is None
    help = choose_local_well_request(WorldState(**d), allow_hunter=True)
    assert help is not None and help.donor == "omar" and help.recipient == "huda"
    assert not choose_local_well_settlement(WorldState(**d), allow_hunter=True)
    assert not volunteer_waits_to_offer(WorldState(**d), "omar")
    # The hunter must be voluntarily and physically present. No donation
    # is recorded by choosing the proposal alone.
    assert WorldState(**d).resources["omar"]["food"] == 1
    assert WorldState(**d).resources["huda"]["food"] == 0
