"""Prospective recurring freight wages backed by physical delivery receipts.

Old finite courier provisions keep their lifetime limits. This distinct contract
earns at most one unpaid loaf, no more often than its signed interval, at the
actual receiving employer. A receipt is recorded by the cargo reducer, never
accepted from a caller. Settlement needs local uncommitted employer stock.
"""
from __future__ import annotations

from .domain import DomainEvent, WorldState
from .food_for_work import _available_site_food, _worker_present_and_free

MAX_BALANCE = 2**31 - 1


def sign_contract(state: dict, event: DomainEvent, *, bootstrap: bool) -> None:
    p = event.data
    if (not bootstrap or state["time"] != 0 or event.actor_id is not None
            or set(p) != {"courier_id", "site_id", "resource", "interval_seconds"}
            or type(p["courier_id"]) is not str
            or type(p["interval_seconds"]) is not int
            or not 12 * 3600 <= p["interval_seconds"] <= 48 * 3600):
        raise ValueError("recurring freight wage requires signed time-zero terms")
    who = p["courier_id"]
    circuit = state["supply_circuits"].get(who)
    if (circuit is None or "food_payroll" in circuit
            or (p["site_id"], p["resource"]) not in
                (("bakery", "grain"), ("market", "food"))
            or any(c["courier_id"] == who for c in state["courier_provisions"].values())
            or type(state["resources"].get(p["site_id"], {}).get("food")) is not int):
        raise ValueError("one genuine receiving employer; no overlapping provision")
    circuit["food_payroll"] = {"site_id": p["site_id"], "resource": p["resource"],
                               "interval_seconds": p["interval_seconds"], "receipts": []}


def record_delivery(state: dict, who: str, resource: str) -> None:
    """Called only after the authoritative cargo debit/delivery has succeeded."""
    circuit = state["supply_circuits"][who]
    contract = circuit.get("food_payroll")
    if contract is None:
        return
    if (resource != contract["resource"]
            or state["entities"][who]["location_id"] != contract["site_id"]):
        return
    receipts = contract["receipts"]
    if receipts and (receipts[-1]["payment"] is None or
                    state["time"] - receipts[-1]["delivered_at"] < contract["interval_seconds"]):
        return
    receipts.append({"delivery": circuit["deliveries"],
                     "delivered_at": state["time"], "payment": None})


def _eligible(state: dict, who: str) -> dict | None:
    circuit = state["supply_circuits"].get(who)
    contract = circuit.get("food_payroll") if circuit else None
    if contract is None or not contract["receipts"]:
        return None
    receipt = contract["receipts"][-1]
    site = contract["site_id"]
    food = state["resources"].get(who, {}).get("food")
    if (receipt["payment"] is not None
            or not _worker_present_and_free(state, who, site)
            or _available_site_food(state, site) < 1
            or type(food) is not int or not 0 <= food < MAX_BALANCE):
        return None
    return receipt


def choose_payment(state: WorldState, who: str) -> int | None:
    receipt = _eligible(state.to_dict(), who)
    return receipt["delivery"] if receipt else None


def waits_for_local_payment(state: WorldState, who: str) -> bool:
    circuit = state.supply_circuits.get(who)
    contract = circuit.get("food_payroll") if circuit else None
    if contract is None or not contract["receipts"] or circuit["carry"] is not None:
        return False
    receipt = contract["receipts"][-1]
    needs = state.npcs[who]["needs"]
    from .npc import _injury_rest_decision
    return (contract["site_id"] == "bakery" and receipt["payment"] is None
            and 0 <= state.time - receipt["delivered_at"] < 3600
            and _worker_present_and_free(state, who, "bakery")
            and needs["hunger"] < 90 and needs["fatigue"] < 70
            and needs["safety"] < 75
            and _injury_rest_decision(state.injuries, who) is None)


def next_wait_boundary(state: WorldState, who: str) -> int | None:
    """Wake on the same physiological/expiry boundary in any time partition."""
    if not waits_for_local_payment(state, who):
        return None
    from .survival import FATIGUE_SECONDS_PER_POINT, HUNGER_SECONDS_PER_POINT
    from .consumption import AUTONOMOUS_EATING_THRESHOLD, _reserved_food
    needs = state.npcs[who]['needs']
    progress = state.survival_progress.get(who, {})
    contract = state.supply_circuits[who]['food_payroll']
    expiry = contract['receipts'][-1]['delivered_at'] + 3600
    hunger_boundary = 90
    if (needs['hunger'] < AUTONOMOUS_EATING_THRESHOLD
            and state.resources[who]['food'] > _reserved_food(state.supply_circuits, who)):
        hunger_boundary = AUTONOMOUS_EATING_THRESHOLD
    period = state.metabolism_policy.get('hunger_seconds_per_point', HUNGER_SECONDS_PER_POINT)
    return min(expiry,
               state.time + (70 - needs['fatigue']) * FATIGUE_SECONDS_PER_POINT
               - progress.get('fatigue_seconds', 0),
               state.time + (hunger_boundary - needs['hunger']) * period
               - progress.get('hunger_seconds', 0))


def pay_wage(state: dict, event: DomainEvent, *, supply_authorized: bool) -> None:
    p = event.data
    if (not supply_authorized or event.actor_id is not None
            or set(p) != {"courier_id", "delivery"}
            or type(p["courier_id"]) is not str or type(p["delivery"]) is not int):
        raise ValueError("freight wage needs authorized exact delivery evidence")
    who = p["courier_id"]
    receipt = _eligible(state, who)
    if receipt is None or receipt["delivery"] != p["delivery"]:
        raise ValueError("unearned, duplicate, unavailable or unfunded freight wage")
    site = state["supply_circuits"][who]["food_payroll"]["site_id"]
    source = state["resources"][site]["food"]
    target = state["resources"][who]["food"]
    state["resources"][site]["food"] -= 1
    state["resources"][who]["food"] += 1
    receipt["payment"] = {"paid_at": state["time"], "source_before": source,
                           "source_after": source - 1, "worker_before": target,
                           "worker_after": target + 1}


def validate_contract(state: dict, who: str, circuit: dict) -> None:
    c = circuit.get("food_payroll")
    if c is None:
        return
    if (type(c) is not dict or set(c) !=
            {"site_id", "resource", "interval_seconds", "receipts"}
            or (c["site_id"], c["resource"]) not in (("bakery", "grain"), ("market", "food"))
            or type(c["interval_seconds"]) is not int
            or not 12 * 3600 <= c["interval_seconds"] <= 48 * 3600
            or type(c["receipts"]) is not list
            or any(x["courier_id"] == who for x in state["courier_provisions"].values())):
        raise ValueError("invalid recurring freight contract")
    last_time, last_delivery, unpaid = -c["interval_seconds"], 0, False
    for r in c["receipts"]:
        if (type(r) is not dict or set(r) != {"delivery", "delivered_at", "payment"}
                or type(r["delivery"]) is not int or not last_delivery < r["delivery"] <= circuit["deliveries"]
                or type(r["delivered_at"]) is not int
                or not 0 <= r["delivered_at"] <= state["time"]
                or r["delivered_at"] - last_time < c["interval_seconds"] or unpaid):
            raise ValueError("invalid or duplicate physical service evidence")
        q = r["payment"]
        if q is not None:
            if (type(q) is not dict or set(q) != {"paid_at", "source_before", "source_after", "worker_before", "worker_after"}
                    or any(type(v) is not int or v < 0 for v in q.values())
                    or not r["delivered_at"] <= q["paid_at"] <= state["time"]
                    or any(q[k] > MAX_BALANCE for k in q if k != "paid_at")
                    or q["source_before"] - q["source_after"] != 1
                    or q["worker_after"] - q["worker_before"] != 1):
                raise ValueError("freight payment must conserve actual food")
        last_time, last_delivery, unpaid = r["delivered_at"], r["delivery"], q is None
