"""Immutable state projection from strict, versioned domain events.

No game story or Carlos character state is imported by this module.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any
from collections.abc import Mapping
from hashlib import sha256
import json

SCHEMA_VERSION = 13
RULES_VERSION = 19


def _thaw(value: Any) -> Any:
    # Most nodes in a world state are JSON scalars. Avoid an expensive
    # Mapping ABC check for every such leaf while retaining Mapping support.
    typ = type(value)
    if typ in (str, int, float, bool) or value is None:
        return value
    if typ is dict or typ is MappingProxyType:
        return {k: _thaw(v) for k, v in value.items()}
    if typ is tuple or typ is list:
        return [_thaw(v) for v in value]
    # Support arbitrary Mapping implementations in public-facing inputs.
    if isinstance(value, Mapping):
        return {k: _thaw(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_thaw(v) for v in value]
    return value


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        # Match the deterministic key order produced by the previous
        # json.dumps(sort_keys=True) + json.loads snapshot normalization,
        # including in the fast internal event-projection path.
        return MappingProxyType({k: _freeze(value[k]) for k in sorted(value)})
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
    npcs: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    actions: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    routes: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    travels: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    observations: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    navigation: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    relations: Mapping[str, Mapping[str, int]] = field(default_factory=dict)
    social_messages: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    obligations: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    consumptions: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    gatherings: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    foraging_attempts: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    survival_progress: Mapping[str, Mapping[str, int]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "entities", _freeze(_json_copy(self.entities)))
        object.__setattr__(self, "locations", _freeze(_json_copy(self.locations)))
        object.__setattr__(self, "resources", _freeze(_json_copy(self.resources)))
        object.__setattr__(self, "scheduled", _freeze(_json_copy(self.scheduled)))
        object.__setattr__(self, "npcs", _freeze(_json_copy(self.npcs)))
        object.__setattr__(self, "actions", _freeze(_json_copy(self.actions)))
        object.__setattr__(self, "routes", _freeze(_json_copy(self.routes)))
        object.__setattr__(self, "travels", _freeze(_json_copy(self.travels)))
        object.__setattr__(self, "observations", _freeze(_json_copy(self.observations)))
        object.__setattr__(self, "navigation", _freeze(_json_copy(self.navigation)))
        object.__setattr__(self, "relations", _freeze(_json_copy(self.relations)))
        object.__setattr__(self, "social_messages", _freeze(_json_copy(self.social_messages)))
        object.__setattr__(self, "obligations", _freeze(_json_copy(self.obligations)))
        object.__setattr__(self, "consumptions", _freeze(_json_copy(self.consumptions)))
        object.__setattr__(self, "gatherings", _freeze(_json_copy(self.gatherings)))
        object.__setattr__(self, "foraging_attempts", _freeze(_json_copy(self.foraging_attempts)))
        object.__setattr__(self, "survival_progress", _freeze(_json_copy(self.survival_progress)))

    def to_dict(self) -> dict[str, Any]:
        # Replay/projection states already passed full JSON normalization in
        # from_dict. Thawing their immutable payload is sufficient to hand
        # out a detached mutable copy without another JSON encode/decode.
        # Directly constructed WorldState instances retain the original strict
        # JSON validation, including the scalar fields.
        clone = _thaw if getattr(self, "_projection_normalized", False) else _json_copy
        return clone({"world_id": self.world_id, "time": self.time, "revision": self.revision,
                           "schema_version": self.schema_version, "rules_version": self.rules_version,
                           "entities": self.entities, "locations": self.locations, "resources": self.resources,
                           "scheduled": self.scheduled, "next_schedule_order": self.next_schedule_order,
                           "npcs": self.npcs, "actions": self.actions, "routes": self.routes,
                           "travels": self.travels, "observations": self.observations,
                           "navigation": self.navigation, "relations": self.relations,
                           "social_messages": self.social_messages, "obligations": self.obligations,
                           "consumptions": self.consumptions, "gatherings": self.gatherings,
                           "foraging_attempts": self.foraging_attempts,
                           "survival_progress": self.survival_progress})

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> WorldState:
        """Validate and normalize caller-owned snapshots at the public boundary."""
        return cls._decode_checked(d, normalize_json=True)

    @classmethod
    def _from_internal_projection(cls, d: dict[str, Any]) -> WorldState:
        """Project a domain-reducer output assembled from normalized JSON values.

        This private path is ONLY for apply_event after WorldState.to_dict and
        strict DomainEvent round-tripping. It still runs EVERY world validator,
        but avoids re-encoding/re-decoding the same JSON-native data. External
        snapshots must use from_dict; never trust arbitrary data here.
        """
        return cls._decode_checked(d, normalize_json=False)

    @classmethod
    def _decode_checked(cls, d: dict[str, Any], *, normalize_json: bool) -> WorldState:
        if not isinstance(d, dict) or set(d) != {"world_id", "time", "revision", "schema_version", "rules_version", "entities", "locations", "resources", "scheduled", "next_schedule_order", "npcs", "actions", "routes", "travels", "observations", "navigation", "relations", "social_messages", "obligations", "consumptions", "gatherings", "foraging_attempts", "survival_progress"}:
            raise ValueError("invalid world snapshot")
        if d["schema_version"] != SCHEMA_VERSION or d["rules_version"] != RULES_VERSION:
            raise ValueError("unsupported world version")
        if not isinstance(d["world_id"], str) or not d["world_id"] or any(type(d[k]) is not int or d[k] < 0 for k in ("time", "revision")):
            raise ValueError("invalid world identity/time/revision")
        if type(d["next_schedule_order"]) is not int or d["next_schedule_order"] < 1:
            raise ValueError("invalid schedule order")
        if any(not isinstance(d[k], dict) for k in ("entities", "locations", "resources", "scheduled", "npcs", "actions", "routes", "travels", "observations", "navigation", "relations", "social_messages", "obligations", "consumptions", "gatherings", "foraging_attempts", "survival_progress")):
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
        from .npc import validate_npc_state
        for ident, npc in d["npcs"].items():
            if ident not in d["entities"] or d["entities"][ident]["controller"] != "npc":
                raise ValueError("NPC profile must reference NPC-controlled entity")
            validate_npc_state(npc)
        from .actions import validate_actions
        validate_actions(d)
        from .movement import validate_movement
        validate_movement(d)
        from .movement import validate_player_schedules
        validate_player_schedules(d)
        from .navigation import validate_navigation
        validate_navigation(d)
        from .social import validate_social
        validate_social(d)
        from .assistance import validate_obligations
        validate_obligations(d)
        from .consumption import validate_consumptions
        validate_consumptions(d)
        from .survival import validate_survival_progress
        validate_survival_progress(d)
        from .gathering import validate_gatherings
        validate_gatherings(d)
        from .foraging import validate_foraging_attempts
        validate_foraging_attempts(d)
        # Public snapshots need full portable JSON normalization. Internal
        # projections have already been sourced from a detached, verified
        # WorldState and a portable DomainEvent. Both paths run the SAME
        # complete collection/domain validators above; never shortcut those.
        normalized = _json_copy(d) if normalize_json else d
        restored = object.__new__(cls)
        for name, value in normalized.items():
            object.__setattr__(restored, name, _freeze(value) if isinstance(value, dict) else value)
        object.__setattr__(restored, "_projection_normalized", True)
        return restored


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


def apply_event(state: WorldState, event: DomainEvent, *, bootstrap: bool = False, action_authorized: bool = False, movement_authorized: bool = False, social_authorized: bool = False, assistance_authorized: bool = False, consumption_authorized: bool = False, survival_authorized: bool = False) -> WorldState:
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
    elif kind in ("NPCConfigured", "NPCInformationDelivered", "NPCBeliefReceived", "NPCNeedChanged", "NPCDecisionRecorded"):
        from .npc import project_npc_event
        project_npc_event(d, e, bootstrap=bootstrap, survival_authorized=survival_authorized,
                          action_authorized=action_authorized)
    elif kind in ("RouteCreated", "NPCTravelStarted", "NPCObserved"):
        from .movement import project_movement_event
        project_movement_event(d, e, bootstrap=bootstrap, movement_authorized=movement_authorized)
    elif kind in ("NPCNavigationSurveyed", "NPCNavigationTargetSet"):
        from .navigation import project_navigation_event
        project_navigation_event(d, e, movement_authorized=movement_authorized)
    elif kind in ("SocialMessageSent", "SocialMessageReceived"):
        from .social import project_social_event
        project_social_event(d, e, social_authorized=social_authorized)
    elif kind in ("AssistanceRequested", "AssistanceResponded", "AssistanceFulfilled", "AssistanceCancelled"):
        from .assistance import project_assistance_event
        project_assistance_event(d, e, assistance_authorized=assistance_authorized)
    elif kind == "NPCFoodConsumed":
        from .consumption import project_food_consumed
        project_food_consumed(d, e, consumption_authorized=consumption_authorized)
    elif kind == "NPCFoodGathered":
        from .gathering import project_food_gathered
        project_food_gathered(d, e, action_authorized=action_authorized)
    elif kind == "NPCActionStarted":
        from .actions import start_action
        start_action(d, e, action_authorized=action_authorized)
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
        if resource in ("labor_units", "investigation_attempts") and source != "initialization":
            raise ValueError("NPC action counters may only change through scheduled action completion")
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
        if "__npc_action_id" in p["payload"]:
            if not action_authorized or set(p["payload"]) != {"__npc_action_id"} or p["interrupt"]:
                raise ValueError("NPC action schedule requires trusted action capability")
        if "__npc_travel_id" in p["payload"]:
            if not movement_authorized or set(p["payload"]) != {"__npc_travel_id"} or p["interrupt"]:
                raise ValueError("NPC travel schedule requires trusted movement capability")
        if "__player_travel" in p["payload"]:
            if (not movement_authorized or e.actor_id is not None
                    or set(p["payload"]) != {"__player_travel"} or p["interrupt"]):
                raise ValueError("player travel requires trusted local movement capability")
        d["scheduled"][p["id"]] = {k: _thaw(p[k]) for k in ("due", "order", "kind", "payload", "interrupt")}
        d["next_schedule_order"] += 1
    elif kind == "ScheduledEventCancelled":
        if set(p) != {"id"} or not isinstance(p["id"], str) or p["id"] not in d["scheduled"]:
            raise ValueError("cannot cancel missing schedule")
        if any(a["status"] == "running" and a["schedule_id"] == p["id"] for a in d["actions"].values()):
            raise ValueError("cannot cancel an ongoing NPC action; explicit cancellation is not supported")
        if any(t["status"] == "traveling" and t["schedule_id"] == p["id"] for t in d["travels"].values()):
            raise ValueError("cannot cancel an ongoing NPC travel; explicit cancellation is not supported")
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
        if "__npc_action_id" in scheduled["payload"]:
            from .actions import resolve_action
            resolve_action(d, scheduled["payload"]["__npc_action_id"], p["id"], state.time)
        if "__npc_travel_id" in scheduled["payload"]:
            from .movement import complete_travel
            complete_travel(d, scheduled["payload"]["__npc_travel_id"], p["id"], state.time)
        if "__player_travel" in scheduled["payload"]:
            from .movement import complete_player_travel
            complete_player_travel(d, p["id"], scheduled["payload"]["__player_travel"], state.time)
        del d["scheduled"][p["id"]]
    elif kind == "TimeAdvanced":
        if set(p) != {"from", "to"} or type(p["from"]) is not int or type(p["to"]) is not int:
            raise ValueError("invalid time advance")
        if p["from"] != state.time or p["to"] <= state.time or p["to"] != e.time:
            raise ValueError("invalid time transition")
        if d["scheduled"] and min(x["due"] for x in d["scheduled"].values()) < p["to"]:
            raise ValueError("time advancement would skip due scheduled event")
        if survival_authorized:
            from .survival import apply_survival_elapsed
            apply_survival_elapsed(d, p["to"] - p["from"])
    else:
        raise ValueError(f"unknown event type: {kind}")
    d["revision"] += 1
    d["time"] = e.time
    return WorldState._from_internal_projection(d)
