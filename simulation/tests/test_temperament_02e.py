"""02-E opt-in, deterministic personality and grounded autobiographical memory."""
from __future__ import annotations

import pytest

from carlos_sim import (
    DomainEvent, SQLiteEventStore, TimeEngine, NPCService, NPCActionService,
    WorldState, apply_event, choose_action,
)
from carlos_sim.domain import SCHEMA_VERSION, RULES_VERSION
from carlos_sim.store import InvalidEvent, RevisionConflict
from carlos_sim.time_engine import SessionClosed

PEOPLE = ("basim", "nora", "salma", "adel", "huda", "omar", "layla")
WORKER = {"ambition": 100, "curiosity": 0, "caution": 100, "discipline": 100}
EXPLORER = {"ambition": 0, "curiosity": 100, "caution": 0, "discipline": 0}


def ev(kind, payload, who=None, at=0):
    return DomainEvent(kind, who, "02-E synthetic private temperament", at, payload)


def setup(db, *, configured=True, traits=None, members=PEOPLE,
          hunger=5, fatigue=10, earn=40, explore=45):
    db.create_world("test")
    events = [ev("LocationCreated", {"id": "square", "name": "Square"})]
    for who in members:
        events += [
            ev("EntityCreated", {"id": who, "name": who, "location_id": "square",
                                 "controller": "npc"}),
            ev("NPCConfigured", {
                "npc_id": who, "role": "resident",
                "needs": {"fatigue": fatigue, "hunger": hunger, "safety": 0},
                "goals": {"earn": earn, "explore": explore, "survive": 30},
            }),
        ]
        for kind in ("labor_units", "investigation_attempts"):
            events.append(ev("ResourceChanged", {
                "owner_id": who, "resource": kind,
                "previous": None, "current": 0, "source": "initialization",
            }))
    if configured:
        for who, values in (traits or {"basim": WORKER, "nora": EXPLORER}).items():
            events.append(ev("NPCTemperamentConfigured", {
                "npc_id": who, "traits": values,
            }))
    db.append("test", "genesis", 0, events, bootstrap=True)


@pytest.fixture
def village(tmp_path):
    with SQLiteEventStore(tmp_path / "traits.sqlite") as db:
        setup(db)
        clock = TimeEngine(db)
        clock.open_session("test")
        yield db, clock


def rev(db):
    return db.load("test").revision


def step(db, clock, seconds, cid):
    return clock.advance("test", seconds=seconds, command_id=cid,
                         expected_revision=rev(db)).state


def decide(db, clock, who, ident):
    return NPCService(db, clock).decide("test", who, command_id=ident,
                                        expected_revision=rev(db))


def test_schema_and_default_off_is_exact_legacy_choice(tmp_path):
    assert (SCHEMA_VERSION, RULES_VERSION) == (24, 32)  # 02-F adds opt-in routine schema
    with SQLiteEventStore(tmp_path / "off.sqlite") as db:
        setup(db, configured=False, members=("basim", "nora"))
        clock = TimeEngine(db)
        clock.open_session("test")
        state = db.load("test")
        assert not state.npc_temperaments
        a, b = choose_action(state, "basim"), choose_action(state, "nora")
        assert a.action == b.action == "work"
        assert a.score == b.score == 35
        assert "temperament" not in a.reason
        assert db.verify("test").to_dict() == state.to_dict()


def test_same_conditions_different_rational_choices(village):
    db, clock = village
    s = db.load("test")
    worker, explorer = choose_action(s, "basim"), choose_action(s, "nora")
    assert worker.action == "work" and worker.score > 35
    assert explorer.action == "investigate" and explorer.score > 35
    assert "ambition=100" in worker.reason and "curiosity=100" in explorer.reason
    assert s.npcs["basim"]["needs"] == s.npcs["nora"]["needs"]
    assert s.npcs["basim"]["goals"] == s.npcs["nora"]["goals"]
    assert choose_action(s, "salma").action == "work"
    x = decide(db, clock, "basim", "decide-worker")
    y = decide(db, clock, "nora", "decide-explorer")
    assert x.action == worker.action and y.action == explorer.action
    assert db.verify("test").to_dict() == db.load("test").to_dict()


def test_memory_is_created_only_by_real_action_completion(village):
    db, clock = village
    decision = decide(db, clock, "basim", "first")
    assert decision.action == "work"
    started = NPCActionService(db, clock).start("test", "basim", "first-job",
                                                expected_revision=rev(db))
    assert started.state.npc_temperaments["basim"]["memories"] == ()
    prior = step(db, clock, 179, "before-due")
    assert len(prior.npc_temperaments["basim"]["memories"]) == 0
    completed = step(db, clock, 1, "due")
    m = completed.npc_temperaments["basim"]["memories"]
    assert len(m) == 1
    assert m[0]["action_id"] == "first-job"
    assert m[0]["action"] == "work"
    assert m[0]["completed_at"] == 180
    assert m[0]["effects"] == completed.actions["first-job"]["result"]
    assert "remembered_last=work" in choose_action(completed, "basim").reason
    assert db.verify("test").to_dict() == completed.to_dict()


def test_fake_memory_without_action_cannot_pass_snapshot_or_replay(village):
    db, clock = village
    s = db.load("test")
    forged = s.to_dict()
    forged["npc_temperaments"]["basim"]["memories"].append({
        "action_id": "imaginary", "action": "work", "completed_at": 0,
        "effects": {"needs": {}, "counters": {}},
    })
    with pytest.raises(ValueError, match="exact completed"):
        WorldState.from_dict(forged)
    with pytest.raises(ValueError, match="time-zero"):
        apply_event(s, ev("NPCTemperamentConfigured", {
            "npc_id": "huda", "traits": WORKER,
        }, who="basim"))
    assert db.load("test").to_dict() == s.to_dict()


def test_invalid_traits_and_duplicate_profiles_roll_back(tmp_path):
    for i, bad in enumerate((None, True, -1, 101, "99")):
        with SQLiteEventStore(tmp_path / f"bad-{i}.sqlite") as db:
            changed = dict(WORKER)
            changed["caution"] = bad
            with pytest.raises(InvalidEvent):
                setup(db, traits={"basim": changed})
            assert db.load("test").revision == 0
    with SQLiteEventStore(tmp_path / "duplicate.sqlite") as db:
        with pytest.raises(InvalidEvent):
            setup(db, traits={"basim": WORKER, "nora": EXPLORER, "ghost": WORKER})
        assert db.load("test").revision == 0


def test_duplicate_personality_and_late_reconfiguration_refused(village):
    db, clock = village
    before = db.load("test")
    duplicate = ev("NPCTemperamentConfigured", {
        "npc_id": "basim", "traits": EXPLORER,
    })
    with pytest.raises(InvalidEvent):
        db.append("test", "dup-traits", before.revision, [duplicate], bootstrap=True)
    with pytest.raises(InvalidEvent):
        db.append("test", "late-traits", before.revision, [
            ev("NPCTemperamentConfigured", {"npc_id": "salma", "traits": WORKER})
        ])
    assert db.load("test").to_dict() == before.to_dict()


def test_partial_or_fabricated_decision_policy_is_not_accepted(village):
    db, clock = village
    prior = db.load("test")
    actual = choose_action(prior, "basim")
    fake = ev("NPCDecisionRecorded", {
        "npc_id": "basim", "action": "investigate", "score": 900,
        "reason": "made-up plan", "next_decision_at": 60,
    }, who="basim")
    with pytest.raises(InvalidEvent, match="utility policy"):
        db.append("test", "spoof-policy", prior.revision, [fake],
                  npc_authorized=True)
    assert actual.action == "work"
    assert db.load("test").to_dict() == prior.to_dict()


def test_critical_survival_mode_keeps_nonessential_actions_suppressed(tmp_path):
    with SQLiteEventStore(tmp_path / "survival.sqlite") as db:
        setup(db, hunger=100)
        state = db.load("test")
        chosen = choose_action(state, "basim", survival_enabled=True)
        assert chosen.action not in ("work", "investigate")
        assert "ambition=100" in chosen.reason


def test_personality_decision_rejected_after_session_pause(village):
    db, clock = village
    before = db.load("test").to_dict()
    clock.close_session("test")
    with pytest.raises(SessionClosed):
        decide(db, clock, "basim", "paused")
    assert db.load("test").to_dict() == before
