"""Phase 01-Q: finite, physically sourced food gathering (test worlds only).

A finished, time-costly investigation can recover one unit of wild food from
the NPC's present site. It is a local, explicit recovery decision, NOT a new
instantaneous investigation, a harvest growth model, or autonomous hunting.
The resource is transferred atomically, not minted or guessed from zero.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

from .domain import DomainEvent, WorldState
from .store import RevisionConflict, SQLiteEventStore
from .time_engine import TimeEngine

WILD_FOOD_RESOURCE = "wild_food"
OWNED_FOOD_RESOURCE = "food"
RECOVERY_QUANTITY = 1


def validate_gatherings(state: dict[str, Any]) -> None:
    """Validate persistent provenance of every historical gathering."""
    for action_id, record in state["gatherings"].items():
        if (not isinstance(action_id, str) or not action_id
                or not isinstance(record, dict)
                or set(record) != {"npc_id", "site_id", "at", "quantity",
                                   "site_before", "site_after", "food_before", "food_after"}):
            raise ValueError("invalid food-gathering record")
        npc, site, at = record["npc_id"], record["site_id"], record["at"]
        action = state["actions"].get(action_id)
        if (npc not in state["npcs"] or site not in state["locations"]
                or action is None or action["npc_id"] != npc
                or action["action"] != "investigate" or action["status"] != "completed"
                or type(at) is not int or not 0 <= at <= state["time"]
                or action["completed_at"] != at or record["quantity"] != RECOVERY_QUANTITY
                or type(record["quantity"]) is not int):
            raise ValueError("food gathering needs one completed investigation")
        source, remaining = record["site_before"], record["site_after"]
        owned, new_owned = record["food_before"], record["food_after"]
        if (any(type(v) is not int for v in (source, remaining, owned, new_owned))
                or source < RECOVERY_QUANTITY or owned < 0
                or remaining != source - RECOVERY_QUANTITY
                or new_owned != owned + RECOVERY_QUANTITY
                or source + owned != remaining + new_owned):
            raise ValueError("gathering must conserve initialized food")


def project_food_gathered(state: dict[str, Any], event: DomainEvent, *, action_authorized: bool) -> None:
    if not action_authorized or set(event.data) != {"npc_id", "action_id", "site_id"}:
        raise ValueError("gathering requires a trusted action capability and precise fields")
    npc_id, action_id, site = (
        event.data["npc_id"], event.data["action_id"], event.data["site_id"])
    if (not isinstance(npc_id, str) or npc_id not in state["npcs"]
            or event.actor_id != npc_id or not isinstance(action_id, str)
            or not action_id or not isinstance(site, str) or site not in state["locations"]):
        raise ValueError("invalid gatherer identity or site")
    if site != state["entities"][npc_id]["location_id"]:
        raise ValueError("gatherer must be physically at the source site")
    if any(t["npc_id"] == npc_id and t["status"] == "traveling"
           for t in state["travels"].values()):
        raise ValueError("gathering is impossible while traveling")
    if any(a["npc_id"] == npc_id and a["status"] == "running"
           for a in state["actions"].values()):
        raise ValueError("gathering is impossible while busy")
    action = state["actions"].get(action_id)
    if (action is None or action["npc_id"] != npc_id
            or action["action"] != "investigate" or action["status"] != "completed"
            or action["completed_at"] != state["time"]):
        raise ValueError("gathering requires a newly completed investigation")
    if action_id in state["gatherings"]:
        raise ValueError("investigation has already recovered food")
    # Unknown or absent resources are NOT zero and cannot be taken.
    source = state["resources"].get(site, {}).get(WILD_FOOD_RESOURCE)
    owned = state["resources"].get(npc_id, {}).get(OWNED_FOOD_RESOURCE)
    if (type(source) is not int or source < RECOVERY_QUANTITY
            or type(owned) is not int or owned < 0):
        raise ValueError("gathering requires initialized, sufficient natural food and owned inventory")
    state["resources"][site][WILD_FOOD_RESOURCE] = source - RECOVERY_QUANTITY
    state["resources"][npc_id][OWNED_FOOD_RESOURCE] = owned + RECOVERY_QUANTITY
    state["gatherings"][action_id] = {
        "npc_id": npc_id, "site_id": site, "at": state["time"],
        "quantity": RECOVERY_QUANTITY,
        "site_before": source, "site_after": source - RECOVERY_QUANTITY,
        "food_before": owned, "food_after": owned + RECOVERY_QUANTITY,
    }


@dataclass(frozen=True)
class GatheringResult:
    action_id: str
    quantity: int
    state: WorldState


class NPCGatheringService:
    """Explicit trusted-local command; does not run while play is paused."""

    def __init__(self, store: SQLiteEventStore, clock: TimeEngine):
        if clock.store is not store:
            raise ValueError("gathering service and clock must use the same store")
        self.store, self.clock = store, clock

    def collect(self, world_id: str, npc_id: str, action_id: str, *, command_id: str,
                expected_revision: int) -> GatheringResult:
        self.clock._require_session(world_id)
        state = self.store.load(world_id)
        if state.revision != expected_revision:
            raise RevisionConflict("stale food-gathering revision")
        location = state.entities[npc_id]["location_id"]
        event = DomainEvent("NPCFoodGathered", npc_id, "finite local food recovered after investigation",
                            state.time, {"npc_id": npc_id, "action_id": action_id, "site_id": location})
        saved = self.store.append(world_id, command_id, expected_revision, [event],
                                  action_authorized=True)
        return GatheringResult(action_id, RECOVERY_QUANTITY, saved)
