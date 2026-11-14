"""PLAY48 fast, isolated proof: hunger never authorizes imaginary work.

Authentic thirteen-NPC time-zero village, read-only modified *selector*
snapshots (not persisted, not a claimed 96/168h economic recovery).
Tests real physically supplied wage_food jobs and the emergency priority
gate while preserving the original default opt-out.
"""
from __future__ import annotations

import pytest

from carlos_sim import LivingWorldEngine, SQLiteEventStore, TimeEngine
from carlos_sim.domain import WorldState
from carlos_sim.economic_autonomy import choose_local_production
from test_play48_peddler_fast import seed


def hungry_copy(original, who="omar", **changes):
    raw = original.to_dict()
    raw["npcs"][who]["needs"].update({"hunger": 80, "fatigue": 5, "safety": 0})
    raw["npcs"][who]["needs"].update(changes)
    return WorldState.from_dict(raw)


def engine(db, *, priority=False):
    return LivingWorldEngine(
        db, TimeEngine(db), economic_enabled=True,
        agriculture_enabled=True, navigation_enabled=True,
        routines_enabled=True, consumption_enabled=True,
        survival_enabled=True, multi_professional_markets_enabled=True,
        compound_procurement_enabled=True,
        professional_full_life_enabled=True,
        food_for_work_enabled=True,
        subsistence_work_priority_enabled=priority,
    )


def test_authentic_paid_hunter_can_choose_shift_at_80_without_overriding_survival(tmp_path):
    initial = seed(tmp_path / "original-13-real-npcs.sqlite")
    assert len(initial.npcs) == 13
    assert initial.entities["omar"]["location_id"] == "hunting_woods"
    hungry = hungry_copy(initial)
    intent = choose_local_production(hungry, "omar")
    assert intent is not None
    assert hungry.production_recipes[intent.recipe_id]["wage_food"] == 2
    assert hungry.resources["hunting_woods"]["wild_food"] >= 1
    with SQLiteEventStore(tmp_path / "original-13-real-npcs.sqlite") as db:
        default, priority = engine(db), engine(db, priority=True)
        assert default._professional_life_emergency(hungry, "omar") is True
        assert priority._professional_life_emergency(hungry, "omar") is False
        assert initial.to_dict() == db.verify(initial.world_id).to_dict()


def test_no_precarious_work_when_inputs_missing_or_too_hungry(tmp_path):
    initial = seed(tmp_path / "genuine-finite-wilderness.sqlite")
    with SQLiteEventStore(tmp_path / "genuine-finite-wilderness.sqlite") as db:
        priority = engine(db, priority=True)
        hungry = hungry_copy(initial)
        for needs in ({"hunger": 90}, {"fatigue": 70}, {"safety": 75}):
            unsafe = hungry_copy(initial, **needs)
            assert priority._professional_life_emergency(unsafe, "omar") is True
        # The business cannot invent one more wild-food lot.
        raw = hungry.to_dict()
        raw["resources"]["hunting_woods"]["wild_food"] = 0
        out_of_inputs = WorldState.from_dict(raw)
        assert choose_local_production(out_of_inputs, "omar") is None
        assert priority._professional_life_emergency(out_of_inputs, "omar") is True
        # A courier without a local paid job does not gain fictitious work.
        assert priority._professional_life_emergency(
            hungry_copy(initial, "huda"), "huda") is True


def test_priority_is_strict_opt_in(tmp_path):
    initial = seed(tmp_path / "validation-real-world.sqlite")
    with SQLiteEventStore(tmp_path / "validation-real-world.sqlite") as db:
        for bad in ("yes", 1, None):
            with pytest.raises(ValueError):
                LivingWorldEngine(db, TimeEngine(db),
                    subsistence_work_priority_enabled=bad)
        with pytest.raises(ValueError):
            LivingWorldEngine(db, TimeEngine(db),
                subsistence_work_priority_enabled=True)
        assert engine(db).subsistence_work_priority_enabled is False
        assert engine(db, priority=True).subsistence_work_priority_enabled is True
        assert len(initial.npcs) == 13
