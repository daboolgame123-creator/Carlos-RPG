"""02-G grounded gossip: only real heard speech can become local attributed rumor."""
import pytest
from carlos_sim import DomainEvent, SQLiteEventStore, TimeEngine, NPCSocialService, LivingWorldEngine
from carlos_sim.store import InvalidEvent
from carlos_sim.domain import SCHEMA_VERSION, RULES_VERSION, WorldState
from carlos_sim.rumors import NPCRumorService, heard_rumors, perceived_reputation, choose_rumor_round
from test_social import setup, ev


def world(tmp_path):
    db = SQLiteEventStore(tmp_path / "rumors.sqlite")
    setup(db)
    clock = TimeEngine(db)
    clock.open_session("world")
    return db, clock, NPCRumorService(db, clock)


def speak(db, clock, *, msg="original", kind="threat", sender="carlos",
          receiver="basim", text="You are a goblin!"):
    NPCSocialService(db, clock).interact(
        "world", sender, receiver, kind=kind, text=text,
        message_id=msg, expected_revision=db.load("world").revision)


def step(db, clock, seconds=60, ident="tick"):
    clock.advance("world", seconds=seconds, command_id=ident,
                  expected_revision=db.load("world").revision)


def tell(db, svc, sender, receiver, original="original", parent=None, ident="r1"):
    return svc.tell("world", sender, receiver, original,
                    delivery_id=ident, parent_id=parent,
                    expected_revision=db.load("world").revision)


def test_genuine_player_utterance_becomes_uncertain_local_rumor(tmp_path):
    db, clock, service = world(tmp_path)
    try:
        assert (SCHEMA_VERSION, RULES_VERSION) == (21, 28)
        speak(db, clock)
        step(db, clock)
        result = tell(db, service, "basim", "nora")
        records = heard_rumors(result, "nora")
        assert len(records) == 1
        assert (records[0]["subject"], records[0]["speaker"],
                records[0]["hops"], records[0]["confidence"]) == ("carlos", "basim", 1, 70)
        score = perceived_reputation(result, "nora", "carlos")
        assert score["reported_threats"] == 1 and score["proven_misconduct"] is False
        assert heard_rumors(result, "sara") == ()
        assert result.entities["carlos"]["name"] == "carlos"
        assert db.verify("world").to_dict() == result.to_dict()
    finally:
        db.close()


def test_unwitnessed_self_relay_and_same_tick_forgery_fail_closed(tmp_path):
    db, clock, service = world(tmp_path)
    try:
        speak(db, clock)
        baseline = db.load("world")
        with pytest.raises(InvalidEvent):
            tell(db, service, "basim", "nora")
        assert db.load("world").to_dict() == baseline.to_dict()
        step(db, clock)
        with pytest.raises(InvalidEvent):
            tell(db, service, "nora", "basim", ident="invent")
        with pytest.raises(InvalidEvent):
            tell(db, service, "basim", "nora", original="unknown", ident="unknown")
        with pytest.raises(InvalidEvent):
            tell(db, service, "basim", "carlos", ident="player")
        assert db.verify("world").to_dict() == db.load("world").to_dict()
    finally:
        db.close()


def test_secondary_hearsay_needs_genuine_parent_and_elapsed_time(tmp_path):
    db, clock, service = world(tmp_path)
    try:
        # Add a real fourth NPC before any time advances.
        db.append("world", "new-neighbor", db.load("world").revision, [
            ev("EntityCreated", {"id": "adel", "name": "Adel",
                                  "controller": "npc", "location_id": "market"}),
            ev("NPCConfigured", {"npc_id": "adel", "role": "merchant",
                                  "needs": {"fatigue": 5, "hunger": 10, "safety": 0},
                                  "goals": {"earn": 30, "explore": 10, "survive": 20}}),
        ], bootstrap=True)
        speak(db, clock, sender="carlos", receiver="basim")
        step(db, clock, ident="first-time")
        tell(db, service, "basim", "nora", ident="first")
        before = db.load("world")
        with pytest.raises(InvalidEvent):
            tell(db, service, "nora", "adel", parent="first", ident="instant")
        assert db.load("world").to_dict() == before.to_dict()
        step(db, clock, ident="second-time")
        forwarded = tell(db, service, "nora", "adel", parent="first", ident="second")
        assert forwarded.rumor_deliveries["second"]["hops"] == 2
        assert forwarded.rumor_deliveries["second"]["confidence"] == 50
        assert forwarded.rumor_deliveries["second"]["original_id"] == "original"
        assert db.verify("world").to_dict() == forwarded.to_dict()
    finally:
        db.close()


def test_remote_gossip_and_duplicate_listener_rejected(tmp_path):
    db, clock, service = world(tmp_path)
    try:
        speak(db, clock)
        step(db, clock)
        with pytest.raises(InvalidEvent, match="co-located"):
            tell(db, service, "basim", "sara", ident="remote")
        first = tell(db, service, "basim", "nora")
        step(db, clock, seconds=600, ident="cooldown")
        with pytest.raises(InvalidEvent, match="already heard"):
            tell(db, service, "basim", "nora", ident="duplicate")
        assert db.load("world").rumor_deliveries == first.rumor_deliveries
    finally:
        db.close()


def test_snapshot_reopen_preserves_rumor_provenance(tmp_path):
    path = tmp_path / "restart.sqlite"
    with SQLiteEventStore(path) as db:
        setup(db)
        clock = TimeEngine(db); clock.open_session("world")
        speak(db, clock)
        step(db, clock)
        NPCRumorService(db, clock).tell(
            "world", "basim", "nora", "original", delivery_id="first",
            expected_revision=db.load("world").revision)
        saved = db.load("world").to_dict()
        db.snapshot("world")
    with SQLiteEventStore(path) as db:
        state = db.load("world")
        assert state.to_dict() == saved
        assert db.verify("world").to_dict() == saved
        assert state.rumor_deliveries["first"]["parent_id"] is None


def test_default_off_retains_no_autonomous_rumor(tmp_path):
    db, clock, service = world(tmp_path)
    try:
        # Baseline social fixture does not initialize action counters.
        # Include the real resources needed for autonomous work/foraging.
        setup_resources = []
        for npc in ("nora", "basim", "sara"):
            for resource in ("labor_units", "investigation_attempts"):
                setup_resources.append(ev("ResourceChanged", {
                    "owner_id": npc, "resource": resource, "previous": None,
                    "current": 0, "source": "initialization"}))
        db.append("world", "counters", db.load("world").revision,
                  setup_resources, bootstrap=True)
        speak(db, clock)
        result = LivingWorldEngine(db, clock).advance(
            "world", seconds=120, command_id="off",
            expected_revision=db.load("world").revision)
        assert result.state.rumor_deliveries == {}
        assert result.state.social_messages["original"]["status"] == "received"
    finally:
        db.close()


def test_invalid_stored_snapshot_cannot_invent_story(tmp_path):
    db, clock, service = world(tmp_path)
    try:
        speak(db, clock)
        step(db, clock)
        tell(db, service, "basim", "nora")
        corrupted = db.load("world").to_dict()
        corrupted["rumor_deliveries"]["r1"]["original_id"] = "made-up-event"
        with pytest.raises(ValueError):
            WorldState.from_dict(corrupted)
    finally:
        db.close()
