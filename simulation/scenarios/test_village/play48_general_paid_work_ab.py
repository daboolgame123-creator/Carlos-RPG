"""PLAY-48: read-only causal A/B of the proposed hunger-work precedence.

Authentic 13-resident Rules63 village, same seeded ownership, weather, clocks,
routes, recipes and work contracts. The only changed engine flag is
hungry_paid_work_enabled. A green diagnostic is NOT economic release approval.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from carlos_sim import LivingWorldEngine, SQLiteEventStore, TimeEngine
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.food_access_diagnostics import audit_food_access_barriers
from carlos_sim.hydrology import FiniteWaterService
from test_play48_authorized_food_for_work import seed
from test_play48h3_early_market_wage import _conserve
from test_play48_13npc_post72_relay import _stats
from test_play47_closure_endurance import WORLD

HOUR = 3600
CHECKPOINT_HOURS = (24, 48, 72, 96, 168)


def reading(state):
    before = state.to_dict()
    cash = audit_npc_economy(state)
    access = audit_food_access_barriers(state)
    assert len(state.npcs) == access["npc_count"] == 13
    assert (state.schema_version, state.rules_version) == (45, 63)
    assert cash["copper_scope_complete"] and cash["copper_known_total"] == 12
    report = _stats(state)
    report["seller_hunger"] = state.npcs["salma"]["needs"]["hunger"]
    report["seller_at_market"] = (
        state.entities["salma"]["location_id"] == "market"
    )
    report["hunger_75_plus"] = sum(
        n["needs"]["hunger"] >= 75 for n in state.npcs.values()
    )
    report["hungry_without_personal_cash_and_food"] = sum(
        actor["hunger"] >= 75
        and actor["personally_spendable_copper"] == 0
        and actor["known_personal_food"] == 0
        for actor in access["actors"]
    )
    report["genuine_food_wages"] = sum(
        "food_wage" in job for job in state.production_jobs.values()
    )
    report["genuine_courier_food_wages"] = sum(
        len(contract["payments"]) for contract in state.courier_provisions.values()
    )
    report["site_food"] = {
        site: state.resources[site].get("food", 0)
        for site in ("farm", "farm_east", "bakery", "market")
    }
    assert state.to_dict() == before, "operator audit must be read-only"
    return report


def run_arm(path: Path, *, enabled: bool, hours: int):
    readings = {}
    with SQLiteEventStore(path) as db:
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            engine = LivingWorldEngine(
                db, clock, max_events_per_advance=5000,
                decision_cooldown=3600,
                economic_enabled=True, agriculture_enabled=True,
                navigation_enabled=True, routines_enabled=True,
                consumption_enabled=True, survival_enabled=True,
                supply_enabled=True, shopping_routes_enabled=True,
                multi_professional_markets_enabled=True,
                compound_procurement_enabled=True,
                professional_full_life_enabled=True,
                food_for_work_enabled=True,
                hungry_paid_work_enabled=enabled,
            )
            state = db.verify(WORLD)
            for hour in range(6, hours + 1, 6):
                state = engine.advance(
                    WORLD, seconds=6 * HOUR,
                    command_id=f"paid-work-ab:{hour}",
                    expected_revision=state.revision,
                ).state
                if hour in (24, 48, 72):
                    state = FiniteWaterService(db, clock).record(
                        WORLD, "well", f"paid-work-observed-rain-{hour}", 2,
                        command_id=f"paid-work-rain-{hour}",
                        expected_revision=state.revision,
                    ).state
                _conserve(state)
                if hour in CHECKPOINT_HOURS:
                    assert db.verify(WORLD).to_dict() == state.to_dict()
                    assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
                    assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
                    readings[hour] = reading(state)
            assert db.snapshot(WORLD).to_dict() == state.to_dict()
        finally:
            clock.close_session(WORLD)
    with SQLiteEventStore(path) as reopened:
        assert reopened.verify(WORLD).to_dict() == state.to_dict()
        assert reopened.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert reopened.db.execute("PRAGMA foreign_key_check").fetchall() == []
    return readings


def compare(hours: int):
    if hours not in CHECKPOINT_HOURS:
        raise ValueError("hours must be a diagnostic checkpoint (24/48/72/96/168)")
    with TemporaryDirectory(prefix="play48-paid-work-ab-") as temp:
        paths = {
            label: Path(temp) / (label + ".sqlite")
            for label in ("control", "candidate")
        }
        original = seed(paths["control"])
        candidate = seed(paths["candidate"])
        assert original.to_dict() == candidate.to_dict()
        assert len(original.npcs) == 13
        results = {
            "control": run_arm(paths["control"], enabled=False, hours=hours),
            "candidate": run_arm(paths["candidate"], enabled=True, hours=hours),
        }
        for hour in sorted(results["control"]):
            left = results["control"][hour]
            right = results["candidate"][hour]
            measures = ("jobs", "wages", "food_sales", "meals",
                        "hunger_cap", "hunger_75_plus", "trades",
                        "genuine_food_wages", "genuine_courier_food_wages")
            deltas = {key: right[key] - left[key] for key in measures}
            delivery_deltas = {
                who: right["deliveries"][who] - left["deliveries"][who]
                for who in left["deliveries"]
            }
            print("PLAY48_REAL_13NPC_PAID_WORK_AB " + json.dumps({
                "hour": hour,
                "control": left,
                "candidate": right,
                "deltas": deltas,
                "delivery_deltas": delivery_deltas,
                "sole_policy_difference": "hungry_paid_work_enabled",
                "copper_conserved": True,
                "food_and_water_conservation_asserted": True,
                "sqlite_replay_and_integrity_asserted": True,
                "168h_recovery_verified": False if hours < 168 else None,
                "release_no_go": True,
            }, sort_keys=True), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--hours", type=int, choices=CHECKPOINT_HOURS,
                        default=48)
    compare(parser.parse_args().hours)
