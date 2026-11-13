"""PLAY48 honest first finite aquifer: physical pumping and paid work A/B.

NOT an automatic rain machine: exactly SIX existing source-owned geological
water units are disclosed at time-zero. A real former miner uses an actual
one-pump tool and 30-minute scheduled labor to move one into the same well.
One of the original 13 NPC and TWO of the original TWELVE copper coins are
reassigned at genesis. Real completed work pays one of these existing coins.
No groundwater beyond its original finite stock ever appears. This pilot is
NOT renewable aquifer recharge and NOT a 168h rescue.
"""
from __future__ import annotations

import json

from carlos_sim import (
    DomainEvent, LivingWorldEngine, SQLiteEventStore, TimeEngine,
)
from carlos_sim.economic_diagnostics import audit_npc_economy
from test_play38_multi_farm_couriers import WORLD, seed_two_field_world
from test_play47_joined_professions import _joined_bootstrap
from test_play47_closure_endurance import DAY
from test_play48_peddler_24h_diagnostic import measures

HOUR = 3600
INITIAL_AQUIFER = 6
INITIAL_SURFACE = 2


def _aquifer_genesis(db, *, initial_market_food, **options):
    assert initial_market_food == 3
    assert options == {
        "water": 2, "seed": 1, "harvest_yield": 3,
        "personal_food": 0, "market_wallets": True,
        "hungry_market_buyers": True,
        "one_hungry_market_buyer": False,
    }
    return _joined_bootstrap(
        db, initial_market_food=3,
        wilderness_food_jobs_enabled=True,
        wilderness_food_peddler_enabled=True,
        food_for_work_bakery_enabled=True,
        bakery_opening_food_wage=True,
        finite_aquifer_work_enabled=True,
    )


def seed(path):
    with SQLiteEventStore(path) as db:
        seed_two_field_world(
            db, east_growth_seconds=DAY, east_grain_yield=12,
            initial_water=2, initial_market_food=3,
            market_wallets=True, hungry_market_buyers=True,
            cash_return=True, waged_harvest=True,
            harvest_wage_copper=2, bootstrap=_aquifer_genesis,
        )
        s = db.load(WORLD)
        s = db.append(WORLD, "finite-aquifer:natural-source-policy",
                      s.revision, [
            DomainEvent("WaterSourceConfigured", None,
                        "finite audited well", 0,
                        {"site_id": "well", "capacity": 8}),
            DomainEvent("MetabolismPolicyConfigured", None,
                        "existing physical metabolism", 0,
                        {"hunger_seconds_per_point": 3600,
                         "activity_hunger_percent": 20}),
        ], bootstrap=True)
        assert len(s.npcs) == 13
        assert (s.schema_version, s.rules_version) == (45, 63)
        assert s.npcs["miner"]["role"] == "well_pumper"
        assert s.entities["miner"]["location_id"] == "well"
        assert s.resources["miner"]["coin_copper"] == 0
        assert s.resources["smith"]["coin_copper"] == 0
        assert s.resources["well"]["coin_copper"] == 2
        assert s.resources["well"]["water"] == INITIAL_SURFACE
        assert s.resources["well"]["groundwater_reserve"] == INITIAL_AQUIFER
        assert s.resources["well"]["hand_pump"] == 1
        assert s.production_recipes["finite-aquifer-to-well"]["wage_coin"] == 1
        assert audit_npc_economy(s)["copper_scope_complete"]
        assert audit_npc_economy(s)["copper_known_total"] == 12
        assert db.verify(WORLD).to_dict() == s.to_dict()
        return s


def conserve_water(state):
    """Include water still in one running, not-yet-completed pump job."""
    stock = state.resources
    water = sum(stock[who]["water"] for who in (
        "well", "farm", "farm_east", "huda", "hana"
    ) if "water" in stock.get(who, {}))
    used = sum(p["started"] for p in state.farm_plots.values())
    reserve = stock["well"]["groundwater_reserve"]
    pending = sum(
        1 for j in state.production_jobs.values()
        if j["recipe_id"] == "finite-aquifer-to-well"
        and j["status"] == "running"
    )
    assert water + used + reserve + pending == (
        INITIAL_SURFACE + INITIAL_AQUIFER
        + state.hydrology_sources["well"]["received_total"]
    )
    pumped = sum(j["status"] == "completed"
                 for j in state.production_jobs.values()
                 if j["recipe_id"] == "finite-aquifer-to-well")
    started = sum(j["recipe_id"] == "finite-aquifer-to-well"
                  for j in state.production_jobs.values())
    assert reserve + started == INITIAL_AQUIFER
    assert pumped + pending == started
    assert started <= 2, "cannot hire workers with fewer than two real coins"
    starts = sorted(
        job["started_at"] for job in state.production_jobs.values()
        if job["recipe_id"] == "finite-aquifer-to-well"
    )
    assert all(b - a >= 4*HOUR
               for a, b in zip(starts, starts[1:]))
    assert sum(
        "work_wage" in job
        for job in state.production_jobs.values()
        if job["recipe_id"] == "finite-aquifer-to-well"
    ) == pumped, "completed pump work must actually be paid"
    for j in state.production_jobs.values():
        if j["recipe_id"] != "finite-aquifer-to-well":
            continue
        assert j["site_id"] == "well"
        assert j["npc_id"] == "miner"
        if "work_wage" in j:
            w = j["work_wage"]
            assert w["amount"] == 1
            assert w["worker_id"] == "miner"
            assert w["site_id"] == "well"
            assert w["site_before"] - w["site_after"] == 1
            assert w["worker_after"] - w["worker_before"] == 1


def _engine(db, clock, *, pump):
    return LivingWorldEngine(
        db, clock, max_events_per_advance=9000,
        decision_cooldown=3600, economic_enabled=True,
        agriculture_enabled=True, navigation_enabled=True,
        routines_enabled=True, consumption_enabled=True,
        survival_enabled=True, supply_enabled=True,
        shopping_routes_enabled=True,
        multi_professional_markets_enabled=True,
        compound_procurement_enabled=True,
        professional_full_life_enabled=True,
        food_for_work_enabled=True,
        food_peddler_enabled=True,
        seek_alternative_food_market_enabled=True,
        foraging_enabled=True, gathering_enabled=True,
        knowledge_enabled=True, food_navigation_enabled=True,
        assistance_enabled=True, aid_relay_enabled=True,
        scarcity_enabled=True,
        finite_aquifer_pumping_enabled=pump,
    )


def test_same_original_thirteen_and_twelve_copper_with_six_declared_aquifer_units(tmp_path):
    initial = seed(tmp_path / "physically-declared-aquifer.sqlite")
    assert len(initial.npcs) == 13
    assert initial.resources["well"]["water"] == 2
    assert initial.resources["well"]["groundwater_reserve"] == 6
    conserve_water(initial)


def test_identical_aquifer_worlds_with_or_without_actual_pumping_12h(tmp_path):
    paths = [tmp_path / "unused-aquifer.sqlite",
             tmp_path / "working-aquifer.sqlite"]
    originals = [seed(p) for p in paths]
    assert originals[0].to_dict() == originals[1].to_dict()
    records = []
    for path, enabled in zip(paths, (False, True)):
        snapshots = []
        with SQLiteEventStore(path) as db:
            clock = TimeEngine(db)
            clock.open_session(WORLD)
            try:
                engine = _engine(db, clock, pump=enabled)
                for hour in (3, 6, 12):
                    current = db.verify(WORLD)
                    new = engine.advance(
                        WORLD, seconds=hour*HOUR - current.time,
                        command_id=f"finite-aquifer:{enabled}:{hour}h",
                        expected_revision=current.revision,
                    ).state
                    assert new.time == hour*HOUR
                    conserve_water(new)
                    cash = audit_npc_economy(new)
                    assert cash["copper_scope_complete"]
                    assert cash["copper_known_total"] == 12
                    assert db.verify(WORLD).to_dict() == new.to_dict()
                    assert db.db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
                    assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
                    row = measures(new)
                    row["water_stored_at_well"] = new.resources["well"]["water"]
                    row["groundwater_reserve"] = new.resources["well"]["groundwater_reserve"]
                    row["real_pump_jobs_completed"] = sum(
                        j["recipe_id"] == "finite-aquifer-to-well"
                        and j["status"] == "completed"
                        for j in new.production_jobs.values()
                    )
                    row["funded_well_wages"] = sum(
                        j["recipe_id"] == "finite-aquifer-to-well"
                        and "work_wage" in j
                        for j in new.production_jobs.values()
                    )
                    snapshots.append(row)
                if not enabled:
                    assert all(row["real_pump_jobs_completed"] == 0
                               for row in snapshots)
                else:
                    assert snapshots[-1]["real_pump_jobs_completed"] > 0, (
                        "aquifer signed work never started; inspect work guards"
                    )
                    assert snapshots[-1]["real_pump_jobs_completed"] <= 2
                    assert snapshots[-1]["groundwater_reserve"] >= 4
                    assert (snapshots[-1]["funded_well_wages"]
                            == snapshots[-1]["real_pump_jobs_completed"])
            finally:
                clock.close_session(WORLD)
        records.append({"finite_pumping_policy": enabled,
                        "points": snapshots})
    print("PLAY48_FINITE_AQUIFER_AUTHENTIC_12H_AB " +
          json.dumps(records, sort_keys=True), flush=True)
