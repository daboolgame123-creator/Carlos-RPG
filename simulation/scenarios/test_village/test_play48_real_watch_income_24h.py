"""PLAY48: genuinely funded paid watch service and real food resale in 13NPC village.

Baseline remains the original genuine world. Treatment moves Carlos' two
EXISTING opening copper to a distinct watch employer at trusted t=0; guards
perform one actual local 900s watch work order, and ONLY the original
production reducer may debit employer and credit Adel after completed work.

No post-genesis gifts or orders, invented prey/water, automatic purchases,
population additions, loan, or forced NPC employment. Security is a finite
publicly funded service, not an unlimited lasting revenue loop.
"""
from __future__ import annotations
import json

from carlos_sim import DomainEvent, LivingWorldEngine, SQLiteEventStore, TimeEngine
from carlos_sim.economic_diagnostics import audit_npc_economy
from test_play38_multi_farm_couriers import seed_two_field_world, WORLD
from test_play47_joined_professions import _joined_bootstrap
from test_play47_closure_endurance import DAY
from test_play48_peddler_fast import seed as seed_original
from test_play48_finite_hunt_fish_roads import conserve_diverse
from test_play48_peddler_24h_diagnostic import measures, market_resale_gates

HOUR = 3600


def _watch_genesis(db, *, initial_market_food,
                   sale_backed_keeper_commission_enabled=False, **options):
    assert initial_market_food == 3
    assert options == {
        "water": 2, "seed": 1, "harvest_yield": 3,
        "personal_food": 0, "market_wallets": True,
        "hungry_market_buyers": True,
        "one_hungry_market_buyer": False,
    }
    return _joined_bootstrap(
        db, initial_market_food=3, wilderness_food_jobs_enabled=True,
        wilderness_food_peddler_enabled=True,
        food_for_work_bakery_enabled=True, bakery_opening_food_wage=True,
        signed_market_watch_service_enabled=True,
        sale_backed_keeper_commission_enabled=sale_backed_keeper_commission_enabled,
    )


def seed(path, *, sale_backed_keeper_commission_enabled=False):
    with SQLiteEventStore(path) as db:
        seed_two_field_world(
            db, east_growth_seconds=DAY, east_grain_yield=12,
            initial_water=2, initial_market_food=3,
            market_wallets=True, hungry_market_buyers=True,
            cash_return=True, waged_harvest=True,
            harvest_wage_copper=2,
            bootstrap=(lambda db, **kwargs: _watch_genesis(
                db, sale_backed_keeper_commission_enabled=
                sale_backed_keeper_commission_enabled, **kwargs)),
        )
        old = db.load(WORLD)
        current = db.append(
            WORLD, "watch-initial-season-and-metabolism", old.revision, [
                DomainEvent("WaterSourceConfigured", None, "finite well", 0,
                            {"site_id": "well", "capacity": 8}),
                DomainEvent("MetabolismPolicyConfigured", None, "actual needs", 0,
                            {"hunger_seconds_per_point": 3600,
                             "activity_hunger_percent": 20}),
            ], bootstrap=True,
        )
        assert (current.schema_version, current.rules_version) == (45, 63)
        assert len(current.npcs) == 13
        assert audit_npc_economy(current)["copper_known_total"] == 12
        assert current.resources["watch_post"]["coin_copper"] == 2
        assert current.resources["carlos"]["coin_copper"] == 0
        assert db.verify(WORLD).to_dict() == current.to_dict()
        conserve_diverse(current)
    return current


def engine(db, clock, *, reserve_trader_meal=False,
           deferred_market_courier_wage=False):
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
        food_for_work_enabled=True, food_peddler_enabled=True,
        food_peddler_self_meal_reserve_enabled=reserve_trader_meal,
        early_courier_food_wage_enabled=deferred_market_courier_wage,
        market_sourced_wage_refill_enabled=deferred_market_courier_wage,
        seek_alternative_food_market_enabled=True,
    )


def test_signed_real_watch_service_pays_only_after_actual_work_and_can_buy_food(tmp_path):
    # Same opening scarce nutrition/environment/people as the official source;
    # the new watch order is an explicit finite non-food work item.
    control = seed_original(tmp_path / "original.sqlite")
    start = seed(tmp_path / "signed-watch.sqlite")
    assert len(control.npcs) == len(start.npcs) == 13
    assert sum(r.get("food", 0) for r in control.resources.values()) == 3
    assert sum(r.get("food", 0) for r in start.resources.values()) == 3
    assert audit_npc_economy(control)["copper_known_total"] == 12
    assert audit_npc_economy(start)["copper_known_total"] == 12
    assert control.resources["carlos"]["coin_copper"] == 2
    assert start.resources["carlos"]["coin_copper"] == 0
    path = tmp_path / "signed-watch.sqlite"
    rows = []
    with SQLiteEventStore(path) as db:
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            runner = engine(db, clock)
            for h in (1, 2, 4, 6, 12, 18, 24):
                prev = db.verify(WORLD)
                state = runner.advance(
                    WORLD, seconds=h * HOUR - prev.time,
                    expected_revision=prev.revision,
                    command_id=f"actual-guard-work:{h}",
                ).state
                assert state.time == h * HOUR
                assert len(state.npcs) == 13
                conserve_diverse(state)
                cash = audit_npc_economy(state)
                assert cash["copper_scope_complete"]
                assert cash["copper_known_total"] == 12
                assert db.verify(WORLD).to_dict() == state.to_dict()
                assert db.db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
                assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
                guard_jobs = [
                    job for job in state.production_jobs.values()
                    if job["recipe_id"] == "finite-watch-duty"
                ]
                guard_pay = [
                    j["work_wage"] for j in guard_jobs if "work_wage" in j
                ]
                for receipt in guard_pay:
                    assert receipt["worker_id"] == "adel"
                    assert receipt["site_id"] == "watch_post"
                    assert receipt["amount"] == 2
                    assert receipt["site_before"] - receipt["site_after"] == 2
                    assert receipt["worker_after"] - receipt["worker_before"] == 2
                bought_by_guard = [
                    t for t in state.market_trades.values()
                    if t["buyer_id"] == "adel" and t["resource"] == "food"
                ]
                trader_sale_to_guard = [
                    t for t in bought_by_guard if t["seller_id"] == "repairman"
                    and t["stock_owner_id"] == "repairman"
                    and t["site_id"] == "market"
                ]
                guard_meals = [
                    v for v in state.consumptions.values()
                    if v["npc_id"] == "adel"
                ]
                row = measures(state)
                row.update({
                    "real_watch_jobs": len(guard_jobs),
                    "real_completed_watch_jobs": sum(
                        j["status"] == "completed" for j in guard_jobs
                    ),
                    "actually_paid_watch_wages": len(guard_pay),
                    "guard_copper": state.resources["adel"]["coin_copper"],
                    "guard_market_food_purchases": len(bought_by_guard),
                    "guard_real_trader_purchases": len(trader_sale_to_guard),
                    "guard_actual_meals": len(guard_meals),
                    "watch_employer_coins": state.resources["watch_post"]["coin_copper"],
                    "peddler_market_buyers_now": (
                        market_resale_gates(state)["eligible_on_site_purchases"]
                    ),
                })
                rows.append(row)
            print("PLAY48_PHYSICAL_GUARD_WAGE_TO_FOOD_CAUSAL_24H " +
                  json.dumps(rows, sort_keys=True), flush=True)
            assert sum(j["status"] == "completed"
                       for j in state.production_jobs.values()
                       if j["recipe_id"] == "finite-watch-duty") == 1, (
                "guard never completed signed physical 15-minute shift"
            )
            assert len(guard_pay) == 1, "guard never received actual funded copper"
            assert len(bought_by_guard) >= 2, (
                "authentic earned guard pay failed to finance a second food purchase"
            )
            assert trader_sale_to_guard, (
                "earned income did not enable a genuine personal peddler resale"
            )
            assert guard_meals, "no authentic guard meal was consumed"
        finally:
            clock.close_session(WORLD)
