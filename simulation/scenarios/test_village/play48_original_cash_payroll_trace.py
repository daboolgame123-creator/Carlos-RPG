"""PLAY-48 original 13-person cash, wages and food access BEFORE freight dies.

Diagnose a SOURCE-PINNED actual 13-NPC economy. No interventions, gifts,
production overrides, jobs, ownership edits, made-up payroll or score tuning.
Use the exact original seed/engine and weather from the PR107 h72 proof.
"""
from __future__ import annotations

import json
from pathlib import Path

from carlos_sim import SQLiteEventStore, TimeEngine
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.food_access_diagnostics import audit_food_access_barriers
from carlos_sim.hydrology import FiniteWaterService
from test_play38_multi_farm_couriers import WORLD
from test_play48_deferred_courier_market_income import signed_genesis
from test_play48_real_watch_income_24h import engine, HOUR
from test_play48_finite_hunt_fish_roads import conserve_diverse

CHECKPOINT_HOURS = (24, 30, 36)


def payroll_flow(state):
    before = state.to_dict()
    economy = audit_npc_economy(state)
    food = audit_food_access_barriers(state)
    assert economy["copper_scope_complete"]
    assert economy["copper_known_total"] == 12
    assert len(state.npcs) == food["npc_count"] == 13

    # Owners, not apparent locations, hold the copper. Treat missing cash as
    # UNKNOWN, never as someone else's wallet or as automatically spendable.
    wallets = {owner: amount for owner, amount in
               economy["copper_known_by_owner"].items() if amount > 0}
    site_coins = {owner: amount for owner, amount in sorted(wallets.items())
                  if owner in state.locations}
    personal_coins = {owner: amount for owner, amount in sorted(wallets.items())
                      if owner in state.npcs}
    other_coins = {owner: amount for owner, amount in sorted(wallets.items())
                   if owner not in state.locations and owner not in state.npcs}

    # Distinguish genuine signed but unpaid contracts from work that NEVER
    # promised wages, and never label the latter as unpaid salary obligations.
    paid_cash = 0
    paid_food = 0
    signed_unpaid = []
    work_without_contract = {}
    for job_id, job in sorted(state.production_jobs.items()):
        if job["status"] != "completed":
            continue
        who, site = job["npc_id"], job["site_id"]
        terms = state.production_recipes[job["recipe_id"]]
        if "work_wage" in job:
            paid_cash += 1
        if "food_wage" in job:
            paid_food += 1
        wage_type = ("coin_copper" if "wage_coin" in terms else
                     "food" if "wage_food" in terms else None)
        if wage_type is None:
            work_without_contract[who] = work_without_contract.get(who, 0) + 1
        elif ("work_wage" not in job and "food_wage" not in job):
            signed_unpaid.append({
                "job": job_id, "worker": who, "site": site,
                "wage_resource": wage_type,
                "wage_due": terms["wage_coin"] if wage_type == "coin_copper"
                    else terms["wage_food"],
                "site_available": state.resources.get(site, {}).get(wage_type),
                "worker_at_site": state.entities[who]["location_id"] == site,
            })

    # Distinguish actual seller work and location-owned shop revenue from a
    # merchant's private purse; prior sales do not make site funds personal.
    seller_trade_counts = {}
    seller_trade_value = {}
    owner_trade_value = {}
    for trade in state.market_trades.values():
        seller = trade["seller_id"]
        owner = trade["stock_owner_id"]
        seller_trade_counts[seller] = seller_trade_counts.get(seller, 0) + 1
        if trade["payment_resource"] == "coin_copper":
            seller_trade_value[seller] = (
                seller_trade_value.get(seller, 0) + trade["total_paid"])
            owner_trade_value[owner] = (
                owner_trade_value.get(owner, 0) + trade["total_paid"])

    couriers = {
        who: {
            "deliveries": state.supply_circuits[who]["deliveries"],
            "own_copper": state.resources[who].get("coin_copper"),
            "own_food": state.resources[who].get("food"),
            "hunger": state.npcs[who]["needs"]["hunger"],
            "at": state.entities[who]["location_id"],
            "completed_paid_food_services": sum(
                len(contract["payments"]) for contract in
                state.courier_provisions.values()
                if contract["courier_id"] == who
            ),
        } for who in ("hana", "huda")
    }
    merchant = state.npcs["salma"]
    market = {
        "keeper_hunger": merchant["needs"]["hunger"],
        "keeper_copper": state.resources["salma"].get("coin_copper"),
        "keeper_food": state.resources["salma"].get("food"),
        "owner_copper": state.resources["market"].get("coin_copper"),
        "owner_food": state.resources["market"].get("food"),
        "food_quoted": sum(
            offer["remaining"] for offer in state.market_offers.values()
            if offer["status"] == "open" and offer["site_id"] == "market"
            and offer["resource"] == "food"
        ),
        "merchant_executed_sales": seller_trade_counts.get("salma", 0),
        "merchant_buyer_payments_to_site": seller_trade_value.get("salma", 0),
    }
    hungry = [{
        "id": who, "hunger": state.npcs[who]["needs"]["hunger"],
        "location": state.entities[who]["location_id"],
        "cash": state.resources[who].get("coin_copper"),
        "food": state.resources[who].get("food"),
        "jobs_completed": sum(
            job["npc_id"] == who and job["status"] == "completed"
            for job in state.production_jobs.values()
        ),
    } for who in sorted(state.npcs)
       if state.npcs[who]["needs"]["hunger"] >= 75]

    report = {
        "hour": state.time // HOUR,
        "original_npcs": len(state.npcs),
        "physical_copper_total": 12,
        "site_coins": site_coins,
        "personal_coins": personal_coins,
        "other_coins": other_coins,
        "site_sale_copper_receipts": dict(sorted(owner_trade_value.items())),
        "seller_handled_sale_copper": dict(sorted(seller_trade_value.items())),
        "completed_production_jobs": economy["completed_jobs"],
        "paid_cash_jobs": paid_cash,
        "paid_food_jobs": paid_food,
        "signed_but_unpaid_jobs": signed_unpaid,
        "jobs_without_signed_salary": dict(sorted(work_without_contract.items())),
        "market": market,
        "couriers": couriers,
        "hungry_75_plus": hungry,
        "hunger_100": food["hunger_at_100"],
    }
    assert state.to_dict() == before, "operator diagnostic must be read-only"
    return report


def run(path: Path):
    original = signed_genesis(path)
    assert len(original.npcs) == 13
    assert audit_npc_economy(original)["copper_known_total"] == 12
    with SQLiteEventStore(path) as db:
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            sim = engine(db, clock, reserve_trader_meal=True,
                         deferred_market_courier_wage=True)
            rain = FiniteWaterService(db, clock)
            last = db.verify(WORLD)
            for hour in CHECKPOINT_HOURS:
                last = sim.advance(
                    WORLD, seconds=hour * HOUR - last.time,
                    command_id=f"source-real-payroll-audit:{hour}",
                    expected_revision=last.revision,
                ).state
                assert last.time == hour * HOUR
                conserve_diverse(last)
                assert db.verify(WORLD).to_dict() == last.to_dict()
                assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
                assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
                print("PLAY48_ORIGINAL_PHYSICAL_PAYROLL_FLOW " +
                      json.dumps(payroll_flow(last), sort_keys=True), flush=True)
                if hour == 24:
                    last = rain.record(
                        WORLD, "well", "fixed-external-rain-day1", 2,
                        command_id="real-attributed-source-day1",
                        expected_revision=last.revision,
                    ).state
                    conserve_diverse(last)
                    assert db.verify(WORLD).to_dict() == last.to_dict()
            assert db.snapshot(WORLD).to_dict() == last.to_dict()
        finally:
            clock.close_session(WORLD)
    with SQLiteEventStore(path) as db:
        assert db.verify(WORLD).to_dict() == last.to_dict()
        assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
    return True


def test_original_13_npc_payroll_flow_read_only(tmp_path):
    assert run(tmp_path / "original-physical-payroll-flow.sqlite")


if __name__ == "__main__":
    import tempfile
    with tempfile.TemporaryDirectory() as directory:
        run(Path(directory) / "original-physical-payroll-flow.sqlite")
