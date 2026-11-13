"""PLAY48: focused physical porter contract, stock and firsthand road tests.

These are intentionally cheap (genesis + pure selectors); do NOT by themselves
claim a completed real merchant sale or long-term 13NPC economic recovery.
"""
from __future__ import annotations

from carlos_sim import DomainEvent, SQLiteEventStore
from carlos_sim.domain import WorldState
from carlos_sim.economic_autonomy import choose_local_food_offer
from carlos_sim.food_peddler import (
    TRADER, choose_purchase, choose_offer, choose_withdrawal, choose_walk,
)
from test_play38_multi_farm_couriers import seed_two_field_world, WORLD
from test_play47_joined_professions import _joined_bootstrap
from test_play47_closure_endurance import DAY
from carlos_sim.economic_diagnostics import audit_npc_economy

HOUR = 3600


def _peddler_bootstrap(db, *, initial_market_food, **options):
    assert initial_market_food == 3
    assert options == {
        "water": 2, "seed": 1, "harvest_yield": 3,
        "personal_food": 0, "market_wallets": True,
        "hungry_market_buyers": True,
        "one_hungry_market_buyer": False,
    }
    return _joined_bootstrap(
        db, initial_market_food=3, wilderness_food_jobs_enabled=True,
        wilderness_food_peddler_enabled=True,
        food_for_work_bakery_enabled=True,
        bakery_opening_food_wage=True,
    )


def seed(path):
    with SQLiteEventStore(path) as db:
        seed_two_field_world(
            db, east_growth_seconds=DAY, east_grain_yield=12,
            initial_water=2, initial_market_food=3,
            market_wallets=True, hungry_market_buyers=True,
            cash_return=True, waged_harvest=True,
            harvest_wage_copper=2, bootstrap=_peddler_bootstrap,
        )
        s = db.load(WORLD)
        s = db.append(WORLD, "peddler:actual-weather-and-food", s.revision, [
            DomainEvent("WaterSourceConfigured", None, "recorded finite water", 0,
                        {"site_id": "well", "capacity": 8}),
            DomainEvent("MetabolismPolicyConfigured", None, "physical metabolism", 0,
                        {"hunger_seconds_per_point": 3600,
                         "activity_hunger_percent": 20}),
        ], bootstrap=True)
        assert len(s.npcs) == 13
        assert (s.schema_version, s.rules_version) == (45, 63)
        assert s.entities[TRADER]["location_id"] == "market"
        assert s.npcs[TRADER]["role"] == "food_peddler"
        assert s.resources[TRADER]["coin_copper"] == 2
        assert s.resources[TRADER]["food"] == 0
        assert s.npc_routines[TRADER]["workplace_id"] == "hunting_woods"
        assert audit_npc_economy(s)["copper_scope_complete"]
        assert audit_npc_economy(s)["copper_known_total"] == 12
        assert db.verify(WORLD).to_dict() == s.to_dict()
    return s


def view(s, **changes):
    raw = s.to_dict()
    for section, updates in changes.items():
        for key, data in updates.items():
            if section == "resources":
                raw[section][key].update(data)
            elif section == "entities":
                raw[section][key].update(data)
            elif section == "npcs":
                raw[section][key].update(data)
            else:
                raw[section][key] = data
    return WorldState.from_dict(raw)


def test_peddler_is_one_of_original_thirteen_and_only_walks_known_roads(tmp_path):
    s = seed(tmp_path / "same-thirteen-no-new-copper.sqlite")
    assert choose_walk(s) is None  # Not omniscient about wilderness paths.
    nav = {"known_routes": ["market-woods"], "visited": ["market"], "target": None}
    saw_adjacent = view(s, navigation={TRADER: nav})
    trip = choose_walk(saw_adjacent)
    assert trip is not None and trip.route_id == "market-woods"
    assert trip.destination == "hunting_woods"
    # Source contents are never inspected by the home-to-work journey:
    stocks = saw_adjacent.to_dict()
    stocks["resources"]["hunting_woods"]["food"] = 100
    assert choose_walk(WorldState.from_dict(stocks)) == trip


def test_wild_sell_requires_real_unpromised_local_stock_and_personal_copper(tmp_path):
    s = seed(tmp_path / "physical-financed-commerce.sqlite")
    raw = s.to_dict()
    raw["resources"]["hunting_woods"]["food"] = 4
    wild = WorldState.from_dict(raw)
    offer = choose_local_food_offer(wild, "omar")
    assert offer is not None and offer.quantity == 2 and offer.unit_price == 1
    raw = wild.to_dict()
    raw["entities"][TRADER]["location_id"] = "hunting_woods"
    raw["market_offers"][offer.offer_id] = {
        "seller_id": "omar", "stock_owner_id": "hunting_woods",
        "site_id": "hunting_woods", "resource": "food",
        "payment_resource": "coin_copper", "quantity": 2,
        "remaining": 2, "unit_price": 1, "posted_at": 0,
        "status": "open", "closed_at": None,
    }
    there = WorldState.from_dict(raw)
    bought = choose_purchase(there)
    assert bought is not None
    assert bought.offer_id == offer.offer_id and bought.unit_price == 1

    raw["resources"][TRADER]["coin_copper"] = 0
    assert choose_purchase(WorldState.from_dict(raw)) is None
    raw["resources"][TRADER]["coin_copper"] = 2
    raw["resources"][TRADER]["food"] = 1
    carrying = WorldState.from_dict(raw)
    assert choose_purchase(carrying) is None
    nav = {"known_routes": ["market-woods"], "visited": ["hunting_woods", "market"],
           "target": None}
    carrying = view(carrying, navigation={TRADER: nav})
    home = choose_walk(carrying)
    assert home is not None and home.route_id == "market-woods"
    assert home.destination == "market"

    raw = carrying.to_dict()
    raw["entities"][TRADER]["location_id"] = "market"
    back = WorldState.from_dict(raw)
    sell = choose_offer(back)
    assert sell is not None and sell.quantity == 1
    raw["market_offers"][sell.offer_id] = {
        "seller_id": TRADER, "stock_owner_id": TRADER,
        "site_id": "market", "resource": "food",
        "payment_resource": "coin_copper", "quantity": 1,
        "remaining": 1, "unit_price": 2, "posted_at": 0,
        "status": "open", "closed_at": None,
    }
    posted = WorldState.from_dict(raw)
    assert choose_offer(posted) is None  # Not double listed.
    assert choose_withdrawal(posted) is None
    hungry = posted.to_dict()
    hungry["npcs"][TRADER]["needs"]["hunger"] = 70
    assert choose_withdrawal(WorldState.from_dict(hungry)).offer_id == sell.offer_id
