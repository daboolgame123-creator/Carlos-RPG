"""PLAY-36: zero-sum pre-positioned food vs market-first initial allocation.

Nothing is granted while the world runs. These are *two alternative trusted
starting states*, not a magic delivery service or a permanent wage policy.
"""
from __future__ import annotations

import json

import pytest

from carlos_sim import LivingWorldEngine, SQLiteEventStore, TimeEngine
from carlos_sim.food_chain_diagnostics import audit_food_chain
from play_physical_supply import (
    DAY, PEOPLE, WORLD, seed_physical_supply, audit_physical_supply,
)

WORKERS = ("basim", "nora", "huda")
CHECKPOINTS = (0, 300, 3600, DAY, 2 * DAY, 3 * DAY)


def _visible_diagnostic(state):
    d = audit_food_chain(state, farm_site="farm", bakery_site="bakery",
                         market_site="market", courier_id="huda")
    return {
        "time": state.time,
        "worker_hunger": {who: state.npcs[who]["needs"]["hunger"]
                          for who in WORKERS},
        "worker_food": {who: state.resources[who]["food"] for who in WORKERS},
        "worker_meals": {
            who: sum(m["quantity"] for m in state.consumptions.values()
                     if m["npc_id"] == who)
            for who in WORKERS
        },
        "all_meals": d.eaten_food_units,
        "market_food": d.market_food,
        "market_copper": state.resources["market"]["coin_copper"],
        "bread_batches": d.completed_bread_batches,
        "field_crop_ready": d.farm_crop_ready,
        "field_matured": d.harvested_crop_lots,
        "courier_deliveries": d.courier_deliveries,
        "courier_leg_reason": d.courier_leg_reason,
        "high_risk": len(d.high_risk_without_food),
        "hunger_cap": len(d.hunger_at_cap),
        "trades": d.trades,
        "copper": d.known_copper_total,
    }


def _run(path, *, staff_provisions):
    with SQLiteEventStore(path) as db:
        seed_physical_supply(
            db, personal_food=0, initial_market_food=3, harvest_yield=3,
            market_wallets=True, hungry_market_buyers=True,
            staff_provisions=staff_provisions,
        )
        first = db.load(WORLD)
        assert len(first.npcs) == len(PEOPLE) == 7
        assert first.time == 0
        assert first.resources["market"]["food"] == (0 if staff_provisions else 3)
        assert tuple(first.resources[who]["food"] for who in WORKERS) == (
            (1, 1, 1) if staff_provisions else (0, 0, 0))
        assert audit_physical_supply(
            first, seed=1, water=2, buyer_copper=2,
            personal_food=0, initial_market_food=3,
        )["food_equivalent"] == 3
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            engine = LivingWorldEngine(
                db, clock, max_events_per_advance=5000,
                decision_cooldown=3600, navigation_enabled=True,
                routines_enabled=True, survival_enabled=True,
                consumption_enabled=True, supply_enabled=True,
                economic_enabled=True, adaptive_market_enabled=True,
                agriculture_enabled=True, economy_only_enabled=True,
            )
            timeline = [_visible_diagnostic(first)]
            for at in CHECKPOINTS[1:]:
                while db.load(WORLD).time < at:
                    before = db.load(WORLD)
                    seconds = min(DAY // 4, at - before.time)
                    state = engine.advance(
                        WORLD, seconds=seconds,
                        command_id=f"play36:{staff_provisions}:{at}:{before.time}",
                        expected_revision=before.revision,
                    ).state
                    assert state.time == before.time + seconds
                    conserved = audit_physical_supply(
                        state, seed=1, water=2, buyer_copper=2,
                        personal_food=0, initial_market_food=3,
                    )
                    assert conserved["copper"] == 12
                state = db.load(WORLD)
                assert state.time == at
                timeline.append(_visible_diagnostic(state))
                assert db.verify(WORLD).to_dict() == state.to_dict()
                db.snapshot(WORLD)
                assert db.verify(WORLD).to_dict() == state.to_dict()
            return timeline, db.load(WORLD).to_dict()
        finally:
            clock.close_session(WORLD)


def test_seven_npcs_market_first_vs_worker_rations_72h(tmp_path):
    market, market_state = _run(tmp_path / "market.sqlite", staff_provisions=False)
    staff, staff_state = _run(tmp_path / "staff.sqlite", staff_provisions=True)
    assert [record["time"] for record in market] == list(CHECKPOINTS)
    assert [record["time"] for record in staff] == list(CHECKPOINTS)
    assert all(t["copper"] == 12 and 0 <= t["hunger_cap"] <= 7
               for t in market + staff)
    assert market_state["world_id"] == staff_state["world_id"] == WORLD
    assert market[0]["worker_meals"] == staff[0]["worker_meals"] == {
        who: 0 for who in WORKERS}
    assert market[0]["all_meals"] == staff[0]["all_meals"] == 0
    assert market[0]["market_food"] + sum(market[0]["worker_food"].values()) == 3
    assert staff[0]["market_food"] + sum(staff[0]["worker_food"].values()) == 3
    # Count actual consumption and job records; do not declare that the
    # staff survive or that any baked food is guaranteed by three extra meals.
    assert all(t["all_meals"] >= 0 and t["bread_batches"] >= 0
               and t["courier_deliveries"] >= 0 for t in market + staff)
    print("PLAY36_FINITE_STAFF_FOOD_ALLOCATIONS_72H",
          json.dumps({"market_first": market, "worker_provisions": staff},
                     sort_keys=True))


@pytest.mark.parametrize("invalid", [None, "yes", 1, 0, [], {}, 2.0])
def test_staff_rations_option_must_be_real_boolean(tmp_path, invalid):
    with SQLiteEventStore(tmp_path / "invalid.sqlite") as db:
        with pytest.raises(ValueError, match="staff_provisions"):
            seed_physical_supply(db, personal_food=0, initial_market_food=3,
                                 staff_provisions=invalid)


@pytest.mark.parametrize("market_food,personal_food", [(0, 0), (1, 0), (2, 0), (3, 1)])
def test_staff_rations_cannot_be_added_on_top_of_existing_stock(
        tmp_path, market_food, personal_food):
    with SQLiteEventStore(tmp_path / "invalid-stock.sqlite") as db:
        with pytest.raises(ValueError, match="staff_provisions"):
            seed_physical_supply(
                db, initial_market_food=market_food, personal_food=personal_food,
                staff_provisions=True,
            )


def test_initial_food_ownership_is_replayable_and_initial_time_frozen(tmp_path):
    with SQLiteEventStore(tmp_path / "seed-only.sqlite") as db:
        seed_physical_supply(db, initial_market_food=3, staff_provisions=True)
        state = db.verify(WORLD)
        assert state.time == 0
        assert state.resources["market"]["food"] == 0
        assert sum(state.resources[who]["food"] for who, *_ in PEOPLE) == 3
        assert sum(state.resources[who]["food"] for who in WORKERS) == 3
        assert sum(v["coin_copper"] for v in state.resources.values()
                   if "coin_copper" in v) == 12
        db.snapshot(WORLD)
        assert db.verify(WORLD).to_dict() == state.to_dict()
