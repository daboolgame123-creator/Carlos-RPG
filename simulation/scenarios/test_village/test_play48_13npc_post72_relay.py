"""PLAY-48G: genuine PLAY-47 13-NPC 72→96h blocked-vs-relay fork.

No extra initial stock, no new personally learned routes, no time-zero donor,
no arbitrary courier wallet and no post-bootstrap direct NPC commands.
This measures whether the already verified small-world rescue *actually*
works when switched on at the genuine collapse checkpoint. It may not.
"""
from __future__ import annotations

import json
import shutil

from carlos_sim import LivingWorldEngine, SQLiteEventStore, TimeEngine
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.supply_diagnostics import audit_courier
from test_play47_closure_endurance import _seed, _day, _reading, DAY, WORLD


def _stats(state):
    return {
        "time": state.time,
        "trades": len(state.market_trades),
        "food_sales": sum(t["resource"] == "food"
                          for t in state.market_trades.values()),
        "jobs": sum(j["status"] == "completed"
                    for j in state.production_jobs.values()),
        "wages": sum("work_wage" in j for j in state.production_jobs.values()),
        "meals": len(state.consumptions),
        "hunger_cap": sum(n["needs"]["hunger"] == 100
                          for n in state.npcs.values()),
        "market_loaves": state.resources["market"]["food"],
        "deliveries": {
            who: state.supply_circuits[who]["deliveries"]
            for who in ("huda", "hana")
        },
        "copper": audit_npc_economy(state)["copper_known_total"],
    }


def _live_help_options(state):
    """Conservative visible-world eligibility; a payer is not presumed."""
    people = []
    for npc_id, npc in sorted(state.npcs.items()):
        current = state.entities[npc_id]["location_id"]
        coins = state.resources.get(npc_id, {}).get("coin_copper")
        nav = state.navigation.get(npc_id)
        physical_visited = sorted(nav["visited"]) if nav else []
        people.append({
            "npc": npc_id,
            "location": current,
            "hunger": npc["needs"]["hunger"],
            "fatigue": npc["needs"]["fatigue"],
            "personal_copper": coins,
            "personally_visited_market": "market" in physical_visited,
            "at_courier_well": current == "well",
            "is_courier": npc_id in state.supply_circuits,
            "potential_healthy_donor": (
                npc_id not in state.supply_circuits
                and npc["needs"]["hunger"] <= 60
                and npc["needs"]["fatigue"] <= 69
                and coins is not None and coins >= 2
            ),
        })
    return people


def _existing_13npc_engine(db, clock, *, help_enabled):
    # Exact original PLAY-47 full-life/market/supply configuration, adding
    # ONLY two explicit opt-in flags in the counterfactual continuation.
    return LivingWorldEngine(
        db, clock, max_events_per_advance=5000,
        decision_cooldown=3600,
        economic_enabled=True, agriculture_enabled=True,
        economy_only_enabled=False,
        navigation_enabled=True, routines_enabled=True,
        consumption_enabled=True, survival_enabled=True,
        multi_professional_markets_enabled=True,
        compound_procurement_enabled=True,
        supply_enabled=True, shopping_routes_enabled=True,
        professional_full_life_enabled=True,
        assistance_enabled=help_enabled,
        aid_relay_enabled=help_enabled,
    )


def _day_four_with_relief(path):
    with SQLiteEventStore(path) as db:
        state = db.load(WORLD)
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            engine = _existing_13npc_engine(db, clock, help_enabled=True)
            for target in (DAY * 3 + DAY // 4, DAY * 3 + DAY // 2,
                           DAY * 3 + 3 * DAY // 4, DAY * 4):
                state = engine.advance(
                    WORLD, seconds=target - state.time,
                    command_id=f"play48:13npc:relay:{target}",
                    expected_revision=state.revision,
                ).state
                assert state.time == target
                assert audit_npc_economy(state)["copper_known_total"] == 12
                _reading(state)
                assert db.snapshot(WORLD).to_dict() == state.to_dict()
            assert db.verify(WORLD).to_dict() == state.to_dict()
            assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
            assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
        finally:
            clock.close_session(WORLD)
    with SQLiteEventStore(path) as reopened:
        assert reopened.verify(WORLD).to_dict() == state.to_dict()
    return state


def test_real_thirteen_npc_day_four_science_not_false_recovery(tmp_path):
    control = tmp_path / "genuine-play47-unrecovered.sqlite"
    relay = tmp_path / "genuine-play48-opt-in-after-72h.sqlite"
    _seed(control)

    # Past is EXACTLY the same proven history and weather as PLAY-47, including
    # three observed finite rainfalls of two units after days 1, 2 and 3.
    for day in range(1, 4):
        state72 = _day(control, day * DAY, rain=True)
    assert state72.time == 3 * DAY
    baseline = _stats(state72)
    assert baseline["copper"] == 12
    assert baseline["market_loaves"] == 5
    assert baseline["deliveries"] == {"huda": 3, "hana": 25}
    assert len(state72.npcs) == 13
    assert state72.npcs["huda"]["needs"]["hunger"] == 100
    assert state72.npcs["hana"]["needs"]["hunger"] == 100

    # Because the running authority itself hasn't enabled aid earlier,
    # no one can be assumed to hold a pre-existing signed request or pledge.
    assert not state72.obligations
    eligible = _live_help_options(state72)
    well_healthy = [x for x in eligible
                    if x["potential_healthy_donor"] and x["at_courier_well"]]
    # This captures the actual physical/financial prerequisite. A default
    # post-72 relay cannot fabricate the missing willing co-present donor.
    assert not well_healthy

    # A true SQLite copy of the CLOSED verified day-3 ledger. No event
    # revision rewrite or altered prior route/social history is possible.
    shutil.copyfile(control, relay)
    control96 = _day(control, DAY * 4, rain=False)
    aid96 = _day_four_with_relief(relay)
    old, new = _stats(control96), _stats(aid96)
    for metric in ("copper", "market_loaves"):
        assert old[metric] >= 0 and new[metric] >= 0
    assert old["copper"] == new["copper"] == 12
    assert aid96.time == control96.time == 4 * DAY
    assert old["deliveries"] == baseline["deliveries"]
    assert new["deliveries"]["huda"] >= baseline["deliveries"]["huda"]
    assert new["deliveries"]["hana"] >= baseline["deliveries"]["hana"]
    assert new["jobs"] >= baseline["jobs"]
    assert new["trades"] >= baseline["trades"]
    assert new["wages"] >= baseline["wages"]

    delivered_later = any(
        new["deliveries"][who] > baseline["deliveries"][who]
        for who in ("huda", "hana")
    )
    later_actual_activity = any(
        new[k] > baseline[k] for k in ("jobs", "trades", "meals")
    )
    recovered = delivered_later and later_actual_activity
    report = {
        "same_72h_genesis_weather_and_actual_history": True,
        "identical_finite_copper": 12,
        "baseline_72h": baseline,
        "control_96h": old,
        "aid_enabled_only_after_72h": new,
        "possible_healthy_co_present_donors_at_72h": well_healthy,
        "all_npc_funding_and_first_hand_market_history_at_72h": eligible,
        "new_post72_real_delivery": delivered_later,
        "new_post72_real_activity": later_actual_activity,
        "post72_recovery_proved": recovered,
        "no_teleport_no_free_copper_or_loaves": True,
        "no_new_wallet_or_genesis_modification": True,
    }
    # An honest result is either a fully receipted delivery+activity or a
    # verified remaining blockade. Both are useful acceptance evidence.
    if recovered:
        assert new["meals"] > baseline["meals"], (
            "at least one consumed aid loaf must make later work possible"
        )
    print("PLAY48_13NPC_REAL_POST72_COUNTERFACTUAL " +
          json.dumps(report, sort_keys=True), flush=True)
