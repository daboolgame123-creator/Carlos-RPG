"""PLAY-12: 60s player forage, autonomous NPC time, durable competition/replay."""
from __future__ import annotations

import json
import pytest

from carlos_sim import DomainEvent, PlayerGateway, SQLiteEventStore, TimeEngine
from carlos_sim.domain import RULES_VERSION, SCHEMA_VERSION, WorldState, apply_event
from carlos_sim.player_handoff import player_handoff
from carlos_sim.resumable_play import ResumableTestSession
from carlos_sim.store import DuplicateCommand, IntegrityError, InvalidEvent
from carlos_sim.player_foraging import FORAGE_SECONDS
from test_player_foraging_batch_11 import demo, take
from living_player_fixture import (
    WORLD, PLAYER, setup_living_foraging_world, living_player_gateway,
)


def wait(db, gateway, seconds, cid="wait"):
    return gateway.wait(seconds, command_id=cid,
                        expected_revision=db.load(WORLD).revision)


def test_new_rules_without_changing_schema_or_unknown_resources():
    assert SCHEMA_VERSION == 41
    assert RULES_VERSION == 56
    assert FORAGE_SECONDS == 60


def test_start_is_physically_local_and_creates_no_immediate_food(tmp_path):
    db, clock, gateway = demo(tmp_path)
    with db:
        before = db.load(WORLD)
        started = take(db, gateway, "begin")
        state = db.load(WORLD)
        assert started.status == "foraging"
        assert started.details == {"site_id": "square", "remaining_seconds": 60}
        assert state.time == 0 and state.revision == before.revision + 2
        assert state.resources == before.resources
        assert gateway.supplies().details["balances"]["food"] == 0
        assert gateway.check_food().details == {
            "status": "foraging", "location_id": "square", "remaining_seconds": 60}
        assert player_handoff(gateway)["player_local_food"] == gateway.check_food().details
        assert len([s for s in state.scheduled.values()
                    if "__player_forage" in s["payload"]]) == 1
        assert db.verify(WORLD).to_dict() == state.to_dict()


def test_partial_clock_and_npc_autonomy_continue_without_autoplayer(tmp_path):
    db, clock, gateway = demo(tmp_path)
    with db:
        start = db.load(WORLD)
        take(db, gateway)
        first = wait(db, gateway, 59, "partial")
        mid = db.load(WORLD)
        assert first.status == "foraging"
        assert first.details["forage_remaining_seconds"] == 1
        assert mid.time == 59
        assert mid.resources[PLAYER]["food"] == 0
        assert mid.resources["square"]["wild_food"] == 2
        assert PLAYER not in mid.npcs
        assert mid.actions or mid.travels  # autonomous NPC decisions advanced
        assert len({row["npc_id"] for row in mid.actions.values()}) >= 2
        assert db.verify(WORLD).to_dict() == mid.to_dict()
        finished = wait(db, gateway, 1, "finish")
        end = db.load(WORLD)
        assert finished.status == "ready"
        assert finished.details["forage_result"] == "collected"
        assert finished.details["forage_site_id"] == "square"
        assert end.time == 60
        assert end.resources[PLAYER]["food"] == 1
        assert end.resources["square"]["wild_food"] == 1
        assert db.verify(WORLD).to_dict() == end.to_dict()


def test_long_wait_completes_once_and_time_continues(tmp_path):
    db, clock, gateway = demo(tmp_path)
    with db:
        take(db, gateway)
        result = wait(db, gateway, 180, "long-wait")
        assert result.status == "ready"
        assert result.details["forage_result"] == "collected"
        state = db.load(WORLD)
        assert state.time == 180
        assert state.resources[PLAYER]["food"] == 1
        assert state.resources["square"]["wild_food"] == 1
        assert all("__player_forage" not in s["payload"] for s in state.scheduled.values())
        assert db.verify(WORLD).to_dict() == state.to_dict()


def test_busy_player_cannot_teleport_trade_gift_talk_or_research(tmp_path):
    db, clock, gateway = demo(tmp_path)
    with db:
        take(db, gateway, "busy")
        original = db.load(WORLD).to_dict()
        for command in (
            lambda: take(db, gateway, "second"),
            lambda: gateway.move("square-woods", command_id="moving",
                                 expected_revision=db.load(WORLD).revision),
            lambda: gateway.observe(command_id="extra-look",
                                    expected_revision=db.load(WORLD).revision),
            lambda: gateway.interact("basim", kind="greeting", text="Hi",
                                     command_id="chat",
                                     expected_revision=db.load(WORLD).revision),
            lambda: gateway.ask_food("basim", "square", command_id="ask",
                                     expected_revision=db.load(WORLD).revision),
            lambda: gateway.give("salma", "coin_copper", 1, command_id="gift",
                                 expected_revision=db.load(WORLD).revision),
            lambda: gateway.buy("salma-bread", 1, 2, command_id="buy",
                                expected_revision=db.load(WORLD).revision),
        ):
            with pytest.raises(ValueError, match="foraging"):
                command()
        assert db.verify(WORLD).to_dict() == original
        assert gateway.supplies().details["balances"]["food"] == 0
        wait(db, gateway, 60, "released")
        assert gateway.check_food().details["status"] == "present"


def test_duplicate_command_cannot_restart_or_skip_timed_search(tmp_path):
    db, clock, gateway = demo(tmp_path)
    with db:
        take(db, gateway, "same")
        before = db.load(WORLD).to_dict()
        with pytest.raises(DuplicateCommand):
            take(db, gateway, "same")
        assert db.verify(WORLD).to_dict() == before
        wait(db, gateway, 60, "done")
        with pytest.raises(DuplicateCommand):
            take(db, gateway, "same")
        assert gateway.supplies().details["balances"]["food"] == 1


def test_protected_signal_cannot_be_forged_or_shortened(tmp_path):
    db, clock, gateway = demo(tmp_path)
    with db:
        state = db.load(WORLD)
        bad = DomainEvent("ScheduledEventCreated", None, "fake", 0, {
            "id": "player-forage:carlos:fake", "due": 1,
            "order": state.next_schedule_order, "kind": "signal",
            "interrupt": False,
            "payload": {"__player_forage": {
                "player_id": PLAYER, "site_id": "square", "started_at": 0}},
        })
        with pytest.raises(InvalidEvent, match="observation|trusted"):
            db.append(WORLD, "bad-signal", state.revision, [bad],
                      action_authorized=True, movement_authorized=True)
        with pytest.raises(ValueError, match="forage"):
            apply_event(state, bad, action_authorized=True)
        assert db.verify(WORLD).to_dict() == state.to_dict()


def test_schedule_cannot_be_cancelled_or_collected_instantly(tmp_path):
    db, clock, gateway = demo(tmp_path)
    with db:
        take(db, gateway, "protected")
        current = db.load(WORLD)
        signal_id = next(ident for ident, s in current.scheduled.items()
                         if "__player_forage" in s["payload"])
        with pytest.raises(InvalidEvent, match="cannot cancel"):
            clock.cancel(WORLD, signal_id, command_id="cancel",
                         expected_revision=current.revision)
        raw = DomainEvent("PlayerFoodCollected", PLAYER, "legacy", current.time,
                          {"site_id": "square", "quantity": 1})
        with pytest.raises(ValueError, match="instant"):
            apply_event(current, raw, action_authorized=True)
        assert db.verify(WORLD).to_dict() == current.to_dict()


def test_three_independent_players_compete_for_two_finite_units(tmp_path):
    db, clock, carlos = demo(tmp_path)
    with db:
        state = db.load(WORLD)
        events = []
        for who in ("pat", "eli"):
            events.extend([
                DomainEvent("EntityCreated", None, "test contender", state.time,
                    {"id": who, "name": who.capitalize(),
                     "controller": "player", "location_id": "square"}),
                DomainEvent("ResourceChanged", None, "test initialized zero", state.time,
                    {"owner_id": who, "resource": "food", "previous": None,
                     "current": 0, "source": "initialization"}),
            ])
        db.append(WORLD, "more-players", state.revision, events, bootstrap=True)
        pat = PlayerGateway(db, clock, world_id=WORLD, player_id="pat")
        eli = PlayerGateway(db, clock, world_id=WORLD, player_id="eli")
        take(db, carlos, "carlos-first")
        take(db, pat, "pat-second")
        take(db, eli, "eli-third")
        assert db.load(WORLD).resources["square"]["wild_food"] == 2
        result = wait(db, carlos, 60, "all-three-due")
        final = db.load(WORLD)
        assert result.details["forage_result"] == "collected"
        assert final.resources[PLAYER]["food"] == 1
        assert final.resources["pat"]["food"] == 1
        assert final.resources["eli"]["food"] == 0
        assert final.resources["square"]["wild_food"] == 0
        assert sum(final.resources[x]["food"] for x in (PLAYER, "pat", "eli")) == 2
        assert carlos.check_food().details["status"] == "empty"
        assert db.verify(WORLD).to_dict() == final.to_dict()


def test_snapshot_reopen_mid_search_no_wall_clock_and_one_completion(tmp_path):
    path = tmp_path / "timed.sqlite"
    with ResumableTestSession.create(
        path, WORLD, PLAYER, setup_living_foraging_world, disposable_test=True
    ) as session:
        session.bind_gateway(living_player_gateway(session.store, session.clock))
        take(session.store, session.gateway, "begin")
        wait(session.store, session.gateway, 25, "partial")
        original = session.handoff()
        frozen = session.store.verify(WORLD).to_dict()
        session.store.snapshot(WORLD)
    with ResumableTestSession.resume(path, WORLD, PLAYER, disposable_test=True) as session:
        session.bind_gateway(living_player_gateway(session.store, session.clock))
        assert session.store.verify(WORLD).to_dict() == frozen
        assert session.handoff() == original
        assert session.gateway.check_food().details["remaining_seconds"] == 35
        result = wait(session.store, session.gateway, 35, "resume-finish")
        assert result.details["forage_result"] == "collected"
        assert session.store.verify(WORLD).time == 60
        assert session.store.load(WORLD).resources[PLAYER]["food"] == 1


def test_forged_snapshot_schedule_and_damaged_event_chain_fail_closed(tmp_path):
    db, clock, gateway = demo(tmp_path)
    with db:
        take(db, gateway, "tamper")
        current = db.load(WORLD).to_dict()
        raw = json.loads(json.dumps(current))
        signal = next(s for s in raw["scheduled"].values()
                      if "__player_forage" in s["payload"])
        signal["due"] = 1
        with pytest.raises(ValueError, match="forage"):
            WorldState.from_dict(raw)
        before = db.verify(WORLD).to_dict()
        rows = list(db.db.execute(
            "SELECT seq,payload FROM events WHERE world_id=? AND command_id=?",
            (WORLD, "player-forage:tamper")))
        seq, original = rows[-1]
        forged = json.loads(original)
        forged["data"]["due"] = 1
        db.db.execute("UPDATE events SET payload=? WHERE world_id=? AND seq=?",
                      (json.dumps(forged), WORLD, seq))
        with pytest.raises(IntegrityError):
            db.verify(WORLD)
        db.db.execute("UPDATE events SET payload=? WHERE world_id=? AND seq=?",
                      (original, WORLD, seq))
        assert db.verify(WORLD).to_dict() == before


def test_plain_clock_fires_real_foraging_at_due_without_npc_planning(tmp_path):
    db, clock, gateway = demo(tmp_path)
    with db:
        take(db, gateway)
        state = db.load(WORLD)
        clock.advance(WORLD, seconds=60, command_id="raw-clock",
                      expected_revision=state.revision)
        result = db.load(WORLD)
        assert result.time == 60
        assert result.resources[PLAYER]["food"] == 1
        assert result.resources["square"]["wild_food"] == 1
        assert db.verify(WORLD).to_dict() == result.to_dict()


def test_real_temporary_cli_wait_required_before_food_owned():
    from test_play_living_village_batch_02 import _cli, _json_handoffs
    out = _cli("forage\nsupplies\ncheckfood\nwait 59\nsupplies\n"
               "wait 1\nsupplies\nhandoff\nquit\n").stdout
    assert "foraging" in out
    assert "forage_remaining_seconds: 1" in out
    assert "forage_result: collected" in out
    views = _json_handoffs(out)
    assert views[0]["player_supplies"]["balances"]["food"] == 1


def test_saved_cli_wait_resumes_and_finishes_without_extra_pick(tmp_path):
    from test_play_living_resumable_batch_03 import run_cli, saved_states, backups_list
    path, backups = tmp_path / "game.sqlite", tmp_path / "checkpoints"
    backups.mkdir()
    before = run_cli("id start forage\nid half wait 30\nhandoff\nquit\n",
                     path, backups, "--new", extra=("--disposable-test",))
    snapshot = saved_states(before.stdout)[0]
    assert snapshot["player_local_food"]["remaining_seconds"] == 30
    n = len(backups_list(backups))
    after = run_cli("id finish wait 30\nhandoff\nquit\n",
                    path, backups, "--resume", extra=("--disposable-test",))
    assert "forage_result: collected" in after.stdout
    assert saved_states(after.stdout)[0]["player_supplies"]["balances"]["food"] == 1
    assert len(backups_list(backups)) == n + 1



def test_prevent_backdated_shortcuts_at_schedule_creation(tmp_path):
    from carlos_sim.movement import _visible
    db, clock, gateway = demo(tmp_path)
    with db:
        wait(db, gateway, 100, "establish-world-time")
        state = db.load(WORLD)
        assert state.time == 100
        instant = DomainEvent("ScheduledEventCreated", None,
                              "fraudulent old start", state.time, {
            "id": "player-forage:carlos:backdate",
            "due": state.time + 10,
            "order": state.next_schedule_order,
            "kind": "signal", "interrupt": False,
            "payload": {"__player_forage": {
                "player_id": PLAYER, "site_id": "square",
                "started_at": state.time - 50}},
        })
        with pytest.raises(ValueError, match="current world time"):
            apply_event(state, instant, action_authorized=True)
        prior = state.to_dict()
        sight = DomainEvent("PlayerObserved", PLAYER, "local witness",
                            state.time, {
            "location_id": "square",
            "occupants": _visible(state.to_dict(), "square")})
        with pytest.raises(InvalidEvent, match="current world time"):
            db.append(WORLD, "backdate-attempt", state.revision,
                      [sight, instant], action_authorized=True,
                      movement_authorized=True)
        assert db.verify(WORLD).to_dict() == prior
