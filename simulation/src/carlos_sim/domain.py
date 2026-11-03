"""Immutable state projection from strict, versioned domain events.

No game story or Carlos character state is imported by this module.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping
from hashlib import sha256
import json

SCHEMA_VERSION = 2
RULES_VERSION = 3


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {k: _thaw(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_thaw(v) for v in value]
    return value


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({k: _freeze(v) for k, v in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(v) for v in value)
    return value


def canonical(data: Any) -> str:
    return json.dumps(_thaw(data), sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def canonical_hash(data: Any) -> str:
    return sha256(canonical(data).encode("utf-8")).hexdigest()


def _json_copy(value: Any) -> Any:
    """Enforce portable JSON values and sever caller-owned mutable references."""
    try:
        return json.loads(canonical(value))
    except (TypeError, ValueError) as exc:
        raise ValueError("payload must contain only finite JSON data") from exc


@dataclass(frozen=True)
class WorldState:
    world_id: str
    time: int = 0
    revision: int = 0
    schema_version: int = SCHEMA_VERSION
    rules_version: int = RULES_VERSION
    entities: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    locations: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    resources: Mapping[str, Mapping[str, int | None]] = field(default_factory=dict)
    scheduled: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    next_schedule_order: int = 1

    def __post_init__(self) -> None:
        object.__setattr__(self, "entities", _freeze(_json_copy(self.entities)))
        object.__setattr__(self, "locations", _freeze(_json_copy(self.locations)))
        object.__setattr__(self, "resources", _freeze(_json_copy(self.resources)))
        object.__setattr__(self, "scheduled", _freeze(_json_copy(self.scheduled)))

    def to_dict(self) -> dict[str, Any]:
        return _json_copy({"world_id": self.world_id, "time": self.time, "revision": self.revision,
                           "schema_version": self.schema_version, "rules_version": self.rules_version,
                           "entities": self.entities, "locations": self.locations, "resources": self.resources,
                           "scheduled": self.scheduled, "next_schedule_order": self.next_schedule_order})

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> WorldState:
        if not isinstance(d, dict) or set(d) != {"world_id", "time", "revision", "schema_version", "rules_version", "entities", "locations", "resources", "scheduled", "next_schedule_order"}:
            raise ValueError("invalid world snapshot")
        if d["schema_version"] != SCHEMA_VERSION or d["rules_version"] != RULES_VERSION:
            raise ValueError("unsupported world version")
        if not isinstance(d["world_id"], str) or not d["world_id"] or any(type(d[k]) is not int or d[k] < 0 for k in ("time", "revision")):
            raise ValueError("invalid world identity/time/revision")
        if type(d["next_schedule_order"]) is not int or d["next_schedule_order"] < 1:
            raise ValueError("invalid schedule order")
        if any(not isinstance(d[k], dict) for k in ("entities", "locations", "resources", "scheduled")):
            raise ValueError("invalid state collections")
        for owner, balances in d["resources"].items():
            if owner not in d["entities"] and owner not in d["locations"]:
                raise ValueError("unknown resource owner")
            if not isinstance(balances, dict):
                raise ValueError("invalid resource group")
            for amount in balances.values():
                if amount is not None and (type(amount) is not int or amount < 0):
                    raise ValueError("invalid resource amount")
        orders = set()
        for ident, item in d["scheduled"].items():
            if not isinstance(ident, str) or not ident or not isinstance(item, dict) or set(item) != {"due", "order", "kind", "payload", "interrupt"}:
                raise ValueError("invalid scheduled item")
            if type(item["due"]) is not int or item["due"] < d["time"] or type(item["order"]) is not int or not 0 < item["order"] < d["next_schedule_order"]:
                raise ValueError("invalid scheduled timing")
            if item["order"] in orders:
                raise ValueError("duplicate schedule order")
            orders.add(item["order"])
            if item["kind"] != "signal" or type(item["interrupt"]) is not bool or not isinstance(item["payload"], dict):
                raise ValueError("invalid scheduled action")
        return cls(**_json_copy(d))


@dataclass(frozen=True)
class DomainEvent:
    event_type: str
    actor_id: str | None
    cause: str
    time: int
    data: Mapping[str, Any]
    event_version: int = 1

    def __post_init__(self) -> None:
        object.__setattr__(self, "data", _freeze(_json_copy(self.data)))

    def to_dict(self) -> dict[str, Any]:
        return _json_copy({"event_type": self.event_type, "actor_id": self.actor_id,
                           "cause": self.cause, "time": self.time, "data": self.data,
                           "event_version": self.event_version})

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> DomainEvent:
        if not isinstance(value, dict) or set(value) != {"event_type", "actor_id", "cause", "time", "data", "event_version"}:
            raise ValueError("malformed event")
        if value["event_version"] != 1 or not isinstance(value["event_type"], str) or not isinstance(value["cause"], str) or not value["cause"]:
            raise ValueError("unsupported/malformed event")
        if value["actor_id"] is not None and (not isinstance(value["actor_id"], str) or not value["actor_id"]):
            raise ValueError("invalid actor")
        if type(value["time"]) is not int or value["time"] < 0 or not isinstance(value["data"], dict):
            raise ValueError("invalid event time or data")
        return cls(**_json_copy(value))


def apply_event(state: WorldState, event: DomainEvent, *, bootstrap: bool = False) -> WorldState:
    """Pure projection. Any rejected event leaves the original state unmodified."""
    data = event.to_dict()
    e = DomainEvent.from_dict(data)
    d = state.to_dict()
    if e.event_type in ("TimeAdvanced", "ScheduledEventFired"):
        # Both operations are system-driven; an NPC cannot impersonate the clock.
        if e.actor_id is not None:
            raise ValueError("system clock event must not impersonate an actor")
        if e.event_type == "ScheduledEventFired" and e.time != state.time:
            raise ValueError("scheduled firing cannot alter logical time")
    elif e.time != state.time:
        raise ValueError("ordinary event cannot advance or rewind simulation time")
    if e.actor_id is not None and e.actor_id not in state.entities:
        raise ValueError("event actor does not exist")
    p = e.data
    kind = e.event_type
    if kind == "LocationCreated":
        if set(p) != {"id", "name"} or not all(isinstance(p[k], str) and p[k] for k in p):
            raise ValueError("invalid location")
        if p["id"] in d["locations"] or p["id"] in d["entities"]:
            raise ValueError("duplicate location")
        d["locations"][p["id"]] = {"name": p["name"]}
    elif kind == "EntityCreated":
        if set(p) != {"id", "name", "location_id", "controller"} or not all(isinstance(p[k], str) and p[k] for k in p):
            raise ValueError("invalid entity")
        if p["controller"] not in ("player", "npc") or p["location_id"] not in d["locations"]:
            raise ValueError("invalid controller or entity location")
        if p["id"] in d["entities"] or p["id"] in d["locations"]:
            raise ValueError("duplicate entity")
        d["entities"][p["id"]] = {k: p[k] for k in ("name", "location_id", "controller")}
    elif kind == "ResourceChanged":
        if set(p) != {"owner_id", "resource", "previous", "current", "source"}:
            raise ValueError("invalid resource change fields")
        owner, resource = p["owner_id"], p["resource"]
        if not isinstance(owner, str) or not isinstance(resource, str) or not resource or owner not in d["entities"] and owner not in d["locations"]:
            raise ValueError("invalid resource owner")
        balances = d["resources"].setdefault(owner, {})
        previous = balances.get(resource)  # Missing means unknown, never zero.
        if p["previous"] != previous or type(p["previous"]) is bool:
            raise ValueError("resource previous-value mismatch")
        current = p["current"]
        if current is not None and (type(current) is not int or current < 0):
            raise ValueError("invalid resource amount")
        if current == previous and type(current) is type(previous):
            raise ValueError("resource did not change")
        source = p["source"]
        if source == "initialization":
            if not bootstrap or state.time != 0 or previous is not None or current is None or e.actor_id is not None:
                raise ValueError("resource initialization requires authorized bootstrap at time zero")
        elif source == "consumption":
            if bootstrap or owner != e.actor_id or owner not in state.entities:
                raise ValueError("resource consumption requires the owning actor")
            if type(previous) is not int or type(current) is not int or current >= previous:
                raise ValueError("consumption must decrease a known balance")
        else:
            raise ValueError("unsupported resource source; transfers/production not yet implemented")
        balances[resource] = current
    elif kind == "ScheduledEventCreated":
        if set(p) != {"id", "due", "order", "kind", "payload", "interrupt"}:
            raise ValueError("invalid schedule fields")
        if not isinstance(p["id"], str) or not p["id"] or p["id"] in d["scheduled"]:
            raise ValueError("duplicate or invalid schedule ID")
        if type(p["due"]) is not int or p["due"] <= state.time or type(p["order"]) is not int or p["order"] != state.next_schedule_order:
            raise ValueError("invalid due time or schedule order")
        if p["kind"] != "signal" or not isinstance(p["payload"], Mapping) or type(p["interrupt"]) is not bool:
            raise ValueError("unsupported scheduled action")
        d["scheduled"][p["id"]] = {k: _thaw(p[k]) for k in ("due", "order", "kind", "payload", "interrupt")}
        d["next_schedule_order"] += 1
    elif kind == "ScheduledEventCancelled":
        if set(p) != {"id"} or not isinstance(p["id"], str) or p["id"] not in d["scheduled"]:
            raise ValueError("cannot cancel missing schedule")
        del d["scheduled"][p["id"]]
    elif kind == "ScheduledEventFired":
        if set(p) != {"id"} or not isinstance(p["id"], str) or p["id"] not in d["scheduled"]:
            raise ValueError("cannot fire missing schedule")
        scheduled = d["scheduled"][p["id"]]
        if scheduled["due"] != state.time:
            raise ValueError("scheduled event cannot fire before or after due time")
        earliest = min(d["scheduled"].items(), key=lambda x: (x[1]["due"], x[1]["order"], x[0]))[0]
        if earliest != p["id"]:
            raise ValueError("scheduled event fired out of order")
        del d["scheduled"][p["id"]]
    elif kind == "TimeAdvanced":
        if set(p) != {"from", "to"} or type(p["from"]) is not int or type(p["to"]) is not int:
            raise ValueError("invalid time advance")
        if p["from"] != state.time or p["to"] <= state.time or p["to"] != e.time:
            raise ValueError("invalid time transition")
        if d["scheduled"] and min(x["due"] for x in d["scheduled"].values()) < p["to"]:
            raise ValueError("time advancement would skip due scheduled event")
    else:
        raise ValueError(f"unknown event type: {kind}")
    d["revision"] += 1
    d["time"] = e.time
    return WorldState.from_dict(d)
