"""PLAY48 read-only wage/income audit of the genuine 168h saved SQLite worlds.

Distinguishes no wage contract, signed unpaid wages, paid wages and zero cash
remaining after purchases. Never changes world rules or releases a gate.
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from carlos_sim import SQLiteEventStore
from carlos_sim.economic_diagnostics import audit_npc_economy, audit_production_wages
from play48_integrated_acceptance import WORLD, HOUR


def examine(path: Path, arm: str, recorded: dict) -> dict:
    # A binary comparison catches unintended writes as well as ledger replay errors.
    original_digest = sha256(path.read_bytes()).hexdigest()
    with SQLiteEventStore(path) as db:
        state = db.verify(WORLD)
        assert db.load(WORLD).to_dict() == state.to_dict()
    assert sha256(path.read_bytes()).hexdigest() == original_digest, "audit modified saved ledger"
    assert state.time == 168 * HOUR and len(state.npcs) == 13
    ownership = audit_npc_economy(state)
    assert ownership["copper_scope_complete"]
    assert ownership["copper_known_total"] == recorded["copper"] == 12
    assert ownership["copper_known_by_owner"] == recorded["copper_by_owner"]

    wages = audit_production_wages(state)
    npc_ids = set(state.npcs)
    completed = [j for j in state.production_jobs.values() if j["status"] == "completed"]
    unpaid = Counter((d["worker_id"], d["resource"]) for d in wages["unpaid_jobs"])
    personal_cash = sum(state.resources[who]["coin_copper"] for who in npc_ids)
    site_cash = sum(v for k, v in ownership["copper_known_by_owner"].items() if k not in npc_ids)
    assert personal_cash + site_cash == 12

    workers = {}
    for who, npc in sorted(state.npcs.items()):
        jobs = [j for j in completed if j["npc_id"] == who]
        courier = state.supply_circuits.get(who, {})
        receipts = courier.get("food_payroll", {}).get("receipts", [])
        provision_payments = sum(len(c["payments"]) for c in state.courier_provisions.values()
                                 if c["courier_id"] == who)
        meals = sum(c["npc_id"] == who for c in state.consumptions.values())
        purchases = sum(t["buyer_id"] == who and t["resource"] == "food"
                        for t in state.market_trades.values())
        workers[who] = {
            "role": npc["role"],
            "hunger": npc["needs"]["hunger"],
            "cash_now": state.resources[who]["coin_copper"],
            "food_now": state.resources[who]["food"],
            "meals": meals,
            "purchases": purchases,
            "completed_jobs": len(jobs),
            "paid_coin_jobs": sum("work_wage" in j for j in jobs),
            "paid_food_jobs": sum("food_wage" in j for j in jobs),
            "signed_unpaid_coin_jobs": unpaid[(who, "coin")],
            "signed_unpaid_food_jobs": unpaid[(who, "food")],
            "jobs_without_wage_contract": sum(
                "wage_coin" not in state.production_recipes[j["recipe_id"]]
                and "wage_food" not in state.production_recipes[j["recipe_id"]]
                for j in jobs
            ),
            "recurring_freight_paid": sum(r["payment"] is not None for r in receipts),
            "recurring_freight_unpaid": sum(r["payment"] is None for r in receipts),
            "provision_food_payments": provision_payments,
        }

    report = {
        "arm": arm,
        "hour": 168,
        "ledger_sha256": original_digest,
        "replay_verified": True,
        "physical_copper_total": ownership["copper_known_total"],
        "copper_in_npc_wallets_now": personal_cash,
        "copper_in_non_npc_accounts_now": site_cash,
        "non_npc_copper_owners": {k: v for k, v in ownership["copper_known_by_owner"].items()
                                  if k not in npc_ids and v},
        "bakery_grain": state.resources["bakery"].get("grain", 0),
        "market_food": state.resources["market"].get("food", 0),
        "production_wages": wages,
        "completed_jobs": len(completed),
        "workers": workers,
        "release_gate_passed": False,
        "observational_only": True,
    }
    assert len(workers) == 13
    assert report["production_wages"]["coin_paid"] == recorded["cash_wages"]
    assert sum(x["hunger"] == 100 for x in workers.values()) == recorded["starving"]
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    rows = json.loads((args.directory / "results.json").read_text(encoding="utf-8"))
    assert "168" in rows and all(arm in rows["168"] for arm in ("control", "candidate"))
    output = {arm: examine(args.directory / (arm + ".sqlite"), arm, rows["168"][arm])
              for arm in ("control", "candidate")}
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True), encoding="utf-8")
    for arm, data in output.items():
        brief = {
            "arm": arm,
            "cash_in_wallets": data["copper_in_npc_wallets_now"],
            "cash_at_sites": data["copper_in_non_npc_accounts_now"],
            "paid_coin_jobs": data["production_wages"]["coin_paid"],
            "signed_unpaid_coin_jobs": data["production_wages"]["coin_unpaid"],
            "paid_food_jobs": data["production_wages"]["food_paid"],
            "signed_unpaid_food_jobs": data["production_wages"]["food_unpaid"],
            "jobs_without_wage_contract": data["production_wages"]["without_contract"],
            "zero_cash_npcs": [who for who, r in data["workers"].items()
                               if r["cash_now"] == 0],
            "no_completed_production_jobs_npcs": [
                who for who, r in data["workers"].items() if r["completed_jobs"] == 0
            ],
            "unpaid_contracts_by_worker": {
                who: {"coin": r["signed_unpaid_coin_jobs"],
                      "food": r["signed_unpaid_food_jobs"]}
                for who, r in data["workers"].items()
                if r["signed_unpaid_coin_jobs"] or r["signed_unpaid_food_jobs"]
            },
        }
        print("PLAY48_INCOME_AUDIT " + json.dumps(brief, sort_keys=True), flush=True)
    print("PLAY48_INCOME_AUDIT_SAVED " + str(args.output), flush=True)


if __name__ == "__main__":
    main()
