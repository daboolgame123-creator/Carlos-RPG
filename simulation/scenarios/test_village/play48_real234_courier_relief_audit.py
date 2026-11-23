"""Read-only forensic audit of REAL P7 saved h234 economic and physical rescue paths.

Auditor may inspect complete world; no omniscience is granted to NPCs.
Source SQLite SHA is checked before and after. No world events are appended.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from carlos_sim import SQLiteEventStore
from carlos_sim.navigation import shortest_known_route
from carlos_sim.community_food import choose_market_ration, signed_local_relief_quote_capacity
from carlos_sim.steward_food_payroll import choose_steward_food_wage
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.food_for_work import _available_site_food
from play48_integrated_acceptance import WORLD, HOUR, metrics

SOURCE = Path("evidence/authentic234")


def main() -> None:
    matches = sorted(SOURCE.rglob("P7_signed_wage.sqlite"))
    assert len(matches) == 1, matches
    source = matches[0]
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    with SQLiteEventStore(source) as db:
        state = db.load(WORLD)
        assert state.time == 234 * HOUR and len(state.npcs) == 13
        assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert not db.db.execute("PRAGMA foreign_key_check").fetchall()
        economy = audit_npc_economy(state)
        assert economy["copper_scope_complete"] and economy["copper_known_total"] == 12
        residents = {}
        for who, npc in sorted(state.npcs.items()):
            loc = state.entities[who]["location_id"]
            nav = state.navigation.get(who)
            path = shortest_known_route(state, who, "well") if loc != "well" else ()
            owned = state.resources.get(who, {})
            residents[who] = {
                "role": npc["role"], "site": loc, "hunger": npc["needs"]["hunger"],
                "fatigue": npc["needs"]["fatigue"], "safety": npc["needs"]["safety"],
                "food": owned.get("food", 0), "coin": owned.get("coin_copper", 0),
                "known_road_to_well": list(path) if path else [],
                "visited_well": bool(nav and "well" in nav["visited"]),
            }
        offers = [{
            "id": i, "site": o["site_id"], "owner": o["stock_owner_id"],
            "resource": o["resource"], "price": o["unit_price"],
            "remaining": o["remaining"], "posted_at": o["posted_at"],
        } for i, o in sorted(state.market_offers.items()) if o["status"] == "open"]
        relief = state.market_stalls["market"].get("community_food", {})
        days = {}
        for rec in relief.get("payments", []):
            day = rec["paid_at"] // (24 * HOUR)
            days[day] = days.get(day, 0) + 1
        materials = {
            site: dict(stock) for site, stock in sorted(state.resources.items())
            if site in state.locations and any(v for v in stock.values())
        }
        obligations = [{
            "id": oid, "requester": o["requester"], "provider": o["provider"],
            "resource": o["resource"], "status": o["status"],
            "site": o["location_id"], "created_at": o["created_at"],
        } for oid, o in state.obligations.items() if o["status"] in ("requested", "promised")]
        layla_trip = sorted([
            {"id": ident, "origin": trip["origin"],
             "destination": trip["destination"], "route_id": trip["route_id"],
             "arrived_at": trip.get("arrived_at")}
            for ident, trip in state.travels.items()
            if trip["npc_id"] == "layla" and trip["status"] == "arrived"
        ], key=lambda row: (row["arrived_at"], row["id"]))
        fisher_home = state.npc_routines["layla"]["home_id"]
        homeward = shortest_known_route(state, "layla", fisher_home)
        report = {
            "fisher_return_diagnostics": {
                "home": fisher_home, "routine": dict(state.npc_routines["layla"]),
                "known_routes": list(state.navigation["layla"]["known_routes"]),
                "visited": list(state.navigation["layla"]["visited"]),
                "home_path_known": list(homeward) if homeward else [],
                "last_five_arrivals": layla_trip[-5:],
                "known_contacts": dict(state.relations.get("layla", {})),
                "fisher_help_requesters": {
                    who: state.relations.get(who, {}).get("layla", 0)
                    for who in ("hana", "huda")
                },
            },
            "source_sha256": digest, "time": state.time,
            "summary": {k: metrics(state)[k] for k in ("bread", "meals", "starving", "cash_wages")},
            "residents": residents, "site_resources": materials, "open_offers": offers,
            "relief_by_day": days,
            "relief_limit": relief.get("daily_limit"),
            "relief_now": choose_market_ration(state),
            "relief_quote_capacity": signed_local_relief_quote_capacity(state),
            "merchant_earned_food_wage_now": choose_steward_food_wage(state, "market"),
            "market_available_unquoted_food": _available_site_food(state, "market"),
            "well_available_unquoted_food": _available_site_food(state, "well"),
            "unsatisfied_person_to_person_requests": obligations,
            "couriers": {
                who: {
                    "current": state.entities[who]["location_id"],
                    "hunger": state.npcs[who]["needs"]["hunger"],
                    "stops": list(c["stops"]), "index": c["index"],
                    "deliveries": c["deliveries"],
                } for who,c in sorted(state.supply_circuits.items())
            },
        }
        print("PLAY48_REAL234_COURIER_RESCUE_AUDIT " + json.dumps(report, sort_keys=True), flush=True)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == digest, "auditor modified saved source"


if __name__ == "__main__":
    main()
