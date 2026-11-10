"""PLAY-48P read-only diagnosis: do earned wood/coal wages reach a food buyer?

Same authentic 13-NPC 2h physical scenario. Never run this operator-level
forensic projection in an NPC planner or give the actor remote market knowledge.
All movements, trades and wages are produced by the existing world engine.
"""
from __future__ import annotations
import json

from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.food_access_diagnostics import audit_food_access_barriers
from test_play48n_smith_visited_kiln import _actual_two_hours
from test_play48m_finite_employment import _seed_employed, _real_stats


def _operator_check(state):
    original = state.to_dict()
    economics = audit_npc_economy(state)
    access = audit_food_access_barriers(state)
    assert state.to_dict() == original, "forensic report must not alter world"
    assert economics["copper_scope_complete"]
    assert economics["copper_known_total"] == 12
    assert access["npc_count"] == 13
    assert access["scope"].startswith("operator-only")
    assert access["sim_time"] == state.time == 7200
    owners = economics["copper_known_by_owner"]
    assert sum(owners.values()) == 12
    actors = access["actors"]
    assert len({a["npc_id"] for a in actors}) == 13
    for person in actors:
        assert person["locally_affordable_now"] == any(
            offer["personally_affordable"]
            for offer in person["locally_listed_food"]
        )
        if person["copper_scope"] != "personal":
            assert person["personally_spendable_copper"] is None
        if person["known_road_path_to_market"] is None:
            assert person["known_road_seconds_to_market"] is None
    return {
        "locally_affordable_now_count": sum(
            p["locally_affordable_now"] for p in actors
        ),
        "owns_at_least_2_personal_copper": sum(
            p["personally_spendable_copper"] is not None
            and p["personally_spendable_copper"] >= 2
            for p in actors
        ),
        "owns_at_least_2_and_knows_market_road": sum(
            p["personally_spendable_copper"] is not None
            and p["personally_spendable_copper"] >= 2
            and p["known_road_path_to_market"] is not None
            for p in actors
        ),
        "hunger_100": access["hunger_at_100"],
        "market_food_current_on_hand": access["market_saleable_food_known"],
        "market_food_open_offer_count": access[
            "opening_food_offer_count_currently_open"
        ],
        "earnings_related_people": {
            p["npc_id"]: {
                "hunger": p["hunger"],
                "location": p["location"],
                "personal_cash": p["personally_spendable_copper"],
                "food_owned": p["known_personal_food"],
                "market_road_personally_known":
                    p["known_road_path_to_market"] is not None,
                "affordable_food_offered_at_current_site":
                    p["locally_affordable_now"],
                "has_currently_local_offer":
                    bool(p["locally_listed_food"]),
            }
            for p in actors if p["npc_id"] in
            ("layla", "burner", "smith", "huda", "hana")
        },
        "cash_ownership": owners,
    }


def test_true_two_hour_charcoal_wages_food_access_causal_audit(tmp_path):
    control = tmp_path / "no-revisit.sqlite"
    treatment = tmp_path / "with-revisit.sqlite"
    _seed_employed(control)
    _seed_employed(treatment)
    old = _actual_two_hours(control, retry=False)
    new = _actual_two_hours(treatment, retry=True)
    old_economy, new_economy = _real_stats(old), _real_stats(new)
    assert new_economy["coal_worker_wages"] >= 1
    assert new_economy["charcoal_sales"] >= 1
    assert old_economy["copper_total"] == new_economy["copper_total"] == 12
    assert old_economy["people"] == new_economy["people"] == 13
    before = _operator_check(old)
    after = _operator_check(new)
    report = {
        "sim_seconds": 7200,
        "same_people": 13,
        "same_existing_total_copper": 12,
        "control_food_access": before,
        "revisit_food_access": after,
        "control_meals": old_economy["meals"],
        "revisit_meals": new_economy["meals"],
        "control_food_sales": old_economy["bread_sales"],
        "revisit_food_sales": new_economy["bread_sales"],
        "new_charcoal_sales": new_economy["charcoal_sales"]
                              - old_economy["charcoal_sales"],
        "new_paid_jobs": new_economy["wages_paid"]
                         - old_economy["wages_paid"],
        "forensic_did_not_drive_npc_decisions": True,
        "automatic_wage_to_food_conversion_claimed": False,
        "seven_day_recovery_proven": False,
    }
    print("PLAY48P_ACTUAL_WAGE_TO_FOOD_ACCESS",
          json.dumps(report, sort_keys=True), flush=True)
