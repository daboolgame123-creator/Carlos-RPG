"""PLAY48: real prior meals permit finite courier work, never fabricated stamina."""
from carlos_sim.supply import (
    _courier_able_after_recent_genuine_meal, MAX_REAL_MEAL_ENDURANCE_SECONDS,
)

NOW = 4 * 86400

def world(hunger, when, *, who="hana", amount=1):
    return {
        "time": NOW,
        "npcs": {"hana": {"needs": {"hunger": hunger}}},
        "consumptions": {} if when is None else {"eaten-real-food": {
            "npc_id": who, "resource": "food", "quantity": amount,
            "consumed_at": when,
        }},
    }


def test_genuine_meal_at_hunger_100_allows_ongoing_labor_before_three_days():
    assert _courier_able_after_recent_genuine_meal(
        world(100,NOW-3600),"hana")

def test_genuine_meal_72h_bounded_no_perpetual_starvation_exemption():
    assert _courier_able_after_recent_genuine_meal(
        world(100,NOW-MAX_REAL_MEAL_ENDURANCE_SECONDS),"hana")
    assert not _courier_able_after_recent_genuine_meal(
        world(100,NOW-MAX_REAL_MEAL_ENDURANCE_SECONDS-1),"hana")

def test_genuine_meal_other_person_or_absent_cannot_fund_own_endurance():
    assert not _courier_able_after_recent_genuine_meal(world(100,None),"hana")
    assert not _courier_able_after_recent_genuine_meal(
        world(100,NOW-3600,who="huda"),"hana")

def test_genuine_meal_normal_hunger_vs_higher_hunger_absent_real_food():
    assert _courier_able_after_recent_genuine_meal(world(89,None),"hana")
    assert not _courier_able_after_recent_genuine_meal(world(90,None),"hana")

def test_genuine_meal_future_or_boolean_fraud_not_accepted():
    assert not _courier_able_after_recent_genuine_meal(
        world(100,NOW+10),"hana")
    assert not _courier_able_after_recent_genuine_meal(
        world(100,NOW-10,amount=True),"hana")
