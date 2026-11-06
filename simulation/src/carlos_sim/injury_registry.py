"""03-A candidate injury registry validation/projection only.

No event, medical authority, persistence or SQLite mutation is granted.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .injury_transitions import validate_injury_record


def validate_candidate_registry(
    registry: Mapping[str, Any], entities: Mapping[str, Any], *, at_time: int,
) -> None:
    if not isinstance(registry, Mapping) or not isinstance(entities, Mapping):
        raise ValueError("invalid proposed registry")
    if type(at_time) is not int or not 0 <= at_time <= 2**63 - 1:
        raise ValueError("invalid proposed world time")
    for ident, row in registry.items():
        validate_injury_record(row)
        if ident != row["injury_id"]:
            raise ValueError("injury registry key mismatch")
        if row["subject_id"] not in entities:
            raise ValueError("injury references unknown subject")
        if row["last_changed"] > at_time:
            raise ValueError("future injury transition")


def draft_registry_insertion(
    registry: Mapping[str, Any], entities: Mapping[str, Any], *,
    record: Mapping[str, Any], at_time: int,
) -> dict[str, Any]:
    """Return an uncommitted detached candidate without granting source trust."""
    validate_candidate_registry(registry, entities, at_time=at_time)
    validate_injury_record(record)
    if record["subject_id"] not in entities:
        raise ValueError("unknown injured subject")
    if (record["onset"] != at_time
            or record["last_changed"] != at_time
            or record["status"] != "active"):
        raise ValueError("new injury must start active at current logical time")
    ident = record["injury_id"]
    if ident in registry:
        raise ValueError("duplicate injury ID")
    result = {key: dict(value) for key, value in registry.items()}
    result[ident] = dict(record)
    validate_candidate_registry(result, entities, at_time=at_time)
    return result
