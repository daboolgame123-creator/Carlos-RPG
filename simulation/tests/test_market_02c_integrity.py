"""Independent adversarial-style 02-C probes: ownership, replay and rollback.

This is an author-run suite, not independent external review.
"""
from __future__ import annotations

import pytest

from carlos_sim import (
    DomainEvent, SQLiteEventStore, TimeEngine, NPCMarketService,
    WorldState, apply_event, NPCMovementService,
)
from carlos_sim.store import InvalidEvent, RevisionConflict
from carlos_sim.backup import create_backup_bundle, verify_backup_bundle, restore_backup_bundle
from test_market_02c import ev, prepare, _bake, _offer, _buy, _rev

BASE_SHA = "6dbee22a4b6b167a5b5ca5ece1c51612016b9e5d"


def test_snapshot_reopen_and_isolated_backup_preserves_real_bakery_market(tmp_path):
    original = tmp_path / "market.sqlite"
    with SQLiteEventStore(original) as db:
        prepare(db)
        clock = TimeEngine(db)
        clock.open_session("village")
        market = NPCMarketService(db, clock)
        _bake(db, clock)
        _offer(db, market)
        sold = _buy(db, market)
        before = sold.to_dict()
        db.snapshot("village")
        assert db.verify("village").to_dict() == before
        bundle = tmp_path / "bundle"
        manifest = create_backup_bundle(db, "village", bundle, code_commit=BASE_SHA)
        assert (manifest["schema"], manifest["rules"]) == (30, 38)
        assert verify_backup_bundle(bundle) == manifest
    target = tmp_path / "restore.sqlite"
    restore_backup_bundle(bundle, target)
    with SQLiteEventStore(target) as db:
        assert db.db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert db.verify("village").to_dict() == before
        clock = TimeEngine(db)
        clock.open_session("village")
        market = NPCMarketService(db, clock)
        second = _buy(db, market, who="huda", ident="second-buyer")
        assert second.resources["bakery"]["bread"] == 0
        assert second.resources["bakery"]["coin_copper"] == 6
        assert second.market_offers["bread-quote"]["status"] == "filled"
        assert db.verify("village").to_dict() == second.to_dict()
    with SQLiteEventStore(original) as db:
        assert db.verify("village").to_dict() == before
        assert db.load("village").resources["bakery"]["bread"] == 1


def test_full_buyer_storage_rejects_overflow_without_deducting_coin(tmp_path):
    with SQLiteEventStore(tmp_path / "overflow-bread.sqlite") as db:
        prepare(db, buyer_bread=2**31 - 1)
        clock = TimeEngine(db)
        clock.open_session("village")
        market = NPCMarketService(db, clock)
        _bake(db, clock)
        _offer(db, market)
        before = db.load("village").to_dict()
        with pytest.raises(InvalidEvent, match="overflow"):
            _buy(db, market)
        assert db.load("village").to_dict() == before


def test_full_stall_till_rejects_payment_overflow_without_deducting_bread(tmp_path):
    with SQLiteEventStore(tmp_path / "overflow-till.sqlite") as db:
        prepare(db, site_copper=2**31 - 1)
        clock = TimeEngine(db)
        clock.open_session("village")
        market = NPCMarketService(db, clock)
        _bake(db, clock)
        _offer(db, market)
        before = db.load("village").to_dict()
        with pytest.raises(InvalidEvent, match="overflow"):
            _buy(db, market)
        assert db.load("village").to_dict() == before


def test_seller_in_transit_cannot_complete_an_old_local_quote(tmp_path):
    with SQLiteEventStore(tmp_path / "seller-travel.sqlite") as db:
        prepare(db)
        clock = TimeEngine(db)
        clock.open_session("village")
        market = NPCMarketService(db, clock)
        _bake(db, clock)
        _offer(db, market)
        NPCMovementService(db, clock).start(
            "village", "adel", "bakery-square", "leaving-market",
            expected_revision=_rev(db))
        frozen = db.load("village").to_dict()
        with pytest.raises(InvalidEvent, match="present"):
            _buy(db, market)
        assert db.load("village").to_dict() == frozen
        # Goods stay at the bakery; the steward has not teleported their title.
        assert db.load("village").resources["bakery"]["bread"] == 2


def test_buyer_in_transit_cannot_teleport_purchase(tmp_path):
    with SQLiteEventStore(tmp_path / "buyer-travel.sqlite") as db:
        prepare(db)
        clock = TimeEngine(db)
        clock.open_session("village")
        market = NPCMarketService(db, clock)
        _bake(db, clock)
        _offer(db, market)
        NPCMovementService(db, clock).start(
            "village", "salma", "bakery-square", "leaving",
            expected_revision=_rev(db))
        with pytest.raises(InvalidEvent):
            _buy(db, market)
        assert db.load("village").resources["salma"]["bread"] == 0


def test_spoofed_actor_id_cannot_take_another_buyers_copper(tmp_path):
    with SQLiteEventStore(tmp_path / "spoof.sqlite") as db:
        prepare(db)
        clock = TimeEngine(db)
        clock.open_session("village")
        market = NPCMarketService(db, clock)
        _bake(db, clock)
        _offer(db, market)
        prior = db.load("village")
        forged = ev("MarketTradeExecuted", {
            "id": "stolen", "offer_id": "bread-quote",
            "buyer_id": "salma", "quantity": 1,
            "expected_unit_price": 3,
        }, actor="huda", time=prior.time)
        with pytest.raises(InvalidEvent):
            db.append("village", "forged-buyer", prior.revision, [forged],
                      market_authorized=True)
        assert db.load("village").to_dict() == prior.to_dict()


def test_unconfigured_steward_or_impostor_never_sells_location_goods(tmp_path):
    with SQLiteEventStore(tmp_path / "unregistered.sqlite") as db:
        prepare(db, market=False)
        clock = TimeEngine(db)
        clock.open_session("village")
        market = NPCMarketService(db, clock)
        _bake(db, clock)
        before = db.load("village").to_dict()
        with pytest.raises(InvalidEvent):
            _offer(db, market)
        assert db.load("village").to_dict() == before
        with pytest.raises(InvalidEvent):
            db.append("village", "fake-stall", _rev(db), [
                ev("MarketStallConfigured", {
                    "site_id": "bakery", "keeper_id": "adel",
                }, time=before["time"]),
            ], bootstrap=True)
        assert db.load("village").to_dict() == before


def test_market_rejects_fake_free_commodities_and_counter_sale(tmp_path):
    with SQLiteEventStore(tmp_path / "illegal-item.sqlite") as db:
        prepare(db)
        clock = TimeEngine(db)
        clock.open_session("village")
        market = NPCMarketService(db, clock)
        _bake(db, clock)
        old = db.load("village").to_dict()
        for item in ("coin_copper", "oven", "regrowth_reserve",
                     "investigation_attempts", "labor_units", "wild_food"):
            with pytest.raises(InvalidEvent):
                _offer(db, market, ident="sell-" + item, item=item, count=1)
        assert db.load("village").to_dict() == old


def test_followup_sales_use_updated_ledger_not_original_offer_stock(tmp_path):
    with SQLiteEventStore(tmp_path / "fresh-balances.sqlite") as db:
        prepare(db)
        clock = TimeEngine(db)
        clock.open_session("village")
        market = NPCMarketService(db, clock)
        _bake(db, clock)
        _offer(db, market)
        first = _buy(db, market)
        assert first.market_offers["bread-quote"]["remaining"] == 1
        second = _buy(db, market, who="huda", ident="second-purchase")
        trade = second.market_trades["second-purchase"]
        assert trade["goods_source_before"] == 1
        assert trade["goods_source_after"] == 0
        assert trade["pay_target_before"] == 3
        assert trade["pay_target_after"] == 6
        assert second.market_offers["bread-quote"]["remaining"] == 0
        assert db.verify("village").to_dict() == second.to_dict()
