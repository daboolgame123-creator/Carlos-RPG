"""P8 authentic P7 h234 two-branch test of off-duty shopkeeper returning home.

Only existing movement, safety, shift and signed goods apply. This test
does not claim the stranded couriers are rescued by a passerby.
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
OUT = Path("real234_keeper_homeward")
HOURS = (235, 236, 238, 240)


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
            assert state.entities["layla"]["location_id"] == "riverbank"
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
            runner.offshift_steward_homeward_enabled = enabled
            for hour in HOURS:
                state = runner.advance(
                    WORLD, seconds=hour * HOUR - state.time,
                    command_id=f"p8-h234-{label}-{hour}",
                    expected_revision=state.revision).state
                conserve_diverse(state)
                audit = audit_npc_economy(state)
                assert audit["copper_scope_complete"]
                assert audit["copper_known_total"] == 12
                assert len(state.npcs) == 13
                assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
                assert not db.db.execute("PRAGMA foreign_key_check").fetchall()
                db.snapshot(WORLD)
                arrived = sorted(
                    [(t["arrived_at"], ident, t["destination"])
                     for ident, t in state.travels.items()
                     if t["npc_id"] == "layla" and t["status"] == "arrived"
                     and t["arrived_at"] > 234 * HOUR])
                m = metrics(state)
                rows[str(hour)] = {
                    "hour": hour, "arm": label,
                    "layla": m["npcs"]["layla"],
                    "layla_arrived_after234": arrived,
                    "hana": m["npcs"]["hana"],
                    "huda": m["npcs"]["huda"],
                    "bread": m["bread"], "meals": m["meals"],
                    "starving": m["starving"], "cash_wages": m["cash_wages"],
                    "copper": 12, "decision": "P8_EXPERIMENTAL_NO_GO",
                }
                print("PLAY48_REAL234_OFFSHIFT_WALK " +
                      json.dumps(rows[str(hour)], sort_keys=True), flush=True)
        finally:
            clock.close_session(WORLD)
        assert db.load(WORLD).to_dict() == state.to_dict()
    (OUT / (label + "-report.json")).write_text(json.dumps(
        rows, sort_keys=True, indent=2), encoding="utf8")
    return rows


def main() -> None:
    sources = sorted(SOURCE.rglob("P7_signed_wage.sqlite"))
    assert len(sources) == 1, sources
    source = sources[0]
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    OUT.mkdir(exist_ok=False)
    control = run_arm(source, "P7_control", False)
    candidate = run_arm(source, "P8_offshift_return", True)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == digest
    assert not control["235"]["layla_arrived_after234"]
    assert candidate["235"]["layla_arrived_after234"], (
        "P8 must demonstrate an actual autonomous, physically traveled return")
    for hour in HOURS:
        a, b = control[str(hour)], candidate[str(hour)]
        assert a["copper"] == b["copper"] == 12
        print("PLAY48_P8_MINUS_P7 " + json.dumps({
            "hour": hour, "source_sha256": digest,
            "walked": len(b["layla_arrived_after234"]),
            "meals_delta": b["meals"] - a["meals"],
            "starving_delta": b["starving"] - a["starving"],
            "hana_hunger_delta": b["hana"]["hunger"] - a["hana"]["hunger"],
            "huda_hunger_delta": b["huda"]["hunger"] - a["huda"]["hunger"],
            "release_gate": "PLAY48_NO_GO",
        }, sort_keys=True), flush=True)
    (OUT / "comparison.json").write_text(
        json.dumps({"control": control, "candidate": candidate}, indent=2),
        encoding="utf8")


if __name__ == "__main__":
    main()
