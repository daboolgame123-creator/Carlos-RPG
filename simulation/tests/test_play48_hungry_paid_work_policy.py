"""PLAY-48: real work eligibility must not be confused with free food."""
from types import SimpleNamespace

import pytest

from carlos_sim.living_world import LivingWorldEngine


def engine(*, enabled, legacy=False):
    coordinator = object.__new__(LivingWorldEngine)
    coordinator.professional_full_life_enabled = True
    coordinator.hungry_paid_work_enabled = enabled
    coordinator.hungry_woodcutter_work_enabled = legacy
    coordinator.agriculture_enabled = True
    coordinator.finite_aquifer_pumping_enabled = False
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


@pytest.fixture(autouse=True)
def actual_work_intent_stub(monkeypatch):
    """Emulate only the external selector's job eligibility, not its internals."""
    def eligible(world, who, **kwargs):
        here = world.entities[who]["location_id"]
        if (world.npcs[who]["needs"]["hunger"] >= 90
                or world.npcs[who]["needs"]["fatigue"] >= 70
                or world.npcs[who]["needs"]["safety"] >= 75):
            return None
        from carlos_sim.living_world import routine_allows_work
        if not routine_allows_work(world, who):
            return None
        return next((
            SimpleNamespace(job_id="physical-eligible-job")
            for recipe in world.production_recipes.values()
            if recipe["site_id"] == here
            and recipe["role"] == world.npcs[who]["role"]
        ), None)
    monkeypatch.setattr(
        "carlos_sim.economic_autonomy.choose_local_production", eligible)


def test_recipe_without_actual_startable_job_cannot_override_emergency(monkeypatch):
    # No actual inputs/available tool or depleted payroll => pure selector None.
    monkeypatch.setattr("carlos_sim.living_world.routine_allows_work",
                        lambda world, who: True)
    monkeypatch.setattr(
        "carlos_sim.economic_autonomy.choose_local_production",
        lambda world, who, **kwargs: None,
    )
    assert engine(enabled=True)._professional_life_emergency(
        state(hunger=82), "worker") is True


def test_real_selector_receives_physical_policy_flags(monkeypatch):
    monkeypatch.setattr("carlos_sim.living_world.routine_allows_work",
                        lambda world, who: True)
    seen = []
    def accepted(world, who, **kwargs):
        seen.append((who, kwargs))
        return SimpleNamespace(job_id="real-work")
    monkeypatch.setattr(
        "carlos_sim.economic_autonomy.choose_local_production", accepted)
    assert engine(enabled=True)._professional_life_emergency(
        state(hunger=83), "worker") is False
    assert seen == [("worker", {
        "agriculture_enabled": True, "finite_aquifer_enabled": False,
    })]


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
