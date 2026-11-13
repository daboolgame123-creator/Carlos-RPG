"""PLAY-48 owner-approved food diversity: real finite hunting and fishing.

An opt-in thirteen-NPC world at exact original copper/food budget adds
physically located forest & river sites with local tools, finite ecological
resource lots, scheduled finite reserve-to-wild-food conversion, road segments,
and two genuine worker roles (existing Omar and Layla, no extra NPC). A hunted
animal or caught fish yields two edible portions after ONE actual hour of
on-site work. Paying the worker two portions is a real site→person debit.

This is a bounded initial ecology trial, NOT renewable seven-day fish/wildlife,
not a finished market transport system and not GO on the economy.
"""
from __future__ import annotations

import json

import pytest

from carlos_sim import (
    DomainEvent, InvalidEvent, LivingWorldEngine, SQLiteEventStore, TimeEngine,
)
from test_play38_multi_farm_couriers import seed_two_field_world, WORLD
from test_play47_joined_professions import _joined_bootstrap
from test_play47_closure_endurance import DAY
from carlos_sim.economic_diagnostics import audit_npc_economy

INITIAL_FOOD = 3
INITIAL_WATER = 2

def conserve_diverse(state):
    """Count two real portions from each completed prey-processing job.

    A running prey-processing job has already reserved its wildlife lot but
    adds NO nutrition until the scheduled job finishes. Grain/bread remains
    tracked separately and copper/water may never be minted.
    """
    assert len(state.npcs) == 13
    cash = audit_npc_economy(state)
    assert cash["copper_scope_complete"] and cash["copper_known_total"] == 12
    stock = state.resources
    eaten = sum(r["quantity"] for r in state.consumptions.values())
    escrow = sum(c["remaining"] for c in state.courier_provisions.values())
    food = sum(v.get("food", 0) for v in stock.values()) + escrow
    grain = sum(v.get("grain", 0) for v in stock.values())
    fields = {}
    for site, plot in state.farm_plots.items():
        choices = [recipe["output_amount"]
                   for recipe in state.production_recipes.values()
                   if recipe["site_id"] == site
                   and recipe.get("input_resource") == "crop_ready"
                   and recipe["output_resource"] == "grain"]
        assert len(choices) == 1
        fields[site] = choices[0]
    pending_grain_inputs = sum(
        state.production_recipes[job["recipe_id"]]["input_amount"]
        for job in state.production_jobs.values()
        if job["status"] == "running"
        and state.production_recipes[job["recipe_id"]].get("input_resource") == "grain"
        and state.production_recipes[job["recipe_id"]]["output_resource"] == "food"
    )
    pending_harvest = sum(
        fields[job["site_id"]] for job in state.production_jobs.values()
        if job["status"] == "running"
        and state.production_recipes[job["recipe_id"]].get("input_resource") == "crop_ready"
    )
    ripe = sum(stock[site]["crop_ready"] * amount
               for site, amount in fields.items())
    grown = sum(plot["matured"] * fields[site]
                for site, plot in state.farm_plots.items())
    completed_wildlife = sum(
        1 for job in state.production_jobs.values()
        if job["status"] == "completed"
        and job["recipe_id"] in ("two-portions-hunter", "two-portions-fisher")
    )
    assert food + grain + eaten + pending_grain_inputs + pending_harvest + ripe == (
        INITIAL_FOOD + grown + 2 * completed_wildlife
    )
    water = sum(stock[who]["water"] for who in
                ("well", "farm", "farm_east", "huda", "hana")
                if who in stock and "water" in stock[who])
    used = sum(plot["started"] for plot in state.farm_plots.values())
    assert water + used == (
        INITIAL_WATER + state.hydrology_sources["well"]["received_total"]
    )
    for site in SITES:
        prey_reserved = sum(
            1 for job in state.production_jobs.values()
            if job["site_id"] == site
            and job["recipe_id"] in ("two-portions-hunter", "two-portions-fisher")
        )
        assert (stock[site]["wild_food"] +
                stock[site]["regrowth_reserve"] + prey_reserved == 8)


SITES = {"hunting_woods": ("omar", "hunter", "bow"),
         "riverbank": ("layla", "fisher", "net")}
HOUR = 3600


def _ecology_bootstrap(db, *, initial_market_food, **options):
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
        food_for_work_bakery_enabled=True,
        bakery_opening_food_wage=True,
    )


def seed(path):
    with SQLiteEventStore(path) as db:
        seed_two_field_world(
            db, east_growth_seconds=DAY, east_grain_yield=12,
            initial_water=2, initial_market_food=3,
            market_wallets=True, hungry_market_buyers=True,
            cash_return=True, waged_harvest=True,
            harvest_wage_copper=2, bootstrap=_ecology_bootstrap,
        )
        s = db.load(WORLD)
        s = db.append(WORLD, "play48-ecology-signed-genesis", s.revision, [
            DomainEvent("WaterSourceConfigured", None,
                        "bounded water authority", 0,
                        {"site_id": "well", "capacity": 8}),
            DomainEvent("MetabolismPolicyConfigured", None,
                        "existing real hunger progress", 0,
                        {"hunger_seconds_per_point": 3600,
                         "activity_hunger_percent": 20}),
        ], bootstrap=True)
        assert len(s.npcs) == 13
        assert (s.schema_version, s.rules_version) == (45, 63)
        assert sum(bag.get("coin_copper", 0)
                   for bag in s.resources.values()) == 12
        assert s.resources["market"]["food"] == 2
        assert s.resources["bakery"]["food"] == 1
        for site, (who, role, tool) in SITES.items():
            assert s.entities[who]["location_id"] == site
            assert s.npcs[who]["role"] == role
            assert s.resources[site]["wild_food"] == 2
            assert s.resources[site]["regrowth_reserve"] == 6
            assert s.resources[site]["food"] == 0
            assert s.market_stalls[site]["keeper_id"] == who
            assert s.resources[site][tool] == 1
            recipe = s.production_recipes["two-portions-" + role]
            assert recipe["input_resource"] == "wild_food"
            assert recipe["input_amount"] == 1
            assert recipe["output_resource"] == "food"
            assert recipe["output_amount"] == 2
            assert recipe["wage_food"] == 2
            assert s.environment_cycles[site + "-finite-ecology"]["capacity"] == 3
        assert s.routes["market-woods"]["seconds"] == 240
        assert s.routes["well-river"]["seconds"] == 180
        assert not any(route in s.navigation.get("omar", {}).get("known_routes", [])
                       for route in ("market-woods", "well-river"))
        assert db.verify(WORLD).to_dict() == s.to_dict()
        conserve_diverse(s)
    return s


def test_genesis_contains_real_finite_forest_river_and_no_new_people_or_money(tmp_path):
    s = seed(tmp_path / "time-zero-real-forest-river.sqlite")
    assert len(s.environment_cycles) == 2
    # Each site initially has exactly two real lots and six reserved lots,
    # not an immortal source. These are additional disclosed physical genesis
    # resources, so this is not an identical-resources control world.
    for site in SITES:
        assert s.resources[site]["wild_food"] + s.resources[site]["regrowth_reserve"] == 8


def test_real_work_produces_two_owned_portions_with_conserved_prey_and_roads(tmp_path):
    path = tmp_path / "three-hour-finite-ecology.sqlite"
    seed(path)
    with SQLiteEventStore(path) as db:
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            engine = LivingWorldEngine(
                db, clock, max_events_per_advance=5000,
                decision_cooldown=3600, economic_enabled=True,
                agriculture_enabled=True, navigation_enabled=True,
                routines_enabled=True, consumption_enabled=True,
                survival_enabled=True, supply_enabled=True,
                shopping_routes_enabled=True,
                multi_professional_markets_enabled=True,
                compound_procurement_enabled=True,
                professional_full_life_enabled=True,
                food_for_work_enabled=True,
            )
            current = db.load(WORLD)
            actual = engine.advance(
                WORLD, seconds=3*HOUR,
                command_id="real-hunt-fish:3h",
                expected_revision=current.revision,
            ).state
            assert actual.time == 3 * HOUR
            conserve_diverse(actual)
            assert db.verify(WORLD).to_dict() == actual.to_dict()
            assert db.db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
            assert sum(v.get("coin_copper", 0)
                       for v in actual.resources.values()) == 12

            output = {}
            for site, (who, role, _tool) in SITES.items():
                completed = [
                    (name, job) for name, job in actual.production_jobs.items()
                    if job["site_id"] == site and job["status"] == "completed"
                ]
                assert completed, "no real work completed: " + site
                earned = [(key, j["food_wage"]) for key,j in completed
                          if "food_wage" in j]
                assert earned, "no physical food wage: " + site
                assert all(r["amount"] == 2
                           and r["site_before"]-r["site_after"] == 2
                           and r["worker_after"]-r["worker_before"] == 2
                           and r["worker_id"] == who for _,r in earned)
                wild_now = actual.resources[site]["wild_food"]
                reserve_now = actual.resources[site]["regrowth_reserve"]
                # No one outside these jobs forages in this focused world.
                assert (wild_now + reserve_now + len(completed) == 8), site
                output[site] = {
                    "jobs": len(completed),
                    "two_portion_wages": len(earned),
                    "wild_food_remaining": wild_now,
                    "regrowth_reserve": reserve_now,
                    "personally_owned": actual.resources[who]["food"],
                    "worker_hunger": actual.npcs[who]["needs"]["hunger"],
                }

                paid_id, _ = earned[0]
                stable = db.verify(WORLD).to_dict()
                for amount in (1, 2, 3):
                    with pytest.raises(InvalidEvent):
                        db.append(WORLD, "illegal-food-" + role + str(amount),
                                  actual.revision, [
                                      DomainEvent("ProductionFoodWagePaid",
                                                  None, "counterfeit job pay",
                                                  actual.time,
                                                  {"job_id": paid_id,
                                                   "amount": amount}),
                                  ], production_authorized=True)
                    assert db.verify(WORLD).to_dict() == stable

            print("PLAY48_FINITE_HUNT_FISH_ACTUAL_WORK " +
                  json.dumps(output, sort_keys=True))
        finally:
            clock.close_session(WORLD)


def test_local_food_offer_protects_contracted_worker_share(tmp_path):
    """Food buyers can only quote produced *surplus*, never the worker's wage.

    Pure decision selector: no inventory is created or world-state mutated.
    The actual 13NPC physical-work test separately verifies signed receipts.
    """
    from carlos_sim.economic_autonomy import choose_local_food_offer
    from carlos_sim.domain import WorldState
    s = seed(tmp_path / "finite-site-stalls.sqlite")
    for site, (who, _role, _tool) in SITES.items():
        raw = s.to_dict()
        # Alter a *read-only selector copy* solely to test reservation arithmetic.
        # No such direct mutation is submitted as a physical game event.
        for total, quoted in ((0, None), (2, None), (3, 1), (6, 4)):
            scenario = s.to_dict()
            scenario["resources"][site]["food"] = total
            mock = WorldState.from_dict(scenario)
            intent = choose_local_food_offer(mock, who)
            assert (intent.quantity if intent else None) == quoted, (
                site, total, intent
            )
