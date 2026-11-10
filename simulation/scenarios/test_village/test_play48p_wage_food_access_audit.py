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


def test_true_first_day_bakery_grain_location_and_access_audit(tmp_path):
    """Locate observed grain/food after a real day; never spawn a buffer."""
    from test_play47_closure_endurance import DAY, WORLD
    from test_play48h3_early_market_wage import _run
    from carlos_sim import SQLiteEventStore

    path = tmp_path / "physical-food-chain-day1.sqlite"
    _seed_employed(path)
    state, history = _run(
        path, DAY, early=False,
        hungry_woodcutter_work_enabled=True,
        retry_known_supplier_enabled=True,
    )
    assert state.time == DAY and len(history) == 1
    economy = audit_npc_economy(state)
    access = audit_food_access_barriers(state)
    before = state.to_dict()
    assert economy["copper_known_total"] == 12
    assert len(state.npcs) == access["npc_count"] == 13
    per_site = {
        owner: {
            resource: stock[resource]
            for resource in ("grain", "food", "crop_ready", "water")
            if type(stock.get(resource)) is int and stock[resource] > 0
        }
        for owner, stock in sorted(state.resources.items())
    }
    per_site = {owner: stock for owner, stock in per_site.items() if stock}
    baker = _real_stats(state)["bakery_buffer"]
    assert baker["owned_local_grain"] == state.resources["bakery"]["grain"]
    assert baker["missing_grain"] == max(0, 3 - baker["owned_local_grain"])
    assert state.to_dict() == before
    with SQLiteEventStore(path) as db:
        assert db.verify(WORLD).to_dict() == before
        assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
    report = {
        "time": DAY, "same_thirteen_people": True,
        "same_twelve_existing_copper": True,
        "positive_actual_physical_stock_by_site": per_site,
        "bakery_three_grain_target": baker,
        "market_food_site_stock": access["market_saleable_food_known"],
        "hunger_100": access["hunger_at_100"],
        "food_sales": _real_stats(state)["bread_sales"],
        "meals": _real_stats(state)["meals"],
        "farm_courier_deliveries": history[0]["economy"]["deliveries"],
        "no_material_fabrication_or_npc_commands": True,
        "production_and_7day_recovery_not_assumed": True,
    }
    print("PLAY48P_DAY1_BAKERY_REAL_GRAIN_CHAIN",
          json.dumps(report, sort_keys=True), flush=True)


def test_real_24_48h_grain_chain_not_confused_with_zero_daily_stock(tmp_path):
    """Distinguish no grain delivery from delivered grain promptly baked.

    Uses genuine rain, first-hand physical routes, and production receipts.
    All event inspection is external operator forensics after autonomous run.
    """
    from collections import Counter
    from carlos_sim import SQLiteEventStore
    from carlos_sim.supply_diagnostics import audit_courier
    from test_play47_closure_endurance import DAY, WORLD
    from test_play48h3_early_market_wage import _run

    path = tmp_path / "real-13-food-supply-48h.sqlite"
    _seed_employed(path)
    checkpoints = []
    for day in (1, 2):
        state, history = _run(
            path, day * DAY, early=False,
            hungry_woodcutter_work_enabled=True,
            retry_known_supplier_enabled=True,
        )
        assert len(history) == 1 and state.time == day * DAY
        assert audit_npc_economy(state)["copper_known_total"] == 12
        assert len(state.npcs) == 13
        original = state.to_dict()
        counts = Counter()
        unfinished = Counter()
        for job in state.production_jobs.values():
            recipe = state.production_recipes[job["recipe_id"]]
            if job["status"] == "completed":
                counts[(job["site_id"], recipe["output_resource"])] += 1
            else:
                unfinished[(job["site_id"], recipe["output_resource"])] += 1

        with SQLiteEventStore(path) as db:
            rows = [json.loads(row[0]) for row in db.db.execute(
                "SELECT payload FROM events WHERE world_id=? ORDER BY seq",
                (WORLD,)
            )]
            assert db.verify(WORLD).to_dict() == original
            assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
            assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
        delivery_counts = Counter(
            e["data"]["resource"] for e in rows
            if e["event_type"] == "SupplyCargoDelivered"
        )
        # Standard trusted courier contracts use real legs for grain farm
        # -> bakery and for food bakery -> market. We count durable events,
        # not infer deliveries from an empty instantaneous inventory snapshot.
        baker = _real_stats(state)["bakery_buffer"]
        assert baker["owned_local_grain"] == state.resources["bakery"]["grain"]
        couriers = {
            who: audit_courier(state, who, supply_enabled=True)
            for who in ("huda", "hana")
        }
        access = audit_food_access_barriers(state)
        assert state.to_dict() == original
        checkpoints.append({
            "day": day,
            "time": state.time,
            "farm_grain_completed_jobs": sum(
                n for (site, output), n in counts.items()
                if output == "grain" and site in ("farm", "farm_east")
            ),
            "bakery_food_completed_jobs": counts.get(("bakery", "food"), 0),
            "grain_physical_courier_deliveries": delivery_counts["grain"],
            "baked_food_physical_courier_deliveries": delivery_counts["food"],
            "running_food_jobs": unfinished.get(("bakery", "food"), 0),
            "bakery_grain_on_hand": baker["owned_local_grain"],
            "bakery_buffer_shortfall": baker["missing_grain"],
            "farm_grain_on_hand": {
                field: state.resources[field].get("grain")
                for field in ("farm", "farm_east")
            },
            "market_food_on_hand": access["market_saleable_food_known"],
            "hunger_100": access["hunger_at_100"],
            "completed_food_sales": _real_stats(state)["bread_sales"],
            "recorded_meals": _real_stats(state)["meals"],
            "courier_status": {
                who: {
                    "hunger": report["needs"]["hunger"],
                    "contract_index": report["contract_index"],
                    "next_action": report["next_action"],
                    "blocked_reasons": report["blocked_reasons"],
                    "deliveries": report["deliveries"],
                } for who, report in couriers.items()
            },
        })
    print("PLAY48P_REAL_48H_GRAIN_TO_BREAD_OPERATOR_TRACE",
          json.dumps({
              "checkpoints": checkpoints,
              "opening_food_loaves": 3,
              "real_total_copper_every_day": 12,
              "new_grain_or_cash_injected": False,
              "unverified_7day_recovery_claimed": False,
              "forensics_do_not_change_npc_choices": True,
          }, sort_keys=True), flush=True)
