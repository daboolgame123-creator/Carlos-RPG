"""PLAY-28B: real water comes only from bounded, explicitly attested rain.

No wall-clock rainfall, implicit well replenishment, or remote farm credit.
Persistent observations are versioned with the world; active-session delivery
is gated independently of crop growth, supply travel and ordinary NPC actions.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .domain import DomainEvent, WorldState
from .store import SQLiteEventStore, RevisionConflict
from .time_engine import TimeEngine

MAX_WATER = 2**31 - 1
MAX_OBSERVATIONS = 1024
MAX_RAIN_PER_RECORD = 1000


def _valid_id(value: Any, max_length: int = 64) -> bool:
    return (type(value) is str and 1 <= len(value) <= max_length
            and value.isascii()
            and all(ch.isalnum() or ch in "._-" for ch in value))


def _stock(value: Any) -> bool:
    return type(value) is int and 0 <= value <= MAX_WATER


def configure_source(state: dict, event: DomainEvent, *, bootstrap: bool) -> None:
    p = event.data
    if (not bootstrap or state["time"] != 0 or event.actor_id is not None
            or set(p) != {"site_id", "capacity"}):
        raise ValueError("rain source requires trusted time-zero configuration")
    site, capacity = p["site_id"], p["capacity"]
    if (not _valid_id(site, 32) or site not in state["locations"]
            or site in state["hydrology_sources"]
            or not _stock(capacity) or capacity < 1):
        raise ValueError("invalid finite water source or capacity")
    water = state["resources"].get(site, {}).get("water")
    if not _stock(water) or water > capacity:
        raise ValueError("source requires known initialized water within capacity")
    state["hydrology_sources"][site] = {
        "site_id": site, "capacity": capacity,
        "initial": water, "received_total": 0,
        "last_refill_at": None, "observations": {},
    }


def record_rain(state: dict, event: DomainEvent, *,
                hydrology_authorized: bool, bootstrap: bool) -> None:
    p = event.data
    if (not hydrology_authorized or bootstrap or event.actor_id is not None
            or set(p) != {"source_id", "observation_id", "units"}):
        raise ValueError("rain requires dedicated authenticated observation authority")
    site, ident, units = p["source_id"], p["observation_id"], p["units"]
    source = state["hydrology_sources"].get(site) if type(site) is str else None
    if (source is None or not _valid_id(ident)
            or type(units) is not int or not 1 <= units <= MAX_RAIN_PER_RECORD
            or ident in source["observations"]
            or len(source["observations"]) >= MAX_OBSERVATIONS):
        raise ValueError("invalid, repeated or unbounded rain observation")
    if source["last_refill_at"] is not None and event.time < source["last_refill_at"]:
        raise ValueError("rain observation would rewind time")
    available = state["resources"][site]["water"]
    if (not _stock(available) or available + units > source["capacity"]
            or source["received_total"] + units > MAX_WATER):
        raise ValueError("rain exceeds finite physical well capacity")
    state["resources"][site]["water"] = available + units
    source["received_total"] += units
    source["last_refill_at"] = state["time"]
    source["observations"][ident] = {"units": units, "at": state["time"]}


def validate_sources(state: dict) -> None:
    sources = state["hydrology_sources"]
    if type(sources) is not dict:
        raise ValueError("invalid hydrology collection")
    for site, source in sources.items():
        if (not _valid_id(site, 32) or site not in state["locations"]
                or type(source) is not dict
                or set(source) != {"site_id", "capacity", "initial",
                                   "received_total", "last_refill_at", "observations"}
                or source["site_id"] != site
                or not all(_stock(source[k])
                           for k in ("capacity", "initial", "received_total"))
                or source["capacity"] < 1 or source["initial"] > source["capacity"]
                or type(source["observations"]) is not dict
                or len(source["observations"]) > MAX_OBSERVATIONS):
            raise ValueError("invalid durable finite water source")
        water = state["resources"].get(site, {}).get("water")
        if not _stock(water) or water > source["capacity"]:
            raise ValueError("water source exceeds known capacity")
        records = source["observations"]
        total = 0
        newest = None
        for ident, obs in records.items():
            if (not _valid_id(ident) or type(obs) is not dict
                    or set(obs) != {"units", "at"}
                    or type(obs["units"]) is not int
                    or not 1 <= obs["units"] <= MAX_RAIN_PER_RECORD
                    or type(obs["at"]) is not int
                    or not 0 <= obs["at"] <= state["time"]):
                raise ValueError("invalid recorded rain provenance")
            total += obs["units"]
            newest = max(newest or 0, obs["at"])
        if (total != source["received_total"]
                or (newest is None and source["last_refill_at"] is not None)
                or (newest is not None and source["last_refill_at"] != newest)):
            raise ValueError("rain receipts and received water disagree")


@dataclass(frozen=True)
class RainRecordResult:
    state: WorldState
    observation_id: str
    accepted_units: int


class FiniteWaterService:
    """Application-level measurement gate; no autonomous rainfall emitter."""

    def __init__(self, store: SQLiteEventStore, clock: TimeEngine):
        if clock.store is not store:
            raise ValueError("hydrology and logical clock must share a database")
        self.store, self.clock = store, clock

    def record(self, world_id: str, source_id: str, observation_id: str, units: int,
               *, command_id: str, expected_revision: int) -> RainRecordResult:
        self.clock._require_session(world_id)
        current = self.store.load(world_id)
        if current.revision != expected_revision:
            raise RevisionConflict("stale rain observation revision")
        event = DomainEvent("RainWaterRecorded", None,
                            "attested measured rainfall, not autonomous weather",
                            current.time, {"source_id": source_id,
                                           "observation_id": observation_id,
                                           "units": units})
        saved = self.store.append(world_id, command_id, expected_revision, [event],
                                  hydrology_authorized=True)
        return RainRecordResult(saved, observation_id, units)
