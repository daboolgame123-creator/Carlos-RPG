"""PLAY-07: true resource conservation when Carlos hands an NPC a gift.

The independent NPC may refuse based on its existing social response.
This prototype does NOT infer gratitude, hunger relief, medical recovery,
experience, equipment or legal possession.
"""
from __future__ import annotations

import json

import pytest

from carlos_sim import (
    DomainEvent, PlayerGateway, SQLiteEventStore, TimeEngine, WorldState,
)
from carlos_sim.domain import apply_event
from carlos_sim.resumable_play import ResumableTestSession
from carlos_sim.store import InvalidEvent, DuplicateCommand, RevisionConflict, IntegrityError
from test_player_market_batch_05 import (
    village, purchase, assert_finite_market, WORLD, PLAYER,
    setup_living_market_world, living_player_gateway,
)


def handoff(db, gw, recipient="salma", resource="bread", qty=1, cid="first-gift"):
    return gw.give(recipient, resource, qty, command_id=cid,
                   expected_revision=db.load(WORLD).revision)


def test_carlos_pays_for_bread_then_gives_back_real_loaf(tmp_path):
    db, clock, gw = village(tmp_path)
    with db:
        purchase(db, gw, "buy-one")
        before = db.load(WORLD)
        trust = before.relations.get("salma", {}).get(PLAYER, 0)
        gift = handoff(db, gw)
        assert gift.status == "gifted"
        assert gift.details == {"recipient_id": "salma", "resource": "bread",
                                "quantity": 1}
        assert gift.time == 0
        assert_finite_market(db, player_bread=0, player_copper=8,
                             salma_bread=3, salma_copper=2)
        now = db.load(WORLD)
        assert now.relations.get("salma", {}).get(PLAYER, 0) == trust
        assert now.npcs["salma"]["needs"] == before.npcs["salma"]["needs"]
        assert now.rpg_profiles[PLAYER] == before.rpg_profiles[PLAYER]
        assert now.market_offers == before.market_offers
        provenance = db.db.execute(
            "SELECT gift_authorized FROM commands WHERE world_id=? AND command_id=?",
            (WORLD, "player-gift:first-gift")).fetchone()
        assert provenance == (1,)


def test_gift_without_purchased_stock_or_initialized_counterpart_rejected(tmp_path):
    db, clock, gw = village(tmp_path)
    with db:
        before = db.load(WORLD).to_dict()
        with pytest.raises(InvalidEvent, match="initialized balances"):
            handoff(db, gw, "basim", "bread")
        with pytest.raises(InvalidEvent, match="stock"):
            handoff(db, gw, "salma", "bread")
        assert db.load(WORLD).to_dict() == before
        assert db.verify(WORLD).to_dict() == before


@pytest.mark.parametrize("recipient,resource,quantity", [
    ("carlos", "bread", 1), ("nora", "bread", 1),
    ("huda", "bread", 1), ("omar", "bread", 1),
    ("missing-npc", "bread", 1), ("salma", "labor_units", 1),
    ("salma", "wild_food", 1), ("salma", "bread", 0),
    ("salma", "bread", -1), ("salma", "bread", 1001),
    ("salma", "bread", 2), ("salma", "bread", True),
    ("salma", "bread", "1"),
])
def test_invalid_npc_place_resource_quantity_or_insufficient_stock_atomic(
        tmp_path, recipient, resource, quantity):
    db, clock, gw = village(tmp_path)
    with db:
        purchase(db, gw, "buy-one")
        before = db.load(WORLD).to_dict()
        with pytest.raises((ValueError, InvalidEvent)):
            handoff(db, gw, recipient, resource, quantity)
        assert db.load(WORLD).to_dict() == before
        assert db.verify(WORLD).to_dict() == before


def test_untrusted_or_impersonated_gift_event_is_denied(tmp_path):
    db, clock, gw = village(tmp_path)
    with db:
        purchase(db, gw, "buy-one")
        prior = db.load(WORLD)
        event = DomainEvent("PlayerGiftDelivered", PLAYER, "forged", prior.time, {
            "recipient_id": "salma", "resource": "bread", "quantity": 1})
        with pytest.raises(InvalidEvent, match="dedicated capability"):
            db.append(WORLD, "forged-no-capability", prior.revision, [event])
        with pytest.raises(InvalidEvent, match="actual player"):
            db.append(WORLD, "npc-pretends-to-gift", prior.revision, [
                DomainEvent("PlayerGiftDelivered", "basim", "forged", prior.time, {
                    "recipient_id": "salma", "resource": "bread", "quantity": 1})
            ], gift_authorized=True)
        impostor = PlayerGateway(db, clock, world_id=WORLD, player_id="basim")
        with pytest.raises(PermissionError):
            impostor.give("salma", "bread", 1,
                          command_id="impersonation", expected_revision=prior.revision)
        assert db.verify(WORLD).to_dict() == prior.to_dict()


def test_real_npc_rejection_does_not_confiscate_goods_or_change_trust(tmp_path):
    db, clock, gw = village(tmp_path)
    with db:
        purchase(db, gw, "buy-one")
        modified = db.load(WORLD).to_dict()
        modified["relations"]["salma"] = {PLAYER: -25}
        state = WorldState.from_dict(modified)
        event = DomainEvent("PlayerGiftDelivered", PLAYER, "gifting", state.time, {
            "recipient_id": "salma", "resource": "bread", "quantity": 1})
        with pytest.raises(ValueError, match="did not accept"):
            apply_event(state, event, gift_authorized=True)
        assert state.to_dict() == modified
        assert db.verify(WORLD).to_dict() == db.load(WORLD).to_dict()


def test_gift_after_arrival_or_during_travel_is_not_remote_delivery(tmp_path):
    db, clock, gw = village(tmp_path)
    with db:
        purchase(db, gw, "buy-one")
        gw.move("square-woods", command_id="depart",
                expected_revision=db.load(WORLD).revision)
        transit = db.load(WORLD).to_dict()
        with pytest.raises(ValueError, match="travelling"):
            handoff(db, gw, cid="travel-gift")
        assert db.load(WORLD).to_dict() == transit
        gw.wait(50, command_id="arrive",
                expected_revision=db.load(WORLD).revision)
        current = db.load(WORLD).to_dict()
        with pytest.raises(InvalidEvent, match="co-located"):
            handoff(db, gw, cid="remote-gift")
        assert db.load(WORLD).to_dict() == current


def test_reusing_same_command_or_stale_revision_cannot_double_gift(tmp_path):
    db, clock, gw = village(tmp_path)
    with db:
        purchase(db, gw, "buy-two", qty=2)
        rev = db.load(WORLD).revision
        handoff(db, gw, qty=1, cid="once")
        after = db.load(WORLD).to_dict()
        with pytest.raises(DuplicateCommand):
            handoff(db, gw, qty=1, cid="once")
        with pytest.raises(RevisionConflict):
            gw.give("salma", "bread", 1, command_id="stale",
                    expected_revision=rev)
        assert db.load(WORLD).to_dict() == after
        assert_finite_market(db, player_bread=1, player_copper=6,
                             salma_bread=2, salma_copper=4)


def test_carlos_gift_replay_is_provenanced_and_corrupted_capability_fails(tmp_path):
    db, clock, gw = village(tmp_path)
    with db:
        purchase(db, gw, "buy-two", qty=2)
        handoff(db, gw, qty=1, cid="verified")
        pristine = db.load(WORLD).to_dict()
        assert db.load(WORLD, use_snapshot=False).to_dict() == pristine
        db.db.execute(
            "UPDATE commands SET gift_authorized=0 WHERE world_id=? AND command_id=?",
            (WORLD, "player-gift:verified"))
        with pytest.raises(IntegrityError):
            db.verify(WORLD)
        db.db.execute(
            "UPDATE commands SET gift_authorized=1 WHERE world_id=? AND command_id=?",
            (WORLD, "player-gift:verified"))
        assert db.verify(WORLD).to_dict() == pristine


def test_player_gift_survives_sqlite_snapshot_and_reopen(tmp_path):
    path = tmp_path / "gift.sqlite"
    with ResumableTestSession.create(
        path, WORLD, PLAYER, setup_living_market_world, disposable_test=True
    ) as session:
        session.bind_gateway(living_player_gateway(session.store, session.clock))
        purchase(session.store, session.gateway, "persist-buy", qty=2)
        handoff(session.store, session.gateway, qty=1, cid="persist-gift")
        view = session.handoff()
        session.store.snapshot(WORLD)
        frozen = session.store.verify(WORLD).to_dict()
    with ResumableTestSession.resume(
        path, WORLD, PLAYER, disposable_test=True
    ) as session:
        session.bind_gateway(living_player_gateway(session.store, session.clock))
        assert session.handoff() == view
        assert session.store.verify(WORLD).to_dict() == frozen
        assert_finite_market(session.store, player_bread=1, player_copper=6,
                             salma_bread=2, salma_copper=4)


def test_temporary_cli_gives_only_real_owned_goods():
    from test_play_living_village_batch_02 import _cli, _json_handoffs
    out = _cli(
        "buy salma-bread 1 2\ngive salma bread 1\nsupplies\nhandoff\nquit\n"
    ).stdout
    assert "gifted" in out
    assert "'recipient_id': 'salma'" in out or "recipient_id: salma" in out
    views = _json_handoffs(out)
    assert len(views) == 1
    assert views[0]["player_supplies"]["balances"]["bread"] == 0
    assert views[0]["player_supplies"]["balances"]["coin_copper"] == 8


def test_resumable_cli_reopen_does_not_duplicate_gift(tmp_path):
    from test_play_living_resumable_batch_03 import (
        run_cli, saved_states, backups_list,
    )
    dbfile, backups = tmp_path / "world.sqlite", tmp_path / "backup"
    backups.mkdir()
    first = run_cli(
        "id purchase buy salma-bread 2 2\nid donate give salma bread 1\nhandoff\nquit\n",
        dbfile, backups, "--new", extra=("--disposable-test",),
    )
    saved = saved_states(first.stdout)
    assert len(saved) == 1
    assert saved[0]["player_supplies"]["balances"]["bread"] == 1
    count = len(backups_list(backups))
    assert count == 3
    again = run_cli(
        "id donate give salma bread 1\nhandoff\nquit\n",
        dbfile, backups, "--resume", extra=("--disposable-test",),
    )
    assert "Rejected:" in again.stdout
    assert saved_states(again.stdout) == saved
    assert len(backups_list(backups)) == count
