"""Opt-in PLAY48 harvest rescue: never mint food, copper, labor or water."""
import pytest

from carlos_sim.domain import WorldState
from carlos_sim.economic_autonomy import choose_local_production


def field(*, hunger=100, cash=5, ready=1, fatigue=6,
          at_work=True, tool=1, recipe="east-finite-harvest",
          duration=60, safety=0):
    return WorldState(
        world_id="desperate-farm",
        time=168 * 3600,
        locations={"farm_east": {}, "market": {}},
        entities={"farid": {"controller": "npc",
                            "location_id": "farm_east" if at_work else "market"}},
        npcs={"farid": {
            "role": "farmer", "last_decision": None,
            "needs": {"hunger": hunger, "fatigue": fatigue, "safety": safety},
        }},
        resources={"farm_east": {
            "crop_ready":ready,"coin_copper":cash,"sickle":tool,
            "grain":0, "seed":1, "water":3}},
        production_recipes={recipe:{
            "site_id":"farm_east","role":"farmer",
            "input_resource":"crop_ready","input_amount":1,
            "output_resource":"grain","output_amount":2,
            "tool_resource":"sickle","duration_seconds":duration,
            "wage_coin":2,
        }},
        npc_routines={"farid":{
            "workplace_id":"farm_east", "home_id":"market",
            "work_start":0,"work_end":30000,
        }},
        farm_plots={"farm_east":{"site_id":"farm_east","status":"idle"}},
    )


def choose(state, flag=True):
    return choose_local_production(
        state,"farid", agriculture_enabled=True,
        desperate_paid_harvest_enabled=flag,
    )


def test_original_starving_worker_remains_blocked_by_default():
    s=field()
    assert choose(s,False) is None
    before=s.to_dict()
    intent=choose(s,True)
    assert intent is not None and intent.recipe_id=="east-finite-harvest"
    assert s.to_dict()==before
    assert s.resources["farm_east"]["coin_copper"]==5
    assert s.resources["farm_east"]["crop_ready"]==1


@pytest.mark.parametrize("changes",[
    {"cash":1},{"ready":0},{"at_work":False},{"fatigue":70},
    {"tool":0},{"safety":75},{"duration":301},
    {"recipe":"east-seed-planting"},
])
def test_no_desperate_harvest_when_unfunded_unripe_unsafe_or_unavailable(changes):
    assert choose(field(**changes)) is None


def test_less_hungry_worker_keeps_existing_offline_behavior():
    s=field(hunger=70)
    assert choose(s,False)==choose(s,True)


def test_opt_in_requires_strict_boolean():
    with pytest.raises(ValueError):
        choose_local_production(
            field(),"farid", agriculture_enabled=True,
            desperate_paid_harvest_enabled=1,
        )


def test_never_allows_other_resources_or_role_to_fake_finite_paid_harvest():
    s=field().to_dict()
    s["production_recipes"]["east-finite-harvest"]["wage_coin"]=0
    assert choose(WorldState(**s)) is None
    s["production_recipes"]["east-finite-harvest"]["wage_coin"]=2
    s["npcs"]["farid"]["role"]="baker"
    assert choose(WorldState(**s)) is None
