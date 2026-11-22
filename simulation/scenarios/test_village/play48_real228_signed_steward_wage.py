"""Authentic P6 h228 -> 229 P7 paid signed steward wage A/B.

Both arms are copies of the very same saved 13-NPC, 12-copper event ledger.
No gifts, no rewrites, no new recipes, contracts, actors or buyer credit.
"""
from __future__ import annotations
import hashlib
import json
import shutil
from pathlib import Path

from carlos_sim import SQLiteEventStore, TimeEngine
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.steward_food_payroll import _earned_sales
from play48_integrated_acceptance import WORLD, HOUR, engine, metrics, conserve_diverse

SOURCE = Path("evidence/authentic228")
OUT = Path("real228_steward_wage")


def row(s, label):
    earned, paid = _earned_sales(s, "market")
    m = metrics(s)
    return {
        "arm": label,
        "hour": s.time // HOUR,
        "starving": m["starving"],
        "bread": m["bread"],
        "meals": m["meals"],
        "sales": m["sales"],
        "cash_wages": m["cash_wages"],
        "salma": m["npcs"]["salma"],
        "steward_sales": len(earned),
        "steward_paid_food_wages": len(paid),
        "unpaid_signed_steward_wages": max(0, len(earned) // 2 - len(paid)),
        "market_food": s.resources["market"]["food"],
        "market_copper": s.resources["market"]["coin_copper"],
        "market_open_quoted_food": sum(q["remaining"] for q in s.market_offers.values()
            if q["status"] == "open" and q["stock_owner_id"] == "market"
            and q["resource"] == "food"),
        "total_copper": audit_npc_economy(s)["copper_known_total"],
    }


def run_arm(source, label, enabled):
    dest = OUT / (label + ".sqlite")
    shutil.copyfile(source, dest)
    assert hashlib.sha256(dest.read_bytes()).digest() == hashlib.sha256(source.read_bytes()).digest()
    with SQLiteEventStore(dest) as db:
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            s = db.load(WORLD)
            assert s.time == 228 * HOUR and len(s.npcs) == 13
            earned, paid = _earned_sales(s, "market")
            assert len(earned) == 14 and len(paid) == 6  # real signed debt
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
            sim.signed_steward_wage_quote_rescue_enabled = enabled
            initial = row(s, label)
            print("PLAY48_REAL228_SIGNED_STEWARD " + json.dumps(initial, sort_keys=True),
                  flush=True)
            s = sim.advance(WORLD, seconds=HOUR,
                            command_id="real228-signed-steward-" + label,
                            expected_revision=s.revision).state
            conserve_diverse(s)
            cash = audit_npc_economy(s)
            assert len(s.npcs) == 13 and cash["copper_scope_complete"]
            assert cash["copper_known_total"] == 12
            db.snapshot(WORLD)
            assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
            assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
            assert db.load(WORLD).to_dict() == s.to_dict()
            final = row(s, label)
            print("PLAY48_REAL228_SIGNED_STEWARD " + json.dumps(final, sort_keys=True),
                  flush=True)
        finally:
            clock.close_session(WORLD)
    (OUT / (label + "-report.json")).write_text(
        json.dumps({"initial": initial, "final": final}, indent=2, sort_keys=True),
        encoding="utf8")
    return final


def main():
    originals = sorted(SOURCE.rglob("P6_paid_baker_return.sqlite"))
    assert len(originals) == 1, originals
    source = originals[0]
    original_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    OUT.mkdir(exist_ok=False)
    control = run_arm(source, "P6_control", False)
    candidate = run_arm(source, "P7_signed_steward_wage", True)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == original_hash
    assert candidate["total_copper"] == control["total_copper"] == 12
    difference = {
        "source_sha256": original_hash,
        "signed_steward_wages_paid": candidate["steward_paid_food_wages"] -
                                    control["steward_paid_food_wages"],
        "salma_hunger": candidate["salma"]["hunger"] - control["salma"]["hunger"],
        "salma_meals": candidate["salma"]["meals"] - control["salma"]["meals"],
        "hungry100": candidate["starving"] - control["starving"],
        "sales": candidate["sales"] - control["sales"],
        "market_food": candidate["market_food"] - control["market_food"],
        "total_copper": 12,
        "release_gate": "PLAY48_NO_GO",
    }
    (OUT / "comparison.json").write_text(
        json.dumps({"control": control, "candidate": candidate,
                    "difference": difference}, indent=2, sort_keys=True), encoding="utf8")
    print("PLAY48_P7_MINUS_P6 " + json.dumps(difference, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
