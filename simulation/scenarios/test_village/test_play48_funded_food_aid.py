"""PLAY-48E: authorized food access can revive a blocked courier in a local proof.

Narrow service feasibility, NOT autonomous 96h recovery: a trusted test driver
explicitly orders a funded buyer to travel and help. Only existing 42/57
Market/Movement/Assistance/Consumption/Supply reducers may change the world.
"""
from __future__ import annotations

import json

import pytest

from carlos_sim import (
    SQLiteEventStore, TimeEngine, LivingWorldEngine, NPCMovementService,
    NPCAssistanceService, NPCConsumptionService,
)
from carlos_sim.market import NPCMarketService
from carlos_sim.store import InvalidEvent
from carlos_sim.supply_diagnostics import audit_courier
from play_physical_supply import seed_physical_supply, audit_physical_supply, WORLD


def test_physically_funded_local_bread_assistance_restores_one_real_delivery(tmp_path):
    with SQLiteEventStore(tmp_path / "manual-contract-feasibility.sqlite") as db:
        seed_physical_supply(
            db, market_wallets=True, initial_market_food=3, courier_hunger=89,
        )
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            market = NPCMarketService(db, clock)
            movement = NPCMovementService(db, clock)
            assistance = NPCAssistanceService(db, clock)
            consumption = NPCConsumptionService(db, clock)
            state = db.load(WORLD)
            assert sum(x.get("coin_copper", 0)
                       for x in state.resources.values()) == 12
            # A real seller owns three opening loaves. Omar personally pays
            # two of his four INITIAL copper to buy just one existing loaf.
            offer = market.post(
                WORLD, "salma", "market", "market", "welfare-loaf",
                "food", 1, "coin_copper", 2,
                expected_revision=state.revision,
            )
            sale = market.buy(
                WORLD, "omar", "welfare-sale", "welfare-loaf", 1, 2,
                expected_revision=offer.state.revision,
            )
            state = sale.state
            assert state.resources["omar"]["coin_copper"] == 2
            assert state.resources["omar"]["food"] == 1
            assert state.resources["market"]["coin_copper"] == 2
            assert state.resources["market"]["food"] == 2

            # Only the trusted clock runs. The courier's unmet hunger reaches
            # the actual supply selector cutoff; no NPC is moved by fiat.
            # A bare TimeEngine is intentionally NOT a survival clock:
            # hunger ages only under the authorized opt-in survival coordinator.
            # Disable the supply coordinator during this causal blockade setup
            # so no courier trips occur before the recovery comparison.
            aging_engine = LivingWorldEngine(
                db, clock, economic_enabled=True, agriculture_enabled=True,
                economy_only_enabled=True, survival_enabled=True,
                supply_enabled=False, max_events_per_advance=5000,
            )
            state = aging_engine.advance(
                WORLD, seconds=3600, command_id="play48:aid:starve",
                expected_revision=state.revision,
            ).state
            before = audit_courier(state, "huda", supply_enabled=True)
            assert before["needs"]["hunger"] >= 90
            assert before["next_action"] is None
            assert "hunger_at_or_above_90" in before["blocked_reasons"]
            assert state.resources["huda"]["food"] == 0
            market_food_before_help = state.resources["market"]["food"]
            assert 0 <= market_food_before_help <= 2

            # Omar must carry the bought loaf for each adjacent road,
            # consuming all 150 simulated seconds of market -> bakery ->
            # farm -> well. No direct teleported delivery.
            for route, label in (
                ("bakery-market", "bakery"),
                ("farm-bakery", "farm"),
                ("well-farm", "well"),
            ):
                trip = movement.start(
                    WORLD, "omar", route, "play48:aid:" + label,
                    expected_revision=state.revision,
                )
                assert trip.state.entities["omar"]["location_id"] != label
                state = clock.advance(
                    WORLD, seconds=trip.due-state.time,
                    command_id="play48:aid:arrive:" + label,
                    expected_revision=trip.state.revision,
                ).state
                assert state.entities["omar"]["location_id"] == label
            assert state.resources["omar"]["food"] == 1
            assert state.entities["huda"]["location_id"] == "well"

            # A signed food request + personal promise + local physical
            # transfer. Market SITE stock cannot be given by an NPC who
            # never legally bought it.
            request = assistance.request(
                WORLD, "huda", "omar", "food", 1, "play48:aid:request",
                expected_revision=state.revision,
            )
            promise = assistance.respond(
                WORLD, "omar", "play48:aid:request",
                accept=True, command_id="play48:aid:accept",
                expected_revision=request.state.revision,
            )
            fulfilled = assistance.deliver(
                WORLD, "omar", "play48:aid:request",
                command_id="play48:aid:physical-handover",
                expected_revision=promise.state.revision,
            )
            state = fulfilled.state
            assert state.resources["omar"]["food"] == 0
            assert state.resources["huda"]["food"] == 1
            with pytest.raises(InvalidEvent):
                assistance.deliver(
                    WORLD, "omar", "play48:aid:request",
                    command_id="play48:aid:duplicate-handover",
                    expected_revision=state.revision,
                )
            assert db.load(WORLD).to_dict() == state.to_dict()

            # Eating from personal inventory, never consigned cargo,
            # lowers genuine hunger sufficiently to resume pickup.
            fed = consumption.eat(
                WORLD, "huda", 1, command_id="play48:aid:eat",
                expected_revision=state.revision,
            )
            state = fed.state
            assert state.npcs["huda"]["needs"]["hunger"] <= 75
            assert state.resources["huda"]["food"] == 0
            eligible = audit_courier(state, "huda", supply_enabled=True)
            assert eligible["next_action"] == "SupplyCargoPicked"
            assert state.resources["market"]["food"] == market_food_before_help, (
                "Actual local help transfers personal bread, not site-owned stock"
            )
            assert sum(x.get("coin_copper", 0)
                       for x in state.resources.values()) == 12
            # The first real local water leg and delivery can now be carried
            # autonomously by the existing unmodified supply coordinator.
            engine = LivingWorldEngine(
                db, clock, economic_enabled=True, agriculture_enabled=True,
                economy_only_enabled=True, navigation_enabled=True,
                routines_enabled=True, supply_enabled=True,
                survival_enabled=True, max_events_per_advance=5000,
            )
            result = engine.advance(
                WORLD, seconds=350, command_id="play48:aid:resume",
                expected_revision=state.revision,
            )
            state = result.state
            assert state.supply_circuits["huda"]["deliveries"] >= 1
            assert "coin_copper" not in state.resources["huda"], (
                "A worker who receives bread never receives fictitious cash"
            )
            audit_physical_supply(
                state, seed=1, water=2, buyer_copper=2,
                initial_market_food=3,
            )
            assert sum(x.get("coin_copper", 0)
                       for x in state.resources.values()) == 12
            assert len(state.consumptions) == 1
            assert db.snapshot(WORLD).to_dict() == state.to_dict()
            assert db.verify(WORLD).to_dict() == state.to_dict()
            print("PLAY48_REAL_FOOD_AID_FEASIBILITY " + json.dumps({
                "travel_legs_by_real_buyer": 3,
                "loaf_paid_copper": 2,
                "market_food_after_omar_sale": 2,
                "market_food_before_help": market_food_before_help,
                "physical_food_transfer": 1,
                "authentic_meal": 1,
                "blocked_hunger_before": before["needs"]["hunger"],
                "hunger_after": fed.new_hunger,
                "real_courier_deliveries_after_recovery": state.supply_circuits["huda"]["deliveries"],
                "total_copper": 12, "food_created_after_genesis": False,
                "all_ownership_reducers_unmodified": True,
                "manual_local_aid_driver_not_autonomous": True,
                "not_96h_recovery": True,
            }, sort_keys=True), flush=True)
        finally:
            clock.close_session(WORLD)
