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
    contract = state.supply_circuits[who]['food_payroll']
    return _next_need_boundary(state, who,
                               contract['receipts'][-1]['delivered_at'] + 3600, 90)


def waits_for_departure(state: WorldState, who: str) -> bool:
    """Only a free, safe courier at the scheduled circuit origin can idle."""
    circuit = state.supply_circuits.get(who)
    if (circuit is None or circuit['index'] != 0 or circuit['carry'] is not None
            or circuit['next_departure'] <= state.time
            or not _worker_present_and_free(state, who, circuit['stops'][0])):
        return False
    from .npc import _injury_rest_decision
    needs = state.npcs[who]['needs']
    return (needs['hunger'] < 75 and needs['fatigue'] < 70 and needs['safety'] < 75
            and _injury_rest_decision(state.injuries, who) is None)


def next_departure_wait_boundary(state: WorldState, who: str) -> int | None:
    if not waits_for_departure(state, who):
        return None
    return _next_need_boundary(state, who,
                               state.supply_circuits[who]['next_departure'], 75)


def _next_need_boundary(state: WorldState, who: str, expiry: int,
                        hunger_boundary: int) -> int:
    from .survival import FATIGUE_SECONDS_PER_POINT, HUNGER_SECONDS_PER_POINT
    from .consumption import AUTONOMOUS_EATING_THRESHOLD, _reserved_food
    needs = state.npcs[who]['needs']
    progress = state.survival_progress.get(who, {})
    if state.resources[who]['food'] > _reserved_food(state.supply_circuits, who):
        if needs['hunger'] >= AUTONOMOUS_EATING_THRESHOLD:
            # The consumption pass already ran. A same-tick meal/decision
            # can defer another owned loaf, but not until the caller's next
            # arbitrary advance boundary. The next logical tick is eligible.
            return state.time + 1
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
    if (type(c) is not dict or set(c) not in (
            {"site_id", "resource", "interval_seconds", "receipts"},
            {"site_id", "resource", "interval_seconds", "receipts", "signed_at"},
            {"site_id", "resource", "interval_seconds", "receipts", "signed_at",
             "initial_grain_service"})
            or (c["site_id"], c["resource"]) not in (("bakery", "grain"), ("market", "food"))
            or type(c["interval_seconds"]) is not int
            or not 12 * 3600 <= c["interval_seconds"] <= 48 * 3600
            or type(c["receipts"]) is not list
            or (("signed_at" not in c) and any(x["courier_id"] == who for x in state["courier_provisions"].values()))
            or ("signed_at" in c and (type(c["signed_at"]) is not int
                or not 0 < c["signed_at"] <= state["time"]
                or (c["site_id"], c["resource"]) != ("market", "food")
                or c["interval_seconds"] != 12 * 3600))):
        raise ValueError("invalid recurring freight contract")
    if "initial_grain_service" in c:
        proof = c["initial_grain_service"]
        if (not isinstance(proof, dict)
                or set(proof) != {"delivery", "delivered_at"}
                or type(proof["delivery"]) is not int
                or type(proof["delivered_at"]) is not int
                or not 0 <= c["signed_at"] - proof["delivered_at"] <= 600
                or not c["receipts"]
                or c["receipts"][0]["delivery"] != proof["delivery"]
                or c["receipts"][0]["delivered_at"] != c["signed_at"]
                or not any(r["delivery"] == proof["delivery"]
                           and r["delivered_at"] == proof["delivered_at"]
                           for r in circuit.get("grain_purchase", {}).get("receipts", ()))
                or any(o["courier_id"] == who
                       and any(p["service_deliveries"] == proof["delivery"]
                               and p["paid_at"] is not None
                               for p in o.get("deferred_grain_services", ()))
                       for o in state["courier_provisions"].values())):
            raise ValueError("first local grain route service must be physically delivered once")
    last_time, last_delivery, unpaid = (c.get("signed_at", -c["interval_seconds"])
                                        - c["interval_seconds"]), 0, False
    for r in c["receipts"]:
        if (type(r) is not dict or set(r) != {"delivery", "delivered_at", "payment"}
                or type(r["delivery"]) is not int or not last_delivery < r["delivery"] <= circuit["deliveries"]
                or type(r["delivered_at"]) is not int
                or not c.get("signed_at", 0) <= r["delivered_at"] <= state["time"]
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


def choose_local_market_freight_agreement(state: WorldState, who: str) -> bool:
    """An employed courier and Salma meet locally to sign a future, earned wage."""
    circuit = state.supply_circuits.get(who)
    if (not circuit or "food_payroll" in circuit or circuit["index"] != 3
            or circuit["stops"][3] != "market"
            or state.npcs[who]["role"] != "courier"
            or state.entities[who]["location_id"] != "market"):
        return False
    from .market import _present
    employer = state.market_stalls.get("market", {}).get("keeper_id")
    if not employer or not _present(state.to_dict(), employer, "market"):
        return False
    from .npc import _injury_rest_decision
    needs = state.npcs[who]["needs"]
    if (needs["hunger"] >= 90 or needs["fatigue"] >= 70
            or needs["safety"] >= 75
            or _injury_rest_decision(state.injuries, who) is not None
            or not _worker_present_and_free(state.to_dict(), who, "market")):
        return False
    stock = state.resources.get("market", {}).get("food")
    return type(stock) is int and stock >= 2


def agree_local_market_freight_wage(state: dict, event: DomainEvent, *,
                                    supply_authorized: bool,
                                    market_authorized: bool) -> None:
    p = event.data
    if (not supply_authorized or not market_authorized
            or set(p) != {"courier_id", "site_id", "resource", "interval_seconds"}
            or p["site_id"] != "market" or p["resource"] != "food"
            or p["interval_seconds"] != 12 * 3600
            or event.actor_id != state["market_stalls"]["market"]["keeper_id"]
            or not choose_local_market_freight_agreement(
                WorldState.from_dict(state), p["courier_id"])):
        raise ValueError("future market food contract requires two consenting present parties")
    # An old, bounded bakery grain wage remains an independently enforceable
    # obligation. A new market agreement only earns on FUTURE food deliveries.
    who = p["courier_id"]
    circuit = state["supply_circuits"][who]
    contract = {"site_id": "market", "resource": "food",
                "interval_seconds": 12 * 3600,
                "signed_at": state["time"], "receipts": []}
    # The courier may have ALREADY transported farm grain to the bakery
    # on this same tour and met the market owner just 40s afterward.
    # This is a legitimate signing-day settlement of one earlier,
    # authenticated UNPAID physical service, not payment for presence.
    recent = next((x for x in reversed(
        circuit.get("grain_purchase", {}).get("receipts", ()))
        if (x["delivery"] == circuit["deliveries"]
            and 0 <= state["time"] - x["delivered_at"] <= 600)), None)
    if recent is not None and not any(
        previous["courier_id"] == who and any(
            x["service_deliveries"] == recent["delivery"]
            and x["paid_at"] is not None
            for x in previous.get("deferred_grain_services", ()))
        for previous in state["courier_provisions"].values()
    ):
        contract["initial_grain_service"] = {
            "delivery": recent["delivery"],
            "delivered_at": recent["delivered_at"],
        }
        contract["receipts"].append({
            "delivery": recent["delivery"],
            "delivered_at": state["time"],
            "payment": None,
        })
    circuit["food_payroll"] = contract


def choose_market_wage_quote_retirement(state: WorldState, who: str) -> str | None:
    """Retire a stale owner quote only when earned wage is already pending."""
    c = state.supply_circuits.get(who, {}).get("food_payroll", {})
    receipts = c.get("receipts", ())
    if (not c.get("signed_at") or c["site_id"] != "market"
            or not receipts or receipts[-1]["payment"] is not None
            or state.entities[who]["location_id"] != "market"):
        return None
    raw = state.to_dict()
    from .market import _present
    from .movement import _in_transit
    employer = state.market_stalls["market"]["keeper_id"]
    if not _present(raw, employer, "market"):
        return None
    from .steward_food_payroll import _earned_sales, PAYMENT_SALES
    sales, wages = _earned_sales(state, "market")
    hold = 3 if len(sales) >= PAYMENT_SALES * (len(wages) + 1) else 2
    if _available_site_food(state, "market") >= hold:
        return None
    for oid, q in sorted(state.market_offers.items()):
        if (q["status"] != "open" or q["site_id"] != "market"
                or q["stock_owner_id"] != "market" or q["seller_id"] != employer
                or q["resource"] != "food"
                or state.time - q["posted_at"] < 6 * 3600
                or _available_site_food(state, "market") + q["remaining"] < hold):
            continue
        for buyer, person in raw["entities"].items():
            if (buyer == employer or person["location_id"] != "market"
                    or _in_transit(raw, buyer)):
                continue
            if buyer in raw["npcs"] and not _present(raw, buyer, "market"):
                continue
            if buyer not in raw["npcs"] and person["controller"] != "player":
                continue
            cash = raw["resources"].get(buyer, {}).get("coin_copper")
            if type(cash) is int and cash >= q["unit_price"]:
                return None
        return oid
    return None
