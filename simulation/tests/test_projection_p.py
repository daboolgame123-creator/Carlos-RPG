"""Phase 01-P: trusted reducer copies skip redundant serialization, not checks."""
from __future__ import annotations

from dataclasses import FrozenInstanceError
import math
from types import MappingProxyType

import pytest

from carlos_sim import DomainEvent, WorldState, apply_event, canonical_hash
import carlos_sim.domain as domain


def event(kind, data, at=0):
    return DomainEvent(kind, None, "phase 01-P consistency", at, data)


def test_internal_reducer_avoids_reencoding_whole_world(monkeypatch):
    original_copy = domain._json_copy
    captured_world_copies = []

    def inspecting_copy(value):
        if isinstance(value, dict) and "world_id" in value:
            captured_world_copies.append(value["world_id"])
        return original_copy(value)

    # The internal hot path receives a checked/replayed state, not a
    # directly constructed state that still needs strict public normalization.
    s = WorldState.from_dict(WorldState("test-world").to_dict())
    e = event("LocationCreated", {"id": "square", "name": "Square"})
    monkeypatch.setattr(domain, "_json_copy", inspecting_copy)
    projected = apply_event(s, e)
    assert projected.locations["square"]["name"] == "Square"
    assert captured_world_copies == []
    # Public incoming snapshots must still use a full JSON portability pass.
    _ = WorldState.from_dict(projected.to_dict())
    assert captured_world_copies == ["test-world"]


def test_reducer_validates_unrelated_invariants_after_local_change():
    s = WorldState("test-world")
    raw = s.to_dict()
    raw["resources"]["ghost"] = {"food": 1}
    with pytest.raises(ValueError, match="unknown resource owner"):
        WorldState.from_dict(raw)
    # The private constructor must also reject an invalid resource owner,
    # even when the reducer's event would affect a different collection.
    with pytest.raises(ValueError, match="unknown resource owner"):
        WorldState._from_internal_projection(raw)


def test_reducer_projection_is_detached_and_still_immutable():
    source = {"id": "market", "name": "Market"}
    e = event("LocationCreated", source)
    s = apply_event(WorldState("test-world"), e)
    source["name"] = "Tampered"
    assert isinstance(s.locations, MappingProxyType)
    assert s.locations["market"]["name"] == "Market"
    out = s.to_dict()
    out["locations"]["market"]["name"] = "Changed"
    assert s.locations["market"]["name"] == "Market"
    with pytest.raises(TypeError):
        s.locations["market"]["name"] = "Changed"
    assert s.to_dict() == WorldState.from_dict(s.to_dict()).to_dict()


def test_public_snapshot_rejects_nonportable_leaves_and_event_is_strict():
    bad = WorldState("test-world").to_dict()
    bad["locations"]["market"] = {"name": math.nan}
    with pytest.raises(ValueError):
        WorldState.from_dict(bad)
    bad["locations"]["market"]["name"] = object()
    with pytest.raises(ValueError):
        WorldState.from_dict(bad)
    with pytest.raises(ValueError):
        event("LocationCreated", {"id": "market", "name": math.nan})


def test_rejected_event_keeps_original_world_unchanged():
    s = apply_event(WorldState("test-world"), event(
        "LocationCreated", {"id": "market", "name": "Market"}))
    before = canonical_hash(s.to_dict())
    with pytest.raises(ValueError, match="duplicate location"):
        apply_event(s, event("LocationCreated", {"id": "market", "name": "Other"}))
    assert canonical_hash(s.to_dict()) == before


def test_projection_preserves_canonical_key_iteration_in_nested_collections():
    world = WorldState("test-world")
    world = apply_event(world, event(
        "LocationCreated", {"id": "z-place", "name": "Z Place"}))
    world = apply_event(world, event(
        "LocationCreated", {"id": "a-place", "name": "A Place"}))
    assert list(world.locations) == ["a-place", "z-place"]

    raw = world.to_dict()
    raw["locations"]["z-place"]["z_field"] = {"z": 1, "a": 2}
    expected = WorldState.from_dict(raw)
    actual = WorldState._from_internal_projection(raw)
    assert list(actual.locations) == list(expected.locations)
    assert list(actual.locations["z-place"]) == list(expected.locations["z-place"])
    assert list(actual.locations["z-place"]["z_field"]) == ["a", "z"]
    assert canonical_hash(actual.to_dict()) == canonical_hash(expected.to_dict())
