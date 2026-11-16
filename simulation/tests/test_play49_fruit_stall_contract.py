"""PLAY49-A: independent physical fruit market, not PLAY48 economic fix."""
import pytest
from carlos_sim import (DomainEvent, SQLiteEventStore, TimeEngine,
                       NPCMarketService, NPCMovementService, NPCProductionService)
from carlos_sim.store import InvalidEvent
from test_market_02c import prepare, ev, _bake, _rev

WORLD = "village"


def copper(s):
    return sum(v.get("coin_copper", 0) for v in s.resources.values())


def add_orchard(db, *, ready_stock=1):
    old = db.load(WORLD)
    actions = [
        ev("LocationCreated", {"id": "orchard", "name": "Fruit Orchard"}),
        ev("RouteCreated", {"id": "bakery-orchard", "a": "bakery", "b": "orchard", "seconds": 50}),
    ]
    for person, role in (("fruit_farmer", "farmer"), ("fruit_seller", "merchant")):
        actions += [
            ev("EntityCreated", {"id": person, "name": person, "location_id": "orchard", "controller": "npc"}),
            ev("NPCConfigured", {"npc_id": person, "role": role,
                                 "needs": {"hunger": 20, "fatigue": 0, "safety": 0},
                                 "goals": {"earn": 50, "explore": 10, "survive": 30}}),
        ]
    for owner, resource, amount in (
        ("orchard", "fruit_ready", ready_stock), ("orchard", "fruit", 0),
        ("orchard", "fruit_basket", 1), ("orchard", "coin_copper", 1),
        ("fruit_farmer", "coin_copper", 0), ("fruit_seller", "coin_copper", 0),
        ("salma", "fruit", 0),
    ):
        actions.append(ev("ResourceChanged", {
            "owner_id": owner, "resource": resource, "previous": None,
            "current": amount, "source": "initialization"}))
    actions += [
        ev("ProductionRecipeConfigured", {
            "id": "fruit-picking", "site_id": "orchard", "role": "farmer",
            "input_resource": "fruit_ready", "input_amount": 1,
            "output_resource": "fruit", "output_amount": 1,
            "tool_resource": "fruit_basket", "duration_seconds": 120,
            "wage_coin": 1}),
        ev("MarketStallConfigured", {"site_id": "orchard", "keeper_id": "fruit_seller"}),
    ]
    s = db.append(WORLD, "fruit:bootstrap", old.revision, actions, bootstrap=True)
    assert s.resources["bakery"] == old.resources["bakery"]
    assert s.resources["salma"]["coin_copper"] == old.resources["salma"]["coin_copper"]
    assert copper(s) == copper(old) + 1  # explicitly funded orchard capital
    assert s.resources["orchard"]["fruit"] == 0 and len(s.market_stalls) == 2
    assert db.verify(WORLD).to_dict() == s.to_dict()


@pytest.fixture
def world(tmp_path):
    with SQLiteEventStore(tmp_path / "fruit.sqlite") as db:
        prepare(db)
        add_orchard(db)
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            yield db, clock, NPCMarketService(db, clock)
        finally:
            clock.close_session(WORLD)


def harvest(db, clock):
    NPCProductionService(db, clock).start(
        WORLD, "fruit_farmer", "fruit-picking", "fruit-batch",
        expected_revision=_rev(db))
    _bake(db, clock)
    clock.advance(WORLD, seconds=30, command_id="fruit:finish120",
                  expected_revision=_rev(db))
    s = db.load(WORLD)
    assert s.time == 120
    assert s.production_jobs["fruit-batch"]["status"] == "completed"
    assert s.resources["orchard"]["fruit_ready"] == s.production_jobs["fruit-batch"]["input_after"]
    assert s.resources["orchard"]["fruit"] == 1
    return s


def pay(db):
    s = db.load(WORLD)
    result = db.append(WORLD, "fruit:earned-wage", s.revision, [
        DomainEvent("ProductionWagePaid", None, "completed local fruit work",
                    s.time, {"job_id": "fruit-batch", "amount": 1})
    ], production_authorized=True)
    assert result.resources["orchard"]["coin_copper"] == 0
    assert result.resources["fruit_farmer"]["coin_copper"] == 1
    return result


def test_real_two_market_sales_local_travel_wage_and_replay(world):
    db, clock, market = world
    opening = db.load(WORLD)
    harvest(db, clock)
    pay(db)
    market.post(WORLD, "adel", "bakery", "bakery", "bread-quote",
                "bread", 2, "coin_copper", 3, expected_revision=_rev(db))
    market.post(WORLD, "fruit_seller", "orchard", "orchard", "fruit-quote",
                "fruit", 1, "coin_copper", 1, expected_revision=_rev(db))
    assert {x["offer_id"] for x in market.local_quotes(WORLD, "salma")} == {"bread-quote"}
    assert {x["offer_id"] for x in market.local_quotes(WORLD, "fruit_seller")} == {"fruit-quote"}
    before = db.load(WORLD)
    with pytest.raises(InvalidEvent):
        market.buy(WORLD, "salma", "remote", "fruit-quote", 1, 1,
                   expected_revision=_rev(db))
    assert db.verify(WORLD).to_dict() == before.to_dict()
    market.buy(WORLD, "salma", "bread-purchase", "bread-quote", 1, 3,
               expected_revision=_rev(db))
    NPCMovementService(db, clock).start(
        WORLD, "salma", "bakery-orchard", "fruit-walk",
        expected_revision=_rev(db))
    clock.advance(WORLD, seconds=50, command_id="fruit:physical-arrival",
                  expected_revision=_rev(db))
    assert {x["offer_id"] for x in market.local_quotes(WORLD, "salma")} == {"fruit-quote"}
    sold = market.buy(WORLD, "salma", "fruit-purchase", "fruit-quote", 1, 1,
                      expected_revision=_rev(db)).state
    assert sold.resources["orchard"]["fruit"] == 0
    assert sold.resources["salma"]["fruit"] == 1
    assert sold.resources["fruit_farmer"]["coin_copper"] == 1
    assert sold.resources["orchard"]["coin_copper"] == 1
    assert sold.resources["salma"]["coin_copper"] == opening.resources["salma"]["coin_copper"] - 4
    assert sold.market_trades["fruit-purchase"]["site_id"] == "orchard"
    assert sold.market_trades["bread-purchase"]["site_id"] == "bakery"
    assert copper(sold) == copper(opening)
    assert len(sold.consumptions) == 0  # fruit is not magically edible 'food'
    assert db.verify(WORLD).to_dict() == sold.to_dict()
    db.snapshot(WORLD)
    assert db.verify(WORLD).to_dict() == sold.to_dict()
    assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)


def test_no_free_fruit_no_oversell_and_no_owner_impersonation(world):
    db, clock, market = world
    original = db.load(WORLD)
    with pytest.raises(InvalidEvent):
        market.post(WORLD, "fruit_seller", "orchard", "orchard", "impossible",
                    "fruit", 1, "coin_copper", 1, expected_revision=_rev(db))
    assert db.verify(WORLD).to_dict() == original.to_dict()
    harvest(db, clock)
    with pytest.raises(InvalidEvent):
        market.post(WORLD, "fruit_seller", "orchard", "orchard", "oversell",
                    "fruit", 2, "coin_copper", 1, expected_revision=_rev(db))
    market.post(WORLD, "fruit_seller", "orchard", "orchard", "one-fruit",
                "fruit", 1, "coin_copper", 1, expected_revision=_rev(db))
    original = db.load(WORLD)
    with pytest.raises(InvalidEvent):
        market.post(WORLD, "adel", "orchard", "orchard", "forged-seller",
                    "fruit", 1, "coin_copper", 1, expected_revision=_rev(db))
    assert db.verify(WORLD).to_dict() == original.to_dict()


def test_unearned_untrusted_and_duplicate_cash_wage_rejected(world):
    db, clock, market = world
    initial = db.load(WORLD)
    with pytest.raises(InvalidEvent):
        db.append(WORLD, "fruit:forged-pre-harvest", initial.revision, [
            DomainEvent("ProductionWagePaid", None, "unearned", 0,
                        {"job_id": "fruit-batch", "amount": 1})],
            production_authorized=True)
    harvest(db, clock)
    before = db.load(WORLD)
    with pytest.raises(InvalidEvent):
        db.append(WORLD, "fruit:untrusted", before.revision, [
            DomainEvent("ProductionWagePaid", None, "untrusted", before.time,
                        {"job_id": "fruit-batch", "amount": 1})])
    assert db.verify(WORLD).to_dict() == before.to_dict()
    after = pay(db)
    with pytest.raises(InvalidEvent):
        db.append(WORLD, "fruit:duplicate", after.revision, [
            DomainEvent("ProductionWagePaid", None, "duplicate", after.time,
                        {"job_id": "fruit-batch", "amount": 1})],
            production_authorized=True)
    assert db.verify(WORLD).to_dict() == after.to_dict()
