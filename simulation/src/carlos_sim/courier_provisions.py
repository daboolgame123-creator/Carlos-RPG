"""PLAY-48H1 prototype: physically funded in-kind courier wages.

A signed contract reserves EXISTING market food at time zero (no debt).
Each eligible physical food delivery at market earns ONE reserved personal loaf.
The authenticated event log, not a mutable counter supplied by an NPC,
remains the sole source of wage authority.
"""
from __future__ import annotations

from typing import Any

from .domain import DomainEvent, WorldState

MAX_UNIT = 3
MAX_BALANCE = 2**31 - 1


def _id(value: Any) -> bool:
    return (type(value) is str and 0 < len(value) <= 64
            and value.isascii()
            and all(ch.isalnum() or ch in "._-" for ch in value))


def escrow_food_units(state: WorldState | dict[str, Any]) -> int:
    contracts = (state.courier_provisions if isinstance(state, WorldState)
                 else state["courier_provisions"])
    return sum(contract["remaining"] for contract in contracts.values())


def configure_provision(state: dict[str, Any], event: DomainEvent, *,
                        bootstrap: bool) -> None:
    p = event.data
    if (not bootstrap or state["time"] != 0 or event.actor_id is not None
            or set(p) not in (
                {"id", "courier_id", "payer_site", "units"},
                {"id", "courier_id", "payer_site", "units",
                 "authorized_total_units"},
            )
            or not _id(p["id"]) or not _id(p["courier_id"])
            or p["id"] in state["courier_provisions"]
            or any(
                c["courier_id"] == p["courier_id"]
                and not (
                    p["payer_site"] == "market" and p["units"] == 0
                    and c["payer_site"] == "bakery"
                    and c["total_units"] == c["authorized_total_units"] == 1
                    and sum(x["courier_id"] == p["courier_id"]
                            for x in state["courier_provisions"].values()) == 1
                ) for c in state["courier_provisions"].values()
            )
            or p["payer_site"] not in
                ("market", "bakery", state["supply_circuits"].get(
                    p["courier_id"], {}).get("stops", ["", ""])[1])
            or type(p["units"]) is not int
            or not 0 <= p["units"] <= MAX_UNIT
            or (p["units"] == 0 and (
                p["payer_site"] != "market"
                or "authorized_total_units" not in p))):
        raise ValueError("provision requires unique funded time-zero contract")
    # Explicit, owner-authorized future wage ceiling at trusted signing.
    # The default remains exactly the pre-paid opening number, so all
    # historic one-shot contracts CANNOT be secretly renewed at runtime.
    maximum = p.get("authorized_total_units", p["units"])
    if (type(maximum) is not int or not p["units"] <= maximum <= MAX_UNIT
            or (p["units"] == 0 and maximum < 1)
            or (maximum > p["units"] and p["payer_site"] == "bakery")):
        raise ValueError("future payroll needs a signed market or physical farm employer")
    who = p["courier_id"]
    if (who not in state["supply_circuits"]
            or who not in state["npcs"]
            or state["npcs"][who]["role"] != "courier"
            or "market" not in state["market_stalls"]
            or state["supply_circuits"][who]["stops"][3] != "market"
            or (p["payer_site"] == "bakery"
                and state["supply_circuits"][who]["stops"][2] != "bakery")
            or (p["payer_site"] not in ("market", "bakery")
                and p["payer_site"] != state["supply_circuits"][who]["stops"][1])):
        raise ValueError("provision needs an actual named worksite and courier")
    food = state["resources"].get(p["payer_site"], {}).get("food")
    worker_food = state["resources"].get(who, {}).get("food")
    if (type(food) is not int or food < p["units"]
            or type(worker_food) is not int
            or worker_food < 0 or worker_food > MAX_BALANCE):
        raise ValueError("employer cannot reserve absent or unknown real food")
    # An explicitly 0-funded *market-only* time-zero contract is a bounded
    # contingent offer of FUTURE work, not an escrow or owned food. It may
    # be funded ONLY after an independently authenticated real FOOD delivery,
    # sufficient actually held market surplus, and a physically present
    # stall keeper. No initial stock gets removed in that opt-in case.
    # All uncommitted market sales, gathering and cargo routes now see a
    # physically REDUCED market balance. Escrow is in this durable record,
    # still owned by the employer and unavailable for ordinary market sale.
    state["resources"][p["payer_site"]]["food"] -= p["units"]
    state["courier_provisions"][p["id"]] = {
        "courier_id": who, "payer_site": p["payer_site"],
        "total_units": p["units"], "remaining": p["units"],
        "authorized_total_units": maximum,
        "created_at": state["time"], "payments": [],
    }


def choose_courier_provision(state: WorldState, courier_id: str
                             ) -> tuple[str, int] | None:
    circuit = state.supply_circuits.get(courier_id)
    if circuit is None or circuit["carry"] is not None:
        return None
    delivery_count = circuit["deliveries"]
    if delivery_count < 1:
        return None  # Never pay for an empty route or mere hired presence.
    here = state.entities[courier_id]["location_id"]
    for contract_id, contract in sorted(state.courier_provisions.items()):
        site = contract["payer_site"]
        expected_stop = (2 if site == "bakery" else 3 if site == "market"
                         else 1 if site == circuit["stops"][1] else -1)
        if (contract["courier_id"] == courier_id
                and circuit["index"] == expected_stop and here == site
                and contract["remaining"] > 0
                and not any(row["service_deliveries"] == delivery_count
                            for row in contract["payments"])):
            return contract_id, delivery_count
    return None




def _market_uncommitted_bread_after_sales(state: WorldState | dict[str, Any]) -> int:
    """Available market bread excluding physical consignments and OPEN quotes.

    An outstanding open food offer is a real obligation to customers, not
    unclaimed bakery surplus. A courier wage must not cannibalize it.
    """
    if isinstance(state, WorldState):
        goods, offers, circuits = (
            state.resources, state.market_offers, state.supply_circuits)
    else:
        goods, offers, circuits = (
            state["resources"], state["market_offers"], state["supply_circuits"])
    stock = goods.get("market", {}).get("food")
    if type(stock) is not int or stock < 0:
        return -1
    open_promises = sum(
        offer["remaining"] for offer in offers.values()
        if offer["status"] == "open"
        and offer["stock_owner_id"] == "market"
        and offer["site_id"] == "market"
        and offer["resource"] == "food"
    )
    from .market import reserved_trade_units
    return stock - open_promises - reserved_trade_units(
        circuits, "market", "food")


def choose_market_owned_food_refill(state: WorldState, courier_id: str
                                  ) -> tuple[str, int] | None:
    """Existing signed *market* employer may fund one more verified service.

    Returns a pure, local intent only: never reads any distant stock.
    The option is enabled separately by the trusted LivingWorld engine.
    Old one-shot wage contracts remain unchanged with the option off.
    """
    circuit = state.supply_circuits.get(courier_id)
    if circuit is None or circuit["carry"] is not None:
        return None
    if circuit["index"] != 3 or state.entities[courier_id]["location_id"] != "market":
        return None
    if any(trip["npc_id"] == courier_id and trip["status"] == "traveling"
           for trip in state.travels.values()):
        return None
    from .market import _present
    keeper = state.market_stalls.get("market", {}).get("keeper_id")
    if not keeper or not _present(state.to_dict(), keeper, "market"):
        return None
    if _market_uncommitted_bread_after_sales(state) < 2:
        return None  # Protect ALL open customer quotes plus one spare loaf.
    service = circuit["deliveries"]
    for ident, c in sorted(state.courier_provisions.items()):
        if (c["courier_id"] == courier_id and c["payer_site"] == "market"
                and c["remaining"] == 0
                and c["total_units"] < c["authorized_total_units"]
                and service >= 1
                and not any(pay["service_deliveries"] == service
                            for pay in c["payments"])):
            return ident, service
    return None


def replenish_provision_from_delivered_market_food(
    state: dict[str, Any], event: DomainEvent, *,
    supply_authorized: bool,
) -> None:
    """Transfer exactly one real employer-owned market loaf into existing escrow.

    The store separately requires this event to immediately follow the SAME
    atomic command's authenticated food-delivery receipt by this worker.
    The reducer independently checks the physical location, contract, worker
    identity, service count, employer stock and known remaining obligations.
    A second event without another completed delivery must fail closed.
    """
    p = event.data
    if (not supply_authorized or event.actor_id is not None
            or set(p) != {"id", "courier_id", "service_deliveries"}
            or not _id(p.get("id"))
            or type(p.get("service_deliveries")) is not int
            or type(p.get("courier_id")) is not str):
        raise ValueError("market food wage renewal needs trusted exact service receipt")
    contract = state["courier_provisions"].get(p["id"])
    if (contract is None or contract["payer_site"] != "market"
            or contract["courier_id"] != p["courier_id"]
            or contract["remaining"] != 0
            or contract["total_units"] >= contract["authorized_total_units"]):
        raise ValueError("only a spent, pre-signed market wage may be re-funded")
    who = p["courier_id"]
    circuit = state["supply_circuits"].get(who)
    if (circuit is None or circuit["index"] != 3
            or circuit["carry"] is not None
            or circuit["deliveries"] != p["service_deliveries"]
            or circuit["deliveries"] < 1
            or state["entities"][who]["location_id"] != "market"
            or any(row["service_deliveries"] == p["service_deliveries"]
                   for row in contract["payments"])
            or any(t["npc_id"] == who and t["status"] == "traveling"
                   for t in state["travels"].values())
            or any(a["npc_id"] == who and a["status"] == "running"
                   for a in state["actions"].values())
            or any(j["npc_id"] == who and j["status"] == "running"
                   for j in state["production_jobs"].values())):
        raise ValueError("renewal requires local completed, unpaid delivery")
    from .market import _present
    keeper = state["market_stalls"].get("market", {}).get("keeper_id")
    if not keeper or not _present(state, keeper, "market"):
        raise ValueError("market owner is not locally available to fund a wage")
    if _market_uncommitted_bread_after_sales(state) < 2:
        raise ValueError("market wage cannot take listed, reserved, or absent customer food")
    # The signed employer owns these physically produced/transported goods.
    # Decrease site stock BEFORE increasing contractual escrow, atomically.
    state["resources"]["market"]["food"] -= 1
    contract["total_units"] += 1
    contract["remaining"] += 1



def choose_farm_owned_food_refill(state: WorldState, courier_id: str
                                  ) -> tuple[str, int] | None:
    """Pure local intent after an actual bakery->farm FOOD arrival.

    This consumes no remote inventory and never signs a new promise.
    A separate pre-signed ceiling is mandatory, and payment still requires
    a *subsequent* authenticated water delivery at the farm.
    """
    circuit = state.supply_circuits.get(courier_id)
    if (circuit is None or circuit["carry"] is not None
            or circuit["index"] != 5
            or len(circuit["stops"]) < 6
            or circuit["stops"][5] != circuit["stops"][1]):
        return None
    site = circuit["stops"][1]
    if (state.entities[courier_id]["location_id"] != site
            or any(t["npc_id"] == courier_id and t["status"] == "traveling"
                   for t in state.travels.values())
            or type(state.resources.get(site, {}).get("food")) is not int
            or state.resources[site]["food"] < 1):
        return None
    for ident, c in sorted(state.courier_provisions.items()):
        if (c["courier_id"] == courier_id and c["payer_site"] == site
                and c["total_units"] < c["authorized_total_units"]):
            return ident, circuit["deliveries"]
    return None


def replenish_farm_provision_from_returned_bread(
    state: dict[str, Any], event: DomainEvent, *, supply_authorized: bool,
) -> None:
    """Escrow ONE farm-owned loaf after the immediately prior physical return.

    Store validates event adjacency to a real FOOD delivery in the same
    atomic trusted command. Reducer independently checks the real endpoint,
    signed ceiling, worker, stock and physical custody.
    """
    p = event.data
    if (not supply_authorized or event.actor_id is not None
            or set(p) != {"id", "courier_id", "service_deliveries"}
            or not _id(p.get("id")) or not _id(p.get("courier_id"))
            or type(p.get("service_deliveries")) is not int):
        raise ValueError("farm food wage renewal requires trusted physical receipt")
    contract = state["courier_provisions"].get(p["id"])
    who = p["courier_id"]
    circuit = state["supply_circuits"].get(who)
    if (contract is None or circuit is None
            or contract["courier_id"] != who
            or contract["payer_site"] != circuit["stops"][1]
            or circuit["index"] != 5 or len(circuit["stops"]) < 6
            or circuit["stops"][5] != circuit["stops"][1]
            or circuit["carry"] is not None
            or circuit["deliveries"] != p["service_deliveries"]
            or circuit["deliveries"] < 1
            or contract["total_units"] >= contract["authorized_total_units"]):
        raise ValueError("farm wage renewal needs a genuine signed return")
    site = contract["payer_site"]
    if (state["entities"][who]["location_id"] != site
            or any(t["npc_id"] == who and t["status"] == "traveling"
                   for t in state["travels"].values())
            or any(a["npc_id"] == who and a["status"] == "running"
                   for a in state["actions"].values())
            or any(j["npc_id"] == who and j["status"] == "running"
                   for j in state["production_jobs"].values())):
        raise ValueError("farm wage funding requires worker actually present")
    stock = state["resources"].get(site, {}).get("food")
    if type(stock) is not int or stock < 1:
        raise ValueError("farm cannot escrow absent, unowned bread")
    state["resources"][site]["food"] -= 1
    contract["total_units"] += 1
    contract["remaining"] += 1


def pay_courier_provision(state: dict[str, Any], event: DomainEvent, *,
                          supply_authorized: bool) -> None:
    p = event.data
    fields = set(p)
    if (not supply_authorized or event.actor_id is not None
            or fields not in ({"id", "courier_id", "service_deliveries"},
                              {"id", "courier_id", "service_deliveries", "proof"})
            or (fields == {"id", "courier_id", "service_deliveries", "proof"}
                and p["proof"] not in ("prior_market_service",
                                       "bakery_grain_delivery",
                                       "farm_water_delivery"))
            or not _id(p["id"])
            or type(p["service_deliveries"]) is not int):
        raise ValueError("courier food wage needs trusted physical-service proof")
    contract = state["courier_provisions"].get(p["id"])
    if contract is None or contract["remaining"] < 1:
        raise ValueError("courier wage requires real escrowed employer food")
    who = contract["courier_id"]
    if p["courier_id"] != who:
        raise ValueError("wage contract worker identity does not match")
    circuit = state["supply_circuits"][who]
    site = contract["payer_site"]
    service = p["service_deliveries"]
    expected_stop = (2 if site == "bakery" else 3 if site == "market"
                     else 1 if site == circuit["stops"][1] else -1)
    proof = p.get("proof")
    if ((site == "bakery" and proof != "bakery_grain_delivery")
            or (site not in ("bakery", "market")
                and proof != "farm_water_delivery")
            or (site == "market" and proof in
                ("bakery_grain_delivery", "farm_water_delivery"))
            or service < 1 or circuit["deliveries"] != service
            or circuit["index"] != expected_stop or circuit["carry"] is not None
            or state["entities"][who]["location_id"] != site
            or any(t["npc_id"] == who and t["status"] == "traveling"
                   for t in state["travels"].values())
            or any(a["npc_id"] == who and a["status"] == "running"
                   for a in state["actions"].values())
            or any(job["npc_id"] == who and job["status"] == "running"
                   for job in state["production_jobs"].values())
            or any(row["service_deliveries"] == service
                   for row in contract["payments"])):
        raise ValueError("wage cannot be paid without completed service at the actual hiring market")
    food = state["resources"].get(who, {}).get("food")
    if type(food) is not int or food < 0 or food >= MAX_BALANCE:
        raise ValueError("worker must have bounded initialized personal food")
    # Site food was reserved and subtracted at contract time; a payment may
    # move ONLY that escrow unit into the legitimate worker's personal stock.
    contract["remaining"] -= 1
    state["resources"][who]["food"] = food + 1
    contract["payments"].append({
        "service_deliveries": service,
        "paid_at": state["time"],
        "worker_food_before": food,
        "worker_food_after": food + 1,
    })


def validate_courier_provisions(state: dict[str, Any]) -> None:
    contracts = state["courier_provisions"]
    if type(contracts) is not dict:
        raise ValueError("invalid courier wage contracts")
    pairs: set[tuple[str, str]] = set()
    employers: dict[str, dict[str, dict[str, Any]]] = {}
    for ident, c in contracts.items():
        if (not _id(ident) or type(c) is not dict
                or set(c) != {"courier_id", "payer_site", "total_units",
                              "remaining", "authorized_total_units",
                              "created_at", "payments"}
                or c["payer_site"] not in (
                    "market", "bakery",
                    state["supply_circuits"].get(c["courier_id"], {})
                        .get("stops", ["", ""])[1])
                or "market" not in state["market_stalls"]
                or (c["payer_site"] == "bakery" and
                    state["supply_circuits"][c["courier_id"]]["stops"][2] != "bakery")
                or c["courier_id"] not in state["supply_circuits"]
                or (c["courier_id"], c["payer_site"]) in pairs
                or state["npcs"][c["courier_id"]]["role"] != "courier"
                or type(c["total_units"]) is not int
                or not 0 <= c["total_units"] <= MAX_UNIT
                or (c["total_units"] == 0
                    and (c["payer_site"] != "market"
                         or c["authorized_total_units"] < 1
                         or c["remaining"] != 0 or c["payments"]))
                or type(c["authorized_total_units"]) is not int
                or not c["total_units"] <= c["authorized_total_units"] <= MAX_UNIT
                or (c["authorized_total_units"] > c["total_units"]
                    and c["payer_site"] == "bakery")
                or type(c["remaining"]) is not int
                or not 0 <= c["remaining"] <= c["total_units"]
                or c["created_at"] != 0
                or type(c["payments"]) is not list
                or len(c["payments"]) != c["total_units"] - c["remaining"]):
            raise ValueError("invalid funded service contract ledger")
        pairs.add((c["courier_id"], c["payer_site"]))
        employers.setdefault(c["courier_id"], {})[c["payer_site"]] = c
        seen: set[int] = set()
        for row in c["payments"]:
            if (type(row) is not dict
                    or set(row) != {"service_deliveries", "paid_at",
                                   "worker_food_before", "worker_food_after"}
                    or type(row["service_deliveries"]) is not int
                    or not 1 <= row["service_deliveries"] <=
                           state["supply_circuits"][c["courier_id"]]["deliveries"]
                    or row["service_deliveries"] in seen
                    or type(row["paid_at"]) is not int
                    or not 0 <= row["paid_at"] <= state["time"]
                    or type(row["worker_food_before"]) is not int
                    or not 0 <= row["worker_food_before"] < MAX_BALANCE
                    or row["worker_food_after"] != row["worker_food_before"] + 1):
                raise ValueError("invalid unique courier wage receipt")
            seen.add(row["service_deliveries"])
    # EXPERIMENT ONLY: signed independent bakery GRAIN and market FOOD
    # services. Same employer cannot pay twice for two duplicate contracts.
    # Legacy single-employer histories still validate without changes.
    # Release requires RulesVersion migration and independent replay review.
    for who, sites in employers.items():
        if len(sites) > 1 and (
                len(sites) != 2 or set(sites) != {"bakery", "market"}
                or sites["bakery"]["total_units"] != 1
                or sites["bakery"]["authorized_total_units"] != 1
                or sites["market"]["authorized_total_units"] < 1):
            raise ValueError("secondary wage needs distinct signed real services")

