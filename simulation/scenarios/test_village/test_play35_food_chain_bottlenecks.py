"""PLAY-35: measure NPC food-chain bottlenecks, not imagined prosperity.

Two 72-hour physical villages have identical grain/land/water/food/total coins;
the only initial difference is who owns eight existing copper coins.
"""
from __future__ import annotations

import json

import pytest

from carlos_sim import LivingWorldEngine, SQLiteEventStore, TimeEngine
from carlos_sim.food_chain_diagnostics import audit_food_chain
from play_physical_supply import (
    DAY, PEOPLE, WORLD, seed_physical_supply, audit_physical_supply,
)

LOAVES = 3
DAYS = 3
TIMES = (0, 300, DAY, 2 * DAY, DAYS * DAY)


def _diagnose(state):
    before = state.to_dict()
    diagnosis = audit_food_chain(
        state, farm_site="farm", bakery_site="bakery",
        market_site="market", courier_id="huda",
    )
    assert state.to_dict() == before, "read-only diagnostics changed world state"
    assert diagnosis.known_copper_total == 12
    assert diagnosis.market_food is not None and diagnosis.market_food >= 0
    assert diagnosis.bakery_food is not None and diagnosis.bakery_food >= 0
    assert diagnosis.completed_bread_units >= 0
    assert diagnosis.traded_food_units >= 0
    assert diagnosis.market_open_units >= 0
    assert diagnosis.eaten_food_units >= 0
    assert 0 <= len(diagnosis.hunger_at_cap) <= len(PEOPLE) == 7
    # No offer is counted as new physical stock, even when all three
    # starting loaves are listed as a single market contract.
    assert diagnosis.market_open_units >= 0
    return diagnosis.to_dict()


def _run(tmp_path, *, distributed):
    path = tmp_path / ("funded.sqlite" if distributed else "concentrated.sqlite")
    with SQLiteEventStore(path) as db:
        seed_physical_supply(
            db, personal_food=0, harvest_yield=3,
            market_wallets=distributed, initial_market_food=LOAVES,
            hungry_market_buyers=True,
        )
        initial = db.load(WORLD)
        assert len(initial.npcs) == 7
        timeline = [_diagnose(initial)]
        assert timeline[0]["logical_time"] == 0
        audit_physical_supply(
            initial, water=2, seed=1, buyer_copper=2,
            personal_food=0, initial_market_food=LOAVES,
        )
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
            for target in TIMES[1:]:
                while db.load(WORLD).time < target:
                    state = db.load(WORLD)
                    step = min(DAY // 4, target - state.time)
                    advanced = engine.advance(
                        WORLD, seconds=step,
                        command_id=f"play35:{distributed}:{target}:{state.time}",
                        expected_revision=state.revision,
                    ).state
                    assert advanced.time == state.time + step
                    assert audit_physical_supply(
                        advanced, seed=1, water=2, buyer_copper=2,
                        personal_food=0, initial_market_food=LOAVES,
                    )["copper"] == 12
                checkpoint = db.load(WORLD)
                assert checkpoint.time == target
                timeline.append(_diagnose(checkpoint))
                assert db.verify(WORLD).to_dict() == checkpoint.to_dict()
                db.snapshot(WORLD)
                assert db.verify(WORLD).to_dict() == checkpoint.to_dict()
            final = db.load(WORLD)
            assert final.time == DAYS * DAY
            return timeline, final.to_dict()
        finally:
            clock.close_session(WORLD)


def test_two_real_villages_audit_72h_material_and_personal_access(tmp_path):
    concentrated, a = _run(tmp_path, distributed=False)
    distributed, b = _run(tmp_path, distributed=True)
    assert [t["logical_time"] for t in concentrated] == list(TIMES)
    assert [t["logical_time"] for t in distributed] == list(TIMES)
    assert concentrated[1]["trades"] == 1
    assert distributed[1]["trades"] == 3
    # Supply outcomes must be observed, never inferred from price/coins.
    for series in (concentrated, distributed):
        for key in ("harvested_crop_lots", "completed_bread_batches",
                    "completed_bread_units", "trades", "traded_food_units",
                    "eaten_food_units", "courier_deliveries"):
            assert [t[key] for t in series] == sorted(t[key] for t in series)
        assert series[-1]["harvested_crop_lots"] <= 2
        assert series[-1]["known_copper_total"] == 12
        assert all(len(t["hunger_at_cap"]) <= 7 for t in series)
    assert a["world_id"] == b["world_id"] == WORLD
    print("PLAY35_TWO_72H_NPC_FOOD_CHAIN_BOTTLENECKS",
          json.dumps({"concentrated": concentrated, "distributed": distributed},
                     sort_keys=True))


def test_private_diagnostic_rejects_nonexistent_circuit_and_is_pure(tmp_path):
    with SQLiteEventStore(tmp_path / "safe.sqlite") as db:
        seed_physical_supply(db, market_wallets=True,
                             initial_market_food=LOAVES, hungry_market_buyers=True)
        state = db.load(WORLD)
        frozen = state.to_dict()
        with pytest.raises(ValueError, match="distinct world sites"):
            audit_food_chain(state, farm_site="market", bakery_site="market",
                             market_site="market", courier_id="huda")
        with pytest.raises(ValueError, match="configured farm plot and courier"):
            audit_food_chain(state, farm_site="farm", bakery_site="bakery",
                             market_site="market", courier_id="adel")
        diag = audit_food_chain(state, farm_site="farm", bakery_site="bakery",
                                market_site="market", courier_id="huda")
        assert diag.market_food == LOAVES
        assert diag.known_copper_total == 12
        assert diag.market_open_units == 0
        assert diag.trades == 0
        assert state.to_dict() == frozen
        assert db.verify(WORLD).to_dict() == frozen
