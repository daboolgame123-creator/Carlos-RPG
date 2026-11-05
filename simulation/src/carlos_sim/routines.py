"""Phase 02-F: explicit, optional NPC home/work routine without privileged travel."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from .domain import DomainEvent, WorldState, _json_copy
from .navigation import shortest_known_route

DAY_SECONDS = 86400

def configure_routine(state: dict[str, Any], event: DomainEvent, *, bootstrap: bool) -> None:
    data = _json_copy(event.data)
    if not bootstrap or state["time"] != 0 or event.actor_id is not None or set(data) != {
        "npc_id", "home_id", "workplace_id", "work_start", "work_end"
    }:
        raise ValueError("routine requires trusted time-zero bootstrap")
    who = data["npc_id"]
    if type(who) is not str or who not in state["npcs"] or who in state["npc_routines"]:
        raise ValueError("routine owner must be a unique configured NPC")
    _validate_profile(state, who, {k: data[k] for k in ("home_id", "workplace_id", "work_start", "work_end")})
    state["npc_routines"][who] = {k: data[k] for k in ("home_id", "workplace_id", "work_start", "work_end")}

def _validate_profile(state: dict[str, Any], who: str, profile: Any) -> None:
    if not isinstance(profile, dict) or set(profile) != {
        "home_id", "workplace_id", "work_start", "work_end"
    }:
        raise ValueError("invalid routine profile")
    if type(profile["home_id"]) is not str or profile["home_id"] not in state["locations"]:
        raise ValueError("home must be a real location")
    place = profile["workplace_id"]
    if place is not None and (type(place) is not str or place not in state["locations"]
                              or place == profile["home_id"]):
        raise ValueError("workplace must be a distinct real location or null")
    if any(type(profile[k]) is not int or not 0 <= profile[k] < DAY_SECONDS
           for k in ("work_start", "work_end")):
        raise ValueError("routine bounds must be integer day offsets")
    if place is None and (profile["work_start"] != 0 or profile["work_end"] != 0):
        raise ValueError("work-free schedule must use zero time bounds")
    if place is not None and profile["work_start"] == profile["work_end"]:
        raise ValueError("work shift must have a nonzero duration")

def validate_routines(state: dict[str, Any]) -> None:
    records = state["npc_routines"]
    if not isinstance(records, dict):
        raise ValueError("routine ledger must be a mapping")
    for who, record in records.items():
        if who not in state["npcs"]:
            raise ValueError("routine actor is not an NPC")
        _validate_profile(state, who, record)

@dataclass(frozen=True)
class RoutineIntent:
    destination: str
    route_id: str
    reason: str

def choose_routine_route(state: WorldState, npc_id: str) -> RoutineIntent | None:
    """Decide one physical known-road leg; no state mutation and no remote inspection."""
    profile = state.npc_routines.get(npc_id)
    if profile is None or npc_id not in state.npcs:
        return None
    if any(a["npc_id"] == npc_id and a["status"] == "running" for a in state.actions.values()):
        return None
    if any(t["npc_id"] == npc_id and t["status"] == "traveling" for t in state.travels.values()):
        return None
    if any(job["npc_id"] == npc_id and job["status"] == "running"
           for job in state.production_jobs.values()):
        return None
    nav = state.navigation.get(npc_id)
    if nav is None or nav["target"] is not None:
        return None
    npc = state.npcs[npc_id]
    # This is a voluntary schedule; a hungry, exhausted or frightened person
    # must not blindly commute. No remote information or food is consulted.
    if (npc["needs"]["hunger"] >= 75 or npc["needs"]["fatigue"] >= 70
            or npc["needs"]["safety"] >= 75):
        return None
    now = state.time % DAY_SECONDS
    start, end = profile["work_start"], profile["work_end"]
    at_work = (start <= now < end) if start < end else (now >= start or now < end)
    dest = profile["workplace_id"] if at_work and profile["workplace_id"] is not None else profile["home_id"]
    here = state.entities[npc_id]["location_id"]
    if dest == here:
        return None
    path = shortest_known_route(state, npc_id, dest)
    if not path:
        return None
    return RoutineIntent(dest, path[0], "scheduled work commute" if at_work else "scheduled homeward commute")


def work_allowed_at(entities: Any, npcs: Any, routines: Any,
                    world_time: int, npc_id: str) -> bool:
    """The shared deterministic work gate for both planning and event reduction."""
    profile = routines.get(npc_id)
    if profile is None:
        return True
    place = profile["workplace_id"]
    if place is None or entities[npc_id]["location_id"] != place:
        return False
    npc = npcs[npc_id]
    if npc["needs"]["hunger"] >= 90 or npc["needs"]["safety"] >= 75:
        return False
    now = world_time % DAY_SECONDS
    start, end = profile["work_start"], profile["work_end"]
    return (start <= now < end) if start < end else (now >= start or now < end)


def routine_allows_work(state: WorldState, npc_id: str) -> bool:
    """Work has a physical workplace and shift; ongoing work is never cancelled."""
    return work_allowed_at(state.entities, state.npcs, state.npc_routines,
                           state.time, npc_id)


def next_routine_boundary(state: WorldState) -> int | None:
    """Next future clock boundary for active shifts; never uses wall-clock time."""
    candidates = []
    start_day = (state.time // DAY_SECONDS) * DAY_SECONDS
    for profile in state.npc_routines.values():
        if profile["workplace_id"] is None:
            continue
        for offset in (profile["work_start"], profile["work_end"]):
            transition = start_day + offset
            if transition <= state.time:
                transition += DAY_SECONDS
            candidates.append(transition)
    return min(candidates) if candidates else None
