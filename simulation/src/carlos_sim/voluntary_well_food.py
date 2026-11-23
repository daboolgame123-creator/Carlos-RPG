"""PLAY48 P8: voluntary fisher visit and existing *local assistance* at a well.

A personally fed fisher who owns one real spare loaf may choose to visit a
personally learned adjacent communal well. This never reads distant hunger,
food or occupants. ONLY upon physical arrival may a starving present neighbor
ask for one real loaf through existing AssistanceRequested/Responded/Fulfilled
events. The donor retains complete freedom to decline when unwell, unwilling,
busy or committed. This file contains PURE proposals, no world mutations.
"""
from __future__ import annotations

from dataclasses import dataclass

from .domain import WorldState
from .navigation import shortest_known_route
from .npc import _injury_rest_decision

MAX_VOLUNTEER_HUNGER = 35
MAX_VOLUNTEER_FATIGUE = 69
MAX_VOLUNTEER_SAFETY = 74
MIN_NEIGHBOR_HUNGER = 90


@dataclass(frozen=True)
class VolunteerWellVisit:
    donor: str
    route_id: str


@dataclass(frozen=True)
class NeighborAid:
    donor: str
    recipient: str
    request_id: str


def _available(state: WorldState, who: str) -> bool:
    return (who in state.npcs
        and not any(a["npc_id"] == who and a["status"] == "running"
                    for a in state.actions.values())
        and not any(t["npc_id"] == who and t["status"] == "traveling"
                    for t in state.travels.values())
        and not any(j["npc_id"] == who and j["status"] == "running"
                    for j in state.production_jobs.values()))


def _prepared_fisher(state: WorldState, who: str) -> bool:
    """The donor has already personally eaten and still owns one spare loaf."""
    npc = state.npcs.get(who)
    if npc is None or npc["role"] != "fisher" or not _available(state, who):
        return False
    needs = npc["needs"]
    food = state.resources.get(who, {}).get("food")
    if (type(food) is not int or food < 1
            or needs["hunger"] > MAX_VOLUNTEER_HUNGER
            or needs["fatigue"] > MAX_VOLUNTEER_FATIGUE
            or needs["safety"] > MAX_VOLUNTEER_SAFETY
            or _injury_rest_decision(state.injuries, who) is not None):
        return False
    # An already promised portion takes precedence over a new courtesy trip.
    return not any(o["provider"] == who and o["resource"] == "food"
                   and o["status"] in ("requested", "promised")
                   for o in state.obligations.values())


def choose_volunteer_well_visit(state: WorldState, who: str) -> VolunteerWellVisit | None:
    """Leave from the fisher's ACTUAL fishery over ONE previously learned road.

    No read of recipients or food anywhere else; an unsuccessful well visit is
    a possible and legitimate outcome. Never skip the physical road.
    """
    if not _prepared_fisher(state, who) or "well" not in state.locations:
        return None
    here = state.entities[who]["location_id"]
    routine = state.npc_routines.get(who)
    nav = state.navigation.get(who)
    if (routine is None or routine["workplace_id"] != here
            or here == "well" or nav is None or nav["target"] is not None):
        return None
    route = shortest_known_route(state, who, "well")
    if len(route) != 1:
        return None
    return VolunteerWellVisit(who, route[0])


def _prepared_hunter(state: WorldState, who: str) -> bool:
    """A hunter can volunteer only with a genuinely owned spare food portion."""
    npc = state.npcs.get(who)
    if npc is None or npc["role"] != "hunter" or not _available(state, who):
        return False
    needs = npc["needs"]
    food = state.resources.get(who, {}).get("food")
    nav = state.navigation.get(who)
    if (type(food) is not int or food < 1
            or needs["hunger"] > MAX_VOLUNTEER_HUNGER
            or needs["fatigue"] > MAX_VOLUNTEER_FATIGUE
            or needs["safety"] > MAX_VOLUNTEER_SAFETY
            or _injury_rest_decision(state.injuries, who) is not None
            or nav is None or nav["target"] is not None):
        return False
    return not any(o["provider"] == who and o["resource"] == "food"
                   and o["status"] in ("requested", "promised")
                   for o in state.obligations.values())


HUNTER_VOLUNTEER_PREFIX = "well-neighbor:"
HUNTER_MAX_EXPLORATION = 1800


def hunter_can_seek_well(state: WorldState, who: str) -> bool:
    """One bounded visit starting at actual hunting workplace, no map oracle."""
    if not _prepared_hunter(state, who) or "well" not in state.locations:
        return False
    if state.entities[who]["location_id"] == "well":
        return False
    history = [t["start"] for ident, t in state.travels.items()
               if t["npc_id"] == who
               and ident.startswith(HUNTER_VOLUNTEER_PREFIX + who + ":")]
    if history:
        return state.time - min(history) < HUNTER_MAX_EXPLORATION
    routine = state.npc_routines.get(who)
    return routine is not None and (
        state.entities[who]["location_id"] == routine["workplace_id"]
    )


def choose_hunter_well_visit(state: WorldState, who: str) -> VolunteerWellVisit | None:
    """Follow a genuine known well road or explore a locally learned frontier.

    Well location is a community facility, not knowledge of its occupants:
    the hunter cannot observe distant recipients or obtain a hidden route.
    Survey and adjacent-road knowledge must be acquired on *actual arrival*.
    Frontier exploration is bounded to one 30-minute attempt and never
    changes a historical route, money, food or welfare contract.
    """
    if not hunter_can_seek_well(state, who):
        return None
    known = shortest_known_route(state, who, "well")
    if known:
        return VolunteerWellVisit(who, known[0])
    nav = state.navigation[who]
    here = state.entities[who]["location_id"]
    frontier = []
    for rid in nav["known_routes"]:
        road = state.routes[rid]
        for destination in (road["a"], road["b"]):
            if destination == here or destination in nav["visited"]:
                continue
            path = shortest_known_route(state, who, destination)
            if path:
                distance = sum(state.routes[x]["seconds"] for x in path)
                frontier.append((distance, destination, path))
    if not frontier:
        return None
    _, _, path = min(frontier)
    return VolunteerWellVisit(who, path[0])


def volunteer_waits_to_offer(state: WorldState, who: str, *,
                             allow_hunter: bool = False) -> bool:
    """Spend at most one real hour witnessing nearby needs after arriving.

    People resting at the well cannot transact until their current activity
    ends. A visitor need not immediately depart before anyone can speak.
    This has no distant knowledge, force, transfer, or indefinite waiting.
    """
    if (not (_prepared_fisher(state, who) or
             (allow_hunter and _prepared_hunter(state, who)))
            or state.entities[who]["location_id"] != "well"):
        return False
    latest_arrival = max((
        t["arrived_at"] for t in state.travels.values()
        if t["npc_id"] == who and t["status"] == "arrived"
        and t["destination"] == "well"
    ), default=None)
    if latest_arrival is None or not 0 <= state.time - latest_arrival < 3600:
        return False
    return any(
        peer != who and state.entities[peer]["location_id"] == "well"
        and state.npcs[peer]["needs"]["hunger"] >= MIN_NEIGHBOR_HUNGER
        and state.resources.get(peer, {}).get("food") == 0
        for peer in state.npcs
    )


def choose_local_well_request(state: WorldState, *,
                              allow_hunter: bool = False) -> NeighborAid | None:
    """Starving neighbor sees a WILLING, well-fed donor physically at the well.

    No donor stock is conjured, no requester can infer remote food, and
    untrusted or occupied people cannot be forced into a social contract.
    """
    if "well" not in state.locations:
        return None
    raw = state.to_dict()
    donors = []
    for who in sorted(state.npcs):
        if not (_prepared_fisher(state, who) or
                (allow_hunter and _prepared_hunter(state, who))):
            continue
        if state.entities[who]["location_id"] == "well":
            donors.append(who)
    for recipient in sorted(state.npcs,
                            key=lambda x: (-state.npcs[x]["needs"]["hunger"], x)):
        if not _available(state, recipient) or state.entities[recipient]["location_id"] != "well":
            continue
        if state.npcs[recipient]["needs"]["hunger"] < MIN_NEIGHBOR_HUNGER:
            continue
        if raw["resources"].get(recipient, {}).get("food") != 0:
            continue
        # A person awaiting help does not ask someone else or repeatedly
        # demand food at the same logical timestamp.
        if any(o["requester"] == recipient and o["resource"] == "food"
               and (o["status"] in ("requested", "promised")
                    or o["created_at"] == state.time)
               for o in state.obligations.values()):
            continue
        for donor in donors:
            if donor == recipient or state.relations.get(donor, {}).get(recipient, 0) < 0:
                continue
            request_id = f"auto-help:{recipient}:{state.time}"
            if request_id in state.obligations or len(request_id) > 128:
                continue
            return NeighborAid(donor, recipient, request_id)
    return None


def choose_local_well_settlement(state: WorldState, *,
                                 allow_hunter: bool = False) -> NeighborAid | None:
    """Honor only an old, already accepted, physically payable well promise."""
    for ident, o in sorted(state.obligations.items(),
                           key=lambda kv: (kv[1]["created_at"], kv[0])):
        if (o["status"] != "promised" or o["resource"] != "food"
                or o["quantity"] != 1 or o["location_id"] != "well"
                or o["responded_at"] >= state.time):
            continue
        donor, recipient = o["provider"], o["requester"]
        if not _available(state, donor) or not _available(state, recipient):
            continue
        if (state.entities[donor]["location_id"] == "well"
                and state.entities[recipient]["location_id"] == "well"
                and (state.npcs[donor]["role"] == "fisher" or
                     (allow_hunter and state.npcs[donor]["role"] == "hunter"))
                and state.resources[donor].get("food", 0) >= 1):
            return NeighborAid(donor, recipient, ident)
    return None
