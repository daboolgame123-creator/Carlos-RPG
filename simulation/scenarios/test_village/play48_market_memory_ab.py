"""PLAY48 market-memory economic pilot: authentic 13-NPC 24/48/72h A/B.

No resource, price, wage, water, hunger guard, route or genesis differences.
Both arms activate already-signed physical FARM pay exactly alike.
Only the optional previously-seen-food-stall recall differs, and the
underlying selector itself cannot purchase, mint stock, teleport or feed.
Economic recovery is NOT assumed from successfully running this diagnostic.
"""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from carlos_sim import SQLiteEventStore
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.food_access_diagnostics import audit_food_access_barriers
from test_play48aa_actual_barter_bread_return import _seed_signed_share
from test_play48h3_early_market_wage import _conserve, _run
from test_play48_13npc_post72_relay import _stats
from test_play47_closure_endurance import WORLD

HOUR = 3600


def report(state):
    stats = _stats(state)
    audit = audit_food_access_barriers(state)
    account = audit_npc_economy(state)
    assert len(audit["actors"]) == 13
    assert account["copper_scope_complete"] and account["copper_known_total"] == 12
    return {
        "stats": stats,
        "personal_food": {a["npc_id"]: a["known_personal_food"]
                          for a in audit["actors"]},
        "spendable_copper": {a["npc_id"]: a["personally_spendable_copper"]
                             for a in audit["actors"]},
        "hunger": {a["npc_id"]: a["hunger"] for a in audit["actors"]},
        "market_visits": {
            a["npc_id"]: sum(
                t["npc_id"] == a["npc_id"] and t["destination"] == "market"
                and t["status"] == "arrived"
                for t in state.travels.values())
            for a in audit["actors"]
        },
        "food_purchases_by_buyer": {
            a["npc_id"]: sum(
                t["buyer_id"] == a["npc_id"] and t["resource"] == "food"
                for t in state.market_trades.values())
            for a in audit["actors"]
        },
        "fully_starving": sum(a["hunger"] == 100 for a in audit["actors"]),
        "personally_afford_local_now": sum(
            a["locally_affordable_now"] for a in audit["actors"]
        ),
        "market_stock": state.resources["market"]["food"],
        "paid_production_wages": account["wage_receipts"],
    }


def compare():
    with TemporaryDirectory(prefix="play48-market-memory-") as temporary:
        paths = {label: Path(temporary) / (label + ".sqlite")
                 for label in ("control", "visited_market_memory")}
        controls = [_seed_signed_share(
            paths[label], share=True, farm_refill_authority=True)
            for label in ("control", "visited_market_memory")]
        assert controls[0].to_dict() == controls[1].to_dict()
        first = {}
        for hour in (24, 48, 72):
            row = {"hour": hour}
            for label in ("control", "visited_market_memory"):
                state, _ = _run(
                    paths[label], hour * HOUR, early=True,
                    hungry_woodcutter_work_enabled=True,
                    retry_known_supplier_enabled=True,
                    farm_sourced_wage_refill_enabled=True,
                    remember_unbought_stalls_enabled=(
                        label == "visited_market_memory"
                    ),
                )
                _conserve(state)
                with SQLiteEventStore(paths[label]) as db:
                    assert db.verify(WORLD).to_dict() == state.to_dict()
                    assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
                    assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
                row[label] = report(state)
            if hour == 24:
                first = row
            print("PLAY48_REAL_13NPC_MARKET_MEMORY_AB " +
                  json.dumps(row, sort_keys=True), flush=True)
        a, b = row["control"]["stats"], row["visited_market_memory"]["stats"]
        compare_keys = ("jobs", "trades", "food_sales", "meals", "hunger_cap")
        print("PLAY48_REAL_72H_MEMORY_CAUSAL_RESULT " + json.dumps({
            "same_genesis": True, "same_true_currency": 12,
            "only_policy_change": "remember_already_visited_food_stall_after_wage",
            "deltas": {key: b[key] - a[key] for key in compare_keys},
            "courier_delivery_deltas": {
                who: b["deliveries"][who] - a["deliveries"][who]
                for who in ("huda", "hana")
            },
            "control_at24": first["control"]["stats"],
            "candidate_at24": first["visited_market_memory"]["stats"],
            "control_at72": a, "candidate_at72": b,
            "168h_recovery_claimed": False,
            "acceptance_passed": False,
            "release_no_go": True,
        }, sort_keys=True), flush=True)


if __name__ == "__main__":
    compare()
