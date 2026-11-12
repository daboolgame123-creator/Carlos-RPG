"""PLAY48 pre72 forensic experiment: READ ONLY, not an acceptance test.

Same verified 13-NPC Rules62 genesis/physical clocks in both arms.
Only the already implemented farm-sourced wage refill option differs.
No modified hunger thresholds, forced choices, extra coins, food or paths.
The output measures why wages/shops fail before the 72h standstill;
a successful CI run DOES NOT certify economic recovery.
"""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from carlos_sim import SQLiteEventStore
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.food_access_diagnostics import audit_food_access_barriers
from carlos_sim.economic_autonomy import (
    choose_local_food_purchase,
    choose_local_production,
)
from carlos_sim.market_navigation import (
    choose_known_market_walk,
    wants_local_market,
)
from test_play48aa_actual_barter_bread_return import _seed_signed_share
from test_play48h3_early_market_wage import _conserve, _run
from test_play48_13npc_post72_relay import _stats
from test_play47_closure_endurance import WORLD

HOUR = 3600
CHECKPOINT_HOURS = (24, 48, 72)


def forensic_snapshot(state):
    before = state.to_dict()
    cash = audit_npc_economy(state)
    access = audit_food_access_barriers(state)
    assert cash["copper_scope_complete"]
    assert cash["copper_known_total"] == 12
    assert access["npc_count"] == 13
    assert (state.schema_version, state.rules_version) == (45, 62)

    actors = []
    for item in access["actors"]:
        who = item["npc_id"]
        npc = state.npcs[who]
        courier = who in state.supply_circuits
        # The selectors are pure local intents. This is an operator-only audit:
        # results never feed a decision or issue an engine command.
        can_seek = wants_local_market(
            state, who, repeat_errands=True
        ) if not courier else False
        known_walk = choose_known_market_walk(
            state, who, repeat_errands=True
        ) if can_seek else None
        local_purchase = choose_local_food_purchase(
            state, who
        ) if not courier else None
        production = choose_local_production(
            state, who, agriculture_enabled=True
        )
        owned_job_wages = sum(
            j["npc_id"] == who and j["status"] == "completed"
            and "work_wage" in j
            for j in state.production_jobs.values()
        )
        genuine_meals = sum(
            m["npc_id"] == who for m in state.consumptions.values()
        )
        genuine_food_buys = sum(
            t["buyer_id"] == who and t["resource"] == "food"
            for t in state.market_trades.values()
        )
        actors.append({
            "npc": who, "role": npc["role"],
            "hunger": item["hunger"], "fatigue": item["fatigue"],
            "location": item["location"],
            "food_personal": item["known_personal_food"],
            "copper_personal": item["personally_spendable_copper"],
            "copper_scope": item["copper_scope"],
            "market_known_route": item["known_road_path_to_market"],
            "market_known_seconds": item["known_road_seconds_to_market"],
            "affordable_local_offer": item["locally_affordable_now"],
            "local_offers": item["locally_listed_food"],
            "courier_travel_blockers": item["courier_leg_blockers"],
            "shopper_wants_road": can_seek,
            "shopper_can_plan_known_road": known_walk is not None,
            "locally_buyable_by_selector": local_purchase is not None,
            "can_start_local_production": production is not None,
            "next_decision_at": npc["next_decision_at"],
            "genuine_paid_production_jobs": owned_job_wages,
            "genuine_meals": genuine_meals,
            "genuine_food_purchases": genuine_food_buys,
            "signed_unearned_food_wage": item["signed_unearned_food_wage"],
        })
    sites = {
        who: {
            "copper": cash["copper_known_by_owner"][who],
            "food": state.resources[who].get("food", 0),
            "grain": state.resources[who].get("grain", 0),
            "wood": state.resources[who].get("wood", 0),
            "charcoal": state.resources[who].get("charcoal", 0),
        }
        for who in sorted(state.locations)
        if who in state.resources and who in cash["copper_known_by_owner"]
    }
    output = {
        "hour": state.time // HOUR,
        "stats": _stats(state),
        "npc": actors,
        "sites": sites,
        "wage_receipts": cash["wage_receipts"],
        "completed_without_wage": cash["completed_without_wage_receipt"],
        "trades_by_resource": cash["trades_by_resource"],
        "paid_food_provision_receipts": {
            name: len(c["payments"])
            for name, c in sorted(state.courier_provisions.items())
        },
        "unpaid_food_provision_escrow": {
            name: c["remaining"]
            for name, c in sorted(state.courier_provisions.items())
        },
        "market_food": state.resources["market"]["food"],
        "market_food_offer_count": access["opening_food_offer_count_currently_open"],
    }
    # Forensic utilities are strictly observational and cannot mutate a
    # simulation state, route knowledge, inventory or source ledger.
    assert state.to_dict() == before
    return output


def run_probe():
    with TemporaryDirectory(prefix="play48-pre72-") as temp:
        paths = {
            label: Path(temp) / (label + ".sqlite")
            for label in ("control", "candidate")
        }
        original = _seed_signed_share(
            paths["control"], share=True, farm_refill_authority=True)
        other = _seed_signed_share(
            paths["candidate"], share=True, farm_refill_authority=True)
        assert original.to_dict() == other.to_dict()
        prior = {}
        for hour in CHECKPOINT_HOURS:
            row = {"hour": hour}
            for label in ("control", "candidate"):
                state, _ = _run(
                    paths[label], hour * HOUR,
                    early=True,
                    hungry_woodcutter_work_enabled=True,
                    retry_known_supplier_enabled=True,
                    farm_sourced_wage_refill_enabled=(label == "candidate"),
                )
                _conserve(state)
                with SQLiteEventStore(paths[label]) as db:
                    assert db.verify(WORLD).to_dict() == state.to_dict()
                    assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
                    assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
                observed = forensic_snapshot(state)
                row[label] = observed
                current = observed["stats"]
                if label in prior:
                    previous = prior[label]
                    row[label + "_since_previous"] = {
                        key: current[key] - previous[key]
                        for key in ("jobs", "food_sales", "meals", "trades")
                    }
                    row[label + "_since_previous"]["courier_deliveries"] = {
                        who: current["deliveries"][who] - previous["deliveries"][who]
                        for who in sorted(current["deliveries"])
                    }
                prior[label] = current
            print("PLAY48_PRE72_CAUSAL_AUDIT " + json.dumps(
                row, sort_keys=True), flush=True)
        print("PLAY48_PRE72_AUDIT_COMPLETE_NO_ECONOMIC_APPROVAL", flush=True)


if __name__ == "__main__":
    run_probe()
