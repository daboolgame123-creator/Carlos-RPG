"""PLAY48 merchant sales wage authentic 13NPC causal A/B, no free inventory.

Two identically seeded physical villages with all real couriers, personally
owned money, market trades and fixed observed rainfall. The candidate adds
only an explicit time-zero one-copper labor wage contract to market steward.
No runtime grants, hunger bypasses, fake prices or magical cash.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from carlos_sim import DomainEvent, SQLiteEventStore, TimeEngine
from carlos_sim.store import InvalidEvent
from carlos_sim.hydrology import FiniteWaterService
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.steward_wages import choose_steward_wage
from test_play38_multi_farm_couriers import WORLD
from test_play48_deferred_courier_market_income import signed_genesis
from test_play48_real_watch_income_24h import engine as original_engine, HOUR
from test_play48_finite_hunt_fish_roads import conserve_diverse

CHECKPOINTS = (6, 24, 30, 36)


def seeded(path: Path, *, employer_signed: bool):
    created = signed_genesis(path)
    if employer_signed:
        with SQLiteEventStore(path) as db:
            created = db.append(
                WORLD, "merchant-employer-original-trusted-genesis",
                created.revision,
                [DomainEvent("MarketStewardWageConfigured", None,
                    "market employer signs one coin per completed food sale", 0,
                    {"site_id": "market", "keeper_id": "salma", "wage_coin": 1})],
                bootstrap=True,
            )
            assert db.verify(WORLD).to_dict() == created.to_dict()
    assert (created.schema_version, created.rules_version) == (45, 64)
    assert len(created.npcs) == 13
    assert audit_npc_economy(created)["copper_known_total"] == 12
    conserve_diverse(created)
    return created


def snapshot(state):
    before = state.to_dict()
    economy = audit_npc_economy(state)
    seller_receipts = [(ident, t["sale_wage"]) for ident, t
                       in state.market_trades.items() if "sale_wage" in t]
    assert economy["copper_scope_complete"] and economy["copper_known_total"] == 12
    assert all(t["worker_id"] == "salma" and t["site_id"] == "market"
               and t["amount"] == 1 for _, t in seller_receipts)
    assert len(state.npcs) == 13
    report = {
        "hour": state.time // HOUR,
        "merchant_earned_sales": len(seller_receipts),
        "merchant_earned_coins": sum(t["amount"] for _, t in seller_receipts),
        "merchant_wallet": state.resources["salma"].get("coin_copper"),
        "merchant_hunger": state.npcs["salma"]["needs"]["hunger"],
        "merchant_meals": sum(m["npc_id"] == "salma" for m in state.consumptions.values()),
        "market_site_coins": state.resources["market"].get("coin_copper"),
        "market_site_food": state.resources["market"].get("food"),
        "hunger_100": sum(x["needs"]["hunger"] == 100 for x in state.npcs.values()),
        "meals": len(state.consumptions),
        "jobs": sum(x["status"] == "completed" for x in state.production_jobs.values()),
        "food_sales": sum(x["resource"] == "food" for x in state.market_trades.values()),
        "courier_deliveries": {
            who: state.supply_circuits[who]["deliveries"] for who in ("hana", "huda")
        },
        "courier_hunger": {
            who: state.npcs[who]["needs"]["hunger"] for who in ("hana", "huda")
        },
        "site_coins": {owner: amt for owner, amt in
                       economy["copper_known_by_owner"].items()
                       if owner in state.locations and amt > 0},
    }
    assert state.to_dict() == before
    return report


def simulate(path: Path, *, employer_signed: bool):
    seeded(path, employer_signed=employer_signed)
    output = {}
    with SQLiteEventStore(path) as db:
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            sim = original_engine(
                db, clock, reserve_trader_meal=True,
                deferred_market_courier_wage=True,
            )
            # Restrict experimental behavior to existing actual economic engine,
            # signed genesis contract and strict event reducer.
            sim.merchant_sale_wage_enabled = True
            last = db.verify(WORLD)
            for hour in CHECKPOINTS:
                last = sim.advance(
                    WORLD, seconds=hour * HOUR - last.time,
                    command_id=f"real-merchant-commission-ab:{hour}",
                    expected_revision=last.revision,
                ).state
                conserve_diverse(last)
                assert db.verify(WORLD).to_dict() == last.to_dict()
                assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
                assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
                output[hour] = snapshot(last)
                if hour == 24:
                    last = FiniteWaterService(db, clock).record(
                        WORLD, "well", "fixed-external-rain-day1", 2,
                        command_id="real-attributed-source-day1",
                        expected_revision=last.revision,
                    ).state
                    conserve_diverse(last)
            assert db.snapshot(WORLD).to_dict() == last.to_dict()
        finally:
            clock.close_session(WORLD)
    with SQLiteEventStore(path) as db:
        assert db.verify(WORLD).to_dict() == last.to_dict()
        assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
    return output


def test_forged_shop_wage_is_rejected_without_earned_sale(tmp_path):
    path = tmp_path / "forgery.sqlite"
    first = seeded(path, employer_signed=True)
    with SQLiteEventStore(path) as db:
        event = DomainEvent("MarketStewardWagePaid", None,
                            "fake non-sale wage", 0,
                            {"trade_id": "nonexistent", "amount": 1})
        with pytest.raises(InvalidEvent):
            db.append(WORLD, "forged-missing-sale", first.revision, [event],
                      market_authorized=True)
        with pytest.raises(InvalidEvent):
            db.append(WORLD, "forged-no-capability", first.revision, [event])
        assert db.verify(WORLD).to_dict() == first.to_dict()
        assert audit_npc_economy(db.load(WORLD))["copper_known_total"] == 12


def test_seller_sale_commission_13npc_actual_controlled_ab(tmp_path):
    original = simulate(tmp_path / "control.sqlite", employer_signed=False)
    candidate = simulate(tmp_path / "candidate.sqlite", employer_signed=True)
    for hour in CHECKPOINTS:
        old, new = original[hour], candidate[hour]
        print("PLAY48_MERCHANT_SIGNED_EARNED_SALE_AB " +
              json.dumps({"hour": hour, "control": old, "candidate": new,
                          "delta": {metric: new[metric] - old[metric]
                                    for metric in ("merchant_earned_sales",
                                         "merchant_wallet", "hunger_100",
                                         "meals", "jobs", "food_sales")},
                          "unminted_copper_conservation": True,
                          "physical_food_water_conservation": True,
                          "sqlite_replay_and_integrity": True,
                          "release_no_go": True}, sort_keys=True), flush=True)
        assert old["merchant_earned_sales"] == 0
        assert new["merchant_earned_coins"] == new["merchant_earned_sales"]
    assert candidate[24]["merchant_earned_sales"] > 0, (
        "no authentic completed merchant sale earned any contracted coin")
