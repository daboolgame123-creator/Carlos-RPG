"""PLAY49-B: real finite milk -> cheese in a third independent local market."""
import pytest
from carlos_sim import DomainEvent, SQLiteEventStore, TimeEngine, NPCMarketService, NPCMovementService, NPCProductionService
from carlos_sim.store import InvalidEvent
from test_market_02c import ev, prepare, _rev
from test_play49_fruit_stall_contract import WORLD, add_orchard, harvest, pay, copper

def add_dairy(db):
    before = db.load(WORLD)
    events = [
        ev("LocationCreated", {"id": "dairy", "name": "Dairy"}),
        ev("RouteCreated", {"id": "orchard-dairy", "a": "orchard", "b": "dairy", "seconds": 70}),
    ]
    for who, role in (("cheese_maker", "cheesemaker"), ("cheese_seller", "merchant")):
        events += [
            ev("EntityCreated", {"id": who, "name": who, "location_id": "dairy", "controller": "npc"}),
            ev("NPCConfigured", {"npc_id": who, "role": role,
                "needs": {"hunger": 20, "fatigue": 0, "safety": 0},
                "goals": {"earn": 50, "explore": 10, "survive": 30}}),
        ]
    for owner, resource, quantity in (
        ("dairy", "milk", 2), ("dairy", "cheese", 0),
        ("dairy", "cheese_press", 1), ("dairy", "coin_copper", 1),
        ("cheese_maker", "coin_copper", 0), ("cheese_seller", "coin_copper", 0),
        ("salma", "cheese", 0),
    ):
        events.append(ev("ResourceChanged", {
            "owner_id": owner, "resource": resource, "previous": None,
            "current": quantity, "source": "initialization"}))
    events += [
        ev("ProductionRecipeConfigured", {
            "id": "milk-to-cheese", "site_id": "dairy", "role": "cheesemaker",
            "input_resource": "milk", "input_amount": 2,
            "output_resource": "cheese", "output_amount": 1,
            "tool_resource": "cheese_press", "duration_seconds": 180, "wage_coin": 1}),
        ev("MarketStallConfigured", {"site_id": "dairy", "keeper_id": "cheese_seller"}),
    ]
    after = db.append(WORLD, "dairy:finite-genesis", before.revision, events, bootstrap=True)
    assert len(after.market_stalls) == 3
    assert after.resources["bakery"] == before.resources["bakery"]
    assert after.resources["orchard"] == before.resources["orchard"]
    assert after.resources["salma"]["coin_copper"] == before.resources["salma"]["coin_copper"]
    assert after.resources["dairy"]["milk"] == 2 and after.resources["dairy"]["cheese"] == 0
    assert copper(after) == copper(before) + 1  # declared employer opening capital
    assert db.verify(WORLD).to_dict() == after.to_dict()

@pytest.fixture
def village(tmp_path):
    with SQLiteEventStore(tmp_path / "play49-three-market.sqlite") as db:
        prepare(db)
        add_orchard(db)
        add_dairy(db)
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            yield db, clock, NPCMarketService(db, clock)
        finally:
            clock.close_session(WORLD)

def produce(db, clock):
    NPCProductionService(db, clock).start(
        WORLD, "cheese_maker", "milk-to-cheese", "cheese-batch", expected_revision=_rev(db))
    harvest(db, clock)  # original orchard fruit + bakery at 90/120 seconds
    s = db.load(WORLD)
    assert s.time == 120 and s.resources["dairy"]["milk"] == 0
    clock.advance(WORLD, seconds=60, command_id="dairy:complete180", expected_revision=_rev(db))
    s = db.load(WORLD)
    assert s.time == 180 and s.production_jobs["cheese-batch"]["status"] == "completed"
    assert s.resources["dairy"]["cheese"] == 1

def pay_both(db):
    pay(db)  # existing real fruit work salary
    s = db.load(WORLD)
    result = db.append(WORLD, "dairy:paid", s.revision, [
        DomainEvent("ProductionWagePaid", None, "one completed signed cheese job",
                    s.time, {"job_id": "cheese-batch", "amount": 1})], production_authorized=True)
    assert result.resources["dairy"]["coin_copper"] == 0
    assert result.resources["cheese_maker"]["coin_copper"] == 1
    assert result.resources["fruit_farmer"]["coin_copper"] == 1

def post_three(db, market):
    for seller, owner, resource, quantity, price, key in (
        ("adel", "bakery", "bread", 2, 3, "bread-quote"),
        ("fruit_seller", "orchard", "fruit", 1, 1, "fruit-quote"),
        ("cheese_seller", "dairy", "cheese", 1, 2, "cheese-quote"),
    ):
        market.post(WORLD, seller, owner, owner, key, resource, quantity,
                    "coin_copper", price, expected_revision=_rev(db))

def walk(db, clock, road, name, duration):
    NPCMovementService(db, clock).start(WORLD, "salma", road, name, expected_revision=_rev(db))
    clock.advance(WORLD, seconds=duration, command_id=name+":arrived", expected_revision=_rev(db))

def test_three_market_real_work_two_road_trips_and_conserved_currency(village):
    db, clock, market = village
    opening = db.load(WORLD)
    produce(db, clock)
    pay_both(db)
    post_three(db, market)
    assert {o["offer_id"] for o in market.local_quotes(WORLD, "salma")} == {"bread-quote"}
    assert {o["offer_id"] for o in market.local_quotes(WORLD, "fruit_seller")} == {"fruit-quote"}
    assert {o["offer_id"] for o in market.local_quotes(WORLD, "cheese_seller")} == {"cheese-quote"}
    market.buy(WORLD, "salma", "bread-sale", "bread-quote", 1, 3, expected_revision=_rev(db))
    walk(db, clock, "bakery-orchard", "bakery-to-orchard", 50)
    market.buy(WORLD, "salma", "fruit-sale", "fruit-quote", 1, 1, expected_revision=_rev(db))
    walk(db, clock, "orchard-dairy", "orchard-to-dairy", 70)
    assert {o["offer_id"] for o in market.local_quotes(WORLD, "salma")} == {"cheese-quote"}
    s = market.buy(WORLD, "salma", "cheese-sale", "cheese-quote", 1, 2, expected_revision=_rev(db)).state
    assert s.resources["salma"]["bread"] == s.resources["salma"]["fruit"] == s.resources["salma"]["cheese"] == 1
    assert s.resources["salma"]["coin_copper"] == opening.resources["salma"]["coin_copper"] - 6
    assert s.resources["bakery"]["coin_copper"] == 3
    assert s.resources["orchard"]["coin_copper"] == 1
    assert s.resources["dairy"]["coin_copper"] == 2
    assert s.resources["cheese_maker"]["coin_copper"] == s.resources["fruit_farmer"]["coin_copper"] == 1
    assert s.resources["dairy"]["milk"] == s.resources["dairy"]["cheese"] == 0
    assert set(s.market_trades) == {"bread-sale", "fruit-sale", "cheese-sale"}
    assert s.market_trades["cheese-sale"]["site_id"] == "dairy"
    assert copper(s) == copper(opening)
    assert not s.consumptions  # no invented nutritional effects from fruit/cheese
    assert db.verify(WORLD).to_dict() == s.to_dict()
    db.snapshot(WORLD)
    assert db.verify(WORLD).to_dict() == s.to_dict()
    assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    assert not db.db.execute("PRAGMA foreign_key_check").fetchall()

def test_no_remote_purchase_or_sale_while_in_transit(village):
    db, clock, market = village
    produce(db, clock)
    post_three(db, market)
    old = db.load(WORLD)
    for name, price in (("fruit-quote", 1), ("cheese-quote", 2)):
        with pytest.raises(InvalidEvent):
            market.buy(WORLD, "salma", "remote-"+name, name, 1, price, expected_revision=_rev(db))
    assert db.verify(WORLD).to_dict() == old.to_dict()
    NPCMovementService(db, clock).start(WORLD, "salma", "bakery-orchard",
                                         "in-transit", expected_revision=_rev(db))
    walking = db.load(WORLD)
    with pytest.raises(InvalidEvent):
        market.buy(WORLD, "salma", "no-teleport", "fruit-quote", 1, 1, expected_revision=_rev(db))
    assert db.verify(WORLD).to_dict() == walking.to_dict()
    clock.advance(WORLD, seconds=50, command_id="arrive-at-orchard", expected_revision=_rev(db))
    at_orchard = db.load(WORLD)
    with pytest.raises(InvalidEvent):
        market.buy(WORLD, "salma", "dairy-still-remote", "cheese-quote", 1, 2, expected_revision=_rev(db))
    assert db.verify(WORLD).to_dict() == at_orchard.to_dict()

def test_no_infinite_cheese_no_unauthorized_owner_or_nonexistent_stock(village):
    db, clock, market = village
    before = db.load(WORLD)
    with pytest.raises(InvalidEvent):
        market.post(WORLD, "cheese_seller", "dairy", "dairy", "imaginary",
                    "cheese", 1, "coin_copper", 2, expected_revision=_rev(db))
    assert db.verify(WORLD).to_dict() == before.to_dict()
    produce(db, clock)
    with pytest.raises(InvalidEvent):
        NPCProductionService(db, clock).start(WORLD, "cheese_maker", "milk-to-cheese",
                                               "no-milk-again", expected_revision=_rev(db))
    before = db.load(WORLD)
    with pytest.raises(InvalidEvent):
        market.post(WORLD, "cheese_seller", "dairy", "dairy", "oversell",
                    "cheese", 2, "coin_copper", 1, expected_revision=_rev(db))
    with pytest.raises(InvalidEvent):
        market.post(WORLD, "fruit_seller", "dairy", "dairy", "forged-owner",
                    "cheese", 1, "coin_copper", 1, expected_revision=_rev(db))
    assert db.verify(WORLD).to_dict() == before.to_dict()

def test_cheese_employer_cannot_pay_unearned_forged_or_duplicate_wages(village):
    db, clock, market = village
    s = db.load(WORLD)
    with pytest.raises(InvalidEvent):
        db.append(WORLD, "dairy:fake-job", s.revision, [
            DomainEvent("ProductionWagePaid", None, "unearned", 0,
                        {"job_id": "cheese-batch", "amount": 1})], production_authorized=True)
    produce(db, clock)
    s = db.load(WORLD)
    with pytest.raises(InvalidEvent):
        db.append(WORLD, "dairy:inflated", s.revision, [
            DomainEvent("ProductionWagePaid", None, "inflated", s.time,
                        {"job_id": "cheese-batch", "amount": 2})], production_authorized=True)
    with pytest.raises(InvalidEvent):
        db.append(WORLD, "dairy:untrusted", s.revision, [
            DomainEvent("ProductionWagePaid", None, "untrusted", s.time,
                        {"job_id": "cheese-batch", "amount": 1})])
    assert db.verify(WORLD).to_dict() == s.to_dict()
    pay_both(db)
    paid = db.load(WORLD)
    with pytest.raises(InvalidEvent):
        db.append(WORLD, "dairy:double-pay", paid.revision, [
            DomainEvent("ProductionWagePaid", None, "duplicate", paid.time,
                        {"job_id": "cheese-batch", "amount": 1})], production_authorized=True)
    assert db.verify(WORLD).to_dict() == paid.to_dict()
