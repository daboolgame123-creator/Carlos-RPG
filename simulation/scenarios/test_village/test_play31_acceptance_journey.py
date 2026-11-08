"""PLAY-31 acceptance: independent full player journey through active seven-NPC economy.

Only player-authorized gateway calls. Never access hidden NPC state as a
player-facing view; internal audit is used strictly by this trusted test.
"""
from __future__ import annotations

import pytest

from carlos_sim import SQLiteEventStore, TimeEngine
from carlos_sim.store import InvalidEvent
from play_physical_supply import WORLD, audit_physical_supply
from play_village_local import create_session, execute


def test_carlos_walks_into_market_sees_quote_buys_and_preserves_stock(tmp_path):
    with SQLiteEventStore(tmp_path / "journey.sqlite") as db:
        clock = TimeEngine(db)
        gateway = create_session(db, clock)
        try:
            before = db.verify(WORLD)
            assert before.resources["carlos"]["coin_copper"] == 10
            assert before.resources["carlos"]["food"] == 0
            assert execute(gateway, "offers", 1).details["offers"] == ()
            with pytest.raises((ValueError, InvalidEvent)):
                execute(gateway, "buy forged-local-quote 1 2", 2)
            assert db.verify(WORLD).to_dict() == before.to_dict()

            assert execute(gateway, "move home-market", 3).status == "traveling"
            assert execute(gateway, "wait 90", 4).time == 90
            assert execute(gateway, "scene", 5).details["location_id"] == "market"
            scene = execute(gateway, "scene", 6).details
            assert "salma" in {person["id"] for person in scene["occupants"]}

            offers = execute(gateway, "offers", 7).details["offers"]
            quote = next(q for q in offers if q["resource"] == "food")
            assert quote["seller_id"] == "salma"
            assert quote["unit_price"] == 2
            assert quote["available"] >= 1

            # Same site, real existing quote, exact price, finite personal cash.
            bought = execute(
                gateway, f"buy {quote['offer_id']} 1 2", 8,
            )
            assert bought.status == "purchased"
            supplies = execute(gateway, "supplies", 9).details["balances"]
            assert supplies["food"] == 1
            assert supplies["coin_copper"] == 8
            receipts = execute(gateway, "purchases", 10).details
            assert receipts["total"] >= 1
            assert receipts["recent"][0]["total_paid"] == 2
            handoff = execute(gateway, "handoff", 11)
            assert handoff["canonical_story"] is False
            assert handoff["player_supplies"]["balances"] == supplies
            assert "npcs" not in handoff and "resources" not in handoff
            state = db.verify(WORLD)
            assert audit_physical_supply(
                state, seed=1, water=2, buyer_copper=2, personal_food=2,
                initial_market_food=2,
            )["copper"] == 12
            db.snapshot(WORLD)
            assert db.verify(WORLD).to_dict() == state.to_dict()
        finally:
            clock.close_session(WORLD)


def test_player_speech_is_local_and_does_not_autodirect_npcs(tmp_path):
    with SQLiteEventStore(tmp_path / "conversation.sqlite") as db:
        clock = TimeEngine(db)
        gateway = create_session(db, clock)
        try:
            original = db.verify(WORLD).to_dict()
            with pytest.raises((ValueError, InvalidEvent)):
                execute(gateway, "talk salma greeting Hello", 1)
            assert db.verify(WORLD).to_dict() == original
            execute(gateway, "move home-market", 2)
            execute(gateway, "wait 90", 3)
            spoke = execute(gateway, "talk salma greeting Hello", 4)
            assert spoke.status == "interacted"
            assert spoke.details["recipient_id"] == "salma"
            history = execute(gateway, "conversations", 5)
            assert history.status == "conversations"
            assert db.verify(WORLD).to_dict() == db.load(WORLD).to_dict()
        finally:
            clock.close_session(WORLD)
