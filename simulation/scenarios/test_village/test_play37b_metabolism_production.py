"""PLAY-37B: isolate world-time metabolism from actual NPC production.

No engine rule is changed here. Compare two independent physically identical
full-NPC villages over 48h; the only difference is a *preexisting supported*
time-zero metabolism policy. Observe whether viable labor actually emerges.
"""
from __future__ import annotations

import json

from carlos_sim import DomainEvent, LivingWorldEngine, SQLiteEventStore, TimeEngine
from carlos_sim.food_chain_diagnostics import audit_food_chain
from play_physical_supply import (
    DAY, PEOPLE, WORLD, seed_physical_supply, audit_physical_supply,
)
from play37_food_feasibility import closed_test_village_feasibility

TIMES = (0, 3600, DAY, DAY + 3600, 2 * DAY)


def _record(state):
    diagnosis = audit_food_chain(
        state, farm_site="farm", bakery_site="bakery",
        market_site="market", courier_id="huda",
    )
    jobs = state.production_jobs
    return {
        "time": state.time,
        "worker_needs": {
            who: {k: state.npcs[who]["needs"][k] for k in ("hunger", "fatigue")}
            for who in ("basim", "nora", "huda")
        },
        "hunger_cap": len(diagnosis.hunger_at_cap),
        "hunger_blocked_workers": list(diagnosis.essential_workers_hunger_blocked),
        "completed_plantings": sum(
            j["status"] == "completed" and j["recipe_id"] == "seed-planting"
            for j in jobs.values()
        ),
        "completed_harvests": sum(
            j["status"] == "completed" and j["recipe_id"] == "finite-harvest"
            for j in jobs.values()
        ),
        "completed_bakes": diagnosis.completed_bread_batches,
        "matured_lots": diagnosis.harvested_crop_lots,
        "crop_ready": diagnosis.farm_crop_ready,
        "farm_grain": diagnosis.farm_grain,
        "bakery_grain": diagnosis.bakery_grain,
        "bakery_food": diagnosis.bakery_food,
        "courier_deliveries": diagnosis.courier_deliveries,
        "courier_cargo": diagnosis.courier_carry_resource,
        "courier_block": diagnosis.courier_leg_reason,
        "market_food": diagnosis.market_food,
        "market_trades": diagnosis.trades,
        "meals": diagnosis.eaten_food_units,
        "completed_npc_rests": sum(
            a["action"] == "rest" and a["status"] == "completed"
            for a in state.actions.values()
        ),
        "completed_npc_actions": sum(
            a["status"] == "completed" for a in state.actions.values()
        ),
        "copper": diagnosis.known_copper_total,
    }


def _run(path, *, slower):
    with SQLiteEventStore(path) as db:
        seed_physical_supply(
            db, initial_market_food=3, personal_food=0,
            harvest_yield=3, market_wallets=True,
            hungry_market_buyers=True,
        )
        first = db.load(WORLD)
        if slower:
            db.append(
                WORLD, "play37b-frozen-slower-physiology", first.revision,
                [DomainEvent(
                    "MetabolismPolicyConfigured", None,
                    "trusted counterfactual uses existing declared policy", 0,
                    {"hunger_seconds_per_point": 3600,
                     "activity_hunger_percent": 20},
                )],
                bootstrap=True,
            )
        first = db.verify(WORLD)
        assert len(first.npcs) == len(PEOPLE) == 7
        b=closed_test_village_feasibility(first,horizon_seconds=3 * DAY)
        assert b.theoretical_max_food_units == 9
        assert b.minimum_food_shortfall == (3 if slower else 223)
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            engine = LivingWorldEngine(
                db, clock, max_events_per_advance=5000,
                decision_cooldown=3600, navigation_enabled=True,
                routines_enabled=True, survival_enabled=True,
                consumption_enabled=True, supply_enabled=True,
                economic_enabled=True, adaptive_market_enabled=True,
                agriculture_enabled=True, economy_only_enabled=False,
            )
            timeline = [_record(first)]
            for target in TIMES[1:]:
                while db.load(WORLD).time < target:
                    before = db.load(WORLD)
                    duration = min(DAY // 4, target - before.time)
                    after = engine.advance(
                        WORLD, seconds=duration,
                        command_id=f"play37b:{slower}:{target}:{before.time}",
                        expected_revision=before.revision,
                    ).state
                    assert after.time == before.time + duration
                    conserved = audit_physical_supply(
                        after, seed=1, water=2, buyer_copper=2,
                        personal_food=0, initial_market_food=3,
                    )
                    assert conserved["copper"] == 12
                state = db.load(WORLD)
                assert state.time == target
                timeline.append(_record(state))
                assert db.verify(WORLD).to_dict() == state.to_dict()
                db.snapshot(WORLD)
                assert db.verify(WORLD).to_dict() == state.to_dict()
            return timeline
        finally:
            clock.close_session(WORLD)


def test_only_frozen_metabolism_differs_in_real_full_npc_villages(tmp_path):
    baseline = _run(tmp_path / "standard.sqlite", slower=False)
    calibrated = _run(tmp_path / "calibrated.sqlite", slower=True)
    assert [row["time"] for row in baseline] == list(TIMES)
    assert [row["time"] for row in calibrated] == list(TIMES)
    assert baseline[0]["worker_needs"] == calibrated[0]["worker_needs"]
    assert baseline[0]["market_food"] == calibrated[0]["market_food"] == 3
    assert baseline[0]["copper"] == calibrated[0]["copper"] == 12
    # A PASS proves physically conserved observation and deterministic replay.
    # It does NOT imply that slower hunger alone solves a transport, rest or
    # resource infeasibility, or that full NPC decisions are economy-only ones.
    for series in (baseline, calibrated):
        assert series[-1]["time"] == 2 * DAY
        assert all(r["copper"] == 12 for r in series)
        assert all(0 <= r["hunger_cap"] <= 7 for r in series)
        assert all(r["completed_plantings"] <= 2 for r in series)
        assert all(r["matured_lots"] <= 2 for r in series)
        assert all(r["meals"] <= 9 for r in series)
    print("PLAY37B_REAL_FULL_NPC_METABOLISM_ONLY_48H",
          json.dumps({"baseline": baseline, "slower": calibrated},
                     sort_keys=True))
