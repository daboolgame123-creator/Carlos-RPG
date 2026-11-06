"""03-A pre-integration contract: malformed and aliased injury data fail closed.

Tests pure standalone logic only; not evidence of persisted injury treatment.
"""
import pytest
from carlos_sim.injury_intake import assess_injury_intake
from carlos_sim.injury_transitions import (
    draft_injury_record, validate_injury_record, compute_recovery_transition,
)
from carlos_sim.domain import WorldState


def world():
    return WorldState(
        world_id="injury-contract", time=10,
        locations={"square": {"name": "Square"}},
        entities={"nora": {
            "name": "Nora", "controller": "npc", "location_id": "square",
        }},
    )


def test_injury_intake_does_not_authorize_unverified_source():
    w = world()
    old = w.to_dict()
    result = assess_injury_intake(
        w, subject_id="nora", injury_id="inj-1", severity=40,
        source_kind="trusted_test_scenario",
        source_reference="claimed-event-1", onset_time=10,
    )
    assert result["source_provenance_verified"] is False
    assert result["commit_authorized"] is False
    assert result["injury_recorded"] is False
    assert w.to_dict() == old


def test_transition_inputs_remain_detached_after_mutating_result():
    record = draft_injury_record(
        injury_id="inj-1", subject_id="nora", severity=40, onset=10,
    )
    before = dict(record)
    result = compute_recovery_transition(
        record, started_at=10, due_at=20, at_time=20, improvement=15,
    )
    result["injury_id"] = "forged-id"
    result["severity"] = 0
    assert record == before
    assert compute_recovery_transition(
        record, started_at=10, due_at=20, at_time=20, improvement=15,
    )["severity"] == 25


@pytest.mark.parametrize("mutation", [
    {"status": "recovered", "severity": 1},
    {"status": "active", "severity": 0},
    {"injury_id": "bad id"},
    {"subject_id": True},
    {"last_changed": True},
    {"last_changed": 9},
    {"severity": 101},
    {"extra_field": "forged"},
])
def test_forged_record_rejected_before_transition(mutation):
    record = draft_injury_record(
        injury_id="inj-1", subject_id="nora", severity=40, onset=10,
    )
    record.update(mutation)
    with pytest.raises(ValueError):
        validate_injury_record(record)
    with pytest.raises(ValueError):
        compute_recovery_transition(
            record, started_at=10, due_at=20, at_time=20, improvement=1,
        )
