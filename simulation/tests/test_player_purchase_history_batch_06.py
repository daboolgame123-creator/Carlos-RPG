"""PLAY-06: bounded player purchase receipts; no NPC market history leaks.

Purchases are projections of real settled events, not NPC intentions or new
RPG inventory. The original test world remains disposable and offline.
"""
from __future__ import annotations

import json

import pytest

from carlos_sim import DomainEvent, NPCMarketService, PlayerGateway, SQLiteEventStore, TimeEngine
from carlos_sim.player_gateway import PlayerCommandResult
from carlos_sim.player_handoff import player_handoff
from carlos_sim.resumable_play import ResumableTestSession
from carlos_sim.store import DuplicateCommand
from test_player_market_batch_05 import village, purchase, assert_finite_market
from test_player_market_batch_05 import WORLD, PLAYER, setup_living_market_world, living_player_gateway


def test_initial_history_is_empty_bounded_and_read_only(tmp_path):
    db, clock, gw = village(tmp_path)
    with db:
        before = db.load(WORLD).to_dict()
        receipts = gw.purchases()
        assert receipts.status == "purchases"
        assert receipts.details == {"total": 0, "recent": ()}
        handoff = player_handoff(gw)
        assert handoff["player_purchases"] == receipts.details
        assert '"market_trades"' not in json.dumps(handoff)
        assert '"stock_owner_id"' not in json.dumps(handoff)
        assert db.load(WORLD).to_dict() == before
        for invalid in (0, 21, -1, True, "2", None):
            with pytest.raises(ValueError, match="limit"):
                gw.purchases(invalid)
        assert db.verify(WORLD).to_dict() == before


def test_player_sees_only_his_settled_receipts_not_npc_transactions(tmp_path):
    db, clock, gw = village(tmp_path)
    with db:
        # Basim has real currency and a known zero stock; no NPC wealth
        # is inferred from his job or from Carlos's own wallet.
        current = db.load(WORLD)
        db.append(WORLD, "fund-basim-for-own-test-buy", current.revision, [
            DomainEvent("ResourceChanged", None, "trusted test-only stock",
                        current.time, {"owner_id": "basim", "resource": "bread",
                                       "previous": None, "current": 0,
                                       "source": "initialization"}),
            DomainEvent("ResourceChanged", None, "trusted test-only currency",
                        current.time, {"owner_id": "basim", "resource": "coin_copper",
                                       "previous": None, "current": 20,
                                       "source": "initialization"}),
        ], bootstrap=True)
        NPCMarketService(db, clock).buy(
            WORLD, "basim", "basim-private-receipt", "salma-bread", 1, 2,
            expected_revision=db.load(WORLD).revision)
        assert gw.purchases().details == {"total": 0, "recent": ()}
        result = purchase(db, gw, "my-own-purchase", qty=1)
        before = db.load(WORLD).to_dict()
        history = gw.purchases()
        assert history.revision == before["revision"]
        assert history.details["total"] == 1
        assert len(history.details["recent"]) == 1
        own = history.details["recent"][0]
        assert own == {
            "trade_id": result.details["trade_id"],
            "offer_id": "salma-bread", "seller_id": "salma",
            "site_id": "square", "resource": "bread", "quantity": 1,
            "unit_price": 2, "payment_resource": "coin_copper",
            "total_paid": 2, "executed_at": 0,
        }
        encoded = json.dumps(history.details)
        for private in ("basim", "basim-private-receipt",
                        "goods_source_before", "pay_target_after",
                        "stock_owner_id"):
            assert private not in encoded
        assert player_handoff(gw)["player_purchases"]["recent"] == (own,)
        assert db.load(WORLD).to_dict() == before
        assert db.verify(WORLD).to_dict() == before


def test_history_survives_travel_and_duplicate_rejects_without_extra_receipts(tmp_path):
    db, clock, gw = village(tmp_path)
    with db:
        purchase(db, gw, "one", qty=1)
        first = gw.purchases()
        assert first.details["total"] == 1
        with pytest.raises(DuplicateCommand):
            purchase(db, gw, "one", qty=1)
        assert gw.purchases().details == first.details
        gw.move("square-woods", command_id="leave-market",
                expected_revision=db.load(WORLD).revision)
        assert gw.inspect().status == "traveling"
        assert gw.offers().details["offers"] == ()
        assert gw.purchases().details == first.details
        before = db.load(WORLD).to_dict()
        gw.purchases(limit=1)
        assert db.load(WORLD).to_dict() == before
        gw.wait(50, command_id="reach-woods",
                expected_revision=db.load(WORLD).revision)
        assert gw.offers().details["offers"] == ()
        assert gw.purchases().details == first.details
        assert db.verify(WORLD).to_dict() == db.load(WORLD).to_dict()


def test_wrong_gateway_cannot_request_another_characters_purchases(tmp_path):
    db, clock, gw = village(tmp_path)
    with db:
        purchase(db, gw, "legitimate")
        before = db.load(WORLD).to_dict()
        forged = PlayerGateway(db, clock, world_id=WORLD, player_id="basim")
        with pytest.raises(PermissionError):
            forged.purchases()
        assert db.verify(WORLD).to_dict() == before


def test_handoff_refuses_mixed_history_revision(tmp_path, monkeypatch):
    db, clock, gw = village(tmp_path)
    with db:
        original = gw.purchases

        def stale(limit=20):
            row = original(limit)
            return PlayerCommandResult(row.world_id, row.time,
                                       row.revision + 1, row.status, row.details)

        monkeypatch.setattr(gw, "purchases", stale)
        before = db.load(WORLD).to_dict()
        with pytest.raises(RuntimeError, match="changed"):
            player_handoff(gw)
        assert db.verify(WORLD).to_dict() == before


def test_receipts_survive_snapshot_and_independent_reopen(tmp_path):
    filename = tmp_path / "receipt-restart.sqlite"
    with ResumableTestSession.create(
        filename, WORLD, PLAYER, setup_living_market_world, disposable_test=True
    ) as session:
        session.bind_gateway(living_player_gateway(session.store, session.clock))
        purchase(session.store, session.gateway, "saved-receipt", qty=2)
        frozen = session.gateway.purchases().details
        view = session.handoff()
        session.store.snapshot(WORLD)
        current = session.store.verify(WORLD).to_dict()
        assert frozen["total"] == 1

    with ResumableTestSession.resume(
        filename, WORLD, PLAYER, disposable_test=True
    ) as session:
        session.bind_gateway(living_player_gateway(session.store, session.clock))
        assert session.gateway.purchases().details == frozen
        assert session.handoff() == view
        assert session.store.verify(WORLD).to_dict() == current
        assert_finite_market(session.store, player_bread=2, player_copper=6,
                             salma_bread=1, salma_copper=4)


def test_temporary_cli_shows_receipts_without_additional_purchase():
    from test_play_living_village_batch_02 import _cli, _json_handoffs
    out = _cli(
        "purchases\nbuy salma-bread 1 2\npurchases\nhandoff\nquit\n"
    ).stdout
    views = _json_handoffs(out)
    assert len(views) == 1
    assert "purchases" in out
    assert "total: 0" in out and "total: 1" in out
    assert views[0]["player_purchases"]["total"] == 1
    assert views[0]["player_purchases"]["recent"][0]["total_paid"] == 2


def test_restartable_cli_receipts_persist_without_extra_checkpoints(tmp_path):
    from test_play_living_resumable_batch_03 import run_cli, saved_states, backups_list
    filename = tmp_path / "persistent-history.sqlite"
    backups = tmp_path / "backups"
    backups.mkdir()
    original = run_cli(
        "purchases\nid paid-once buy salma-bread 1 2\npurchases\nhandoff\nquit\n",
        filename, backups, "--new", extra=("--disposable-test",),
    )
    frozen = saved_states(original.stdout)
    assert len(frozen) == 1
    assert frozen[0]["player_purchases"]["total"] == 1
    count = len(backups_list(backups))
    assert count == 2
    resumed = run_cli(
        "purchases\nhandoff\nquit\n",
        filename, backups, "--resume", extra=("--disposable-test",),
    )
    assert "total: 1" in resumed.stdout
    assert saved_states(resumed.stdout) == frozen
    assert len(backups_list(backups)) == count
