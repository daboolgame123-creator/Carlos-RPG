"""PLAY-40: actual market coin receipts are consigned back over real roads.

The old world has no configured copper-carrying courier and never changes.
No wages or paychecks are invented; this phase proves a finite physical route
by which future funded wages may actually reach their local workplaces.
"""
from __future__ import annotations

import json
import pytest

from carlos_sim import DomainEvent, InvalidEvent, LivingWorldEngine, SQLiteEventStore, TimeEngine
from test_play38_multi_farm_couriers import (
    WORLD, EAST, COURIER, seed_two_field_world,
)


def _audit(state):
    balances = state.resources
    total = sum(x.get("coin_copper", 0) for x in balances.values())
    paid_by_customers = sum(
        trade["total_paid"] for trade in state.market_trades.values()
    )
    physical_receipts = sum(
        balances[who]["coin_copper"] for who in ("market", "bakery", EAST, COURIER)
    )
    assert total == 12, "cash was created or destroyed"
    assert physical_receipts == paid_by_customers
    assert balances["market"]["coin_copper"] >= 0
    assert balances["bakery"]["coin_copper"] >= 0
    assert balances[EAST]["coin_copper"] >= 0
    assert balances[COURIER]["coin_copper"] in (0, 1)
    assert "coin_copper" not in balances["huda"], "legacy courier gained cash"
    return {
        "time": state.time, "total_copper": total,
        "paid_by_buyers": paid_by_customers,
        "market": balances["market"]["coin_copper"],
        "bakery": balances["bakery"]["coin_copper"],
        "farm_east": balances[EAST]["coin_copper"],
        "physical_courier": balances[COURIER]["coin_copper"],
        "trades": len(state.market_trades),
        "bread": balances["market"]["food"] + balances["bakery"]["food"],
        "delivered": state.supply_circuits[COURIER]["deliveries"],
    }


def test_customer_copper_reaches_real_bakery_and_farm_on_return_roads(tmp_path):
    with SQLiteEventStore(tmp_path / "cash-return.sqlite") as db:
        seed_two_field_world(
            db, cash_return=True, market_wallets=True,
            hungry_market_buyers=True, initial_market_food=3,
        )
        original = db.verify(WORLD)
        assert original.resources["market"]["coin_copper"] == 0
        assert original.resources["bakery"]["coin_copper"] == 0
        assert original.resources[EAST]["coin_copper"] == 0
        _audit(original)
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            engine = LivingWorldEngine(
                db, clock, max_events_per_advance=5000,
                decision_cooldown=3600, navigation_enabled=True,
                routines_enabled=True, survival_enabled=True,
                consumption_enabled=True, supply_enabled=True,
                economic_enabled=True, adaptive_market_enabled=True,
                agriculture_enabled=True, economy_only_enabled=True,
            )
            rows = [_audit(original)]
            for target in (300, 1200, 3600, 7200, 12000):
                old = db.load(WORLD)
                state = engine.advance(
                    WORLD, seconds=target-old.time,
                    command_id=f"play40-coin:{target}",
                    expected_revision=old.revision,
                ).state
                assert state.time == target
                rows.append(_audit(state))
                assert db.verify(WORLD).to_dict() == state.to_dict()
                db.snapshot(WORLD)
                assert db.verify(WORLD).to_dict() == state.to_dict()
            assert rows[-1]["trades"] >= 2
            assert rows[-1]["paid_by_buyers"] >= 2
            assert rows[-1]["bakery"] >= 1
            assert rows[-1]["farm_east"] >= 1
            assert rows[-1]["total_copper"] == 12
            print("PLAY40_REAL_COPPER_ON_ROADS", json.dumps(rows, sort_keys=True))
        finally:
            clock.close_session(WORLD)


def test_cannot_create_copper_cargo_at_wrong_site_or_with_wrong_capability(tmp_path):
    with SQLiteEventStore(tmp_path / "forged-copper.sqlite") as db:
        seed_two_field_world(
            db, cash_return=True, market_wallets=True,
            initial_market_food=3, hungry_market_buyers=True,
        )
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            original = db.verify(WORLD).to_dict()
            forged = DomainEvent(
                "SupplyCargoPicked", COURIER, "forged copper at well", 0,
                {"courier_id": COURIER, "resource": "coin_copper"},
            )
            with pytest.raises(InvalidEvent):
                db.append(WORLD, "copper-remote-attempt", db.load(WORLD).revision,
                          [forged], supply_authorized=True)
            assert db.verify(WORLD).to_dict() == original
            with pytest.raises(InvalidEvent):
                db.append(WORLD, "copper-no-capability", db.load(WORLD).revision,
                          [forged])
            assert db.verify(WORLD).to_dict() == original
        finally:
            clock.close_session(WORLD)


def test_old_courier_does_not_gain_implicit_cash_authorization(tmp_path):
    with SQLiteEventStore(tmp_path / "old-courier.sqlite") as db:
        seed_two_field_world(db)
        state = db.verify(WORLD)
        assert "coin_copper" not in state.resources["huda"]
        assert "coin_copper" not in state.resources[COURIER]
        assert state.supply_circuits["huda"]["carry"] is None
        assert state.supply_circuits[COURIER]["carry"] is None


@pytest.mark.parametrize("hunger", [80, 90])
def test_stranded_courier_cannot_offer_consigned_copper_for_bread(tmp_path, hunger):
    from carlos_sim.domain import WorldState
    from carlos_sim.economic_autonomy import choose_local_food_purchase
    from carlos_sim.market import execute_trade, post_offer
    from carlos_sim.supply import project_cargo, validate_supply_circuits, choose_courier_leg

    with SQLiteEventStore(tmp_path / "cargo-is-not-a-wallet.sqlite") as db:
        seed_two_field_world(db, cash_return=True, market_wallets=True,
                             initial_market_food=3)
        raw = db.verify(WORLD).to_dict()
    # Reproduce an idle courier at the cash pickup stop before the next leg.
    raw["entities"][COURIER]["location_id"] = "market"
    raw["supply_circuits"][COURIER]["index"] = 3
    raw["resources"]["market"]["coin_copper"] = 1
    raw["resources"]["carlos"]["coin_copper"] -= 1
    project_cargo(raw, DomainEvent(
        "SupplyCargoPicked", COURIER, "local cash consignment", 0,
        {"courier_id": COURIER, "resource": "coin_copper"},
    ), supply_authorized=True)
    raw["npcs"][COURIER]["needs"]["hunger"] = hunger
    validate_supply_circuits(raw)
    seller = raw["market_stalls"]["market"]["keeper_id"]
    post_offer(raw, DomainEvent("MarketOfferPosted", seller, "local loaf", 0, {
        "id": "one-coin-loaf", "seller_id": seller, "stock_owner_id": "market",
        "site_id": "market", "resource": "food", "quantity": 1,
        "payment_resource": "coin_copper", "unit_price": 1,
    }), market_authorized=True)
    state = WorldState.from_dict(raw)
    # The food is unaffordable even BEFORE hunger prevents a real next leg.
    assert (choose_courier_leg(state, COURIER) is not None) == (hunger < 90)
    assert choose_local_food_purchase(state, COURIER) is None
    before = state.to_dict()
    with pytest.raises(ValueError, match="insufficient market goods/coins"):
        execute_trade(raw, DomainEvent("MarketTradeExecuted", COURIER, "attempt", 0, {
            "id": "spend-reserved-cash", "offer_id": "one-coin-loaf",
            "buyer_id": COURIER, "quantity": 1, "expected_unit_price": 1,
        }), market_authorized=True)
    assert raw == before
    validate_supply_circuits(raw)


def test_food_purchase_skips_a_listing_backed_only_by_courier_cargo(tmp_path):
    from carlos_sim.domain import WorldState
    from carlos_sim.economic_autonomy import choose_local_food_purchase
    from carlos_sim.market import post_offer
    from carlos_sim.supply import project_cargo, validate_supply_circuits

    with SQLiteEventStore(tmp_path / "cargo-is-not-for-sale.sqlite") as db:
        seed_two_field_world(db, cash_return=True, market_wallets=True,
                             hungry_market_buyers=True, initial_market_food=3)
        raw = db.verify(WORLD).to_dict()
    raw["entities"][COURIER]["location_id"] = "bakery"
    raw["supply_circuits"][COURIER]["index"] = 2
    raw["entities"]["omar"]["location_id"] = "bakery"
    raw["resources"]["market"]["food"] -= 1
    raw["resources"]["bakery"]["food"] += 1
    project_cargo(raw, DomainEvent(
        "SupplyCargoPicked", COURIER, "bread for the market", 0,
        {"courier_id": COURIER, "resource": "food"},
    ), supply_authorized=True)
    validate_supply_circuits(raw)
    post_offer(raw, DomainEvent("MarketOfferPosted", COURIER, "local listing", 0, {
        "id": "courier-loaf", "seller_id": COURIER, "stock_owner_id": COURIER,
        "site_id": "bakery", "resource": "food", "quantity": 1,
        "payment_resource": "coin_copper", "unit_price": 1,
    }), market_authorized=True)
    assert choose_local_food_purchase(WorldState.from_dict(raw), "omar") is None
    raw["resources"]["market"]["food"] -= 1
    raw["resources"][COURIER]["food"] += 1
    validate_supply_circuits(raw)
    purchase = choose_local_food_purchase(WorldState.from_dict(raw), "omar")
    assert purchase is None
    # A personal loaf does not give this cash courier a personal copper slot.
    # Reject before any writes rather than failing the whole world at validation.
    from carlos_sim.market import execute_trade
    from copy import deepcopy
    before = deepcopy(raw)
    with pytest.raises(ValueError, match="receipt conflicts with courier custody"):
        execute_trade(raw, DomainEvent("MarketTradeExecuted", "omar", "local purchase", 0, {
            "id": "personal-loaf-sale", "offer_id": "courier-loaf",
            "buyer_id": "omar", "quantity": 1, "expected_unit_price": 1,
        }), market_authorized=True)
    assert raw == before
    validate_supply_circuits(raw)


def test_market_cannot_sell_water_into_a_courier_custody_slot(tmp_path):
    """Even barter with personal food must preserve the supply contract."""
    from copy import deepcopy
    from carlos_sim.market import post_offer, execute_trade
    from carlos_sim.supply import validate_supply_circuits

    with SQLiteEventStore(tmp_path / "incoming-water.sqlite") as db:
        seed_two_field_world(db, cash_return=True, market_wallets=True,
                             initial_market_food=3)
        raw = db.verify(WORLD).to_dict()
    # Isolated local reducer probe; reallocate real existing water and food.
    raw["entities"][COURIER]["location_id"] = "market"
    raw["supply_circuits"][COURIER]["index"] = 3
    raw["resources"]["well"]["water"] -= 1
    raw["resources"]["market"]["water"] = 1
    raw["resources"]["market"]["food"] -= 1
    raw["resources"][COURIER]["food"] += 1
    validate_supply_circuits(raw)
    seller = raw["market_stalls"]["market"]["keeper_id"]
    post_offer(raw, DomainEvent("MarketOfferPosted", seller, "local water barter", 0, {
        "id": "water-for-food", "seller_id": seller, "stock_owner_id": "market",
        "site_id": "market", "resource": "water", "quantity": 1,
        "payment_resource": "food", "unit_price": 1,
    }), market_authorized=True)
    before = deepcopy(raw)
    with pytest.raises(ValueError, match="receipt conflicts with courier custody"):
        execute_trade(raw, DomainEvent("MarketTradeExecuted", COURIER, "barter", 0, {
            "id": "buy-water", "offer_id": "water-for-food", "buyer_id": COURIER,
            "quantity": 1, "expected_unit_price": 1,
        }), market_authorized=True)
    assert raw == before
    validate_supply_circuits(raw)
