"""Phase 01-N: faster data conversion must preserve isolation and replay contracts."""
from types import MappingProxyType
import math

import pytest

from carlos_sim import DomainEvent, SQLiteEventStore, TimeEngine, WorldState
from carlos_sim.domain import canonical, canonical_hash
from carlos_sim.store import InvalidEvent
from test_survival import make, tick


def test_world_to_dict_is_deep_detached_copy():
    source = {"nora": {"name": "Nora", "controller": "npc", "location_id": "square"}}
    world = WorldState("village", entities=source, locations={"square": {"name": "Square"}})
    source["nora"]["name"] = "TAMPERED"
    out = world.to_dict()
    out["entities"]["nora"]["name"] = "CHANGED"
    out["locations"]["square"]["name"] = "Changed"
    assert world.entities["nora"]["name"] == "Nora"
    assert world.locations["square"]["name"] == "Square"
    assert world.to_dict()["entities"]["nora"]["name"] == "Nora"


def test_event_to_dict_is_deep_detached_copy():
    payload = {"nested": [1, {"flag": True}], "words": ["hi"]}
    event = DomainEvent("FutureEvent", None, "test", 0, payload)
    payload["nested"][1]["flag"] = False
    out = event.to_dict()
    out["data"]["nested"][1]["flag"] = False
    out["data"]["words"].append("injected")
    assert event.data["nested"][1]["flag"] is True
    assert event.to_dict()["data"]["words"] == ["hi"]
    assert event.to_dict() == DomainEvent.from_dict(event.to_dict()).to_dict()


def test_freezing_rejects_nonportable_float_and_objects():
    with pytest.raises(ValueError):
        DomainEvent("Any", None, "nan", 0, {"x": math.nan})
    with pytest.raises(ValueError):
        WorldState("world", resources={"x": {"weird": float("inf")}})
    with pytest.raises(ValueError):
        DomainEvent("Any", None, "object", 0, {"x": object()})


def test_canonical_mapping_fallback_and_frozen_types():
    nested = MappingProxyType({"one": [2, MappingProxyType({"three": 4})]})
    assert canonical(nested) == '{"one":[2,{"three":4}]}'
    assert canonical_hash(nested) == canonical_hash({"one": [2, {"three": 4}]})


def test_from_dict_freezes_original_mutable_input():
    state = WorldState("test", locations={"square": {"name": "Square"}})
    raw = state.to_dict()
    rehydrated = WorldState.from_dict(raw)
    raw["locations"]["square"]["name"] = "Hacked"
    assert rehydrated.locations["square"]["name"] == "Square"
    assert rehydrated.to_dict() == state.to_dict()


def test_valid_replay_and_snapshot_hashes_are_preserved(tmp_path):
    with SQLiteEventStore(tmp_path / 'audit.sqlite') as store:
        clock = make(store, names=("nora", "basim"))
        start = store.load("test")
        after = tick(store, 301, "time-1")
        snap = store.snapshot("test")
        assert after.to_dict() == snap.to_dict()
        assert store.verify("test").to_dict() == after.to_dict()
        later = tick(store, 299, "time-2")
        assert store.verify("test").to_dict() == later.to_dict()
        assert later.revision == start.revision + 2


def test_invalid_events_still_fail_atomically(tmp_path):
    with SQLiteEventStore(tmp_path / 'rejection.sqlite') as store:
        clock = make(store)
        before = store.load('test')
        with pytest.raises(InvalidEvent):
            store.append('test', 'bad', before.revision, [
                DomainEvent('ResourceChanged', 'nora', 'attempt to forge food', 0,
                    {'owner_id': 'nora', 'resource': 'food', 'previous': 0,
                     'current': 100, 'source': 'consumption'})])
        assert store.load('test').to_dict() == before.to_dict()
        assert store.db.execute("SELECT COUNT(*) FROM commands WHERE command_id='bad'").fetchone()[0] == 0
