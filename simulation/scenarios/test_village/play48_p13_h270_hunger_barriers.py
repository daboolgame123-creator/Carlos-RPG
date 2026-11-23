"""PLAY-48 P13: read-only evidence for the six authentic h270 hungry NPCs.

Replays one COPY of the verified P11 h264 ledger with exactly the P12 flags.
Does not add resources, modify the source ledger, influence any NPC planner,
or change the signed food-aid policy. All findings are operator-only.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from carlos_sim import SQLiteEventStore, TimeEngine
from carlos_sim.community_food import _eligible
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.food_access_diagnostics import audit_food_access_barriers
from carlos_sim.food_for_work import _available_site_food
from play48_integrated_acceptance import WORLD, HOUR, conserve_diverse, engine
from play48_p11_real240_renewable_wage import FLAGS

SOURCE = Path("evidence/p13_real264/P11_real_wage.sqlite")
OUT = Path("play48_p13_h270_hunger_audit")
HOURS = (264, 265, 270)
EXPECTED_H270 = ("burner", "hana", "miner", "nora", "repairman", "smith")


def checkpoint(state) -> dict:
    access = audit_food_access_barriers(state)
    money = audit_npc_economy(state)
    assert money["copper_scope_complete"] and money["copper_known_total"] == 12
    assert len(state.npcs) == 13
    raw = state.to_dict()
    market_food = state.resources["market"].get("food", 0)
    bakery_food = state.resources["bakery"].get("food", 0)
    relief = state.market_stalls["market"]["community_food"]
    day = state.time // (24 * 3600)
    used = [p["recipient_id"] for p in relief["payments"]
            if p["paid_at"] // (24 * 3600) == day]
    assert len(used) <= relief["daily_limit"] == 2
    hungry = []
    for actor in access["actors"]:
        if actor["hunger"] != 100:
            continue
        who = actor["npc_id"]
        running_actions = [
            {"action": a["action"], "due": a["due"]}
            for a in state.actions.values()
            if a["npc_id"] == who and a["status"] == "running"
        ]
        traveling = [
            {"destination": t["destination"], "due": t["due"]}
            for t in state.travels.values()
            if t["npc_id"] == who and t["status"] == "traveling"
        ]
        production = [
            {"recipe": j["recipe_id"], "site": j["site_id"]}
            for j in state.production_jobs.values()
            if j["npc_id"] == who and j["status"] == "running"
        ]
        observations = []
        if actor["known_personal_food"] == 0:
            observations.append("no_personally_available_food")
        if actor["personally_spendable_copper"] == 0:
            observations.append("no_personal_cash")
        if actor["personally_spendable_copper"] is None:
            observations.append("no_spendable_personal_cash_slot")
        if not actor["locally_affordable_now"]:
            observations.append("no_affordable_local_offer_at_this_instant")
        if not actor["at_market"]:
            observations.append("not_at_market")
        if actor["known_road_path_to_market"] is None:
            observations.append("no_known_route_to_market")
        if not actor["physically_idle"]:
            observations.append("occupied_at_this_instant")
        if len(used) >= relief["daily_limit"]:
            observations.append("owner_aid_daily_cap_used")
        hungry.append({
            "id": who,
            "role": actor["role"],
            "location": actor["location"],
            "hunger": actor["hunger"],
            "fatigue": actor["fatigue"],
            "personal_food": actor["known_personal_food"],
            "reserved_cargo_food": actor["courier_reserved_cargo_food"],
            "cash_scope": actor["copper_scope"],
            "personal_cash": actor["personally_spendable_copper"],
            "market_route": actor["known_road_path_to_market"],
            "local_food_offers": actor["locally_listed_food"],
            "locally_affordable": actor["locally_affordable_now"],
            "running_actions": running_actions,
            "traveling": traveling,
            "running_production": production,
            "signed_unearned_food_wage": actor["signed_unearned_food_wage"],
            "courier_leg_blockers": actor["courier_leg_blockers"],
            "eligible_for_signed_aid_now": _eligible(
                raw, who, receive_while_resting=True
            ),
            "snapshot_observations_not_proven_causes": observations,
        })
    return {
        "hour": state.time // HOUR,
        "world_revision": state.revision,
        "copper_known_total": money["copper_known_total"],
        "market_owner_food": market_food,
        "market_unquoted_food": _available_site_food(state, "market"),
        "bakery_owner_food": bakery_food,
        "bakery_grain": state.resources["bakery"].get("grain", 0),
        "all_owners_with_food": {
            owner: stock["food"]
            for owner, stock in sorted(state.resources.items())
            if stock.get("food", 0) > 0
        },
        "relief_used_today": used,
        "relief_daily_limit": relief["daily_limit"],
        "open_food_market_offers": [
            {
                "id": ident, "seller": o["seller_id"], "owner": o["stock_owner_id"],
                "remaining": o["remaining"], "unit_price": o["unit_price"],
                "site": o["site_id"],
            }
            for ident, o in sorted(state.market_offers.items())
            if o["status"] == "open" and o["resource"] == "food"
        ],
        "hungry100_count": len(hungry),
        "hungry100": hungry,
    }


def main() -> None:
    assert SOURCE.is_file(), "must use exact authentic P11 h264 SQLite"
    original_sha = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    OUT.mkdir(exist_ok=False)
    copy = OUT / "P12_replayed_for_diagnosis.sqlite"
    shutil.copyfile(SOURCE, copy)
    rows = {}
    with SQLiteEventStore(copy) as db:
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            state = db.load(WORLD)
            assert state.time == 264 * HOUR and len(state.npcs) == 13
            sim = engine(db, clock, reserve_trader_meal=True,
                         deferred_market_courier_wage=True)
            for flag in FLAGS:
                setattr(sim, flag, True)
            sim.local_market_freight_wage_enabled = True
            sim.resting_market_ration_enabled = True
            for hour in HOURS:
                if hour > HOURS[0]:
                    state = sim.advance(
                        WORLD, seconds=hour * HOUR - state.time,
                        command_id=f"p13-forensic-h{hour}",
                        expected_revision=state.revision,
                    ).state
                conserve_diverse(state)
                assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
                assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
                db.snapshot(WORLD)
                assert db.load(WORLD).to_dict() == state.to_dict()
                rows[str(hour)] = checkpoint(state)
                print("PLAY48_P13_CHECKPOINT " + json.dumps({
                    "hour": hour,
                    "hungry100": [p["id"] for p in rows[str(hour)]["hungry100"]],
                    "market_owner_food": rows[str(hour)]["market_owner_food"],
                    "market_unquoted_food": rows[str(hour)]["market_unquoted_food"],
                }, sort_keys=True), flush=True)
        finally:
            clock.close_session(WORLD)
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == original_sha
    actual = tuple(p["id"] for p in rows["270"]["hungry100"])
    assert actual == EXPECTED_H270, (actual, EXPECTED_H270)
    for actor in rows["270"]["hungry100"]:
        print("PLAY48_P13_HUNGRY_BARRIER " +
              json.dumps(actor, sort_keys=True), flush=True)
    summary = {
        "source": "authentic P11 h264; P12 flags ON; no policy changes",
        "source_sha256_unchanged": original_sha,
        "p12_head": "edc40ae4162c6d1977965d25fd6d27cbc34a84db",
        "snapshots": rows,
        "status": "P13_DIAGNOSTIC_ONLY / PLAY48_NO_GO",
    }
    (OUT / "barriers.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8"
    )


if __name__ == "__main__":
    main()
