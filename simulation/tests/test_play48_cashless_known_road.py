"""PLAY48: starvation search uses personal roads; no remote food oracle.

No changes to historically funded shopping unless community aid is opt-in.
"""
import pytest

from carlos_sim.domain import WorldState
from carlos_sim.market_navigation import wants_local_market, choose_known_market_walk


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
