"""PLAY-10: player asks, NPC independently considers, only grounded rumors travel."""
from __future__ import annotations

import json

import pytest

from carlos_sim import DomainEvent, PlayerGateway
from carlos_sim.player_handoff import player_handoff
from carlos_sim.resumable_play import ResumableTestSession
from carlos_sim.store import DuplicateCommand, InvalidEvent, IntegrityError, RevisionConflict
from test_player_market_batch_05 import (
    WORLD, PLAYER, village, setup_living_market_world, living_player_gateway
)


def ask(db, gw, who="basim", site="square", cid="question"):
    return gw.ask_food(who, site, command_id=cid,
                       expected_revision=db.load(WORLD).revision)


def test_basim_knows_only_what_he_directly_observed_at_square(tmp_path):
    db, clock, gw = village(tmp_path)
    with db:
        start = db.load(WORLD)
        assert start.resources["square"]["wild_food"] == 2
        assert start.resources["woods"]["wild_food"] == 4
        assert start.npcs["basim"]["beliefs"]["food:square"]["text"] == \
            "food-state:present; observed_at=0"
        assert "food:woods" not in start.npcs["basim"]["beliefs"]
        received = ask(db, gw)
        assert received.status == "asked_food"
        assert received.details == {
            "recipient_id": "basim", "site_id": "square",
            "reaction": "considered", "shared": True,
            "claim": {"key": "food:square",
                      "text": "food-state:present; observed_at=0",
                      "status": "unverified"}}
        heard = gw.recall().details["hearsay"]
        assert len(heard) == 1
        assert heard[0]["speaker_id"] == "basim"
        assert heard[0]["status"] == "unverified"
        assert heard[0]["key"] == "food:square"
        assert db.load(WORLD).resources == start.resources
        assert db.verify(WORLD).to_dict() == db.load(WORLD).to_dict()


def test_single_atomic_command_records_npc_response_and_one_claim(tmp_path):
    db, clock, gw = village(tmp_path)
    with db:
        before = db.load(WORLD)
        result = ask(db, gw, cid="atomic")
        assert result.revision == before.revision + 3
        types = [json.loads(row[0])["event_type"] for row in db.db.execute(
            "SELECT payload FROM events WHERE world_id=? AND command_id=? ORDER BY seq",
            (WORLD, "social:player-ask-food-atomic"))]
        assert types == [
            "SocialMessageSent", "SocialMessageReceived", "PlayerHearsayReceived"]
        assert gw.conversations().details["recent"][0]["kind"] == "request_help"
        assert gw.conversations().details["recent"][0]["text"] == \
            "Have you seen food at square?"
        assert player_handoff(gw)["player_memory"]["hearsay"][0]["claim"] == \
            "food-state:present; observed_at=0"


def test_salma_knows_no_food_and_basim_does_not_know_remote_woods(tmp_path):
    db, clock, gw = village(tmp_path)
    with db:
        unknowing = ask(db, gw, "salma", "square", "salma-unknown")
        remote = ask(db, gw, "basim", "woods", "basim-unknown")
        assert unknowing.details == {
            "recipient_id": "salma", "site_id": "square",
            "reaction": "considered", "shared": False}
        assert remote.details == {
            "recipient_id": "basim", "site_id": "woods",
            "reaction": "considered", "shared": False}
        assert gw.recall().details["hearsay"] == ()
        assert db.verify(WORLD).to_dict() == db.load(WORLD).to_dict()


def test_adel_guard_does_not_invent_a_woods_sighting(tmp_path):
    db, clock, gw = village(tmp_path)
    with db:
        result = ask(db, gw, "adel", "woods", "guard-asked")
        assert result.details["shared"] is False
        assert "claim" not in result.details
        assert gw.recall().details["hearsay"] == ()


def test_npc_with_real_knowledge_refuses_after_threat(tmp_path):
    db, clock, gw = village(tmp_path)
    with db:
        threatened = gw.interact(
            "basim", kind="threat", text="Do not speak",
            command_id="threat", expected_revision=db.load(WORLD).revision)
        assert threatened.details["reaction"] == "alarmed"
        result = ask(db, gw, "basim", "square", "after-threat")
        assert result.details["reaction"] == "refused"
        assert result.details["shared"] is False
        assert "claim" not in result.details
        assert gw.recall().details["hearsay"] == ()
        assert db.verify(WORLD).to_dict() == db.load(WORLD).to_dict()


@pytest.mark.parametrize("npc,site", [
    ("nora", "square"), ("huda", "square"), ("omar", "woods"),
    ("layla", "woods"),
])
def test_distant_characters_cannot_share_knowledge_remotely(tmp_path, npc, site):
    db, clock, gw = village(tmp_path)
    with db:
        before = db.load(WORLD).to_dict()
        with pytest.raises(InvalidEvent, match="present locally"):
            ask(db, gw, npc, site, "remote-"+npc)
        assert db.load(WORLD).to_dict() == before
        assert gw.recall().details["hearsay"] == ()
        assert db.verify(WORLD).to_dict() == before


@pytest.mark.parametrize("npc,site", [
    ("missing", "square"), ("basim", "somewhere"),
    ("basim", ""), ("basim", "x"*81),
    ("basim", None), ("basim", 4),
])
def test_invalid_player_request_does_not_create_speech(tmp_path, npc, site):
    db, clock, gw = village(tmp_path)
    with db:
        before = db.load(WORLD).to_dict()
        with pytest.raises(ValueError):
            ask(db, gw, npc, site, "bad-args")
        assert db.verify(WORLD).to_dict() == before


def test_duplicate_command_and_same_tick_request_spam_rejected(tmp_path):
    db, clock, gw = village(tmp_path)
    with db:
        ask(db, gw, cid="first")
        first = db.load(WORLD).to_dict()
        with pytest.raises(DuplicateCommand):
            ask(db, gw, cid="first")
        with pytest.raises(InvalidEvent, match="duplicate social act"):
            ask(db, gw, cid="second")
        assert db.load(WORLD).to_dict() == first
        assert len(gw.recall().details["hearsay"]) == 1


def test_stale_revision_rejected_before_npc_knows_request(tmp_path):
    db, clock, gw = village(tmp_path)
    with db:
        old = db.load(WORLD).revision
        ask(db, gw, cid="first")
        after = db.load(WORLD).to_dict()
        with pytest.raises(RevisionConflict):
            gw.ask_food("salma", "square", command_id="stale",
                        expected_revision=old)
        assert db.verify(WORLD).to_dict() == after


def test_forged_player_or_invalid_hearsay_not_committed(tmp_path):
    db, clock, gw = village(tmp_path)
    with db:
        bad = PlayerGateway(db, clock, world_id=WORLD, player_id="salma")
        with pytest.raises(PermissionError):
            bad.ask_food("basim", "square", command_id="fake",
                         expected_revision=db.load(WORLD).revision)
        current = db.load(WORLD)
        with pytest.raises(InvalidEvent):
            db.append(WORLD, "invented-food", current.revision, [
                DomainEvent("PlayerHearsayReceived", "salma", "forged", 0,
                    {"player_id": PLAYER, "key": "food:woods",
                     "text": "food-state:present; observed_at=0"})
            ], social_authorized=True)
        assert db.verify(WORLD).to_dict() == current.to_dict()


def test_travel_blocks_local_question_but_memory_remains(tmp_path):
    db, clock, gw = village(tmp_path)
    with db:
        ask(db, gw, cid="asked")
        prior = gw.recall().details["hearsay"]
        gw.move("square-woods", command_id="leave",
                expected_revision=db.load(WORLD).revision)
        with pytest.raises(ValueError, match="travelling"):
            ask(db, gw, cid="while-travelling")
        assert gw.recall().details["hearsay"] == prior
        gw.wait(50, command_id="reach", expected_revision=db.load(WORLD).revision)
        assert gw.recall().details["hearsay"] == prior
        assert db.verify(WORLD).to_dict() == db.load(WORLD).to_dict()


def test_snapshot_reopen_keeps_exact_earned_hearsay(tmp_path):
    path = tmp_path / "play10.sqlite"
    with ResumableTestSession.create(
        path, WORLD, PLAYER, setup_living_market_world, disposable_test=True
    ) as session:
        session.bind_gateway(living_player_gateway(session.store, session.clock))
        ask(session.store, session.gateway, cid="persistent")
        memory = session.gateway.recall().details
        history = session.gateway.conversations().details
        view = session.handoff()
        session.store.snapshot(WORLD)
        frozen = session.store.verify(WORLD).to_dict()
    with ResumableTestSession.resume(path, WORLD, PLAYER, disposable_test=True) as session:
        session.bind_gateway(living_player_gateway(session.store, session.clock))
        assert session.gateway.recall().details == memory
        assert session.gateway.conversations().details == history
        assert session.handoff() == view
        assert session.store.verify(WORLD).to_dict() == frozen


def test_tampered_hearsay_is_rejected_in_replay(tmp_path):
    db, clock, gw = village(tmp_path)
    with db:
        ask(db, gw, cid="original")
        rows = list(db.db.execute(
            "SELECT seq,payload FROM events WHERE world_id=? AND command_id=?",
            (WORLD, "social:player-ask-food-original")))
        target = next((seq, payload) for seq, payload in rows
                      if json.loads(payload)["event_type"] == "PlayerHearsayReceived")
        seq, original = target
        corrupt = json.loads(original)
        corrupt["data"]["text"] = "food-state:empty; observed_at=0"
        db.db.execute("UPDATE events SET payload=? WHERE world_id=? AND seq=?",
                      (json.dumps(corrupt), WORLD, seq))
        with pytest.raises(IntegrityError):
            db.verify(WORLD)
        db.db.execute("UPDATE events SET payload=? WHERE world_id=? AND seq=?",
                      (original, WORLD, seq))
        assert db.verify(WORLD).to_dict() == db.load(WORLD).to_dict()


def test_temporary_cli_asks_and_handoff_contains_only_verified_claim():
    from test_play_living_village_batch_02 import _cli, _json_handoffs
    out = _cli("askfood basim square\naskfood salma square\n"
               "remember\nconversations\nhandoff\nquit\n").stdout
    assert "asked_food" in out
    views = _json_handoffs(out)
    assert len(views) == 1
    assert len(views[0]["player_memory"]["hearsay"]) == 1
    assert views[0]["player_memory"]["hearsay"][0]["speaker_id"] == "basim"
    assert views[0]["player_conversations"]["total"] == 2


def test_resumable_cli_no_duplicate_answer_after_reopen(tmp_path):
    from test_play_living_resumable_batch_03 import run_cli, saved_states, backups_list
    dbpath, backups = tmp_path / "world.sqlite", tmp_path / "backups"
    backups.mkdir()
    first = run_cli(
        "id where1 askfood basim square\nremember\nhandoff\nquit\n",
        dbpath, backups, "--new", extra=("--disposable-test",))
    earlier = saved_states(first.stdout)
    assert len(earlier) == 1
    assert len(earlier[0]["player_memory"]["hearsay"]) == 1
    count = len(backups_list(backups))
    assert count == 2
    again = run_cli(
        "id where1 askfood basim square\nremember\nhandoff\nquit\n",
        dbpath, backups, "--resume", extra=("--disposable-test",))
    assert "Rejected:" in again.stdout
    assert saved_states(again.stdout) == earlier
    assert len(backups_list(backups)) == count
