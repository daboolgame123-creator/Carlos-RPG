"""02-C test-only market: physical ownership, copper prices and barter."""
from __future__ import annotations

import pytest

from carlos_sim import (
    DomainEvent, SQLiteEventStore, TimeEngine, NPCProductionService,
    NPCMarketService, WorldState, apply_event,
)
from carlos_sim.domain import SCHEMA_VERSION, RULES_VERSION
from carlos_sim.store import InvalidEvent, RevisionConflict, DuplicateCommand
from carlos_sim.time_engine import SessionClosed

PEOPLE = ("basim", "nora", "adel", "salma", "huda", "omar", "layla")


def ev(kind, payload, actor=None, time=0):
    return DomainEvent(kind, actor, "02-C disposable physical market", time, payload)


def prepare(db, *, market=True, production=True, copper_buyer=10,
            init_buyer_bread=True, local_omar=False, grains=4,
            site_copper=0, buyer_bread=0):
    db.create_world("village")
    events = [
        ev("LocationCreated", {"id": "bakery", "name": "Bakery"}),
        ev("LocationCreated", {"id": "square", "name": "Square"}),
        ev("RouteCreated", {
            "id": "bakery-square", "a": "bakery",
            "b": "square", "seconds": 50,
        }),
    ]
    for resource, value in (
        ("grain", grains), ("oven", 2), ("bread", 0), ("coin_copper", site_copper),
    ):
        events.append(ev("ResourceChanged", {
            "owner_id": "bakery", "resource": resource,
            "previous": None, "current": value, "source": "initialization",
        }))
    for person in PEOPLE:
        loc = "bakery" if person != "omar" or local_omar else "square"
        role = "baker" if person in ("basim", "nora") else "merchant" if person == "adel" else "resident"
        events.extend([
            ev("EntityCreated", {
                "id": person, "name": person, "location_id": loc,
                "controller": "npc",
            }),
            ev("NPCConfigured", {
                "npc_id": person, "role": role,
                "needs": {"hunger": 20, "fatigue": 5, "safety": 0},
                "goals": {"earn": 50, "explore": 10, "survive": 30},
            }),
        ])
        quantities = {
            "bread": 2 if person == "huda" else buyer_bread if person == "salma" else 0,
            "grain": 2 if person == "layla" else 0,
            "coin_copper": copper_buyer if person == "salma"
                else 10 if person == "huda" else 0,
        }
        if person == "salma" and not init_buyer_bread:
            del quantities["bread"]
        if person == "salma" and copper_buyer is None:
            del quantities["coin_copper"]
        for resource, value in quantities.items():
            events.append(ev("ResourceChanged", {
                "owner_id": person, "resource": resource,
                "previous": None, "current": value,
                "source": "initialization",
            }))
    if production:
        events.append(ev("ProductionRecipeConfigured", {
            "id": "bread", "site_id": "bakery", "role": "baker",
            "input_resource": "grain", "input_amount": 2,
            "output_resource": "bread", "output_amount": 1,
            "tool_resource": "oven", "duration_seconds": 90,
        }))
    if market:
        events.append(ev("MarketStallConfigured", {
            "site_id": "bakery", "keeper_id": "adel",
        }))
    db.append("village", "setup", 0, events, bootstrap=True)


@pytest.fixture
def village(tmp_path):
    with SQLiteEventStore(tmp_path / "market.sqlite") as db:
        prepare(db)
        clock = TimeEngine(db)
        clock.open_session("village")
        yield db, clock, NPCMarketService(db, clock)


def _rev(db):
    return db.load("village").revision


def _advance(db, clock, seconds, ident):
    return clock.advance("village", seconds=seconds, command_id=ident,
                         expected_revision=_rev(db)).state


def _bake(db, clock):
    factory = NPCProductionService(db, clock)
    factory.start("village", "basim", "bread", "basim-batch",
                  expected_revision=_rev(db))
    factory.start("village", "nora", "bread", "nora-batch",
                  expected_revision=_rev(db))
    return _advance(db, clock, 90, "bake-complete")


def _offer(db, market, *, owner="bakery", seller="adel", item="bread",
           price=3, count=2, payment="coin_copper", ident="bread-quote"):
    return market.post("village", seller, owner, "bakery", ident, item,
                       count, payment, price, expected_revision=_rev(db)).state


def _buy(db, market, *, who="salma", ident="buy-once", listing="bread-quote",
         quantity=1, price=3):
    return market.buy("village", who, ident, listing, quantity, price,
                      expected_revision=_rev(db)).state


def test_opt_in_empty_market_and_schema(tmp_path):
    assert (SCHEMA_VERSION, RULES_VERSION) == (31, 39)
    with SQLiteEventStore(tmp_path / "off.sqlite") as db:
        prepare(db, market=False)
        clock = TimeEngine(db)
        clock.open_session("village")
        state = _advance(db, clock, 500, "time")
        assert not state.market_stalls and not state.market_offers and not state.market_trades
        assert db.verify("village").to_dict() == state.to_dict()


def test_bakery_two_loaves_one_copper_purchase_from_site_owner(village):
    db, clock, market = village
    made = _bake(db, clock)
    assert made.resources["bakery"] == {
        "bread": 2, "coin_copper": 0, "grain": 0, "oven": 2,
    }
    q = _offer(db, market)
    assert q.market_offers["bread-quote"]["stock_owner_id"] == "bakery"
    quotes = market.local_quotes("village", "salma")
    assert quotes == ({
        "offer_id": "bread-quote", "resource": "bread",
        "available": 2, "payment_resource": "coin_copper",
        "unit_price": 3, "site_id": "bakery",
    },)
    sold = _buy(db, market)
    assert sold.resources["bakery"]["bread"] == 1
    assert sold.resources["bakery"]["coin_copper"] == 3
    assert sold.resources["salma"]["bread"] == 1
    assert sold.resources["salma"]["coin_copper"] == 7
    assert sold.resources["adel"]["coin_copper"] == 0
    trade = sold.market_trades["buy-once"]
    assert trade["total_paid"] == 3
    assert trade["goods_source_before"] == 2
    assert trade["goods_source_after"] == 1
    assert trade["goods_target_before"] == 0
    assert trade["goods_target_after"] == 1
    assert trade["pay_source_before"] == 10
    assert trade["pay_source_after"] == 7
    assert trade["pay_target_before"] == 0
    assert trade["pay_target_after"] == 3
    assert db.verify("village").to_dict() == sold.to_dict()


def test_second_buyer_finishes_offer_without_double_selling(village):
    db, clock, market = village
    _bake(db, clock)
    _offer(db, market)
    _buy(db, market)
    final = _buy(db, market, who="huda", ident="buy-two")
    assert final.market_offers["bread-quote"]["remaining"] == 0
    assert final.market_offers["bread-quote"]["status"] == "filled"
    assert final.resources["bakery"]["bread"] == 0
    assert final.resources["bakery"]["coin_copper"] == 6
    assert final.resources["huda"]["bread"] == 3
    assert final.resources["huda"]["coin_copper"] == 7
    with pytest.raises(InvalidEvent):
        _buy(db, market, who="layla", ident="buy-three")
    assert db.load("village").to_dict() == final.to_dict()


def test_private_personal_stock_can_be_bartered_for_grain(village):
    db, clock, market = village
    before = db.load("village")
    assert before.resources["huda"]["bread"] == 2
    market.post("village", "huda", "huda", "bakery",
                "barter", "bread", 1, "grain", 2,
                expected_revision=_rev(db))
    done = market.buy("village", "layla", "barter-trade", "barter", 1, 2,
                      expected_revision=_rev(db)).state
    assert done.resources["huda"]["bread"] == 1
    assert done.resources["huda"]["grain"] == 2
    assert done.resources["layla"]["bread"] == 1
    assert done.resources["layla"]["grain"] == 0
    assert done.resources["bakery"]["coin_copper"] == 0
    assert done.market_trades["barter-trade"]["payment_resource"] == "grain"
    assert done.market_trades["barter-trade"]["total_paid"] == 2
    assert db.verify("village").to_dict() == done.to_dict()


def test_cannot_offer_site_goods_before_real_production(village):
    db, clock, market = village
    before = db.load("village").to_dict()
    with pytest.raises(InvalidEvent, match="inventory"):
        _offer(db, market)
    assert db.load("village").to_dict() == before


def test_unregistered_seller_cannot_take_site_stock(village):
    db, clock, market = village
    _bake(db, clock)
    before = db.load("village").to_dict()
    with pytest.raises(InvalidEvent, match="seller"):
        _offer(db, market, seller="salma", ident="fake-keeper")
    with pytest.raises(InvalidEvent, match="seller"):
        _offer(db, market, seller="adel", owner="basim", ident="fake-owner")
    assert db.load("village").to_dict() == before


def test_wrong_price_bool_price_and_overcommit_refused(village):
    db, clock, market = village
    _bake(db, clock)
    _offer(db, market)
    old = db.load("village").to_dict()
    for price in (0, -1, True, 2**31):
        with pytest.raises(InvalidEvent):
            _offer(db, market, ident="wrong-" + str(price), price=price, count=1)
    with pytest.raises(InvalidEvent):
        _offer(db, market, ident="too-many", count=3)
    with pytest.raises(InvalidEvent):
        _buy(db, market, ident="wrong-price", price=4)
    with pytest.raises(InvalidEvent):
        _buy(db, market, ident="wrong-quantity", quantity=3)
    assert db.load("village").to_dict() == old


def test_unknown_coins_or_unknown_recipient_goods_not_zero(tmp_path):
    for i, options in enumerate((
        {"copper_buyer": None}, {"init_buyer_bread": False},
        {"copper_buyer": 2},
    )):
        with SQLiteEventStore(tmp_path / f"unknown-{i}.sqlite") as db:
            prepare(db, **options)
            clock = TimeEngine(db)
            clock.open_session("village")
            market = NPCMarketService(db, clock)
            _bake(db, clock)
            _offer(db, market)
            before = db.load("village").to_dict()
            with pytest.raises(InvalidEvent, match="known|insufficient"):
                _buy(db, market)
            assert db.load("village").to_dict() == before


def test_distant_actor_cannot_see_or_buy_local_goods(village):
    db, clock, market = village
    _bake(db, clock)
    _offer(db, market)
    assert market.local_quotes("village", "omar") == ()
    before = db.load("village").to_dict()
    with pytest.raises(InvalidEvent, match="present"):
        _buy(db, market, who="omar")
    assert db.load("village").to_dict() == before


def test_only_seller_can_close_and_closed_offer_never_sells(village):
    db, clock, market = village
    _bake(db, clock)
    _offer(db, market)
    with pytest.raises(InvalidEvent):
        market.close("village", "salma", "bread-quote",
                     expected_revision=_rev(db))
    result = market.close("village", "adel", "bread-quote",
                          expected_revision=_rev(db)).state
    assert result.market_offers["bread-quote"]["status"] == "closed"
    assert result.market_offers["bread-quote"]["remaining"] == 2
    assert result.resources["bakery"]["bread"] == 2
    with pytest.raises(InvalidEvent):
        _buy(db, market)
    assert db.verify("village").to_dict() == result.to_dict()


def test_market_capability_required_direct_reducer_and_store(village):
    db, clock, market = village
    _bake(db, clock)
    state = db.load("village")
    event = ev("MarketOfferPosted", {
        "id": "untrusted", "seller_id": "adel", "stock_owner_id": "bakery",
        "site_id": "bakery", "resource": "bread", "quantity": 1,
        "payment_resource": "coin_copper", "unit_price": 1,
    }, actor="adel", time=state.time)
    with pytest.raises(ValueError, match="trusted"):
        apply_event(state, event)
    with pytest.raises(InvalidEvent, match="trusted"):
        db.append("village", "forged", state.revision, [event])
    assert db.load("village").to_dict() == state.to_dict()


def test_market_session_pause_prevents_transfers(village):
    db, clock, market = village
    _bake(db, clock)
    _offer(db, market)
    before = db.load("village").to_dict()
    clock.close_session("village")
    with pytest.raises(SessionClosed):
        _buy(db, market)
    event = ev("MarketTradeExecuted", {
        "id": "closed", "buyer_id": "salma", "offer_id": "bread-quote",
        "quantity": 1, "expected_unit_price": 3,
    }, actor="salma", time=before["time"])
    with pytest.raises(InvalidEvent, match="active"):
        db.append("village", "direct-closed", before["revision"], [event],
                  market_authorized=True)
    assert db.load("village").to_dict() == before


def test_duplicate_request_and_stale_revision_do_not_double_charge(village):
    db, clock, market = village
    _bake(db, clock)
    _offer(db, market)
    initial = db.load("village")
    done = _buy(db, market)
    with pytest.raises(DuplicateCommand):
        _buy(db, market)
    with pytest.raises(RevisionConflict):
        market.buy("village", "huda", "late-buyer", "bread-quote",
                   1, 3, expected_revision=initial.revision)
    assert db.load("village").to_dict() == done.to_dict()


def test_batch_rollback_of_valid_trade_plus_bad_trade(village):
    db, clock, market = village
    _bake(db, clock)
    _offer(db, market)
    before = db.load("village")
    events = [
        ev("MarketTradeExecuted", {
            "id": "first", "buyer_id": "salma",
            "offer_id": "bread-quote", "quantity": 1, "expected_unit_price": 3,
        }, actor="salma", time=before.time),
        ev("MarketTradeExecuted", {
            "id": "second", "buyer_id": "layla",
            "offer_id": "bread-quote", "quantity": 1, "expected_unit_price": 3,
        }, actor="layla", time=before.time),
    ]
    with pytest.raises(InvalidEvent):
        db.append("village", "two-sales-one-bad", before.revision,
                  events, market_authorized=True)
    assert db.load("village").to_dict() == before.to_dict()
    assert db.db.execute(
        "SELECT count(*) FROM commands WHERE command_id='two-sales-one-bad'"
    ).fetchone()[0] == 0


def test_offers_and_trades_are_validated_in_snapshots(village):
    db, clock, market = village
    _bake(db, clock)
    _offer(db, market)
    _buy(db, market)
    state = db.load("village")
    for mode in ("absent", "fake-trade", "bad-coin", "bad-remaining", "wrong-site"):
        d = state.to_dict()
        if mode == "absent":
            del d["market_trades"]
        elif mode == "fake-trade":
            d["market_trades"]["buy-once"]["goods_target_after"] = 5
        elif mode == "bad-coin":
            d["market_trades"]["buy-once"]["total_paid"] = 0
        elif mode == "bad-remaining":
            d["market_offers"]["bread-quote"]["remaining"] = 99
        else:
            d["market_offers"]["bread-quote"]["site_id"] = "square"
        with pytest.raises(ValueError):
            WorldState.from_dict(d)
    assert db.verify("village").to_dict() == state.to_dict()
