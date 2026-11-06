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


def test_earlier_look_cannot_be_reused_to_forge_same_tick_care_delivery(tmp_path):
    from carlos_sim import DomainEvent
    from carlos_sim.store import InvalidEvent
    import pytest
    db, clock, service = scene(tmp_path)
    try:
        movement = NPCMovementService(db, clock)
        seen = movement.observe("v", "basim", command_id="look-first",
                                expected_revision=db.load("v").revision)
        begun = begin(db, service)
        assert begun.time == seen.time == 0
        claim = DomainEvent(
            "NPCInformationDelivered", "basim", "forged late interpretation", 0, {
                "npc_id": "basim", "delivery_id": "false-earlier-care",
                "key": "visible-care:nora:adel:0",
                "claim": {
                    "text": "visible-supportive-care; caregiver=adel; observed_at=0",
                    "source": "observation:bakery",
                    "received_at": 0, "confidence": 90,
                },
                "sender_id": "basim", "location_id": "bakery",
                "method": "observation",
            })
        # Trust flags alone cannot make a past look witness a later action.
        for flags in ({"npc_authorized": True},
                      {"npc_authorized": True, "movement_authorized": True}):
            with pytest.raises(InvalidEvent):
                db.append("v", "forged-care" + str(len(flags)), begun.revision,
                          [claim], **flags)
        assert observed_supportive_care(db.load("v"), "basim", "nora") is None
        assert db.verify("v").to_dict() == begun.to_dict()
        observed = movement.observe("v", "basim", command_id="real-care-look",
                                    expected_revision=begun.revision,
                                    care_enabled=True)
        assert observed_supportive_care(observed, "basim", "nora") is not None
        assert db.verify("v").to_dict() == observed.to_dict()
    finally:
        db.close()


def test_same_batch_care_created_after_look_cannot_be_witnessed(tmp_path):
    from carlos_sim import DomainEvent
    from carlos_sim.store import InvalidEvent
    import pytest
    db, clock, _service = scene(tmp_path)
    try:
        initial = db.load("v")
        sight = DomainEvent("NPCObserved", "basim", "looks before treatment", 0,
                            {"npc_id": "basim"})
        care = DomainEvent("RecoveryStarted", "adel", "later same-tick care", 0, {
            "id": "later-care", "injury_id": "nora-fatigue",
            "subject_id": "nora", "caregiver_id": "adel", "site_id": "bakery",
            "schedule_id": "heal.later-care", "started_at": 0,
            "due_at": 600, "resource": "food", "quantity": 1,
            "improvement": 10,
        })
        forged = DomainEvent("NPCInformationDelivered", "basim",
                             "claimed to see care before it started", 0, {
            "npc_id": "basim", "delivery_id": "impossible-care",
            "key": "visible-care:nora:adel:0",
            "claim": {"text": "visible-supportive-care; caregiver=adel; observed_at=0",
                      "source": "observation:bakery",
                      "received_at": 0, "confidence": 90},
            "sender_id": "basim", "location_id": "bakery",
            "method": "observation",
        })
        with pytest.raises(InvalidEvent, match="care must start before"):
            db.append("v", "wrong-order", initial.revision,
                      [sight, care, forged],
                      movement_authorized=True, npc_authorized=True,
                      recovery_authorized=True)
        assert db.load("v").to_dict() == initial.to_dict()
        assert db.verify("v").to_dict() == initial.to_dict()
    finally:
        db.close()


def test_basim_remembers_real_care_after_completion_but_others_do_not(tmp_path):
    from carlos_sim.injury_observation import recall_supportive_care
    from carlos_sim.store import DuplicateCommand
    import pytest
    path = tmp_path / "care.sqlite"
    db, clock, service = scene(tmp_path)
    try:
        begun = begin(db, service)
        movement = NPCMovementService(db, clock)
        witnessed = movement.observe(
            "v", "basim", command_id="remember-care",
            expected_revision=begun.revision, care_enabled=True)
        expected = ({
            "subject_id": "nora", "caregiver_id": "adel",
            "sign": "visible_supportive_care", "site_id": "bakery",
            "observed_at": 0, "interpretation": "cause_unknown",
            "medical_conclusion": None,
        },)
        assert recall_supportive_care(witnessed, "basim") == expected
        for who in ("salma", "huda", "omar", "adel", "nora"):
            assert recall_supportive_care(witnessed, who) == ()
        again = movement.observe(
            "v", "basim", command_id="look-again",
            expected_revision=witnessed.revision, care_enabled=True)
        assert recall_supportive_care(again, "basim") == expected
        done = clock.advance(
            "v", seconds=600, command_id="finish-care",
            expected_revision=again.revision).state
        assert done.treatments["care-one"]["status"] == "completed"
        assert observed_supportive_care(done, "basim", "nora") is None
        assert recall_supportive_care(done, "basim") == expected
        assert "nora-fatigue" not in repr(expected)
        db.snapshot("v")
        original = done.to_dict()
        assert db.verify("v").to_dict() == original
    finally:
        db.close()
    with SQLiteEventStore(path) as reopened:
        restored = reopened.load("v")
        assert restored.to_dict() == original
        assert reopened.verify("v").to_dict() == original
        assert recall_supportive_care(restored, "basim") == expected
        assert recall_supportive_care(restored, "salma") == ()


def test_look_before_care_creates_no_historical_memory(tmp_path):
    from carlos_sim.injury_observation import recall_supportive_care
    db, clock, service = scene(tmp_path)
    try:
        movement = NPCMovementService(db, clock)
        earlier = movement.observe(
            "v", "basim", command_id="look-before-care",
            expected_revision=db.load("v").revision,
            care_enabled=True)
        begun = begin(db, service)
        assert earlier.time == begun.time
        assert recall_supportive_care(begun, "basim") == ()
        later = movement.observe(
            "v", "basim", command_id="look-during-care",
            expected_revision=begun.revision, care_enabled=True)
        assert len(recall_supportive_care(later, "basim")) == 1
        assert db.verify("v").to_dict() == later.to_dict()
    finally:
        db.close()


def test_unvalidated_snapshot_and_unknown_observers_cannot_recall_care(tmp_path):
    from carlos_sim.injury_observation import recall_supportive_care
    import pytest
    db, clock, service = scene(tmp_path)
    try:
        initial = begin(db, service)
        with pytest.raises(ValueError):
            recall_supportive_care(initial.to_dict(), "basim")
        assert recall_supportive_care(initial, "unknown") == ()
        assert recall_supportive_care(initial, "basim") == ()
    finally:
        db.close()


def test_salma_independently_witnesses_care_while_huda_stays_uninformed(tmp_path):
    from carlos_sim.injury_observation import recall_supportive_care
    db, clock, service = scene(tmp_path)
    try:
        began = begin(db, service)
        movement = NPCMovementService(db, clock)
        basim = movement.observe(
            "v", "basim", command_id="basim-care",
            expected_revision=began.revision, care_enabled=True)
        assert len(recall_supportive_care(basim, "basim")) == 1
        assert recall_supportive_care(basim, "salma") == ()
        salma = movement.observe(
            "v", "salma", command_id="salma-care",
            expected_revision=basim.revision, care_enabled=True)
        assert recall_supportive_care(salma, "salma") == recall_supportive_care(salma, "basim")
        for who in ("huda", "omar", "nora", "adel"):
            assert recall_supportive_care(salma, who) == ()
        assert db.verify("v").to_dict() == salma.to_dict()
    finally:
        db.close()


def test_care_memory_full_does_not_prevent_basim_observing(tmp_path):
    """Long-running funded care can be seen after bounded memory fills."""
    from carlos_sim.injury_observation import recall_supportive_care, MAX_CARE_MEMORIES
    db, clock, service = scene(tmp_path)
    try:
        begin(db, service)
        movement = NPCMovementService(db, clock)
        for tick in range(MAX_CARE_MEMORIES + 1):
            viewed = movement.observe(
                "v", "basim", command_id=f"care-look-{tick}",
                expected_revision=db.load("v").revision, care_enabled=True)
            assert len(recall_supportive_care(viewed, "basim")) == min(
                tick + 1, MAX_CARE_MEMORIES)
            if tick < MAX_CARE_MEMORIES:
                clock.advance("v", seconds=1, command_id=f"care-tick-{tick}",
                              expected_revision=viewed.revision)
        assert len(recall_supportive_care(db.load("v"), "basim")) == MAX_CARE_MEMORIES
        assert db.verify("v").to_dict() == db.load("v").to_dict()
    finally:
        db.close()


def test_care_evidence_refuses_relabelled_subject_and_forged_diagnosis(tmp_path):
    """Care evidence does not grant an arbitrary medical diagnosis."""
    from carlos_sim import DomainEvent
    from carlos_sim.store import InvalidEvent
    import pytest
    db, clock, service = scene(tmp_path)
    try:
        start = begin(db, service)
        valid = NPCMovementService(db, clock).observe(
            "v", "basim", command_id="genuine-look",
            expected_revision=start.revision, care_enabled=True)
        before = valid.to_dict()
        for idx, (key, text) in enumerate((
            ("visible-care:huda:adel:0",
             "visible-supportive-care; caregiver=adel; observed_at=0"),
            ("visible-care:nora:adel:0",
             "diagnosed-severe-injury; observed_at=0"),
            ("visible-care:nora:basim:0",
             "visible-supportive-care; caregiver=basim; observed_at=0"),
        )):
            forged = DomainEvent("NPCInformationDelivered", "basim",
                                  "forged care inference", valid.time, {
                "npc_id": "basim", "delivery_id": f"forged-care-{idx}",
                "key": key,
                "claim": {"text": text, "source": "observation:bakery",
                          "received_at": valid.time, "confidence": 90},
                "sender_id": "basim", "location_id": "bakery",
                "method": "observation",
            })
            # Not even a trusted NPC capability can invent an extra first-hand
            # sighting, reinterpret care as disease, or change its participants.
            with pytest.raises(InvalidEvent):
                db.append("v", f"reject-false-care-{idx}", valid.revision,
                          [forged], npc_authorized=True, movement_authorized=True)
            assert db.load("v").to_dict() == before
        assert db.verify("v").to_dict() == before
    finally:
        db.close()
