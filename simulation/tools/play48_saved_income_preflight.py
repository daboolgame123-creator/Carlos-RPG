"""READ-ONLY diagnostic for saved original-village PLAY48 SQLite evidence.

Never authorizes wages, trades, cargo, or world updates. Designed for archived
GitHub Actions evidence: cheap causal preflight BEFORE another 96/168h run.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from urllib.parse import quote


def inspect(path: Path) -> dict:
    """Inspect a completed original 13-NPC Rules70 snapshot, without writes."""
    absolute = path.resolve(strict=True)
    uri = "file:" + quote(str(absolute), safe="/:") + "?mode=ro"
    with sqlite3.connect(uri, uri=True) as db:
        db.execute("PRAGMA query_only=ON")
        identity = db.execute(
            "SELECT id, revision, sim_time, schema_version, rules_version FROM worlds"
        ).fetchall()
        if len(identity) != 1:
            raise ValueError("evidence must contain exactly one known world")
        world_id, revision, seconds, schema, rules = identity[0]
        if (schema, rules) != (45, 70):
            raise ValueError(f"unsupported audit-only saved version {schema}/{rules}")
        snapshots = db.execute(
            "SELECT revision, state FROM snapshots WHERE world_id=? "
            "ORDER BY revision DESC LIMIT 1", (world_id,)
        ).fetchall()
        if len(snapshots) != 1 or snapshots[0][0] != revision:
            raise ValueError("evidence lacks authoritative current snapshot")
        state = json.loads(snapshots[0][1])
        if (state["world_id"] != world_id or state["revision"] != revision
                or state["time"] != seconds or len(state["npcs"]) != 13):
            raise ValueError("snapshot identity or original population mismatch")
        deliveries = []
        for (blob,) in db.execute(
            "SELECT payload FROM events WHERE world_id=? ORDER BY seq", (world_id,)
        ):
            event = json.loads(blob)
            if (event["event_type"] == "SupplyCargoDelivered"
                    and event["actor_id"] == "huda"):
                deliveries.append((event["time"], event["data"]["resource"]))

    resources = state["resources"]
    known_cash = {
        owner: stock["coin_copper"] for owner, stock in resources.items()
        if "coin_copper" in stock and type(stock["coin_copper"]) is int
    }
    unknown_cash = sorted(
        owner for owner, stock in resources.items()
        if "coin_copper" not in stock or type(stock["coin_copper"]) is not int
    )
    recipes = state["production_recipes"]
    unpaid_farm = [
        {"job": ident, "worker": job["npc_id"], "amount": recipes[job["recipe_id"]]["wage_coin"]}
        for ident, job in sorted(state["production_jobs"].items())
        if job["site_id"] == "farm" and job["status"] == "completed"
        and "work_wage" not in job and "wage_coin" in recipes[job["recipe_id"]]
    ]
    farm_due = sum(item["amount"] for item in unpaid_farm)
    farm_cash = known_cash.get("farm")
    trades = state["market_trades"].values()
    farm_sales = [
        trade for trade in trades if trade["stock_owner_id"] == "farm"
        and trade["resource"] == "grain"
    ]
    nora = state["npcs"]["nora"]["needs"]
    huda = state["npcs"]["huda"]["needs"]
    nora_stock = resources["nora"]
    nora_meals = sum(x["npc_id"] == "nora" for x in state["consumptions"].values())
    nora_buys = sum(
        x["buyer_id"] == "nora" and x["resource"] == "food"
        for x in state["market_trades"].values()
    )
    last_huda = deliveries[-1][0] if deliveries else None
    blockers = []
    if unknown_cash or sum(known_cash.values()) != 12:
        blockers.append("copper_scope_or_conservation_unverified")
    if farm_cash is None or farm_cash < farm_due:
        blockers.append("earned_farm_wages_not_funded")
    if unpaid_farm and not farm_sales:
        blockers.append("farm_harvest_without_grain_sale_receipt")
    if nora["hunger"] == 100 and nora_meals == 0 and nora_buys == 0:
        blockers.append("nora_has_no_real_food_access")
    if (huda["hunger"] >= 90 and last_huda is not None
            and seconds - last_huda >= 12 * 3600):
        blockers.append("huda_freight_stalled_12h_with_hunger")
    return {
        "source": absolute.name, "hour": seconds // 3600,
        "version": [schema, rules], "original_npcs": len(state["npcs"]),
        "copper": sum(known_cash.values()), "unknown_copper_owners": unknown_cash,
        "farm_cash": farm_cash, "farm_unpaid_wages": unpaid_farm,
        "farm_unpaid_copper_due": farm_due, "farm_grain_sale_receipts": len(farm_sales),
        "nora": {"hunger": nora["hunger"], "cash": nora_stock.get("coin_copper"),
                 "food": nora_stock.get("food"), "purchases": nora_buys,
                 "meals": nora_meals},
        "huda": {"hunger": huda["hunger"], "deliveries": len(deliveries),
                 "last_delivery_at": last_huda, "delivery_resources": deliveries},
        "market_food_stock": resources["market"].get("food"),
        "total_food_sales": sum(x["resource"] == "food" for x in trades),
        "total_consumed_meals": len(state["consumptions"]),
        "blockers": blockers, "economic_release_go": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--control", type=Path)
    args = parser.parse_args()
    report = {"candidate": inspect(args.candidate)}
    if args.control is not None:
        baseline = inspect(args.control)
        contender = report["candidate"]
        if baseline["hour"] != contender["hour"]:
            raise ValueError("control and candidate checkpoint hours differ")
        report["control"] = baseline
        report["delta"] = {
            "huda_deliveries": contender["huda"]["deliveries"] - baseline["huda"]["deliveries"],
            "food_sales": contender["total_food_sales"] - baseline["total_food_sales"],
            "meals": contender["total_consumed_meals"] - baseline["total_consumed_meals"],
        }
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
