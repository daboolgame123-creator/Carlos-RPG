"""Read-only operator diagnostics for finite NPC economies (PLAY-47 pilot).

Never expose this omniscient accounting view to NPC planners or a player.
Only the trusted world state/event replay is authoritative; this projection
must not change ownership, supply, market prices, or simulation time.
"""
from __future__ import annotations

from collections import Counter

from .domain import WorldState


def audit_production_wages(state: WorldState) -> dict:
    """Classify completed jobs by their actual signed wage and receipt.

    This is an operator-only accounting view, not authorization to pay a
    worker. A recipe without wage terms is not an unpaid wage, and a food
    receipt must not be mistaken for an unpaid cash receipt.
    """
    counts = Counter()
    due = []
    for job_id, job in sorted(state.production_jobs.items()):
        if job["status"] != "completed":
            continue
        recipe = state.production_recipes[job["recipe_id"]]
        if "wage_coin" in recipe:
            kind, receipt = "coin", "work_wage"
        elif "wage_food" in recipe:
            kind, receipt = "food", "food_wage"
        else:
            counts["without_contract"] += 1
            continue
        if receipt in job:
            counts[kind + "_paid"] += 1
        else:
            counts[kind + "_unpaid"] += 1
            due.append({"job_id": job_id, "worker_id": job["npc_id"],
                        "site_id": job["site_id"], "resource": kind,
                        "amount": recipe["wage_" + kind]})
    return {
        "coin_paid": counts["coin_paid"],
        "coin_unpaid": counts["coin_unpaid"],
        "food_paid": counts["food_paid"],
        "food_unpaid": counts["food_unpaid"],
        "without_contract": counts["without_contract"],
        "unpaid_jobs": due,
    }


def audit_npc_economy(state: WorldState) -> dict:
    """Return a deterministic, read-only snapshot with explicit unknowns.

    A missing copper entry is *unknown*, never implicitly counted as zero.
    The known-total is comparable across checkpoints only with the *same*
    initialized accounting scope; it is not a claim of global monetary
    conservation if any owner has an unknown copper ledger.
    """
    owner_ids = sorted(
        set(state.entities) | set(state.locations) | set(state.resources)
    )
    known_cash: dict[str, int] = {}
    unknown_cash: list[str] = []
    stock_totals: Counter[str] = Counter()
    unknown_stocks: list[tuple[str, str]] = []

    for owner_id in owner_ids:
        holdings = state.resources.get(owner_id, {})
        if "coin_copper" not in holdings or holdings["coin_copper"] is None:
            unknown_cash.append(owner_id)
        for resource, amount in sorted(holdings.items()):
            if amount is None:
                unknown_stocks.append((owner_id, resource))
                continue
            if type(amount) is not int or amount < 0:
                raise ValueError(
                    f"invalid amount for {owner_id}/{resource}: {amount!r}"
                )
            if resource == "coin_copper":
                known_cash[owner_id] = amount
            else:
                stock_totals[resource] += amount

    # Employer-owned food held in provision escrow remains physical food,
    # but is no longer listed in ordinary market saleable inventory.
    for provision in state.courier_provisions.values():
        stock_totals["food"] += provision["remaining"]

    trade_resources: Counter[str] = Counter()
    for trade in state.market_trades.values():
        resource = trade["resource"]
        trade_resources[resource] += 1

    completed = [
        job for job in state.production_jobs.values()
        if job["status"] == "completed"
    ]
    wage_receipts = sum("work_wage" in job for job in completed)
    journeys_arrived = sum(
        journey["status"] == "arrived" for journey in state.travels.values()
    )
    hunger = {
        npc_id: info["needs"].get("hunger")
        for npc_id, info in sorted(state.npcs.items())
    }

    return {
        "world_id": state.world_id,
        "time": state.time,
        "revision": state.revision,
        "copper_known_total": sum(known_cash.values()),
        "copper_known_by_owner": dict(sorted(known_cash.items())),
        "copper_unknown_owners": tuple(unknown_cash),
        "copper_scope_complete": not unknown_cash,
        "stock_known_by_resource": dict(sorted(stock_totals.items())),
        "stock_unknown_entries": tuple(unknown_stocks),
        "trades": len(state.market_trades),
        "trades_by_resource": dict(sorted(trade_resources.items())),
        "completed_jobs": len(completed),
        "completed_without_wage_receipt": len(completed) - wage_receipts,
        "wage_receipts": wage_receipts,
        "trips_arrived": journeys_arrived,
        "npc_hunger": hunger,
    }
