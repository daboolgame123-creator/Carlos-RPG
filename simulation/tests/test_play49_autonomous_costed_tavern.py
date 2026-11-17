"""PLAY49-J: one real auto-cooked menu, cost price, no compulsory customer.

The trusted PLAY49-G physical source fixture supplies fruit and cheese by
signed production, local resale and actual roads. Only site purchases,
the cook's next work and the menu quote are autonomous here. Customer demand
is either absent or an explicit TEST NEED condition; not natural hunger proof.
"""
from __future__ import annotations

import pytest

from carlos_sim import (
    DomainEvent, LivingWorldEngine, NPCMarketService,
    SQLiteEventStore, TimeEngine,
)
from test_market_02c import ev, _rev
from test_play49_fruit_stall_contract import WORLD, copper
from test_play49_site_funded_procurement import (
    _setup, _first_real_plate, _second_authentic_goods,
)
from carlos_sim.prepared_food_autonomy import (
    choose_local_costed_plate_offer,
    has_prepared_food_recipe,
)


@pytest.fixture
def kitchen(tmp_path):
    with SQLiteEventStore(tmp_path / "play49j-real-menu.sqlite") as db:
        _setup(db)
        # A real finite shift is necessary for existing production autonomy.
        initial = db.load(WORLD)
        db.append(
            WORLD, "j-cook-contract-shift", initial.revision, [
                ev("NPCRoutineConfigured", {
                    "npc_id": "tavern_cook", "home_id": "bakery",
                    "workplace_id": "tavern", "work_start": 0,
                    "work_end": 7200,
                })
            ], bootstrap=True,
        )
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            market = NPCMarketService(db, clock)
            _first_real_plate(db, clock, market)
            _second_authentic_goods(db, clock, market)
            yield db, clock, market
        finally:
            clock.close_session(WORLD)


def engine(db, clock, *, enabled=True):
    return LivingWorldEngine(
        db, clock, economic_enabled=True, agriculture_enabled=True,
        economy_only_enabled=True, site_procurement_enabled=True,
        costed_prepared_food_enabled=enabled,
    )


def purchased_actual_ingredients(db, clock):
    a = engine(db, clock).advance(
        WORLD, seconds=1, command_id="j-buy-real-ingredients",
        expected_revision=_rev(db),
    )
    bought = db.load(WORLD)
    receipts = [t for t in bought.market_trades.values()
                if t.get("business_keeper_id") == "tavern_host"]
    assert len(receipts) == 2
    assert len(a.economic_trades) == 2
    assert bought.resources["tavern"]["coin_copper"] == 0
    assert bought.resources["tavern"]["fruit"] == 1
    assert bought.resources["tavern"]["cheese"] == 1
    return bought


def produced_and_quoted(db, clock):
    a = engine(db, clock).advance(
        WORLD, seconds=300, command_id="j-autonomous-real-cook",
        expected_revision=_rev(db),
    )
    s = db.load(WORLD)
    cooked = [
        j for j in s.production_jobs.values()
        if j["recipe_id"] == "fruit-cheese-hot-plate"
    ]
    assert len(cooked) == 2
    assert all(j["status"] == "completed" for j in cooked)
    assert len(a.economic_jobs) == 1
    menu = [(ident, o) for ident, o in s.market_offers.items()
            if ident.startswith("eco-menu-tavern-")]
    assert len(menu) == 1
    ident, offer = menu[0]
    assert offer["unit_price"] == 6
    assert offer["quantity"] == 1
    assert offer["stock_owner_id"] == "tavern"
    assert offer["resource"] == "food"
    assert s.resources["tavern"]["food"] in (0, 1)
    assert s.resources["tavern"]["fruit"] == s.resources["tavern"]["cheese"] == 0
    assert copper(s) == 22
    return ident, offer, s


def test_cook_and_costed_quote_do_not_invent_a_hungry_customer(kitchen):
    db, clock, _ = kitchen
    before = db.load(WORLD)
    assert has_prepared_food_recipe(before, "tavern")
    assert choose_local_costed_plate_offer(before, "tavern_host") is None
    purchased_actual_ingredients(db, clock)
    ident, offer, state = produced_and_quoted(db, clock)
    # Huda ate her first actual meal and has no demonstrated hunger for a
    # second one. No imaginary sale, wage or cash transfer may occur.
    assert state.npcs["huda"]["needs"]["hunger"] < 70
    assert state.resources["tavern"]["coin_copper"] == 0
    assert state.resources["tavern"]["food"] == 1
    assert offer["status"] == "open"
    assert not any(t["offer_id"] == ident for t in state.market_trades.values())
    pending = [
        j for j in state.production_jobs.values()
        if j["recipe_id"] == "fruit-cheese-hot-plate"
        and j["started_at"] > before.time
    ]
    assert len(pending) == 1 and "work_wage" not in pending[0]
    db.snapshot(WORLD)
    assert db.verify(WORLD).to_dict() == state.to_dict()
    assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)


def test_real_onsite_buyer_with_test_specified_hunger_pays_six_and_funds_wage(kitchen):
    db, clock, _ = kitchen
    # A bounded test need condition, visibly recorded in the event log.
    # It is NOT a claim that the engine generated this hunger on its own.
    now = db.load(WORLD)
    assert now.npcs["huda"]["needs"]["hunger"] == 0
    db.append(WORLD, "j-buyer-needs-food", now.revision, [
        DomainEvent(
            "NPCNeedChanged", "huda", "explicit buyer hunger test condition",
            now.time, {
                "npc_id": "huda", "need": "hunger",
                "previous": 0, "current": 80,
            },
        ),
    ])
    bought = purchased_actual_ingredients(db, clock)
    assert bought.resources["huda"]["coin_copper"] == 8
    menu_id, offer, sold = produced_and_quoted(db, clock)
    trades = [t for t in sold.market_trades.values()
              if t["offer_id"] == menu_id and t["buyer_id"] == "huda"]
    assert len(trades) == 1 and trades[0]["total_paid"] == 6
    assert sold.resources["huda"]["food"] == 1
    assert sold.resources["huda"]["coin_copper"] == 2
    assert sold.resources["tavern"]["coin_copper"] == 6
    assert offer["status"] == "filled"
    wage = engine(db, clock).advance(
        WORLD, seconds=1, command_id="j-automatic-earned-cook-wage",
        expected_revision=_rev(db),
    ).state
    assert wage.resources["tavern"]["coin_copper"] == 5
    assert wage.resources["tavern_cook"]["coin_copper"] == 2
    assert copper(wage) == 22
    old_and_new = [j for j in wage.production_jobs.values()
                   if j["recipe_id"] == "fruit-cheese-hot-plate"]
    assert len(old_and_new) == 2
    assert all(j.get("work_wage", {}).get("amount") == 1 for j in old_and_new)
    assert db.verify(WORLD).to_dict() == wage.to_dict()


def test_feature_default_off_keeps_previous_generic_quotation_behavior(kitchen):
    db, clock, _ = kitchen
    # The opt-in flag must protect old simulation worlds.
    off = engine(db, clock, enabled=False)
    assert off.costed_prepared_food_enabled is False
    off.advance(WORLD, seconds=1, command_id="j-default-buy",
                expected_revision=_rev(db))
    off.advance(WORLD, seconds=300, command_id="j-default-cook",
                expected_revision=_rev(db))
    state = db.load(WORLD)
    assert not any(o.startswith("eco-menu-") for o in state.market_offers)
    legacy = [(k, o) for k, o in state.market_offers.items()
              if k.startswith("eco-offer-tavern-")]
    assert len(legacy) == 1 and legacy[0][1]["unit_price"] == 2
    assert copper(state) == 22


def test_expensive_menu_requires_true_site_procurement_flag(kitchen):
    db, clock, _ = kitchen
    with pytest.raises(ValueError, match="costed prepared food requires"):
        LivingWorldEngine(
            db, clock, economic_enabled=True,
            costed_prepared_food_enabled=True,
        )
