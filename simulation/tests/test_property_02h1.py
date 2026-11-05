"""Phase 02-H1: seven-person village, physical taking and fail-closed guards."""
import pytest
from carlos_sim import (
    DomainEvent, SQLiteEventStore, TimeEngine, NPCPropertyService,
    NPCMarketService,
)
from carlos_sim.store import InvalidEvent, DuplicateCommand

PEOPLE = ("basim", "nora", "adel", "salma", "huda", "omar", "layla")


def event(name, data, actor=None):
    return DomainEvent(name, actor, "02-H1 disposable village", 0, data)


def village(db):
    db.create_world("v")
    events = [event("LocationCreated", {"id": "bakery", "name": "Bakery"}),
              event("LocationCreated", {"id": "square", "name": "Square"})]
    events.extend([
        event("ResourceChanged", {"owner_id": "bakery", "resource": "bread",
             "previous": None, "current": 2, "source": "initialization"}),
        event("ResourceChanged", {"owner_id": "bakery", "resource": "coin_copper",
             "previous": None, "current": 0, "source": "initialization"}),
    ])
    for person in PEOPLE:
        site = "square" if person == "omar" else "bakery"
        events.extend([
            event("EntityCreated", {"id": person, "name": person,
                  "location_id": site, "controller": "npc"}),
            event("NPCConfigured", {"npc_id": person, "role": "resident",
                  "needs": {"hunger": 20, "fatigue": 5, "safety": 0},
                  "goals": {"earn": 50, "explore": 10, "survive": 30}}),
            event("ResourceChanged", {"owner_id": person,
                  "resource": "bread", "previous": None, "current": 0,
                  "source": "initialization"}),
            event("ResourceChanged", {"owner_id": person,
                  "resource": "coin_copper", "previous": None, "current": 10,
                  "source": "initialization"}),
        ])
    events.append(event("MarketStallConfigured", {
        "site_id": "bakery", "keeper_id": "adel"}))
    db.append("v", "setup", 0, events, bootstrap=True)


@pytest.fixture
def setup(tmp_path):
    with SQLiteEventStore(tmp_path / "h1.sqlite") as db:
        village(db)
        clock = TimeEngine(db)
        clock.open_session("v")
        yield db, clock, NPCPropertyService(db, clock)


def take(db, service, actor="basim", source="bakery", quantity=1,
         ident="t1", site="bakery"):
    return service.take("v", actor, ident, source, site, "bread", quantity,
                        expected_revision=db.load("v").revision).state


def test_conservation_and_replay(setup):
    db, clock, service = setup
    before = db.load("v")
    after = take(db, service)
    assert after.resources["bakery"]["bread"] == 1
    assert after.resources["basim"]["bread"] == 1
    assert after.resources["bakery"]["bread"] + after.resources["basim"]["bread"] == 2
    assert after.property_takings["t1"]["permission_basis"] == "no_grant_recorded"
    assert db.verify("v").to_dict() == after.to_dict()
    assert before.property_takings == {}


@pytest.mark.parametrize("actor,source,site,quantity", [
    ("omar", "bakery", "bakery", 1),
    ("adel", "bakery", "bakery", 1),
    ("basim", "bakery", "square", 1),
    ("basim", "bakery", "bakery", 3),
    ("basim", "unknown", "bakery", 1),
    ("basim", "basim", "bakery", 1),
])
def test_rejected_takings_do_not_mutate(setup, actor, source, site, quantity):
    db, clock, service = setup
    before = db.load("v").to_dict()
    with pytest.raises(InvalidEvent):
        take(db, service, actor, source, quantity, site=site)
    assert db.load("v").to_dict() == before


def test_untrusted_event_cannot_take(setup):
    db, clock, service = setup
    before = db.load("v").to_dict()
    ev = DomainEvent("PropertyTaken", "basim", "untrusted", 0, {
        "id": "fake", "source_owner_id": "bakery", "site_id": "bakery",
        "resource": "bread", "quantity": 1})
    with pytest.raises(InvalidEvent):
        db.append("v", "bad", db.load("v").revision, [ev])
    assert db.load("v").to_dict() == before


def test_market_cannot_double_sell_stolen_loaf(setup):
    db, clock, service = setup
    market = NPCMarketService(db, clock)
    market.post("v", "adel", "bakery", "bakery", "q", "bread", 2,
                "coin_copper", 3, expected_revision=db.load("v").revision)
    take(db, service)
    market.buy("v", "salma", "sale1", "q", 1, 3,
               expected_revision=db.load("v").revision)
    before = db.load("v").to_dict()
    with pytest.raises(InvalidEvent):
        market.buy("v", "huda", "sale2", "q", 1, 3,
                   expected_revision=db.load("v").revision)
    assert db.load("v").to_dict() == before
    assert db.verify("v").to_dict() == before


def test_duplicate_identifier_does_not_transfer_twice(setup):
    db, clock, service = setup
    take(db, service)
    before = db.load("v").to_dict()
    with pytest.raises(DuplicateCommand):
        take(db, service)
    assert db.load("v").to_dict() == before
