"""Phase 01-T integration tests: seven-NPC knowledge lifecycle and OBS-2."""
from __future__ import annotations

import shutil

import pytest

from carlos_sim import (DomainEvent, SQLiteEventStore, TimeEngine,
                        LivingWorldEngine, choose_action, canonical_hash)
from carlos_sim.store import InvalidEvent
from test_gathering_autonomy import make_world, NAMES
from test_navigation import setup as setup_navigation_world


def ev(kind, data, actor=None, time=0):
    return DomainEvent(kind, actor, "01-T scenario", time, data)


@pytest.fixture
def village(tmp_path):
    with SQLiteEventStore(tmp_path / "01t-scenario.sqlite") as db:
        make_world(db)
        clock = TimeEngine(db)
        clock.open_session("r")
        yield db, clock


def observe_grove_present(db, who="adel", at=0, food_state="present",
                          delivery_id="obs-grove", command_id=None):
    s = db.load("r")
    return db.append("r", command_id or ("obs:" + delivery_id), s.revision, [
        ev("NPCInformationDelivered",
           {"npc_id": who, "delivery_id": delivery_id, "key": "food:grove",
            "claim": {"text": "food-state:%s; observed_at=%d" % (food_state, at),
                      "source": "observation:grove", "received_at": at,
                      "confidence": 90},
            "sender_id": who, "location_id": "grove", "method": "observation"},
           actor=who, time=at),
        ev("NPCBeliefReceived",
           {"npc_id": who, "key": "food:grove", "delivery_id": delivery_id},
           actor=who, time=at),
    ], npc_authorized=True)


def tell_grove_hearsay(db, teller, listener, at, observed_at=0, confidence=60,
                       delivery_id="hearsay", food_state="present"):
    s = db.load("r")
    return db.append("r", "hearsay", s.revision, [
        ev("NPCInformationDelivered",
           {"npc_id": listener, "delivery_id": delivery_id, "key": "food:grove",
            "claim": {"text": "food-state:%s; observed_at=%d" % (food_state, observed_at),
                      "source": teller, "received_at": at, "confidence": confidence},
            "sender_id": teller, "location_id": "grove", "method": "message"},
           actor=teller, time=at),
        ev("NPCBeliefReceived",
           {"npc_id": listener, "key": "food:grove", "delivery_id": delivery_id},
           actor=listener, time=at),
    ], npc_authorized=True)


def test_seven_npc_lifecycle_observe_remember_hearsay_stale_empty(village):
    db, clock = village
    observe_grove_present(db, "adel", 0)
    s = db.load("r")
    assert s.npcs["adel"]["beliefs"]["food:grove"]["text"] == "food-state:present; observed_at=0"

    clock.advance("r", seconds=100, command_id="to100", expected_revision=db.load("r").revision)
    s = db.load("r")
    assert s.npcs["adel"]["beliefs"]["food:grove"]["text"] == "food-state:present; observed_at=0"

    tell_grove_hearsay(db, "adel", "basim", 100, observed_at=0, delivery_id="h1")
    s = db.load("r")
    assert s.npcs["basim"]["beliefs"]["food:grove"]["text"] == "food-state:present; observed_at=0"
    assert s.npcs["basim"]["beliefs"]["food:grove"]["confidence"] == 60

    clock.advance("r", seconds=100, command_id="to200", expected_revision=db.load("r").revision)

    # Forage to deplete grove (adel + basim collect the two units).
    LivingWorldEngine(db, clock, foraging_enabled=True,
                      knowledge_enabled=True).advance(
        "r", seconds=120, command_id="forage-deplete",
        expected_revision=db.load("r").revision)
    s = db.load("r")
    assert s.resources["grove"]["wild_food"] == 0
    assert s.time == 320

    # Direct empty observation is allowed now that real stock is zero.
    observe_grove_present(db, "adel", 320, food_state="empty", delivery_id="obs-empty")
    s = db.load("r")
    assert s.npcs["adel"]["beliefs"]["food:grove"]["text"] == "food-state:empty; observed_at=320"

    # Time passes beyond the 1800s protection window.
    clock.advance("r", seconds=1900, command_id="to2220", expected_revision=db.load("r").revision)
    s = db.load("r")
    assert s.npcs["adel"]["beliefs"]["food:grove"]["text"] == "food-state:empty; observed_at=320"


def test_verify_snapshot_reopen_and_rerun_preserve_hash(village, tmp_path):
    db, clock = village
    observe_grove_present(db, "adel", 0)
    clock.advance("r", seconds=60, command_id="t60", expected_revision=db.load("r").revision)
    s1 = db.load("r")
    h1 = canonical_hash(s1.to_dict())
    db.verify("r")
    db.snapshot("r")

    path = tmp_path / "01t-reopen.sqlite"
    shutil.copy(tmp_path / "01t-scenario.sqlite", path)
    with SQLiteEventStore(path) as db2:
        s2 = db2.load("r")
        assert canonical_hash(s2.to_dict()) == h1
        assert db2.verify("r").to_dict() == s2.to_dict()


@pytest.mark.parametrize(
    ("site_stock", "expected_food_state"),
    [(None, None), (0, "empty"), (3, "present")],
)
def test_autonomous_navigation_arrival_observes_only_initialized_local_food(
        tmp_path, site_stock, expected_food_state):
    # Routes use a completely different scheduled payload from NPC actions.
    # This exercises the actual end-to-end travel-completion hook.
    with SQLiteEventStore(tmp_path / "01t-arrival.sqlite") as db:
        setup_navigation_world(db)
        if site_stock is not None:
            before = db.load("village")
            db.append("village", "initialize-forest-food", before.revision, [
                DomainEvent("ResourceChanged", None, "initialize distant food", 0, {
                    "owner_id": "forest", "resource": "wild_food",
                    "previous": None, "current": site_stock,
                    "source": "initialization",
                })
            ], bootstrap=True)
        clock = TimeEngine(db)
        clock.open_session("village")
        result = LivingWorldEngine(
            db, clock, navigation_enabled=True, knowledge_enabled=True
        ).advance("village", seconds=50, command_id="arrive-forest",
                  expected_revision=db.load("village").revision)
        state = result.state
        assert state.entities["nora"]["location_id"] == "forest"
        claim = state.npcs["nora"]["beliefs"].get("food:forest")
        if expected_food_state is None:
            assert claim is None  # unknown is not "empty"
            assert result.knowledge_shares == ()
        else:
            assert claim is not None
            assert claim["text"] == (
                f"food-state:{expected_food_state}; observed_at=50"
            )
            assert claim["source"] == "observation:forest"
            assert claim["received_at"] == 50
            delivery_id = "food-obs:nora:forest:50:arrival"
            assert state.npcs["nora"]["delivery_history"].count(delivery_id) == 1
            assert result.knowledge_shares.count(delivery_id) == 1
        assert db.verify("village").to_dict() == state.to_dict()


def test_autonomous_arrival_event_budget_rolls_back_entire_command(tmp_path):
    # A newly reached site has food and would produce delivery+ack after the
    # scheduled travel signal. Exhaust the event budget mid-lifecycle: none of
    # the already simulated in-memory events may reach SQLite.
    from carlos_sim.time_engine import AdvanceLimitExceeded

    with SQLiteEventStore(tmp_path / "01t-arrival-budget.sqlite") as db:
        setup_navigation_world(db)
        s = db.load("village")
        db.append("village", "stock-for-budget", s.revision, [
            DomainEvent("ResourceChanged", None, "seed forest stock", 0, {
                "owner_id": "forest", "resource": "wild_food",
                "previous": None, "current": 2,
                "source": "initialization",
            })
        ], bootstrap=True)
        clock = TimeEngine(db)
        clock.open_session("village")
        initial = db.load("village").to_dict()
        prior_events = db.db.execute(
            "SELECT count(*) FROM events WHERE world_id='village'"
        ).fetchone()[0]
        with pytest.raises(AdvanceLimitExceeded, match="event budget"):
            LivingWorldEngine(
                db, clock, navigation_enabled=True, knowledge_enabled=True,
                max_events_per_advance=6,
            ).advance("village", seconds=50, command_id="arrive-with-low-budget",
                      expected_revision=db.load("village").revision)
        assert db.load("village").to_dict() == initial
        assert db.db.execute(
            "SELECT count(*) FROM events WHERE world_id='village'"
        ).fetchone()[0] == prior_events
        assert db.verify("village").to_dict() == initial


def test_session_close_blocks_npc_state_changes(village):
    db, clock = village
    s = db.load("r")
    rev = s.revision
    # A *valid* local direct observation: otherwise a malformed event could
    # fail for reasons other than the intended closed-session gate.
    delivery = ev("NPCInformationDelivered",
                  {"npc_id": "adel", "delivery_id": "x", "key": "food:grove",
                   "claim": {"text": "food-state:present; observed_at=0",
                             "source": "observation:grove", "received_at": 0,
                             "confidence": 90},
                   "sender_id": "adel", "location_id": "grove", "method": "observation"},
                  actor="adel", time=0)
    clock.close_session("r")
    with pytest.raises(InvalidEvent, match="active play session"):
        db.append("r", "after-close", rev, [delivery], npc_authorized=True)
    assert db.load("r").to_dict() == s.to_dict()
    assert db.db.execute(
        "SELECT count(*) FROM events WHERE world_id='r'"
    ).fetchone()[0] == rev

    # Control: the identical event and command succeed once the session is
    # reopened, proving only the play-session boundary blocked the write.
    clock.open_session("r")
    after = db.append("r", "after-close", rev, [delivery], npc_authorized=True)
    assert after.revision == rev + 1
    assert "x" in after.npcs["adel"]["inbox"]
    db.verify("r")


def test_per_npc_independence_only_listener_changes(village):
    db, clock = village
    before = db.load("r").to_dict()
    observe_grove_present(db, "adel", 0, delivery_id="obs-ind")
    after = db.load("r").to_dict()
    assert after["npcs"]["basim"]["beliefs"] == before["npcs"]["basim"]["beliefs"]
    assert after["npcs"]["omar"]["beliefs"] == before["npcs"]["omar"]["beliefs"]
    assert after["npcs"]["adel"]["beliefs"]["food:grove"]["text"] == "food-state:present; observed_at=0"


def test_knowledge_does_not_move_next_decision_at(village):
    db, clock = village
    observe_grove_present(db, "adel", 0)
    s = db.load("r")
    before_nda = s.npcs["adel"]["next_decision_at"]
    clock.advance("r", seconds=60, command_id="t60", expected_revision=s.revision)
    s = db.load("r")
    assert s.npcs["adel"]["next_decision_at"] == before_nda


def test_obs2_forage_timing_identical_flag_on_and_off(tmp_path):
    def run(knowledge_enabled):
        with SQLiteEventStore(tmp_path / ("obs2-%s.sqlite" % knowledge_enabled)) as db:
            make_world(db)
            clock = TimeEngine(db)
            clock.open_session("r")
            result = LivingWorldEngine(db, clock, foraging_enabled=True,
                                       knowledge_enabled=knowledge_enabled).advance(
                "r", seconds=120, command_id="go",
                expected_revision=db.load("r").revision)
            return result.state

    off = run(False)
    on = run(True)
    assert off.foraging_attempts == on.foraging_attempts
    assert off.time == on.time == 120
    for name in NAMES:
        assert off.npcs[name]["next_decision_at"] == on.npcs[name]["next_decision_at"]


def test_decision_cooldown_spacing_unchanged_by_knowledge(village, tmp_path):
    def nda_map(knowledge_enabled):
        with SQLiteEventStore(tmp_path / ("cooldown-%s.sqlite" % knowledge_enabled)) as db:
            make_world(db)
            clock = TimeEngine(db)
            clock.open_session("r")
            result = LivingWorldEngine(db, clock, foraging_enabled=True,
                                       knowledge_enabled=knowledge_enabled).advance(
                "r", seconds=120, command_id="go",
                expected_revision=db.load("r").revision)
            return {n: (p["last_decision"]["at"] if p["last_decision"] else None,
                        p["next_decision_at"])
                    for n, p in result.state.npcs.items()}

    off = nda_map(False)
    on = nda_map(True)
    # Knowledge must not stretch or shrink the 60s decision cooldown for any NPC.
    for name in NAMES:
        assert on[name] == off[name], (name, on[name], off[name])
        last, nda = on[name]
        if last is not None:
            assert nda - last == 60
