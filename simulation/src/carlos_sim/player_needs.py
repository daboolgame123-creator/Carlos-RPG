"""Explicit, opt-in physical player needs for disposable simulation worlds.

These fixed test-world rates are independent of RPG HP/ST/MP and NPC policy.
Only elapsed simulation time, genuinely consumed food, and a completed timed
rest change the configured values. No wall-clock time or automatic player AI.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .domain import DomainEvent, WorldState
from .movement import _in_transit

HUNGER_SECONDS_PER_POINT = 300
FATIGUE_SECONDS_PER_POINT = 600
HUNGER_RELIEF_PER_FOOD = 35
REST_SECONDS = 1800
REST_FATIGUE_RELIEF = 20

_FIELDS = {"hunger", "fatigue", "hunger_seconds", "fatigue_seconds"}


def _need(value: Any) -> bool:
    return type(value) is int and 0 <= value <= 100


def validate_player_needs(state: dict[str, Any]) -> None:
    rows = state["player_needs"]
    if not isinstance(rows, dict):
        raise ValueError("invalid player needs collection")
    for who, needs in rows.items():
        if (not isinstance(who, str) or who not in state["entities"]
                or state["entities"][who]["controller"] != "player"
                or not isinstance(needs, dict) or set(needs) != _FIELDS
                or not _need(needs["hunger"]) or not _need(needs["fatigue"])
                or type(needs["hunger_seconds"]) is not int
                or not 0 <= needs["hunger_seconds"] < HUNGER_SECONDS_PER_POINT
                or type(needs["fatigue_seconds"]) is not int
                or not 0 <= needs["fatigue_seconds"] < FATIGUE_SECONDS_PER_POINT):
            raise ValueError("invalid player needs or elapsed-time residuals")


def initialize_player_needs(state: dict[str, Any], event: DomainEvent, *,
                            bootstrap: bool) -> None:
    data = event.data
    if (not bootstrap or event.actor_id is not None or state["time"] != 0
            or set(data) != {"player_id", "hunger", "fatigue"}):
        raise ValueError("player needs require trusted time-zero initialization")
    who = data["player_id"]
    if (not isinstance(who, str) or who not in state["entities"]
            or state["entities"][who]["controller"] != "player"
            or who in state["player_needs"]
            or not _need(data["hunger"]) or not _need(data["fatigue"])):
        raise ValueError("player needs require a new real player and bounded values")
    state["player_needs"][who] = {
        "hunger": data["hunger"], "fatigue": data["fatigue"],
        "hunger_seconds": 0, "fatigue_seconds": 0,
    }


def player_rest_signal(state: WorldState, player_id: str):
    """Return this player's own durable rest, without consulting NPC needs."""
    for ident, schedule in state.scheduled.items():
        data = schedule["payload"].get("__player_rest")
        if data is not None and data["player_id"] == player_id:
            return ident, schedule, data
    return None


def validate_player_rest_schedules(state: dict[str, Any]) -> None:
    active: set[str] = set()
    foraging = {
        item["payload"]["__player_forage"]["player_id"]
        for item in state["scheduled"].values()
        if "__player_forage" in item["payload"]
    }
    for ident, schedule in state["scheduled"].items():
        payload = schedule["payload"]
        if "__player_rest" not in payload:
            continue
        data = payload["__player_rest"]
        if (set(payload) != {"__player_rest"}
                or not isinstance(data, dict)
                or set(data) != {"player_id", "site_id", "started_at"}):
            raise ValueError("invalid player rest signal")
        who, site, start = data["player_id"], data["site_id"], data["started_at"]
        if (not isinstance(who, str) or who not in state["player_needs"]
                or who in active or who in foraging
                or not isinstance(site, str) or site not in state["locations"]
                or state["entities"][who]["location_id"] != site
                or type(start) is not int
                or not 0 <= start <= state["time"] <= schedule["due"]
                or schedule["due"] - start != REST_SECONDS
                or schedule["interrupt"]
                or not ident.startswith("player-rest:" + who + ":")
                or _in_transit(state, who)):
            raise ValueError("invalid, forged or overlapping player rest schedule")
        active.add(who)


def apply_player_needs_elapsed(state: dict[str, Any], seconds: int) -> None:
    """Accrue once per clock event, preserving exact split-step residuals."""
    if type(seconds) is not int or seconds <= 0:
        raise ValueError("player needs elapsed seconds must be positive")
    resting = {
        item["payload"]["__player_rest"]["player_id"]
        for item in state["scheduled"].values()
        if "__player_rest" in item["payload"]
    }
    for who, needs in state["player_needs"].items():
        hunger, residual = divmod(
            needs["hunger_seconds"] + seconds, HUNGER_SECONDS_PER_POINT)
        needs["hunger_seconds"] = residual
        needs["hunger"] = min(100, needs["hunger"] + hunger)
        if who not in resting:
            fatigue, residual = divmod(
                needs["fatigue_seconds"] + seconds, FATIGUE_SECONDS_PER_POINT)
            needs["fatigue_seconds"] = residual
            needs["fatigue"] = min(100, needs["fatigue"] + fatigue)


def apply_player_meal(state: dict[str, Any], player_id: str) -> None:
    """Called only after the same event debits one genuinely owned edible unit."""
    needs = state["player_needs"].get(player_id)
    if needs is not None:
        needs["hunger"] = max(0, needs["hunger"] - HUNGER_RELIEF_PER_FOOD)


def complete_player_rest(state: dict[str, Any], signal_id: str,
                         data: Mapping[str, Any], now: int) -> None:
    """Relief belongs to the actual due signal, never the request or a read."""
    schedule = state["scheduled"].get(signal_id)
    if (schedule is None or schedule["due"] != now or state["time"] != now
            or schedule["payload"] != {"__player_rest": data}
            or now - data["started_at"] != REST_SECONDS):
        raise ValueError("rest completion requires its actual due signal")
    who, site = data["player_id"], data["site_id"]
    if (who not in state["player_needs"]
            or state["entities"][who]["controller"] != "player"
            or state["entities"][who]["location_id"] != site
            or _in_transit(state, who)):
        raise ValueError("resting player must remain physically at the rest site")
    needs = state["player_needs"][who]
    needs["fatigue"] = max(0, needs["fatigue"] - REST_FATIGUE_RELIEF)
