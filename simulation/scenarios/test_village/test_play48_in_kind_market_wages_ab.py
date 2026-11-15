"""PLAY48 physical food-paid shopkeeper: true 13-NPC A/B source h6-48.

This comparison does not use arbitrary distributions: same original
source, real time, same 12 copper, routes, employment and events.
Only signed genesis shop food-wage contract and engine opt-in differ.
"""
from __future__ import annotations
import json
from pathlib import Path
import pytest
from carlos_sim import DomainEvent, SQLiteEventStore, TimeEngine
from carlos_sim.store import InvalidEvent
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.food_for_work import _available_site_food
from carlos_sim.hydrology import FiniteWaterService
from test_play38_multi_farm_couriers import WORLD
from test_play48_deferred_courier_market_income import signed_genesis
from test_play48_real_watch_income_24h import engine as original_engine, HOUR
from test_play48_finite_hunt_fish_roads import conserve_diverse

CHECKPOINTS = (6, 24, 30, 36, 48, 72, 96, 120, 144, 168)


def seeded(path: Path, *, contract: bool):
    state = signed_genesis(path)
    if contract:
        with SQLiteEventStore(path) as db:
            state = db.append(WORLD, "sign-authentic-market-food-payroll",
                state.revision, [DomainEvent("MarketStewardFoodContractSigned", None,
                    "trusted market owner and on-site keeper sign food wage at genesis",
                    0, {"site_id": "market", "keeper_id": "salma",
                        "sales_per_wage": 2})], bootstrap=True)
            assert db.verify(WORLD).to_dict() == state.to_dict()
    assert (state.schema_version, state.rules_version) == (45, 65)
    assert len(state.npcs) == 13
    assert audit_npc_economy(state)["copper_known_total"] == 12
    conserve_diverse(state)
    return state


def report(state):
    untouched = state.to_dict()
    cash = audit_npc_economy(state)
    assert cash["copper_scope_complete"] and cash["copper_known_total"] == 12
    payments = [(k, v["steward_food_wage"]) for k, v
                in state.market_trades.items() if "steward_food_wage" in v]
    assert all(v["worker_id"] == "salma" and v["site_id"] == "market"
               and v["amount"] == 1 for _, v in payments)
    view = {
        "hour": state.time // HOUR,
        "npcs": len(state.npcs),
        "cash_total": cash["copper_known_total"],
        "market_cash": state.resources["market"].get("coin_copper"),
        "owners_with_copper": {who: amount for who, amount in
            cash["copper_known_by_owner"].items() if amount > 0},
        "starving_ids": [
            who for who in sorted(state.npcs)
            if state.npcs[who]["needs"]["hunger"] == 100
        ],
        "professional_jobs": {
            role: sum(job["status"] == "completed" and
                      state.npcs[job["npc_id"]]["role"] == role
                      for job in state.production_jobs.values())
            for role in sorted({n["role"] for n in state.npcs.values()})
        },
        "market_trades_by_resource": {
            resource: sum(t["resource"] == resource
                          for t in state.market_trades.values())
            for resource in sorted({t["resource"] for t in state.market_trades.values()})
        },
        "personal_food_owners": {
            who: state.resources[who]["food"] for who in sorted(state.npcs)
            if state.resources[who].get("food", 0) > 0
        },
        "market_food": state.resources["market"].get("food"),
        "market_unpromised_food": _available_site_food(state, "market"),
        "market_open_food_quotes": sum(
            q["remaining"] for q in state.market_offers.values()
            if q["status"] == "open" and q["site_id"] == "market"
            and q["resource"] == "food"),
        "salma_earned_site_food": len(payments),
        "salma_food_owned": state.resources["salma"].get("food"),
        "salma_coin_owned": state.resources["salma"].get("coin_copper"),
        "salma_meals": sum(x["npc_id"] == "salma" for x in state.consumptions.values()),
        "salma_hunger": state.npcs["salma"]["needs"]["hunger"],
        "huda_hunger": state.npcs["huda"]["needs"]["hunger"],
        "meals": len(state.consumptions),
        "food_sales": sum(x["resource"] == "food" for x in state.market_trades.values()),
        "jobs": sum(x["status"] == "completed" for x in state.production_jobs.values()),
        "hunger100": sum(x["needs"]["hunger"] == 100 for x in state.npcs.values()),
        "deliveries": {
            who: state.supply_circuits[who]["deliveries"] for who in ("hana", "huda")
        },
        "courier_food_wages": {
            who: sum(len(c["payments"]) for c in state.courier_provisions.values()
                     if c["courier_id"] == who)
            for who in ("hana", "huda")
        },
    }
    assert state.to_dict() == untouched
    return view


def simulate(path: Path, *, contract: bool):
    original = seeded(path, contract=contract)
    result = {}
    with SQLiteEventStore(path) as db:
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            engine = original_engine(
                db, clock, reserve_trader_meal=True,
                deferred_market_courier_wage=True)
            engine.merchant_food_wage_enabled = contract
            last = db.verify(WORLD)
            for hour in CHECKPOINTS:
                last = engine.advance(
                    WORLD, seconds=hour * HOUR - last.time,
                    command_id=f"shop-food-commission-ab-{hour}",
                    expected_revision=last.revision).state
                conserve_diverse(last)
                assert db.verify(WORLD).to_dict() == last.to_dict()
                assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
                assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
                result[hour] = report(last)
                if hour in (24, 48, 72, 96, 120, 144):
                    last = FiniteWaterService(db, clock).record(
                        WORLD, "well", f"fixed-external-rain-day{hour//24}", 2,
                        command_id=f"real-attributed-source-day{hour//24}",
                        expected_revision=last.revision).state
                    conserve_diverse(last)
            assert db.snapshot(WORLD).to_dict() == last.to_dict()
        finally:
            clock.close_session(WORLD)
    with SQLiteEventStore(path) as db:
        assert db.verify(WORLD).to_dict() == last.to_dict()
        assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
    return result


def test_forged_market_food_wage_no_completed_sale(tmp_path):
    path = tmp_path / "invalid-before-sales.sqlite"
    s = seeded(path, contract=True)
    with SQLiteEventStore(path) as db:
        fake = DomainEvent("MarketStewardFoodWagePaid", None,
            "forged wage must be rejected", 0,
            {"site_id": "market", "trade_id": "missing-real-sale", "amount": 1})
        with pytest.raises(InvalidEvent):
            db.append(WORLD, "forgery", s.revision, [fake],
                      market_authorized=True)
        with pytest.raises(InvalidEvent):
            db.append(WORLD, "no-capability", s.revision, [fake])
        assert db.verify(WORLD).to_dict() == s.to_dict()


def test_real_13npc_signed_food_sales_before_starvation_ab(tmp_path):
    orig_path = tmp_path / "control.sqlite"
    candidate_path = tmp_path / "candidate.sqlite"
    baseline = simulate(orig_path, contract=False)
    candidate = simulate(candidate_path, contract=True)
    for hour in CHECKPOINTS:
        old, new = baseline[hour], candidate[hour]
        print("PLAY48_IN_KIND_MERCHANT_13NPC_AB " + json.dumps({
            "hour": hour, "control": old, "candidate": new,
            "meals_delta": new["meals"] - old["meals"],
            "sales_delta": new["food_sales"] - old["food_sales"],
            "hunger100_delta": new["hunger100"] - old["hunger100"],
            "supply_delivery_delta": {
                who: new["deliveries"][who] - old["deliveries"][who]
                for who in old["deliveries"]
            },
            "physical_cash_food_water_conservation": True,
            "sqlite_replay_and_integrity": True,
            "release_no_go": True,
        }, sort_keys=True), flush=True)
        assert old["salma_earned_site_food"] == 0
        assert old["cash_total"] == new["cash_total"] == 12
    # This extended A/B additionally records genuine labor and goods across
    # actual existing farm, mine, kiln, smith, hunting, fishing and trade jobs.
    # More jobs or merchants are NOT invented: measure which existing trades
    # connect actual wages to personal food at days 3, 4 and 7.
    # Guard both livelihoods: a real seller meal must help the shopkeeper,
    # WITHOUT impairing the original freight or actual buyer access.
    assert candidate[36]["salma_earned_site_food"] >= 1, (
        "no genuine two-sale funded shop food wage before h36")
    assert candidate[48]["salma_meals"] > baseline[48]["salma_meals"], (
        "shopkeeper did not eat earned physical food")
    assert candidate[48]["salma_hunger"] < baseline[48]["salma_hunger"], (
        "shopkeeper hunger did not improve from real wages")
    for hour in (30, 36, 48):
        assert candidate[hour]["food_sales"] >= baseline[hour]["food_sales"]
        assert candidate[hour]["meals"] >= baseline[hour]["meals"]
        for courier in ("hana", "huda"):
            assert (candidate[hour]["deliveries"][courier]
                    >= baseline[hour]["deliveries"][courier]), (
                "true freight must not be reduced to feed the merchant")
    for hour in (72, 96, 120, 144, 168):
        assert candidate[hour]["cash_total"] == baseline[hour]["cash_total"] == 12
    with SQLiteEventStore(candidate_path) as db:
        state = db.verify(WORLD)
        paid_ids = [key for key, trade in state.market_trades.items()
                    if "steward_food_wage" in trade]
        assert paid_ids, "must have a real persisted signed wage receipt"
        fake_repeat = DomainEvent("MarketStewardFoodWagePaid", None,
            "duplicate receipt must not pay again", state.time,
            {"site_id": "market", "trade_id": paid_ids[0], "amount": 1})
        with pytest.raises(InvalidEvent):
            db.append(WORLD, "duplicate-steward-wage", state.revision,
                      [fake_repeat], market_authorized=True)
        assert db.verify(WORLD).to_dict() == state.to_dict()
