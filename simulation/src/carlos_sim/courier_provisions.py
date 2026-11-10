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
            or set(p) != {"id", "courier_id", "payer_site", "units"}
            or not _id(p["id"]) or not _id(p["courier_id"])
            or p["id"] in state["courier_provisions"]
            or any(c["courier_id"] == p["courier_id"]
                   for c in state["courier_provisions"].values())
            or p["payer_site"] not in ("market", "bakery")
            or type(p["units"]) is not int
            or not 1 <= p["units"] <= MAX_UNIT):
        raise ValueError("provision requires unique funded time-zero contract")
    who = p["courier_id"]
    if (who not in state["supply_circuits"]
            or who not in state["npcs"]
            or state["npcs"][who]["role"] != "courier"
            or "market" not in state["market_stalls"]
            or state["supply_circuits"][who]["stops"][3] != "market"
            or (p["payer_site"] == "bakery"
                and state["supply_circuits"][who]["stops"][2] != "bakery")):
        raise ValueError("provision needs an actual named worksite and courier")
    food = state["resources"].get(p["payer_site"], {}).get("food")
    worker_food = state["resources"].get(who, {}).get("food")
    if (type(food) is not int or food < p["units"]
            or type(worker_food) is not int
            or worker_food < 0 or worker_food > MAX_BALANCE):
        raise ValueError("employer cannot reserve absent or unknown real food")
    # All uncommitted market sales, gathering and cargo routes now see a
    # physically REDUCED market balance. Escrow is in this durable record,
    # still owned by the employer and unavailable for ordinary market sale.
    state["resources"][p["payer_site"]]["food"] -= p["units"]
    state["courier_provisions"][p["id"]] = {
        "courier_id": who, "payer_site": p["payer_site"],
        "total_units": p["units"], "remaining": p["units"],
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
        expected_stop = 2 if site == "bakery" else 3
        if (contract["courier_id"] == courier_id
                and circuit["index"] == expected_stop and here == site
                and contract["remaining"] > 0
                and not any(row["service_deliveries"] == delivery_count
                            for row in contract["payments"])):
            return contract_id, delivery_count
    return None


def pay_courier_provision(state: dict[str, Any], event: DomainEvent, *,
                          supply_authorized: bool) -> None:
    p = event.data
    fields = set(p)
    if (not supply_authorized or event.actor_id is not None
            or fields not in ({"id", "courier_id", "service_deliveries"},
                              {"id", "courier_id", "service_deliveries", "proof"})
            or (fields == {"id", "courier_id", "service_deliveries", "proof"}
                and p["proof"] not in ("prior_market_service",
                                       "bakery_grain_delivery"))
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
    expected_stop = 2 if site == "bakery" else 3
    proof = p.get("proof")
    if ((site == "bakery" and proof != "bakery_grain_delivery")
            or (site == "market" and proof == "bakery_grain_delivery")
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
    worker_ids: set[str] = set()
    for ident, c in contracts.items():
        if (not _id(ident) or type(c) is not dict
                or set(c) != {"courier_id", "payer_site", "total_units",
                              "remaining", "created_at", "payments"}
                or c["payer_site"] not in ("market", "bakery")
                or "market" not in state["market_stalls"]
                or (c["payer_site"] == "bakery" and
                    state["supply_circuits"][c["courier_id"]]["stops"][2] != "bakery")
                or c["courier_id"] not in state["supply_circuits"]
                or c["courier_id"] in worker_ids
                or state["npcs"][c["courier_id"]]["role"] != "courier"
                or type(c["total_units"]) is not int
                or not 1 <= c["total_units"] <= MAX_UNIT
                or type(c["remaining"]) is not int
                or not 0 <= c["remaining"] <= c["total_units"]
                or c["created_at"] != 0
                or type(c["payments"]) is not list
                or len(c["payments"]) != c["total_units"] - c["remaining"]):
            raise ValueError("invalid funded service contract ledger")
        worker_ids.add(c["courier_id"])
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
