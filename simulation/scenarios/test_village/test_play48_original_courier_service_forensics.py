"""PLAY48 read-only paid-service forensic: real physically delivered parcels.

No hypothetical transfers. Uses actual stored DomainEvent payloads and verified
13-NPC original simulation, not NPC narration or inferred service.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from carlos_sim import SQLiteEventStore, TimeEngine
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.hydrology import FiniteWaterService
from carlos_sim.courier_provisions import (
    choose_market_owned_food_refill, choose_courier_provision,
    _market_uncommitted_bread_after_sales,
)
from test_play38_multi_farm_couriers import WORLD
from test_play48_in_kind_market_wages_ab import seeded, report
from test_play48_real_watch_income_24h import engine, HOUR
from test_play48_finite_hunt_fish_roads import conserve_diverse

HOURS = (6, 24, 30, 36, 48)


def logged_delivery_history(db, hour):
    events = db.db.execute(
        "SELECT seq,payload FROM events WHERE world_id=? ORDER BY seq", (WORLD,)
    ).fetchall()
    deliveries = {who: [] for who in ("hana", "huda")}
    completed_wages = {who: [] for who in ("hana", "huda")}
    market_trades = []
    for sequence, payload in events:
        evt = json.loads(payload)
        kind, who, at = evt["event_type"], evt["actor_id"], evt["time"]
        if at > hour * HOUR:
            continue
        data = evt["data"]
        if kind == "SupplyCargoDelivered" and who in deliveries:
            deliveries[who].append({
                "seq": sequence, "hour": round(at / HOUR, 3),
                "resource": data["resource"],
            })
        elif kind == "CourierProvisionPaid":
            hired = data["courier_id"]
            if hired in completed_wages:
                completed_wages[hired].append({
                    "seq": sequence, "hour": round(at / HOUR, 3),
                    "service_deliveries": data["service_deliveries"],
                    "contract": data["id"],
                })
        elif kind == "MarketTradeExecuted":
            market_trades.append({"seq":sequence, "hour":round(at/HOUR,3)})
    return {
        who: {
            "delivered_by_resource": dict(sorted(Counter(
                row["resource"] for row in deliveries[who]).items())),
            "real_delivery_rows": deliveries[who],
            "signed_wages": completed_wages[who],
        } for who in deliveries
    }, len(market_trades)


def investigate(path: Path):
    seeded(path, contract=True)
    with SQLiteEventStore(path) as db:
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            sim = engine(db, clock, reserve_trader_meal=True,
                         deferred_market_courier_wage=True)
            sim.merchant_food_wage_enabled = True
            state = db.verify(WORLD)
            for hour in HOURS:
                state = sim.advance(
                    WORLD, seconds=hour*HOUR-state.time,
                    command_id=f"real-courier-service-forensic:{hour}",
                    expected_revision=state.revision).state
                assert state.time == hour*HOUR
                conserve_diverse(state)
                assert db.verify(WORLD).to_dict() == state.to_dict()
                assert audit_npc_economy(state)["copper_known_total"] == 12
                timeline, true_sales = logged_delivery_history(db, hour)
                people = {}
                for who in ("hana", "huda"):
                    circuit = state.supply_circuits[who]
                    ledger = [c for c in state.courier_provisions.values()
                              if c["courier_id"] == who]
                    people[who] = {
                        **timeline[who],
                        "hunger": state.npcs[who]["needs"]["hunger"],
                        "food": state.resources[who]["food"],
                        "cash": state.resources[who]["coin_copper"],
                        "place": state.entities[who]["location_id"],
                        "current_route_index": circuit["index"],
                        "current_carry": circuit["carry"],
                        "total_deliveries": circuit["deliveries"],
                        "signed_market_contracts": [{
                            "payer_site": c["payer_site"],
                            "authorized_units": c["authorized_total_units"],
                            "funded_units": c["total_units"],
                            "remaining_units": c["remaining"],
                            "paid_services": [p["service_deliveries"]
                                              for p in c["payments"]]
                        } for c in ledger],
                        "at_market_can_collect_old_escrow":
                            choose_courier_provision(state, who) is not None,
                        "at_market_can_refill_from_real_surplus":
                            choose_market_owned_food_refill(state, who) is not None,
                    }
                    assert circuit["deliveries"] == len(timeline[who]["real_delivery_rows"])
                # No invented wage: identify the actual potential employer
                # on Huda's completed routes and whether it owns unpromised
                # food after all existing buyer, production and barter claims.
                from carlos_sim.food_for_work import _available_site_food
                from carlos_sim.supply import (
                    _bakery_has_pending_physical_farm_claim,
                )
                local_employers = {}
                for farm_or_bakery in ("farm", "farm_east", "bakery", "market"):
                    local_employers[farm_or_bakery] = {
                        "owned_food": state.resources.get(farm_or_bakery, {}).get("food"),
                        "unpromised_food": _available_site_food(state, farm_or_bakery),
                        "owned_copper": state.resources.get(farm_or_bakery, {}).get("coin_copper"),
                        "open_food_quotes": sum(
                            offer["remaining"] for offer in state.market_offers.values()
                            if offer["status"] == "open"
                            and offer["stock_owner_id"] == farm_or_bakery
                            and offer["resource"] == "food"),
                        "completed_production": sum(
                            job["status"] == "completed"
                            and job["site_id"] == farm_or_bakery
                            for job in state.production_jobs.values()),
                    }
                bakery_barter_claim = _bakery_has_pending_physical_farm_claim(state)
                overall = report(state)
                print("PLAY48_HUDA_AUTHENTIC_DELIVERY_VS_PAID_SERVICE " +
                    json.dumps({
                        "hour": hour, "service": people,
                        "real_market_trade_events": true_sales,
                        "market_unquoted_food_after_customer_claims":
                            _market_uncommitted_bread_after_sales(state),
                        "market_merchant_food_paid": overall["salma_earned_site_food"],
                        "actual_potential_employers": local_employers,
                        "bakery_bread_reserved_for_farm_return": bakery_barter_claim,
                        "total_copper_physical": overall["cash_total"],
                        "sqlite_replay_verified": True,
                    }, sort_keys=True), flush=True)
                if hour == 24:
                    state = FiniteWaterService(db, clock).record(
                        WORLD, "well", "fixed-external-rain-day1", 2,
                        command_id="real-attributed-source-day1",
                        expected_revision=state.revision).state
                    assert db.verify(WORLD).to_dict() == state.to_dict()
            assert db.snapshot(WORLD).to_dict() == state.to_dict()
        finally:
            clock.close_session(WORLD)
    with SQLiteEventStore(path) as db:
        assert db.verify(WORLD).to_dict() == state.to_dict()
        assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert not db.db.execute("PRAGMA foreign_key_check").fetchall()


def test_real_courier_service_receipts_have_provenance(tmp_path):
    investigate(tmp_path / "source-traced-real-13npc-courier-service.sqlite")
