"""Read-only audit: who can physically reach real surplus market at 72h?

The world is original genuine persisted candidate (13 NPC, 12 copper), not a
fabricated case. Never edit the database, change history, or infer remote NPC
knowledge. Inspector uses omniscient view for diagnosis only.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

from carlos_sim import SQLiteEventStore
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.food_for_work import _available_site_food
from carlos_sim.navigation import shortest_known_route
from play48_integrated_acceptance import WORLD, HOUR


def main() -> None:
    path = Path("evidence/candidate.sqlite")
    assert path.is_file(), "original candidate saved72 event store required"
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    with SQLiteEventStore(path) as db:
        state = db.load(WORLD)
        assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert not db.db.execute("PRAGMA foreign_key_check").fetchall()
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
    assert state.time == 72 * HOUR and len(state.npcs) == 13
    assert audit_npc_economy(state)["copper_known_total"] == 12
    market_stock = state.resources["market"]["food"]
    market_quoted = sum(
        o["remaining"] for o in state.market_offers.values()
        if o["status"] == "open"
        and o["stock_owner_id"] == "market"
        and o["resource"] == "food"
    )
    report = []
    for who, npc in sorted(state.npcs.items()):
        site = state.entities[who]["location_id"]
        nav = state.navigation.get(who, {})
        path = shortest_known_route(state, who, "market")
        recent_market_visits = [
            trip["arrived_at"] // HOUR for trip in state.travels.values()
            if trip["npc_id"] == who
            and trip["status"] == "arrived"
            and trip["destination"] == "market"
        ]
        wallet = state.resources.get(who, {})
        hunger = npc["needs"]["hunger"]
        free = not any(t["npc_id"] == who and t["status"] == "traveling"
                       for t in state.travels.values())
        busy = any(j["npc_id"] == who and j["status"] == "running"
                   for j in state.production_jobs.values())
        at_market = site == "market"
        could_walk = at_market or bool(path)
        report.append({
            "npc": who,
            "hunger": hunger,
            "hungry75": hunger >= 75,
            "starving100": hunger == 100,
            "copper": wallet.get("coin_copper"),
            "food": wallet.get("food"),
            "site": site,
            "at_market": at_market,
            "visited_market": "market" in nav.get("visited", ()),
            "personal_market_visits": len(recent_market_visits),
            "known_route_to_market": could_walk,
            "travel_seconds": sum(state.routes[r]["seconds"] for r in path) if path else 0,
            "in_transit": not free,
            "working": busy,
            "fatigue": npc["needs"]["fatigue"],
            "cashless_hungry": wallet.get("coin_copper") == 0 and hunger >= 75
                               and wallet.get("food") == 0,
        })
    print("PLAY48_ACCESS_REAL72 " + json.dumps({
        "original_db_sha256": before,
        "hour": 72,
        "market_owned_food": market_stock,
        "market_open_quoted_food": market_quoted,
        "market_unpromised_food": _available_site_food(state, "market"),
        "copper_total": 12,
        "starving100": sum(r["starving100"] for r in report),
        "hungry75": sum(r["hungry75"] for r in report),
        "cashless_hungry": sum(r["cashless_hungry"] for r in report),
        "cashless_hungry_with_known_market_road": sum(
            r["cashless_hungry"] and r["known_route_to_market"] for r in report
        ),
        "cashless_hungry_at_market": sum(
            r["cashless_hungry"] and r["at_market"] for r in report
        ),
        "npc": report, "observational_only": True,
    }, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
