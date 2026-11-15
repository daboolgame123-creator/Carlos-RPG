"""PLAY48 BAKERY-FUNDED COURIER PAY: exact original 13NPC A/B.

Huda did real grain deliveries, but only held zero-funded market-food contract
which requires a real bread-market delivery. Compare replacing Huda's original
contract with a *genuinely pre-funded* bakery contract that pays only after
her grain has been physically delivered, never upon location or hunger alone.

WARNING: opening bakery owns ONE actual loaf. Signing this 1-loaf contract
takes that loaf out of bakery circulation. A valid wage can still destroy
the commodity cycle. Economic acceptance expressly rejects those outcomes.
"""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from carlos_sim import DomainEvent, SQLiteEventStore, TimeEngine
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.hydrology import FiniteWaterService
from test_play38_multi_farm_couriers import WORLD
from test_play48_deferred_courier_market_income import signed_genesis
from test_play48_real_watch_income_24h import engine as source_engine, HOUR
from test_play48_finite_hunt_fish_roads import conserve_diverse

HOURS = (6, 24, 30, 36, 48)


def seed(path: Path, *, bakery_contract: bool):
    # Both participants have same physical people, initial supply, roads and
    # trusted zero-funded Hana contract. Exactly one Huda contract varies.
    first = signed_genesis(path, worker_ids=("hana",))
    with SQLiteEventStore(path) as db:
        first = db.append(WORLD,
            f"original-genuine-huda-contract:{bakery_contract}", first.revision,
            [DomainEvent("CourierProvisionConfigured", None,
                "signed employer actually owns this bread at opening", 0,
                {"id": "huda-physical-bakery-grain-service"
                       if bakery_contract else "real-surplus-only-huda",
                 "courier_id": "huda",
                 "payer_site": "bakery" if bakery_contract else "market",
                 "units": 1 if bakery_contract else 0,
                 **({} if bakery_contract else {"authorized_total_units": 2})})],
            bootstrap=True)
        assert db.verify(WORLD).to_dict() == first.to_dict()
    assert first.rules_version == 64 and len(first.npcs) == 13
    assert audit_npc_economy(first)["copper_known_total"] == 12
    assert sum(c["remaining"] for c in first.courier_provisions.values()) == (
        1 if bakery_contract else 0
    )
    assert first.resources["bakery"]["food"] == (0 if bakery_contract else 1)
    conserve_diverse(first)
    return first


def view(state):
    coin = audit_npc_economy(state)
    assert coin["copper_known_total"] == 12
    return {
        "hour": state.time // HOUR,
        "bakery_food": state.resources["bakery"]["food"],
        "bakery_grain": state.resources["bakery"]["grain"],
        "market_food": state.resources["market"]["food"],
        "market_copper": state.resources["market"]["coin_copper"],
        "bread_made": sum(j["status"] == "completed"
                          for j in state.production_jobs.values()
                          if state.production_recipes[j["recipe_id"]]["output_resource"]
                          == "food" and j["site_id"] == "bakery"),
        "village_hunger100": sum(n["needs"]["hunger"] == 100
                                for n in state.npcs.values()),
        "village_meals": len(state.consumptions),
        "food_sales": sum(x["resource"] == "food"
                          for x in state.market_trades.values()),
        "real_courier_deliveries": {
            who: state.supply_circuits[who]["deliveries"]
            for who in ("hana", "huda")},
        "courier_hunger": {who: state.npcs[who]["needs"]["hunger"]
                           for who in ("hana", "huda")},
        "courier_meals": {
            who: sum(c["npc_id"] == who for c in state.consumptions.values())
            for who in ("hana", "huda")},
        "courier_wages": {
            who: [pay["service_deliveries"]
                  for contract in state.courier_provisions.values()
                  if contract["courier_id"] == who
                  for pay in contract["payments"]]
            for who in ("hana", "huda")},
        "escrow_food": sum(c["remaining"] for c in state.courier_provisions.values()),
    }


def run(path: Path, *, bakery_contract: bool):
    seed(path, bakery_contract=bakery_contract)
    result = {}
    with SQLiteEventStore(path) as db:
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            sim = source_engine(db, clock, reserve_trader_meal=True,
                               deferred_market_courier_wage=True)
            sim.merchant_food_wage_enabled = True
            s = db.verify(WORLD)
            for hour in HOURS:
                s = sim.advance(
                    WORLD, seconds=hour*HOUR-s.time,
                    command_id=f"bakery-vs-market-huda-contract:{hour}",
                    expected_revision=s.revision).state
                conserve_diverse(s)
                assert db.verify(WORLD).to_dict() == s.to_dict()
                assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
                assert not db.db.execute("PRAGMA foreign_key_check").fetchall()
                result[hour] = view(s)
                if hour == 24:
                    s = FiniteWaterService(db, clock).record(
                        WORLD, "well", "fixed-external-rain-day1", 2,
                        command_id="real-attributed-source-day1",
                        expected_revision=s.revision).state
                    conserve_diverse(s)
            assert db.snapshot(WORLD).to_dict() == s.to_dict()
        finally:
            clock.close_session(WORLD)
    with SQLiteEventStore(path) as db:
        assert db.verify(WORLD).to_dict() == s.to_dict()
    return result


def test_genuine_bakery_grain_delivery_wage_affects_other_livelihoods(tmp_path):
    baseline = run(tmp_path / "original-market-contract.sqlite",
                   bakery_contract=False)
    case = run(tmp_path / "paid-bakery-grain-contract.sqlite",
               bakery_contract=True)
    for hour in HOURS:
        before, after = baseline[hour], case[hour]
        print("PLAY48_HUDA_BAKERY_GRAIN_PHYSICAL_WAGE_AB " +
              json.dumps({
                  "hour":hour,
                  "control":before,
                  "candidate":after,
                  "meal_delta":after["village_meals"]-before["village_meals"],
                  "bakery_output_delta":after["bread_made"]-before["bread_made"],
                  "sales_delta":after["food_sales"]-before["food_sales"],
                  "real_delivery_delta":{
                      who:after["real_courier_deliveries"][who] -
                          before["real_courier_deliveries"][who]
                      for who in ("hana","huda")
                  },
                  "conserved_food_water_and_12_copper":True,
                  "strict_sqlite_replay":True,
                  "release_no_go":True,
              },sort_keys=True),flush=True)
        assert after["escrow_food"] >= 0
    assert len(case[36]["courier_wages"]["huda"]) >= 1, (
        "authentic Huda grain service did not earn signed bakery-paid loaf")
    assert case[36]["courier_meals"]["huda"] > baseline[36]["courier_meals"]["huda"], (
        "bakery salary never became an actual worker meal by starvation deadline")
    for hour in (30,36,48):
        assert case[hour]["village_meals"] >= baseline[hour]["village_meals"]
        assert case[hour]["food_sales"] >= baseline[hour]["food_sales"]
        assert case[hour]["bread_made"] >= baseline[hour]["bread_made"]
        for who in ("hana","huda"):
            assert (case[hour]["real_courier_deliveries"][who] >=
                    baseline[hour]["real_courier_deliveries"][who]), (
                "bakery wage diverted essential original logistics")
