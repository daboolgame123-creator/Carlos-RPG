"""PLAY48 P9 optional local, voluntary emergency food help at a real village stop.

There are no global donor searches, magically delivered parcels or free food.
A healthy passer-by with a privately owned loaf and funds for replenishment
may honour ONE co-present starving courier's request. The existing assistance
reducer witnesses both parties and conserves actual inventory.
"""
from __future__ import annotations

from .domain import WorldState
from .market import _present
from .food_for_work import _worker_present_and_free

MIN_SEVERE_HUNGER = 90
MAX_DONOR_HUNGER = 40
MAX_DONOR_FATIGUE = 69


def choose_local_emergency_courier_help(state: WorldState, *, allow_hunter: bool = False) -> tuple[str, str] | None:
    """Return (requester, willing donor), observing only co-present village people.

    A donation is *not* made here; it still needs an authentic request,
    acceptance, settlement and eating events with normal reducer validation.
    """
    here = "well"
    raw = state.to_dict()
    # No rescue agent may scan distant personal stores, hunger or routes.
    present = sorted(
        who for who, entity in state.entities.items()
        if entity["location_id"] == here and who in state.npcs
        and _present(raw, who, here)
        and _worker_present_and_free(state, who, here)
    )
    if len(present) < 2:
        return None
    for recipient in present:
        npc = state.npcs[recipient]
        own = state.resources.get(recipient, {})
        if (npc["role"] != "courier" or npc["needs"]["hunger"] < MIN_SEVERE_HUNGER
                or own.get("food") != 0):
            continue
        if any(
            obligation["requester"] == recipient and obligation["resource"] == "food"
            and obligation["status"] in ("requested", "promised")
            for obligation in state.obligations.values()
        ):
            continue
        for donor in present:
            if donor == recipient:
                continue
            helper = state.npcs[donor]
            carried = state.resources.get(donor, {})
            # Even close-by, a person must not risk their own survival to
            # subsidize the entire village. One loaf and at least one actual
            # coin make this a finite, voluntary rescue opportunity.
            if (helper["needs"]["hunger"] > MAX_DONOR_HUNGER
                    or helper["needs"]["fatigue"] > MAX_DONOR_FATIGUE
                    or helper["needs"]["safety"] >= 75
                    or carried.get("food", 0) < 1
                    or (carried.get("coin_copper", 0) < 1 and not (
                        allow_hunter and helper["role"] == "hunter"
                        and helper["needs"]["hunger"] <= 35))
                    or state.relations.get(donor, {}).get(recipient, 0) < 0):
                continue
            committed = sum(
                obligation["quantity"] for obligation in state.obligations.values()
                if obligation["provider"] == donor
                and obligation["resource"] == "food"
                and obligation["status"] == "promised"
            )
            if carried["food"] - committed >= 1:
                return recipient, donor
    return None
