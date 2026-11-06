"""03-A: known non-injury events never mint bodily damage."""
import pytest
from carlos_sim.domain import DomainEvent, WorldState
from carlos_sim.injury_source_gate import evaluate_injury_source


def scene():
    return WorldState(world_id="probe", time=20, entities={
        "nora": {"name": "Nora", "controller": "npc", "location_id": "square"},
    }, locations={"square": {"name": "Square"}})


@pytest.mark.parametrize("kind", [
    "PropertyTaken", "MarketTradeExecuted", "PlayerVitalChanged",
    "NPCObserved", "PlayerObserved", "PropertyClaimFiled",
    "UnknownEventType",
])
def test_observed_event_never_implicitly_creates_injury(kind):
    w = scene()
    before = w.to_dict()
    ev = DomainEvent(kind, None, "candidate", 10, {})
    result = evaluate_injury_source(w, subject_id="nora", source_event=ev)
    assert result["authority_to_record_injury"] is False
    assert result["causally_proves_injury"] is False
    assert result["source_in_persisted_ledger_verified"] is False
    assert w.to_dict() == before


@pytest.mark.parametrize("changes", [
    {"subject_id": "ghost"}, {"subject_id": True},
    {"source_event": None}, {"source_event": {}},
    {"source_event": DomainEvent("PropertyTaken", None, "future", 21, {})},
    {"source_event": DomainEvent("PropertyTaken", None, "negative", -1, {})},
    {"source_event": DomainEvent("PropertyTaken", None, "boolean", True, {})},
    {"source_event": DomainEvent("PropertyTaken", None, "", 10, {})},
    {"source_event": DomainEvent("", None, "no type", 10, {})},
    {"source_event": DomainEvent("PropertyTaken", None, "future schema", 10, {}, event_version=2)},
])
def test_invalid_source_fails_closed(changes):
    w = scene()
    original = w.to_dict()
    args = dict(subject_id="nora",
                source_event=DomainEvent("PropertyTaken", None, "past", 10, {}))
    args.update(changes)
    with pytest.raises(ValueError):
        evaluate_injury_source(w, **args)
    assert w.to_dict() == original


def test_proposal_is_detached_and_replay_independent():
    w = scene()
    e = DomainEvent("NPCObserved", None, "seen", 20, {})
    a = evaluate_injury_source(w, subject_id="nora", source_event=e)
    a["authority_to_record_injury"] = True
    b = evaluate_injury_source(w, subject_id="nora", source_event=e)
    assert b["authority_to_record_injury"] is False
