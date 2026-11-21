"""PLAY48: starvation search uses personal roads; no remote food oracle.

No changes to historically funded shopping unless community aid is opt-in.
"""
import pytest

from carlos_sim.domain import WorldState
from carlos_sim.market_navigation import (wants_local_market, choose_known_market_walk,
                                          choose_known_market_return)


def village(*, hunger=100, cash=0, visited_market=True, route=True, market_food=8):
    routes = {
        "road": {"a": "farm", "b": "market", "seconds": 120}
    } if route else {}
    return WorldState(
        world_id="cashless-road",
        time=72 * 3600,
        locations={"farm": {"name": "farm"}, "market": {"name": "market"}},
        entities={
            "nora": {"controller": "npc", "location_id": "farm"},
            "salma": {"controller": "npc", "location_id": "market"},
        },
        npcs={
            "nora": {"needs": {"hunger": hunger, "fatigue": 8, "safety": 0}},
            "salma": {"needs": {"hunger": 40, "fatigue": 8, "safety": 0}},
        },
        resources={
            "nora": {"food": 0, "coin_copper": cash},
            "market": {"food": market_food, "coin_copper": 4},
        },
        routes=routes,
        navigation={"nora": {
            "known_routes": ["road"] if route else [],
            "visited": ["farm", "market"] if visited_market else ["farm"],
            "target": None,
        }},
        market_stalls={"market": {"keeper_id": "salma"}},
        market_offers={"food-at-market": {
            "site_id": "market", "resource": "food",
            "posted_at": 30 * 3600,
        }} if visited_market else {},
        travels={"actual-market-visit": {
            "npc_id": "nora", "status": "arrived",
            "destination": "market", "arrived_at": 40 * 3600,
        }} if visited_market else {},
    )


def test_default_policy_never_sends_penniless_hungry_shopper():
    state = village(hunger=100, cash=0)
    assert not wants_local_market(state, "nora")
    assert choose_known_market_walk(state, "nora") is None
    assert wants_local_market(state, "nora", seek_relief=True)
    goal = choose_known_market_walk(state, "nora", seek_relief=True)
    assert goal is not None and goal.route_id == "road"
    assert goal.destination == "market"
    assert "personally" in goal.reason


def test_searches_unvisited_road_without_knowing_remote_shop_or_stock():
    a = village(visited_market=False, market_food=0)
    b = village(visited_market=False, market_food=30)
    # No remote inventory/offer insight: identical next physical step.
    walk_empty = choose_known_market_walk(a, "nora", seek_relief=True)
    walk_full = choose_known_market_walk(b, "nora", seek_relief=True)
    assert walk_empty == walk_full
    assert walk_empty is not None
    assert walk_empty.route_id == "road" and walk_empty.destination == "market"
    assert "searching known roads" in walk_empty.reason


def test_nonfood_shop_is_not_treated_as_a_personally_witnessed_food_stall():
    # The genuine 84h history had thousands of useless trips between ore,
    # smithy and charcoal shops; none had a food quote witnessed by the NPC.
    state = village(visited_market=False)
    raw = state.to_dict()
    raw["entities"]["nora"]["location_id"] = "smithy"
    raw["locations"]["smithy"] = {"name": "smithy"}
    raw["locations"]["charcoal_kiln"] = {"name": "charcoal"}
    raw["routes"] = {
        "coal-road": {"a": "smithy", "b": "charcoal_kiln", "seconds": 40}
    }
    raw["navigation"]["nora"] = {
        "known_routes": ["coal-road"],
        "visited": ["smithy", "charcoal_kiln"],
        "target": None,
    }
    raw["market_stalls"]["smithy"] = {"keeper_id": "nora"}
    raw["market_stalls"]["charcoal_kiln"] = {"keeper_id": "nora"}
    raw["market_offers"] = {"iron-sale": {
        "status": "open", "site_id": "smithy",
        "resource": "iron", "posted_at": 60 * 3600,
    }, "coal-sale": {
        "status": "open", "site_id": "charcoal_kiln",
        "resource": "coal", "posted_at": 60 * 3600,
    }}
    raw["travels"] = {"real-coal-visit": {
        "npc_id": "nora", "status": "arrived",
        "destination": "charcoal_kiln", "arrived_at": 65 * 3600,
    }}
    state = WorldState(**raw)
    assert wants_local_market(state, "nora", seek_relief=True,
                              seek_alternative_if_unaffordable=True)
    assert choose_known_market_walk(
        state, "nora", seek_relief=True,
        seek_alternative_if_unaffordable=True) is None


def test_last_witnessed_market_relief_arrival_has_full_day_cooldown():
    raw = village().to_dict()
    raw["travels"]["actual-market-visit"]["arrived_at"] = 70 * 3600
    assert choose_known_market_walk(
        WorldState(**raw), "nora", seek_relief=True) is None
    raw["travels"]["actual-market-visit"]["arrived_at"] = 40 * 3600
    assert choose_known_market_walk(
        WorldState(**raw), "nora", seek_relief=True) is not None
    # An offer posted after the last personal visit is REMOTE knowledge.
    raw["market_offers"]["food-at-market"]["posted_at"] = 71 * 3600
    assert choose_known_market_walk(
        WorldState(**raw), "nora", seek_relief=True) is None


def test_penniless_hungry_person_already_at_relief_market_does_not_wander():
    raw = village().to_dict()
    raw["entities"]["nora"]["location_id"] = "market"
    state = WorldState(**raw)
    assert not wants_local_market(state, "nora", seek_relief=True)
    assert choose_known_market_walk(state, "nora", seek_relief=True) is None


def test_no_teleport_when_the_npc_knows_no_road():
    state = village(route=False, visited_market=False)
    assert wants_local_market(state, "nora", seek_relief=True)
    assert choose_known_market_walk(state, "nora", seek_relief=True) is None


@pytest.mark.parametrize("hunger,cash,expected", [
    (94, 0, False), (95, 0, True), (100, 0, True),
    (70, 0, False), (70, 1, True),
])
def test_high_hunger_cashless_policy_is_bounded(hunger, cash, expected):
    state = village(hunger=hunger, cash=cash)
    assert wants_local_market(state, "nora", seek_relief=True) is expected


def test_existing_solvent_navigation_unchanged_with_opt_in():
    state = village(hunger=75, cash=2, visited_market=False)
    old = choose_known_market_walk(state, "nora")
    new = choose_known_market_walk(state, "nora", seek_relief=True)
    assert old == new


def test_strict_boolean_flag_validation():
    state = village()
    with pytest.raises(ValueError):
        wants_local_market(state, "nora", seek_relief=1)


def test_cashless_relief_does_not_assume_commercial_bakery_is_a_charity_site():
    state = village()
    raw = state.to_dict()
    raw["locations"]["bakery"] = {"name": "commercial bakery"}
    raw["routes"] = {"farm-bakery": {
        "a": "farm", "b": "bakery", "seconds": 40,
    }, "bakery-market": {
        "a": "bakery", "b": "market", "seconds": 50,
    }}
    raw["entities"]["nora"]["location_id"] = "bakery"
    raw["navigation"]["nora"]["known_routes"] = ["farm-bakery", "bakery-market"]
    raw["navigation"]["nora"]["visited"] = ["farm", "bakery", "market"]
    raw["market_stalls"]["bakery"] = {"keeper_id": "salma"}
    raw["market_offers"]["commercial-food-at-bakery"] = {
        "status": "open", "site_id": "bakery", "resource": "food",
        "posted_at": 65 * 3600, "unit_price": 2, "remaining": 2,
        "payment_resource": "coin_copper",
        "seller_id": "salma", "stock_owner_id": "bakery",
    }
    raw["market_offers"]["food-at-market"]["status"] = "open"
    raw["market_offers"]["food-at-market"]["unit_price"] = 2
    raw["market_offers"]["food-at-market"]["remaining"] = 2
    raw["travels"]["bakery-last-arrival"] = {
        "npc_id": "nora", "status": "arrived",
        "origin": "farm", "destination": "bakery",
        "start": 71 * 3600, "arrived_at": 71 * 3600 + 40,
    }
    raw["travels"]["actual-market-visit"]["origin"] = "bakery"
    raw["travels"]["actual-market-visit"]["start"] = 40 * 3600 - 50
    raw["npc_routines"] = {"nora": {
        "home_id": "farm", "workplace_id": "farm",
        "work_start": 0, "work_end": 12 * 3600,
    }}
    raw["production_jobs"] = {"paid-harvest": {
        "npc_id": "nora", "status": "completed",
        "work_wage": {"paid_at": 35 * 3600},
    }}
    here = WorldState(**raw)
    # Before the fix a starving farmer repeatedly went farm→bakery→farm,
    # losing the aid journey to the intermediate bakery return planner.
    wrong_turn = choose_known_market_return(here, "nora", repeat_errands=True)
    assert wrong_turn is not None and wrong_turn.destination == "farm"
    assert choose_known_market_return(
        here, "nora", repeat_errands=True, seek_relief=True) is None
    walk = choose_known_market_walk(
        here, "nora", seek_relief=True,
        repeat_errands=True,
        seek_alternative_if_unaffordable=True)
    assert walk is not None
    assert walk.destination == "market"
    assert walk.route_id == "bakery-market"
    assert "full day" in walk.reason

    # After a real market arrival less than one day ago, the person must
    # return to work, not immediately begin another pointless bread trip.
    raw["travels"]["actual-market-visit"]["arrived_at"] = 60 * 3600
    raw["travels"]["actual-market-visit"]["start"] = 60 * 3600 - 50
    recent = WorldState(**raw)
    homeward = choose_known_market_return(
        recent, "nora", repeat_errands=True, seek_relief=True)
    assert homeward is not None and homeward.destination == "farm"
    assert choose_known_market_walk(
        recent, "nora", seek_relief=True, repeat_errands=True,
        seek_alternative_if_unaffordable=True) is None


def test_one_day_revisit_does_not_read_distant_quote_or_remote_food():
    state = village(market_food=0)
    raw = state.to_dict()
    a = WorldState(**raw)
    raw["resources"]["market"]["food"] = 200
    b = WorldState(**raw)
    assert choose_known_market_walk(a, "nora", seek_relief=True) == (
        choose_known_market_walk(b, "nora", seek_relief=True))
