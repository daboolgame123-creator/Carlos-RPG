"""P6: a still-capable hungry baker may seek *signed* food work locally.

Only a voluntary known-road commute is proposed. No remote grain oracle,
transported stock, food wage, finished product, or currency is granted.
"""
import pytest

from carlos_sim.domain import WorldState
from carlos_sim.routines import (
    choose_routine_route, signed_hungry_baker_return_allowed,
)
from test_play48_real_watch_income_24h import seed


def baker_at_market(tmp_path):
    actual = seed(tmp_path / "genuine-genesis.sqlite")
    d = actual.to_dict()
    assert d["production_recipes"]["grain-to-bread"]["wage_food"] == 1
    d["entities"]["basim"]["location_id"] = "market"
    d["npcs"]["basim"]["needs"].update(hunger=82, fatigue=20, safety=0)
    nav = d["navigation"].setdefault(
        "basim", {"known_routes": [], "visited": [], "target": None})
    nav["target"] = None
    nav["known_routes"] = sorted(set(nav["known_routes"]) | {"bakery-market"})
    nav["visited"] = sorted(set(nav["visited"]) | {"bakery", "market"})
    return d


def proposal(d, enabled=True):
    return choose_routine_route(WorldState(**d), "basim",
                                hungry_paid_baker_return=enabled)


def test_only_opt_in_work_commute_not_food_or_cash_creation(tmp_path):
    d = baker_at_market(tmp_path)
    before = WorldState(**d).to_dict()
    assert proposal(d, False) is None
    intent = proposal(d)
    assert intent is not None and intent.destination == "bakery"
    assert intent.route_id == "bakery-market"
    assert signed_hungry_baker_return_allowed(WorldState(**d), "basim")
    assert WorldState(**d).to_dict() == before


@pytest.mark.parametrize("mutate", [
    lambda d: d["npcs"]["basim"]["needs"].update(hunger=90),
    lambda d: d["npcs"]["basim"]["needs"].update(fatigue=70),
    lambda d: d["npcs"]["basim"]["needs"].update(safety=75),
    lambda d: d["npcs"]["basim"].update(role="merchant"),
    lambda d: d["production_recipes"]["grain-to-bread"].pop("wage_food"),
    lambda d: d["navigation"]["basim"].update(known_routes=[]),
    lambda d: d["navigation"]["basim"].update(target="market"),
    lambda d: d["entities"]["basim"].update(location_id="bakery"),
])
def test_no_unsafe_unsigned_unknown_or_unnecessary_commute(tmp_path, mutate):
    d = baker_at_market(tmp_path)
    mutate(d)
    assert proposal(d) is None


def test_no_wage_on_a_nonwork_shift(tmp_path):
    d = baker_at_market(tmp_path)
    # The original bakery shift ends at t=30,000 seconds.
    d["time"] = 31_000
    assert proposal(d) is None


@pytest.mark.parametrize("wrong", [None, 0, 1, "yes", [], {}])
def test_flag_requires_strict_boolean(tmp_path, wrong):
    d = baker_at_market(tmp_path)
    with pytest.raises(ValueError, match="hungry paid baker return"):
        proposal(d, wrong)
