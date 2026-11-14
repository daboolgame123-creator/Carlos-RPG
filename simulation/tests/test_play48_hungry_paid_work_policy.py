"""PLAY-48: real work eligibility must not be confused with free food."""
from types import SimpleNamespace

import pytest

from carlos_sim.living_world import LivingWorldEngine


def engine(*, enabled, legacy=False):
    coordinator = object.__new__(LivingWorldEngine)
    coordinator.professional_full_life_enabled = True
    coordinator.hungry_paid_work_enabled = enabled
    coordinator.hungry_woodcutter_work_enabled = legacy
    return coordinator


def state(*, hunger=80, fatigue=20, safety=0, role="farmer",
          site="farm", recipe_site="farm"):
    return SimpleNamespace(
        npcs={"worker": {"role": role, "needs": {
            "hunger": hunger, "fatigue": fatigue, "safety": safety}}},
        entities={"worker": {"location_id": site}},
        production_recipes={"real-batch": {"site_id": recipe_site, "role": role}},
        injuries={},
    )


@pytest.mark.parametrize("enabled,expected", [(False, True), (True, False)])
def test_real_local_worker_can_choose_work_before_starvation(monkeypatch, enabled, expected):
    monkeypatch.setattr("carlos_sim.living_world.routine_allows_work",
                        lambda world, who: True)
    assert engine(enabled=enabled)._professional_life_emergency(
        state(), "worker") is expected


@pytest.mark.parametrize("kwargs", [
    {"hunger": 90},
    {"fatigue": 70},
    {"safety": 75},
    {"site": "well"},
    {"recipe_site": "market"},
])
def test_not_eligible_does_not_bypass_emergency(monkeypatch, kwargs):
    monkeypatch.setattr("carlos_sim.living_world.routine_allows_work",
                        lambda world, who: True)
    assert engine(enabled=True)._professional_life_emergency(
        state(**kwargs), "worker") is True


def test_off_shift_worker_must_not_bypass_emergency(monkeypatch):
    monkeypatch.setattr("carlos_sim.living_world.routine_allows_work",
                        lambda world, who: False)
    assert engine(enabled=True)._professional_life_emergency(
        state(), "worker") is True


def test_legacy_woodcutter_opt_in_stays_unchanged(monkeypatch):
    monkeypatch.setattr("carlos_sim.living_world.routine_allows_work",
                        lambda world, who: False)
    assert engine(enabled=False, legacy=True)._professional_life_emergency(
        state(role="woodcutter"), "worker") is False


def test_injured_worker_cannot_override_rest(monkeypatch):
    monkeypatch.setattr("carlos_sim.living_world.routine_allows_work",
                        lambda world, who: True)
    injured = state()
    injured.injuries["injury"] = {
        "subject_id": "worker", "severity": 100, "status": "active"}
    assert engine(enabled=True)._professional_life_emergency(
        injured, "worker") is True
