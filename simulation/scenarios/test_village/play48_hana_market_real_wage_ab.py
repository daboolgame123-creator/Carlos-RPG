"""PLAY48: one authentic initial market loaf escrowed for Hana's delivered service.

This is a controlled, read-only observer of TWO independently running genuine
13-NPC worlds. The candidate changes only the time-zero, employer-authorized
ownership of ONE preexisting physical market loaf: offerable market stock 1->0,
durable signed unpaid courier escrow 0->1 for Hana. No new bread, cash, roads,
roles, delivery, credit, knowledge or unsafe movement.

The original signed farm-Huda provision and all other engine flags are same.
A test finishing green does not imply a post72 recovery or release approval.
"""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from carlos_sim import DomainEvent, SQLiteEventStore
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.food_access_diagnostics import audit_food_access_barriers
from test_play48aa_actual_barter_bread_return import _seed_signed_share
from test_play48h3_early_market_wage import _conserve, _run
from test_play48_13npc_post72_relay import _stats
from test_play47_closure_endurance import WORLD

HOUR = 3600
CHECKPOINTS = (24, 48, 72)
CONTRACT = "market-hana-existing-loaf-for-food-delivery"


def _seed(path: Path, *, market_hana_signed: bool):
    original = _seed_signed_share(
        path, share=True, farm_refill_authority=True,
    )
    assert len(original.npcs) == 13
    assert original.time == 0
    assert original.resources["market"]["food"] == 1
    assert original.resources["farm"]["food"] == 0
    assert original.resources["hana"]["food"] == 0
    assert sum(c["remaining"] for c in original.courier_provisions.values()) == 2
    assert audit_npc_economy(original)["copper_known_total"] == 12
    if not market_hana_signed:
        return original
    with SQLiteEventStore(path) as db:
        signed = db.append(
            WORLD, "play48:real-market-hana-opening-food-escrow",
            original.revision,
            [DomainEvent(
                "CourierProvisionConfigured", None,
                "the market's existing loaf reserved for verified Hana food-delivery service",
                0,
                {"id": CONTRACT, "courier_id": "hana",
                 "payer_site": "market", "units": 1},
            )],
            bootstrap=True,
        )
        assert signed.resources["market"]["food"] == 0
        assert signed.resources["hana"]["food"] == 0
        assert signed.courier_provisions[CONTRACT]["remaining"] == 1
        assert signed.courier_provisions[CONTRACT]["total_units"] == 1
        assert sum(c["remaining"] for c in signed.courier_provisions.values()) == 3
        assert signed.courier_provisions["farm-water-huda"] == (
            original.courier_provisions["farm-water-huda"]
        )
        assert audit_npc_economy(signed)["copper_known_total"] == 12
        assert db.verify(WORLD).to_dict() == signed.to_dict()
    return signed


def _report(state):
    audit = audit_food_access_barriers(state)
    cash = audit_npc_economy(state)
    assert len(state.npcs) == 13
    assert cash["copper_scope_complete"] and cash["copper_known_total"] == 12
    assert (state.schema_version, state.rules_version) == (45, 62)
    before = state.to_dict()
    result = {
        "stats": _stats(state),
        "market_physically_unconsigned_bread": state.resources["market"]["food"],
        "hunger": {a["npc_id"]: a["hunger"] for a in audit["actors"]},
        "personally_owned_food": {
            a["npc_id"]: a["known_personal_food"] for a in audit["actors"]
        },
        "courier_earned_food_provision_receipts": {
            c["courier_id"]: len(c["payments"])
            for _, c in sorted(state.courier_provisions.items())
        },
        "courier_remaining_signed_food_escrow": {
            c["courier_id"]: c["remaining"]
            for _, c in sorted(state.courier_provisions.items())
        },
        "hana_meals": sum(
            x["npc_id"] == "hana" for x in state.consumptions.values()
        ),
        "hana_food_purchase_count": sum(
            x["buyer_id"] == "hana" and x["resource"] == "food"
            for x in state.market_trades.values()
        ),
    }
    assert state.to_dict() == before
    return result


def compare():
    with TemporaryDirectory(prefix="play48-hana-real-paid-food-") as temp:
        paths = {
            who: Path(temp) / (who + ".sqlite")
            for who in ("unmodified", "pre_signed_market_hana")
        }
        a = _seed(paths["unmodified"], market_hana_signed=False)
        b = _seed(paths["pre_signed_market_hana"], market_hana_signed=True)
        # Explicit trusted birth-allocation change, not an identical genesis.
        # The displaced loaf is in *real market-owned escrow*, not Hana's
        # pocket, until the same-command authenticated delivery is completed.
        assert a.resources["market"]["food"] == b.resources["market"]["food"] + 1
        assert len(b.courier_provisions) == len(a.courier_provisions) + 1
        for target in CHECKPOINTS:
            row = {"hour": target}
            for label, path in paths.items():
                state, _ = _run(
                    path, target * HOUR, early=True,
                    hungry_woodcutter_work_enabled=True,
                    retry_known_supplier_enabled=True,
                    farm_sourced_wage_refill_enabled=True,
                    remember_unbought_stalls_enabled=True,
                )
                _conserve(state)
                with SQLiteEventStore(path) as db:
                    assert db.verify(WORLD).to_dict() == state.to_dict()
                    assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
                    assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
                row[label] = _report(state)
            print(
                "PLAY48_HANA_AUTHENTIC_SIGNED_MARKET_FOOD_WAGE_AB " +
                json.dumps(row, sort_keys=True), flush=True,
            )
        a = row["unmodified"]
        b = row["pre_signed_market_hana"]
        metrics = ("jobs", "food_sales", "meals", "hunger_cap", "wages")
        print(
            "PLAY48_HANA_72H_FIRSTHAND_SERVICE_WAGE_RESULT " +
            json.dumps({
                "same_total_initial_actual_food_and_copper": True,
                "single_genesis_difference":
                    "one existing market food unit escrowed for Hana's verified physical service",
                "no_emergency_grant_or_safety_bypass": True,
                "copper_unchanged_at_12": True,
                "at72_control": a["stats"],
                "at72_candidate": b["stats"],
                "actual_deltas": {
                    key: b["stats"][key] - a["stats"][key] for key in metrics
                },
                "hana_real_wage_receipts": (
                    a["courier_earned_food_provision_receipts"].get("hana", 0),
                    b["courier_earned_food_provision_receipts"].get("hana", 0),
                ),
                "hana_personal_meals": (a["hana_meals"], b["hana_meals"]),
                "no_96h_or_168h_acceptance_claimed": True,
                "release_no_go": True,
            }, sort_keys=True), flush=True,
        )


if __name__ == "__main__":
    compare()
