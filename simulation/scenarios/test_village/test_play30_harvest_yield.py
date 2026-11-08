"""PLAY-30: one real mature crop yields bounded, provenance-backed grain.

This deliberately changes only the disposable village's trusted time-zero
recipe, not the engine's world schema or live NPC inventories by hand.
"""
from __future__ import annotations

import pytest

from carlos_sim import DomainEvent, SQLiteEventStore, TimeEngine, LivingWorldEngine
from carlos_sim.store import InvalidEvent
from play_physical_supply import (
    WORLD, DAY, TARGET, PEOPLE, seed_physical_supply, run_physical_supply,
    audit_physical_supply,
)


def test_two_real_seasons_same_water_more_grain_without_free_bread(tmp_path):
    baseline = run_physical_supply(
        tmp_path / "one-grain.sqlite", harvest_yield=1,
    )["private_test_audit_only"]
    productive = run_physical_supply(
        tmp_path / "three-grain.sqlite", harvest_yield=3,
    )["private_test_audit_only"]
    for audit in (baseline, productive):
        assert audit["grown"] == 2
        assert audit["harvests"] == 2
        assert audit["copper"] == 12
        assert audit["well_water"] == 0
        assert audit["seed"] == 1
        assert audit["deliveries"] <= audit["loads"]
        assert audit["player_issued_courier_orders"] == 0
    assert baseline["harvest_yield"] == 1
    assert productive["harvest_yield"] == 3
    assert baseline["food_equivalent"] == 2
    assert productive["food_equivalent"] == 6
    assert productive["bakes"] <= 6
    # Increased biological grain potential does not imply 6 edible,
    # market-accessible meals were bought by seven NPCs.
    print("PLAY30_REAL_YIELD_AB", {
        "legacy": {k: baseline[k] for k in ("grown", "harvests", "bakes",
                                             "deliveries", "food_equivalent")},
        "three_grain": {k: productive[k] for k in ("grown", "harvests", "bakes",
                                                  "deliveries", "food_equivalent")},
    })


@pytest.mark.parametrize("shortage", [{"water": 0}, {"seed": 0}, {"hoe": 0}])
def test_three_grain_per_crop_still_needs_actual_water_seed_and_hoe(tmp_path, shortage):
    stats = run_physical_supply(
        tmp_path / "shortage.sqlite", harvest_yield=3, **shortage,
    )["private_test_audit_only"]
    assert stats["grown"] == 0
    assert stats["harvests"] == 0
    assert stats["bakes"] == 0
    assert stats["food_equivalent"] == 0
    assert stats["copper"] == 12


@pytest.mark.parametrize("value", [0, 4, -1, 1.0, 3.0, True, False, "3", None])
def test_frozen_test_yield_is_strictly_bounded_before_world_creation(tmp_path, value):
    with SQLiteEventStore(tmp_path / "invalid.sqlite") as db:
        with pytest.raises(ValueError, match="harvest_yield"):
            seed_physical_supply(db, harvest_yield=value)


def test_omitted_yield_uses_exact_old_world_initialization(tmp_path):
    states = []
    for name, explicit in (("original", False), ("explicit-one", True)):
        with SQLiteEventStore(tmp_path / (name + ".sqlite")) as db:
            options = {"harvest_yield": 1} if explicit else {}
            seed_physical_supply(db, **options)
            state = db.load(WORLD)
            assert state.schema_version == 39 and state.rules_version == 51
            assert state.production_recipes["finite-harvest"]["output_amount"] == 1
            assert db.verify(WORLD).to_dict() == state.to_dict()
            states.append(state.to_dict())
    assert states[0] == states[1]


def test_reserved_crop_counts_as_potential_grain_before_work_finishes(tmp_path):
    with SQLiteEventStore(tmp_path / "reservation.sqlite") as db:
        seed_physical_supply(db, harvest_yield=3)
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            engine = LivingWorldEngine(
                db, clock, supply_enabled=True, agriculture_enabled=True,
                economic_enabled=True, economy_only_enabled=True,
                consumption_enabled=True,
            )
            one = engine.advance(
                WORLD, seconds=60, command_id="plant-first",
                expected_revision=db.load(WORLD).revision,
            ).state
            assert one.farm_plots["farm"]["status"] == "growing"
            # The first harvest appointment happens after a real growing day.
            grown = engine.advance(
                WORLD, seconds=DAY, command_id="mature-first",
                expected_revision=one.revision,
            ).state
            assert grown.farm_plots["farm"]["matured"] == 1
            audit = audit_physical_supply(grown, seed=1, water=2, buyer_copper=2)
            assert audit["food_equivalent"] == 3
            assert db.verify(WORLD).to_dict() == grown.to_dict()
            db.snapshot(WORLD)
            assert db.verify(WORLD).to_dict() == grown.to_dict()
        finally:
            clock.close_session(WORLD)


def test_untrusted_grain_mint_is_rejected_without_modifying_store(tmp_path):
    with SQLiteEventStore(tmp_path / "forgery.sqlite") as db:
        seed_physical_supply(db, harvest_yield=3, water=0)
        before = db.load(WORLD)
        attempted = DomainEvent(
            "ResourceChanged", None, "invent-grain", 0,
            {"owner_id": "farm", "resource": "grain", "previous": 0,
             "current": 3, "source": "initialization"},
        )
        with pytest.raises(InvalidEvent):
            db.append(WORLD, "forged-grain", before.revision, [attempted])
        assert db.verify(WORLD).to_dict() == before.to_dict()
