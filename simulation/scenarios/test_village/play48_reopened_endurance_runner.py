"""PLAY-48 reopened: genuine 13-NPC 72/96/168h economic acceptance runner.

This is intentionally NOT an auto-discovered pytest: it is long-running,
must be invoked by the dedicated CI job and MUST FAIL on economic failure,
even when the simulation engine's event and conservation tests stay green.
No loot, copper, NPC or resource is created by this runner.
"""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from carlos_sim import SQLiteEventStore
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.food_access_diagnostics import audit_food_access_barriers
from test_play48aa_actual_barter_bread_return import _seed_signed_share
from test_play48h3_early_market_wage import _run, _conserve
from test_play48_13npc_post72_relay import _stats
from test_play47_closure_endurance import WORLD

HOUR = 3600
CHECKPOINTS = tuple(h * HOUR for h in (24, 48, 72, 96, 120, 144, 168))


def summary(state):
    data = _stats(state)
    # Operator-only verified access audit: a courier's entrusted copper/food
    # is NOT personal spending power. Preserve unknown slots as None.
    access = audit_food_access_barriers(state)
    data["personal"] = [{
        "npc": who["npc_id"],
        "hunger": who["hunger"],
        "location": who["location"],
        "personal_food": who["known_personal_food"],
        "personally_spendable_copper": who["personally_spendable_copper"],
        "copper_scope": who["copper_scope"],
        "known_road_path_to_market": who["known_road_path_to_market"],
        "locally_affordable_now": who["locally_affordable_now"],
        "courier_leg_blockers": who["courier_leg_blockers"],
    } for who in access["actors"]]
    assert len(data["personal"]) == 13
    data["people_locally_affording_food"] = sum(
        who["locally_affordable_now"] for who in access["actors"])
    data["people_personally_solvent_at_two_copper"] = sum(
        who["personally_spendable_copper"] is not None
        and who["personally_spendable_copper"] >= 2
        for who in access["actors"])
    data["people_with_known_market_route"] = sum(
        who["known_road_path_to_market"] is not None
        for who in access["actors"])
    data["escrow_food"] = sum(c["remaining"] for c in state.courier_provisions.values())
    data["farm_owned_food"] = state.resources["farm"]["food"]
    data["huda_wage_total"] = state.courier_provisions["farm-water-huda"]["total_units"]
    data["huda_wages_paid"] = len(state.courier_provisions["farm-water-huda"]["payments"])
    data["real_bakery_farm_bread"] = state.supply_circuits["huda"]["bread_share_delivered"]
    return data


def run_economy_trial():
    with TemporaryDirectory(prefix="play48-reopened-") as folder:
        root = Path(folder)
        control_path, candidate_path = root / "control.sqlite", root / "candidate.sqlite"
        control = _seed_signed_share(
            control_path, share=True, farm_refill_authority=True)
        candidate = _seed_signed_share(
            candidate_path, share=True, farm_refill_authority=True)
        assert control.to_dict() == candidate.to_dict()
        results = {"control": [], "candidate": []}
        for end in CHECKPOINTS:
            for label, path, enabled in (
                ("control", control_path, False),
                ("candidate", candidate_path, True),
            ):
                state, _ = _run(
                    path, end, early=True,
                    hungry_woodcutter_work_enabled=True,
                    retry_known_supplier_enabled=True,
                    farm_sourced_wage_refill_enabled=enabled,
                )
                assert len(state.npcs) == 13 and state.time == end
                _conserve(state)
                assert audit_npc_economy(state)["copper_known_total"] == 12
                with SQLiteEventStore(path) as db:
                    assert db.verify(WORLD).to_dict() == state.to_dict()
                    assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
                    assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
                results[label].append(summary(state))
            print("PLAY48_REOPENED_13NPC_CHECKPOINT", json.dumps({
                "hour": end // HOUR,
                "control": results["control"][-1],
                "candidate": results["candidate"][-1],
            }, sort_keys=True), flush=True)
        by_hour = {point["time"] // HOUR: point for point in results["candidate"]}
        first, mid, last = (by_hour[hour] for hour in (72, 96, 168))
        def activity(after, before):
            return {
                "jobs": after["jobs"] - before["jobs"],
                "food_sales": after["food_sales"] - before["food_sales"],
                "meals": after["meals"] - before["meals"],
                "deliveries": sum(after["deliveries"].values())
                             - sum(before["deliveries"].values()),
            }
        a96 = activity(mid, first)
        a168 = activity(last, mid)
        gate = {
            "post72_real_jobs": a96["jobs"] > 0,
            "post72_real_food_sales": a96["food_sales"] > 0,
            "post72_real_meals": a96["meals"] > 0,
            "post72_real_courier_deliveries": a96["deliveries"] > 0,
            "96h_no_systemwide_hunger_freeze": mid["hunger_cap"] < 13,
            "96to168_real_jobs": a168["jobs"] > 0,
            "96to168_real_meals": a168["meals"] > 0,
            "168h_no_systemwide_hunger_freeze": last["hunger_cap"] < 13,
            "168h_all_residents_not_at_hunger_cap": last["hunger_cap"] == 0,
        }
        print("PLAY48_REOPENED_ECONOMIC_ACCEPTANCE", json.dumps({
            "gates": gate, "passed": all(gate.values()),
            "delta_72_to_96h": a96, "delta_96_to_168h": a168,
            "control_168h": results["control"][-1],
            "candidate_168h": last,
        }, sort_keys=True), flush=True)
        if not all(gate.values()):
            raise AssertionError(
                "PLAY48_ACCEPTANCE_NO_GO: authentic 96h/168h income-food cycle "
                "failed despite physical ledger and SQLite replay invariants"
            )


if __name__ == "__main__":
    run_economy_trial()
