"""PLAY-32 acceptance and adversarial checks in an actual seven-NPC world."""
from __future__ import annotations

import pytest

from carlos_sim import DomainEvent, SQLiteEventStore, TimeEngine
from carlos_sim.store import DuplicateCommand, InvalidEvent, RevisionConflict
from play_physical_supply import WORLD, audit_physical_supply
from play_village_local import create_session, execute

Q = "market_first_loaf"


def _at_real_market(gateway):
    assert execute(gateway, "move home-market", 10).status == "traveling"
    assert execute(gateway, "wait 90", 11).time == 90
    assert execute(gateway, "offers", 12).details["offers"] == ()
    assert execute(gateway, "wait 30", 13).time == 120


def _real_purchase(gateway):
    q = next(
        x for x in execute(gateway, "offers", 14).details["offers"]
        if x["resource"] == "food" and x["seller_id"] == "salma"
    )
    assert q["unit_price"] == 2
    receipt = execute(gateway, f"buy {q['offer_id']} 1 2", 15)
    assert receipt.status == "purchased"
    return receipt.details["trade_id"]


def test_accept_progress_claim_conserve_replay_and_private_handoff(tmp_path):
    path = tmp_path / "quest.sqlite"
    with SQLiteEventStore(path) as db:
        clock = TimeEngine(db)
        g = create_session(db, clock)
        try:
            start = execute(g, "quests", 1)
            assert start.status == "quests"
            assert start.details["quests"][0]["status"] == "available"
            accepted = execute(g, f"accept {Q}", 2)
            assert accepted.status == "quest_accepted"
            quest = execute(g, "quests", 3).details["quests"][0]
            assert quest["status"] == "accepted" and quest["progress"] == 0
            assert "npcs" not in str(quest).lower()
            with pytest.raises(InvalidEvent):
                execute(g, f"claim {Q}", 4)
            _at_real_market(g)
            trade_id = _real_purchase(g)
            progress = execute(g, "quests", 16).details["quests"][0]
            assert progress["status"] == "completed"
            assert progress["progress"] == 1 and progress["goal"] == 1
            assert progress["evidence_trade_id"] == trade_id
            before = execute(g, "supplies", 17).details["balances"]
            assert before["coin_copper"] == 8 and before["food"] == 1
            claimed = execute(g, f"claim {Q}", 18)
            assert claimed.status == "quest_reward_claimed"
            after = execute(g, "supplies", 19).details["balances"]
            assert after["coin_copper"] == 9 and after["food"] == 1
            assert execute(g, "quests", 20).details["quests"][0]["status"] == "claimed"
            private = execute(g, "handoff", 21)
            assert private["player_quests"]["quests"][0]["status"] == "claimed"
            assert "npcs" not in private and "resources" not in private
            assert private["world_id"] == WORLD
            assert audit_physical_supply(db.verify(WORLD), seed=1, water=2,
                buyer_copper=2, personal_food=2, initial_market_food=2)["copper"] == 12
            state = db.verify(WORLD)
            assert state.resources["market"]["coin_copper"] == 1
            assert state.player_quests["carlos"][Q]["claimed_at"] == 120
            db.snapshot(WORLD)
            assert db.load(WORLD).to_dict() == db.verify(WORLD).to_dict()
            frozen = state.to_dict()
        finally:
            clock.close_session(WORLD)
    with SQLiteEventStore(path) as reopened:
        assert reopened.verify(WORLD).to_dict() == frozen
        assert reopened.load(WORLD).to_dict() == frozen


def test_cannot_claim_before_verified_purchase_or_accept_twice(tmp_path):
    with SQLiteEventStore(tmp_path / "no-credit.sqlite") as db:
        clock = TimeEngine(db)
        g = create_session(db, clock)
        try:
            execute(g, f"accept {Q}", 1)
            original = db.verify(WORLD).to_dict()
            with pytest.raises(InvalidEvent):
                execute(g, f"claim {Q}", 2)
            with pytest.raises(InvalidEvent):
                execute(g, f"accept {Q}", 3)
            with pytest.raises(InvalidEvent):
                execute(g, "accept forged_quest", 4)
            assert db.verify(WORLD).to_dict() == original
        finally:
            clock.close_session(WORLD)


def test_purchase_before_accept_does_not_backdate_completion(tmp_path):
    with SQLiteEventStore(tmp_path / "late.sqlite") as db:
        clock = TimeEngine(db)
        g = create_session(db, clock)
        try:
            _at_real_market(g)
            _real_purchase(g)
            execute(g, f"accept {Q}", 30)
            quest = execute(g, "quests", 31).details["quests"][0]
            assert quest["progress"] == 0 and quest["status"] == "accepted"
            with pytest.raises(InvalidEvent):
                execute(g, f"claim {Q}", 32)
        finally:
            clock.close_session(WORLD)


def test_forged_reward_event_and_unsupported_authority_are_rejected(tmp_path):
    with SQLiteEventStore(tmp_path / "authority.sqlite") as db:
        clock = TimeEngine(db)
        g = create_session(db, clock)
        try:
            before = db.verify(WORLD).to_dict()
            event = DomainEvent("PlayerQuestRewardClaimed", "carlos",
                "forged payout", 0, {"quest_id": Q})
            with pytest.raises(InvalidEvent):
                db.append(WORLD, "forged-quest", db.load(WORLD).revision, [event])
            with pytest.raises(InvalidEvent):
                db.append(WORLD, "fake-authority", db.load(WORLD).revision,
                          [event], rpg_authorized=True)
            assert db.verify(WORLD).to_dict() == before
        finally:
            clock.close_session(WORLD)


def test_claim_cannot_duplicate_even_with_fresh_command(tmp_path):
    with SQLiteEventStore(tmp_path / "duplicate.sqlite") as db:
        clock = TimeEngine(db)
        g = create_session(db, clock)
        try:
            execute(g, f"accept {Q}", 1)
            _at_real_market(g)
            _real_purchase(g)
            execute(g, f"claim {Q}", 20)
            original = db.verify(WORLD).to_dict()
            with pytest.raises((InvalidEvent, DuplicateCommand)):
                execute(g, f"claim {Q}", 21)
            with pytest.raises((InvalidEvent, DuplicateCommand)):
                execute(g, f"claim {Q}", 20)
            assert db.verify(WORLD).to_dict() == original
        finally:
            clock.close_session(WORLD)


def test_stale_revision_cannot_accept_and_quest_reads_are_pure(tmp_path):
    with SQLiteEventStore(tmp_path / "stale.sqlite") as db:
        clock = TimeEngine(db)
        g = create_session(db, clock)
        try:
            old = db.load(WORLD).revision
            execute(g, f"accept {Q}", 1)
            frozen = db.verify(WORLD).to_dict()
            with pytest.raises(RevisionConflict):
                g.claim_quest(Q, command_id="stale", expected_revision=old)
            for _ in range(3):
                execute(g, "quests", 2)
                execute(g, "handoff", 3)
            assert db.verify(WORLD).to_dict() == frozen
        finally:
            clock.close_session(WORLD)


def test_travel_blocks_acceptance_and_market_remoteness_blocks_reward(tmp_path):
    with SQLiteEventStore(tmp_path / "local.sqlite") as db:
        clock = TimeEngine(db)
        g = create_session(db, clock)
        try:
            execute(g, "move home-market", 1)
            before = db.verify(WORLD).to_dict()
            with pytest.raises(InvalidEvent):
                execute(g, f"accept {Q}", 2)
            assert db.verify(WORLD).to_dict() == before
        finally:
            clock.close_session(WORLD)
