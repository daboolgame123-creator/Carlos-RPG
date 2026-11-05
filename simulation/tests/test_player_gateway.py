"""01-W local player's explicit commands, persistence and trust boundaries."""
from __future__ import annotations

import pytest

from carlos_sim import (
    PlayerGateway, PlayerCommandResult,
    DomainEvent, SQLiteEventStore, TimeEngine, LivingWorldEngine,
    NPCMovementService, NPCActionService, NPCSocialService,
    WorldState, apply_event,
)
from carlos_sim.store import InvalidEvent, DuplicateCommand, RevisionConflict
from carlos_sim.time_engine import SessionClosed, AdvanceLimitExceeded
from test_social import setup as setup_social


def setup_player_demo_world(db):
    """Initialize known NPC action counters in the disposable test world."""
    setup_social(db)
    state = db.load("world")
    events = [
        DomainEvent("ResourceChanged", None, "test initialization", 0, {
            "owner_id": npc, "resource": counter,
            "previous": None, "current": 0, "source": "initialization",
        })
        for npc in ("nora", "basim", "sara")
        for counter in ("labor_units", "investigation_attempts")
    ]
    db.append("world", "initialize-npc-work-counters",
              state.revision, events, bootstrap=True)


@pytest.fixture
def world(tmp_path):
    with SQLiteEventStore(tmp_path / "01w.sqlite") as db:
        setup_player_demo_world(db)
        clock = TimeEngine(db)
        clock.open_session("world")
        yield db, clock, PlayerGateway(
            db, clock, world_id="world", player_id="carlos"
        )


def test_player_inspection_exposes_only_local_public_presence(world):
    db, clock, gw = world
    view = gw.inspect()
    assert isinstance(view, PlayerCommandResult)
    assert view.status == "present"
    assert view.details["location_id"] == "market"
    assert {e["id"] for e in view.details["occupants"]} == {
        "carlos", "nora", "basim",
    }
    assert view.details["exits"] == (
        {"route_id": "road", "destination": "forest", "seconds": 90},
    )
    assert "sara" not in str(view.details)
    assert "relations" not in str(view.details)
    assert "resources" not in str(view.details)
    assert "beliefs" not in str(view.details)
    assert db.verify("world").to_dict() == db.load("world").to_dict()


def test_travel_is_scheduled_not_teleported_and_player_cannot_be_auto_npc(world):
    db, clock, gw = world
    before = db.load("world")
    move = gw.move("road", command_id="to-forest", expected_revision=before.revision)
    assert move.status == "traveling"
    state = db.load("world")
    assert state.entities["carlos"]["location_id"] == "market"
    assert "carlos" not in state.npcs
    assert move.revision == before.revision + 1
    assert "player-travel:carlos:to-forest" in state.scheduled
    transit = gw.inspect()
    assert transit.status == "traveling"
    assert transit.details == {"route_id": "road", "remaining_seconds": 90}
    assert "market" not in str(transit.details)
    assert "forest" not in str(transit.details)
    with pytest.raises(ValueError, match="travelling"):
        gw.move("road", command_id="second", expected_revision=state.revision)
    with pytest.raises(ValueError, match="travelling"):
        gw.interact("basim", kind="greeting", text="Hi", command_id="during",
                    expected_revision=state.revision)
    assert db.load("world").to_dict() == state.to_dict()

    just_before = gw.wait(89, command_id="first89",
                          expected_revision=state.revision)
    assert just_before.time == 89
    assert gw.inspect().details["remaining_seconds"] == 1
    assert db.load("world").entities["carlos"]["location_id"] == "market"
    arrived = gw.wait(1, command_id="last1",
                      expected_revision=db.load("world").revision)
    assert arrived.time == 90
    assert db.load("world").entities["carlos"]["location_id"] == "forest"
    assert all("__player_travel" not in item["payload"]
               for item in db.load("world").scheduled.values())
    assert gw.inspect().details["location_id"] == "forest"
    assert {x["id"] for x in gw.inspect().details["occupants"]} == {
        "carlos", "sara"
    }
    assert db.verify("world").to_dict() == db.load("world").to_dict()


def test_inspect_from_npc_perspective_cannot_see_traveling_player(world):
    db, clock, gw = world
    gw.move("road", command_id="trip", expected_revision=db.load("world").revision)
    snapshot = NPCMovementService(db, clock).observe(
        "world", "nora", command_id="observe",
        expected_revision=db.load("world").revision
    )
    assert "carlos" not in snapshot.observations["nora"]["market"]["occupants"]


def test_interaction_is_player_chosen_and_npc_controls_own_reaction(world):
    db, clock, gw = world
    response = gw.interact("basim", kind="greeting", text="Good morning",
                           command_id="greet1",
                           expected_revision=db.load("world").revision)
    assert response.status == "interacted"
    assert response.details["reaction"] == "acknowledged"
    assert response.details["recipient_id"] == "basim"
    state = db.load("world")
    assert state.social_messages["player-greet1"]["sender"] == "carlos"
    assert state.social_messages["player-greet1"]["status"] == "received"
    assert state.relations["basim"]["carlos"] == 1
    assert "carlos" not in state.npcs
    with pytest.raises(DuplicateCommand):
        gw.interact("basim", kind="greeting", text="Good morning",
                    command_id="greet1", expected_revision=state.revision)
    assert db.load("world").to_dict() == state.to_dict()


def test_remote_dialogue_rejected_without_creating_history(world):
    db, clock, gw = world
    old = db.load("world").to_dict()
    with pytest.raises(InvalidEvent, match="locally"):
        gw.interact("sara", kind="greeting", text="Hello",
                    command_id="remote", expected_revision=old["revision"])
    assert db.load("world").to_dict() == old
    with pytest.raises(ValueError, match="recipient"):
        gw.interact("carlos", kind="greeting", text="Hi",
                    command_id="self", expected_revision=old["revision"])
    with pytest.raises(ValueError, match="social"):
        gw.interact("basim", kind="teleport", text="Hi",
                    command_id="fake", expected_revision=old["revision"])


def test_nonadjacent_move_invalid_and_two_hops_require_two_commands(world):
    db, clock, gw = world
    added = db.append("world", "add-far-site", db.load("world").revision, [
        DomainEvent("LocationCreated", None, "test setup", 0,
                    {"id": "camp", "name": "Camp"}),
        DomainEvent("RouteCreated", None, "test setup", 0,
                    {"id": "forest-camp", "a": "forest", "b": "camp",
                     "seconds": 30}),
    ], bootstrap=True)
    with pytest.raises(ValueError, match="nonadjacent"):
        gw.move("forest-camp", command_id="no-teleport",
                expected_revision=added.revision)
    assert db.load("world").revision == added.revision
    gw.move("road", command_id="hop1",
            expected_revision=added.revision)
    gw.wait(90, command_id="step1",
            expected_revision=db.load("world").revision)
    assert db.load("world").entities["carlos"]["location_id"] == "forest"
    gw.move("forest-camp", command_id="hop2",
            expected_revision=db.load("world").revision)
    gw.wait(30, command_id="step2",
            expected_revision=db.load("world").revision)
    assert db.load("world").entities["carlos"]["location_id"] == "camp"
    assert db.verify("world").to_dict() == db.load("world").to_dict()


def test_no_player_impersonation_or_npc_exposed_as_player(world):
    db, clock, gw = world
    with pytest.raises(PermissionError, match="player"):
        PlayerGateway(db, clock, world_id="world", player_id="nora").inspect()
    with pytest.raises(PermissionError, match="player"):
        PlayerGateway(db, clock, world_id="world", player_id="absent").inspect()
    assert not any(e["controller"] == "player" and x != "carlos"
                   for x, e in db.load("world").entities.items())
    with pytest.raises(ValueError, match="NPC"):
        NPCMovementService(db, clock).start(
            "world", "carlos", "road", "player-in-npc-service",
            expected_revision=db.load("world").revision
        )


def test_stale_revision_bad_command_and_closed_session_leave_world_unchanged(world):
    db, clock, gw = world
    before = db.load("world").to_dict()
    with pytest.raises(RevisionConflict):
        gw.move("road", command_id="stale", expected_revision=0)
    with pytest.raises(ValueError, match="command ID"):
        gw.move("road", command_id="☃", expected_revision=before["revision"])
    with pytest.raises(ValueError):
        gw.move("not-a-route", command_id="unknown",
                expected_revision=before["revision"])
    with pytest.raises(ValueError):
        gw.wait(True, command_id="bool-is-not-time",
                expected_revision=before["revision"])
    assert db.load("world").to_dict() == before
    clock.close_session("world")
    for action in (
        lambda: gw.inspect(),
        lambda: gw.move("road", command_id="closed",
                        expected_revision=before["revision"]),
        lambda: gw.wait(1, command_id="closed-wait",
                        expected_revision=before["revision"]),
        lambda: gw.interact("basim", kind="greeting", text="Hi",
                            command_id="closed-talk",
                            expected_revision=before["revision"]),
    ):
        with pytest.raises(SessionClosed):
            action()
    assert db.load("world").to_dict() == before


def test_forged_schedule_and_direct_capabilities_are_denied(world):
    db, clock, gw = world
    s = db.load("world")
    fake = DomainEvent("ScheduledEventCreated", None,
                       "spoof travel signal", s.time, {
        "id": "player-travel:carlos:forged",
        "due": s.time + 90, "order": s.next_schedule_order,
        "kind": "signal", "interrupt": False,
        "payload": {"__player_travel": {
            "player_id": "carlos", "route_id": "road", "origin": "market",
            "destination": "forest", "started_at": s.time,
        }}
    })
    with pytest.raises(InvalidEvent, match="trusted"):
        db.append("world", "spoof", s.revision, [fake])
    assert db.load("world").to_dict() == s.to_dict()
    with pytest.raises(ValueError, match="trusted"):
        apply_event(s, fake)
    fake_actor = DomainEvent("ScheduledEventCreated", "nora",
                             "spoof identity", s.time, dict(fake.data))
    with pytest.raises(InvalidEvent, match="trusted"):
        db.append("world", "spoof-actor", s.revision, [fake_actor],
                  movement_authorized=True)
    clock.close_session("world")
    with pytest.raises(InvalidEvent, match="active play session"):
        db.append("world", "spoof-closed", s.revision, [fake],
                  movement_authorized=True)
    assert db.load("world").to_dict() == s.to_dict()


def test_player_wait_failure_is_atomic_and_repeat_wait_is_rejected(world):
    db, clock, gw = world
    gw.move("road", command_id="start",
            expected_revision=db.load("world").revision)
    old = db.load("world").to_dict()
    count = db.db.execute("SELECT COUNT(*) FROM events WHERE world_id='world'").fetchone()[0]
    failing = PlayerGateway(
        db, clock, world_id="world", player_id="carlos",
        engine=LivingWorldEngine(db, clock, max_events_per_advance=1),
    )
    with pytest.raises(AdvanceLimitExceeded):
        failing.wait(90, command_id="exceeded",
                     expected_revision=old["revision"])
    assert db.load("world").to_dict() == old
    assert db.db.execute("SELECT COUNT(*) FROM events WHERE world_id='world'").fetchone()[0] == count
    normal = gw.wait(90, command_id="valid",
                     expected_revision=db.load("world").revision)
    after = db.load("world").to_dict()
    assert normal.time == 90
    with pytest.raises(DuplicateCommand):
        gw.wait(90, command_id="valid",
                expected_revision=after["revision"])
    assert db.load("world").to_dict() == after


def test_player_move_snapshot_close_reopen_full_replay(tmp_path):
    path = tmp_path / "player-reopen.sqlite"
    with SQLiteEventStore(path) as db:
        setup_player_demo_world(db)
        clock = TimeEngine(db)
        clock.open_session("world")
        gw = PlayerGateway(db, clock, world_id="world", player_id="carlos")
        gw.move("road", command_id="go",
                expected_revision=db.load("world").revision)
        db.snapshot("world")
        travelling = db.load("world").to_dict()
        assert db.verify("world").to_dict() == travelling
    with SQLiteEventStore(path) as db:
        clock = TimeEngine(db)
        clock.open_session("world")
        gw = PlayerGateway(db, clock, world_id="world", player_id="carlos")
        assert db.load("world").to_dict() == travelling
        assert gw.inspect().status == "traveling"
        gw.wait(90, command_id="arrive",
                expected_revision=db.load("world").revision)
        db.snapshot("world")
        assert db.load("world").entities["carlos"]["location_id"] == "forest"
        assert db.verify("world").to_dict() == db.load("world").to_dict()


def test_player_journey_cannot_be_cancelled_without_explicit_game_policy(world):
    db, clock, gw = world
    gw.move("road", command_id="must-arrive",
            expected_revision=db.load("world").revision)
    unchanged = db.load("world").to_dict()
    with pytest.raises(InvalidEvent, match="cannot cancel an active player"):
        clock.cancel(
            "world", "player-travel:carlos:must-arrive",
            command_id="erase-journey",
            expected_revision=db.load("world").revision,
        )
    assert db.load("world").to_dict() == unchanged
    assert db.verify("world").to_dict() == unchanged


def test_malformed_player_travel_payload_cannot_forge_impossible_destination(world):
    db, clock, gw = world
    original = db.load("world")
    for actor, route, origin, dest, due in (
        ("carlos", "road", "market", "forest", 89),
        ("carlos", "road", "forest", "market", 90),
        ("nora", "road", "market", "forest", 90),
        ("carlos", "hidden-road", "market", "forest", 90),
    ):
        event = DomainEvent("ScheduledEventCreated", None,
                            "forged player movement", 0, {
            "id": "player-travel:" + actor + ":spoof",
            "due": due, "order": original.next_schedule_order,
            "kind": "signal", "interrupt": False,
            "payload": {"__player_travel": {
                "player_id": actor, "route_id": route,
                "origin": origin, "destination": dest, "started_at": 0,
            }},
        })
        with pytest.raises(ValueError, match="player travel"):
            apply_event(original, event, movement_authorized=True)
    assert db.load("world").to_dict() == original.to_dict()


def test_raw_clock_advancement_resolves_player_arrival_without_gateway_magic(world):
    db, clock, gw = world
    moved = gw.move(
        "road", command_id="start-clock-test",
        expected_revision=db.load("world").revision)
    direct = clock.advance(
        "world", seconds=90, command_id="trusted-clock",
        expected_revision=moved.revision)
    assert direct.state.time == 90
    assert direct.state.entities["carlos"]["location_id"] == "forest"
    assert "player-travel:carlos:start-clock-test" not in direct.state.scheduled
    assert db.verify("world").to_dict() == direct.state.to_dict()
