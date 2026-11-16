"""PLAY49-C: tavern supply resale from real upstream markets, no free meals.

Test-only: Huda buys exactly 1 real fruit and 1 real cheese, physically
walks their owned stock to a tavern, then resells it to an on-site resident.
No instant cooking, virtual meals, wages or stock renewal are asserted.
"""
import pytest

from carlos_sim import SQLiteEventStore, TimeEngine, NPCMarketService, NPCMovementService
from carlos_sim.store import InvalidEvent
from test_market_02c import ev, prepare, _rev
from test_play49_fruit_stall_contract import WORLD, add_orchard, copper
from test_play49_dairy_stall_contract import add_dairy, produce, pay_both, post_three


def add_tavern(db):
    before = db.load(WORLD)
    changes = [
        ev("LocationCreated", {"id": "tavern", "name": "Village Tavern"}),
        ev("RouteCreated", {
            "id": "dairy-tavern", "a": "dairy", "b": "tavern", "seconds": 60}),
        ev("RouteCreated", {
            "id": "bakery-tavern", "a": "bakery", "b": "tavern", "seconds": 80}),
        ev("EntityCreated", {
            "id": "tavern_host", "name": "Tavern Host",
            "location_id": "tavern", "controller": "npc"}),
        ev("NPCConfigured", {
            "npc_id": "tavern_host", "role": "merchant",
            "needs": {"hunger": 20, "fatigue": 0, "safety": 0},
            "goals": {"earn": 50, "explore": 10, "survive": 30}}),
    ]
    for owner, resource, amount in (
        ("tavern", "fruit", 0), ("tavern", "cheese", 0),
        ("tavern", "coin_copper", 0),
        ("tavern_host", "coin_copper", 0),
        ("huda", "fruit", 0), ("huda", "cheese", 0),
    ):
        changes.append(ev("ResourceChanged", {
            "owner_id": owner, "resource": resource, "previous": None,
            "current": amount, "source": "initialization"}))
    changes.append(ev("MarketStallConfigured", {
        "site_id": "tavern", "keeper_id": "tavern_host"}))
    s = db.append(WORLD, "tavern:open-empty-with-real-road", before.revision,
                  changes, bootstrap=True)
    assert len(s.market_stalls) == 4
    assert copper(s) == copper(before), "no fresh opening coins for tavern"
    assert s.resources["tavern"]["fruit"] == s.resources["tavern"]["cheese"] == 0
    assert s.resources["huda"]["coin_copper"] == before.resources["huda"]["coin_copper"]
    assert db.verify(WORLD).to_dict() == s.to_dict()


@pytest.fixture
def village(tmp_path):
    with SQLiteEventStore(tmp_path / "tavern.sqlite") as db:
        prepare(db)
        add_orchard(db)
        add_dairy(db)
        add_tavern(db)
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            yield db, clock, NPCMarketService(db, clock)
        finally:
            clock.close_session(WORLD)


def walk(db, clock, person, road, label, seconds, split=False):
    NPCMovementService(db, clock).start(WORLD, person, road, label,
                                        expected_revision=_rev(db))
    parts = [seconds // 2, seconds - seconds // 2] if split else [seconds]
    for idx, amount in enumerate(parts):
        clock.advance(WORLD, seconds=amount,
                      command_id=f"{label}:travel:{idx}",
                      expected_revision=_rev(db))
    assert not any(
        j["npc_id"] == person and j["status"] == "traveling"
        for j in db.load(WORLD).travels.values()
    )


def source_goods(db, clock, market, *, split=False):
    """All profits are from ordinary paid market trades and physical travel."""
    produce(db, clock)
    pay_both(db)
    post_three(db, market)
    opening = db.load(WORLD)
    assert opening.resources["huda"]["coin_copper"] == 10
    assert opening.resources["huda"]["fruit"] == opening.resources["huda"]["cheese"] == 0
    assert opening.resources["tavern"]["coin_copper"] == 0
    assert market.local_quotes(WORLD, "huda")[0]["offer_id"] == "bread-quote"
    with pytest.raises(InvalidEvent):  # no remote fruit from bakery
        market.buy(WORLD, "huda", "forged-remote-source",
                   "fruit-quote", 1, 1, expected_revision=_rev(db))

    walk(db, clock, "huda", "bakery-orchard", "huda-goes-to-fruit", 50, split=split)
    fruit = market.buy(WORLD, "huda", "huda-buys-real-fruit",
                       "fruit-quote", 1, 1, expected_revision=_rev(db)).state
    assert fruit.resources["huda"]["fruit"] == 1
    assert fruit.resources["orchard"]["fruit"] == 0
    walk(db, clock, "huda", "orchard-dairy", "huda-goes-to-cheese", 70, split=split)
    cheese = market.buy(WORLD, "huda", "huda-buys-real-cheese",
                        "cheese-quote", 1, 2, expected_revision=_rev(db)).state
    assert cheese.resources["huda"]["cheese"] == 1
    assert cheese.resources["dairy"]["cheese"] == 0
    assert cheese.resources["huda"]["coin_copper"] == opening.resources["huda"]["coin_copper"] - 3
    assert copper(cheese) == copper(opening)
    return opening


def post_tavern(db, market):
    # Huda alone owns the carried stock; the tavern host must not steal it.
    for item, price, key in (("fruit", 2, "tavern-fruit-quote"),
                              ("cheese", 3, "tavern-cheese-quote")):
        market.post(WORLD, "huda", "huda", "tavern", key,
                    item, 1, "coin_copper", price, expected_revision=_rev(db))


def resale(db, clock, market, *, split=False):
    opening = source_goods(db, clock, market, split=split)
    walk(db, clock, "huda", "dairy-tavern", "huda-reaches-tavern", 60, split=split)
    assert db.load(WORLD).resources["huda"]["fruit"] == 1
    assert db.load(WORLD).resources["huda"]["cheese"] == 1
    post_tavern(db, market)
    before_customer = db.load(WORLD)
    with pytest.raises(InvalidEvent):  # buyer not in tavern yet
        market.buy(WORLD, "salma", "remote-tavern-fruit",
                   "tavern-fruit-quote", 1, 2, expected_revision=_rev(db))
    assert db.verify(WORLD).to_dict() == before_customer.to_dict()
    walk(db, clock, "salma", "bakery-tavern", "salma-reaches-tavern", 80, split=split)
    assert {q["offer_id"] for q in market.local_quotes(WORLD, "salma")} == {
        "tavern-fruit-quote", "tavern-cheese-quote"}
    market.buy(WORLD, "salma", "salma-gets-fruit-at-tavern",
               "tavern-fruit-quote", 1, 2, expected_revision=_rev(db))
    sold = market.buy(WORLD, "salma", "salma-gets-cheese-at-tavern",
                      "tavern-cheese-quote", 1, 3, expected_revision=_rev(db)).state
    assert sold.resources["salma"]["fruit"] == sold.resources["salma"]["cheese"] == 1
    assert sold.resources["huda"]["fruit"] == sold.resources["huda"]["cheese"] == 0
    assert sold.resources["huda"]["coin_copper"] == opening.resources["huda"]["coin_copper"] + 2
    assert sold.resources["salma"]["coin_copper"] == opening.resources["salma"]["coin_copper"] - 5
    assert sold.resources["tavern"]["coin_copper"] == 0  # Huda owns her proceeds
    assert sold.resources["tavern_host"]["coin_copper"] == 0  # no fabricated service wage
    assert sold.resources["orchard"]["coin_copper"] == 1
    assert sold.resources["dairy"]["coin_copper"] == 2
    assert copper(sold) == copper(opening)
    assert set(sold.market_trades) == {
        "huda-buys-real-fruit", "huda-buys-real-cheese",
        "salma-gets-fruit-at-tavern", "salma-gets-cheese-at-tavern"}
    assert not sold.consumptions  # no free meals or fake cooking
    assert db.verify(WORLD).to_dict() == sold.to_dict()
    return sold


def test_four_local_stalls_real_sourced_tavern_resale_and_provenance(village):
    db, clock, market = village
    sold = resale(db, clock, market)
    assert len(sold.market_stalls) == 4
    assert sold.market_trades["huda-buys-real-fruit"]["site_id"] == "orchard"
    assert sold.market_trades["huda-buys-real-cheese"]["site_id"] == "dairy"
    assert sold.market_trades["salma-gets-fruit-at-tavern"]["site_id"] == "tavern"
    assert sold.market_trades["salma-gets-cheese-at-tavern"]["site_id"] == "tavern"
    assert sold.market_trades["salma-gets-cheese-at-tavern"]["stock_owner_id"] == "huda"
    db.snapshot(WORLD)
    assert db.verify(WORLD).to_dict() == sold.to_dict()
    assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    assert not db.db.execute("PRAGMA foreign_key_check").fetchall()


def test_tavern_host_cannot_steal_vendor_stock_or_offer_unproduced_goods(village):
    db, clock, market = village
    original = db.load(WORLD)
    with pytest.raises(InvalidEvent):
        market.post(WORLD, "tavern_host", "tavern", "tavern", "imaginary",
                    "cheese", 1, "coin_copper", 1, expected_revision=_rev(db))
    assert db.verify(WORLD).to_dict() == original.to_dict()
    source_goods(db, clock, market)
    walk(db, clock, "huda", "dairy-tavern", "huda-arrives-to-open", 60)
    before = db.load(WORLD)
    with pytest.raises(InvalidEvent):
        market.post(WORLD, "tavern_host", "huda", "tavern", "stolen-cheese",
                    "cheese", 1, "coin_copper", 1, expected_revision=_rev(db))
    with pytest.raises(InvalidEvent):
        market.post(WORLD, "huda", "huda", "tavern", "phantom-second-cheese",
                    "cheese", 2, "coin_copper", 1, expected_revision=_rev(db))
    with pytest.raises(InvalidEvent):
        market.post(WORLD, "huda", "tavern", "tavern", "spoof-venue",
                    "cheese", 1, "coin_copper", 1, expected_revision=_rev(db))
    assert db.verify(WORLD).to_dict() == before.to_dict()


def test_cannot_post_remote_quotes_or_double_resell_one_delivery(village):
    db, clock, market = village
    source_goods(db, clock, market)
    before = db.load(WORLD)
    with pytest.raises(InvalidEvent):
        market.post(WORLD, "huda", "huda", "tavern", "teleport-sale",
                    "cheese", 1, "coin_copper", 3, expected_revision=_rev(db))
    assert db.verify(WORLD).to_dict() == before.to_dict()
    NPCMovementService(db, clock).start(
        WORLD, "huda", "dairy-tavern", "moving-cargo",
        expected_revision=_rev(db))
    moving = db.load(WORLD)
    with pytest.raises(InvalidEvent):
        market.post(WORLD, "huda", "huda", "tavern", "mid-transit-quote",
                    "cheese", 1, "coin_copper", 3, expected_revision=_rev(db))
    assert db.verify(WORLD).to_dict() == moving.to_dict()
    clock.advance(WORLD, seconds=60, command_id="arrive-at-tavern",
                  expected_revision=_rev(db))
    post_tavern(db, market)
    walk(db, clock, "salma", "bakery-tavern", "buyer-arrives", 80)
    sale = market.buy(WORLD, "salma", "only-one-cheese-sale",
                      "tavern-cheese-quote", 1, 3, expected_revision=_rev(db)).state
    with pytest.raises(InvalidEvent):
        market.buy(WORLD, "salma", "not-a-second-cheese-sale",
                   "tavern-cheese-quote", 1, 3, expected_revision=_rev(db))
    assert db.verify(WORLD).to_dict() == sale.to_dict()


def test_time_split_cannot_change_tavern_trade_receipts_or_coin_owner(tmp_path):
    receipts = []
    for label, split in (("whole", False), ("split", True)):
        with SQLiteEventStore(tmp_path / f"{label}.sqlite") as db:
            prepare(db)
            add_orchard(db)
            add_dairy(db)
            add_tavern(db)
            clock = TimeEngine(db)
            clock.open_session(WORLD)
            market = NPCMarketService(db, clock)
            s = resale(db, clock, market, split=split)
            receipts.append((
                s.time,
                s.resources,
                s.market_trades,
                {key: v["status"] for key, v in s.market_offers.items()},
            ))
            assert db.verify(WORLD).to_dict() == s.to_dict()
    assert receipts[0] == receipts[1], "sale receipts/owned coins must be partition-stable"
