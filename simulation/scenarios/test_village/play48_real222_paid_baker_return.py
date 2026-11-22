"""Authentic P5 h222 saved-world P6 baker-return A/B; no new resources."""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from carlos_sim import SQLiteEventStore, TimeEngine
from carlos_sim.economic_diagnostics import audit_npc_economy
from play48_integrated_acceptance import WORLD, HOUR, engine, metrics, conserve_diverse

SOURCE = Path("evidence/authentic222")
OUT = Path("real222_baker_return")
HOURS = (223, 225, 228)


def run_arm(source: Path, label: str, enabled: bool) -> dict:
    dest = OUT / (label + ".sqlite")
    shutil.copyfile(source, dest)
    assert hashlib.sha256(dest.read_bytes()).digest() == hashlib.sha256(source.read_bytes()).digest()
    checkpoints = {}
    with SQLiteEventStore(dest) as db:
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            initial = db.load(WORLD)
            assert initial.time == 222 * HOUR and len(initial.npcs) == 13
            assert audit_npc_economy(initial)["copper_known_total"] == 12
            assert initial.resources["bakery"]["grain"] == 19
            assert initial.resources["bakery"]["food"] == 0
            assert initial.npcs["basim"]["needs"]["hunger"] == 82
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
            sim.hungry_paid_baker_return_enabled = enabled
            current = initial
            for hour in HOURS:
                current = sim.advance(
                    WORLD, seconds=hour * HOUR - current.time,
                    command_id=f"p6-real222-{label}-{hour}",
                    expected_revision=current.revision).state
                conserve_diverse(current)
                audit = audit_npc_economy(current)
                assert audit["copper_scope_complete"] and audit["copper_known_total"] == 12
                assert len(current.npcs) == 13
                assert db.db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
                assert not db.db.execute("PRAGMA foreign_key_check").fetchall()
                db.snapshot(WORLD)
                measure = metrics(current)
                checkpoints[str(hour)] = {
                    "hour": hour, "arm": label, "bread": measure["bread"],
                    "meals": measure["meals"], "sales": measure["sales"],
                    "cash_wages": measure["cash_wages"],
                    "hungry100": measure["starving"],
                    "basim": measure["npcs"]["basim"],
                    "bakery_grain": current.resources["bakery"]["grain"],
                    "bakery_food": current.resources["bakery"]["food"],
                    "market_copper": current.resources["market"]["coin_copper"],
                    "farm_east_copper": current.resources["farm_east"]["coin_copper"],
                    "total_copper": 12, "decision": "EXPERIMENTAL_NO_GO",
                }
                print("PLAY48_REAL222_BAKER_RETURN " + json.dumps(
                    checkpoints[str(hour)], sort_keys=True), flush=True)
        finally:
            clock.close_session(WORLD)
        # Re-load the committed snapshot and compare complete canonical state.
        # Full genesis-to-h228 re-verification takes >45 minutes on CI even
        # though the event-sourced h222 source is already verified and immutable.
        # Keep that expensive verification as a separate archival gate.
        assert db.load(WORLD).to_dict() == current.to_dict()
    (OUT / (label + "-report.json")).write_text(
        json.dumps(checkpoints, indent=2, sort_keys=True), encoding="utf8")
    return checkpoints


def main() -> None:
    originals = sorted(SOURCE.rglob("P5_funded_seed.sqlite"))
    assert len(originals) == 1, originals
    source = originals[0]
    immutable_digest = hashlib.sha256(source.read_bytes()).hexdigest()
    OUT.mkdir(exist_ok=False)
    control = run_arm(source, "P5_control", False)
    candidate = run_arm(source, "P6_paid_baker_return", True)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == immutable_digest
    for hour in HOURS:
        a, b = control[str(hour)], candidate[str(hour)]
        # Acceptance here concerns only documented P6 paid-baker recovery.
        assert b["total_copper"] == a["total_copper"] == 12
        assert b["bread"] >= a["bread"] and b["meals"] >= a["meals"]
        assert b["sales"] == a["sales"] and b["cash_wages"] == a["cash_wages"]
        assert b["basim"]["hunger"] < a["basim"]["hunger"]
        assert b["basim"]["site"] == "bakery"
        print("PLAY48_P6_MINUS_P5 " + json.dumps({
            "hour": hour, "source_sha256": immutable_digest,
            "bread": b["bread"] - a["bread"],
            "meals": b["meals"] - a["meals"],
            "hungry100": b["hungry100"] - a["hungry100"],
            "sales": b["sales"] - a["sales"],
            "cash_wages": b["cash_wages"] - a["cash_wages"],
            "release_gate": "PLAY48_NO_GO",
        }, sort_keys=True), flush=True)
    (OUT / "comparison.json").write_text(json.dumps(
        {"control": control, "candidate": candidate}, indent=2), encoding="utf8")


if __name__ == "__main__":
    main()
