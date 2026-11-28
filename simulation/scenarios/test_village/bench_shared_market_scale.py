"""Opt-in scale probe for many real NPC buyers at one finite shared market.

This is a bounded market-path benchmark, not an economy sustainability or
general world-capacity claim. The single opening stock and each buyer's cash
are explicit time-zero resources. Normal NPC selectors create offers/trades;
SQLite remains the source of truth.

Run from ``simulation`` with::

    PYTHONPATH=src python scenarios/test_village/bench_shared_market_scale.py

No wall-time threshold is used. Compare identical Python/source/machine runs.
"""
from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from pathlib import Path
from statistics import median
from tempfile import TemporaryDirectory
from time import perf_counter

from carlos_sim import DomainEvent, LivingWorldEngine, SQLiteEventStore, TimeEngine
from carlos_sim import canonical_hash

WORLD = "shared-market-crowd-scale"
KEEPER = "market-keeper"
MARKET = "market"
BUYER_CASH = 2
FOOD_PRICE = 2


def _event(kind: str, data: dict) -> DomainEvent:
    return DomainEvent(kind, None, "finite shared-market benchmark genesis", 0, data)


def buyer_ids(total_npcs: int) -> tuple[str, ...]:
    if type(total_npcs) is not int or total_npcs < 2:
        raise ValueError("total_npcs must include one keeper and at least one buyer")
    return tuple(f"buyer-{index:03d}" for index in range(1, total_npcs))


def seed_world(store: SQLiteEventStore, total_npcs: int, food_stock: int) -> None:
    buyers = buyer_ids(total_npcs)
    if type(food_stock) is not int or food_stock < 1:
        raise ValueError("food_stock must be a positive finite opening amount")
    store.create_world(WORLD)
    events = [
        _event("LocationCreated", {"id": MARKET, "name": "Shared Market"}),
        _event("EntityCreated", {
            "id": KEEPER, "name": "Market Keeper", "location_id": MARKET,
            "controller": "npc",
        }),
        _event("NPCConfigured", {
            "npc_id": KEEPER, "role": "merchant",
            "needs": {"hunger": 20, "fatigue": 0, "safety": 0},
            "goals": {"earn": 10, "explore": 1, "survive": 30},
        }),
        _event("MarketStallConfigured", {"site_id": MARKET, "keeper_id": KEEPER}),
        _event("ResourceChanged", {
            "owner_id": MARKET, "resource": "food", "previous": None,
            "current": food_stock, "source": "initialization",
        }),
        _event("ResourceChanged", {
            "owner_id": MARKET, "resource": "coin_copper", "previous": None,
            "current": 0, "source": "initialization",
        }),
    ]
    for resource in ("food", "coin_copper", "labor_units", "investigation_attempts"):
        events.append(_event("ResourceChanged", {
            "owner_id": KEEPER, "resource": resource, "previous": None,
            "current": 0, "source": "initialization",
        }))
    for ident in buyers:
        events.extend((
            _event("EntityCreated", {
                "id": ident, "name": ident, "location_id": MARKET,
                "controller": "npc",
            }),
            _event("NPCConfigured", {
                "npc_id": ident, "role": "resident",
                "needs": {"hunger": 85, "fatigue": 0, "safety": 0},
                "goals": {"earn": 10, "explore": 1, "survive": 30},
            }),
        ))
        for resource, quantity in (("food", 0), ("coin_copper", BUYER_CASH),
                                    ("labor_units", 0), ("investigation_attempts", 0)):
            events.append(_event("ResourceChanged", {
                "owner_id": ident, "resource": resource, "previous": None,
                "current": quantity, "source": "initialization",
            }))
    events.append(_event("EntityCreated", {
        "id": "carlos", "name": "Carlos", "location_id": MARKET,
        "controller": "player",
    }))
    store.append(WORLD, "shared-market:bootstrap", 0, events, bootstrap=True)


def _manifest(store: SQLiteEventStore) -> list[dict]:
    rows = store.db.execute(
        "SELECT payload FROM events WHERE world_id=? ORDER BY seq", (WORLD,),
    ).fetchall()
    return [json.loads(payload) for (payload,) in rows]


def _audit(state, total_npcs: int, opening_food: int) -> dict:
    buyers = buyer_ids(total_npcs)
    trades = list(state.market_trades.values())
    expected_sales = min(len(buyers), opening_food)
    if len(trades) != expected_sales:
        raise AssertionError(
            f"expected {expected_sales} real sales from finite stock, got {len(trades)}")
    if len({trade["buyer_id"] for trade in trades}) != len(trades):
        raise AssertionError("one NPC purchased more than once in the same market pass")
    if any((trade["buyer_id"] not in buyers
            or trade["seller_id"] != KEEPER
            or trade["stock_owner_id"] != MARKET
            or trade["site_id"] != MARKET
            or trade["resource"] != "food"
            or trade["quantity"] != 1
            or trade["unit_price"] != FOOD_PRICE
            or trade["total_paid"] != FOOD_PRICE)
           for trade in trades):
        raise AssertionError("market ledger contains a trade outside the seeded contract")
    food_total = sum(wallet.get("food", 0) for wallet in state.resources.values())
    copper_total = sum(wallet.get("coin_copper", 0)
                       for wallet in state.resources.values())
    if food_total != opening_food:
        raise AssertionError(f"food conservation failed: {food_total} != {opening_food}")
    if copper_total != len(buyers) * BUYER_CASH:
        raise AssertionError("opening buyer copper was not conserved")
    if any(value < 0 for wallet in state.resources.values()
           for value in wallet.values() if type(value) is int):
        raise AssertionError("a market participant has a negative resource balance")
    offer = next(iter(state.market_offers.values()), None)
    if offer is None or offer["remaining"] != opening_food - expected_sales:
        raise AssertionError("the market offer does not match remaining owned stock")
    served = sorted(trade["buyer_id"] for trade in trades)
    unserved = sorted(set(buyers) - set(served))
    return {
        "buyers": len(buyers),
        "market_trades": len(trades),
        "served_buyers": served,
        "unserved_buyers": unserved,
        "food_remaining_at_market": state.resources[MARKET]["food"],
        "food_held_by_buyers": sum(
            state.resources.get(ident, {}).get("food", 0) for ident in buyers),
        "opening_copper": len(buyers) * BUYER_CASH,
        "closing_copper": copper_total,
        "offer_remaining": offer["remaining"],
    }


def run_sample(database: Path, total_npcs: int, food_stock: int,
               advance_seconds: int = 1) -> dict:
    if type(advance_seconds) is not int or advance_seconds < 1:
        raise ValueError("advance_seconds must be a positive integer")
    with SQLiteEventStore(database) as store:
        seed_world(store, total_npcs, food_stock)
        clock = TimeEngine(store)
        clock.open_session(WORLD)
        try:
            engine = LivingWorldEngine(
                store, clock, economic_enabled=True, max_events_per_advance=100_000,
            )
            before = store.load(WORLD)
            started = perf_counter()
            outcome = engine.advance(
                WORLD, seconds=advance_seconds,
                command_id=f"shared-market:advance:{advance_seconds}",
                expected_revision=before.revision,
            )
            advance_wall_seconds = perf_counter() - started
            state = outcome.state
            audit = _audit(state, total_npcs, food_stock)
            store.snapshot(WORLD)
            snapshot_started = perf_counter()
            snapshot_state = store.load(WORLD)
            snapshot_load_seconds = perf_counter() - snapshot_started
            if snapshot_state.to_dict() != state.to_dict():
                raise AssertionError("snapshot load differs from the advanced world")
            replay_started = perf_counter()
            replay = store.verify(WORLD)
            replay_seconds = perf_counter() - replay_started
            if replay.to_dict() != state.to_dict():
                raise AssertionError("event replay differs from the advanced world")
            if store.db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise AssertionError("SQLite integrity check failed")
            manifest = _manifest(store)
            event_types = {}
            for row in manifest:
                event_types[row["event_type"]] = event_types.get(row["event_type"], 0) + 1
            result = {
                "total_npcs": total_npcs,
                "food_stock": food_stock,
                "simulated_seconds": state.time,
                "revision": state.revision,
                "events": len(manifest),
                "event_types": event_types,
                "audit": audit,
                "state_digest": canonical_hash(state.to_dict()),
                "event_ledger_digest": canonical_hash(manifest),
                "advance_wall_seconds": advance_wall_seconds,
                "snapshot_load_seconds": snapshot_load_seconds,
                "full_replay_seconds": replay_seconds,
                "sqlite_database_bytes": database.stat().st_size,
            }
        finally:
            clock.close_session(WORLD)
    with SQLiteEventStore(database) as reopened:
        loaded = reopened.load(WORLD)
        replay = reopened.verify(WORLD)
        if loaded.to_dict() != replay.to_dict():
            raise AssertionError("reopened SQLite state differs from event replay")
        if reopened.db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise AssertionError("reopened SQLite integrity check failed")
        if canonical_hash(loaded.to_dict()) != result["state_digest"]:
            raise AssertionError("reopened SQLite state differs from measured digest")
    return result


def measure(total_npcs: int, food_stock: int, repeats: int,
            advance_seconds: int) -> dict:
    samples = []
    with TemporaryDirectory(prefix="carlos-shared-market-") as temp:
        for index in range(repeats):
            path = Path(temp) / f"sample-{index}.sqlite"
            samples.append(run_sample(path, total_npcs, food_stock, advance_seconds))
    digests = {(sample["state_digest"], sample["event_ledger_digest"])
               for sample in samples}
    if len(digests) != 1:
        raise AssertionError("independent shared-market samples were not deterministic")
    return {
        "total_npcs": total_npcs,
        "food_stock": food_stock,
        "repeats": repeats,
        "events": samples[0]["events"],
        "market_trades": samples[0]["audit"]["market_trades"],
        "state_digest": samples[0]["state_digest"],
        "event_ledger_digest": samples[0]["event_ledger_digest"],
        "advance_wall_seconds_median": round(
            median(sample["advance_wall_seconds"] for sample in samples), 6),
        "snapshot_load_seconds_median": round(
            median(sample["snapshot_load_seconds"] for sample in samples), 6),
        "full_replay_seconds_median": round(
            median(sample["full_replay_seconds"] for sample in samples), 6),
        "sqlite_database_bytes_median": int(median(
            sample["sqlite_database_bytes"] for sample in samples)),
    }


def source_identity() -> dict:
    root = Path(__file__).resolve().parents[3]
    try:
        head = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            text=True, stderr=subprocess.DEVNULL,
        ).strip()
        status = subprocess.check_output(
            ["git", "-C", str(root), "status", "--porcelain"],
            text=True, stderr=subprocess.DEVNULL,
        ).strip()
        return {"head_sha": head, "working_tree_clean": not bool(status)}
    except (OSError, subprocess.CalledProcessError):
        return {"head_sha": None, "working_tree_clean": None}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--npcs", nargs="+", type=int, default=[13, 32, 64],
                        help="total NPCs, including the single market keeper")
    parser.add_argument("--stock", type=int, default=None,
                        help="finite opening food units; default funds one per buyer")
    parser.add_argument("--seconds", type=int, default=1,
                        help="one bounded logical advance (default: 1 second)")
    parser.add_argument("--repeats", type=int, default=3,
                        help="fresh SQLite worlds per size; digests must match")
    args = parser.parse_args()
    if (not args.npcs or any(value < 2 for value in args.npcs)
            or args.stock is not None and args.stock < 1
            or args.seconds < 1 or args.repeats < 2):
        parser.error("npcs must be >=2, stock/seconds positive, repeats at least 2")
    results = []
    for population in args.npcs:
        stock = args.stock if args.stock is not None else population - 1
        results.append(measure(population, stock, args.repeats, args.seconds))
    print(json.dumps({
        "benchmark": "shared-market-crowd-scale-v1",
        "source": source_identity(),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "scope": {
            "one_shared_market": True,
            "npcs_include_one_keeper": True,
            "opening_stock_and_buyer_cash_are_explicit_genesis_resources": True,
            "buyer_opening_copper_each": BUYER_CASH,
            "unit_price_copper": FOOD_PRICE,
            "simulated_seconds": args.seconds,
            "repeats": args.repeats,
            "limits": ["food market only", "single short tick",
                       "not a multi-day economy or general capacity claim"],
        },
        "results": results,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
