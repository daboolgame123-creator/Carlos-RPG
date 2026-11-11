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
CASH = "coin_copper"
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
    if (not bootstrap or state["time"] != 0 or event.actor_id is not None
            or set(p) not in ({"courier_id", "stops", "route_ids", "period_seconds"},
                            {"courier_id", "stops", "route_ids", "period_seconds",
                             "farm_bread_share"})):
        raise ValueError("courier circuit is trusted time-zero setup")
    share = p.get("farm_bread_share", False)
    if type(share) is not bool or ("farm_bread_share" in p and share is not True):
        raise ValueError("only explicitly signed real farm grain-for-bread share")
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
    # Water/grain are consignment-only; personally owned food stays personal.
    if (any(stock.get(who, {}).get(item) != 0 for item in ("water", "grain"))
            or not _quantity(stock.get(who, {}).get("food"))):
        raise ValueError("courier requires empty water/grain slots and known owned food")
    # Optional physical copper consignment: declaring a known ZERO coin slot
    # for this particular courier at trusted t=0 configures the return trip.
    # ALL cash depots must be initialized, or the cash contract is rejected.
    # The old, unconfigured courier's record and behavior are identical.
    courier_cash = stock.get(who, {}).get(CASH)
    if courier_cash is not None and (
            not _quantity(courier_cash) or courier_cash != 0
            or any(not _quantity(stock.get(site, {}).get(CASH))
                   for site in (stops[1], "bakery", "market"))):
        raise ValueError("cash return contract needs zero courier cash and known depot balances")
    if share and not _quantity(stock.get(stops[1], {}).get("grain")):
        raise ValueError("real signed grain-share needs initialized actual farm grain")
    # Farm FOOD and courier cash slots can be initialized later inside the
    # SAME trusted time-zero event batch. The new contract creates no bread,
    # and the actual pickup is withheld until the destination FOOD slot exists.
    state["supply_circuits"][who] = {
        "stops": list(stops), "route_ids": list(routes),
        "period_seconds": period, "index": 0, "rounds": 0,
        "next_departure": 0, "carry": None,
        "loads": 0, "deliveries": 0,
        **({"bread_share_earned": 0, "bread_share_delivered": 0} if share else {}),
    }


def _lane(record: Any, *, cash_enabled: bool = False) -> tuple[str, str, str] | None:
    idx = record["index"]
    stops = record["stops"]
    if idx in (0, 1, 2):
        return (stops[idx], stops[idx + 1], RESOURCES[idx])
    if cash_enabled and idx in (3, 4):
        # MARKET RECEIPTS are physically walked back to the bakery, then
        # a surplus coin is carried to the field. One coin is retained at
        # the bakery as its minimal real operating reserve.
        return (stops[idx], stops[idx + 1], CASH)
    return None


def _physically_present(state: dict, who: str) -> bool:
    return not any(x["npc_id"] == who and x["status"] == "traveling"
                   for x in state["travels"].values())


def _local_unpaid_bakery_wage_reserve(state: dict | WorldState) -> int:
    """Protect only REAL finished, unpaid on-site bakery labor when remitting cash.

    This is a local employer obligation, not a remote NPC market oracle.
    No debt and no reservation for jobs that have not actually completed.
    On older no-wage worlds it returns zero: their physical coin-return
    semantics and original one-coin shop reserve remain untouched.
    """
    if isinstance(state, WorldState):
        jobs, recipes = state.production_jobs, state.production_recipes
    else:
        jobs, recipes = state["production_jobs"], state["production_recipes"]
    due = 0
    for job in jobs.values():
        if (job["site_id"] != "bakery" or job["status"] != "completed"
                or "work_wage" in job):
            continue
        wage = recipes[job["recipe_id"]].get("wage_coin")
        if type(wage) is int and wage > 0:
            due += wage
            if due > MAX_STOCK:
                return MAX_STOCK
    return due


def _bakery_cash_remittance_minimum(state: dict | WorldState,
                                    record: dict) -> int:
    """Keep normal 1 bakery operating coin plus any already-earned wages."""
    if record["index"] != 4:
        return 1
    return max(2, 1 + _local_unpaid_bakery_wage_reserve(state))


def _bakery_return_unpromised_food(state: dict | WorldState) -> int:
    """Only locally owned, unquoted, unconsigned bakery loaves are available.

    A farm's signed grain delivery earns a bread claim, NOT an immediate loaf.
    Already advertised customer goods are never repurposed as barter or wages.
    """
    if isinstance(state, WorldState):
        inventory, offers, circuits = (
            state.resources, state.market_offers, state.supply_circuits)
    else:
        inventory, offers, circuits = (
            state["resources"], state["market_offers"], state["supply_circuits"])
    existing = inventory.get("bakery", {}).get("food")
    if not _quantity(existing):
        return -1
    listed = sum(
        row["remaining"] for row in offers.values()
        if row["status"] == "open"
        and row["stock_owner_id"] == "bakery"
        and row["resource"] == "food"
    )
    from .market import reserved_trade_units
    return existing - listed - reserved_trade_units(circuits, "bakery", "food")


def _bakery_has_pending_physical_farm_claim(state: dict | WorldState) -> bool:
    """A bakery-local prepaid farm barter must reserve ONE actual baked loaf.

    The contract is signed at genesis and earned only by real grain delivery.
    This is a baker's local dispatch obligation, not a courier knowing a
    distant farmer's inventory. No obligation means old-world behavior.
    In-flight bread already left bakery stock and needs no second reserve.
    """
    circuits = (state.supply_circuits if isinstance(state, WorldState)
                else state["supply_circuits"])
    return any(
        rec.get("bread_share_earned", 0) > rec.get("bread_share_delivered", 0)
        and not (rec["carry"] is not None
                 and rec["carry"]["resource"] == "food"
                 and rec["carry"]["destination"] == rec["stops"][5])
        for rec in circuits.values()
    )


def _signed_physical_lane(state: dict | WorldState, record: dict, who: str
                          ) -> tuple[str, str, str] | None:
    """Pick exactly ONE real return parcel: owed bread or normal copper.

    Old circuits always return the exact legacy lane. For a specifically
    signed grain-for-one-bread barter, every genuinely delivered farm grain
    earns one owed loaf. The courier can carry one Bakery→Farm food parcel
    on the *existing road* only if bakery has two unpromised finished loaves.
    Cash remittance remains available on the other rounds; no double cargo.
    This is a signed counterfactual, not a globally granted transport right.
    """
    inventory = state.resources if isinstance(state, WorldState) else state["resources"]
    cash_enabled = CASH in inventory.get(who, {})
    old = _lane(record, cash_enabled=cash_enabled)
    # The authenticated farm grain claim is owed by the BAKERY. All the
    # bakery's outgoing MARKET couriers must leave ONE real, unquoted
    # finished loaf on site until a real return trip picks up that wage
    # procurement. Without this local priority, fast market delivery
    # consumes every bread batch before its physical farm return.
    if (record["index"] == 2 and _bakery_has_pending_physical_farm_claim(state)
            and _bakery_return_unpromised_food(state) <= 1):
        return None  # No market pickup may steal the real owed loaf.
    if (record["index"] != 4 or "bread_share_earned" not in record
            or record["bread_share_earned"] <= record["bread_share_delivered"]):
        return old
    if not _quantity(inventory.get(record["stops"][5], {}).get("food")):
        return old  # Farm's durable receiving warehouse must be initialized.
    if _bakery_return_unpromised_food(state) < 1:
        return old  # No bakery-produced unquoted loaf: keep money route.
    # Copper and bread compete for the same physical trip. Alternate whenever
    # both are possible, with the first eligible return paying farm's barter.
    bakery_coins = inventory.get("bakery", {}).get(CASH)
    copper_ready = (
        cash_enabled and _quantity(bakery_coins) and
        bakery_coins >= _bakery_cash_remittance_minimum(state, record)
    )
    if not copper_ready or record["rounds"] % 2 == 0:
        return (record["stops"][4], record["stops"][5], "food")
    return old


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
        lane = _signed_physical_lane(state, record, who)
        if (lane is None or record["carry"] is not None or current != lane[0]
                or p["resource"] != lane[2]):
            raise ValueError("pickup must use the local planned shipping lane")
        src, dest, resource = lane
        from_balance = state["resources"][src][resource]
        to_balance = state["resources"][who][resource]
        if (not _quantity(from_balance) or not _quantity(to_balance)
                or from_balance < (_bakery_cash_remittance_minimum(state, record)
                                   if resource == CASH else 1)
                or to_balance >= MAX_STOCK
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
                or record["index"] not in (1, 2, 3, 4, 5)
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
        # The grain was PHYSICALLY picked at the farm and delivered at the
        # bakery under an explicit time-zero barter. One grain becomes one
        # future bread claim, never an inventory item or immediately a meal.
        if (resource == "grain" and record["index"] == 2
                and "bread_share_earned" in record):
            record["bread_share_earned"] += 1
        if (resource == "food" and record["index"] == 5
                and "bread_share_earned" in record):
            if record["bread_share_delivered"] >= record["bread_share_earned"]:
                raise ValueError("bakery-to-farm bread cannot exceed actual grain barter")
            record["bread_share_delivered"] += 1
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
    lane = _signed_physical_lane(state, record, who)
    if (lane is not None and here == lane[0]
            and _quantity(state.resources.get(here, {}).get(lane[2]))
            and state.resources[here][lane[2]] >= (
                _bakery_cash_remittance_minimum(state, record)
                if lane[2] == CASH else 1
            )):
        return "SupplyCargoPicked"
    return None



def choose_cargo_manifest(state: WorldState, who: str
                          ) -> tuple[str, str] | None:
    """One deterministic single-source cargo action + resource intent.

    The courier policy and its projected reducer MUST agree on resource.
    Never reconstruct a prospective parcel from a fixed leg-index map:
    a signed farm-grain barter may carry actual bread instead of copper
    on bakery→farm, and it may hold back quoted bakery loaves.
    This read-only function neither grants local knowledge nor custody.
    """
    action = choose_cargo(state, who)
    if action is None:
        return None
    rec = state.supply_circuits[who]
    if action == "SupplyCargoDelivered":
        cargo = rec["carry"]
        if cargo is None:
            raise ValueError("delivered cargo manifest missing physical parcel")
        return action, cargo["resource"]
    if action == "SupplyCargoPicked":
        lane = _signed_physical_lane(state, rec, who)
        if lane is None:
            raise ValueError("cargo manifest chose an absent local freight leg")
        return action, lane[2]
    raise ValueError("unrecognized courier cargo manifest action")


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
        base_shape = {"stops", "route_ids", "period_seconds", "index",
                      "rounds", "next_departure", "carry", "loads", "deliveries"}
        share_shape = {"bread_share_earned", "bread_share_delivered"}
        if (who not in state["npcs"] or state["npcs"][who]["role"] != "courier"
                or type(rec) is not dict
                or set(rec) not in (base_shape, base_shape | share_shape)
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
        if "bread_share_earned" in rec:
            if (type(rec["bread_share_earned"]) is not int
                    or type(rec["bread_share_delivered"]) is not int
                    or not 0 <= rec["bread_share_delivered"] <= rec["bread_share_earned"]
                    or rec["bread_share_earned"] > rec["deliveries"]
                    or not _quantity(state["resources"].get(rec["stops"][1], {}).get("grain"))):
                raise ValueError("invalid persisted real farm-bread barter account")
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
            eligible = [
                (rec["stops"][idx], rec["stops"][idx + 1], RESOURCES[idx])
                for idx in range(3)
            ]
            if CASH in state["resources"].get(who, {}):
                eligible.extend(
                    (rec["stops"][idx], rec["stops"][idx + 1], CASH)
                    for idx in (3, 4)
                )
            if "bread_share_earned" in rec:
                eligible.append((rec["stops"][4], rec["stops"][5], "food"))
            if (type(cargo) is not dict
                    or set(cargo) != {"source", "destination", "resource"}
                    or tuple(cargo[k] for k in ("source", "destination", "resource"))
                       not in eligible
                    or not (here == cargo["source"] or here == cargo["destination"])):
                raise ValueError("cargo not physically at its source or destination")
        cash_enabled = CASH in state["resources"].get(who, {})
        if cash_enabled:
            if any(not _quantity(state["resources"].get(site, {}).get(CASH))
                   for site in (rec["stops"][1], "bakery", "market")):
                raise ValueError("optional courier cash contract lost its known depots")
        for item in (*RESOURCES, *((CASH,) if cash_enabled else ())):
            amount = state["resources"].get(who, {}).get(item)
            expected = int(cargo is not None and cargo["resource"] == item)
            if (not _quantity(amount)
                    or (item == "food" and amount < expected)
                    or (item != "food" and amount != expected)):
                raise ValueError("courier inventory and cargo reservations disagree")
        if (rec["rounds"] == 0 and rec["next_departure"] != 0
                or rec["rounds"] > 0 and rec["next_departure"] <= 0):
            raise ValueError("invalid courier period chronology")
