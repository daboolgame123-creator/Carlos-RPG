"""PLAY49-E: real tavern cash ownership and sustainable-price counterfactual.

No new simulation rules. Existing PLAY49-D one-plate fixture has a cash
loss at a 3-copper menu quote; a separate actual purchaser can cover the
5-copper wholesale cost at 6, but the cook's working capital is still
immobilized in the venue, not automatically returned to the worker.
"""
from __future__ import annotations

import pytest

from carlos_sim import (
    DomainEvent, SQLiteEventStore, TimeEngine, NPCMarketService,
    NPCProductionService, NPCConsumptionService,
)
from carlos_sim.store import InvalidEvent
from test_market_02c import ev, prepare, _rev
from test_play49_fruit_stall_contract import WORLD, add_orchard, copper
from test_play49_dairy_stall_contract import add_dairy
from test_play49_tavern_trade_provenance import add_tavern, walk
from test_play49_tavern_cooked_meal import (
    kitchen, add_actual_kitchen, source_and_buy_for_cook,
    deposit_ingredients, cook_real_meal, finish_sale_wage_and_eat,
)


def test_three_copper_menu_is_paid_but_structurally_underpriced(kitchen):
    """A true cooked meal need not be a solvent restaurant."""
    db, clock, market = kitchen
    opening = db.load(WORLD)
    assert opening.resources["tavern_cook"]["coin_copper"] == 5
    assert opening.resources["tavern"]["coin_copper"] == 0
    source_and_buy_for_cook(db, clock, market)
    deposit_ingredients(db, clock)
    paid_and_eaten = finish_sale_wage_and_eat(db, clock, market, opening)

    # Huda's actual receipt of 2+3 copper pays for the raw ingredients.
    # Consumer's 3 cannot cover those 5, even before an independent
    # restaurant owner could account for heat, capital and wages.
    assert paid_and_eaten.resources["huda"]["coin_copper"] == 12
    assert paid_and_eaten.resources["tavern"]["coin_copper"] == 2
    assert paid_and_eaten.resources["tavern_cook"]["coin_copper"] == 1
    actual_menu_revenue = paid_and_eaten.market_trades["real-cooked-food-sale"]["total_paid"]
    wholesale_spending = sum(
        paid_and_eaten.market_trades[key]["total_paid"]
        for key in ("cook-buys-fruit", "cook-buys-cheese")
    )
    assert actual_menu_revenue == 3
    assert wholesale_spending == 5
    assert actual_menu_revenue - wholesale_spending == -2
    start_business_cash = (opening.resources["tavern"]["coin_copper"]
                           + opening.resources["tavern_cook"]["coin_copper"])
    end_business_cash = (paid_and_eaten.resources["tavern"]["coin_copper"]
                         + paid_and_eaten.resources["tavern_cook"]["coin_copper"])
    assert (start_business_cash, end_business_cash) == (5, 3)
    assert copper(paid_and_eaten) == copper(opening)
    assert db.verify(WORLD).to_dict() == paid_and_eaten.to_dict()


def _solvent_case(tmp_path, *, split):
    path = tmp_path / ("split.sqlite" if split else "one.sqlite")
    with SQLiteEventStore(path) as db:
        prepare(db, copper_buyer=5)
        add_orchard(db)
        add_dairy(db)
        add_tavern(db)
        add_actual_kitchen(db)
        # Unlike Salma (5 copper), genuine Huda can pay a 6-copper price.
        # Her buyer ledger must be explicitly initialized, not "None" -> 0.
        old = db.load(WORLD)
        assert old.resources["huda"].get("food") is None
        new = db.append(WORLD, "play49:real-huda-meal-wallet", old.revision, [
            ev("ResourceChanged", {
                "owner_id": "huda", "resource": "food",
                "previous": None, "current": 0, "source": "initialization",
            }),
        ], bootstrap=True)
        assert copper(new) == copper(old)
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        market = NPCMarketService(db, clock)
        opening = db.load(WORLD)
        assert opening.resources["huda"]["coin_copper"] == 10
        assert opening.resources["salma"]["coin_copper"] == 5
        assert opening.resources["tavern_cook"]["coin_copper"] == 5
        assert opening.resources["tavern"]["coin_copper"] == 0

        source_and_buy_for_cook(db, clock, market, split=split)
        deposit_ingredients(db, clock)
        cooked = cook_real_meal(db, clock, split=split)
        assert cooked.resources["tavern"]["food"] == 1
        assert cooked.resources["tavern"]["coin_copper"] == 0

        # The *actual* cooked dish, not free food, gets a different visible
        # quote: 5 real ingredient coins + 1 cash wage = 6.
        market.post(WORLD, "tavern_host", "tavern", "tavern",
                    "six-copper-hot-plate", "food", 1, "coin_copper", 6,
                    expected_revision=_rev(db))

        # Existing village consumer Salma has only 5; price is not magical
        # "demand". She physically arrives but cannot afford this plate.
        walk(db, clock, "salma", "bakery-tavern",
             "salma-sees-too-expensive-meal", 80, split=split)
        before_rejected_buy = db.load(WORLD)
        with pytest.raises(InvalidEvent):
            market.buy(WORLD, "salma", "salma-cannot-afford-six",
                       "six-copper-hot-plate", 1, 6,
                       expected_revision=_rev(db))
        assert db.verify(WORLD).to_dict() == before_rejected_buy.to_dict()
        assert before_rejected_buy.resources["tavern"]["coin_copper"] == 0

        # Physically on-site Huda has 12 after her own legitimate trading.
        before_huda = db.load(WORLD)
        assert before_huda.resources["huda"]["coin_copper"] == 12
        assert before_huda.resources["huda"]["food"] == 0
        bought = market.buy(WORLD, "huda", "huda-pays-full-cook-cost",
                            "six-copper-hot-plate", 1, 6,
                            expected_revision=_rev(db)).state
        assert bought.resources["huda"]["food"] == 1
        assert bought.resources["huda"]["coin_copper"] == 6
        assert bought.resources["tavern"]["food"] == 0
        assert bought.resources["tavern"]["coin_copper"] == 6
        assert bought.market_trades["huda-pays-full-cook-cost"]["total_paid"] == 6

        # Completed signed work is paid from actual *sale proceeds*.
        paid = db.append(WORLD, "tavern:salary-from-six-copper-sale",
                         bought.revision, [
            DomainEvent("ProductionWagePaid", None,
                        "one completed plate paid from real diner purchase",
                        bought.time, {"job_id": "real-hot-plate", "amount": 1}),
        ], production_authorized=True)
        assert paid.resources["tavern"]["coin_copper"] == 5
        assert paid.resources["tavern_cook"]["coin_copper"] == 1

        ate = NPCConsumptionService(db, clock).eat(
            WORLD, "huda", 1, command_id="huda-eats-paid-hot-plate",
            expected_revision=_rev(db))
        ending = ate.state
        assert ate.consumed_quantity == 1
        assert ending.resources["huda"]["food"] == 0
        assert ending.npcs["huda"]["needs"]["hunger"] == 0
        assert ending.consumptions[ate.id]["hunger_before"] == 20
        assert ending.consumptions[ate.id]["hunger_after"] == 0
        assert ending.resources["huda"]["coin_copper"] == 6
        assert ending.resources["tavern"]["coin_copper"] == 5
        assert ending.resources["tavern_cook"]["coin_copper"] == 1
        assert ending.resources["salma"]["coin_copper"] == 5

        # The business+financing-worker combination has made one real
        # copper of gross cash gain: 5 before -> 6 after. The actual cook
        # personally LOST 4, cannot buy another 5-copper ingredient package,
        # and the original milk/fruit is exhausted. Venue-owned 5 copper
        # is not the cook's own working capital!
        assert (opening.resources["tavern"]["coin_copper"]
                + opening.resources["tavern_cook"]["coin_copper"]) == 5
        assert (ending.resources["tavern"]["coin_copper"]
                + ending.resources["tavern_cook"]["coin_copper"]) == 6
        assert ending.resources["tavern"]["food"] == 0
        assert ending.resources["tavern"]["fruit"] == 0
        assert ending.resources["tavern"]["cheese"] == 0
        assert ending.resources["orchard"]["fruit"] == 0
        assert ending.resources["dairy"]["milk"] == 0
        assert ending.resources["dairy"]["cheese"] == 0
        with pytest.raises(InvalidEvent):
            NPCProductionService(db, clock).start(
                WORLD, "tavern_cook", "fruit-cheese-hot-plate",
                "attempt-second-unfunded-meal", expected_revision=_rev(db))
        assert db.verify(WORLD).to_dict() == ending.to_dict()
        db.snapshot(WORLD)
        assert db.verify(WORLD).to_dict() == ending.to_dict()
        assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert not db.db.execute("PRAGMA foreign_key_check").fetchall()

        result = (
            ending.time,
            ending.resources,
            ending.production_jobs,
            ending.market_trades,
            ending.consumptions,
        )
        clock.close_session(WORLD)
        return result


@pytest.mark.parametrize("split", [False, True], ids=["one-tick", "split-time"])
def test_full_cost_real_price_meal_access_and_trapped_working_capital(tmp_path, split):
    _solvent_case(tmp_path, split=split)


def test_six_copper_meal_accounting_does_not_change_with_time_partitions(tmp_path):
    whole = _solvent_case(tmp_path, split=False)
    divided = _solvent_case(tmp_path, split=True)
    assert whole == divided, "true paid market receipts must be partition-stable"
