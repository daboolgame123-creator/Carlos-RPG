"""PLAY-30C: isolate real local market access from late, finite harvests.

Three loaves are physically DECLARED as existing market inventory at bootstrap.
No event can mint stock afterwards. With the same loaves and total 12 coins,
only the distribution of existing copper changes between control worlds.
"""
from __future__ import annotations

import pytest

from carlos_sim import SQLiteEventStore, TimeEngine, LivingWorldEngine
from play_physical_supply import WORLD, PEOPLE, seed_physical_supply, audit_physical_supply

STARTING_MARKET_LOAVES = 3
INITIAL_COPPER = 12
SECONDS = 300


def _run_local_market(path, *, redistributed, market_loaves=STARTING_MARKET_LOAVES):
    with SQLiteEventStore(path) as db:
        seed_physical_supply(
            db, personal_food=0, harvest_yield=3,
            market_wallets=redistributed, initial_market_food=market_loaves,
            hungry_market_buyers=True,
        )
        started = db.load(WORLD)
        assert started.time == 0
        assert len(started.npcs) == len(PEOPLE) == 7
        assert audit_physical_supply(
            started, water=2, seed=1, buyer_copper=2,
            initial_market_food=market_loaves,
        )["copper"] == INITIAL_COPPER
        assert started.resources["market"]["food"] == market_loaves
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            engine = LivingWorldEngine(
                db, clock,
                max_events_per_advance=5000, decision_cooldown=3600,
                navigation_enabled=True, routines_enabled=True,
                survival_enabled=True, consumption_enabled=True,
                supply_enabled=True, economic_enabled=True,
                agriculture_enabled=True, economy_only_enabled=True,
            )
            state = engine.advance(
                WORLD, seconds=SECONDS,
                command_id=f"real-market:{redistributed}:{market_loaves}",
                expected_revision=started.revision,
            ).state
            assert state.time == SECONDS
            assert audit_physical_supply(
                state, seed=1, water=2, buyer_copper=2,
                initial_market_food=market_loaves,
            )["copper"] == INITIAL_COPPER
            assert db.verify(WORLD).to_dict() == state.to_dict()
            db.snapshot(WORLD)
            assert db.verify(WORLD).to_dict() == state.to_dict()
            purchases = {record["buyer_id"] for record in state.market_trades.values()}
            eaten = {record["npc_id"] for record in state.consumptions.values()}
            return {
                "buyers": sorted(purchases),
                "eaters": sorted(eaten),
                "trades": len(state.market_trades),
                "meals": sum(m["quantity"] for m in state.consumptions.values()),
                "market_food": state.resources["market"]["food"],
                "market_copper": state.resources["market"]["coin_copper"],
                "hunger": {who: state.npcs[who]["needs"]["hunger"]
                           for who in ("adel", "layla", "omar")},
            }
        finally:
            clock.close_session(WORLD)


def test_existing_local_stock_plus_finite_buying_power_feeds_three_npcs(tmp_path):
    concentrated = _run_local_market(tmp_path / "owner-holds-coins.sqlite", redistributed=False)
    redistributed = _run_local_market(tmp_path / "neighbors-hold-coins.sqlite", redistributed=True)
    # Both worlds start with precisely the same three physical market loaves
    # and the same total 12 copper. Purchases happen only through the
    # existing authenticated local market and actual food-consumption events.
    assert concentrated["buyers"] == ["adel"]
    assert concentrated["trades"] == concentrated["meals"] == 1
    assert concentrated["market_food"] == 2
    assert concentrated["market_copper"] == 2
    assert redistributed["buyers"] == ["adel", "layla", "omar"]
    assert redistributed["eaters"] == ["adel", "layla", "omar"]
    assert redistributed["trades"] == redistributed["meals"] == 3
    assert redistributed["market_food"] == 0
    assert redistributed["market_copper"] == 6
    assert redistributed["hunger"]["layla"] < concentrated["hunger"]["layla"]
    assert redistributed["hunger"]["omar"] < concentrated["hunger"]["omar"]
    print("PLAY30_FINITE_MARKET_REQUIRES_STOCK_AND_OWNER_CASH",
          {"concentrated": concentrated, "redistributed": redistributed})


def test_even_three_financed_hungry_buyers_cannot_purchase_missing_loaves(tmp_path):
    no_food = _run_local_market(
        tmp_path / "empty-market.sqlite", redistributed=True, market_loaves=0,
    )
    assert no_food["buyers"] == []
    assert no_food["meals"] == no_food["trades"] == 0
    assert no_food["market_copper"] == 0


@pytest.mark.parametrize("invalid", [-1, 4, 1.0, True, None, "3", [], {}])
def test_initial_market_food_is_a_strictly_bounded_bootstrap_endowment(tmp_path, invalid):
    with SQLiteEventStore(tmp_path / "bad-market-stock.sqlite") as db:
        with pytest.raises(ValueError, match="initial_market_food"):
            seed_physical_supply(db, initial_market_food=invalid)


@pytest.mark.parametrize("invalid", [0, 1, None, "true", [], {}])
def test_hungry_market_buyers_requires_boolean(tmp_path, invalid):
    with SQLiteEventStore(tmp_path / "bad-hunger-toggle.sqlite") as db:
        with pytest.raises(ValueError, match="hungry_market_buyers"):
            seed_physical_supply(db, hungry_market_buyers=invalid)
