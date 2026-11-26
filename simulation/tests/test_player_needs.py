"""Player physiology is event-sourced, opt-in and independent of NPC/RPG state."""
from __future__ import annotations

import pytest

from carlos_sim import DomainEvent, LivingWorldEngine, PlayerGateway, SQLiteEventStore, TimeEngine
from carlos_sim.domain import WorldState, apply_event
from carlos_sim.player_needs import REST_SECONDS, player_rest_signal
from carlos_sim.rpg_state import unknown_profile
from carlos_sim.store import DuplicateCommand, InvalidEvent, RevisionConflict
from carlos_sim.time_engine import SessionClosed

WORLD = "player-needs"
PLAYER = "carlos"


def _event(kind, data, *, who=None, at=0):
    return DomainEvent(kind, who, "disposable player-needs fixture", at, data)


def _setup(db, *, configured=True, hunger=60, fatigue=40):
    db.create_world(WORLD)
    events = [
        _event("LocationCreated", {"id": site, "name": site})
        for site in ("home", "woods")
    ]
    events.append(_event("RouteCreated", {
        "id": "home-woods", "a": "home", "b": "woods", "seconds": 90,
    }))
    for who, controller in ((PLAYER, "player"), ("elena", "player"), ("nora", "npc")):
        events.append(_event("EntityCreated", {
            "id": who, "name": who, "location_id": "home", "controller": controller,
        }))
    events.append(_event("NPCConfigured", {
        "npc_id": "nora", "role": "resident",
        "needs": {"hunger": 20, "fatigue": 5, "safety": 0},
        "goals": {"earn": 80, "explore": 0, "survive": 10},
    }))
    for owner, balances in (
        (PLAYER, {"food": 3, "bread": 1, "coin_copper": 10}),
        ("home", {"wild_food": 2}),
        ("nora", {"labor_units": 0, "investigation_attempts": 0}),
    ):
        for resource, quantity in balances.items():
            events.append(_event("ResourceChanged", {
                "owner_id": owner, "resource": resource,
                "previous": None, "current": quantity, "source": "initialization",
            }))
    profile = unknown_profile()
    profile["vitals"]["hp"] = {"current": 12, "max": 12}
    profile["vitals"]["st"] = {"current": 8, "max": 8}
    events.append(_event("PlayerRPGInitialized", {"player_id": PLAYER, "profile": profile}))
    if configured:
        events.append(_event("PlayerNeedsInitialized", {
            "player_id": PLAYER, "hunger": hunger, "fatigue": fatigue,
        }))
    db.append(WORLD, "bootstrap", 0, events, bootstrap=True)
    clock = TimeEngine(db)
    clock.open_session(WORLD)
    return clock


@pytest.fixture
def world(tmp_path):
    with SQLiteEventStore(tmp_path / "needs.sqlite") as db:
        clock = _setup(db)
        yield db, clock, PlayerGateway(db, clock, world_id=WORLD, player_id=PLAYER)


def _tick(db, clock, seconds, command="tick"):
    return clock.advance(WORLD, seconds=seconds, command_id=command,
                         expected_revision=db.load(WORLD).revision).state


def _rest_event(state, *, data=None, due=None, ident=None):
    return _event("ScheduledEventCreated", {
        "id": ident or "player-rest:carlos:rest",
        "due": state.time + REST_SECONDS if due is None else due,
        "order": state.next_schedule_order, "kind": "signal", "interrupt": False,
        "payload": {"__player_rest": data if data is not None else {
            "player_id": PLAYER, "site_id": "home", "started_at": state.time}},
    }, at=state.time)


def _rest(db):
    state = db.load(WORLD)
    return db.append(WORLD, "player-rest:rest", state.revision, [_rest_event(state)],
                     action_authorized=True, movement_authorized=True)


def test_unconfigured_player_retains_legacy_semantics(tmp_path):
    with SQLiteEventStore(tmp_path / "legacy.sqlite") as db:
        clock = _setup(db, configured=False)
        g = PlayerGateway(db, clock, world_id=WORLD, player_id=PLAYER)
        _tick(db, clock, 900)
        g.eat("food", command_id="eat", expected_revision=db.load(WORLD).revision)
        assert db.verify(WORLD).player_needs == {}
        assert g.needs().details["hunger"] == "not_modeled"
        assert g.needs().details["physical_energy"] == "not_modeled"
        with pytest.raises(InvalidEvent):
            _rest(db)


def test_elapsed_boundaries_do_not_require_npc_survival_mode(world):
    db, clock, _ = world
    before = db.load(WORLD)
    first = _tick(db, clock, 299)
    assert dict(first.player_needs[PLAYER]) == {
        "hunger": 60, "fatigue": 40, "hunger_seconds": 299, "fatigue_seconds": 299,
    }
    second = _tick(db, clock, 1, "boundary")
    assert second.player_needs[PLAYER]["hunger"] == 61
    assert second.player_needs[PLAYER]["fatigue"] == 40
    final = _tick(db, clock, 300, "fatigue-boundary")
    assert dict(final.player_needs[PLAYER]) == {
        "hunger": 62, "fatigue": 41, "hunger_seconds": 0, "fatigue_seconds": 0,
    }
    assert final.npcs == before.npcs
    assert final.rpg_profiles == before.rpg_profiles
    assert final.resources == before.resources
    assert "elena" not in final.player_needs
    assert db.verify(WORLD).to_dict() == final.to_dict()


def test_large_and_split_advances_have_identical_needs(tmp_path):
    outcomes = []
    for i, chunks in enumerate(((3601,), (299, 1, 300, 1201, 1800))):
        with SQLiteEventStore(tmp_path / f"split-{i}.sqlite") as db:
            clock = _setup(db)
            for j, seconds in enumerate(chunks):
                _tick(db, clock, seconds, f"part-{j}")
            outcomes.append(dict(db.verify(WORLD).player_needs[PLAYER]))
    assert outcomes[0] == outcomes[1] == {
        "hunger": 72, "fatigue": 46, "hunger_seconds": 1, "fatigue_seconds": 1,
    }


def test_caps_do_not_create_food_heal_or_kill_player(world):
    db, clock, _ = world
    before = db.load(WORLD)
    after = _tick(db, clock, 100_000)
    assert after.player_needs[PLAYER]["hunger"] == 100
    assert after.player_needs[PLAYER]["fatigue"] == 100
    assert after.player_needs[PLAYER]["hunger_seconds"] == 100_000 % 300
    assert after.resources == before.resources
    assert after.rpg_profiles == before.rpg_profiles
    assert after.entities == before.entities


def test_real_meal_reduces_only_own_hunger_once(world):
    db, clock, g = world
    _tick(db, clock, 123)
    before = db.load(WORLD)
    g.eat("food", command_id="meal", expected_revision=before.revision)
    after = db.load(WORLD)
    assert after.player_needs[PLAYER]["hunger"] == 25
    assert after.player_needs[PLAYER]["fatigue"] == 40
    assert after.player_needs[PLAYER]["hunger_seconds"] == 123
    assert after.resources[PLAYER]["food"] == before.resources[PLAYER]["food"] - 1
    assert after.resources[PLAYER]["coin_copper"] == 10
    assert after.rpg_profiles == before.rpg_profiles
    assert after.npcs == before.npcs
    with pytest.raises(DuplicateCommand):
        g.eat("food", command_id="meal", expected_revision=after.revision)
    with pytest.raises(RevisionConflict):
        g.eat("food", command_id="stale-meal", expected_revision=before.revision)
    assert db.verify(WORLD).to_dict() == after.to_dict()


def test_bread_relief_clamps_at_zero_without_free_food(world):
    db, _, g = world
    g.eat("food", command_id="first", expected_revision=db.load(WORLD).revision)
    g.eat("bread", command_id="bread", expected_revision=db.load(WORLD).revision)
    before = db.load(WORLD)
    assert before.player_needs[PLAYER]["hunger"] == 0
    assert before.resources[PLAYER]["bread"] == 0
    with pytest.raises(ValueError):
        g.eat("bread", command_id="no-bread", expected_revision=before.revision)
    assert db.verify(WORLD).to_dict() == before.to_dict()


def test_rest_is_timed_hungry_and_never_automatic(world):
    db, clock, _ = world
    before = db.load(WORLD)
    resting = _rest(db)
    assert resting.time == 0
    assert resting.player_needs == before.player_needs
    assert player_rest_signal(resting, PLAYER) is not None
    partial = _tick(db, clock, REST_SECONDS - 1)
    assert partial.player_needs[PLAYER]["fatigue"] == 40
    assert partial.player_needs[PLAYER]["hunger"] == 65
    assert player_rest_signal(partial, PLAYER) is not None
    done = _tick(db, clock, 1, "finish")
    assert done.player_needs[PLAYER]["fatigue"] == 20
    assert done.player_needs[PLAYER]["hunger"] == 66
    assert player_rest_signal(done, PLAYER) is None
    awake = _tick(db, clock, 600, "awake")
    assert awake.player_needs[PLAYER]["fatigue"] == 21
    assert awake.rpg_profiles == before.rpg_profiles
    assert awake.resources == before.resources
    assert db.verify(WORLD).to_dict() == awake.to_dict()


def test_waiting_is_not_resting(world):
    db, clock, _ = world
    after = _tick(db, clock, REST_SECONDS)
    assert after.player_needs[PLAYER]["fatigue"] == 43
    assert after.player_needs[PLAYER]["hunger"] == 66
    assert player_rest_signal(after, PLAYER) is None


def test_rest_keeps_world_and_npc_actions_running(world):
    db, clock, _ = world
    _rest(db)
    engine = LivingWorldEngine(db, clock, decision_cooldown=3600)
    result = engine.advance(WORLD, seconds=REST_SECONDS, command_id="world-rest",
                            expected_revision=db.load(WORLD).revision)
    assert result.completed_action_ids
    assert result.state.resources["nora"]["labor_units"] > 0
    assert result.state.player_needs[PLAYER]["fatigue"] == 20
    assert result.state.player_needs[PLAYER]["hunger"] == 66
    assert db.verify(WORLD).to_dict() == result.state.to_dict()


def test_interruption_only_charges_actual_elapsed_and_keeps_rest(world):
    db, clock, _ = world
    _rest(db)
    clock.schedule_signal(WORLD, "alarm", due=900, interrupt=True,
                          expected_revision=db.load(WORLD).revision)
    result = clock.advance(WORLD, seconds=REST_SECONDS, command_id="interrupted",
                           expected_revision=db.load(WORLD).revision)
    assert result.interrupted and result.elapsed_seconds == 900
    assert result.state.player_needs[PLAYER]["hunger"] == 63
    assert result.state.player_needs[PLAYER]["fatigue"] == 40
    assert player_rest_signal(result.state, PLAYER) is not None
    done = _tick(db, clock, result.remaining_seconds, "continue")
    assert done.player_needs[PLAYER]["fatigue"] == 20


def test_rest_blocks_eating_travel_forage_and_second_rest(world):
    db, _, g = world
    _rest(db)
    before = db.load(WORLD)
    for command in (
        lambda: g.eat("food", command_id="busy-eat", expected_revision=before.revision),
        lambda: g.move("home-woods", command_id="busy-move", expected_revision=before.revision),
        lambda: g.forage(command_id="busy-forage", expected_revision=before.revision),
        lambda: apply_event(before, _rest_event(before, ident="player-rest:carlos:second"),
                            action_authorized=True, movement_authorized=True),
    ):
        with pytest.raises((ValueError, InvalidEvent)):
            command()
        assert db.verify(WORLD).to_dict() == before.to_dict()


@pytest.mark.parametrize("busy", ["travel", "forage"])
def test_rest_cannot_start_during_other_timed_action(world, busy):
    db, _, g = world
    if busy == "travel":
        g.move("home-woods", command_id="depart", expected_revision=db.load(WORLD).revision)
    else:
        g.forage(command_id="search", expected_revision=db.load(WORLD).revision)
    before = db.load(WORLD)
    with pytest.raises(InvalidEvent):
        _rest(db)
    assert db.verify(WORLD).to_dict() == before.to_dict()


def test_rest_cannot_be_cancelled_or_completed_early(world):
    db, clock, _ = world
    _rest(db)
    before = db.load(WORLD)
    with pytest.raises(InvalidEvent, match="cancel"):
        clock.cancel(WORLD, "player-rest:carlos:rest", command_id="cancel",
                     expected_revision=before.revision)
    with pytest.raises(ValueError, match="due time"):
        apply_event(before, _event("ScheduledEventFired", {"id": "player-rest:carlos:rest"}))
    assert db.verify(WORLD).to_dict() == before.to_dict()


@pytest.mark.parametrize("data", [
    {"player_id": "nora", "hunger": 20, "fatigue": 10},
    {"player_id": "missing", "hunger": 20, "fatigue": 10},
    {"player_id": PLAYER, "hunger": True, "fatigue": 10},
    {"player_id": PLAYER, "hunger": 101, "fatigue": 10},
    {"player_id": PLAYER, "hunger": 20, "fatigue": -1},
    {"player_id": PLAYER, "hunger": 20, "fatigue": "10"},
])
def test_invalid_initial_needs_rejected_without_mutation(tmp_path, data):
    with SQLiteEventStore(tmp_path / "invalid.sqlite") as db:
        _setup(db, configured=False)
        before = db.load(WORLD)
        with pytest.raises(InvalidEvent):
            db.append(WORLD, "invalid-needs", before.revision,
                      [_event("PlayerNeedsInitialized", data)], bootstrap=True)
        assert db.verify(WORLD).to_dict() == before.to_dict()


def test_needs_cannot_be_reset_or_enabled_after_time_zero(world):
    db, clock, _ = world
    before = db.load(WORLD)
    event = _event("PlayerNeedsInitialized", {"player_id": PLAYER, "hunger": 0, "fatigue": 0})
    with pytest.raises(InvalidEvent):
        db.append(WORLD, "reset", before.revision, [event], bootstrap=True)
    _tick(db, clock, 1)
    now = db.load(WORLD)
    with pytest.raises(InvalidEvent):
        db.append(WORLD, "late", now.revision, [_event("PlayerNeedsInitialized", {
            "player_id": "elena", "hunger": 0, "fatigue": 0}, at=now.time)], bootstrap=True)
    assert db.verify(WORLD).to_dict() == now.to_dict()


@pytest.mark.parametrize("field,value", [
    ("hunger", True), ("hunger", 101), ("fatigue", -1),
    ("hunger_seconds", 300), ("fatigue_seconds", 600),
    ("fatigue_seconds", 0.5),
])
def test_invalid_needs_snapshots_fail_closed(world, field, value):
    db, _, _ = world
    raw = db.load(WORLD).to_dict()
    raw["player_needs"][PLAYER][field] = value
    with pytest.raises(ValueError, match="player needs"):
        WorldState.from_dict(raw)


@pytest.mark.parametrize("change", ["duration", "remote", "unconfigured", "old-start", "mixed-payload"])
def test_forged_rest_details_fail_closed(world, change):
    db, clock, _ = world
    _tick(db, clock, 10)
    before = db.load(WORLD)
    obj = _rest_event(before).to_dict()
    if change == "duration":
        obj["data"]["due"] -= 1
    elif change == "remote":
        obj["data"]["payload"]["__player_rest"]["site_id"] = "woods"
    elif change == "unconfigured":
        obj["data"]["payload"]["__player_rest"]["player_id"] = "elena"
    elif change == "old-start":
        obj["data"]["payload"]["__player_rest"]["started_at"] = 0
        obj["data"]["due"] = REST_SECONDS
    else:
        obj["data"]["payload"]["forged"] = True
    with pytest.raises(ValueError):
        apply_event(before, DomainEvent.from_dict(obj),
                    action_authorized=True, movement_authorized=True)
    assert db.verify(WORLD).to_dict() == before.to_dict()


def test_snapshot_resume_keeps_partial_rest_and_frozen_time(tmp_path):
    path = tmp_path / "resume.sqlite"
    with SQLiteEventStore(path) as db:
        clock = _setup(db)
        _tick(db, clock, 123)
        _rest(db)
        partial = _tick(db, clock, 900, "half-rest")
        db.snapshot(WORLD)
        saved = partial.to_dict()
        clock.close_session(WORLD)
        with pytest.raises(SessionClosed):
            _tick(db, clock, 60, "offline")
    with SQLiteEventStore(path) as db:
        clock = TimeEngine(db)
        assert db.verify(WORLD).to_dict() == saved
        assert db.load(WORLD).time == 1023
        clock.open_session(WORLD)
        done = _tick(db, clock, 900, "finish-rest")
        assert done.player_needs[PLAYER]["fatigue"] == 20
        assert done.player_needs[PLAYER]["fatigue_seconds"] == 123
        assert done.player_needs[PLAYER]["hunger"] == 66
        assert done.player_needs[PLAYER]["hunger_seconds"] == 123
        assert player_rest_signal(done, PLAYER) is None
        assert db.verify(WORLD).to_dict() == done.to_dict()
