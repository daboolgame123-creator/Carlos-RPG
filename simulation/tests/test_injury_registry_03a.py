"""03-A registry candidates are detached and fail closed."""
import pytest

from carlos_sim.injury_registry import (
    draft_registry_insertion, validate_candidate_registry,
)
from carlos_sim.injury_transitions import draft_injury_record

ENTITIES = {"nora": {"controller": "npc"}, "basim": {"controller": "npc"}}


def rec(ident="i1", who="nora", t=10):
    return draft_injury_record(
        injury_id=ident, subject_id=who, severity=30, onset=t,
    )


def test_insert_detached_and_duplicate():
    old = {}
    candidate = draft_registry_insertion(old, ENTITIES, record=rec(), at_time=10)
    assert old == {} and candidate["i1"]["severity"] == 30
    candidate["i1"]["severity"] = 22
    assert old == {}
    with pytest.raises(ValueError, match="duplicate"):
        draft_registry_insertion({"i1": rec()}, ENTITIES, record=rec(), at_time=10)


@pytest.mark.parametrize("changes", [
    {"record": rec(who="ghost")}, {"record": rec(t=11)},
    {"record": {**rec(), "status": "recovered"}},
    {"record": {**rec(), "last_changed": 11}},
    {"at_time": True}, {"at_time": -1},
])
def test_reject_bad_proposals(changes):
    args = {"record": rec(), "at_time": 10}
    args.update(changes)
    with pytest.raises(ValueError):
        draft_registry_insertion({}, ENTITIES, **args)


@pytest.mark.parametrize("registry", [
    {"wrong-key": rec()}, {"i1": rec(who="ghost")},
    {"i1": {**rec(), "last_changed": 11}},
    {"i1": {**rec(), "severity": 0}},
])
def test_reject_invalid_registry(registry):
    with pytest.raises(ValueError):
        validate_candidate_registry(registry, ENTITIES, at_time=10)
