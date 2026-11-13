"""One bounded, genuine 13-NPC porter lifecycle, on real scarce supplies.

The 4-5h gate is explicitly NOT 96/168h sustainability. The tester gives no
NPC any orders after trusted genesis and never replenishes wildlife, water,
cash or goods. Store replay and actual route + market trade receipts decide.
"""
from __future__ import annotations

import json

from carlos_sim import LivingWorldEngine, SQLiteEventStore, TimeEngine
from carlos_sim.economic_diagnostics import audit_npc_economy
from test_play38_multi_farm_couriers import WORLD
from test_play48_peddler_fast import seed
from test_play48_finite_hunt_fish_roads import conserve_diverse
from carlos_sim.food_peddler import TRADER

HOUR = 3600


def test_genuine_original_thirteen_npc_bought_and_walked_prey_to_market(tmp_path):
    path = tmp_path / "real-real-no-teleport-5h.sqlite"
    seed(path)
    observed = []
    with SQLiteEventStore(path) as db:
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            engine = LivingWorldEngine(
                db, clock, max_events_per_advance=5000,
                decision_cooldown=3600,
                economic_enabled=True, agriculture_enabled=True,
                navigation_enabled=True, routines_enabled=True,
                consumption_enabled=True, survival_enabled=True,
                supply_enabled=True, shopping_routes_enabled=True,
                multi_professional_markets_enabled=True,
                compound_procurement_enabled=True,
                professional_full_life_enabled=True,
                food_for_work_enabled=True,
                food_peddler_enabled=True,
            )
            for h in (1, 2, 3, 4, 5):
                previous = db.verify(WORLD)
                state = engine.advance(
                    WORLD, seconds=h*HOUR - previous.time,
                    expected_revision=previous.revision,
                    command_id=f"real-peddler:{h}h",
                ).state
                assert state.time == h*HOUR
                conserve_diverse(state)
                assert db.verify(WORLD).to_dict() == state.to_dict()
                assert db.db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
                assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
                cash = audit_npc_economy(state)
                assert cash["copper_scope_complete"]
                assert cash["copper_known_total"] == 12
                bought = [
                    t for t in state.market_trades.values()
                    if t["buyer_id"] == TRADER and t["site_id"] == "hunting_woods"
                    and t["resource"] == "food"
                ]
                returned = [
                    t for t in state.travels.values()
                    if t["npc_id"] == TRADER
                    and t["origin"] == "hunting_woods"
                    and t["destination"] == "market"
                    and t["status"] == "arrived"
                ]
                quotes = [
                    o for o in state.market_offers.values()
                    if o["seller_id"] == TRADER
                    and o["stock_owner_id"] == TRADER
                    and o["site_id"] == "market"
                    and o["resource"] == "food"
                ]
                sales = [
                    t for t in state.market_trades.values()
                    if t["seller_id"] == TRADER
                    and t["stock_owner_id"] == TRADER
                    and t["site_id"] == "market"
                    and t["resource"] == "food"
                ]
                observed.append({
                    "hour": h,
                    "real_wilderness_purchases": len(bought),
                    "real_cargo_return_arrivals": len(returned),
                    "private_market_quotes": len(quotes),
                    "real_market_resales": len(sales),
                    "cash_total": cash["copper_known_total"],
                    "peddler_food_personal": state.resources[TRADER]["food"],
                    "peddler_copper_personal": state.resources[TRADER]["coin_copper"],
                })
            assert bought, "no verified source food purchase by physical porter"
            assert returned, "porter never walked purchased food back to market"
            assert quotes or sales, "market did not receive a personal porter offer"
            assert all(t["unit_price"] == 1 for t in bought)
            assert all(t["unit_price"] == 2 for t in sales)
            print("PLAY48_ACTUAL_PHYSICAL_WILD_FOOD_TRADER " +
                  json.dumps(observed, sort_keys=True), flush=True)
        finally:
            clock.close_session(WORLD)
