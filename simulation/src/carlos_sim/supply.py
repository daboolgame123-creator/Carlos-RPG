"""PLAY-27 — audited site-to-site logistics, with real courier travel.

No remote inventory checks: a courier inspects only its current stop. The
professional circuit is trusted time-zero configuration, not private NPC
omniscience. All inventory follows site -> courier -> adjacent site through
separate atomic events; only the existing real scheduled travel moves Huda.
"""
from __future__ import annotations

from typing import Any
from .domain import DomainEvent, WorldState
from .navigation import needs_survey
from .npc import _injury_rest_decision

MAX_STOCK = 2**31 - 1
RESOURCES = ("water", "grain", "food")
CART_CAPACITIES = frozenset((2, 3))  # A real initialized cart is required.
STOPS = ("well", "farm", "bakery", "market", "bakery", "farm", "well")


def _validated_stops(stops: Any) -> bool:
    """One real field per circuit; every other stop retains canonical roles.

    Farm identity is a *persisted local route choice*, not remote stock access.
    The original seven-stop circuit remains valid byte-for-byte.
    """
    return (type(stops) in (tuple, list) and len(stops) == 7
            and all(type(site) is str and site for site in stops)
            and stops[0] == stops[6] == "well"
            and stops[2] == stops[4] == "bakery"
            and stops[3] == "market"
            and stops[1] == stops[5]
            and stops[1] not in ("well", "bakery", "market"))


def _quantity(v: Any) -> bool:
    return type(v) is int and 0 <= v <= MAX_STOCK


def configure_circuit(state: dict, event: DomainEvent, *, bootstrap: bool) -> None:
    p = event.data
    old_keys = {"courier_id", "stops", "route_ids", "period_seconds"}
    cart_mode = set(p) == old_keys | {"cargo_capacity"}
    if (not bootstrap or state["time"] != 0 or event.actor_id is not None
            or (set(p) != old_keys and not cart_mode)):
        raise ValueError("courier circuit is trusted time-zero setup")
    capacity = p["cargo_capacity"] if cart_mode else 1
    if cart_mode and (type(capacity) is not int or capacity not in CART_CAPACITIES):
        raise ValueError("cart capacity must be 2 or 3 known physical units")
    who, stops, routes, period = (p["courier_id"], p["stops"],
                                p["route_ids"], p["period_seconds"])
    if (type(who) is not str or who not in state["npcs"]
            or state["npcs"][who]["role"] != "courier"
            or who in state["supply_circuits"]
            or not _validated_stops(stops)
            or not isinstance(routes, (list, tuple)) or len(routes) != len(stops) - 1
            or any(type(r) is not str for r in routes)
            or type(period) is not int or not 1800 <= period <= 86400
            or state["entities"][who]["location_id"] != stops[0]):
        raise ValueError("invalid physical courier plan or identity")
    for idx, rid in enumerate(routes):
        road = state["routes"].get(rid)
        if (road is None or {road["a"], road["b"]} != {stops[idx], stops[idx+1]}
                or type(road["seconds"]) is not int or road["seconds"] <= 0):
            raise ValueError("courier legs must be real neighboring routes")
    if sum(state["routes"][r]["seconds"] for r in routes) >= period:
        raise ValueError("one courier tour must fit inside its real interval")
    stock = state["resources"]
    if any(site not in state["locations"] for site in stops):
        raise ValueError("courier logistics location unknown")
    for source, destination, resource in (
        (stops[0], stops[1], "water"),
        (stops[1], stops[2], "grain"),
        (stops[2], stops[3], "food"),
    ):
        if not (_quantity(stock.get(source, {}).get(resource))
                and _quantity(stock.get(destination, {}).get(resource))):
            raise ValueError("every logistics stock must have a known balance")
    # Water/grain are strictly consignment-only. Existing, initialized food
    # belongs to the courier until a food parcel is explicitly reserved.
    if (any(stock.get(who, {}).get(item) != 0 for item in ("water", "grain"))
            or not _quantity(stock.get(who, {}).get("food"))
            or (cart_mode and stock.get(who, {}).get("cart") != 1)):

        raise ValueError("courier requires empty water/grain slots and known owned food")
    state["supply_circuits"][who] = {
        "stops": list(stops), "route_ids": list(routes),
        "period_seconds": period, "index": 0, "rounds": 0,
        "next_departure": 0, "carry": None,
        "loads": 0, "deliveries": 0,
        **({"cargo_capacity": capacity} if cart_mode else {}),
    }


def _lane(record: Any) -> tuple[str, str, str] | None:
    idx = record["index"]
    if idx not in (0, 1, 2):
        return None
    stops = record["stops"]
    return (stops[idx], stops[idx + 1], RESOURCES[idx])


def _physically_present(state: dict, who: str) -> bool:
    return not any(x["npc_id"] == who and x["status"] == "traveling"
                   for x in state["travels"].values())


def project_cargo(state: dict, event: DomainEvent, *, supply_authorized: bool) -> None:
    p = event.data
    if (not supply_authorized or set(p) != {"courier_id", "resource"}
            or type(p["courier_id"]) is not str or event.actor_id != p["courier_id"]):
        raise ValueError("cargo changes need an authorized physical courier")
    who = p["courier_id"]
    record = state["supply_circuits"].get(who)
    if (record is None or not _physically_present(state, who)
            or any(a["npc_id"] == who and a["status"] == "running"
                   for a in state["actions"].values())
            or any(j["npc_id"] == who and j["status"] == "running"
                   for j in state["production_jobs"].values())):
        raise ValueError("cargo cannot move without a configured, idle and present courier")
    current = state["entities"][who]["location_id"]
    if event.event_type == "SupplyCargoPicked":
        npc = state["npcs"][who]
        if (npc["needs"]["hunger"] >= 90 or npc["needs"]["fatigue"] >= 70
                or npc["needs"]["safety"] >= 75
                or _injury_rest_decision(state["injuries"], who) is not None):
            raise ValueError("exhausted or unsafe courier cannot reserve new cargo")
        lane = _lane(record)
        if (lane is None or record["carry"] is not None or current != lane[0]
                or p["resource"] != lane[2]):
            raise ValueError("pickup must use the local planned shipping lane")
        src, dest, resource = lane
        from_balance = state["resources"][src][resource]
        to_balance = state["resources"][who][resource]
        if (not _quantity(from_balance) or not _quantity(to_balance)
                or from_balance < 1 or to_balance >= MAX_STOCK
                or (resource != "food" and to_balance != 0)):
            raise ValueError("courier cannot mint or double-load local cargo")
        state["resources"][src][resource] -= 1
        state["resources"][who][resource] += 1
        record["carry"] = {"source": src, "destination": dest, "resource": resource}
        record["loads"] += 1
    elif event.event_type == "SupplyCargoDelivered":
        cargo = record["carry"]
        if (cargo is None or current != cargo["destination"]
                or p["resource"] != cargo["resource"]
                or record["index"] not in (1, 2, 3)
                or record["stops"][record["index"] - 1] != cargo["source"]):
            raise ValueError("delivery requires recorded real one-leg arrival")
        resource = cargo["resource"]
        amount = state["resources"][who][resource]
        dest = state["resources"][current][resource]
        if (not _quantity(amount) or amount < 1
                or (resource != "food" and amount != 1)
                or not _quantity(dest) or dest >= MAX_STOCK):
            raise ValueError("delivery requires one reserved carried unit")
        state["resources"][who][resource] -= 1
        state["resources"][current][resource] += 1
        record["carry"] = None
        record["deliveries"] += 1
    else:
        raise ValueError("unrecognized supply cargo event")


def check_leg(state: dict, who: str, route_id: str,
              origin: str, destination: str) -> None:
    record = state["supply_circuits"].get(who)
    if record is None:
        return
    npc = state["npcs"][who]
    if (npc["needs"]["hunger"] >= 90 or npc["needs"]["fatigue"] >= 70
            or npc["needs"]["safety"] >= 75
            or _injury_rest_decision(state["injuries"], who) is not None):
        raise ValueError("exhausted or unsafe courier cannot begin a contracted leg")
    idx = record["index"]
    if (idx >= len(record["route_ids"]) or origin != record["stops"][idx]
            or destination != record["stops"][idx+1]
            or route_id != record["route_ids"][idx]
            or (idx == 0 and state["time"] < record["next_departure"])):
        raise ValueError("courier cannot skip a professional physical stop")


def complete_courier_leg(state: dict, who: str, route_id: str,
                         destination: str, now: int) -> None:
    record = state["supply_circuits"].get(who)
    if record is None:
        return
    idx = record["index"]
    if (idx >= len(record["route_ids"])
            or route_id != record["route_ids"][idx]
            or destination != record["stops"][idx+1]):
        raise ValueError("courier arrival differs from the contracted route")
    record["index"] += 1
    if record["index"] == len(record["route_ids"]):
        if record["carry"] is not None:
            raise ValueError("courier cannot finish a circuit with undelivered cargo")
        record["index"] = 0
        record["rounds"] += 1
        record["next_departure"] = ((now // record["period_seconds"]) + 1) * record["period_seconds"]


def choose_cargo(state: WorldState, who: str) -> str | None:
    record = state.supply_circuits.get(who)
    if record is None or _traveling(state, who):
        return None
    here = state.entities[who]["location_id"]
    cargo = record["carry"]
    if cargo is not None:
        return ("SupplyCargoDelivered"
                if here == cargo["destination"] else None)
    # A courier too hungry or exhausted to walk must not reserve a new
    # parcel and block the well or bakery indefinitely.
    npc = state.npcs[who]
    if (npc["needs"]["hunger"] >= 90 or npc["needs"]["fatigue"] >= 70
            or npc["needs"]["safety"] >= 75
            or _injury_rest_decision(state.injuries, who) is not None):
        return None
    lane = _lane(record)
    if (lane is not None and here == lane[0]
            and _quantity(state.resources.get(here, {}).get(lane[2]))
            and state.resources[here][lane[2]] > 0):
        return "SupplyCargoPicked"
    return None


def _traveling(state: WorldState, who: str) -> bool:
    return (any(t["npc_id"] == who and t["status"] == "traveling"
                for t in state.travels.values())
            or any(a["npc_id"] == who and a["status"] == "running"
                   for a in state.actions.values())
            or any(j["npc_id"] == who and j["status"] == "running"
                   for j in state.production_jobs.values()))


def choose_courier_leg(state: WorldState, who: str) -> tuple[str, str, str, int] | None:
    rec = state.supply_circuits.get(who)
    if rec is None or _traveling(state, who):
        return None
    npc = state.npcs[who]
    if (npc["needs"]["hunger"] >= 90 or npc["needs"]["fatigue"] >= 70
            or npc["needs"]["safety"] >= 75
            or _injury_rest_decision(state.injuries, who) is not None):
        return None
    idx = rec["index"]
    if idx == 0 and state.time < rec["next_departure"]:
        return None
    here = state.entities[who]["location_id"]
    if here != rec["stops"][idx]:
        return None
    rid = rec["route_ids"][idx]
    if state.navigation.get(who) is not None and rid not in state.navigation[who]["known_routes"]:
        return None
    destination = rec["stops"][idx+1]
    return rid, here, destination, state.time + state.routes[rid]["seconds"]


def next_courier_departure(state: WorldState) -> int | None:
    possible = []
    for who, rec in state.supply_circuits.items():
        if (rec["index"] == 0 and rec["next_departure"] > state.time
                and not _traveling(state, who)):
            possible.append(rec["next_departure"])
    return min(possible) if possible else None


def validate_supply_circuits(state: dict) -> None:
    circuits = state["supply_circuits"]
    if type(circuits) is not dict:
        raise ValueError("invalid courier contracts")
    for who, rec in circuits.items():
        if (who not in state["npcs"] or state["npcs"][who]["role"] != "courier"
                or type(rec) is not dict
                or set(rec) != {"stops", "route_ids", "period_seconds", "index",
                               "rounds", "next_departure", "carry", "loads", "deliveries"}
                or not _validated_stops(rec["stops"])
                or type(rec["route_ids"]) is not list or len(rec["route_ids"]) != 6
                or type(rec["period_seconds"]) is not int
                or not 1800 <= rec["period_seconds"] <= 86400
                or type(rec["index"]) is not int or not 0 <= rec["index"] <= 5
                or any(type(rec[k]) is not int or rec[k] < 0
                       for k in ("rounds", "next_departure", "loads", "deliveries"))
                or rec["loads"] < rec["deliveries"]
                or rec["loads"] - rec["deliveries"] != int(rec["carry"] is not None)):
            raise ValueError("invalid durable courier logistics state")
        for idx, rid in enumerate(rec["route_ids"]):
            route = state["routes"].get(rid)
            if route is None or {route["a"], route["b"]} != {rec["stops"][idx], rec["stops"][idx+1]}:
                raise ValueError("courier has nonphysical or changed route")
        if sum(state["routes"][rid]["seconds"] for rid in rec["route_ids"]) >= rec["period_seconds"]:
            raise ValueError("courier tour exceeds its finite period")
        here = state["entities"][who]["location_id"]
        if here != rec["stops"][rec["index"]]:
            raise ValueError("courier stage not aligned with physical position")
        cargo = rec["carry"]
        if cargo is not None:
            if (type(cargo) is not dict
                    or set(cargo) != {"source", "destination", "resource"}
                    or tuple(cargo[k] for k in ("source", "destination", "resource"))
                       not in ((rec["stops"][0], rec["stops"][1], "water"),
                               (rec["stops"][1], rec["stops"][2], "grain"),
                               (rec["stops"][2], rec["stops"][3], "food"))
                    or not (here == cargo["source"] or here == cargo["destination"])):
                raise ValueError("cargo not physically at its source or destination")
        for item in RESOURCES:
            amount = state["resources"].get(who, {}).get(item)
            expected = int(cargo is not None and cargo["resource"] == item)
            if (not _quantity(amount)
                    or (item == "food" and amount < expected)
                    or (item != "food" and amount != expected)):
                raise ValueError("courier inventory and cargo reservations disagree")
        if (rec["rounds"] == 0 and rec["next_departure"] != 0
                or rec["rounds"] > 0 and rec["next_departure"] <= 0):
            raise ValueError("invalid courier period chronology")
