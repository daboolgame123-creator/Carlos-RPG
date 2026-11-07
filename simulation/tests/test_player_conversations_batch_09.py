"""PLAY-09: true player speech and recorded NPC reaction, no other knowledge."""
from __future__ import annotations

import json

import pytest

from carlos_sim import PlayerGateway
from carlos_sim.player_gateway import PlayerCommandResult
from carlos_sim.player_handoff import player_handoff
from carlos_sim.resumable_play import ResumableTestSession
from carlos_sim.store import DuplicateCommand, InvalidEvent, IntegrityError
from test_player_market_batch_05 import (
    WORLD, PLAYER, village, setup_living_market_world, living_player_gateway,
)


def say(db, gw, who="basim", kind="greeting", text="Hello", cid="hello"):
    return gw.interact(who, kind=kind, text=text, command_id=cid,
                       expected_revision=db.load(WORLD).revision)


def test_empty_conversations_and_bad_limits_do_not_write(tmp_path):
    db, clock, gw = village(tmp_path)
    with db:
        before = db.load(WORLD).to_dict()
        assert gw.conversations().status == "conversations"
        assert gw.conversations().details == {"total": 0, "recent": ()}
        assert player_handoff(gw)["player_conversations"] == {"total": 0, "recent": ()}
        for invalid in (0, -1, 21, True, 2.0, "10", None):
            with pytest.raises(ValueError, match="limit"):
                gw.conversations(invalid)
        assert db.verify(WORLD).to_dict() == before


def test_basim_and_salma_record_only_actual_words_and_reactions(tmp_path):
    db, clock, gw = village(tmp_path)
    with db:
        first = say(db, gw)
        second = say(db, gw, "salma", "request_help", "Can you help?",
                     "request-salma")
        assert first.details["reaction"] == "acknowledged"
        assert second.details["reaction"] == "considered"
        before = db.load(WORLD).to_dict()
        convo = gw.conversations().details
        assert convo == {"total": 2, "recent": (
            {"recipient_id": "salma", "kind": "request_help",
             "text": "Can you help?", "reaction": "considered", "spoken_at": 0},
            {"recipient_id": "basim", "kind": "greeting",
             "text": "Hello", "reaction": "acknowledged", "spoken_at": 0},
        )}
        handoff = player_handoff(gw)
        assert handoff["player_conversations"] == convo
        raw = json.dumps(handoff)
        for secret in ('"relations"', '"trust_before"', '"trust_after"',
                       '"npcs"', '"goals"', '"beliefs"', '"social_messages"'):
            assert secret not in raw
        assert db.verify(WORLD).to_dict() == before


def test_adel_threat_and_salma_greeting_are_distinct_not_fake_dialogue(tmp_path):
    db, clock, gw = village(tmp_path)
    with db:
        say(db, gw, "adel", "threat", "Move away", "adel-threat")
        say(db, gw, "salma", "greeting", "Good morning", "salma-hi")
        rows = gw.conversations().details["recent"]
        assert [x["recipient_id"] for x in rows] == ["salma", "adel"]
        assert rows[1]["reaction"] == "alarmed"
        assert rows[1]["text"] == "Move away"
        assert rows[0]["reaction"] == "acknowledged"
        assert "reply" not in rows[0]


def test_remote_nora_huda_omar_layla_cannot_create_private_exchange(tmp_path):
    db, clock, gw = village(tmp_path)
    with db:
        before = db.load(WORLD).to_dict()
        for who in ("nora", "huda", "omar", "layla"):
            with pytest.raises(InvalidEvent, match="present locally"):
                say(db, gw, who, cid="not-here-" + who)
        assert gw.conversations().details["total"] == 0
        assert db.verify(WORLD).to_dict() == before


def test_duplicates_and_invalid_speech_never_become_history(tmp_path):
    db, clock, gw = village(tmp_path)
    with db:
        say(db, gw)
        original = gw.conversations().details
        with pytest.raises(DuplicateCommand):
            say(db, gw)
        # Same social act at identical logical tick is disallowed even
        # with a different command ID; no trust-farming.
        with pytest.raises(InvalidEvent, match="duplicate social act"):
            say(db, gw, cid="try-again")
        with pytest.raises(ValueError):
            say(db, gw, "salma", "unknown", "X", "bad-kind")
        assert gw.conversations().details == original
        assert db.verify(WORLD).to_dict() == db.load(WORLD).to_dict()


def test_player_identity_is_bound_and_does_not_reveal_npc_messages(tmp_path):
    db, clock, gw = village(tmp_path)
    with db:
        say(db, gw)
        wrong = PlayerGateway(db, clock, world_id=WORLD, player_id="salma")
        with pytest.raises(PermissionError):
            wrong.conversations()
        assert gw.conversations().details["total"] == 1


def test_player_talk_history_survives_travel_without_remote_sight(tmp_path):
    db, clock, gw = village(tmp_path)
    with db:
        say(db, gw, "salma", "greeting", "Hello Salma", "market")
        remembered = gw.conversations().details
        gw.move("square-woods", command_id="away", expected_revision=db.load(WORLD).revision)
        assert gw.inspect().status == "traveling"
        assert gw.conversations().details == remembered
        assert player_handoff(gw)["player_conversations"] == remembered
        with pytest.raises(ValueError, match="travelling"):
            say(db, gw, "salma", cid="travel-chat")
        gw.wait(50, command_id="arrive", expected_revision=db.load(WORLD).revision)
        assert gw.conversations().details == remembered
        assert db.verify(WORLD).to_dict() == db.load(WORLD).to_dict()


def test_conversation_limit_but_correct_total_for_three_messages(tmp_path):
    db, clock, gw = village(tmp_path)
    with db:
        say(db, gw, "basim", "greeting", "Hi", "first")
        say(db, gw, "basim", "offer_help", "Want help?", "second")
        say(db, gw, "salma", "greeting", "Hello", "third")
        data = gw.conversations(limit=1).details
        assert data["total"] == 3
        assert data["recent"] == ({"recipient_id": "salma", "kind": "greeting",
                                    "text": "Hello", "reaction": "acknowledged",
                                    "spoken_at": 0},)
        assert len(gw.conversations(limit=2).details["recent"]) == 2
        assert len(gw.conversations().details["recent"]) == 3


def test_handoff_denies_mixed_conversation_revision(tmp_path, monkeypatch):
    db, clock, gw = village(tmp_path)
    with db:
        original = gw.conversations

        def changed(limit=20):
            row = original(limit)
            return PlayerCommandResult(row.world_id, row.time, row.revision + 1,
                                       row.status, row.details)

        monkeypatch.setattr(gw, "conversations", changed)
        before = db.load(WORLD).to_dict()
        with pytest.raises(RuntimeError, match="changed"):
            player_handoff(gw)
        assert db.verify(WORLD).to_dict() == before


def test_corrupted_social_event_is_rejected_not_recalled(tmp_path):
    db, clock, gw = village(tmp_path)
    with db:
        say(db, gw)
        seq, payload = db.db.execute(
            "SELECT seq,payload FROM events WHERE world_id=? AND command_id=? "
            "AND payload LIKE '%SocialMessageSent%'",
            (WORLD, "social:player-hello")).fetchone()
        tampered = json.loads(payload)
        tampered["data"]["text"] = "A lie"
        db.db.execute("UPDATE events SET payload=? WHERE world_id=? AND seq=?",
                      (json.dumps(tampered), WORLD, seq))
        with pytest.raises(IntegrityError):
            gw.conversations()
        db.db.execute("UPDATE events SET payload=? WHERE world_id=? AND seq=?",
                      (payload, WORLD, seq))
        assert gw.conversations().details["recent"][0]["text"] == "Hello"


def test_snapshot_and_resumable_reopen_keep_social_history(tmp_path):
    path = tmp_path / "conversations.sqlite"
    with ResumableTestSession.create(
        path, WORLD, PLAYER, setup_living_market_world, disposable_test=True
    ) as session:
        session.bind_gateway(living_player_gateway(session.store, session.clock))
        say(session.store, session.gateway, "basim", "greeting", "Hello", "hello")
        saved = session.gateway.conversations().details
        view = session.handoff()
        session.store.snapshot(WORLD)
        canonical = session.store.verify(WORLD).to_dict()
    with ResumableTestSession.resume(
        path, WORLD, PLAYER, disposable_test=True
    ) as session:
        session.bind_gateway(living_player_gateway(session.store, session.clock))
        assert session.gateway.conversations().details == saved
        assert session.handoff() == view
        assert session.store.verify(WORLD).to_dict() == canonical


def test_temporary_cli_conversations_and_handoff():
    from test_play_living_village_batch_02 import _cli, _json_handoffs
    stdout = _cli(
        "conversations\ntalk basim greeting Hi\ntalk salma request_help Help\n"
        "conversations\nhandoff\nquit\n"
    ).stdout
    views = _json_handoffs(stdout)
    assert len(views) == 1
    assert "total: 0" in stdout and "total: 2" in stdout
    assert views[0]["player_conversations"]["total"] == 2
    assert views[0]["player_conversations"]["recent"][0]["recipient_id"] == "salma"


def test_resumable_cli_conversations_are_checkpoint_neutral(tmp_path):
    from test_play_living_resumable_batch_03 import (
        run_cli, saved_states, backups_list,
    )
    db_path, backups = tmp_path / "world.sqlite", tmp_path / "backup"
    backups.mkdir()
    first = run_cli(
        "conversations\nid speech1 talk basim greeting Hello\nconversations\n"
        "handoff\nquit\n",
        db_path, backups, "--new", extra=("--disposable-test",),
    )
    views = saved_states(first.stdout)
    assert len(views) == 1
    assert views[0]["player_conversations"]["total"] == 1
    n = len(backups_list(backups))
    assert n == 2
    second = run_cli(
        "conversations\nhandoff\nquit\n",
        db_path, backups, "--resume", extra=("--disposable-test",),
    )
    assert "total: 1" in second.stdout
    assert saved_states(second.stdout) == views
    assert len(backups_list(backups)) == n
