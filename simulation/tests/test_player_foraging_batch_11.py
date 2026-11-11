"""PLAY-11: physically local, finite player-owned wild-food pickup."""
import json
import pytest
from carlos_sim import DomainEvent, PlayerGateway, SQLiteEventStore, TimeEngine
from carlos_sim.domain import apply_event, SCHEMA_VERSION, RULES_VERSION
from carlos_sim.player_handoff import player_handoff
from carlos_sim.resumable_play import ResumableTestSession
from carlos_sim.store import DuplicateCommand, InvalidEvent, RevisionConflict
from test_player_market_batch_05 import WORLD, PLAYER, living_player_gateway, setup_living_player_world
from living_player_fixture import setup_living_foraging_world


def demo(tmp_path):
    db = SQLiteEventStore(tmp_path / "play11.sqlite")
    setup_living_foraging_world(db)
    clock = TimeEngine(db)
    clock.open_session(WORLD)
    return db, clock, living_player_gateway(db, clock)


def take(db, gateway, ident="pick"):
    return gateway.forage(command_id=ident, expected_revision=db.load(WORLD).revision)


def test_version_and_local_survey_readonly(tmp_path):
    assert (SCHEMA_VERSION, RULES_VERSION) == (44, 59)
    db, clock, g = demo(tmp_path)
    with db:
        before = db.load(WORLD).to_dict()
        assert g.check_food().details == {"location_id": "square", "status": "present"}
        assert g.supplies().details["balances"]["food"] == 0
        assert player_handoff(g)["player_local_food"] == g.check_food().details
        assert "woods" not in str(g.check_food().details)
        assert db.verify(WORLD).to_dict() == before


def test_atomic_pick_and_provenance_conserve_real_food(tmp_path):
    db, clock, g = demo(tmp_path)
    with db:
        initial = db.load(WORLD)
        out = take(db, g)
        waiting = db.load(WORLD)
        assert out.status == "foraging" and out.revision == initial.revision + 2
        assert out.details == {"site_id": "square", "remaining_seconds": 60}
        assert waiting.time == 0
        assert waiting.resources["square"]["wild_food"] == 2
        assert waiting.resources[PLAYER]["food"] == 0
        assert g.check_food().details["status"] == "foraging"
        kinds = [json.loads(p)["event_type"] for (p,) in db.db.execute(
            "SELECT payload FROM events WHERE world_id=? AND command_id=? ORDER BY seq",
            (WORLD, "player-forage:pick"))]
        assert kinds == ["PlayerObserved", "ScheduledEventCreated"]
        finished = g.wait(60, command_id="complete-pick",
                          expected_revision=waiting.revision)
        now = db.load(WORLD)
        assert finished.details["forage_result"] == "collected"
        assert finished.details["forage_site_id"] == "square"
        assert now.time == 60
        assert now.resources["square"]["wild_food"] == 1
        assert now.resources[PLAYER]["food"] == 1
        assert now.resources["woods"]["wild_food"] == 4
        assert now.resources["salma"]["bread"] == 3
        assert now.rpg_profiles[PLAYER]["inventory"] == {}
        assert db.verify(WORLD).to_dict() == now.to_dict()

def test_depleted_site_has_no_partial_observation_or_resource_creation(tmp_path):
    db, clock, g = demo(tmp_path)
    with db:
        take(db, g, "one")
        g.wait(60, command_id="first-done", expected_revision=db.load(WORLD).revision)
        take(db, g, "two")
        g.wait(60, command_id="second-done", expected_revision=db.load(WORLD).revision)
        assert g.check_food().details["status"] == "empty"
        before = db.load(WORLD).to_dict()
        with pytest.raises(ValueError, match="no initialized"):
            take(db, g, "three")
        assert db.verify(WORLD).to_dict() == before
        assert g.supplies().details["balances"]["food"] == 2

def test_woods_needs_real_travel_and_time_not_rumor(tmp_path):
    db, clock, g = demo(tmp_path)
    with db:
        g.move("square-woods", command_id="go",
               expected_revision=db.load(WORLD).revision)
        assert g.check_food().details == {"status": "traveling"}
        with pytest.raises(ValueError, match="travelling"):
            take(db, g, "during-travel")
        g.wait(50, command_id="reach", expected_revision=db.load(WORLD).revision)
        assert g.check_food().details == {"location_id": "woods", "status": "present"}
        before = db.load(WORLD)
        result = take(db, g, "woods")
        assert result.status == "foraging"
        assert db.load(WORLD).resources["woods"]["wild_food"] == before.resources["woods"]["wild_food"]
        done = g.wait(60, command_id="woods-finish",
                      expected_revision=db.load(WORLD).revision)
        after = db.load(WORLD)
        assert done.details["forage_result"] == "collected"
        assert after.resources["woods"]["wild_food"] == before.resources["woods"]["wild_food"] - 1
        assert after.resources[PLAYER]["food"] == before.resources[PLAYER]["food"] + 1
        assert db.verify(WORLD).to_dict() == after.to_dict()

def test_plain_demo_preserves_unknown_food_not_zero(tmp_path):
    with SQLiteEventStore(tmp_path / "plain.sqlite") as db:
        setup_living_player_world(db)
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        g = living_player_gateway(db, clock)
        before = db.load(WORLD).to_dict()
        assert g.check_food().details["status"] == "unknown"
        with pytest.raises(ValueError):
            take(db, g)
        assert db.verify(WORLD).to_dict() == before


@pytest.mark.parametrize("actor,site,qty", [
    ("nora", "bakery", 1), ("carlos", "woods", 1),
    ("carlos", "square", 2), ("carlos", "square", True),
    ("carlos", "square", 0), ("carlos", "bakery", 1),
])
def test_fake_person_or_remote_or_bad_quantity_is_rejected(tmp_path, actor, site, qty):
    db, clock, g = demo(tmp_path)
    with db:
        state = db.load(WORLD)
        event = DomainEvent("PlayerFoodCollected", actor, "fraud", state.time,
                            {"site_id": site, "quantity": qty})
        with pytest.raises(ValueError):
            apply_event(state, event, action_authorized=True)
        with pytest.raises(InvalidEvent):
            db.append(WORLD, "fraud", state.revision, [event], action_authorized=True)
        assert db.verify(WORLD).to_dict() == state.to_dict()


def test_npc_cannot_obtain_human_gateway(tmp_path):
    db, clock, g = demo(tmp_path)
    with db:
        other = PlayerGateway(db, clock, world_id=WORLD, player_id="basim")
        before = db.load(WORLD).to_dict()
        with pytest.raises(PermissionError):
            other.forage(command_id="fraud", expected_revision=before["revision"])
        assert db.verify(WORLD).to_dict() == before


def test_raw_trusted_collection_requires_matching_observation(tmp_path):
    db, clock, g = demo(tmp_path)
    with db:
        state = db.load(WORLD)
        raw = DomainEvent("PlayerFoodCollected", PLAYER, "no observation", state.time,
                          {"site_id": "square", "quantity": 1})
        with pytest.raises(InvalidEvent, match="observation"):
            db.append(WORLD, "no-sight", state.revision, [raw], action_authorized=True)
        with pytest.raises(InvalidEvent, match="trusted"):
            db.append(WORLD, "no-capability", state.revision, [raw])
        clock.close_session(WORLD)
        with pytest.raises(InvalidEvent, match="active"):
            db.append(WORLD, "closed", state.revision, [raw], action_authorized=True)
        assert db.verify(WORLD).to_dict() == state.to_dict()


def test_duplicate_and_stale_revision_cannot_mint_food(tmp_path):
    db, clock, g = demo(tmp_path)
    with db:
        old = db.load(WORLD).revision
        take(db, g, "first")
        after = db.load(WORLD).to_dict()
        with pytest.raises(DuplicateCommand):
            take(db, g, "first")
        with pytest.raises(RevisionConflict):
            g.forage(command_id="stale", expected_revision=old)
        assert db.verify(WORLD).to_dict() == after


def test_snapshot_reopen_keeps_food_and_npcs(tmp_path):
    path = tmp_path / "resume.sqlite"
    with ResumableTestSession.create(
        path, WORLD, PLAYER, setup_living_foraging_world, disposable_test=True
    ) as session:
        session.bind_gateway(living_player_gateway(session.store, session.clock))
        take(session.store, session.gateway, "persistent")
        view = session.handoff()
        state = session.store.verify(WORLD).to_dict()
        session.store.snapshot(WORLD)
    with ResumableTestSession.resume(path, WORLD, PLAYER, disposable_test=True) as session:
        session.bind_gateway(living_player_gateway(session.store, session.clock))
        assert session.handoff() == view
        assert session.store.verify(WORLD).to_dict() == state
        assert session.gateway.supplies().details["balances"]["food"] == 0
        done = session.gateway.wait(60, command_id="resumed-completion",
            expected_revision=session.store.load(WORLD).revision)
        assert done.details["forage_result"] == "collected"
        assert session.gateway.supplies().details["balances"]["food"] == 1

def test_temporary_cli_actual_food_and_no_third_pick():
    from test_play_living_village_batch_02 import _cli, _json_handoffs
    output = _cli(
        "checkfood\nforage\nwait 60\nforage\nwait 60\n"
        "forage\nsupplies\nhandoff\nquit\n"
    ).stdout
    assert output.count("foraging") >= 2
    assert output.count("forage_result: collected") == 2
    assert "Rejected: no initialized" in output
    views = _json_handoffs(output)
    assert views[0]["player_local_food"]["status"] == "empty"
    assert views[0]["player_supplies"]["balances"]["food"] == 2

def test_resumable_cli_rejects_duplicate_after_restart_without_checkpoint(tmp_path):
    from test_play_living_resumable_batch_03 import run_cli, saved_states, backups_list
    file, backups = tmp_path / "world.sqlite", tmp_path / "checkpoints"
    backups.mkdir()
    first = run_cli("checkfood\nid pick1 forage\nhandoff\nquit\n",
                    file, backups, "--new", extra=("--disposable-test",))
    views = saved_states(first.stdout)
    assert views[0]["player_supplies"]["balances"]["food"] == 0
    assert views[0]["player_local_food"]["status"] == "foraging"
    n = len(backups_list(backups))
    assert n == 2
    again = run_cli("checkfood\nid pick1 forage\nhandoff\nquit\n",
                    file, backups, "--resume", extra=("--disposable-test",))
    assert "Rejected:" in again.stdout
    assert saved_states(again.stdout) == views
    assert len(backups_list(backups)) == n
    last = run_cli("id completion wait 60\nhandoff\nquit\n",
                    file, backups, "--resume", extra=("--disposable-test",))
    assert "forage_result: collected" in last.stdout
    assert saved_states(last.stdout)[0]["player_supplies"]["balances"]["food"] == 1
    assert len(backups_list(backups)) == n + 1
