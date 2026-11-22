"""Read-only P7 real saved h229: discover physical courier recovery evidence.

Read saved event ledger only: no NPC action, invented money, relief, contract
or synthetic supply. Inspects own freight claims, food/copper/roads, and actual
delivery/payment timestamps before considering changes to the motor.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from carlos_sim import SQLiteEventStore
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.freight_payroll import choose_payment, waits_for_local_payment
from carlos_sim.navigation import shortest_known_route
from carlos_sim.food_for_work import _available_site_food
from play48_integrated_acceptance import WORLD, HOUR, metrics
SOURCE = Path("evidence/real229")
OUT = Path("real229_courier_diagnostics")


def main():
    files = sorted(SOURCE.rglob("P7_signed_steward_wage.sqlite"))
    assert len(files) == 1, files
    file = files[0]
    sha = hashlib.sha256(file.read_bytes()).hexdigest()
    OUT.mkdir(exist_ok=False)
    with SQLiteEventStore(file) as db:
        s = db.load(WORLD)
        assert s.time == 229 * HOUR and len(s.npcs) == 13
        assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
        cash = audit_npc_economy(s)
        assert cash["copper_scope_complete"] and cash["copper_known_total"] == 12
        plain = s.to_dict()  # Unfreeze nested snapshot-projected mappingproxy records.
        couriers = {}
        for who, circuit in sorted(s.supply_circuits.items()):
            contract = plain["supply_circuits"][who].get("food_payroll")
            receipts = contract["receipts"] if contract else []
            nav = s.navigation.get(who, {})
            meals = sorted(
                (m["consumed_at"] for m in s.consumptions.values()
                 if m["npc_id"] == who))
            arrived = sorted(
                ((t["arrived_at"], t["destination"]) for t in s.travels.values()
                 if t["npc_id"] == who and t["status"] == "arrived"))
            couriers[who] = {
                "site": s.entities[who]["location_id"],
                "need": dict(s.npcs[who]["needs"]),
                "food": s.resources[who].get("food"),
                "copper": s.resources[who].get("coin_copper"),
                "contract": dict(contract) if contract else None,
                "food_payable_here": choose_payment(s, who),
                "waits_for_local_payment": waits_for_local_payment(s, who),
                "deliveries": circuit["deliveries"],
                "rounds": circuit["rounds"],
                "index": circuit["index"],
                "last_meals": meals[-5:],
                "last_arrivals": arrived[-8:],
                "known_routes": len(nav.get("known_routes", [])),
                "known_to_market": list(shortest_known_route(s, who, "market")),
                "known_to_bakery": list(shortest_known_route(s, who, "bakery")),
            }
        candidates = []
        for who, npc in sorted(s.npcs.items()):
            food = s.resources.get(who, {}).get("food", 0)
            if food <= 0:
                continue
            nav = s.navigation.get(who, {})
            candidates.append({
                "id": who, "role": npc["role"],
                "site": s.entities[who]["location_id"],
                "food": food, "coin": s.resources.get(who, {}).get("coin_copper", 0),
                "need": dict(npc["needs"]),
                "known_to_well": list(shortest_known_route(s, who, "well")),
                "nav_routes": len(nav.get("known_routes", [])),
            })
        stocks = {
            place: {
                "food": stock.get("food", 0),
                "unquoted_food": _available_site_food(s, place),
                "copper": stock.get("coin_copper", 0),
                "route_to_well": sorted([
                    {"route_id": rid, "seconds": road["seconds"]}
                    for rid, road in s.routes.items() if "well" in (road["a"], road["b"])
                    and place in (road["a"], road["b"])], key=lambda v: v["route_id"]),
            } for place, stock in s.resources.items()
            if place in s.locations and (stock.get("food", 0) or stock.get("coin_copper", 0))
        }
        report = {
            "hour": 229, "source_sha256": sha,
            "metrics": metrics(s), "money_by_owner": cash["copper_known_by_owner"],
            "couriers": couriers, "personally_fed_workers": candidates,
            "physical_site_stocks": stocks,
            "all_well_roads": {
                rid: dict(road) for rid, road in s.routes.items()
                if "well" in (road["a"], road["b"])
            },
        }
        print("PLAY48_REAL229_COURIER_FOOD_DIAG " + json.dumps(
            {k: v for k, v in report.items() if k != "metrics"},
            sort_keys=True), flush=True)
    assert hashlib.sha256(file.read_bytes()).hexdigest() == sha
    (OUT / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True), encoding="utf8")


if __name__ == "__main__":
    main()
