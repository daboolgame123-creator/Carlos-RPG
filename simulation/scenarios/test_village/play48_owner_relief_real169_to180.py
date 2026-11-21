"""Continue actual P3/P4 saved h169 original worlds to h174 and h180.

NO bootstrap, event replacement, fabricated supplies, money or rain. The
shopkeeper contract and real old offers are already stored independently in
the authenticated source event histories from h168→169 A/B.
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

ARM_FLAGS = {"P3_original": False, "P4_signed_quote_relief": True}
SOURCE = Path("evidence/saved169")
OUT = Path("relief180")


def continue_saved(arm: str, *, allow_requote: bool) -> tuple[dict, str]:
    matches = sorted(SOURCE.rglob(arm + ".sqlite"))
    assert len(matches) == 1, (arm, matches)
    original = matches[0]
    source_hash = hashlib.sha256(original.read_bytes()).hexdigest()
    dest = OUT / (arm + ".sqlite")
    shutil.copyfile(original, dest)
    assert hashlib.sha256(dest.read_bytes()).hexdigest() == source_hash
    rows = {}
    with SQLiteEventStore(dest) as db:
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            s = db.load(WORLD)
            assert s.time == 169 * HOUR and len(s.npcs) == 13
            assert audit_npc_economy(s)["copper_known_total"] == 12
            sim = engine(db, clock, reserve_trader_meal=True,
                         deferred_market_courier_wage=True)
            sim.merchant_food_wage_enabled = True
            sim.community_food_enabled = True
            sim.cashless_relief_walk_enabled = True
            sim.desperate_paid_harvest_enabled = True
            sim.deferred_bakery_grain_wage_enabled = True
            sim.integrated_livelihoods_enabled = True
            sim.remember_unbought_stalls_enabled = True
            sim.reserve_signed_relief_offer_enabled = allow_requote
            for hour in (174, 180):
                s = sim.advance(
                    WORLD, seconds=(hour * HOUR - s.time),
                    command_id=f"authentic-owner-help-{arm}-{hour*HOUR}",
                    expected_revision=s.revision,
                ).state
                assert s.time == hour * HOUR
                assert len(s.npcs) == 13
                conserve_diverse(s)
                money = audit_npc_economy(s)
                assert money["copper_scope_complete"] and money["copper_known_total"] == 12
                assert _available_site_food(s, "market") >= 0
                db.snapshot(WORLD)
                assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
                assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
                m = metrics(s)
                payments = s.market_stalls["market"]["community_food"]["payments"]
                row = {
                    "arm": arm, "hour": hour,
                    "hungry100": m["starving"], "meals": m["meals"],
                    "sales": m["sales"], "cash_wages": m["cash_wages"],
                    "bread": m["bread"], "copper": 12,
                    "market_owned_food": s.resources["market"]["food"],
                    "quoted_market_food": sum(o["remaining"] for o in s.market_offers.values()
                        if o["status"] == "open" and o["stock_owner_id"] == "market"
                        and o["resource"] == "food"),
                    "signed_rations": len(payments),
                    "signed_recipients": [p["recipient_id"] for p in payments],
                    "observational_only": True,
                    "release_gate": "PLAY48_NO_GO",
                }
                rows[str(hour)] = row
                print("PLAY48_OWNER_SIGNED_RELIEF_REAL " +
                      json.dumps(row, sort_keys=True), flush=True)
                (OUT / (arm + "-observations.json")).write_text(
                    json.dumps(rows, indent=2, sort_keys=True), encoding="utf8")
        finally:
            clock.close_session(WORLD)
    assert hashlib.sha256(original.read_bytes()).hexdigest() == source_hash
    return rows, source_hash


def main() -> None:
    OUT.mkdir(exist_ok=False)
    rows = {}
    for arm, enabled in ARM_FLAGS.items():
        rows[arm], source_sha = continue_saved(arm, allow_requote=enabled)
        rows[arm]["source169_sha256"] = source_sha
    for h in ("174", "180"):
        a, b = (rows[arm][h] for arm in ARM_FLAGS)
        delta = {key: b[key] - a[key]
                 for key in ("hungry100", "meals", "sales",
                             "cash_wages", "signed_rations")}
        assert a["copper"] == b["copper"] == 12
        print("PLAY48_OWNER_SIGNED_RELIEF_DELTA " + json.dumps({
            "hour": int(h), "P4_minus_P3": delta,
            "release_gate": "PLAY48_NO_GO",
            "source_worlds_unchanged": True,
        }, sort_keys=True), flush=True)
    (OUT / "comparison.json").write_text(
        json.dumps(rows, indent=2, sort_keys=True), encoding="utf8")


if __name__ == "__main__":
    main()
