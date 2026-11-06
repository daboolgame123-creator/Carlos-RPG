"""Standalone 03-A deterministic injury-state contract tests."""
import pytest
from carlos_sim.injury_transitions import (draft_injury_record, validate_injury_record,
                                           compute_recovery_transition)


def injury():
    return draft_injury_record(injury_id='i-1', subject_id='nora', severity=35, onset=10)


def test_injury_creation_and_read_only_recovery():
    original = injury()
    result = compute_recovery_transition(original, started_at=10, due_at=70,
                                         at_time=70, improvement=10)
    assert result['severity'] == 25
    assert result['status'] == 'active'
    assert original['severity'] == 35
    assert original['last_changed'] == 10


def test_full_recovery_has_zero_severity_and_no_repeat():
    record = injury()
    finished = compute_recovery_transition(record, started_at=10, due_at=70,
                                           at_time=70, improvement=70)
    assert finished['severity'] == 0 and finished['status'] == 'recovered'
    with pytest.raises(ValueError):
        compute_recovery_transition(finished, started_at=70, due_at=130,
                                    at_time=130, improvement=1)


@pytest.mark.parametrize('change', [
    {'injury_id': ''}, {'subject_id': 'bad id'}, {'severity': True},
    {'severity': -1}, {'severity': 101}, {'status': 'recovered'},
    {'status': 'judged'}, {'onset': -1}, {'last_changed': 9},
])
def test_invalid_injury_records_fail_closed(change):
    record = injury()
    record.update(change)
    with pytest.raises(ValueError):
        validate_injury_record(record)


@pytest.mark.parametrize('change', [
    {'started_at': 9}, {'due_at': 10}, {'at_time': 69}, {'at_time': 71},
    {'improvement': 0}, {'improvement': True}, {'improvement': 101},
    {'started_at': True}, {'due_at': 2**63},
])
def test_invalid_recovery_attempts_fail_closed(change):
    row = injury()
    original = row.copy()
    kwargs = dict(started_at=10, due_at=70, at_time=70, improvement=10)
    kwargs.update(change)
    with pytest.raises(ValueError):
        compute_recovery_transition(row, **kwargs)
    assert row == original


def test_recovery_stale_interval_rejected():
    updated = compute_recovery_transition(injury(), started_at=10, due_at=70,
                                          at_time=70, improvement=10)
    with pytest.raises(ValueError, match='stale'):
        compute_recovery_transition(updated, started_at=50, due_at=100,
                                    at_time=100, improvement=10)


def test_repeated_same_inputs_are_deterministic():
    assert (compute_recovery_transition(injury(), started_at=10, due_at=70,
                                        at_time=70, improvement=10)
            == compute_recovery_transition(injury(), started_at=10, due_at=70,
                                           at_time=70, improvement=10))
