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
        assert (SCHEMA_VERSION, RULES_VERSION) == (37, 49)
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


def test_autonomous_gossip_is_opt_in_local_and_based_on_actual_threat(tmp_path):
    db, clock, service = world(tmp_path)
    try:
        for npc in ("nora", "basim", "sara"):
            events = []
            for item in ("labor_units", "investigation_attempts"):
                events.append(ev("ResourceChanged", {
                    "owner_id": npc, "resource": item, "previous": None,
                    "current": 0, "source": "initialization"}))
            db.append("world", "init:"+npc, db.load("world").revision,
                      events, bootstrap=True)
        speak(db, clock)
        step(db, clock, seconds=60, ident="time-for-gossip")
        before = db.load("world")
        assert len(choose_rumor_round(before)) == 1
        state = LivingWorldEngine(db, clock, rumors_enabled=True).advance(
            "world", seconds=1, command_id="gossip-day",
            expected_revision=before.revision).state
        assert len(state.rumor_deliveries) == 1
        delivery = next(iter(state.rumor_deliveries.values()))
        assert (delivery["sender"], delivery["recipient"], delivery["subject"]) == (
            "basim", "nora", "carlos")
        assert state.rumor_deliveries
        assert heard_rumors(state, "sara") == ()
        assert db.verify("world").to_dict() == state.to_dict()
    finally:
        db.close()


def test_untrusted_rumor_command_and_closed_session_rejected(tmp_path):
    db, clock, service = world(tmp_path)
    try:
        speak(db, clock)
        step(db, clock)
        baseline = db.load("world")
        claim = DomainEvent("RumorDelivered", "basim", "attempted forged API", baseline.time, {
            "id": "unsafe", "recipient_id": "nora",
            "original_id": "original", "parent_id": None})
        with pytest.raises(InvalidEvent, match="trusted"):
            db.append("world", "unauthorized", baseline.revision, [claim])
        assert db.load("world").to_dict() == baseline.to_dict()
        clock.close_session("world")
        with pytest.raises(InvalidEvent, match="active play session"):
            db.append("world", "while-closed", baseline.revision,
                      [claim], social_authorized=True)
        assert db.load("world").to_dict() == baseline.to_dict()
    finally:
        db.close()


def test_seven_npc_three_step_gossip_chain_preserves_private_views(tmp_path):
    from test_social_autonomy import make_world
    with SQLiteEventStore(tmp_path / "seven.sqlite") as db:
        names = ("adel", "basim", "huda", "layla", "nora", "omar", "salma")
        make_world(db, names=names)
        clock = TimeEngine(db)
        clock.open_session("village")
        NPCSocialService(db, clock).interact(
            "village", "carlos", "basim", kind="threat",
            text="You are a goblin.", message_id="actual-insult",
            expected_revision=db.load("village").revision)
        service = NPCRumorService(db, clock)
        for n, sender, receiver, parent in (
            (1, "basim", "adel", None),
            (2, "adel", "huda", "first"),
            (3, "huda", "layla", "second"),
        ):
            clock.advance("village", seconds=60, command_id=f"time-{n}",
                          expected_revision=db.load("village").revision)
            service.tell(
                "village", sender, receiver, "actual-insult",
                parent_id=parent, delivery_id=("first", "second", "third")[n-1],
                expected_revision=db.load("village").revision)
        state = db.load("village")
        assert len(state.npcs) == 7
        assert [state.rumor_deliveries[x]["hops"] for x in ("first", "second", "third")] == [1, 2, 3]
        assert [state.rumor_deliveries[x]["confidence"] for x in ("first", "second", "third")] == [70, 50, 30]
        assert heard_rumors(state, "nora") == ()
        assert perceived_reputation(state, "nora", "carlos")["reported_threats"] == 0
        assert perceived_reputation(state, "layla", "carlos")["reported_threats"] == 1
        assert state.entities["carlos"]["name"] == "Carlos"
        assert db.verify("village").to_dict() == state.to_dict()
        clock.advance("village", seconds=60, command_id="time-4",
                      expected_revision=state.revision)
        with pytest.raises(InvalidEvent, match="maximum hops"):
            service.tell("village", "layla", "omar", "actual-insult",
                         parent_id="third", delivery_id="fourth",
                         expected_revision=db.load("village").revision)
