"""PLAY48: a site-funded, genuine post-sale retail service wage pilot.

A new *signed time-zero* optional market contract is the only difference from
the archived genuine 13NPC/12-copper candidate. Nothing gives any NPC a coin.
Only an authorized local buyer->site trade may transfer one *existing* site
coin onward to its actual local seller. No market sale means NO salary.
This is bounded causal evidence only, not 168h economic acceptance.
"""
from __future__ import annotations

import json

import pytest

from carlos_sim import (DomainEvent, InvalidEvent, LivingWorldEngine,
                        SQLiteEventStore, TimeEngine)
from carlos_sim.domain import WorldState
from carlos_sim.economic_diagnostics import audit_npc_economy
from test_play38_multi_farm_couriers import seed_two_field_world, WORLD
from test_play47_joined_professions import _joined_bootstrap
from test_play47_closure_endurance import DAY
from test_play48_finite_hunt_fish_roads import conserve_diverse
from test_play48_peddler_24h_diagnostic import measures, market_resale_gates

HOUR = 3600


def bootstrap(db, *, initial_market_food, **options):
    assert initial_market_food == 3
    assert options == {
        "water": 2, "seed": 1, "harvest_yield": 3,
        "personal_food": 0, "market_wallets": True,
        "hungry_market_buyers": True, "one_hungry_market_buyer": False,
    }
    return _joined_bootstrap(
        db, initial_market_food=3, wilderness_food_jobs_enabled=True,
        wilderness_food_peddler_enabled=True,
        food_for_work_bakery_enabled=True, bakery_opening_food_wage=True,
        retail_service_wage_enabled=True,
    )


def seed(path):
    with SQLiteEventStore(path) as db:
        seed_two_field_world(
            db, east_growth_seconds=DAY, east_grain_yield=12,
            initial_water=2, initial_market_food=3,
            market_wallets=True, hungry_market_buyers=True,
            cash_return=True, waged_harvest=True, harvest_wage_copper=2,
            bootstrap=bootstrap,
        )
        s = db.load(WORLD)
        s = db.append(WORLD, "real-retail:ordinary-natural-policy",
                      s.revision, [
            DomainEvent("WaterSourceConfigured", None, "finite well", 0,
                        {"site_id": "well", "capacity": 8}),
            DomainEvent("MetabolismPolicyConfigured", None, "actual needs", 0,
                        {"hunger_seconds_per_point": 3600,
                         "activity_hunger_percent": 20}),
        ], bootstrap=True)
        assert len(s.npcs) == 13
        assert (s.schema_version, s.rules_version) == (45, 63)
        assert s.market_stalls["market"] == {
            "keeper_id": "salma", "commission_coin": 1,
        }
        assert audit_npc_economy(s)["copper_known_total"] == 12
        assert db.verify(WORLD).to_dict() == s.to_dict()
        conserve_diverse(s)


def test_signed_actual_retail_24h_never_issues_credit_or_fake_jobs(tmp_path):
    path = tmp_path / "one-real-coin-per-completed-market-trade.sqlite"
    seed(path)
    rows = []
    with SQLiteEventStore(path) as db:
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            engine = LivingWorldEngine(
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
                seek_alternative_food_market_enabled=True,
            )
            for hour in (6, 12, 18, 24):
                initial = db.verify(WORLD)
                s = engine.advance(
                    WORLD, seconds=hour*HOUR - initial.time,
                    expected_revision=initial.revision,
                    command_id=f"signed-retail-wages:{hour}",
                ).state
                assert db.verify(WORLD).to_dict() == s.to_dict()
                assert db.db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
                assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
                conserve_diverse(s)
                audit = audit_npc_economy(s)
                assert audit["copper_scope_complete"]
                assert audit["copper_known_total"] == 12
                receipts = [trade["retail_wage"]
                            for trade in s.market_trades.values()
                            if "retail_wage" in trade]
                assert all(r["worker_id"] == "salma"
                           and r["employer_site"] == "market"
                           and r["amount"] == 1
                           and r["site_before"] - r["site_after"] == 1
                           and r["worker_after"] - r["worker_before"] == 1
                           for r in receipts)
                assert len(receipts) == sum(
                    t["seller_id"] == "salma" and t["site_id"] == "market"
                    and t["total_paid"] >= 2
                    for t in s.market_trades.values())
                row = measures(s)
                row["real_signed_retail_service_wages"] = len(receipts)
                row["salma_personal_copper"] = s.resources["salma"]["coin_copper"]
                row["adel_personal_copper"] = s.resources["adel"]["coin_copper"]
                row["cash_by_owner"] = {
                    key: amount for key, amount in
                    audit["copper_known_by_owner"].items() if amount
                }
                row["trader_eligible_market_buyers"] = (
                    market_resale_gates(s)["eligible_on_site_purchases"]
                )
                rows.append(row)
            assert rows[0]["real_signed_retail_service_wages"] > 0
            frozen = db.verify(WORLD).to_dict()
            from carlos_sim.domain import WorldState
            forged = WorldState.from_dict(frozen).to_dict()
            market_trade = next(
                t for t in forged["market_trades"].values()
                if "retail_wage" in t
            )
            market_trade["retail_wage"]["amount"] = 2
            with pytest.raises(ValueError):
                WorldState.from_dict(forged)
            assert db.verify(WORLD).to_dict() == frozen
        finally:
            clock.close_session(WORLD)
    print("PLAY48_ACTUAL_TRUSTED_RETAIL_WAGES_24H " +
          json.dumps(rows, sort_keys=True), flush=True)


def test_unsigned_or_midworld_signed_market_contract_rejected(tmp_path):
    path = tmp_path / "unauthorized-retail-salary.sqlite"
    seed(path)
    with SQLiteEventStore(path) as db:
        before = db.verify(WORLD)
        with pytest.raises(InvalidEvent):
            db.append(WORLD, "fake-late-contract", before.revision, [
                DomainEvent("MarketStallConfigured", None, "unsigned new salary",
                            before.time, {
                                "site_id": "hunting_woods",
                                "keeper_id": "omar",
                                "commission_coin": 1,
                            }),
            ], market_authorized=True)
        assert db.verify(WORLD).to_dict() == before.to_dict()
