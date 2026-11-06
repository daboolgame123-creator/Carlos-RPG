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
                                expected_revision=begun.revision)
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
        assert all(not npc["beliefs"] for npc in seen.npcs.values())
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
            expected_revision=begun.revision)
        assert observed_supportive_care(observed, "basim", "nora") is not None
        db.snapshot("v")
        assert db.verify("v").to_dict() == observed.to_dict()
        later = clock.advance(
            "v", seconds=1, command_id="tick",
            expected_revision=observed.revision).state
        assert observed_supportive_care(later, "basim", "nora") is None
        assert later.npcs["basim"]["beliefs"] == {}
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
            expected_revision=finished.revision)
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
