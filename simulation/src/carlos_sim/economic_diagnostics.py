"""Read-only operator diagnostics for finite NPC economies (PLAY-47 pilot).

Never expose this omniscient accounting view to NPC planners or a player.
Only the trusted world state/event replay is authoritative; this projection
must not change ownership, supply, market prices, or simulation time.
"""
from __future__ import annotations

from collections import Counter

from .domain import WorldState


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
    # A market keeper is not the legal owner of the till. Count transfers
    # from authenticated receipts, never infer a salary from a sale or a
    # courier's consigned copper. This operator view is not NPC knowledge.
    cash_flows: dict[tuple[str, str, str], int] = {}
    for trade in state.market_trades.values():
        if trade["payment_resource"] != "coin_copper":
            continue
        key = (trade["buyer_id"], trade["stock_owner_id"], "sale")
        cash_flows[key] = cash_flows.get(key, 0) + trade["total_paid"]
    for job in completed:
        if "work_wage" not in job:
            continue
        receipt = job["work_wage"]
        key = (receipt["site_id"], receipt["worker_id"], "completed_job")
        cash_flows[key] = cash_flows.get(key, 0) + receipt["amount"]
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
        "cash_flows_from_receipts": [
            {"from": source, "to": target, "cause": cause, "copper": amount}
            for (source, target, cause), amount in sorted(cash_flows.items())
        ],
        "trips_arrived": journeys_arrived,
        "npc_hunger": hunger,
    }
