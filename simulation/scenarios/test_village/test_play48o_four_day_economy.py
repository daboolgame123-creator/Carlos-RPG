"""PLAY-48O — genuine 13-NPC 24/48/72/96h wood/charcoal economy A/B.

No new NPC, coin, grain, bread, or foreknowledge. Both villages use the
same PLAY-48M finite-employment genesis, weather and time partitions;
only the opt-in firsthand supplier retry differs. This is an observational
counterfactual, not a promise of four-day recovery or a policy change.
"""
from __future__ import annotations

import json

from carlos_sim import SQLiteEventStore
from carlos_sim.economic_diagnostics import audit_npc_economy
from test_play47_closure_endurance import DAY, WORLD
from test_play48h3_early_market_wage import _run
from test_play48m_finite_employment import _seed_employed, _real_stats


def _four_day_checkpoints(path, *, firsthand_retry):
    opening = _seed_employed(path)
    assert len(opening.npcs) == 13
    assert _real_stats(opening)["copper_total"] == 12
    rows = []
    for day in range(1, 5):
        state, history = _run(
            path, day * DAY, early=False,
            hungry_woodcutter_work_enabled=True,
            retry_known_supplier_enabled=firsthand_retry,
        )
        assert state.time == day * DAY
        assert len(history) == 1
        metrics = _real_stats(state)
        assert metrics["people"] == 13
        assert metrics["copper_total"] == 12
        assert metrics["forest_timber_left"] + metrics["wood_jobs"] == 3
        assert metrics["woodcutter_wages"] <= metrics["wood_jobs"]
        assert metrics["coal_worker_wages"] <= metrics["charcoal_jobs"]
        assert all(
            amount >= 0
            for stock in state.resources.values()
            for amount in stock.values()
            if type(amount) is int
        )
        buffer = metrics["bakery_buffer"]
        assert buffer["owned_local_grain"] >= 0
        assert buffer["missing_grain"] == max(
            0, buffer["target_grain"] - buffer["owned_local_grain"]
        )
        assert buffer["stock_filled"] == (
            buffer["owned_local_grain"] >= buffer["target_grain"]
        )
        rows.append({
            "day": day,
            "time": state.time,
            "wood_jobs": metrics["wood_jobs"],
            "wood_sales": metrics["wood_sales"],
            "charcoal_jobs": metrics["charcoal_jobs"],
            "charcoal_sales": metrics["charcoal_sales"],
            "woodcutter_wages": metrics["woodcutter_wages"],
            "charcoal_worker_wages": metrics["coal_worker_wages"],
            "food_sales": metrics["bread_sales"],
            "meals": metrics["meals"],
            "hunger_100": metrics["hunger_100"],
            "bakery_buffer": buffer,
            "deliveries": history[0]["economy"]["deliveries"],
            "total_completed_jobs": history[0]["economy"]["jobs"],
            "total_trades": history[0]["economy"]["trades"],
            "total_work_wages": history[0]["economy"]["wages"],
        })
        # The 24/48/72/96h checkpoints must survive an actual SQLite close
        # and reopen, including complete event replay and referential integrity.
        with SQLiteEventStore(path) as reopened:
            assert reopened.verify(WORLD).to_dict() == state.to_dict()
            assert reopened.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
            assert reopened.db.execute("PRAGMA foreign_key_check").fetchall() == []
        cash = audit_npc_economy(state)
        assert cash["copper_scope_complete"] and cash["copper_known_total"] == 12
    return rows


def _post72_changes(rows):
    before, after = rows[2], rows[3]
    cols = ("wood_jobs", "wood_sales", "charcoal_jobs",
            "charcoal_sales", "woodcutter_wages", "charcoal_worker_wages",
            "food_sales", "meals", "total_completed_jobs",
            "total_trades", "total_work_wages")
    diffs = {name: after[name] - before[name] for name in cols}
    diffs["deliveries"] = {
        name: after["deliveries"][name] - before["deliveries"][name]
        for name in ("huda", "hana")
    }
    assert all(n >= 0 for name, n in diffs.items() if name != "deliveries")
    assert all(n >= 0 for n in diffs["deliveries"].values())
    diffs["hunger_cap_before"] = before["hunger_100"]
    diffs["hunger_cap_after"] = after["hunger_100"]
    return diffs


def test_true_13npc_wood_charcoal_four_day_repeat_visit_vs_one_visit(tmp_path):
    old = _four_day_checkpoints(
        tmp_path / "same-jobs-no-fuel-revisit.sqlite",
        firsthand_retry=False,
    )
    retry = _four_day_checkpoints(
        tmp_path / "same-jobs-physical-revisit.sqlite",
        firsthand_retry=True,
    )
    assert [x["time"] for x in old] == [x["time"] for x in retry] == [
        DAY, 2 * DAY, 3 * DAY, 4 * DAY
    ]
    base_delta, retry_delta = _post72_changes(old), _post72_changes(retry)
    recovery = (
        any(x > 0 for x in retry_delta["deliveries"].values())
        and any(retry_delta[k] > 0
                for k in ("total_completed_jobs", "total_trades", "meals",
                          "food_sales"))
    )
    report = {
        "same_original_13_people": True,
        "exact_copper_in_each_world": 12,
        "initial_loaves_in_each_world": 3,
        "forest_standing_timber_opening": 3,
        "bakery_target_grain_not_assumed_stock": True,
        "no_postgenesis_player_or_test_commands_to_npcs": True,
        "only_treatment_difference": "personally-known charcoal shop revisit",
        "baseline": old,
        "retry": retry,
        "baseline_72_to_96": base_delta,
        "retry_72_to_96": retry_delta,
        "genuine_post72_delivery_plus_economic_activity": recovery,
        "seven_day_resilience_proven": False,
        "schema_or_rules_changed": False,
        "production_release_approved": False,
    }
    # A green diagnostic is not a 'prosperous village' assertion.
    print("PLAY48O_GENUINE_FOUR_DAY_WOOD_CHARCOAL_COUNTERFACTUAL",
          json.dumps(report, sort_keys=True), flush=True)
