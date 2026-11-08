"""PLAY-28B experimental, pure, finite-water accounting.

NOT connected to WorldState, events, or a real weather provider. This module
makes no claim of water magically appearing during elapsed time: rainfall
is an externally recorded observation, not an autonomous game decision.
The eventual event reducer must enforce its own authorization and exact time.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

MAX_STOCK = 2**31 - 1
MAX_OBSERVATIONS = 1024


def _stock(amount: object) -> bool:
    return type(amount) is int and 0 <= amount <= MAX_STOCK


@dataclass(frozen=True)
class Well:
    site: str
    capacity: int
    initial: int
    balance: int
    received_total: int = 0
    observations: tuple[tuple[str, int, int], ...] = ()

    def __post_init__(self) -> None:
        if (type(self.site) is not str or not 1 <= len(self.site) <= 32
                or not self.site.isascii()
                or any(not (ch.isalnum() or ch in "._-") for ch in self.site)):
            raise ValueError("well requires a stable physical location identifier")
        if (not all(_stock(n) for n in
                    (self.capacity, self.initial, self.balance, self.received_total))
                or self.initial > self.capacity
                or self.balance > self.capacity
                or type(self.observations) is not tuple
                or len(self.observations) > MAX_OBSERVATIONS):
            raise ValueError("invalid finite well stock or capacity")
        seen: set[str] = set()
        prev_time = 0
        total = 0
        for item in self.observations:
            if (type(item) is not tuple or len(item) != 3
                    or type(item[0]) is not str
                    or not 1 <= len(item[0]) <= 64 or not item[0].isascii()
                    or any(not (c.isalnum() or c in "._-") for c in item[0])
                    or item[0] in seen
                    or not _stock(item[1]) or item[1] == 0
                    or not _stock(item[2]) or item[2] < prev_time):
                raise ValueError("invalid or duplicate rain observation")
            seen.add(item[0])
            total += item[1]
            prev_time = item[2]
        if total != self.received_total:
            raise ValueError("rain provenance does not account for accepted units")


def recorded_rain(well: Well, *, observation_id: str,
                  units: int, logical_time: int) -> Well:
    """Pure proposed state; a trusted boundary must attest the observation."""
    if (type(observation_id) is not str
            or not 1 <= len(observation_id) <= 64 or not observation_id.isascii()
            or any(not (c.isalnum() or c in "._-") for c in observation_id)):
        raise ValueError("rain requires a stable valid observation ID")
    if type(units) is not int or not 1 <= units <= MAX_STOCK:
        raise ValueError("rain must provide positive measured units")
    if type(logical_time) is not int or not 0 <= logical_time <= 2**63 - 1:
        raise ValueError("rain must use a valid logical clock tick")
    if (any(ident == observation_id for ident, _, _ in well.observations)
            or len(well.observations) >= MAX_OBSERVATIONS):
        raise ValueError("repeated or unbounded rain observation")
    if well.observations and logical_time < well.observations[-1][2]:
        raise ValueError("rain cannot rewrite previous time")
    if well.balance + units > well.capacity:
        raise ValueError("rain exceeds physical well capacity")
    if well.received_total + units > MAX_STOCK:
        raise ValueError("rain ledger counter overflow")
    return replace(well, balance=well.balance + units,
                   received_total=well.received_total + units,
                   observations=well.observations +
                   ((observation_id, units, logical_time),))


def local_load(well: Well, *, courier_location: str,
               cargo_water: int) -> tuple[Well, int]:
    """One physical water parcel at the well; no remote loading or extra cargo."""
    if (type(courier_location) is not str or courier_location != well.site
            or not _stock(cargo_water) or cargo_water != 0
            or well.balance < 1):
        raise ValueError("loading needs courier present and exactly one free slot")
    return replace(well, balance=well.balance - 1), 1


def local_delivery(*, courier_location: str, farm_site: str,
                   cargo_water: int, farm_water: int) -> tuple[int, int]:
    if (type(courier_location) is not str or courier_location != farm_site
            or type(farm_site) is not str or not farm_site
            or not _stock(cargo_water) or cargo_water != 1
            or not _stock(farm_water) or farm_water == MAX_STOCK):
        raise ValueError("delivery must reach the real farm with carried water")
    return farm_water + 1, 0


def consume_for_crop(farm_water: int, water_used: int) -> tuple[int, int]:
    if (not _stock(farm_water) or farm_water < 1
            or not _stock(water_used) or water_used == MAX_STOCK):
        raise ValueError("crop requires genuine farm-owned water")
    return farm_water - 1, water_used + 1


def audit_water(well: Well, *, farm_water: int, cargo_water: int,
                water_used: int) -> dict[str, int]:
    """Exactly conserved across the well, farm, courier and actual crop use."""
    if not all(_stock(x) for x in (farm_water, cargo_water, water_used)):
        raise ValueError("uninitialized or negative water is not auditable")
    if cargo_water > 1:
        raise ValueError("one courier cannot carry two water parcels")
    origin = well.initial + well.received_total
    remaining = well.balance + farm_water + cargo_water + water_used
    if origin != remaining:
        raise ValueError("water disappeared or appeared without a recorded cause")
    return {"initial": well.initial, "recorded_rain": well.received_total,
            "well": well.balance, "farm": farm_water,
            "courier": cargo_water, "crops": water_used}
