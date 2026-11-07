"""PLAY-12: 60-second physically local forage; conserved, replay-safe due signal.

No player search succeeds at its start. The trusted scheduled firing commits
the finite transfer at the due tick or yields nothing if food was exhausted.
"""
from __future__ import annotations
from typing import Any
from .domain import WorldState
from .movement import _in_transit

WILD_FOOD_RESOURCE = "wild_food"
OWNED_FOOD_RESOURCE = "food"
FORAGE_SECONDS = 60


def player_forage_signal(state: WorldState, player_id: str):
    """The named player's own pending job, never an arbitrary NPC schedule."""
    for ident, schedule in state.scheduled.items():
        data = schedule["payload"].get("__player_forage")
        if data is not None and data["player_id"] == player_id:
            return ident, schedule, data
    return None


def local_food_view(state: WorldState, player_id: str) -> dict[str, Any]:
    """Only local qualitative stock; a busy player's search is visible."""
    if _in_transit(state.to_dict(), player_id):
        return {"status": "traveling"}
    site = state.entities[player_id]["location_id"]
    pending = player_forage_signal(state, player_id)
    if pending is not None:
        return {"location_id": site, "status": "foraging",
                "remaining_seconds": pending[1]["due"] - state.time}
    stock = state.resources.get(site, {}).get(WILD_FOOD_RESOURCE)
    status = ("present" if stock > 0 else "empty") if type(stock) is int else "unknown"
    return {"location_id": site, "status": status}


def validate_player_forage_schedules(state: dict[str, Any]) -> None:
    """Durable anti-teleport, anti-parallelism and immutable duration invariant."""
    active: set[str] = set()
    travelling = {
        item["payload"]["__player_travel"]["player_id"]
        for item in state["scheduled"].values()
        if "__player_travel" in item["payload"]
    }
    for ident, item in state["scheduled"].items():
        payload = item["payload"]
        if "__player_forage" not in payload:
            continue
        if set(payload) != {"__player_forage"} or not isinstance(payload["__player_forage"], dict):
            raise ValueError("invalid player forage signal")
        data = payload["__player_forage"]
        if set(data) != {"player_id", "site_id", "started_at"}:
            raise ValueError("invalid player forage data")
        who, site, start = data["player_id"], data["site_id"], data["started_at"]
        if (not isinstance(who, str) or not who or who not in state["entities"]
                or state["entities"][who]["controller"] != "player"
                or not isinstance(site, str) or site not in state["locations"]
                or state["entities"][who]["location_id"] != site
                or who in active or who in travelling
                or type(start) is not int or not 0 <= start <= state["time"] <= item["due"]
                or item["due"] - start != FORAGE_SECONDS
                or item["interrupt"]
                or not ident.startswith("player-forage:" + who + ":")
                or _in_transit(state, who)):
            raise ValueError("invalid, forged or overlapping player forage schedule")
        active.add(who)


def complete_player_forage(state: dict[str, Any], signal_id: str,
                           data: dict[str, Any], now: int) -> None:
    """Resolve using stock *at due time*. Zero or missing gives no reward."""
    schedule = state["scheduled"].get(signal_id)
    if (schedule is None or schedule["due"] != now
            or schedule["payload"] != {"__player_forage": data}):
        raise ValueError("forage completion requires its actual due signal")
    who, site = data["player_id"], data["site_id"]
    if (state["entities"][who]["controller"] != "player"
            or state["entities"][who]["location_id"] != site
            or _in_transit(state, who)):
        raise ValueError("forager must remain physically at the source")
    source = state["resources"].get(site, {}).get(WILD_FOOD_RESOURCE)
    owned = state["resources"].get(who, {}).get(OWNED_FOOD_RESOURCE)
    if type(owned) is not int or owned < 0:
        raise ValueError("player owned food is not initialized")
    if type(source) is int and source > 0:
        state["resources"][site][WILD_FOOD_RESOURCE] = source - 1
        state["resources"][who][OWNED_FOOD_RESOURCE] = owned + 1
