"""PLAY-14: explicit, opt-in daily player needs, completely separate from RPG vitals.

This is a deterministic *test-village* hunger/fatigue model, not combat ST,
HP, MP, skills, injury treatment, starvation, death or canonical Carlos data.

Known values are 0..100 pressure (HIGHER means MORE hunger/fatigue).
The NPC prototype already uses these exact clock rates and 25-point food
relief. Without an explicit PlayerNeedsInitialized, values remain UNKNOWN.
"""
from __future__ import annotations
from typing import Any
from .domain import DomainEvent
from .survival import HUNGER_SECONDS_PER_POINT, FATIGUE_SECONDS_PER_POINT
from .consumption import HUNGER_RELIEF_PER_FOOD

NEED_FIELDS = frozenset(("hunger", "fatigue", "hunger_seconds", "fatigue_seconds"))


def validate_player_needs(state: dict[str, Any]) -> None:
    for ident, record in state["player_needs"].items():
        if (ident not in state["entities"]
                or state["entities"][ident]["controller"] != "player"
                or not isinstance(record, dict) or set(record) != NEED_FIELDS):
            raise ValueError("player needs must be an explicitly configured player")
        h, f = record["hunger"], record["fatigue"]
        hs, fs = record["hunger_seconds"], record["fatigue_seconds"]
        if (type(h) is not int or not 0 <= h <= 100
                or type(f) is not int or not 0 <= f <= 100
                or type(hs) is not int or not 0 <= hs < HUNGER_SECONDS_PER_POINT
                or type(fs) is not int or not 0 <= fs < FATIGUE_SECONDS_PER_POINT):
            raise ValueError("invalid player needs or fractional clock progress")


def project_player_needs_initialized(state: dict[str, Any], event: DomainEvent, *,
                                     bootstrap: bool) -> None:
    data = event.data
    if (not bootstrap or state["time"] != 0 or event.actor_id is not None
            or set(data) != {"player_id", "hunger", "fatigue"}):
        raise ValueError("player needs initialization requires trusted time-zero bootstrap")
    who = data["player_id"]
    if (not isinstance(who, str) or who not in state["entities"]
            or state["entities"][who]["controller"] != "player"
            or who in state["player_needs"]
            or any(type(data[k]) is not int or not 0 <= data[k] <= 100
                   for k in ("hunger", "fatigue"))):
        raise ValueError("invalid or duplicated player needs initialization")
    state["player_needs"][who] = {
        "hunger": data["hunger"], "fatigue": data["fatigue"],
        "hunger_seconds": 0, "fatigue_seconds": 0,
    }


def apply_player_needs_elapsed(state: dict[str, Any], seconds: int) -> None:
    """Split-step associative; ordinary explicit game time, never wall clock."""
    if type(seconds) is not int or seconds <= 0:
        raise ValueError("invalid elapsed time for player needs")
    for who in sorted(state["player_needs"]):
        row = state["player_needs"][who]
        points, residue = divmod(
            row["hunger_seconds"] + seconds, HUNGER_SECONDS_PER_POINT)
        row["hunger_seconds"] = residue
        row["hunger"] = min(100, row["hunger"] + points)
        points, residue = divmod(
            row["fatigue_seconds"] + seconds, FATIGUE_SECONDS_PER_POINT)
        row["fatigue_seconds"] = residue
        row["fatigue"] = min(100, row["fatigue"] + points)


def apply_player_meal(state: dict[str, Any], who: str) -> None:
    """Only an actual authorized own-food meal reduces *ordinary hunger*.

    Existing PlayerFoodEaten must already have debited one known owned food
    unit. No fatigue relief, HP/ST/MP healing or inferred nutrition.
    """
    row = state["player_needs"].get(who)
    if row is not None:
        row["hunger"] = max(0, row["hunger"] - HUNGER_RELIEF_PER_FOOD)
