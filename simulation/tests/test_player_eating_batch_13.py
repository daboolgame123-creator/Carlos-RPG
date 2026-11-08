"""PLAY-13: owned food/bread is consumed exactly once, without invented health."""
from __future__ import annotations

import json
import pytest

from carlos_sim import DomainEvent, PlayerGateway, SQLiteEventStore, TimeEngine
from carlos_sim.domain import SCHEMA_VERSION, RULES_VERSION, apply_event
from carlos_sim.player_handoff import player_handoff
from carlos_sim.resumable_play import ResumableTestSession
from carlos_sim.store import DuplicateCommand, InvalidEvent, IntegrityError, RevisionConflict
from test_player_foraging_batch_11 import demo, take
from living_player_fixture import (
    WORLD, PLAYER, setup_living_foraging_world, setup_living_player_world,
    living_player_gateway,
)


def consume(db, gateway, food="food", cid="eat"):
    return gateway.eat(food, command_id=cid,
                       expected_revision=db.load(WORLD).revision)


def harvest(db, gateway, cid="forage"):
    take(db, gateway, cid)
    done = gateway.wait(60, command_id="complete-"+cid,
                        expected_revision=db.load(WORLD).revision)
    assert done.details["forage_result"] == "collected"


def test_rule_version_and_no_implicit_nutrition():
    assert SCHEMA_VERSION == 41 and RULES_VERSION == 55


def test_earned_food_eaten_once_and_replay_exact(tmp_path):
    db, clock, g = demo(tmp_path)
    with db:
        harvest(db, g)
        prior = db.load(WORLD)
        previous_profile = prior.rpg_profiles[PLAYER]
        previous_npcs = prior.npcs
        previous_food = prior.resources[PLAYER]["food"]
        done = consume(db, g)
        after = db.load(WORLD)
        assert done.status == "ate"
        assert done.details == {
            "resource": "food", "quantity": 1, "remaining_owned": 0,
            "health_effect": "not_modeled"}
        assert after.revision == prior.revision + 1
        assert after.time == prior.time
        assert after.resources[PLAYER]["food"] == previous_food - 1 == 0
        assert after.resources["square"]["wild_food"] == 1
        assert after.rpg_profiles[PLAYER] == previous_profile
        assert after.npcs == previous_npcs
        assert g.meals().details == {"total": 1, "recent": (
            {"resource": "food", "quantity": 1, "consumed_at": after.time},)}
        assert db.verify(WORLD).to_dict() == after.to_dict()


def test_bought_bread_is_edible_without_extra_money_or_hp(tmp_path):
    db, clock, g = demo(tmp_path)
    with db:
        initial = db.load(WORLD)
        bought = g.buy("salma-bread", 1, 2, command_id="purchase",
                       expected_revision=initial.revision)
        assert bought.status == "purchased"
        prior = db.load(WORLD)
        assert prior.resources[PLAYER]["bread"] == 1
        assert prior.resources[PLAYER]["coin_copper"] == 8
        assert prior.resources["salma"]["bread"] == 2
        status = g.status().details
        consumed = consume(db, g, "bread", "bread-eaten")
        now = db.load(WORLD)
        assert consumed.details["remaining_owned"] == 0
        assert now.resources[PLAYER]["bread"] == 0
        assert now.resources[PLAYER]["coin_copper"] == 8
        assert now.resources["salma"]["bread"] == 2
        assert g.status().details == status
        assert g.meals().details["recent"][0]["resource"] == "bread"
        assert db.verify(WORLD).to_dict() == now.to_dict()


def test_eating_cannot_create_food_or_restore_empty_balance(tmp_path):
    db, clock, g = demo(tmp_path)
    with db:
        initial = db.load(WORLD).to_dict()
        with pytest.raises(ValueError, match="absent, unknown or exhausted"):
            consume(db, g)
        with pytest.raises(ValueError, match="absent, unknown or exhausted"):
            consume(db, g, "bread", "bread-zero")
        assert db.verify(WORLD).to_dict() == initial
        assert g.meals().details == {"total": 0, "recent": ()}


@pytest.mark.parametrize("resource", [
    "", "coin_copper", "wild_food", "labor_units", "investigation_attempts",
    "Food", None, 123, True,
])
def test_unapproved_resource_cannot_be_eaten(tmp_path, resource):
    db, clock, g = demo(tmp_path)
    with db:
        before = db.load(WORLD).to_dict()
        with pytest.raises(ValueError, match="only owned food or bread"):
            consume(db, g, resource, "invalid-resource")
        assert db.verify(WORLD).to_dict() == before


@pytest.mark.parametrize("resource,quantity", [
    ("food", 0), ("food", 2), ("food", True), ("food", -1),
    ("food", None), ("bread", "1"), ("coin_copper", 1),
    ("wild_food", 1),
])
def test_forged_amount_and_nonfood_are_rejected(tmp_path, resource, quantity):
    db, clock, g = demo(tmp_path)
    with db:
        before = db.load(WORLD)
        forged = DomainEvent("PlayerFoodEaten", PLAYER, "forged meal", before.time,
                             {"resource": resource, "quantity": quantity})
        with pytest.raises(ValueError):
            apply_event(before, forged, consumption_authorized=True)
        with pytest.raises(InvalidEvent):
            db.append(WORLD, "forged-meal", before.revision, [forged],
                      consumption_authorized=True)
        assert db.verify(WORLD).to_dict() == before.to_dict()


def test_untrusted_or_closed_session_cannot_eat(tmp_path):
    db, clock, g = demo(tmp_path)
    with db:
        event = DomainEvent("PlayerFoodEaten", PLAYER, "forged", 0,
                            {"resource": "bread", "quantity": 1})
        before = db.load(WORLD)
        with pytest.raises(InvalidEvent, match="trusted"):
            db.append(WORLD, "not-authorized", before.revision, [event])
        clock.close_session(WORLD)
        with pytest.raises(InvalidEvent, match="active"):
            db.append(WORLD, "not-playing", before.revision, [event],
                      consumption_authorized=True)
        assert db.verify(WORLD).to_dict() == before.to_dict()


def test_npc_cannot_impersonate_carlos_or_consume_his_food(tmp_path):
    db, clock, g = demo(tmp_path)
    with db:
        harvest(db, g)
        original = db.load(WORLD)
        impostor = PlayerGateway(db, clock, world_id=WORLD, player_id="basim")
        with pytest.raises(PermissionError):
            consume(db, impostor, "food", "basim-eats")
        bad = DomainEvent("PlayerFoodEaten", "basim", "npc forged", original.time,
                          {"resource": "food", "quantity": 1})
        with pytest.raises(ValueError, match="real player"):
            apply_event(original, bad, consumption_authorized=True)
        assert db.verify(WORLD).to_dict() == original.to_dict()


def test_travel_and_search_block_eating_without_leaking_resources(tmp_path):
    db, clock, g = demo(tmp_path)
    with db:
        g.buy("salma-bread", 1, 2, command_id="bread", expected_revision=db.load(WORLD).revision)
        take(db, g, "while-foraging")
        busy = db.load(WORLD).to_dict()
        with pytest.raises(ValueError, match="foraging"):
            consume(db, g, "bread", "busy-eat")
        assert db.verify(WORLD).to_dict() == busy
        g.wait(60, command_id="forage-finishes",
               expected_revision=db.load(WORLD).revision)
        g.move("square-woods", command_id="travel",
               expected_revision=db.load(WORLD).revision)
        traveling = db.load(WORLD).to_dict()
        with pytest.raises(ValueError, match="travelling"):
            consume(db, g, "bread", "travel-eat")
        assert db.verify(WORLD).to_dict() == traveling
        g.wait(50, command_id="arrive", expected_revision=db.load(WORLD).revision)
        done = consume(db, g, "bread", "safe-eat")
        assert done.status == "ate"


def test_stale_revision_and_duplicate_request_prevent_double_eating(tmp_path):
    db, clock, g = demo(tmp_path)
    with db:
        harvest(db, g)
        original_revision = db.load(WORLD).revision
        consume(db, g, "food", "used-once")
        once = db.load(WORLD).to_dict()
        with pytest.raises(DuplicateCommand):
            consume(db, g, "food", "used-once")
        with pytest.raises(RevisionConflict):
            g.eat("food", command_id="stale",
                  expected_revision=original_revision)
        assert db.verify(WORLD).to_dict() == once


def test_history_only_actual_meals_and_readonly_handoff(tmp_path):
    db, clock, g = demo(tmp_path)
    with db:
        g.buy("salma-bread", 2, 2, command_id="bread-twice",
              expected_revision=db.load(WORLD).revision)
        consume(db, g, "bread", "first-meal")
        before = db.load(WORLD).to_dict()
        a = g.meals().details
        b = g.meals().details
        view = player_handoff(g)
        assert a == b
        assert a == {"total": 1, "recent": (
            {"resource": "bread", "quantity": 1, "consumed_at": 0},)}
        assert view["player_meals"] == a
        assert view["player_supplies"]["balances"]["bread"] == 1
        assert "npc_temperaments" not in json.dumps(view)
        assert view["player_needs"]["hunger"] == "not_modeled"
        assert "hunger" not in json.dumps(view["player_status"])
        assert db.verify(WORLD).to_dict() == before


@pytest.mark.parametrize("limit", [0, -1, 21, False, True, None, "2"])
def test_meal_history_bounded_and_typechecked(tmp_path, limit):
    db, clock, g = demo(tmp_path)
    with db:
        with pytest.raises(ValueError, match="meal history limit"):
            g.meals(limit)


def test_multiple_meals_last_five_handoff_and_no_npc_food_exposure(tmp_path):
    db, clock, g = demo(tmp_path)
    with db:
        g.buy("salma-bread", 3, 2, command_id="buy-three",
              expected_revision=db.load(WORLD).revision)
        for index in range(3):
            consume(db, g, "bread", "meal-"+str(index))
        assert g.meals(limit=2).details["total"] == 3
        assert len(g.meals(limit=2).details["recent"]) == 2
        view = player_handoff(g)
        assert view["player_meals"]["total"] == 3
        assert len(view["player_meals"]["recent"]) == 3
        assert view["player_supplies"]["balances"]["bread"] == 0
        assert "nora" not in json.dumps(view["player_meals"])
        assert db.verify(WORLD).to_dict() == db.load(WORLD).to_dict()


def test_meal_survives_snapshot_and_session_resume(tmp_path):
    path = tmp_path / "meals.sqlite"
    with ResumableTestSession.create(
        path, WORLD, PLAYER, setup_living_foraging_world, disposable_test=True
    ) as session:
        session.bind_gateway(living_player_gateway(session.store, session.clock))
        gateway = session.gateway
        gateway.buy("salma-bread", 1, 2, command_id="buy",
                    expected_revision=session.store.load(WORLD).revision)
        consume(session.store, gateway, "bread", "eat-after-buy")
        handoff = session.handoff()
        state = session.store.verify(WORLD).to_dict()
        session.store.snapshot(WORLD)
    with ResumableTestSession.resume(path, WORLD, PLAYER, disposable_test=True) as session:
        session.bind_gateway(living_player_gateway(session.store, session.clock))
        assert session.handoff() == handoff
        assert session.store.verify(WORLD).to_dict() == state
        assert session.gateway.meals().details["total"] == 1
        with pytest.raises(DuplicateCommand):
            consume(session.store, session.gateway, "bread", "eat-after-buy")


def test_tampered_food_event_refused_by_full_replay(tmp_path):
    db, clock, g = demo(tmp_path)
    with db:
        g.buy("salma-bread", 1, 2, command_id="buy",
              expected_revision=db.load(WORLD).revision)
        consume(db, g, "bread", "verified")
        original_world = db.verify(WORLD).to_dict()
        seq, payload = db.db.execute(
            "SELECT seq,payload FROM events WHERE world_id=? AND command_id=?",
            (WORLD, "player-eat:verified")).fetchone()
        corrupted = json.loads(payload)
        corrupted["data"]["resource"] = "coin_copper"
        db.db.execute("UPDATE events SET payload=? WHERE world_id=? AND seq=?",
                      (json.dumps(corrupted), WORLD, seq))
        with pytest.raises(IntegrityError):
            db.verify(WORLD)
        db.db.execute("UPDATE events SET payload=? WHERE world_id=? AND seq=?",
                      (payload, WORLD, seq))
        assert db.verify(WORLD).to_dict() == original_world


def test_living_npcs_continue_their_life_no_automatic_player_meals(tmp_path):
    db, clock, g = demo(tmp_path)
    with db:
        initial = db.load(WORLD)
        g.wait(180, command_id="other-people-work",
               expected_revision=initial.revision)
        now = db.load(WORLD)
        assert PLAYER not in now.npcs
        assert len({a["npc_id"] for a in now.actions.values()}) >= 2
        assert g.meals().details["total"] == 0
        assert now.resources[PLAYER]["food"] == 0
        assert db.verify(WORLD).to_dict() == now.to_dict()


def test_disposable_temporary_cli_buys_eats_and_shows_receipt():
    from test_play_living_village_batch_02 import _cli, _json_handoffs
    output = _cli("buy salma-bread 1 2\neat bread\nmeals\nsupplies\nhandoff\nquit\n").stdout
    assert "purchased" in output
    assert "ate" in output
    views = _json_handoffs(output)
    assert len(views) == 1
    assert views[0]["player_meals"]["total"] == 1
    assert views[0]["player_meals"]["recent"][0]["resource"] == "bread"
    assert views[0]["player_supplies"]["balances"]["bread"] == 0


def test_resumable_cli_meal_checkpoint_and_duplicate_rejected(tmp_path):
    from test_play_living_resumable_batch_03 import run_cli, saved_states, backups_list
    file, backups = tmp_path / "world.sqlite", tmp_path / "checkpoints"
    backups.mkdir()
    initial = run_cli(
        "id paid1 buy salma-bread 1 2\nid meal1 eat bread\n"
        "meals\nhandoff\nquit\n",
        file, backups, "--new", extra=("--disposable-test",))
    v = saved_states(initial.stdout)
    assert len(v) == 1 and v[0]["player_meals"]["total"] == 1
    assert v[0]["player_supplies"]["balances"]["bread"] == 0
    checkpoints = len(backups_list(backups))
    assert checkpoints == 3  # initial + one buy + one meal
    replay = run_cli("id meal1 eat bread\nmeals\nhandoff\nquit\n",
                     file, backups, "--resume", extra=("--disposable-test",))
    assert "Rejected:" in replay.stdout
    assert saved_states(replay.stdout) == v
    assert len(backups_list(backups)) == checkpoints
