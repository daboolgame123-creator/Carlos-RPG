"""PLAY-48 funded relief adversarial boundaries and default-off parity."""
from __future__ import annotations

from carlos_sim import SQLiteEventStore, TimeEngine, LivingWorldEngine
from carlos_sim.assistance import NPCAssistanceService
from carlos_sim.market import NPCMarketService
from carlos_sim.movement import NPCMovementService
from carlos_sim.npc_food_relief import choose_aid_relay
from play_physical_supply import WORLD, seed_physical_supply
from test_play48_autonomous_funded_aid import (
    _surveyed_donor_at_well, _starve_safely, _own_copper,
)


def _request(db, clock, state, ident):
    svc = NPCAssistanceService(db, clock)
    return svc.request(
        WORLD, "huda", "omar", "food", 1, ident,
        expected_revision=state.revision,
    ).state


def test_cannot_find_remote_market_without_personal_road_experience(tmp_path):
    with SQLiteEventStore(tmp_path / "no-remote-market.sqlite") as db:
        seed_physical_supply(
            db, market_wallets=True, initial_market_food=3,
            courier_hunger=89,
        )
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        state = db.load(WORLD)
        movement = NPCMovementService(db, clock)
        # Legitimate historical manual travel without any opt-in navigation
        # survey. The current location is real but the character has never
        # registered the *memory* required by autonomous route planning.
        for rid, dest in (
            ("bakery-market", "bakery"),
            ("farm-bakery", "farm"),
            ("well-farm", "well"),
        ):
            trip = movement.start(
                WORLD, "omar", rid, "unlearned-" + dest,
                expected_revision=state.revision,
            )
            state = clock.advance(
                WORLD, seconds=trip.due-state.time,
                command_id="unlearned-arrive-" + dest,
                expected_revision=trip.state.revision,
            ).state
        assert "omar" not in state.navigation
        state = _request(db, clock, state, "aid:no-road")
        assert state.resources["market"]["food"] == 3
        assert state.resources["omar"]["coin_copper"] == 4
        assert choose_aid_relay(state, "omar") is None
        assert db.verify(WORLD).to_dict() == state.to_dict()
        clock.close_session(WORLD)


def test_absent_personal_coin_slot_cannot_be_replaced_by_site_funds(tmp_path):
    with SQLiteEventStore(tmp_path / "no-coin.sqlite") as db:
        clock = TimeEngine(db)
        state = _surveyed_donor_at_well(
            db, clock, market_wallets=False,
        )
        assert state.resources["omar"].get("coin_copper") is None
        assert _own_copper(state) == 12
        state = _request(db, clock, state, "aid:no-money")
        assert choose_aid_relay(state, "omar") is None
        assert choose_aid_relay(state, "huda") is None  # entrusted supply
        assert db.verify(WORLD).to_dict() == state.to_dict()
        clock.close_session(WORLD)


def test_unposted_and_overpriced_remote_quotes_never_finance_food(tmp_path):
    with SQLiteEventStore(tmp_path / "bad-local-price.sqlite") as db:
        clock = TimeEngine(db)
        state = _surveyed_donor_at_well(db, clock)
        state = _request(db, clock, state, "aid:real-quote")
        original = choose_aid_relay(state, "omar")
        assert original is not None and original.kind == "travel"
        assert original.route_id == "well-farm"
        assert _own_copper(state) == 12
        mover = NPCMovementService(db, clock)
        for rid, dest in (
            ("well-farm", "farm"),
            ("farm-bakery", "bakery"),
            ("bakery-market", "market"),
        ):
            trip = mover.start(
                WORLD, "omar", rid, "informed-" + dest,
                expected_revision=state.revision,
            )
            state = clock.advance(
                WORLD, seconds=trip.due-state.time,
                command_id="informed-arrive-" + dest,
                expected_revision=trip.state.revision,
            ).state
            assert _own_copper(state) == 12
        assert state.entities["omar"]["location_id"] == "market"
        assert choose_aid_relay(state, "omar") is None, (
            "Remote market existence never implies a real posted sale"
        )
        market = NPCMarketService(db, clock)
        too_expensive = market.post(
            WORLD, "salma", "market", "market", "aid-price-three",
            "food", 1, "coin_copper", 3,
            expected_revision=state.revision,
        ).state
        assert choose_aid_relay(too_expensive, "omar") is None
        valid = market.post(
            WORLD, "salma", "market", "market", "aid-price-two",
            "food", 1, "coin_copper", 2,
            expected_revision=too_expensive.revision,
        ).state
        intent = choose_aid_relay(valid, "omar")
        assert intent is not None and intent.kind == "buy"
        assert (intent.offer_id, intent.price) == ("aid-price-two", 2)
        purchased = market.buy(
            WORLD, "omar", "paid-firsthand", intent.offer_id, 1, intent.price,
            expected_revision=valid.revision,
        ).state
        assert purchased.resources["omar"]["food"] == 1
        assert purchased.resources["omar"]["coin_copper"] == 2
        assert purchased.resources["market"]["food"] == 2
        assert _own_copper(purchased) == 12
        back = choose_aid_relay(purchased, "omar")
        assert back is not None and back.kind == "travel"
        assert db.verify(WORLD).to_dict() == purchased.to_dict()
        clock.close_session(WORLD)


def test_existing_assistance_behavior_unchanged_with_relay_disabled(tmp_path):
    with SQLiteEventStore(tmp_path / "off-by-default.sqlite") as db:
        clock = TimeEngine(db)
        state = _surveyed_donor_at_well(db, clock)
        state = _starve_safely(db, clock, state)
        old = LivingWorldEngine(
            db, clock, economic_enabled=True, agriculture_enabled=True,
            economy_only_enabled=True, survival_enabled=True,
            assistance_enabled=True, consumption_enabled=True,
            navigation_enabled=True, supply_enabled=False,
            aid_relay_enabled=False, max_events_per_advance=5000,
        )
        state = old.advance(
            WORLD, seconds=60, command_id="aid:default-off",
            expected_revision=state.revision,
        ).state
        req = [item for item in state.obligations.values()
               if item["requester"] == "huda" and item["provider"] == "omar"]
        assert len(req) == 1
        assert req[0]["quantity"] == 3
        assert req[0]["status"] == "declined"
        assert not any(t["buyer_id"] == "omar" for t in state.market_trades.values())
        assert not any(t["npc_id"] == "omar" and t["start"] > 3600
                       for t in state.travels.values())
        assert _own_copper(state) == 12
        assert db.verify(WORLD).to_dict() == state.to_dict()
        clock.close_session(WORLD)
