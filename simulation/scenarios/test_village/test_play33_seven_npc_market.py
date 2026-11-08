"""PLAY-33: actual seven-NPC autonomous local-market counterfactuals.

No player command buys, posts or changes prices. Three disposable worlds use
separately declared physical food and the same twelve opening copper coins.
"""
from __future__ import annotations

import pytest

from carlos_sim import LivingWorldEngine, SQLiteEventStore, TimeEngine
from play_physical_supply import WORLD, PEOPLE, audit_physical_supply, seed_physical_supply


@pytest.mark.parametrize("loaves,expected_price,expected_sales", [
    (0, None, 0),
    (1, 3, 1),
    (3, 2, 3),
])
def test_seven_independent_npcs_experience_local_stock_shortage_without_free_goods(
        tmp_path, loaves, expected_price, expected_sales):
    with SQLiteEventStore(tmp_path / f"market-{loaves}.sqlite") as db:
        seed_physical_supply(
            db, personal_food=0, harvest_yield=3, market_wallets=True,
            initial_market_food=loaves, hungry_market_buyers=True,
        )
        before = db.load(WORLD)
        assert before.time == 0 and len(before.npcs) == len(PEOPLE) == 7
        assert before.resources["market"]["food"] == loaves
        assert audit_physical_supply(before, water=2, seed=1, buyer_copper=2,
                                     initial_market_food=loaves)["copper"] == 12
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
            result = engine.advance(WORLD, seconds=300,
                                    command_id=f"adaptive-seven:{loaves}",
                                    expected_revision=before.revision)
            final = result.state
            market_quotes = [v for v in final.market_offers.values()
                             if v["site_id"] == "market" and v["resource"] == "food"]
            assert (market_quotes[0]["unit_price"] if market_quotes else None) == expected_price
            assert len(final.market_trades) == expected_sales
            if loaves == 1:
                # Layla holds enough finite coins for the scarcity price.
                assert next(iter(final.market_trades.values()))["buyer_id"] == "layla"
            assert len(final.consumptions) == expected_sales
            assert final.resources["market"]["food"] == loaves - expected_sales
            assert final.resources["market"]["coin_copper"] == expected_sales * (expected_price or 0)
            assert audit_physical_supply(final, seed=1, water=2, buyer_copper=2,
                                         initial_market_food=loaves)["copper"] == 12
            assert db.verify(WORLD).to_dict() == final.to_dict()
            db.snapshot(WORLD)
            assert db.verify(WORLD).to_dict() == final.to_dict()
        finally:
            clock.close_session(WORLD)
