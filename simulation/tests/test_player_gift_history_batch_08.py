"""PLAY-08: only verified owned gifts appear in bounded player history."""
from __future__ import annotations

import json

import pytest

from carlos_sim import PlayerGateway
from carlos_sim.player_gateway import PlayerCommandResult
from carlos_sim.player_handoff import player_handoff
from carlos_sim.resumable_play import ResumableTestSession
from carlos_sim.store import DuplicateCommand, IntegrityError
from test_player_market_batch_05 import (
    WORLD, PLAYER, village, purchase, assert_finite_market,
    setup_living_market_world, living_player_gateway,
)


def donate(db, gw, cid="gift-one", *, quantity=1):
    return gw.give("salma", "bread", quantity, command_id=cid,
                   expected_revision=db.load(WORLD).revision)


def test_empty_gifts_and_bounds_are_read_only(tmp_path):
    db, clock, gw = village(tmp_path)
    with db:
        before = db.load(WORLD).to_dict()
        assert gw.gifts().status == "gifts"
        assert gw.gifts().details == {"total": 0, "recent": ()}
        assert player_handoff(gw)["player_gifts"] == {"total": 0, "recent": ()}
        for invalid in (0, -1, 21, True, "2", None, 2.0):
            with pytest.raises(ValueError, match="limit"):
                gw.gifts(invalid)
        assert db.load(WORLD).to_dict() == before
        assert db.verify(WORLD).to_dict() == before


def test_only_delivered_gift_is_visible_without_private_npc_details(tmp_path):
    db, clock, gw = village(tmp_path)
    with db:
        purchase(db, gw, "bought-two", qty=2)
        assert gw.gifts().details["total"] == 0
        donate(db, gw)
        before = db.load(WORLD).to_dict()
        receipt = {"recipient_id": "salma", "resource": "bread",
                   "quantity": 1, "delivered_at": 0}
        assert gw.gifts().details == {"total": 1, "recent": (receipt,)}
        handoff = player_handoff(gw)
        assert handoff["player_gifts"] == {"total": 1, "recent": (receipt,)}
        payload = json.dumps(handoff)
        for private in ('"npcs"', '"needs"', '"relations"', '"gift_authorized"',
                        '"resources"', '"coin_copper": 4', '"market_trades"'):
            assert private not in payload
        assert db.load(WORLD).to_dict() == before
        assert_finite_market(db, player_bread=1, player_copper=6,
                             salma_bread=2, salma_copper=4)


def test_multiple_same_tick_gifts_are_counted_not_deduplicated(tmp_path):
    db, clock, gw = village(tmp_path)
    with db:
        purchase(db, gw, "two-loaves", qty=2)
        donate(db, gw, "first")
        donate(db, gw, "second")
        receipts = gw.gifts()
        assert receipts.details["total"] == 2
        assert len(receipts.details["recent"]) == 2
        assert receipts.details["recent"][0] == receipts.details["recent"][1]
        assert len(gw.gifts(limit=1).details["recent"]) == 1
        assert gw.gifts(limit=1).details["total"] == 2
        assert_finite_market(db, player_bread=0, player_copper=6,
                             salma_bread=3, salma_copper=4)


def test_rejections_duplicates_and_travel_do_not_add_gifts(tmp_path):
    db, clock, gw = village(tmp_path)
    with db:
        purchase(db, gw, "one-loaf")
        donate(db, gw, "successful")
        history = gw.gifts().details
        with pytest.raises(DuplicateCommand):
            donate(db, gw, "successful")
        with pytest.raises(Exception):
            donate(db, gw, "no-stock")
        assert gw.gifts().details == history
        gw.move("square-woods", command_id="depart",
                expected_revision=db.load(WORLD).revision)
        with pytest.raises(ValueError, match="travelling"):
            donate(db, gw, "in-transit")
        assert gw.gifts().details == history
        assert db.verify(WORLD).to_dict() == db.load(WORLD).to_dict()


def test_wrong_player_gateway_cannot_read_gifts(tmp_path):
    db, clock, gw = village(tmp_path)
    with db:
        purchase(db, gw, "player-buy")
        donate(db, gw)
        wrong = PlayerGateway(db, clock, world_id=WORLD, player_id="nora")
        with pytest.raises(PermissionError):
            wrong.gifts()
        assert gw.gifts().details["total"] == 1


def test_handoff_refuses_stale_gift_history(tmp_path, monkeypatch):
    db, clock, gw = village(tmp_path)
    with db:
        original = gw.gifts

        def stale(limit=20):
            row = original(limit)
            return PlayerCommandResult(row.world_id, row.time,
                                       row.revision + 1, row.status, row.details)

        monkeypatch.setattr(gw, "gifts", stale)
        before = db.load(WORLD).to_dict()
        with pytest.raises(RuntimeError, match="changed"):
            player_handoff(gw)
        assert db.verify(WORLD).to_dict() == before


def test_tampered_event_cannot_supply_a_fake_receipt(tmp_path):
    db, clock, gw = village(tmp_path)
    with db:
        purchase(db, gw, "bought")
        donate(db, gw)
        target = db.db.execute(
            "SELECT seq,payload FROM events WHERE world_id=? "
            "AND command_id=?", (WORLD, "player-gift:gift-one")).fetchone()
        assert target is not None
        seq, original = target
        fake = json.loads(original)
        fake["data"]["quantity"] = 999
        db.db.execute("UPDATE events SET payload=? WHERE world_id=? AND seq=?",
                      (json.dumps(fake), WORLD, seq))
        with pytest.raises(IntegrityError):
            gw.gifts()
        db.db.execute("UPDATE events SET payload=? WHERE world_id=? AND seq=?",
                      (original, WORLD, seq))
        assert gw.gifts().details["recent"][0]["quantity"] == 1


def test_gifts_survive_sqlite_snapshot_and_real_reopen(tmp_path):
    path = tmp_path / "persist-gifts.sqlite"
    with ResumableTestSession.create(
        path, WORLD, PLAYER, setup_living_market_world, disposable_test=True
    ) as session:
        session.bind_gateway(living_player_gateway(session.store, session.clock))
        purchase(session.store, session.gateway, "persist-buy", qty=2)
        donate(session.store, session.gateway, "persist-gift")
        current = session.gateway.gifts().details
        handoff = session.handoff()
        session.store.snapshot(WORLD)
        original = session.store.verify(WORLD).to_dict()
    with ResumableTestSession.resume(
        path, WORLD, PLAYER, disposable_test=True
    ) as session:
        session.bind_gateway(living_player_gateway(session.store, session.clock))
        assert session.gateway.gifts().details == current
        assert session.handoff() == handoff
        assert session.store.verify(WORLD).to_dict() == original
        assert_finite_market(session.store, player_bread=1, player_copper=6,
                             salma_bread=2, salma_copper=4)


def test_temporary_cli_shows_gifts_and_handoff():
    from test_play_living_village_batch_02 import _cli, _json_handoffs
    out = _cli(
        "gifts\nbuy salma-bread 1 2\ngive salma bread 1\ngifts\nhandoff\nquit\n"
    ).stdout
    views = _json_handoffs(out)
    assert "total: 0" in out and "total: 1" in out
    assert len(views) == 1
    assert views[0]["player_gifts"]["total"] == 1
    assert views[0]["player_gifts"]["recent"][0]["recipient_id"] == "salma"


def test_resumable_cli_gifts_do_not_create_new_checkpoints(tmp_path):
    from test_play_living_resumable_batch_03 import (
        run_cli, saved_states, backups_list,
    )
    dbfile, backups = tmp_path / "saved.sqlite", tmp_path / "backups"
    backups.mkdir()
    start = run_cli(
        "id buy1 buy salma-bread 2 2\n"
        "id gift1 give salma bread 1\ngifts\nhandoff\nquit\n",
        dbfile, backups, "--new", extra=("--disposable-test",),
    )
    frozen = saved_states(start.stdout)
    assert len(frozen) == 1
    assert frozen[0]["player_gifts"]["total"] == 1
    checkpoints = len(backups_list(backups))
    assert checkpoints == 3
    resume = run_cli(
        "gifts\nhandoff\nquit\n",
        dbfile, backups, "--resume", extra=("--disposable-test",),
    )
    assert "total: 1" in resume.stdout
    assert saved_states(resume.stdout) == frozen
    assert len(backups_list(backups)) == checkpoints
