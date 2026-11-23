"""P7: saved real P6 h228 to h234, option-off versus signed earned wage quote.

Same event sourced starting point; no new food, money, wages or donor.
All payments use the original signed MarketStewardFoodWagePaid reducer.
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
HOURS = (229, 231, 234)


def run_arm(source: Path, label: str, enable: bool) -> dict:
    dest = OUT / (label + ".sqlite")
    shutil.copyfile(source, dest)
    checkpoints = {}
    with SQLiteEventStore(dest) as db:
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            initial = db.load(WORLD)
            assert initial.time == 228 * HOUR and len(initial.npcs) == 13
            assert initial.resources["market"]["food"] == 8
            assert initial.npcs["salma"]["needs"]["hunger"] == 100
            assert audit_npc_economy(initial)["copper_known_total"] == 12
            earned, paid = _earned_sales(initial, "market")
            assert len(earned) == 14 and len(paid) == 6
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
            sim.signed_steward_wage_quote_release_enabled = enable
            current = initial
            for h in HOURS:
                current = sim.advance(
                    WORLD, seconds=h * HOUR - current.time,
                    command_id=f"p7-h228-{label}-{h}",
                    expected_revision=current.revision).state
                conserve_diverse(current)
                audit = audit_npc_economy(current)
                assert audit["copper_scope_complete"]
                assert audit["copper_known_total"] == 12
                assert len(current.npcs) == 13
                assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
                assert not db.db.execute("PRAGMA foreign_key_check").fetchall()
                db.snapshot(WORLD)
                earned, paid = _earned_sales(current, "market")
                m = metrics(current)
                checkpoints[str(h)] = {
                    "arm": label, "hour": h,
                    "bread": m["bread"], "meals": m["meals"],
                    "sales": m["sales"], "cash_wages": m["cash_wages"],
                    "hungry100": m["starving"],
                    "salma": m["npcs"]["salma"],
                    "earned_sales": len(earned), "paid_steward_wages": len(paid),
                    "market_food": current.resources["market"]["food"],
                    "market_copper": current.resources["market"]["coin_copper"],
                    "coin_total": 12, "decision": "P7_EXPERIMENTAL_NO_GO",
                }
                print("PLAY48_REAL228_STEWARD_WAGE " + json.dumps(
                    checkpoints[str(h)], sort_keys=True), flush=True)
        finally:
            clock.close_session(WORLD)
        assert db.load(WORLD).to_dict() == current.to_dict()
    (OUT / (label + "-report.json")).write_text(
        json.dumps(checkpoints, indent=2, sort_keys=True), encoding="utf8")
    return checkpoints


def main() -> None:
    found = sorted(SOURCE.rglob("P6_paid_baker_return.sqlite"))
    assert len(found) == 1, found
    source = found[0]
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    OUT.mkdir(exist_ok=False)
    control = run_arm(source, "P6_control", False)
    improved = run_arm(source, "P7_signed_wage", True)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == digest
    for h in HOURS:
        a, b = control[str(h)], improved[str(h)]
        assert b["coin_total"] == a["coin_total"] == 12
        assert b["paid_steward_wages"] >= a["paid_steward_wages"]
        assert b["salma"]["hunger"] <= a["salma"]["hunger"]
        assert b["bread"] >= a["bread"] and b["meals"] >= a["meals"]
        assert b["hungry100"] <= a["hungry100"]
        print("PLAY48_P7_MINUS_P6 " + json.dumps({
            "hour": h, "source_sha256": digest,
            "meals": b["meals"] - a["meals"],
            "bread": b["bread"] - a["bread"],
            "starving": b["hungry100"] - a["hungry100"],
            "paid_steward_wages": b["paid_steward_wages"] - a["paid_steward_wages"],
            "salma_hunger": b["salma"]["hunger"] - a["salma"]["hunger"],
            "release_gate": "PLAY48_NO_GO",
        }, sort_keys=True), flush=True)
    assert improved["229"]["paid_steward_wages"] > control["229"]["paid_steward_wages"], (
        "an already earned signed food wage was not paid at the owner shop")
    (OUT / "comparison.json").write_text(
        json.dumps({"control": control, "candidate": improved}, indent=2),
        encoding="utf8")


if __name__ == "__main__":
    main()
