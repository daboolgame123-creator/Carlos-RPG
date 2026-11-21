"""P5: starving farmer can plant real seed only against a funded harvest future."""
import pytest

from carlos_sim.domain import WorldState
from carlos_sim.economic_autonomy import choose_local_production
from test_play48_desperate_paid_harvest import field


def planted_field(*, money=3, water=3, seed=1, hunger=100, fatigue=6,
                  at_work=True, ready=0, hoe=1):
    d = field(hunger=hunger, cash=money, ready=ready, fatigue=fatigue,
              at_work=at_work).to_dict()
    d["resources"]["farm_east"].update(
        seed=seed, water=water, hoe=hoe, crop_seeded=0)
    d["production_recipes"]["east-seed-planting"] = {
        "site_id": "farm_east", "role": "farmer",
        "input_resource": "seed", "input_amount": 1,
        "output_resource": "crop_seeded", "output_amount": 1,
        "tool_resource": "hoe", "duration_seconds": 60,
    }
    return d


def propose(d, *, new_flag=True, harvest=True):
    return choose_local_production(
        WorldState(**d), "farid", agriculture_enabled=True,
        desperate_paid_harvest_enabled=harvest,
        desperate_funded_planting_enabled=new_flag)


def test_real_funded_local_farmer_can_propose_one_seed_and_no_state_writes():
    d = planted_field()
    assert propose(d, new_flag=False) is None
    old = WorldState(**d).to_dict()
    intent = propose(d)
    assert intent is not None and intent.recipe_id == "east-seed-planting"
    assert WorldState(**d).to_dict() == old
    assert d["resources"]["farm_east"]["seed"] == 1
    assert d["resources"]["farm_east"]["coin_copper"] == 3


@pytest.mark.parametrize("change", [
    ("money", 1), ("water", 0), ("seed", 0),
    ("ready", 1), ("hoe", 0), ("fatigue", 70), ("at_work", False),
])
def test_never_start_unfunded_unwatered_dangerous_or_obstructed_planting(change):
    assert propose(planted_field(**{change[0]: change[1]})) is None


def test_no_signed_two_coin_harvest_means_no_speculative_seed():
    d = planted_field()
    d["production_recipes"]["east-finite-harvest"]["wage_coin"] = 1
    assert propose(d) is None
    d["production_recipes"]["east-finite-harvest"]["wage_coin"] = 2
    del d["production_recipes"]["east-finite-harvest"]
    assert propose(d) is None


def test_only_agreed_seed_recipe_and_no_remote_plot_spawning():
    d = planted_field()
    d["production_recipes"]["east-seed-planting"]["input_resource"] = "grain"
    assert propose(d) is None
    d = planted_field()
    d["farm_plots"]["farm_east"]["status"] = "growing"
    assert propose(d) is None


def test_option_default_changes_nothing_for_nonstarving_farmer():
    d = planted_field(hunger=70)
    assert propose(d, new_flag=False) == propose(d, new_flag=True)


@pytest.mark.parametrize("invalid", [1, 0, None, "yes", [], {}])
def test_mode_is_strict_boolean(invalid):
    with pytest.raises(ValueError, match="desperate funded planting"):
        choose_local_production(
            WorldState(**planted_field()), "farid",
            agriculture_enabled=True,
            desperate_paid_harvest_enabled=True,
            desperate_funded_planting_enabled=invalid)


def test_new_planting_flag_cannot_silently_authorize_harvest():
    d = planted_field(ready=1)
    assert propose(d, new_flag=True, harvest=False) is None
