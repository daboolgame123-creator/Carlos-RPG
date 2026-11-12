"""PLAY48: audit genuine unpaid finished jobs, without changing world decisions.

Operator-only forensic at 24/48/72/96h, on the authenticated 13-NPC
candidate genesis with previously tested six-hour market-revisit enabled.
No invented employer funds, wages, new actors, relocated labor, resources,
market knowledge, events, changed hunger or starvation gates.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from carlos_sim import SQLiteEventStore
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.production import choose_local_production_wage
from test_play48aa_actual_barter_bread_return import _seed_signed_share
from test_play48h3_early_market_wage import _conserve, _run
from test_play48_13npc_post72_relay import _stats
from test_play47_closure_endurance import WORLD

HOUR = 3600
CHECKPOINTS = (24, 48, 72, 96)


def _active(state, who):
    return {
        "active_travel": any(
            x["npc_id"] == who and x["status"] == "traveling"
            for x in state.travels.values()),
        "active_action": any(
            x["npc_id"] == who and x["status"] == "running"
            for x in state.actions.values()),
        "active_production": any(
            x["npc_id"] == who and x["status"] == "running"
            for x in state.production_jobs.values()),
    }


def classify_job(state, ident, job):
    assert job["status"] == "completed"
    assert "work_wage" not in job
    rec = state.production_recipes[job["recipe_id"]]
    who, site = job["npc_id"], job["site_id"]
    wage = rec.get("wage_coin")
    employer = state.resources.get(site, {}).get("coin_copper")
    worker = state.resources.get(who, {}).get("coin_copper")
    at_site = state.entities[who]["location_id"] == site
    busy = _active(state, who)
    blockers = []
    if wage is None:
        blockers.append("no_contracted_coin_wage")
    else:
        if type(employer) is not int:
            blockers.append("employer_cash_uninitialized")
        elif employer < wage:
            blockers.append("employer_cash_insufficient")
        if type(worker) is not int:
            blockers.append("worker_cash_uninitialized")
    if not at_site:
        blockers.append("worker_absent_from_contract_site")
    blockers.extend(k for k, active in busy.items() if active)
    eligible = choose_local_production_wage(state, ident)
    if eligible is not None:
        assert not blockers and eligible == wage
    elif not blockers:
        blockers.append("other_rule_gate_needs_investigation")
    return {
        "job": ident, "worker": who, "role": state.npcs[who]["role"],
        "site": site, "recipe": job["recipe_id"],
        "finished_at": job["finished_at"],
        "wage_contract_coin": wage, "employer_current_coin": employer,
        "worker_current_coin": worker,
        "worker_location_now": state.entities[who]["location_id"],
        "worker_onsite_now": at_site,
        "busy": busy,
        "payable_this_tick": eligible is not None,
        "blockers": blockers,
    }


def audit_unpaid_jobs(state):
    before = state.to_dict()
    assert (len(state.npcs), state.schema_version, state.rules_version) == (13, 45, 62)
    accounts = audit_npc_economy(state)
    assert accounts["copper_scope_complete"]
    assert accounts["copper_known_total"] == 12
    all_jobs = state.production_jobs
    unpaid = [
        classify_job(state, ident, job)
        for ident, job in sorted(all_jobs.items())
        if job["status"] == "completed" and "work_wage" not in job
    ]
    paid_jobs = [
        job for job in all_jobs.values()
        if job["status"] == "completed" and "work_wage" in job
    ]
    assert len(unpaid) == accounts["completed_without_wage_receipt"]
    assert len(paid_jobs) == accounts["wage_receipts"]
    employer_sales = defaultdict(int)
    sales_receipts = defaultdict(int)
    for trade in state.market_trades.values():
        site = trade["stock_owner_id"]
        employer_sales[site] += trade["total_paid"]
        sales_receipts[site] += 1
    by_site = {}
    for job in unpaid:
        site = job["site"]
        line = by_site.setdefault(site, {
            "unpaid_jobs": 0, "contracted_unpaid_coin": 0,
            "jobs_with_no_coin_wage": 0,
        })
        line["unpaid_jobs"] += 1
        if type(job["wage_contract_coin"]) is int:
            line["contracted_unpaid_coin"] += job["wage_contract_coin"]
        else:
            line["jobs_with_no_coin_wage"] += 1
    for site, row in by_site.items():
        row["current_site_coin"] = state.resources.get(site, {}).get("coin_copper")
        row["genuine_market_sale_receipts"] = sales_receipts[site]
        row["genuine_market_copper_received_to_date"] = employer_sales[site]
    blocker_counts = Counter(
        reason for job in unpaid for reason in job["blockers"]
    )
    results = {
        "hour": state.time // HOUR,
        "sim_time": state.time,
        "stats": _stats(state),
        "copper_known_total": accounts["copper_known_total"],
        "completed_unpaid_jobs": len(unpaid),
        "completed_paid_jobs": len(paid_jobs),
        "unpaid_blockers_not_mutually_exclusive": dict(sorted(blocker_counts.items())),
        "unpaid_by_site": dict(sorted(by_site.items())),
        "individual_unpaid_jobs": unpaid,
    }
    assert state.to_dict() == before, "operator audit must never change world"
    return results


def main():
    with TemporaryDirectory(prefix="play48-wage-forensics-") as root:
        path = Path(root) / "authentic-13npc.sqlite"
        original = _seed_signed_share(path, share=True, farm_refill_authority=True)
        assert len(original.npcs) == 13
        for hour in CHECKPOINTS:
            state, _ = _run(
                path, hour * HOUR, early=True,
                hungry_woodcutter_work_enabled=True,
                retry_known_supplier_enabled=True,
                farm_sourced_wage_refill_enabled=True,
                remember_unbought_stalls_enabled=True,
            )
            _conserve(state)
            with SQLiteEventStore(path) as store:
                assert store.verify(WORLD).to_dict() == state.to_dict()
                assert store.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
                assert store.db.execute("PRAGMA foreign_key_check").fetchall() == []
            print("PLAY48_WAGE_RECEIPTS_BY_GENUINE_JOB " +
                  json.dumps(audit_unpaid_jobs(state), sort_keys=True), flush=True)
        print("PLAY48_WAGE_FORENSICS_COMPLETE_NOT_RELEASE_APPROVAL", flush=True)


if __name__ == "__main__":
    main()
