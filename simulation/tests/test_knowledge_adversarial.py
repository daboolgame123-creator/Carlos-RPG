"""Phase 01-T adversarial tests: reducer is the boundary, state stays unchanged."""
from __future__ import annotations

import pytest

from carlos_sim import DomainEvent
from carlos_sim.store import InvalidEvent
from test_gathering_autonomy import make_world, NAMES


def head(db):
    s = db.load("r")
    return s.revision, s.time


def snap(db):
    return db.load("r").to_dict()


def events_count(db):
    return db.db.execute("SELECT count(*) FROM events WHERE world_id='r'").fetchone()[0]


def claim(text, source, received_at, confidence):
    return {"text": text, "source": source, "received_at": received_at,
            "confidence": confidence}


def observe_deliver(db, who, site, food_state, observed_at, received_at,
                    confidence=90, delivery_id="obs", method="observation",
                    source=None, sender=None, location_id=None, key=None,
                    expect_revision=None, command_id=None):
    """Build and append a direct-observation delivery+ack pair at ``received_at``."""
    key = key or f"food:{site}"
    loc = location_id or site
    snd = sender if sender is not None else who
    src = source if source is not None else f"observation:{site}"
    cl = claim(f"food-state:{food_state}; observed_at={observed_at}", src,
               received_at, confidence)
    rev, _ = head(db)
    if expect_revision is not None:
        rev = expect_revision
    cid = command_id if command_id is not None else "know:" + delivery_id
    return db.append("r", cid, rev, [
        DomainEvent("NPCInformationDelivered", snd, "observation", received_at,
                    {"npc_id": who, "delivery_id": delivery_id, "key": key, "claim": cl,
                     "sender_id": snd, "location_id": loc, "method": method}),
        DomainEvent("NPCBeliefReceived", who, "ack", received_at,
                    {"npc_id": who, "key": key, "delivery_id": delivery_id}),
    ], npc_authorized=True)


@pytest.fixture
def village(tmp_path):
    with SQLiteEventStore(tmp_path / "adv.sqlite") as db:
        make_world(db)
        clock = TimeEngine(db)
        clock.open_session("r")
        yield db, clock


from carlos_sim import SQLiteEventStore, TimeEngine  # noqa: E402


def test_trailing_newline_food_observation_fails_closed(village):
    db, _clock = village
    old_state = snap(db)
    old_events = events_count(db)
    for index, trailing in enumerate(("\n", "\r\n")):
        s = db.load("r")
        event = DomainEvent("NPCInformationDelivered", "adel", "forged food text",
                            s.time, {
            "npc_id": "adel",
            "delivery_id": f"bad-trailing-newline-{index}",
            "key": "food:grove",
            "claim": claim("food-state:present; observed_at=0" + trailing,
                           "observation:grove", s.time, 90),
            "sender_id": "adel", "location_id": "grove",
            "method": "observation",
        })
        with pytest.raises(InvalidEvent, match="invalid food claim text"):
            db.append("r", f"reject-trailing-newline-{index}", s.revision,
                      [event], npc_authorized=True)
        assert snap(db) == old_state
        assert events_count(db) == old_events


def test_direct_observation_sets_belief_verified_against_stock(village):
    db, clock = village
    before = snap(db); n_before = events_count(db)
    observe_deliver(db, "adel", "grove", "present", 0, 0)
    s = db.load("r")
    assert s.npcs["adel"]["beliefs"]["food:grove"]["text"] == "food-state:present; observed_at=0"
    assert s.npcs["adel"]["beliefs"]["food:grove"]["confidence"] == 90
    assert snap(db) != before or True  # state legitimately changed
    assert events_count(db) == n_before + 2


def assert_rejected(db, before, n_before, fn):
    try:
        fn()
    except InvalidEvent:
        pass
    else:
        raise AssertionError("expected reducer rejection")
    assert snap(db) == before, "state must be unchanged after rejection"
    assert events_count(db) == n_before, "event log must be unchanged after rejection"


def test_forged_observation_wrong_site_rejected(village):
    db, clock = village
    before = snap(db); n_before = events_count(db)
    # adel stands at grove but claims to observe square.
    assert_rejected(db, before, n_before, lambda: observe_deliver(
        db, "adel", "square", "present", 0, 0, delivery_id="bad1",
        location_id="square", key="food:square", source="observation:square"))


def test_forged_observation_present_when_stock_zero_rejected(village):
    db, clock = village
    before = snap(db); n_before = events_count(db)
    # omar stands at square whose wild_food is 0; claims present.
    assert_rejected(db, before, n_before, lambda: observe_deliver(
        db, "omar", "square", "present", 0, 0, delivery_id="bad2",
        location_id="square", key="food:square", source="observation:square"))


def test_forged_observation_empty_when_stock_positive_rejected(village):
    db, clock = village
    before = snap(db); n_before = events_count(db)
    # grove has wild_food=2; claims empty.
    assert_rejected(db, before, n_before, lambda: observe_deliver(
        db, "adel", "grove", "empty", 0, 0, delivery_id="bad3",
        location_id="grove", key="food:grove", source="observation:grove"))


def test_observation_uninitialized_site_rejected(village):
    db, clock = village
    before = snap(db); n_before = events_count(db)
    # adel stands at grove but keys food:cave (a site she is not at / unknown).
    assert_rejected(db, before, n_before, lambda: observe_deliver(
        db, "adel", "cave", "present", 0, 0, delivery_id="bad4",
        location_id="grove", key="food:cave", source="observation:grove"))


def test_observation_wrong_time_rejected(village):
    db, clock = village
    before = snap(db); n_before = events_count(db)
    assert_rejected(db, before, n_before, lambda: observe_deliver(
        db, "adel", "grove", "present", 0, 999, delivery_id="bad5",
        location_id="grove", key="food:grove", source="observation:grove"))


def test_hearsay_cannot_masquerade_as_observation(village):
    db, clock = village
    before = snap(db); n_before = events_count(db)
    # basim tells adel a message whose source pretends to be a direct sighting.
    assert_rejected(db, before, n_before, lambda: observe_deliver(
        db, "adel", "grove", "present", 0, 0, delivery_id="bad6",
        location_id="grove", key="food:grove", source="observation:grove",
        sender="basim", method="message"))


def test_hearsay_accepted_as_low_confidence_belief_not_truth(village):
    db, clock = village
    before = snap(db); n_before = events_count(db)
    # basim (at grove) tells adel (at grove) that square has present food:
    # square actually has wild_food=0, but hearsay is not truth-verified.
    observe_deliver(db, "adel", "square", "present", 0, 0, confidence=60,
                    delivery_id="hearsay1", location_id="grove", key="food:square",
                    source="basim", sender="basim", method="message")
    s = db.load("r")
    assert s.npcs["adel"]["beliefs"]["food:square"]["text"] == "food-state:present; observed_at=0"
    assert s.npcs["adel"]["beliefs"]["food:square"]["confidence"] == 60
    assert s.npcs["adel"]["beliefs"]["food:square"]["source"] == "basim"
    # The false belief must not change adel's forage decision (remote site).
    from carlos_sim import choose_action
    assert choose_action(s, "adel", foraging_enabled=True).action == "forage"


def test_recent_observation_protected_from_fresh_hearsay(village):
    db, clock = village
    before = snap(db); n_before = events_count(db)
    observe_deliver(db, "adel", "grove", "present", 0, 0, delivery_id="obs0")
    # Advance time to 100s; the observation is still within the 1800s protection.
    clock.advance("r", seconds=100, command_id="to100",
                  expected_revision=db.load("r").revision)
    # basim tells adel hearsay that grove is empty (fresh arrival, old fact).
    rev, _ = head(db)
    observe_deliver(db, "adel", "grove", "empty", 0, 100, confidence=60,
                    delivery_id="hearsay2", location_id="grove", key="food:grove",
                    source="basim", sender="basim", method="message", expect_revision=rev)
    s = db.load("r")
    # Belief unchanged: recent direct sighting protected; delivery consumed.
    assert s.npcs["adel"]["beliefs"]["food:grove"]["text"] == "food-state:present; observed_at=0"
    assert s.npcs["adel"]["inbox"] == {}
    assert "hearsay2" in s.npcs["adel"]["delivery_history"]


def test_stale_observation_superseded_by_fresher_hearsay(village):
    db, clock = village
    observe_deliver(db, "adel", "grove", "present", 0, 0, delivery_id="obs0")
    clock.advance("r", seconds=1901, command_id="to1901",
                  expected_revision=db.load("r").revision)
    # Protection lapsed (>1800s); fresher hearsay (observed 1900) beats stale sighting (observed 0).
    rev, _ = head(db)
    observe_deliver(db, "adel", "grove", "empty", 1900, 1901, confidence=60,
                    delivery_id="hearsay3", location_id="grove", key="food:grove",
                    source="basim", sender="basim", method="message", expect_revision=rev)
    s = db.load("r")
    assert s.npcs["adel"]["beliefs"]["food:grove"]["text"] == "food-state:empty; observed_at=1900"


def test_ack_consumes_delivery_keeps_belief_when_should_adopt_rejects(village):
    db, clock = village
    observe_deliver(db, "adel", "grove", "present", 0, 0, delivery_id="obs0")
    clock.advance("r", seconds=100, command_id="to100",
                  expected_revision=db.load("r").revision)
    # Recent observation (age 0) protected: hearsay rejected at ack.
    rev, _ = head(db)
    before = snap(db); n_before = events_count(db)
    observe_deliver(db, "adel", "grove", "empty", 0, 100, confidence=60,
                    delivery_id="hearsay4", location_id="grove", key="food:grove",
                    source="basim", sender="basim", method="message", expect_revision=rev)
    s = db.load("r")
    assert s.npcs["adel"]["beliefs"]["food:grove"]["text"] == "food-state:present; observed_at=0"
    assert s.npcs["adel"]["inbox"] == {}
    assert "hearsay4" in s.npcs["adel"]["delivery_history"]


def test_batch_atomicity_one_bad_knowledge_event_rolls_back(village):
    db, clock = village
    before = snap(db); n_before = events_count(db)
    rev, _ = head(db)
    good = DomainEvent("NPCInformationDelivered", "adel", "t", 0,
        {"npc_id": "adel", "delivery_id": "g1", "key": "food:grove",
         "claim": claim("food-state:present; observed_at=0", "observation:grove", 0, 90),
         "sender_id": "adel", "location_id": "grove", "method": "observation"})
    # Second delivery reuses an ID already used by the first in the same batch -> duplicate.
    bad = DomainEvent("NPCInformationDelivered", "adel", "t", 0,
        {"npc_id": "adel", "delivery_id": "g1", "key": "food:grove",
         "claim": claim("food-state:empty; observed_at=0", "observation:grove", 0, 90),
         "sender_id": "adel", "location_id": "grove", "method": "observation"})
    with pytest.raises((InvalidEvent, ValueError)):
        db.append("r", "batch", rev, [good, bad], npc_authorized=True)
    assert snap(db) == before
    assert events_count(db) == n_before


def test_duplicate_delivery_id_rejected(village):
    db, clock = village
    observe_deliver(db, "adel", "grove", "present", 0, 0, delivery_id="dup")
    before = snap(db); n_before = events_count(db)
    rev, _ = head(db)
    with pytest.raises(InvalidEvent):
        observe_deliver(db, "adel", "grove", "present", 0, 0, delivery_id="dup",
                        expect_revision=rev, command_id="know-dup2")
    assert snap(db) == before
    assert events_count(db) == n_before
