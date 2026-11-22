"""Read-only audit of authentic P5 vs P6 h228 saved economic histories.

No replay, no source mutation, no gifts, no conjectural labor or currency.
Outputs deterministic explanations of local hunger, food, quotes and courier lock.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from carlos_sim import SQLiteEventStore
from carlos_sim.economic_diagnostics import audit_npc_economy, audit_production_wages
from carlos_sim.economic_autonomy import choose_local_food_purchase, choose_local_production
from carlos_sim.community_food import (
    choose_market_ration,
    choose_market_relief_quote_retirement,
    signed_local_relief_quote_capacity,
)
from carlos_sim.food_for_work import _available_site_food
from play48_integrated_acceptance import WORLD, HOUR, metrics

SOURCE = Path("evidence/authentic228")
OUT = Path("real228_income_audit")


def audit(arm: str) -> dict:
    matches = sorted(SOURCE.rglob(arm + ".sqlite"))
    assert len(matches) == 1, (arm, matches)
    source = matches[0]
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    with SQLiteEventStore(source) as db:
        state = db.load(WORLD)
        assert state.time == 228 * HOUR and len(state.npcs) == 13
        assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
        money = audit_npc_economy(state)
        assert money["copper_scope_complete"] and money["copper_known_total"] == 12
        score = metrics(state)
        wage = audit_production_wages(state)
        residents = []
        for who, npc in sorted(state.npcs.items()):
            held = state.resources.get(who, {})
            place = state.entities[who]["location_id"]
            purchase = choose_local_food_purchase(state, who)
            job = choose_local_production(
                state, who,
                agriculture_enabled=True,
                desperate_paid_harvest_enabled=True,
                desperate_funded_planting_enabled=True,
            )
            residents.append({
                "id": who, "role": npc["role"], "site": place,
                "hunger": npc["needs"]["hunger"],
                "fatigue": npc["needs"]["fatigue"],
                "coin": held.get("coin_copper", 0),
                "food": held.get("food", 0),
                "offer": purchase.offer_id if purchase else None,
                "work": job.recipe_id if job else None,
            })
        stalls = [{
            "id": ident,
            "site": offer["site_id"],
            "seller": offer["seller_id"],
            "owner": offer["stock_owner_id"],
            "resource": offer["resource"],
            "remaining": offer["remaining"],
            "price": offer["unit_price"],
        } for ident, offer in sorted(state.market_offers.items())
          if offer["status"] == "open"]
        circuits = {
            who: {
                "position": state.entities[who]["location_id"],
                "carry": circuit["carry"],
                "index": circuit["index"],
                "next_departure": circuit["next_departure"],
                "hunger": state.npcs[who]["needs"]["hunger"],
            }
            for who, circuit in sorted(state.supply_circuits.items())
        }
        relief = state.market_stalls["market"].get("community_food")
        report = {
            "arm": arm, "time": state.time, "hour": 228,
            "sha256": digest,
            "headline": {k: score[k] for k in ("bread", "meals", "sales",
                "cash_wages", "starving")},
            "copper_by_owner": {k: v for k, v in money["copper_known_by_owner"].items() if v},
            "market_stock": dict(state.resources["market"]),
            "bakery_stock": dict(state.resources["bakery"]),
            "market_available_unquoted_food": _available_site_food(state, "market"),
            "bakery_available_unquoted_food": _available_site_food(state, "bakery"),
            "open_offers": stalls,
            "market_relief": {
                "signed_daily_limit": relief["daily_limit"] if relief else None,
                "paid_receipts": len(relief["payments"]) if relief else None,
                "paid_current_day": (
                    sum(p["paid_at"] // (24 * HOUR) == state.time // (24 * HOUR)
                        for p in relief["payments"]) if relief else None),
                "recipient_now": choose_market_ration(state),
                "permitted_quote_release": choose_market_relief_quote_retirement(state),
                "quota_capacity": signed_local_relief_quote_capacity(state),
            },
            "couriers": circuits,
            "residents": residents,
            "unpaid_real_jobs": {
                k: v for k, v in wage.items() if k != "unpaid_jobs"},
        }
    assert hashlib.sha256(source.read_bytes()).hexdigest() == digest
    return report


def main() -> None:
    OUT.mkdir(exist_ok=False)
    for arm in ("P5_control", "P6_paid_baker_return"):
        row = audit(arm)
        (OUT / (arm + ".json")).write_text(
            json.dumps(row, indent=2, sort_keys=True), encoding="utf8")
        print("PLAY48_REAL228_ECONOMIC_LOCK " + json.dumps(
            row, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
