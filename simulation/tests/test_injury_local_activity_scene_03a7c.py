"""03-A7c scene-wide visible activity is a scoped projection, not diagnosis."""
from carlos_sim import DomainEvent, SQLiteEventStore, NPCService, TimeEngine
from carlos_sim.actions import NPCActionService
from carlos_sim.injury_observation import observed_local_activities
from carlos_sim.movement import NPCMovementService
from test_property_02h1 import village


def _setup(db):
    village(db)
    w = db.load("v")
    db.append(
        "v", "injured-nora", w.revision,
        [DomainEvent("InjuryRecorded", None, "trusted time-zero injury", w.time, {
            "injury_id": "nora-private", "subject_id": "nora",
            "severity": 65, "source": "trusted_test_bootstrap"})],
        bootstrap=True,
    )
    clock = TimeEngine(db)
    clock.open_session("v")
    return clock, NPCMovementService(db, clock)


def test_seven_npc_scene_scoped_to_observer_and_factual_actions(tmp_path):
    with SQLiteEventStore(tmp_path / "scene.sqlite") as db:
        clock, movement = _setup(db)
        assert observed_local_activities(db.load("v"), "basim") == ()
        NPCService(db, clock).decide(
            "v", "nora", command_id="nora-decides",
            expected_revision=db.load("v").revision,
        )
        started = NPCActionService(db, clock).start(
            "v", "nora", "nora-rest", expected_revision=db.load("v").revision,
        )
        assert observed_local_activities(started.state, "basim") == ()
        seen = movement.observe(
            "v", "basim", command_id="basim-looks",
            expected_revision=started.state.revision,
        )
        expected = ({
            "subject_id": "nora", "sign": "visible_resting",
            "site_id": "bakery", "observed_at": 0,
        },)
        assert observed_local_activities(seen, "basim") == expected
        assert observed_local_activities(seen, "salma") == ()
        assert observed_local_activities(seen, "adel") == ()
        assert observed_local_activities(seen, "omar") == ()
        assert observed_local_activities(seen, "huda") == ()
        assert observed_local_activities(seen, "nora") == ()
        assert observed_local_activities(seen, "not-real") == ()
        assert all("severity" not in repr(row) and "injury" not in repr(row)
                   for row in observed_local_activities(seen, "basim"))
        assert all(not npc["beliefs"] for npc in seen.npcs.values())
        salma_seen = movement.observe(
            "v", "salma", command_id="salma-looks",
            expected_revision=seen.revision,
        )
        assert observed_local_activities(salma_seen, "salma") == expected
        assert observed_local_activities(salma_seen, "basim") == expected
        assert db.verify("v").to_dict() == salma_seen.to_dict()


def test_historical_scene_does_not_become_current_diagnosis(tmp_path):
    path = tmp_path / "reopened-scene.sqlite"
    with SQLiteEventStore(path) as db:
        clock, movement = _setup(db)
        NPCService(db, clock).decide(
            "v", "nora", command_id="nora-decision",
            expected_revision=db.load("v").revision)
        NPCActionService(db, clock).start(
            "v", "nora", "rest-action",
            expected_revision=db.load("v").revision)
        observed = movement.observe(
            "v", "basim", command_id="observation",
            expected_revision=db.load("v").revision)
        assert len(observed_local_activities(observed, "basim")) == 1
        db.snapshot("v")
        expected = observed.to_dict()
    with SQLiteEventStore(path) as db:
        restored = db.load("v")
        assert restored.to_dict() == expected
        assert len(observed_local_activities(restored, "basim")) == 1
        assert db.verify("v").to_dict() == expected
        clock = TimeEngine(db)
        clock.open_session("v")
        advanced = clock.advance(
            "v", seconds=1, command_id="tick",
            expected_revision=restored.revision).state
        assert observed_local_activities(advanced, "basim") == ()
        assert db.verify("v").to_dict() == advanced.to_dict()


def test_untrusted_plain_mapping_rejected(tmp_path):
    from pytest import raises
    with SQLiteEventStore(tmp_path / "raw.sqlite") as db:
        _setup(db)
        with raises(ValueError):
            observed_local_activities(db.load("v").to_dict(), "basim")
