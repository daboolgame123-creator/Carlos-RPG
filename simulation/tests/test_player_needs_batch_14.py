"""PLAY-14: opt-in deterministic daily player needs, no medical/HP/ST changes."""
from __future__ import annotations

import json

import pytest

from carlos_sim import DomainEvent, PlayerGateway, SQLiteEventStore, TimeEngine, WorldState
from carlos_sim.domain import SCHEMA_VERSION, RULES_VERSION, apply_event
from carlos_sim.player_handoff import player_handoff
from carlos_sim.resumable_play import ResumableTestSession
from carlos_sim.store import IntegrityError, InvalidEvent, RevisionConflict
from carlos_sim.player_needs import (
    HUNGER_SECONDS_PER_POINT, FATIGUE_SECONDS_PER_POINT, HUNGER_RELIEF_PER_FOOD,
)
from living_player_fixture import (
    WORLD, PLAYER, setup_living_foraging_world, living_player_gateway,
)
from test_player_foraging_batch_11 import demo, take


def wait(db, gw, ticks, cid="time"):
    return gw.wait(ticks, command_id=cid,
                   expected_revision=db.load(WORLD).revision)


def eat(db, gw, item="food", cid="meal"):
    return gw.eat(item, command_id=cid,
                  expected_revision=db.load(WORLD).revision)


def test_rule_and_schema_bump_is_explicit_and_rates_use_npc_model():
    assert (SCHEMA_VERSION, RULES_VERSION) == (35, 47)
    assert HUNGER_SECONDS_PER_POINT == 300
    assert FATIGUE_SECONDS_PER_POINT == 600
    assert HUNGER_RELIEF_PER_FOOD == 25


def test_player_needs_explicitly_configured_and_handoff_safe(tmp_path):
    db, clock, gw = demo(tmp_path)
    with db:
        before = db.load(WORLD).to_dict()
        profile = gw.status().details["profile"]
        result = gw.needs()
        assert result.status == "needs"
        assert result.details == {
            "configured": True, "hunger": 25, "fatigue": 10,
            "health_effect": "not_modeled",
        }
        view = player_handoff(gw)
        assert view["player_needs"] == result.details
        assert view["player_status"]["details"]["profile"] == profile
        assert view["revision"] == result.revision
        assert "hunger_seconds" not in json.dumps(view)
        assert "survival_progress" not in json.dumps(view)
        assert "npc_temperaments" not in json.dumps(view)
        assert db.verify(WORLD).to_dict() == before


def test_wait_only_logical_time_progress_and_split_second_remainders(tmp_path):
    db, clock, gw = demo(tmp_path)
    with db:
        wait(db, gw, 299, "part1")
        needs = gw.needs().details
        assert (needs["hunger"], needs["fatigue"]) == (25, 10)
        wait(db, gw, 1, "part2")
        assert (gw.needs().details["hunger"], gw.needs().details["fatigue"]) == (26, 10)
        wait(db, gw, 300, "part3")
        now = db.load(WORLD)
        assert now.time == 600
        assert (gw.needs().details["hunger"], gw.needs().details["fatigue"]) == (27, 11)
        assert now.player_needs[PLAYER]["hunger_seconds"] == 0
        assert now.player_needs[PLAYER]["fatigue_seconds"] == 0
        assert db.verify(WORLD).to_dict() == now.to_dict()


def test_split_step_associativity_under_pure_clock(tmp_path):
    def run(name, durations):
        with SQLiteEventStore(tmp_path / name) as db:
            setup_living_foraging_world(db)
            clock = TimeEngine(db)
            clock.open_session(WORLD)
            for i, duration in enumerate(durations):
                current = db.load(WORLD)
                clock.advance(WORLD, seconds=duration,
                              command_id="tick-"+str(i),
                              expected_revision=current.revision)
            outcome = dict(db.verify(WORLD).player_needs[PLAYER])
            assert db.load(WORLD).time == 1777
            return outcome
    assert run("one.sqlite", [1777]) == run(
        "split.sqlite", [1, 299, 300, 599, 578])


def test_actual_paid_bread_relieves_hunger_only_once(tmp_path):
    db, clock, gw = demo(tmp_path)
    with db:
        state = db.load(WORLD)
        gw.buy("salma-bread", 1, 2, command_id="buy",
               expected_revision=state.revision)
        before = db.load(WORLD)
        hp = before.rpg_profiles[PLAYER]
        npc = before.npcs
        eaten = eat(db, gw, "bread")
        after = db.load(WORLD)
        assert eaten.details["health_effect"] == "not_modeled"
        assert after.resources[PLAYER]["bread"] == 0
        assert gw.needs().details["hunger"] == 0
        assert gw.needs().details["fatigue"] == 10
        assert after.rpg_profiles[PLAYER] == hp
        assert after.npcs == npc
        assert gw.meals().details["total"] == 1
        assert db.verify(WORLD).to_dict() == after.to_dict()


def test_real_forage_60_seconds_then_meal_relieves_hunger_no_stamina(tmp_path):
    db, clock, gw = demo(tmp_path)
    with db:
        take(db, gw, "find-food")
        assert db.load(WORLD).resources[PLAYER]["food"] == 0
        assert gw.needs().details["hunger"] == 25
        wait(db, gw, 60, "search-completion")
        before = db.load(WORLD)
        assert before.resources[PLAYER]["food"] == 1
        assert gw.needs().details["hunger"] == 25
        stamina = before.rpg_profiles[PLAYER]["vitals"]["st"]
        eat(db, gw, "food")
        after = db.load(WORLD)
        assert after.resources[PLAYER]["food"] == 0
        assert after.resources["square"]["wild_food"] == 1
        assert gw.needs().details["hunger"] == 0
        assert after.rpg_profiles[PLAYER]["vitals"]["st"] == stamina
        assert after.rpg_profiles[PLAYER] == before.rpg_profiles[PLAYER]
        assert db.verify(WORLD).to_dict() == after.to_dict()


def test_hunger_fatigue_saturate_at_100_without_injury_or_death(tmp_path):
    db, clock, gw = demo(tmp_path)
    with db:
        start = db.load(WORLD)
        # Use the basic clock: no autonomous NPC speed or need to simulate
        # thousands of NPC decisions just to check a clamped player need.
        clock.advance(WORLD, seconds=61000, command_id="long-day",
                      expected_revision=start.revision)
        after = db.load(WORLD)
        assert gw.needs().details["hunger"] == 100
        assert gw.needs().details["fatigue"] == 100
        assert after.rpg_profiles[PLAYER] == start.rpg_profiles[PLAYER]
        assert after.injuries == start.injuries
        assert db.verify(WORLD).to_dict() == after.to_dict()


def test_time_cannot_move_while_session_closed(tmp_path):
    db, clock, gw = demo(tmp_path)
    with db:
        before = db.load(WORLD).to_dict()
        clock.close_session(WORLD)
        from carlos_sim.time_engine import SessionClosed
        with pytest.raises(SessionClosed):
            wait(db, gw, 3600, "closed")
        assert db.verify(WORLD).to_dict() == before


def test_unknown_remains_unknown_in_nonopted_player_world(tmp_path):
    from test_player_gateway import setup_player_demo_world
    with SQLiteEventStore(tmp_path / "plain.sqlite") as db:
        setup_player_demo_world(db)
        clock = TimeEngine(db)
        clock.open_session("world")
        gw = PlayerGateway(db, clock, world_id="world", player_id="carlos")
        assert gw.needs().details == {
            "configured": False, "hunger": None, "fatigue": None,
            "health_effect": "not_modeled",
        }
        before = db.load("world")
        clock.advance("world", seconds=300, command_id="unconfigured-clock",
                      expected_revision=before.revision)
        assert gw.needs().details["hunger"] is None
        assert db.load("world").player_needs == {}
        assert db.verify("world").to_dict() == db.load("world").to_dict()


def test_meal_without_opted_in_needs_does_not_fabricate_hunger(tmp_path):
    from test_player_gateway import setup_player_demo_world
    with SQLiteEventStore(tmp_path / "plain.sqlite") as db:
        setup_player_demo_world(db)
        initial = db.load("world")
        db.append("world", "known-bread", initial.revision, [
            DomainEvent("ResourceChanged", None, "explicit owned bread zero-to-one",
                        initial.time, {"owner_id": "carlos", "resource": "bread",
                                       "previous": None, "current": 1,
                                       "source": "initialization"})], bootstrap=True)
        clock = TimeEngine(db)
        clock.open_session("world")
        gw = PlayerGateway(db, clock, world_id="world", player_id="carlos")
        consumed = gw.eat("bread", command_id="meal-no-needs",
                          expected_revision=db.load("world").revision)
        assert consumed.status == "ate"
        assert gw.needs().details["hunger"] is None
        assert db.load("world").player_needs == {}
        assert db.verify("world").to_dict() == db.load("world").to_dict()


@pytest.mark.parametrize("who,hunger,fatigue", [
    ("basim", 20, 10), ("unknown", 10, 10),
    ("carlos", True, 10), ("carlos", -1, 10),
    ("carlos", 101, 10), ("carlos", 10, False),
    ("carlos", 10, 101), ("carlos", 10, "10"),
])
def test_invalid_actor_boolean_or_range_initializers_fail_closed(tmp_path, who, hunger, fatigue):
    db, clock, gw = demo(tmp_path)
    with db:
        before = db.load(WORLD)
        forged = DomainEvent("PlayerNeedsInitialized", None, "forged needs",
                             before.time, {"player_id": who, "hunger": hunger,
                                           "fatigue": fatigue})
        with pytest.raises(InvalidEvent):
            db.append(WORLD, "forged-needs", before.revision, [forged],
                      bootstrap=True)
        assert db.verify(WORLD).to_dict() == before.to_dict()


def test_untrusted_bootstrap_or_actor_bound_init_is_denied(tmp_path):
    from test_player_gateway import setup_player_demo_world
    with SQLiteEventStore(tmp_path / "plain.sqlite") as db:
        setup_player_demo_world(db)
        state = db.load("world")
        valid = DomainEvent("PlayerNeedsInitialized", None, "trusted only", 0,
                            {"player_id": "carlos", "hunger": 25, "fatigue": 10})
        actor = DomainEvent("PlayerNeedsInitialized", "carlos", "actor spoof", 0,
                            {"player_id": "carlos", "hunger": 25, "fatigue": 10})
        with pytest.raises(InvalidEvent, match="trusted"):
            db.append("world", "untrusted", state.revision, [valid])
        with pytest.raises(InvalidEvent, match="trusted"):
            db.append("world", "spoof", state.revision, [actor], bootstrap=True)
        after = db.append("world", "explicit-opt-in", state.revision,
                          [valid], bootstrap=True)
        assert after.player_needs["carlos"]["hunger"] == 25
        with pytest.raises(InvalidEvent):
            db.append("world", "again", after.revision, [valid], bootstrap=True)


def test_forged_snapshot_missing_fields_out_of_range_or_npc_needs_refused(tmp_path):
    db, clock, gw = demo(tmp_path)
    with db:
        old = db.load(WORLD).to_dict()
        bad = json.loads(json.dumps(old))
        del bad["player_needs"]
        with pytest.raises(ValueError, match="snapshot"):
            WorldState.from_dict(bad)
        for field, value in (("hunger", 101), ("fatigue", -1),
                             ("hunger_seconds", 300), ("fatigue_seconds", True)):
            bad = json.loads(json.dumps(old))
            bad["player_needs"][PLAYER][field] = value
            with pytest.raises(ValueError, match="player needs"):
                WorldState.from_dict(bad)
        bad = json.loads(json.dumps(old))
        bad["player_needs"]["basim"] = bad["player_needs"].pop(PLAYER)
        with pytest.raises(ValueError, match="player needs"):
            WorldState.from_dict(bad)
        assert db.verify(WORLD).to_dict() == old


def test_independent_players_and_npc_needs_not_disclosed(tmp_path):
    db, clock, gw = demo(tmp_path)
    with db:
        before = db.load(WORLD)
        db.append(WORLD, "add-second-player", before.revision,
                  [DomainEvent("EntityCreated", None, "test other human", before.time,
                               {"id": "pat", "name": "Pat", "controller": "player",
                                "location_id": "square"})], bootstrap=True)
        pat = PlayerGateway(db, clock, world_id=WORLD, player_id="pat")
        assert pat.needs().details["configured"] is False
        current = db.load(WORLD)
        db.append(WORLD, "optin-pat", current.revision,
                  [DomainEvent("PlayerNeedsInitialized", None,
                               "trusted other player opt-in", current.time,
                               {"player_id": "pat", "hunger": 70, "fatigue": 30})],
                  bootstrap=True)
        assert gw.needs().details["hunger"] == 25
        assert pat.needs().details["hunger"] == 70
        view = player_handoff(gw)
        assert view["player_needs"]["hunger"] == 25
        assert "pat" not in json.dumps(view["player_needs"])
        assert "basim" not in json.dumps(view["player_needs"])
        clock.advance(WORLD, seconds=300, command_id="time",
                      expected_revision=db.load(WORLD).revision)
        assert gw.needs().details["hunger"] == 26
        assert pat.needs().details["hunger"] == 71
        assert db.verify(WORLD).to_dict() == db.load(WORLD).to_dict()


def test_food_when_zero_hunger_stays_zero_but_is_spent(tmp_path):
    db, clock, gw = demo(tmp_path)
    with db:
        gw.buy("salma-bread", 2, 2, command_id="two",
               expected_revision=db.load(WORLD).revision)
        eat(db, gw, "bread", "first")
        assert gw.needs().details["hunger"] == 0
        eat(db, gw, "bread", "second")
        assert gw.needs().details["hunger"] == 0
        assert db.load(WORLD).resources[PLAYER]["bread"] == 0
        assert gw.meals().details["total"] == 2


def test_snapshots_resume_preserve_player_needs_and_fractions(tmp_path):
    path = tmp_path / "player-needs.sqlite"
    with ResumableTestSession.create(
        path, WORLD, PLAYER, setup_living_foraging_world, disposable_test=True
    ) as session:
        session.bind_gateway(living_player_gateway(session.store, session.clock))
        session.gateway.wait(349, command_id="before-break",
                             expected_revision=session.store.load(WORLD).revision)
        original = session.handoff()
        frozen = session.store.verify(WORLD).to_dict()
        session.store.snapshot(WORLD)
    with ResumableTestSession.resume(path, WORLD, PLAYER, disposable_test=True) as session:
        session.bind_gateway(living_player_gateway(session.store, session.clock))
        assert session.handoff() == original
        assert session.store.verify(WORLD).to_dict() == frozen
        assert session.gateway.needs().details["hunger"] == 26
        session.gateway.wait(251, command_id="after-break",
                             expected_revision=session.store.load(WORLD).revision)
        assert session.gateway.needs().details["hunger"] == 27
        assert session.gateway.needs().details["fatigue"] == 11
        assert session.store.verify(WORLD).to_dict() == session.store.load(WORLD).to_dict()


def test_bad_event_chain_refused_and_cannot_invent_player_needs(tmp_path):
    db, clock, gw = demo(tmp_path)
    with db:
        before = db.verify(WORLD).to_dict()
        seq, payload = db.db.execute(
            "SELECT seq,payload FROM events WHERE world_id=? AND "
            "payload LIKE '%PlayerNeedsInitialized%' ORDER BY seq LIMIT 1",
            (WORLD,)).fetchone()
        tampered = json.loads(payload)
        tampered["data"]["hunger"] = 99
        db.db.execute("UPDATE events SET payload=? WHERE world_id=? AND seq=?",
                      (json.dumps(tampered), WORLD, seq))
        with pytest.raises(IntegrityError):
            db.verify(WORLD)
        db.db.execute("UPDATE events SET payload=? WHERE world_id=? AND seq=?",
                      (payload, WORLD, seq))
        assert db.verify(WORLD).to_dict() == before


def test_real_temporary_cli_shows_hunger_change_and_no_hp_change():
    from test_play_living_village_batch_02 import _cli, _json_handoffs
    output = _cli(
        "needs\nbuy salma-bread 1 2\nwait 300\nneeds\n"
        "eat bread\nneeds\nhandoff\nquit\n"
    ).stdout
    assert "hunger: 25" in output
    assert "hunger: 26" in output
    assert "hunger: 1" in output
    view = _json_handoffs(output)[0]
    assert view["player_needs"]["hunger"] == 1
    assert view["player_needs"]["fatigue"] == 10
    assert view["player_status"]["details"]["profile"]["vitals"]["hp"] == {
        "current": 12, "max": 12}


def test_resumable_cli_player_need_remains_after_restart(tmp_path):
    from test_play_living_resumable_batch_03 import run_cli, saved_states, backups_list
    path, backups = tmp_path / "world.sqlite", tmp_path / "backups"
    backups.mkdir()
    initial = run_cli(
        "needs\nid time wait 300\nneeds\nhandoff\nquit\n",
        path, backups, "--new", extra=("--disposable-test",))
    before = saved_states(initial.stdout)[0]
    assert before["player_needs"]["hunger"] == 26
    n = len(backups_list(backups))
    assert n == 2
    resumed = run_cli("needs\nhandoff\nquit\n",
                      path, backups, "--resume", extra=("--disposable-test",))
    after = saved_states(resumed.stdout)[0]
    assert before == after
    assert len(backups_list(backups)) == n


def test_seven_npc_autonomy_unchanged_and_no_player_medical_effect(tmp_path):
    db, clock, gw = demo(tmp_path)
    with db:
        initial = db.load(WORLD)
        wait(db, gw, 120, "npc-life")
        now = db.load(WORLD)
        assert PLAYER not in now.npcs
        assert len({a["npc_id"] for a in now.actions.values()}) >= 2
        assert now.rpg_profiles[PLAYER] == initial.rpg_profiles[PLAYER]
        assert now.injuries == initial.injuries
        assert gw.needs().details["configured"] is True
        assert db.verify(WORLD).to_dict() == now.to_dict()
