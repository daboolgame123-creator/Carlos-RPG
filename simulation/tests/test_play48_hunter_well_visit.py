"""P10 hunter travels by personally learned roads, never by remote rescue magic."""
import pytest
from carlos_sim.domain import WorldState
from carlos_sim.hunter_well_visit import (
    hunter_seeks_well, choose_hunter_well_leg, hunter_waits_at_well,
)
from carlos_sim.local_emergency_aid import choose_local_emergency_courier_help
from test_play48_local_emergency_courier_aid import sample


def hunter_state(tmp_path):
    d = sample(tmp_path)
    d["time"] = 234 * 3600
    d["entities"]["omar"]["location_id"] = "hunting_woods"
    d["npcs"]["omar"]["needs"].update(hunger=30, fatigue=40, safety=0)
    d["resources"]["omar"]["food"] = 1
    d["resources"]["omar"]["coin_copper"] = 0
    assert d["npcs"]["omar"]["role"] == "hunter"
    assert d["npc_routines"]["omar"]["workplace_id"] == "hunting_woods"
    d["navigation"]["omar"] = {
        "known_routes": ["bakery-market", "market-watch-post", "market-woods"],
        "visited": ["hunting_woods", "market"], "target": None,
    }
    return d


def test_visits_only_surveyable_real_roads_without_remote_hunger(tmp_path):
    d = hunter_state(tmp_path)
    state = WorldState(**d)
    original = state.to_dict()
    assert hunter_seeks_well(state, "omar")
    assert choose_hunter_well_leg(state, "omar") == "market-woods"
    assert state.to_dict() == original
    for who in ("hana", "huda"):
        d["npcs"][who]["needs"]["hunger"] = 1
    assert choose_hunter_well_leg(WorldState(**d), "omar") == "market-woods"


def test_bounded_real_market_bakery_farm_well_progress(tmp_path):
    d = hunter_state(tmp_path)
    origin = d["time"]
    d["travels"]["p10-well-hunter:omar:" + str(origin)] = {
        "npc_id": "omar", "route_id": "market-woods",
        "origin": "hunting_woods", "destination": "market",
        "start": origin, "due": origin+240,
        "schedule_id": "npc-travel:p10-well-hunter:omar:" + str(origin),
        "status": "arrived", "arrived_at": origin+240,
    }
    d["time"] = origin + 300
    d["entities"]["omar"]["location_id"] = "market"
    assert choose_hunter_well_leg(WorldState(**d), "omar") == "bakery-market"
    d["time"] = origin + 400
    d["entities"]["omar"]["location_id"] = "bakery"
    d["navigation"]["omar"]["known_routes"].append("farm-bakery")
    d["navigation"]["omar"]["known_routes"].sort()
    d["navigation"]["omar"]["visited"].append("bakery")
    d["navigation"]["omar"]["visited"].sort()
    assert choose_hunter_well_leg(WorldState(**d), "omar") == "farm-bakery"
    d["time"] = origin + 500
    d["entities"]["omar"]["location_id"] = "farm"
    d["navigation"]["omar"]["known_routes"].append("well-farm")
    d["navigation"]["omar"]["known_routes"].sort()
    d["navigation"]["omar"]["visited"].append("farm")
    d["navigation"]["omar"]["visited"].sort()
    assert choose_hunter_well_leg(WorldState(**d), "omar") == "well-farm"
    d["time"] = origin + 1800
    assert choose_hunter_well_leg(WorldState(**d), "omar") is None


def test_hunter_owns_one_real_food_without_coin_and_helps_only_on_site(tmp_path):
    d = hunter_state(tmp_path)
    d["entities"]["layla"]["location_id"] = "riverbank"
    d["entities"]["omar"]["location_id"] = "well"
    d["npcs"]["hana"]["needs"]["hunger"] = 51
    assert choose_local_emergency_courier_help(WorldState(**d)) is None
    assert choose_local_emergency_courier_help(
        WorldState(**d), allow_hunter=True) == ("huda", "omar")
    d["entities"]["omar"]["location_id"] = "market"
    assert choose_local_emergency_courier_help(
        WorldState(**d), allow_hunter=True) is None


@pytest.mark.parametrize("key,value", [
    ("hunger", 36), ("fatigue", 70), ("safety", 75)
])
def test_ineligible_hunter_keeps_own_food(tmp_path, key, value):
    d = hunter_state(tmp_path)
    d["npcs"]["omar"]["needs"][key] = value
    assert not hunter_seeks_well(WorldState(**d), "omar")


def test_no_donation_of_committed_food_or_to_remote_recipient(tmp_path):
    d = hunter_state(tmp_path)
    d["entities"]["layla"]["location_id"] = "riverbank"
    d["entities"]["omar"]["location_id"] = "well"
    d["npcs"]["hana"]["needs"]["hunger"] = 51
    d["obligations"]["hunter-existing-debt"] = {
        "requester": "nora", "provider": "omar", "resource": "food",
        "quantity": 1, "location_id": "well", "created_at": d["time"],
        "status": "promised", "responded_at": d["time"],
        "resolved_at": None, "reason": None,
        "trust_before": None, "trust_after": None, "transfer": None,
    }
    assert choose_local_emergency_courier_help(
        WorldState(**d), allow_hunter=True) is None
    assert not hunter_waits_at_well(WorldState(**d), "omar")
