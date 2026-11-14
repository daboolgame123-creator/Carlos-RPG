"""PLAY48 independent real, local economic causality: sale -> paid work -> food.

Runs genuine existing PLAY-40/41/42 economic reducers, not synthetic snapshots.
Small 9NPC fixture intentionally tests *one necessary income pathway*, NOT
13NPC h72 or h168 endurance. No game code, wages, stock or prices are changed.
Original time-zero 12 copper and finite baker/farm/well assets are conserved.
"""
from __future__ import annotations

import json

from carlos_sim import SQLiteEventStore, TimeEngine
from carlos_sim.economic_diagnostics import audit_npc_economy
from test_play38_multi_farm_couriers import (
    WORLD, EAST, COURIER, FARMER, seed_two_field_world,
)
from test_play42_market_shopping import _engine, _advance

POINTS = (300, 1200, 3600, 3900, 4800, 7200, 8400, 12000)


def _authentic_events(db):
    return [(seq, json.loads(payload))
            for seq, payload in db.db.execute(
                "SELECT seq,payload FROM events WHERE world_id=? ORDER BY seq",
                (WORLD,),
            ).fetchall()]


def test_real_market_sale_physically_funds_wage_then_farmer_buys_and_eats(tmp_path):
    """The exactly traced source-to-mouth chain must work without a subsidy."""
    path = tmp_path / "real-circular-copper-to-food.sqlite"
    with SQLiteEventStore(path) as db:
        seed_two_field_world(
            db, cash_return=True, waged_harvest=True,
            hungry_waged_farmer=True, harvest_wage_copper=2,
            market_wallets=True, hungry_market_buyers=False,
            one_hungry_market_buyer=True, initial_market_food=3,
        )
        start = db.verify(WORLD)
        assert len(start.npcs) == 9  # Focused existing fixture, NOT 13NPC gate.
        assert start.resources[FARMER]["coin_copper"] == 0
        assert start.resources[FARMER]["food"] == 0
        assert start.resources["market"]["coin_copper"] == 0
        assert start.resources[EAST]["coin_copper"] == 0
        assert start.production_recipes["east-finite-harvest"]["wage_coin"] == 2
        assert audit_npc_economy(start)["copper_known_total"] == 12

        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            engine = _engine(db, clock)
            measurements = []
            state = start
            for target in POINTS:
                state = _advance(db, engine, target)
                audit = audit_npc_economy(state)
                assert audit["copper_scope_complete"]
                assert audit["copper_known_total"] == 12
                assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
                assert not db.db.execute("PRAGMA foreign_key_check").fetchall()
                measurements.append({
                    "second": target,
                    "market_till": state.resources["market"]["coin_copper"],
                    "farm_till": state.resources[EAST]["coin_copper"],
                    "farmer_wallet": state.resources[FARMER]["coin_copper"],
                    "farmer_meals": sum(
                        x["npc_id"] == FARMER for x in state.consumptions.values()
                    ),
                    "farmer_trades": sum(
                        x["buyer_id"] == FARMER for x in state.market_trades.values()
                    ),
                })

            jobs = [
                (job_id, job) for job_id, job in state.production_jobs.items()
                if job["npc_id"] == FARMER and "work_wage" in job
            ]
            assert jobs, "no actual finished salaried harvest occurred"
            job_id, job = jobs[0]
            wage = job["work_wage"]
            assert job["status"] == "completed"
            assert job["recipe_id"] == "east-finite-harvest"
            assert wage["amount"] == 2 and wage["site_id"] == EAST
            assert wage["worker_id"] == FARMER
            assert job["finished_at"] <= wage["paid_at"]
            assert wage["site_before"] - wage["site_after"] == 2
            assert wage["worker_after"] - wage["worker_before"] == 2

            genuine_incoming_market_revenue = [
                t for t in state.market_trades.values()
                if (t["stock_owner_id"] == "market"
                    and t["payment_resource"] == "coin_copper"
                    and t["buyer_id"] != FARMER
                    and t["executed_at"] < wage["paid_at"])
            ]
            assert sum(t["total_paid"] for t in genuine_incoming_market_revenue) >= 2, (
                "employer funds must derive from previous actual consumer sales"
            )
            assert all(t["pay_source_before"] - t["pay_source_after"] == t["total_paid"]
                       for t in genuine_incoming_market_revenue)
            assert all(t["pay_target_after"] - t["pay_target_before"] == t["total_paid"]
                       for t in genuine_incoming_market_revenue)

            events = _authentic_events(db)
            # Real cash cargo with its own authorized worker must move along
            # market->bakery->east's scheduled route before the farm pays.
            cash_pickups = [
                (i, e) for i, e in events
                if (e["event_type"] == "SupplyCargoPicked"
                    and e["actor_id"] == COURIER
                    and e["data"].get("resource") == "coin_copper")
            ]
            cash_deliveries = [
                (i, e) for i, e in events
                if (e["event_type"] == "SupplyCargoDelivered"
                    and e["actor_id"] == COURIER
                    and e["data"].get("resource") == "coin_copper")
            ]
            wage_events = [
                (i, e) for i, e in events
                if (e["event_type"] == "ProductionWagePaid"
                    and e["data"].get("job_id") == job_id)
            ]
            assert cash_pickups and cash_deliveries, "no actual copper cargo traveled"
            assert len(wage_events) == 1, "one authenticated wage per completed job"
            wage_seq, wage_event = wage_events[0]
            assert wage_event["time"] == wage["paid_at"]
            assert any(i < wage_seq for i, e in cash_deliveries), (
                "site wage was not preceded by a physically delivered copper cargo"
            )
            assert any(i < wage_seq for i, e in cash_pickups)

            own_purchases = [
                t for t in state.market_trades.values()
                if t["buyer_id"] == FARMER and t["resource"] == "food"
            ]
            own_meals = [
                m for m in state.consumptions.values()
                if m["npc_id"] == FARMER
            ]
            assert len(own_purchases) == len(own_meals) == 1
            trade, meal = own_purchases[0], own_meals[0]
            assert trade["site_id"] == "market"
            assert trade["total_paid"] == 2
            assert trade["pay_source_before"] - trade["pay_source_after"] == 2
            assert trade["goods_target_after"] - trade["goods_target_before"] == 1
            assert trade["executed_at"] >= wage["paid_at"]
            assert meal["location_id"] == "market"
            assert meal["consumed_at"] >= trade["executed_at"]
            assert meal["hunger_after"] < meal["hunger_before"]

            travel = [
                t for t in state.travels.values() if t["npc_id"] == FARMER
            ]
            arrivals = [
                t for t in travel
                if t["status"] == "arrived" and t["destination"] == "market"
            ]
            assert arrivals and any(
                t["arrived_at"] <= trade["executed_at"]
                and t["start"] >= wage["paid_at"] for t in arrivals
            ), "cash-paid buyer must first physically reach known market"
            assert all(
                (t["route_id"] in state.routes
                 and t["due"] - t["start"] == state.routes[t["route_id"]]["seconds"]
                 and {t["origin"], t["destination"]} ==
                     {state.routes[t["route_id"]]["a"],
                      state.routes[t["route_id"]]["b"]})
                for t in travel
            )
            assert any(t["origin"] == "market"
                       and t["destination"] == EAST
                       and t["status"] == "arrived" for t in travel), (
                "shopper must physically return toward workplace"
            )

            # No direct net income creation: market buyer's actual two copper
            # return to a LEGAL site owner after the farmer really consumes.
            assert sum(bal.get("coin_copper", 0)
                       for bal in state.resources.values()) == 12
            assert state.resources[FARMER]["coin_copper"] == 0
            assert state.resources[FARMER]["food"] == 0
            assert db.verify(WORLD).to_dict() == state.to_dict()

            print("PLAY48_REAL_SALE_WORK_PAY_BUY_EAT_PROVEN "+json.dumps({
                "fixture": "nine-existing-NPC-micro-scenario-not-13NPC-release",
                "initial_copper": 12,
                "real_market_revenue_before_job": sum(
                    t["total_paid"] for t in genuine_incoming_market_revenue
                ),
                "cash_cargo_pickups": len(cash_pickups),
                "cash_cargo_deliveries": len(cash_deliveries),
                "worker_wage_paid": wage["amount"],
                "worked_finished_at": job["finished_at"],
                "wage_paid_at": wage["paid_at"],
                "purchase_at": trade["executed_at"],
                "meal_at": meal["consumed_at"],
                "real_travel_legs": len(travel),
                "measurements": measurements,
                "original_13NPC_168h_recovery_proven": False,
            }, sort_keys=True), flush=True)
        finally:
            clock.close_session(WORLD)
