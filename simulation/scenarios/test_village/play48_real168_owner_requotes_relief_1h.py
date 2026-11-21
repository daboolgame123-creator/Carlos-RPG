"""Genuine original h168 saved P3 vs opt-in owner-signed quote release to h169.

Two independent copies of the authenticated original 13-NPC, 12-copper h168
ledger. No historical rewrites, money/food generation, donor teleport, NPC
spawning, new rain or arbitrary market ownership. Only an on-site owner may
retract an aged, unsold offer before distributing signed 2/day market aid.
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


SOURCE_DIR = Path("evidence/genuine168")
OUT = Path("relief169")


def run_arm(source: Path, arm: str, *, allow_reallocation: bool) -> dict:
    dest = OUT / (arm + ".sqlite")
    shutil.copyfile(source, dest)
    assert hashlib.sha256(dest.read_bytes()).hexdigest() == hashlib.sha256(source.read_bytes()).hexdigest()
    with SQLiteEventStore(dest) as db:
        s = db.load(WORLD)
        assert s.time == 168 * HOUR and len(s.npcs) == 13
        initial_cash = audit_npc_economy(s)
        assert initial_cash["copper_scope_complete"] and initial_cash["copper_known_total"] == 12
        opening = {
            oid for oid, offer in s.market_offers.items()
            if offer["site_id"] == "market" and offer["stock_owner_id"] == "market"
            and offer["resource"] == "food" and offer["status"] == "open"
        }
        opening_rations = len(s.market_stalls["market"]["community_food"]["payments"])
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            sim = engine(db, clock, reserve_trader_meal=True,
                         deferred_market_courier_wage=True)
            sim.merchant_food_wage_enabled = True
            sim.community_food_enabled = True
            sim.cashless_relief_walk_enabled = True
            sim.desperate_paid_harvest_enabled = True
            sim.deferred_bakery_grain_wage_enabled = True
            sim.integrated_livelihoods_enabled = True
            sim.remember_unbought_stalls_enabled = True
            sim.reserve_signed_relief_offer_enabled = allow_reallocation
            end = sim.advance(
                WORLD, seconds=HOUR,
                command_id="genuine-168-to169-owner-quote-relief",
                expected_revision=s.revision,
            ).state
            assert end.time == 169 * HOUR and len(end.npcs) == 13
            conserve_diverse(end)
            money = audit_npc_economy(end)
            assert money["copper_scope_complete"] and money["copper_known_total"] == 12
            assert _available_site_food(end, "market") >= 0
            db.snapshot(WORLD)
            assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
            assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
            m = metrics(end)
            receipts = end.market_stalls["market"]["community_food"]["payments"]
            departed = [{
                "id": oid, "status": end.market_offers[oid]["status"],
                "remaining": end.market_offers[oid]["remaining"],
            } for oid in sorted(opening) if end.market_offers[oid]["status"] == "closed"]
            row = {
                "arm": arm, "hour": 169, "meals": m["meals"],
                "starving": m["starving"], "sales": m["sales"],
                "cash_wages": m["cash_wages"], "bread": m["bread"],
                "copper_total": money["copper_known_total"],
                "market_food": end.resources["market"]["food"],
                "market_unquoted_food": _available_site_food(end, "market"),
                "market_open_quotes": [{
                    "id": oid, "unit_price": o["unit_price"],
                    "remaining": o["remaining"],
                } for oid, o in sorted(end.market_offers.items())
                    if o["status"] == "open" and o["stock_owner_id"] == "market"
                    and o["resource"] == "food"],
                "original_168_open_offers_closed": departed,
                "new_signed_rations": len(receipts) - opening_rations,
                "new_signed_recipients": [
                    receipt["recipient_id"] for receipt in receipts[opening_rations:]
                ],
                "no_resource_or_currency_injection": True,
                "release_gate": "PLAY48_NO_GO",
            }
            print("PLAY48_REAL169_OWNER_REQUOTED " +
                  json.dumps(row, sort_keys=True), flush=True)
        finally:
            clock.close_session(WORLD)
    return row


def main() -> None:
    original = sorted(SOURCE_DIR.rglob("genuine_harvest.sqlite"))
    assert len(original) == 1, [str(p) for p in original]
    source = original[0]
    initial_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    OUT.mkdir(exist_ok=False)
    rows = {
        "P3_original": run_arm(source, "P3_original", allow_reallocation=False),
        "P4_signed_quote_relief": run_arm(source, "P4_signed_quote_relief", allow_reallocation=True),
    }
    assert hashlib.sha256(source.read_bytes()).hexdigest() == initial_hash
    baseline, treatment = rows.values()
    delta = {
        key: treatment[key] - baseline[key]
        for key in ("meals", "starving", "sales", "cash_wages", "new_signed_rations")
    }
    assert baseline["copper_total"] == treatment["copper_total"] == 12
    assert treatment["new_signed_rations"] <= 2
    print("PLAY48_REAL169_OWNER_REQUOTED_DELTA " + json.dumps({
        "P4_minus_P3": delta, "observational_only": True,
        "source_immutable_sha256": initial_hash, "release_gate": "PLAY48_NO_GO",
    }, sort_keys=True), flush=True)
    (OUT / "comparison.json").write_text(
        json.dumps({"rows": rows, "delta": delta,
                    "original168_sha256": initial_hash}, indent=2, sort_keys=True),
        encoding="utf8")


if __name__ == "__main__":
    main()
