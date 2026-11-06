"""03-A7c: visible funded supportive care is local, not an injury diagnosis."""
from carlos_sim import SQLiteEventStore, TimeEngine
from carlos_sim.injury_observation import observed_supportive_care
from carlos_sim.movement import NPCMovementService
from test_funded_recovery_03a import scene, begin


def test_adel_caring_for_nora_visible_only_to_real_witness(tmp_path):
    db, clock, service = scene(tmp_path)
    try:
        begun = begin(db, service)
        assert observed_supportive_care(begun, "basim", "nora") is None
        movement = NPCMovementService(db, clock)
        seen = movement.observe("v", "basim", command_id="watch-care",
                                expected_revision=begun.revision, care_enabled=True)
        expected = {
            "subject_id": "nora", "caregiver_id": "adel",
            "sign": "visible_supportive_care", "site_id": "bakery",
            "observed_at": 0, "medical_conclusion": None,
        }
        assert observed_supportive_care(seen, "basim", "nora") == expected
        for observer in ("salma", "huda", "omar", "nora", "adel"):
            assert observed_supportive_care(seen, observer, "nora") is None
        assert "nora-fatigue" not in repr(expected)
        assert "severity" not in repr(expected)
        assert seen.npcs["salma"]["beliefs"] == {}
        assert seen.npcs["nora"]["beliefs"] == {}
        assert all("nora-fatigue" not in repr(v) for v in seen.npcs["basim"]["beliefs"].values())
        assert db.verify("v").to_dict() == seen.to_dict()
    finally:
        db.close()


def test_care_sighting_expires_without_retroactive_medical_knowledge(tmp_path):
    db, clock, svc = scene(tmp_path)
    try:
        begun = begin(db, svc)
        movement = NPCMovementService(db, clock)
        observed = movement.observe(
            "v", "basim", command_id="care",
            expected_revision=begun.revision, care_enabled=True)
        assert observed_supportive_care(observed, "basim", "nora") is not None
        db.snapshot("v")
        assert db.verify("v").to_dict() == observed.to_dict()
        later = clock.advance(
            "v", seconds=1, command_id="tick",
            expected_revision=observed.revision).state
        assert observed_supportive_care(later, "basim", "nora") is None
        assert len([k for k in later.npcs["basim"]["beliefs"] if k.startswith("visible-care:")]) == 1
        assert db.verify("v").to_dict() == later.to_dict()
    finally:
        db.close()


def test_care_after_its_completion_is_not_visible_as_active(tmp_path):
    db, clock, svc = scene(tmp_path)
    try:
        begun = begin(db, svc)
        finished = clock.advance(
            "v", seconds=600, command_id="care-completes",
            expected_revision=begun.revision).state
        assert finished.treatments["care-one"]["status"] == "completed"
        observed = NPCMovementService(db, clock).observe(
            "v", "basim", command_id="late-look",
            expected_revision=finished.revision, care_enabled=True)
        assert observed_supportive_care(observed, "basim", "nora") is None
        assert db.verify("v").to_dict() == observed.to_dict()
    finally:
        db.close()


def test_forged_world_cannot_be_used_as_care_sighting(tmp_path):
    import pytest
    db, clock, svc = scene(tmp_path)
    try:
        begun = begin(db, svc)
        with pytest.raises(ValueError):
            observed_supportive_care(begun.to_dict(), "basim", "nora")
    finally:
        db.close()


def test_caregiver_departs_so_supportive_care_is_not_visible(tmp_path):
    """A still-pending appointment alone cannot put Adel at the bakery."""
    from carlos_sim import DomainEvent
    db, clock, service = scene(tmp_path)
    try:
        before = db.load("v")
        db.append("v", "route-for-caregiver", before.revision, [
            DomainEvent("RouteCreated", None, "physical bakery to square road",
                        before.time, {"id": "care-route", "a": "bakery",
                                      "b": "square", "seconds": 50})
        ], bootstrap=True)
        started = begin(db, service)
        movement = NPCMovementService(db, clock)
        departing = movement.start(
            "v", "adel", "care-route", "caregiver-departs",
            expected_revision=started.revision)
        sight = movement.observe(
            "v", "basim", command_id="watch-departed",
            expected_revision=departing.state.revision, care_enabled=True)
        assert sight.treatments["care-one"]["status"] == "pending"
        assert observed_supportive_care(sight, "basim", "nora") is None
        assert sight.injuries["nora-fatigue"]["severity"] == 25
        assert db.verify("v").to_dict() == sight.to_dict()
    finally:
        db.close()


def test_care_is_visible_only_to_present_witness_after_snapshot_reopen(tmp_path):
    path = tmp_path / "care.sqlite"
    db, clock, service = scene(tmp_path)
    try:
        started = begin(db, service)
        movement = NPCMovementService(db, clock)
        observed = movement.observe(
            "v", "basim", command_id="seen-before-close",
            expected_revision=started.revision, care_enabled=True)
        evidence = observed_supportive_care(observed, "basim", "nora")
        assert evidence is not None
        assert observed_supportive_care(observed, "salma", "nora") is None
        db.snapshot("v")
        original = observed.to_dict()
    finally:
        db.close()
    with SQLiteEventStore(path) as reopened:
        loaded = reopened.load("v")
        assert loaded.to_dict() == original
        assert reopened.verify("v").to_dict() == original
        assert observed_supportive_care(loaded, "basim", "nora") == evidence
        clock = TimeEngine(reopened)
        clock.open_session("v")
        later = clock.advance(
            "v", seconds=1, command_id="tick-after-restart",
            expected_revision=loaded.revision).state
        assert observed_supportive_care(later, "basim", "nora") is None
        assert reopened.verify("v").to_dict() == later.to_dict()


def test_look_before_care_same_tick_never_predicts_future_care(tmp_path):
    db, clock, service = scene(tmp_path)
    try:
        movement = NPCMovementService(db, clock)
        looked = movement.observe("v", "basim", command_id="look-before-care",
                                  expected_revision=db.load("v").revision,
                                  care_enabled=True)
        assert observed_supportive_care(looked, "basim", "nora") is None
        started = begin(db, service)
        assert started.time == looked.time == 0
        # Even with matching time and occupants, the earlier look has no
        # ordered claim about an action that had not started.
        assert observed_supportive_care(started, "basim", "nora") is None
        now_seen = movement.observe("v", "basim", command_id="look-after-care",
                                    expected_revision=started.revision,
                                    care_enabled=True)
        assert observed_supportive_care(now_seen, "basim", "nora") is not None
        assert db.verify("v").to_dict() == now_seen.to_dict()
    finally:
        db.close()
