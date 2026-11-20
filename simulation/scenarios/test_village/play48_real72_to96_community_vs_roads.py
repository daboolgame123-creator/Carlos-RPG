"""Continue two authentic SQLite event histories from 72h to 96h.

P0 = market owner-signed finite relief (PR160 saved72).
P1 = same market relief plus cashless personally-known-road physical travel
     (PR161 saved72).
Both have 13 original NPCs, exactly 12 genuine copper and the original
3-food time-zero source. They may now differ because of authentic prior events.
Every 6-hour partition is a deterministic authenticated simulation advance.
No resource injection, world rewind, NPC teleport or historic re-seeding.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

from carlos_sim import SQLiteEventStore
from carlos_sim.economic_diagnostics import audit_npc_economy
from play48_integrated_acceptance import WORLD, HOUR, advance_to, metrics

HOURS = (84, 96)
ARMS = {
    "owner_relief_only": ("p0/community.sqlite", False),
    "owner_relief_plus_roads": ("p1/cashless_known_roads.sqlite", True),
}


def audit_saved(path: Path, *, hour: int) -> dict:
    with SQLiteEventStore(path) as db:
        state = db.load(WORLD)
        assert state.time == hour * HOUR
        assert len(state.npcs) == 13
        assert db.verify(WORLD).to_dict() == state.to_dict()
    copper = audit_npc_economy(state)
    assert copper["copper_scope_complete"]
    assert copper["copper_known_total"] == 12
    recipients = state.market_stalls["market"]["community_food"]["payments"]
    m = metrics(state)
    return {
        "hour": hour,
        "copper": copper["copper_known_total"],
        "meals": m["meals"],
        "hungry100": m["starving"],
        "bread": m["bread"],
        "sales": m["sales"],
        "cash_wages": m["cash_wages"],
        "market_food": state.resources["market"]["food"],
        "quoted_market_food": sum(o["remaining"] for o in state.market_offers.values()
                                   if o["status"] == "open" and o["stock_owner_id"] == "market"
                                   and o["resource"] == "food"),
        "community_rations": len(recipients),
        "community_recipients": [r["recipient_id"] for r in recipients],
        "destitute_hungry75": sorted(who for who, n in state.npcs.items()
            if n["needs"]["hunger"] >= 75
            and state.resources[who].get("food") == 0
            and state.resources[who].get("coin_copper") == 0),
        "npc": {who: {
            "hunger": entry["hunger"], "food": entry["food"], "cash": entry["cash"],
            "site": entry["site"], "meals": entry["meals"],
        } for who, entry in m["npcs"].items()},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)

    paths: dict[str, Path] = {}
    rows: dict[str, dict] = {}
    for arm, (source, use_roads) in ARMS.items():
        original = args.input / source
        assert original.is_file(), f"required persisted original-village 72h ledger missing: {original}"
        dest = args.output / f"{arm}.sqlite"
        shutil.copyfile(original, dest)
        paths[arm] = dest
        before = audit_saved(dest, hour=72)
        before_hash = hashlib.sha256(original.read_bytes()).hexdigest()
        assert before_hash == hashlib.sha256(dest.read_bytes()).hexdigest()
        rows[arm] = {"72": before, "original72_sha256": before_hash}
        print("PLAY48_RESUME72_INITIAL " + json.dumps({
            "variant": arm, "initial72_sha256": before_hash, **{
                key: before[key] for key in ("hour", "meals", "hungry100",
                                            "bread", "sales", "cash_wages",
                                            "community_rations", "copper")
            }
        }, sort_keys=True), flush=True)

    for hour in HOURS:
        for arm, (_, use_roads) in ARMS.items():
            checkpoint = advance_to(paths[arm], hour, candidate=True,
                                    community_food=True, cashless_relief_walk=use_roads)
            audited = audit_saved(paths[arm], hour=hour)
            assert checkpoint["meals"] == audited["meals"]
            assert checkpoint["starving"] == audited["hungry100"]
            rows[arm][str(hour)] = audited
            print("PLAY48_RESUME72_REAL " + json.dumps({
                "variant": arm, **{
                    key: audited[key] for key in ("hour", "meals", "hungry100",
                                                 "bread", "sales", "cash_wages",
                                                 "community_rations", "market_food",
                                                 "community_recipients", "copper")
                }
            }, sort_keys=True), flush=True)
            (args.output / "comparison.json").write_text(
                json.dumps(rows, indent=2, sort_keys=True), encoding="utf8")
        p0, p1 = (rows[a][str(hour)] for a in ARMS)
        delta = {key: p1[key] - p0[key] for key in (
            "meals", "hungry100", "bread", "sales", "cash_wages", "community_rations")}
        print("PLAY48_RESUME72_DELTA " + json.dumps({
            "hour": hour, "roads_minus_owner_relief": delta,
            "copper_conserved": p0["copper"] == p1["copper"] == 12,
            "observational_only": True, "release_gate_unchanged": True,
        }, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
