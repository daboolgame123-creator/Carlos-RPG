"""Pure 03-A injury lifecycle contract; not wired to domain events or SQLite.

This module evaluates deterministic injury-state transitions for an internal
simulator prototype. It grants no write capability and never changes HP.
"""
from __future__ import annotations
from collections.abc import Mapping
from typing import Any

SEVERITY_MAX = 100
TIME_MAX = 2**63 - 1
_FIELDS = frozenset({'injury_id', 'subject_id', 'severity', 'status', 'onset', 'last_changed'})


def _ident(value: Any) -> bool:
    return (type(value) is str and 1 <= len(value) <= 80 and value.isascii()
            and all(c.isalnum() or c in '._-' for c in value))


def _time(value: Any) -> bool:
    return type(value) is int and 0 <= value <= TIME_MAX


def validate_injury_record(record: Mapping[str, Any]) -> None:
    """Check a stand-alone proposed injury record without trusting provenance."""
    if not isinstance(record, Mapping) or set(record) != _FIELDS:
        raise ValueError('invalid injury record shape')
    if not _ident(record['injury_id']) or not _ident(record['subject_id']):
        raise ValueError('invalid injury identity')
    if type(record['severity']) is not int or not 0 <= record['severity'] <= SEVERITY_MAX:
        raise ValueError('invalid injury severity')
    if record['status'] not in ('active', 'recovered') or type(record['status']) is not str:
        raise ValueError('invalid injury status')
    if not _time(record['onset']) or not _time(record['last_changed']):
        raise ValueError('invalid injury time')
    if record['last_changed'] < record['onset']:
        raise ValueError('injury change precedes onset')
    if (record['status'] == 'active' and record['severity'] == 0) or (record['status'] == 'recovered' and record['severity'] != 0):
        raise ValueError('injury status and severity inconsistent')


def draft_injury_record(*, injury_id: str, subject_id: str, severity: int, onset: int) -> dict[str, Any]:
    """Build an untrusted proposal; a valid record is not authorization to persist."""
    row = dict(injury_id=injury_id, subject_id=subject_id, severity=severity,
               status='active', onset=onset, last_changed=onset)
    validate_injury_record(row)
    return row


def compute_recovery_transition(record: Mapping[str, Any], *,
                                started_at: int, due_at: int, at_time: int,
                                improvement: int) -> dict[str, Any]:
    """Compute a hypothetical bounded recovery, requiring a completed interval.

    The caller must separately establish trusted scheduling, character presence,
    available resources and authority. Never apply this result directly as an
    event, or treat the time arguments as proof of a scheduled event.
    """
    validate_injury_record(record)
    if record['status'] != 'active':
        raise ValueError('cannot recover already recovered injury')
    if not all(_time(x) for x in (started_at, due_at, at_time)):
        raise ValueError('invalid simulation time')
    if started_at < record['onset'] or due_at <= started_at or at_time != due_at:
        raise ValueError('recovery requires exact scheduled due time')
    if record['last_changed'] > started_at:
        raise ValueError('stale recovery interval')
    if type(improvement) is not int or not 1 <= improvement <= SEVERITY_MAX:
        raise ValueError('invalid recovery improvement')
    severity = max(0, record['severity'] - improvement)
    return {**record, 'severity': severity,
            'status': 'recovered' if severity == 0 else 'active',
            'last_changed': at_time}
