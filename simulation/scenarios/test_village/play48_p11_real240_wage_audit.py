"""P11: inspect genuine P10 h240 recovery without modifying its prior history.

Only copies the immutable SQLite artifact and advances the unchanged simulation.
Reports actual co-located employer, inherited finite contract, money, food, quotes,
cargo and recent wage receipts before proposing any new agreement.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from carlos_sim import SQLiteEventStore, TimeEngine
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.food_for_work import _available_site_food
from play48_integrated_acceptance import WORLD, HOUR, engine, metrics, conserve_diverse

SOURCE = Path("evidence/p10_h240")
OUT = Path("real240_huda_wage_audit")
HOURS = (241, 242, 244)

def facts(s):
    m=metrics(s)
    c=s.to_dict()["supply_circuits"]["huda"]
    merchant=s.market_stalls["market"]["keeper_id"]
    offers=[
        {"id":key, "posted_at":q["posted_at"], "remaining":q["remaining"],
         "price":q["unit_price"]}
        for key,q in sorted(s.market_offers.items())
        if q["site_id"]=="market" and q["status"]=="open" and q["resource"]=="food"
    ]
    return {
        "hour":s.time//HOUR,
        "huda":m["npcs"]["huda"],
        "huda_delivery_count":c["deliveries"],
        "huda_recent_grain":c.get("grain_purchase",{}).get("receipts",[])[-3:],
        "huda_current_circuit":{"index":c["index"],"next_departure":c["next_departure"],"rounds":c["rounds"],"carry":c["carry"]},
        "huda_prior_bounded_food_wages":[v for v in s.to_dict()["courier_provisions"].values() if v["courier_id"]=="huda"],
        "huda_recurring_contract":c.get("food_payroll"),
        "salma":m["npcs"][merchant],
        "market_owners_food":s.resources["market"]["food"],
        "market_unquoted_food":_available_site_food(s,"market"),
        "market_open_offers":offers,
        "bakery_food":s.resources["bakery"]["food"],
        "bakery_grain":s.resources["bakery"]["grain"],
        "bread_jobs":m["bread"],
        "total_meals":m["meals"],
        "starving":m["starving"],
        "copper":12,
    }

def main():
    paths=sorted(SOURCE.rglob("P10_hunter.sqlite"))
    assert len(paths)==1,paths
    source=paths[0]
    sh=hashlib.sha256(source.read_bytes()).hexdigest()
    OUT.mkdir(exist_ok=False)
    dest=OUT/"P11_unchanged.sqlite"
    shutil.copyfile(source,dest)
    reports={}
    with SQLiteEventStore(dest) as db:
        clock=TimeEngine(db)
        clock.open_session(WORLD)
        try:
            s=db.load(WORLD)
            assert s.time==240*HOUR and len(s.npcs)==13
            sim=engine(db,clock,reserve_trader_meal=True,deferred_market_courier_wage=True)
            for attr in (
                "merchant_food_wage_enabled","community_food_enabled",
                "cashless_relief_walk_enabled","desperate_paid_harvest_enabled",
                "deferred_bakery_grain_wage_enabled","integrated_livelihoods_enabled",
                "remember_unbought_stalls_enabled","reserve_signed_relief_offer_enabled",
                "desperate_funded_planting_enabled","hungry_paid_baker_return_enabled",
                "signed_steward_wage_quote_release_enabled",
                "offshift_steward_homeward_enabled",
                "local_emergency_courier_help_enabled",
                "hunter_well_visit_enabled",
            ):
                setattr(sim,attr,True)
            reports["240"]=facts(s)
            print("PLAY48_P11_WAGE_AUDIT "+json.dumps(reports["240"],sort_keys=True),flush=True)
            for hour in HOURS:
                s=sim.advance(WORLD,seconds=hour*HOUR-s.time,
                    command_id=f"p11-audit-{hour}",
                    expected_revision=s.revision).state
                conserve_diverse(s)
                audit=audit_npc_economy(s)
                assert audit["copper_scope_complete"] and audit["copper_known_total"]==12
                assert len(s.npcs)==13
                assert db.db.execute("PRAGMA integrity_check").fetchone()==("ok",)
                assert db.db.execute("PRAGMA foreign_key_check").fetchall()==[]
                db.snapshot(WORLD)
                reports[str(hour)]=facts(s)
                print("PLAY48_P11_WAGE_AUDIT "+json.dumps(reports[str(hour)],sort_keys=True),flush=True)
            assert db.load(WORLD).to_dict()==s.to_dict()
        finally:
            clock.close_session(WORLD)
    assert hashlib.sha256(source.read_bytes()).hexdigest()==sh
    (OUT/"audit.json").write_text(json.dumps(
        {"source_sha256":sh,"snapshots":reports,"gate":"PLAY48_NO_GO"},
        indent=2,sort_keys=True),encoding="utf8")

if __name__=="__main__":
    main()
