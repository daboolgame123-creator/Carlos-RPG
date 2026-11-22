"""P8 authentic saved P7 h229 voluntary fisher well-food A/B.

No new money, food, contracts, actors, water or shortcuts. Real fisher
personally travels known road, then uses unchanged 01-J physically signed
request/accept/fulfill receipts. A/B both start from EXACT same event ledger.
"""
from __future__ import annotations
import hashlib
import json
import shutil
from pathlib import Path
from carlos_sim import SQLiteEventStore, TimeEngine
from carlos_sim.economic_diagnostics import audit_npc_economy
from play48_integrated_acceptance import WORLD, HOUR, engine, metrics, conserve_diverse

SOURCE = Path("evidence/real229")
OUT = Path("real229_well_food_recovery")
HOURS = (230, 232, 236)


def info(s, arm):
    m = metrics(s)
    return {
        "arm": arm, "hour": s.time // HOUR, "total_copper": 12,
        "bread": m["bread"], "meals": m["meals"],
        "hungry100": m["starving"], "sales": m["sales"],
        "deliveries": m["deliveries"],
        "freight_wages": m["freight_wages"],
        "local_food_help": sum(o["status"] == "fulfilled" and
            o["location_id"] == "well" and o["resource"] == "food"
            for o in s.obligations.values()),
        "local_food_requests": sum(o["location_id"] == "well" and o["resource"] == "food"
            for o in s.obligations.values()),
        "hana": m["npcs"]["hana"],
        "huda": m["npcs"]["huda"],
        "layla": m["npcs"]["layla"],
        "well_food": s.resources["well"].get("food"),
        "market_food": s.resources["market"]["food"],
    }


def run_arm(source, arm, volunteer):
    target = OUT / (arm + ".sqlite")
    shutil.copyfile(source, target)
    assert hashlib.sha256(target.read_bytes()).digest() == hashlib.sha256(source.read_bytes()).digest()
    reports = {}
    with SQLiteEventStore(target) as db:
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            s = db.load(WORLD)
            assert s.time == 229 * HOUR and len(s.npcs) == 13
            assert audit_npc_economy(s)["copper_known_total"] == 12
            sim = engine(db, clock, reserve_trader_meal=True,
                         deferred_market_courier_wage=True)
            sim.merchant_food_wage_enabled = True
            sim.community_food_enabled = True
            sim.cashless_relief_walk_enabled = True
            sim.desperate_paid_harvest_enabled = True
            sim.deferred_bakery_grain_wage_enabled = True
            sim.integrated_livelihoods_enabled = True
            sim.remember_unbought_stalls_enabled = True
            sim.reserve_signed_relief_offer_enabled = True
            sim.desperate_funded_planting_enabled = True
            sim.hungry_paid_baker_return_enabled = True
            sim.signed_steward_wage_quote_rescue_enabled = True
            sim.voluntary_well_food_visit_enabled = volunteer
            for hour in HOURS:
                s = sim.advance(WORLD, seconds=hour * HOUR - s.time,
                                command_id=f"real229-well-{arm}-{hour}",
                                expected_revision=s.revision).state
                assert s.time == hour * HOUR and len(s.npcs) == 13
                conserve_diverse(s)
                money = audit_npc_economy(s)
                assert money["copper_scope_complete"] and money["copper_known_total"] == 12
                assert db.db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
                assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
                db.snapshot(WORLD)
                assert db.load(WORLD).to_dict() == s.to_dict()
                reports[str(hour)] = info(s, arm)
                print("PLAY48_REAL229_WELL_FOOD " + json.dumps(
                    reports[str(hour)], sort_keys=True), flush=True)
        finally:
            clock.close_session(WORLD)
    (OUT / (arm + "-report.json")).write_text(
        json.dumps(reports, indent=2, sort_keys=True), encoding="utf8")
    return reports


def main():
    matches = sorted(SOURCE.rglob("P7_signed_steward_wage.sqlite"))
    assert len(matches) == 1, matches
    source = matches[0]
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    OUT.mkdir(exist_ok=False)
    control = run_arm(source, "P7_control", False)
    candidate = run_arm(source, "P8_voluntary_neighbor_well", True)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before
    delta = {}
    for hour in HOURS:
        a, b = control[str(hour)], candidate[str(hour)]
        delta[str(hour)] = {
            "hour": hour, "new_genuine_well_food_help":
                b["local_food_help"] - a["local_food_help"],
            "hana_deliveries": b["deliveries"]["hana"] - a["deliveries"]["hana"],
            "huda_deliveries": b["deliveries"]["huda"] - a["deliveries"]["huda"],
            "meals": b["meals"] - a["meals"],
            "hungry100": b["hungry100"] - a["hungry100"],
            "same_start_sha256": before,
            "conserved_copper": 12, "release_gate": "PLAY48_NO_GO",
        }
        print("PLAY48_P8_MINUS_P7 " + json.dumps(delta[str(hour)], sort_keys=True), flush=True)
    (OUT / "comparison.json").write_text(json.dumps(
        {"control": control, "candidate": candidate, "delta": delta},
        indent=2, sort_keys=True), encoding="utf8")


if __name__ == "__main__":
    main()
