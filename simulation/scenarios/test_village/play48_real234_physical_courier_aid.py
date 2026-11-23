"""PLAY48 P9 original P7 h234 saved history, real P8 road + local aid A/B.

Only existing goods may be handed over. Every request, acceptance, fulfilled
physical aid and eaten meal are authoritative events in independently saved
SQLite histories; no manual gifts or fake relief seeding.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from carlos_sim import SQLiteEventStore, TimeEngine
from carlos_sim.economic_diagnostics import audit_npc_economy
from play48_integrated_acceptance import WORLD, HOUR, engine, metrics, conserve_diverse

SOURCE = Path("evidence/authentic234")
OUT = Path("real234_courier_aid")
HOURS = (235, 236, 240, 244)


def run_arm(source: Path, label: str, enabled: bool) -> dict:
    dest = OUT / (label + ".sqlite")
    shutil.copyfile(source, dest)
    rows = {}
    with SQLiteEventStore(dest) as db:
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            state = db.load(WORLD)
            assert state.time == 234 * HOUR and len(state.npcs) == 13
            assert state.npcs["hana"]["needs"]["hunger"] == 100
            assert state.npcs["huda"]["needs"]["hunger"] == 100
            assert state.resources["layla"]["food"] == 1
            assert audit_npc_economy(state)["copper_known_total"] == 12
            runner = engine(db, clock, reserve_trader_meal=True,
                            deferred_market_courier_wage=True)
            runner.merchant_food_wage_enabled = True
            runner.community_food_enabled = True
            runner.cashless_relief_walk_enabled = True
            runner.desperate_paid_harvest_enabled = True
            runner.deferred_bakery_grain_wage_enabled = True
            runner.integrated_livelihoods_enabled = True
            runner.remember_unbought_stalls_enabled = True
            runner.reserve_signed_relief_offer_enabled = True
            runner.desperate_funded_planting_enabled = True
            runner.hungry_paid_baker_return_enabled = True
            runner.signed_steward_wage_quote_release_enabled = True
            runner.offshift_steward_homeward_enabled = True
            runner.local_emergency_courier_help_enabled = enabled
            for hour in HOURS:
                state = runner.advance(
                    WORLD, seconds=hour * HOUR - state.time,
                    command_id=f"p9-h234-{label}-{hour}",
                    expected_revision=state.revision).state
                conserve_diverse(state)
                audit = audit_npc_economy(state)
                assert audit["copper_scope_complete"] and audit["copper_known_total"] == 12
                assert len(state.npcs) == 13
                assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
                assert not db.db.execute("PRAGMA foreign_key_check").fetchall()
                db.snapshot(WORLD)
                m = metrics(state)
                receipts = {
                    ident: {
                        "requester": item["requester"],
                        "donor": item["provider"],
                        "status": item["status"],
                        "transfer": item["transfer"],
                    }
                    for ident, item in state.obligations.items()
                    if ident.startswith("p9-well:")
                }
                rows[str(hour)] = {
                    "arm": label, "hour": hour,
                    "hana": m["npcs"]["hana"],
                    "huda": m["npcs"]["huda"],
                    "layla": m["npcs"]["layla"],
                    "bread": m["bread"], "meals": m["meals"],
                    "starving": m["starving"], "cash_wages": m["cash_wages"],
                    "market_food": state.resources["market"]["food"],
                    "authentic_physical_aid": receipts,
                    "copper": 12,
                    "gate": "PLAY48_NO_GO",
                }
                print("PLAY48_REAL234_COURIER_AID " +
                      json.dumps(rows[str(hour)], sort_keys=True), flush=True)
        finally:
            clock.close_session(WORLD)
        assert db.load(WORLD).to_dict() == state.to_dict()
    (OUT / (label + "-report.json")).write_text(
        json.dumps(rows, indent=2, sort_keys=True), encoding="utf8")
    return rows


def main() -> None:
    sources = sorted(SOURCE.rglob("P7_signed_wage.sqlite"))
    assert len(sources) == 1, sources
    source = sources[0]
    original_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    OUT.mkdir(exist_ok=False)
    control = run_arm(source, "P8_control", False)
    candidate = run_arm(source, "P9_local_aid", True)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == original_hash
    for hour in HOURS:
        a, b = control[str(hour)], candidate[str(hour)]
        assert a["copper"] == b["copper"] == 12
        assert b["bread"] >= a["bread"]
        assert b["starving"] <= a["starving"]
        print("PLAY48_P9_MINUS_P8 " + json.dumps({
            "hour": hour, "source_sha256": original_hash,
            "extra_meals": b["meals"] - a["meals"],
            "extra_starving": b["starving"] - a["starving"],
            "hana_hunger_delta": b["hana"]["hunger"] - a["hana"]["hunger"],
            "huda_hunger_delta": b["huda"]["hunger"] - a["huda"]["hunger"],
            "aid_receipts": len(b["authentic_physical_aid"]),
            "release_gate": "PLAY48_NO_GO",
        }, sort_keys=True), flush=True)
    receipts = candidate["235"]["authentic_physical_aid"]
    assert len(receipts) == 1, "real emergency donor encounter did not settle"
    receipt = next(iter(receipts.values()))
    assert receipt["status"] == "fulfilled"
    assert receipt["donor"] == "layla"
    assert receipt["requester"] in ("hana", "huda")
    assert receipt["transfer"]["provider_before"] - receipt["transfer"]["provider_after"] == 1
    assert receipt["transfer"]["requester_after"] - receipt["transfer"]["requester_before"] == 1
    assert candidate["235"]["meals"] > control["235"]["meals"]
    assert candidate["235"]["starving"] < control["235"]["starving"]
    (OUT / "comparison.json").write_text(
        json.dumps({"control": control, "candidate": candidate}, indent=2),
        encoding="utf8")


if __name__ == "__main__":
    main()
