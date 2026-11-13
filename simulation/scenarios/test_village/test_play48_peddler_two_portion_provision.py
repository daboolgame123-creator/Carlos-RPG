"""PLAY48 same-trader actual double-purchase carrying one own meal + one sale.

Only difference from real 24h funded-guard A/B is the peddler's self-owned
physical procurement of TWO existing on-site food units (two genuine copper)
and one preserved personal meal. Real stock+cash checks, real road to market,
authentic local sales, actual consumption. NO additional hunting, food, cash,
people, ecology, rescue, or unsolicited NPC commands.

If food genuinely available only as one portion, reserve policy rejects
the trade rather than inventing a second portion.
"""
from __future__ import annotations

import json
import pytest
from carlos_sim import SQLiteEventStore, TimeEngine
from carlos_sim.domain import WorldState
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.food_peddler import choose_purchase, choose_offer
from test_play38_multi_farm_couriers import WORLD
from test_play48_real_watch_income_24h import seed, engine, HOUR
from test_play48_finite_hunt_fish_roads import conserve_diverse
from test_play48_peddler_24h_diagnostic import measures


def simulate(path, *, reserve_own_meal):
    genesis = seed(path)
    row = []
    with SQLiteEventStore(path) as db:
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            run = engine(db, clock, reserve_trader_meal=reserve_own_meal)
            for hour in (6, 12, 18, 24):
                prev = db.verify(WORLD)
                state = run.advance(
                    WORLD, seconds=hour * HOUR - prev.time,
                    command_id=f"self-ration:{reserve_own_meal}:{hour}",
                    expected_revision=prev.revision,
                ).state
                assert len(state.npcs) == 13
                conserve_diverse(state)
                assert db.verify(WORLD).to_dict() == state.to_dict()
                assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
                assert not db.db.execute("PRAGMA foreign_key_check").fetchall()
                audit = audit_npc_economy(state)
                assert audit["copper_scope_complete"]
                assert audit["copper_known_total"] == 12
                r = measures(state)
                r["trader_meals"] = sum(x["npc_id"] == "repairman"
                                       for x in state.consumptions.values())
                r["guard_meals"] = sum(x["npc_id"] == "adel"
                                      for x in state.consumptions.values())
                r["trader_hunger"] = state.npcs["repairman"]["needs"]["hunger"]
                r["guard_hunger"] = state.npcs["adel"]["needs"]["hunger"]
                r["actual_trader_source_quantity"] = sum(
                    x["quantity"] for x in state.market_trades.values()
                    if x["buyer_id"] == "repairman"
                    and x["site_id"] == "hunting_woods"
                    and x["resource"] == "food"
                )
                r["actual_market_trader_sales_qty"] = sum(
                    x["quantity"] for x in state.market_trades.values()
                    if x["seller_id"] == "repairman"
                    and x["site_id"] == "market"
                    and x["resource"] == "food"
                )
                row.append(r)
        finally:
            clock.close_session(WORLD)
    return genesis, row


def test_physical_two_portion_trader_reserve_real_13npc_24h_causes_extra_meal(tmp_path):
    initial, control = simulate(tmp_path / "original-source.sqlite",
                                reserve_own_meal=False)
    other, treatment = simulate(tmp_path / "physical-self-meal.sqlite",
                                reserve_own_meal=True)
    assert initial.to_dict() == other.to_dict(), (
        "policy A/B must start from exactly identical genesis"
    )
    a, b = control[-1], treatment[-1]
    print("PLAY48_ACTUAL_FUNDED_TRADER_RESERVED_OWN_MEAL_24H_AB " +
          json.dumps({"baseline": control, "two_portions": treatment},
                     sort_keys=True), flush=True)
    assert b["copper"] == a["copper"] == 12
    assert b["actual_trader_source_quantity"] >= 2
    assert b["actual_market_trader_sales_qty"] >= 1
    assert b["guard_meals"] >= a["guard_meals"], "cannot starve the existing customer"
    assert b["trader_meals"] > a["trader_meals"], "trader did not actually eat reserve"
    assert b["food_eaten_meals"] > a["food_eaten_meals"], (
        "extra trade stock was not eaten by any resident"
    )
    assert b["courier_deliveries"] == a["courier_deliveries"], (
        "do not damage real water/grain logistics"
    )


def test_reserve_policy_never_buys_unavailable_second_portion(tmp_path):
    state = seed(tmp_path / "genesis-no-remote-quotes.sqlite")
    # At unvisited genesis a trader must not infer source goods from the city.
    assert choose_purchase(state, reserve_self_meal=True) is None
    # An empty personal food balance at market never opens fictitious sale.
    assert choose_offer(state, reserve_self_meal=True) is None
