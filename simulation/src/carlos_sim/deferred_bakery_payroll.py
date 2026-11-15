"""Bounded PLAY48 post-production courier wage: REAL bakery grain delivery only.

Does not reserve opening food. Only real grain delivery establishes a signed
nonspendable work claim in the canonical physical cargo reducer. A later
completed real bakery bread job may pay it, but ONLY to its physically present
courier from unquoted, unescrowed local surplus. Customer quotes, cargo and
pre-existing barter obligations outrank payroll. A bounded *physical stay*
(up to 1 simulated hour) allows the courier to collect her real earned loaf
before she walks the next known road; no fictitious source stock exists.
"""
from __future__ import annotations
from typing import Any
from .domain import DomainEvent, WorldState
from .food_for_work import _available_site_food, _worker_present_and_free

MAX_BALANCE = 2**31 - 1
MIN_UNPROMISED_BREAD = 1
MAX_WAGE_COLLECTION_WAIT = 3600

def register_local_grain_service(state: dict[str, Any], who: str) -> None:
    circuit = state["supply_circuits"][who]
    if (state["entities"][who]["location_id"] != "bakery"
            or circuit["index"] != 2 or circuit["carry"] is not None):
        raise ValueError("deferred salary needs a physically delivered grain manifest")
    for c in state["courier_provisions"].values():
        if (c["courier_id"] != who or c["payer_site"] != "bakery"
                or "deferred_grain_services" not in c):
            continue
        proof = circuit["deliveries"]
        if any(x["service_deliveries"] == proof for x in c["deferred_grain_services"]):
            raise ValueError("duplicate grain-service evidence")
        if len(c["deferred_grain_services"]) >= c["authorized_total_units"]:
            return
        c["deferred_grain_services"].append({
            "service_deliveries": proof, "earned_at": state["time"],
            "paid_at": None,
        })


def _genuine_later_bread(jobs: Any, recipes: Any, earned_at: int, now: int) -> bool:
    return any(
        j["status"] == "completed" and j["site_id"] == "bakery"
        and j["finished_at"] is not None and earned_at < j["finished_at"] <= now
        and recipes[j["recipe_id"]]["output_resource"] == "food"
        for j in jobs.values()
    )


def courier_waits_for_due_bakery_food(state: WorldState, who: str) -> bool:
    """One-hour maximum local payment collection at the *real* worksite.

    Requires the original grain-delivery receipt and signed contract.
    No travel shortcut, hunger/stamina bypass, remote stock read, fake food,
    or open-ended waiting. If bread never finishes, the courier continues
    her existing physical route after the finite window.
    """
    circuit = state.supply_circuits.get(who)
    if (circuit is None or circuit["index"] != 2 or circuit["carry"] is not None
            or not _worker_present_and_free(state, who, "bakery")):
        return False
    for c in state.courier_provisions.values():
        if (c["courier_id"] != who or c["payer_site"] != "bakery"
                or "deferred_grain_services" not in c):
            continue
        for receipt in c["deferred_grain_services"]:
            if (receipt["paid_at"] is None
                    and 0 <= state.time-receipt["earned_at"] < MAX_WAGE_COLLECTION_WAIT):
                return True
    return False


def choose_deferred_bakery_payment(state: WorldState,
                                   who: str) -> tuple[str, int] | None:
    circuit = state.supply_circuits.get(who)
    if (circuit is None or circuit["index"] != 2 or circuit["carry"] is not None
            or not _worker_present_and_free(state, who, "bakery")
            or _available_site_food(state, "bakery") < MIN_UNPROMISED_BREAD
            or type(state.resources.get(who, {}).get("food")) is not int
            or state.resources[who]["food"] >= MAX_BALANCE):
        return None
    for ident, c in sorted(state.courier_provisions.items()):
        if (c["courier_id"] != who or c["payer_site"] != "bakery"
                or "deferred_grain_services" not in c):
            continue
        for proof in c["deferred_grain_services"]:
            if proof["paid_at"] is None and _genuine_later_bread(
                    state.production_jobs, state.production_recipes,
                    proof["earned_at"], state.time):
                return ident, proof["service_deliveries"]
    return None


def pay_deferred_bakery_food(state: dict[str, Any], event: DomainEvent, *,
                             supply_authorized: bool,
                             production_authorized: bool) -> None:
    p = event.data
    if (not supply_authorized or not production_authorized
            or event.actor_id is not None
            or set(p) != {"id", "courier_id", "service_deliveries", "amount"}
            or type(p["id"]) is not str or not p["id"]
            or type(p["courier_id"]) is not str or not p["courier_id"]
            or type(p["service_deliveries"]) is not int
            or type(p["amount"]) is not int or p["amount"] != 1):
        raise ValueError("invalid trusted deferred bakery food-wage receipt")
    c = state["courier_provisions"].get(p["id"])
    who = p["courier_id"]
    circuit = state["supply_circuits"].get(who)
    if (c is None or circuit is None or c["courier_id"] != who
            or c["payer_site"] != "bakery"
            or "deferred_grain_services" not in c
            or circuit["index"] != 2 or circuit["carry"] is not None
            or not _worker_present_and_free(state, who, "bakery")):
        raise ValueError("real bakery worker must be physically present")
    proof = next((row for row in c["deferred_grain_services"]
                  if row["service_deliveries"] == p["service_deliveries"]
                  and row["paid_at"] is None), None)
    if (proof is None or p["service_deliveries"] > circuit["deliveries"]
            or not _genuine_later_bread(state["production_jobs"],
                                        state["production_recipes"],
                                        proof["earned_at"], state["time"])
            or _available_site_food(state, "bakery") < MIN_UNPROMISED_BREAD):
        raise ValueError("no real later unquoted bakery food for actual service")
    shop, person = state["resources"].get("bakery", {}), state["resources"].get(who, {})
    source, own = shop.get("food"), person.get("food")
    if (type(source) is not int or source < MIN_UNPROMISED_BREAD
            or type(own) is not int or not 0 <= own < MAX_BALANCE):
        raise ValueError("missing bounded physical source/worker food")
    shop["food"], person["food"] = source - 1, own + 1
    proof.update({"paid_at": state["time"],
                  "site_before": source, "site_after": source - 1,
                  "worker_before": own, "worker_after": own + 1})


def validate_deferred_grain_ledger(state: dict[str, Any],
                                   c: dict[str, Any]) -> None:
    if (c["payer_site"] != "bakery" or c["total_units"] != 0
            or c["remaining"] != 0 or c["payments"]
            or not 1 <= c["authorized_total_units"] <= 3
            or type(c["deferred_grain_services"]) is not list
            or len(c["deferred_grain_services"]) > c["authorized_total_units"]):
        raise ValueError("deferred bakery contract is finite and initially unfunded")
    upper = state["supply_circuits"][c["courier_id"]]["deliveries"]
    seen = set()
    previous = -1
    for row in c["deferred_grain_services"]:
        if type(row) is not dict:
            raise ValueError("invalid deferred grain proof")
        paid, service, earned = (row.get("paid_at"),
                                 row.get("service_deliveries"), row.get("earned_at"))
        fields = {"service_deliveries", "earned_at", "paid_at"}
        if paid is not None:
            fields |= {"site_before", "site_after", "worker_before", "worker_after"}
        if (set(row) != fields
                or type(service) is not int or not 1 <= service <= upper
                or service in seen or type(earned) is not int
                or not previous <= earned <= state["time"]
                or (paid is not None and (
                    type(paid) is not int or not earned < paid <= state["time"]
                    or any(type(row[k]) is not int or not 0 <= row[k] <= MAX_BALANCE
                           for k in ("site_before", "site_after",
                                     "worker_before", "worker_after"))
                    or row["site_before"] - row["site_after"] != 1
                    or row["worker_after"] - row["worker_before"] != 1))):
            raise ValueError("forged, duplicated or unbalanced bakery wage")
        seen.add(service)
        previous = earned
