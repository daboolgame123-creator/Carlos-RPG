"""04-A/J1a: seven-NPC historical ownership provenance, not a court."""
import pytest

from carlos_sim import DomainEvent, SQLiteEventStore, TimeEngine, NPCPropertyService, NPCMarketService
from carlos_sim.domain import WorldState
from carlos_sim.rights import origin_history
from carlos_sim.store import InvalidEvent
from test_property_02h1 import village


def origin(ident="origin-bread", source="bakery", beneficiary="bakery",
           quantity=2, resource="bread", site="bakery"):
    return DomainEvent("PropertyTitleOriginRegistered", None, "trusted zero-time origin", 0, {
        "id": ident, "source_owner_id": source,
        "recorded_beneficiary_id": beneficiary,
        "quantity": quantity, "resource": resource, "site_id": site,
    })


@pytest.fixture
def scene(tmp_path):
    with SQLiteEventStore(tmp_path / "origin.sqlite") as db:
        village(db)
        clock = TimeEngine(db)
        clock.open_session("v")
        yield db, clock


def register(db, events):
    return db.append("v", "origin:" + str(db.load("v").revision),
                     db.load("v").revision, events, bootstrap=True)


def test_original_title_record_is_distinct_from_possession_after_taking(scene):
    db, clock = scene
    old = db.load("v")
    recorded = register(db, [origin()])
    assert recorded.resources == old.resources
    assert recorded.property_title_origins["origin-bread"]["record_kind"] == "historical_origin_only"
    assert len(origin_history(recorded)) == 1
    taken = NPCPropertyService(db, clock).take(
        "v", "basim", "taking1", "bakery", "bakery", "bread", 1,
        expected_revision=db.load("v").revision).state
    assert taken.resources["bakery"]["bread"] == 1
    assert taken.resources["basim"]["bread"] == 1
    assert taken.property_title_origins == recorded.property_title_origins
    assert db.verify("v").to_dict() == taken.to_dict()


def test_trade_changes_stock_without_relabeling_historical_right(scene):
    db, clock = scene
    register(db, [origin()])
    market = NPCMarketService(db, clock)
    market.post("v", "adel", "bakery", "bakery", "offer1",
                "bread", 2, "coin_copper", 2,
                expected_revision=db.load("v").revision)
    sold = market.buy("v", "salma", "trade1", "offer1", 1, 2,
                      expected_revision=db.load("v").revision).state
    assert sold.resources["salma"]["bread"] == 1
    assert sold.resources["bakery"]["bread"] == 1
    assert sold.property_title_origins["origin-bread"]["recorded_beneficiary_id"] == "bakery"
    assert db.verify("v").to_dict() == sold.to_dict()


@pytest.mark.parametrize("changes", [
    {"quantity": 3}, {"quantity": 0}, {"quantity": True},
    {"resource": "coin_copper"}, {"resource": "wild_food"},
    {"source": "ghost"}, {"beneficiary": "basim"},
    {"site": "square"}, {"source": "basim", "beneficiary": "bakery"},
])
def test_invalid_origin_rejected_without_stock_or_record_mutation(scene, changes):
    db, _ = scene
    old = db.load("v").to_dict()
    with pytest.raises(InvalidEvent):
        register(db, [origin(**changes)])
    assert db.load("v").to_dict() == old


def test_overlap_cannot_mint_more_entitlement_than_registered_stock(scene):
    db, _ = scene
    register(db, [origin("r1", quantity=2)])
    old = db.load("v").to_dict()
    with pytest.raises(InvalidEvent):
        register(db, [origin("r2", quantity=1)])
    assert db.load("v").to_dict() == old


def test_forged_origin_without_bootstrap_rejected(scene):
    db, _ = scene
    old = db.load("v").to_dict()
    with pytest.raises(InvalidEvent):
        db.append("v", "forged", db.load("v").revision, [origin()])
    assert db.load("v").to_dict() == old


def test_snapshot_cannot_forge_origin_record_shape(scene):
    db, _ = scene
    register(db, [origin()])
    data = db.load("v").to_dict()
    data["property_title_origins"]["origin-bread"]["record_kind"] = "current_legal_owner"
    with pytest.raises(ValueError):
        WorldState.from_dict(data)


def test_same_command_batch_failure_rolls_back_origin(scene):
    db, _ = scene
    original = db.load("v").to_dict()
    with pytest.raises(InvalidEvent):
        register(db, [origin("r1", quantity=2), origin("r2", quantity=2)])
    assert db.load("v").to_dict() == original


def test_money_is_excluded_from_physical_title_origin(scene):
    db, _ = scene
    old = db.load("v").to_dict()
    with pytest.raises(InvalidEvent):
        register(db, [origin("money", "nora", "nora", 1, "coin_copper")])
    assert db.load("v").to_dict() == old


def test_forged_second_valid_shaped_origin_cannot_overallocate_snapshot(scene):
    db, _ = scene
    register(db, [origin()])
    old = db.load("v").to_dict()
    second = dict(old["property_title_origins"]["origin-bread"])
    old["property_title_origins"]["invented"] = second
    with pytest.raises(ValueError, match="overlapping"):
        WorldState.from_dict(old)


def test_historical_balance_provenance_survives_when_stock_depleted(scene):
    db, clock = scene
    register(db, [origin()])
    svc = NPCPropertyService(db, clock)
    svc.take("v", "basim", "t1", "bakery", "bakery", "bread", 1,
             expected_revision=db.load("v").revision)
    svc.take("v", "nora", "t2", "bakery", "bakery", "bread", 1,
             expected_revision=db.load("v").revision)
    after = db.load("v")
    assert after.resources["bakery"]["bread"] == 0
    assert after.property_title_origins["origin-bread"]["source_balance_at_registration"] == 2
    assert db.verify("v").to_dict() == after.to_dict()
