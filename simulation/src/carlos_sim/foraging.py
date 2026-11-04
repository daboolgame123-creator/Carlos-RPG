"""Phase 01-S: hunger-driven *local* forage decision and physical outcome.

No remote sensing, map knowledge, price, crop regrowth or RPG skill system.
At the current site a visible initialized wild-food deposit may motivate an
NPC to forage. A completed, scheduled action consumes effort/time before
transfer. Scarcity may make an already started attempt fail. No randomness.
"""
from __future__ import annotations
from collections.abc import Mapping
from typing import Any

FORAGING_MIN_HUNGER = 65
FORAGING_MAX_FATIGUE = 75
FORAGING_MAX_SAFETY_NEED = 70
WILD_FOOD = "wild_food"
OWNED_FOOD = "food"


def choose_local_foraging(
    npc_id: str, npc: Mapping[str, Any], site: str,
    resources: Mapping[str, Mapping[str, int | None]],
) -> tuple[int, str] | None:
    """A pure *locally observable* offer; never inspect another NPC/site.

    'wild_food' at the actor's present location is visible in the synthetic
    test environment, consistent with the previous 01-R policy. Knowledge
    of remote deposits, incorrect rumors and navigation are Phase 01-T/U.
    """
    needs = npc["needs"]
    own = resources.get(npc_id, {}).get(OWNED_FOOD)
    wild = resources.get(site, {}).get(WILD_FOOD)
    if (needs["hunger"] < FORAGING_MIN_HUNGER
            or needs["fatigue"] > FORAGING_MAX_FATIGUE
            or needs["safety"] > FORAGING_MAX_SAFETY_NEED
            or type(own) is not int or own != 0
            or type(wild) is not int or wild < 1):
        return None
    # Recorded intent explains physical site and subjective need. The precise
    # supply is deliberately not embedded in a promise/reservation: another
    # character may take the remaining food before this actor completes.
    return (1000 + needs["hunger"],
            f"local-forage-v1; npc={npc_id}; site={site}; hunger={needs['hunger']}; "
            f"fatigue={needs['fatigue']}; safety={needs['safety']}; food=0; deposit-visible")


def resolve_foraging(state: dict[str, Any], action_id: str, time: int) -> None:
    """Resolve on ScheduledEventFired, independent of coordinator mode.

    One completed forage = one logged attempt; an empty deposit produces a
    durable failed attempt with ZERO inventory added. This is not an extra
    command/event; the scheduled completion itself is the provenance.
    """
    action = state["actions"].get(action_id)
    if (action is None or action["action"] != "forage"
            or action["status"] != "completed"
            or action["completed_at"] != time
            or action_id in state["foraging_attempts"]):
        raise ValueError("foraging resolution requires one completed forage action")
    npc_id = action["npc_id"]
    site = state["entities"][npc_id]["location_id"]
    if (any(t["npc_id"] == npc_id and t["status"] == "traveling"
            for t in state["travels"].values())
            or any(a["npc_id"] == npc_id and a["status"] == "running"
                   for a in state["actions"].values())):
        raise ValueError("forage cannot resolve while actor is busy or traveling")
    source = state["resources"].get(site, {}).get(WILD_FOOD)
    owned = state["resources"].get(npc_id, {}).get(OWNED_FOOD)
    if (type(source) is not int or source < 0
            or type(owned) is not int or owned < 0):
        raise ValueError("foraging requires initialized local/owned stocks at resolution")
    got = 1 if source > 0 else 0
    state["resources"][site][WILD_FOOD] = source - got
    state["resources"][npc_id][OWNED_FOOD] = owned + got
    state["foraging_attempts"][action_id] = {
        "npc_id": npc_id, "site_id": site, "at": time,
        "outcome": "collected" if got else "depleted",
        "quantity": got,
        "site_before": source, "site_after": source - got,
        "food_before": owned, "food_after": owned + got,
    }


def validate_foraging_attempts(state: dict[str, Any]) -> None:
    """Reject absent outcomes, forged results and unrelated action history."""
    # Forage is an action with a mandatory physical outcome. In a normal
    # ScheduledEventFired reducer, resolve_action writes this record before
    # validation. A fabricated snapshot must not silently erase a failure.
    for action_id, action in state["actions"].items():
        if (action["action"] == "forage"
                and action["status"] == "completed"
                and action_id not in state["foraging_attempts"]):
            raise ValueError("completed forage action missing recorded outcome")
    for action_id, record in state["foraging_attempts"].items():
        if (not isinstance(action_id, str) or not action_id
                or not isinstance(record, dict)
                or set(record) != {"npc_id", "site_id", "at", "outcome",
                                   "quantity", "site_before", "site_after",
                                   "food_before", "food_after"}):
            raise ValueError("invalid foraging record")
        action = state["actions"].get(action_id)
        npc, site, at = record["npc_id"], record["site_id"], record["at"]
        if (npc not in state["npcs"] or site not in state["locations"]
                or action is None or action["npc_id"] != npc
                or action["action"] != "forage" or action["status"] != "completed"
                or type(at) is not int or not 0 <= at <= state["time"]
                or action["completed_at"] != at):
            raise ValueError("foraging record must match completed action")
        before, after = record["site_before"], record["site_after"]
        own_before, own_after = record["food_before"], record["food_after"]
        qty = record["quantity"]
        if (any(type(v) is not int for v in (before, after, own_before, own_after, qty))
                or before < 0 or own_before < 0
                or qty != (1 if before > 0 else 0)
                or after != before - qty
                or own_after != own_before + qty
                or record["outcome"] != ("collected" if qty else "depleted")
                or before + own_before != after + own_after):
            raise ValueError("foraging record violates resource conservation")
