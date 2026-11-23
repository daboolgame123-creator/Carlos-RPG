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
    if (type(c) is not dict or set(c) !=
            {"site_id", "resource", "interval_seconds", "receipts"}
            or (c["site_id"], c["resource"]) not in (("bakery", "grain"), ("market", "food"))
            or type(c["interval_seconds"]) is not int
            or not 12 * 3600 <= c["interval_seconds"] <= 48 * 3600
            or type(c["receipts"]) is not list
            or not _previous_wages_fully_satisfied(state, who)):
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


# PLAY48 P10: Real market employer and a physically present working courier may
# agree a NEW prospective in-kind wage after a previous bounded contract is
# actually spent. Never re-open or mutate the old signed service contract.
LOCAL_MARKET_HIRE_INTERVAL = 12 * 3600


def _previous_wages_fully_satisfied(state: dict, who: str) -> bool:
    """No existing funding or documented claim is lost by a new job agreement."""
    for c in state["courier_provisions"].values():
        if c["courier_id"] != who:
            continue
        if "deferred_grain_services" in c:
            # This historical bakery contract expires at its original signed
            # ceiling; every delivery must already have actually been paid.
            proof = c["deferred_grain_services"]
            if (c["remaining"] != 0 or len(proof) != c["authorized_total_units"]
                    or any(row["paid_at"] is None for row in proof)):
                return False
        elif (c["remaining"] != 0
              or c["total_units"] < c["authorized_total_units"]):
            return False
    return True


def _local_market_hire_eligible(state: dict, who: str) -> bool:
    """A witnessed wage for subsequent unloading, not a free-food grant.

    At a worksite, an able courier may negotiate BEFORE surrendering the
    physically carried market-bound FOOD, or before later freight. No loaf
    transfers until actual delivery has completed and created its own receipt.
    No existing posted offer is ever overridden.
    """
    from .market import _present
    site = "market"
    circuit = state["supply_circuits"].get(who)
    stall = state["market_stalls"].get(site)
    keeper = stall["keeper_id"] if stall else None
    if (circuit is None or keeper not in state["npcs"]
            or who not in state["npcs"] or who == keeper
            or state["npcs"][who]["role"] != "courier"
            or state["npcs"][keeper]["role"] != "merchant"
            or "food_payroll" in circuit
            or circuit["index"] != 3
            or (circuit["carry"] is not None
                and circuit["carry"].get("resource") != "food")
            or circuit["deliveries"] < 1
            or site != circuit["stops"][3]
            or not _previous_wages_fully_satisfied(state, who)
            or not _worker_present_and_free(state, who, site)
            or not _worker_present_and_free(state, keeper, site)
            or not _present(state, keeper, site)):
        return False
    # The one REAL carried market-bound loaf can fund its OWN unloading:
    # signing happens BEFORE physical transfer, a wage receipt is established
    # only AFTER the canonical SupplyCargoDelivered reducer succeeds. Existing
    # posted offers remain fully protected; never pay against promised stock.
    incoming = circuit["carry"] is not None
    local_free = _available_site_food(state, site)
    if local_free < (0 if incoming else 1):
        return False
    needs = state["npcs"][who]["needs"]
    return (needs["hunger"] < 90 and needs["fatigue"] < 70
            and needs["safety"] < 75)


def choose_local_market_employment(state: WorldState, who: str) -> bool:
    """Pure opt-in choice, grounded in the two workers' actual same-place facts."""
    return _local_market_hire_eligible(state.to_dict(), who)


def sign_local_market_employment(state: dict, event: DomainEvent, *,
                                 market_authorized: bool,
                                 supply_authorized: bool) -> None:
    """Authority and consent at the merchant's REAL stall before future work.

    Does not move, mint or escrow food and never create a paid work receipt.
    The existing cargo reducer will independently sign future labor receipts;
    its existing wage reducer alone can later pay one genuinely owned loaf.
    """
    p = event.data
    if (not market_authorized or not supply_authorized
            or event.time == 0
            or set(p) != {"courier_id", "site_id", "resource", "interval_seconds"}
            or type(p.get("courier_id")) is not str
            or p.get("site_id") != "market"
            or p.get("resource") != "food"
            or type(p.get("interval_seconds")) is not int
            or p["interval_seconds"] != LOCAL_MARKET_HIRE_INTERVAL):
        raise ValueError("local employment needs both trusted market and freight authority")
    who = p["courier_id"]
    stall = state["market_stalls"].get("market")
    if (stall is None or event.actor_id != stall["keeper_id"]
            or not _local_market_hire_eligible(state, who)):
        raise ValueError("unavailable courier, employer or real food, or active earlier wage")
    state["supply_circuits"][who]["food_payroll"] = {
        "site_id": "market", "resource": "food",
        "interval_seconds": LOCAL_MARKET_HIRE_INTERVAL, "receipts": [],
    }


LOCAL_MARKET_MEETING_MAX_WAIT = 3600


def waits_for_local_market_hire(state: WorldState, who: str) -> bool:
    """A courier can wait briefly at a REAL market for a resting steward.

    The meeting is NOT an agreement, payroll, purchase or new resource. A
    documented actual market arrival is required; expiry is tied to that real
    arrival rather than an unlimited count of reattempts. Only when the
    merchant finishes a scheduled rest may the normal local signer run.
    """
    from .npc import _injury_rest_decision
    c = state.supply_circuits.get(who)
    if (c is None or "food_payroll" in c or c["index"] != 3
            or (c["carry"] is not None
                and c["carry"].get("resource") != "food")
            or c["deliveries"] < 1
            or state.entities[who]["location_id"] != "market"
            or not _previous_wages_fully_satisfied(state.to_dict(), who)
            or not _worker_present_and_free(state, who, "market")):
        return False
    needs = state.npcs[who]["needs"]
    if (needs["hunger"] >= 90 or needs["fatigue"] >= 70
            or needs["safety"] >= 75
            or _injury_rest_decision(state.injuries, who) is not None):
        return False
    latest_arrival = max((
        t["arrived_at"] for t in state.travels.values()
        if t["npc_id"] == who and t["status"] == "arrived"
        and t["destination"] == "market"
    ), default=None)
    if (latest_arrival is None
            or not 0 <= state.time-latest_arrival < LOCAL_MARKET_MEETING_MAX_WAIT):
        return False
    stall = state.market_stalls.get("market")
    keeper = stall["keeper_id"] if stall else None
    if (keeper not in state.npcs
            or state.npcs[keeper]["role"] != "merchant"
            or state.entities[keeper]["location_id"] != "market"
            or type(state.resources.get("market",{}).get("food")) is not int
            or state.resources["market"]["food"] <= 0):
        return False
    return any(
        action["npc_id"] == keeper and action["status"] == "running"
        and action["action"] == "rest"
        and state.time < action["due"] <= latest_arrival + LOCAL_MARKET_MEETING_MAX_WAIT
        for action in state.actions.values())
