"""PLAY-05: real, conserved human-player purchases in the seven-NPC village.

All money and stock are finite, test-only initialized resource ledger entries.
RPG inventory/equipment remains unimplemented and is never fabricated.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from carlos_sim import (
    DomainEvent, NPCMarketService, PlayerGateway,
    SQLiteEventStore, TimeEngine,
)
from carlos_sim.player_handoff import player_handoff
from carlos_sim.resumable_play import ResumableTestSession
from carlos_sim.store import InvalidEvent, DuplicateCommand, RevisionConflict

SIM = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SIM / "scenarios" / "test_village"))
from living_player_fixture import (  # noqa: E402
    WORLD, PLAYER, PEOPLE, living_player_gateway, setup_living_market_world,
    setup_living_player_world,
)


def village(tmp_path):
    db = SQLiteEventStore(tmp_path / "player-market.sqlite")
    setup_living_market_world(db)
    clock = TimeEngine(db)
    clock.open_session(WORLD)
    return db, clock, living_player_gateway(db, clock)


def purchase(db, gw, cid, *, qty=1, price=2):
    return gw.buy(
        "salma-bread", qty, price, command_id=cid,
        expected_revision=db.load(WORLD).revision,
    )


def assert_finite_market(db, *, player_bread, player_copper,
                         salma_bread, salma_copper):
    state = db.load(WORLD)
    p, s = state.resources[PLAYER], state.resources["salma"]
    assert (p["bread"], p["coin_copper"]) == (player_bread, player_copper)
    assert (s["bread"], s["coin_copper"]) == (salma_bread, salma_copper)
    assert p["bread"] + s["bread"] == 3
    assert p["coin_copper"] + s["coin_copper"] == 10
    assert state.rpg_profiles[PLAYER]["inventory"] == {}
    assert state.rpg_profiles[PLAYER]["equipment"] == {}
    assert db.verify(WORLD).to_dict() == state.to_dict()


def test_test_market_is_finite_and_view_is_local_read_only(tmp_path):
    db, clock, gw = village(tmp_path)
    with db:
        initial = db.load(WORLD).to_dict()
        quote = gw.offers()
        wallet = gw.supplies()
        assert quote.status == "offers"
        assert quote.details["offers"] == (
            {"offer_id": "salma-bread", "seller_id": "salma",
             "resource": "bread", "available": 3,
             "payment_resource": "coin_copper", "unit_price": 2},
        )
        assert wallet.status == "supplies"
        assert wallet.details == {"balances": {"bread": 0, "coin_copper": 10}}
        visible = player_handoff(gw)
        assert visible["player_supplies"] == wallet.details
        secret = json.dumps(visible, ensure_ascii=False)
        for forbidden in ('"npcs"', '"goals"', '"needs"', '"market_trades"',
                          '"market_offers"', '"coin_copper": 0'):
            assert forbidden not in secret
        for distant in ("nora", "huda", "omar", "layla"):
            assert distant not in secret
        assert db.load(WORLD).to_dict() == initial
        assert db.verify(WORLD).to_dict() == initial


def test_carlos_buys_two_loaves_then_last_one_and_stock_conserves(tmp_path):
    db, clock, gw = village(tmp_path)
    with db:
        sale = purchase(db, gw, "first", qty=2)
        assert sale.status == "purchased"
        assert sale.details["resource"] == "bread"
        assert sale.details["quantity"] == 2
        assert sale.details["total_paid"] == 4
        assert sale.details["payment_resource"] == "coin_copper"
        assert_finite_market(db, player_bread=2, player_copper=6,
                             salma_bread=1, salma_copper=4)
        assert gw.offers().details["offers"][0]["available"] == 1
        receipt = purchase(db, gw, "second")
        assert receipt.details["total_paid"] == 2
        state = db.load(WORLD)
        assert state.market_offers["salma-bread"]["status"] == "filled"
        assert gw.offers().details["offers"] == ()
        assert_finite_market(db, player_bread=3, player_copper=4,
                             salma_bread=0, salma_copper=6)
        assert len(db.load(WORLD).market_trades) == 2
        assert set(x["buyer_id"] for x in state.market_trades.values()) == {PLAYER}
        assert "bread" not in state.rpg_profiles[PLAYER]["inventory"]


@pytest.mark.parametrize("qty,price", [
    (0, 2), (-1, 2), (4, 2), (1001, 2),
    (1, 0), (1, 3), (1, -1), (1, 1001),
    (True, 2), (1, True), ("1", 2), (1, "2"),
])
def test_invalid_trade_quantity_or_price_cannot_mutate_world(tmp_path, qty, price):
    db, clock, gw = village(tmp_path)
    with db:
        before = db.load(WORLD).to_dict()
        with pytest.raises((ValueError, InvalidEvent)):
            purchase(db, gw, "bad", qty=qty, price=price)
        assert db.load(WORLD).to_dict() == before


def test_player_id_bound_and_npc_service_cannot_impersonate_human(tmp_path):
    db, clock, gw = village(tmp_path)
    with db:
        before = db.load(WORLD).to_dict()
        with pytest.raises(PermissionError, match="real NPC"):
            NPCMarketService(db, clock).buy(
                WORLD, PLAYER, "forged", "salma-bread", 1, 2,
                expected_revision=before["revision"],
            )
        wrong = PlayerGateway(db, clock, world_id=WORLD, player_id="nora")
        with pytest.raises(PermissionError):
            wrong.buy("salma-bread", 1, 2, command_id="forged",
                      expected_revision=before["revision"])
        with pytest.raises(InvalidEvent):
            db.append(WORLD, "no-market-authority", before["revision"], [
                DomainEvent("MarketTradeExecuted", PLAYER, "untrusted", 0, {
                    "id": "unauthorized", "buyer_id": PLAYER,
                    "offer_id": "salma-bread", "quantity": 1,
                    "expected_unit_price": 2,
                }),
            ])
        assert db.load(WORLD).to_dict() == before


def test_player_remote_busy_and_travelling_trade_refused_without_leak(tmp_path):
    db, clock, gw = village(tmp_path)
    with db:
        departure = gw.move("square-woods", command_id="forest-first",
                            expected_revision=db.load(WORLD).revision)
        travel_state = db.load(WORLD).to_dict()
        assert gw.offers().details["offers"] == ()
        with pytest.raises(ValueError, match="travelling"):
            purchase(db, gw, "during-travel")
        assert db.load(WORLD).to_dict() == travel_state
        gw.wait(50, command_id="reach-woods",
                expected_revision=db.load(WORLD).revision)
        assert gw.inspect().details["location_id"] == "woods"
        assert gw.offers().details["offers"] == ()
        with pytest.raises(InvalidEvent, match="both present"):
            purchase(db, gw, "remote-seller")
        assert_finite_market(db, player_bread=0, player_copper=10,
                             salma_bread=3, salma_copper=0)


def test_seller_started_work_so_quote_is_not_current_trade_ability(tmp_path):
    db, clock, gw = village(tmp_path)
    with db:
        gw.wait(1, command_id="village-life",
                expected_revision=db.load(WORLD).revision)
        state = db.load(WORLD)
        assert any(a["npc_id"] == "salma" and a["status"] == "running"
                   for a in state.actions.values())
        assert gw.offers().details["offers"] == ()
        with pytest.raises(InvalidEvent):
            purchase(db, gw, "busy-salma")
        assert_finite_market(db, player_bread=0, player_copper=10,
                             salma_bread=3, salma_copper=0)


def test_stale_and_duplicate_player_buys_cannot_double_spend(tmp_path):
    db, clock, gw = village(tmp_path)
    with db:
        initial = db.load(WORLD)
        purchase(db, gw, "unique-first", qty=1)
        settled = db.load(WORLD).to_dict()
        with pytest.raises(DuplicateCommand):
            purchase(db, gw, "unique-first", qty=1)
        with pytest.raises(RevisionConflict):
            gw.buy("salma-bread", 1, 2, command_id="different-id",
                   expected_revision=initial.revision)
        assert db.load(WORLD).to_dict() == settled
        assert_finite_market(db, player_bread=1, player_copper=8,
                             salma_bread=2, salma_copper=2)


def test_missing_or_unknown_buyer_stock_cannot_be_assumed_zero(tmp_path):
    with SQLiteEventStore(tmp_path / "unknown.sqlite") as db:
        setup_living_player_world(db)
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        gw = living_player_gateway(db, clock)
        assert gw.supplies().details["balances"] == {}
        assert gw.offers().details["offers"] == ()
        before = db.load(WORLD).to_dict()
        with pytest.raises(InvalidEvent):
            gw.buy("unknown-offer", 1, 2, command_id="no-market",
                   expected_revision=before["revision"])
        assert db.load(WORLD).to_dict() == before


def test_trade_and_player_ownership_survive_sqlite_snapshot_reopen(tmp_path):
    path = tmp_path / "persistent.sqlite"
    with ResumableTestSession.create(
        path, WORLD, PLAYER, setup_living_market_world, disposable_test=True
    ) as session:
        session.bind_gateway(living_player_gateway(session.store, session.clock))
        first = purchase(session.store, session.gateway, "saved", qty=2)
        frozen = session.handoff()
        session.store.snapshot(WORLD)
        saved = session.store.verify(WORLD).to_dict()
        assert first.details["quantity"] == 2
    with ResumableTestSession.resume(
        path, WORLD, PLAYER, disposable_test=True
    ) as session:
        session.bind_gateway(living_player_gateway(session.store, session.clock))
        assert session.handoff() == frozen
        assert session.store.verify(WORLD).to_dict() == saved
        assert_finite_market(session.store,
                             player_bread=2, player_copper=6,
                             salma_bread=1, salma_copper=4)
        with pytest.raises(DuplicateCommand):
            purchase(session.store, session.gateway, "saved", qty=2)
        assert session.store.verify(WORLD).to_dict() == saved


def test_local_cli_buys_real_goods_and_reports_only_carlos_supplies():
    from test_play_living_village_batch_02 import _cli, _json_handoffs
    output = _cli(
        "offers\nsupplies\nbuy salma-bread 2 2\nsupplies\noffers\nhandoff\nquit\n"
    ).stdout
    views = _json_handoffs(output)
    assert len(views) == 1
    assert views[0]["player_supplies"]["balances"]["bread"] == 2
    assert views[0]["player_supplies"]["balances"]["coin_copper"] == 6
    assert "purchased" in output and "'total_paid': 4" in output
    assert "'available': 1" in output
    assert "nora" not in json.dumps(views)


def test_resumable_cli_purchase_preserved_and_duplicate_request_rejected(tmp_path):
    from test_play_living_resumable_batch_03 import (
        run_cli, saved_states, backups_list,
    )
    file = tmp_path / "trade.sqlite"
    backups = tmp_path / "backups"
    backups.mkdir()
    first = run_cli(
        "offers\nid bought-once buy salma-bread 1 2\nhandoff\nquit\n",
        file, backups, "--new", extra=("--disposable-test",),
    )
    exported = saved_states(first.stdout)
    assert len(exported) == 1
    assert exported[0]["player_supplies"]["balances"]["bread"] == 1
    assert exported[0]["player_supplies"]["balances"]["coin_copper"] == 8
    count = len(backups_list(backups))
    assert count == 2
    again = run_cli(
        "id bought-once buy salma-bread 1 2\nscene\nhandoff\nquit\n",
        file, backups, "--resume", extra=("--disposable-test",),
    )
    assert "Rejected:" in again.stdout
    assert saved_states(again.stdout) == exported
    assert len(backups_list(backups)) == count
    with SQLiteEventStore(file) as db:
        assert_finite_market(db, player_bread=1, player_copper=8,
                             salma_bread=2, salma_copper=2)
