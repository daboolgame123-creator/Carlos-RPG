"""Opt-in benchmark for the event-sourced market steward payroll history.

The fixture starts with explicitly declared, finite market food and buyer
copper. It then sends real authorized clock, offer, trade, and payroll events
through SQLiteEventStore reducers. Timings have no pass/fail threshold; digests,
conservation, payroll backing, and replay parity are the acceptance checks.

Run from ``simulation`` with:
    PYTHONPATH=src python scenarios/test_village/bench_market_payroll_history.py
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
import json
from pathlib import Path
import platform
import subprocess
import sys
from statistics import median
from tempfile import TemporaryDirectory
from time import perf_counter
from typing import Any

from carlos_sim import DomainEvent, SQLiteEventStore, TimeEngine
from carlos_sim.domain import WorldState, canonical_hash
from carlos_sim import steward_food_payroll


WORLD = "market-payroll-benchmark"
SITE = "market"
KEEPER = "keeper"
BUYERS = ("buyer-00", "buyer-01", "buyer-02", "buyer-03")


def _event(kind: str, data: dict[str, Any], *, actor: str | None = None,
           at: int = 0, cause: str = "finite payroll benchmark genesis") -> DomainEvent:
    return DomainEvent(kind, actor, cause, at, data)


def _bootstrap_events(receipts: int, *, contract: bool) -> list[DomainEvent]:
    sales = receipts * 2
    opening_food = sales + receipts + 1  # sales, paid wages, one operating loaf
    purchases_per_buyer = [
        sales // len(BUYERS) + (index < sales % len(BUYERS))
        for index in range(len(BUYERS))
    ]
    events = [_event("LocationCreated", {"id": SITE, "name": "Market"})]
    for ident, name, role in (
        (KEEPER, "Market keeper", "merchant"),
        *((buyer, f"Buyer {index:02d}", "resident")
          for index, buyer in enumerate(BUYERS)),
    ):
        events.extend((
            _event("EntityCreated", {
                "id": ident, "name": name, "location_id": SITE,
                "controller": "npc",
            }),
            _event("NPCConfigured", {
                "npc_id": ident, "role": role,
                "needs": {"hunger": 20, "fatigue": 5, "safety": 0},
                "goals": {"earn": 50, "explore": 10, "survive": 30},
            }),
        ))

    opening_balances = [(SITE, "food", opening_food), (SITE, "coin_copper", 0),
                        (KEEPER, "food", 0), (KEEPER, "coin_copper", 0)]
    for buyer, quota in zip(BUYERS, purchases_per_buyer):
        opening_balances.extend(((buyer, "food", 0), (buyer, "coin_copper", quota)))
    events.extend(_event("ResourceChanged", {
        "owner_id": owner, "resource": resource, "previous": None,
        "current": amount, "source": "initialization",
    }) for owner, resource, amount in opening_balances)
    events.append(_event("MarketStallConfigured", {
        "site_id": SITE, "keeper_id": KEEPER,
    }))
    if contract:
        events.append(_event("MarketStewardFoodContractSigned", {
            "site_id": SITE, "keeper_id": KEEPER, "sales_per_wage": 2,
        }))
    return events


def _transaction_events(receipts: int, *, contract: bool) -> list[DomainEvent]:
    events: list[DomainEvent] = []
    logical_time = 0
    sales = receipts * 2
    for index in range(sales):
        previous_time = logical_time
        logical_time += 1
        events.append(_event("TimeAdvanced", {
            "from": previous_time, "to": logical_time,
        }, at=logical_time, cause="one second between actual market sales"))
        quote_id = f"quote-{index:06d}"
        trade_id = f"trade-{index:06d}"
        buyer_id = BUYERS[index % len(BUYERS)]
        events.append(_event("MarketOfferPosted", {
            "id": quote_id, "seller_id": KEEPER, "stock_owner_id": SITE,
            "site_id": SITE, "resource": "food", "quantity": 1,
            "payment_resource": "coin_copper", "unit_price": 1,
        }, actor=KEEPER, at=logical_time,
           cause="keeper lists one physically owned benchmark loaf"))
        events.append(_event("MarketTradeExecuted", {
            "id": trade_id, "offer_id": quote_id, "buyer_id": buyer_id,
            "quantity": 1, "expected_unit_price": 1,
        }, actor=buyer_id, at=logical_time,
           cause="present buyer purchases one funded benchmark loaf"))
        if contract and index % 2 == 1:
            events.append(_event("MarketStewardFoodWagePaid", {
                "site_id": SITE, "trade_id": trade_id, "amount": 1,
            }, at=logical_time,
               cause="two completed local sales fund one physical keeper loaf"))
    return events


class _ScanCounter:
    def __init__(self) -> None:
        self.calls = 0
        self.trade_rows_scanned = 0

    def record(self, state: WorldState | dict[str, Any]) -> None:
        trades = (state.market_trades if isinstance(state, WorldState)
                  else state["market_trades"])
        self.calls += 1
        # _earned_sales iterates the complete trade map before filtering it.
        self.trade_rows_scanned += len(trades)

    def snapshot(self) -> dict[str, int]:
        return {"earned_sales_calls": self.calls,
                "trade_rows_scanned": self.trade_rows_scanned}

    def reset(self) -> None:
        self.calls = self.trade_rows_scanned = 0


@contextmanager
def _count_payroll_history_scans():
    counter = _ScanCounter()
    original = steward_food_payroll._earned_sales

    def counted(state: WorldState | dict[str, Any], site: str):
        counter.record(state)
        return original(state, site)

    steward_food_payroll._earned_sales = counted
    try:
        yield counter
    finally:
        steward_food_payroll._earned_sales = original


def _resource_total(state: WorldState, resource: str) -> int:
    return sum(balance.get(resource, 0) for balance in state.resources.values())


def run_sample(receipts: int, *, contract: bool,
               count_scans: bool = False) -> dict[str, Any]:
    with TemporaryDirectory(prefix="carlos-market-payroll-") as temp:
        database = Path(temp) / "world.sqlite"
        with SQLiteEventStore(database) as store:
            store.create_world(WORLD)
            genesis = _bootstrap_events(receipts, contract=contract)
            opening = store.append(WORLD, "finite-benchmark-genesis", 0,
                                   genesis, bootstrap=True)
            opening_food = _resource_total(opening, "food")
            opening_cash = _resource_total(opening, "coin_copper")
            expected_opening_food = receipts * 3 + 1
            if opening_food != expected_opening_food or opening_cash != receipts * 2:
                raise AssertionError("benchmark fixture opening ownership is not explicit")

            clock = TimeEngine(store)
            clock.open_session(WORLD)
            events = _transaction_events(receipts, contract=contract)
            if count_scans:
                with _count_payroll_history_scans() as counter:
                    append_started = perf_counter()
                    result = store.append(
                        WORLD, "sequential-market-history", opening.revision, events,
                        clock_authorized=True, market_authorized=True,
                    )
                    append_seconds = perf_counter() - append_started
                    append_work = counter.snapshot()
                    counter.reset()
                    replay_started = perf_counter()
                    replay = store.verify(WORLD)
                    replay_seconds = perf_counter() - replay_started
                    replay_work = counter.snapshot()
            else:
                append_started = perf_counter()
                result = store.append(
                    WORLD, "sequential-market-history", opening.revision, events,
                    clock_authorized=True, market_authorized=True,
                )
                append_seconds = perf_counter() - append_started
                append_work = None
                replay_started = perf_counter()
                replay = store.verify(WORLD)
                replay_seconds = perf_counter() - replay_started
                replay_work = None
            clock.close_session(WORLD)

            if replay.to_dict() != result.to_dict():
                raise AssertionError("full event replay differs from committed projection")
            if replay.time != receipts * 2:
                raise AssertionError("logical sale times did not advance monotonically")
            if len(replay.market_trades) != receipts * 2:
                raise AssertionError("benchmark did not execute every physical market sale")
            paid = [trade for trade in replay.market_trades.values()
                    if "steward_food_wage" in trade]
            expected_paid = receipts if contract else 0
            if len(paid) != expected_paid:
                raise AssertionError("payroll count differs from signed completed work")
            if any(receipt["steward_food_wage"]["paid_at"]
                   != receipt["executed_at"] for receipt in paid):
                raise AssertionError("benchmark wage is not paid after its real sale")

            final_food = _resource_total(replay, "food")
            final_cash = _resource_total(replay, "coin_copper")
            if final_food != opening_food or final_cash != opening_cash:
                raise AssertionError("market benchmark failed physical food/cash conservation")
            expected_market_food = 1 if contract else receipts + 1
            expected_keeper_food = receipts if contract else 0
            if (replay.resources[SITE]["food"] != expected_market_food
                    or replay.resources[KEEPER]["food"] != expected_keeper_food
                    or replay.resources[SITE]["coin_copper"] != receipts * 2):
                raise AssertionError("final owned balances differ from sales/wage transfers")
            if store.db.execute("PRAGMA integrity_check").fetchone() != ("ok",):
                raise AssertionError("SQLite integrity check failed")
            if store.db.execute("PRAGMA foreign_key_check").fetchall():
                raise AssertionError("SQLite foreign key check failed")

            trade_identity_fields = (
                "offer_id", "buyer_id", "seller_id", "stock_owner_id", "site_id",
                "resource", "payment_resource", "unit_price", "quantity",
                "total_paid", "executed_at",
            )
            trade_identities = {
                ident: {key: trade[key] for key in trade_identity_fields}
                for ident, trade in replay.market_trades.items()
            }
            trade_digest = canonical_hash({
                "offers": dict(replay.market_offers),
                "trades": trade_identities,
            })
            rows = [json.loads(row[0]) for row in store.db.execute(
                "SELECT payload FROM events WHERE world_id=? ORDER BY seq", (WORLD,))]
            event_types = Counter(row["event_type"] for row in rows)
            return {
                "receipts": receipts,
                "contract": contract,
                "events": len(rows),
                "sales": len(replay.market_trades),
                "wages": len(paid),
                "opening_food": opening_food,
                "final_food": final_food,
                "opening_copper": opening_cash,
                "final_copper": final_cash,
                "market_food": replay.resources[SITE]["food"],
                "keeper_food": replay.resources[KEEPER]["food"],
                "market_cash": replay.resources[SITE]["coin_copper"],
                "trade_digest": trade_digest,
                "state_digest": canonical_hash(replay.to_dict()),
                "event_ledger_digest": canonical_hash(rows),
                "event_types": dict(sorted(event_types.items())),
                "append_seconds": append_seconds,
                "full_replay_seconds": replay_seconds,
                "append_payroll_scan_work": append_work,
                "replay_payroll_scan_work": replay_work,
            }


def _same_deterministic_result(samples: list[dict[str, Any]], label: str) -> None:
    for key in ("state_digest", "event_ledger_digest", "trade_digest", "events",
                "sales", "wages", "event_types"):
        if any(sample[key] != samples[0][key] for sample in samples[1:]):
            raise AssertionError(f"{label} runs diverged in {key}")


def measure(receipts: int, repeats: int) -> dict[str, Any]:
    controls = [run_sample(receipts, contract=False) for _ in range(repeats)]
    candidates = [run_sample(receipts, contract=True) for _ in range(repeats)]
    _same_deterministic_result(controls, "control")
    _same_deterministic_result(candidates, "contract")
    if controls[0]["trade_digest"] != candidates[0]["trade_digest"]:
        raise AssertionError("control and payroll scenarios changed real market trades")

    work = run_sample(receipts, contract=True, count_scans=True)
    return {
        "receipts": receipts,
        "sales": receipts * 2,
        "repeats": repeats,
        "repeatability_verified": True,
        "market_trade_parity": True,
        "state_digest_control": controls[0]["state_digest"],
        "state_digest_contract": candidates[0]["state_digest"],
        "trade_digest": controls[0]["trade_digest"],
        "event_ledger_digest_control": controls[0]["event_ledger_digest"],
        "event_ledger_digest_contract": candidates[0]["event_ledger_digest"],
        "median_append_seconds_control": round(
            median(sample["append_seconds"] for sample in controls), 6),
        "median_append_seconds_contract": round(
            median(sample["append_seconds"] for sample in candidates), 6),
        "median_full_replay_seconds_control": round(
            median(sample["full_replay_seconds"] for sample in controls), 6),
        "median_full_replay_seconds_contract": round(
            median(sample["full_replay_seconds"] for sample in candidates), 6),
        "payroll_scan_work": {
            "append": work["append_payroll_scan_work"],
            "full_replay": work["replay_payroll_scan_work"],
        },
        "finite_resources_conserved": True,
        "sqlite_replay_and_integrity": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipts", nargs="+", type=int, default=[1, 2, 4, 8, 16, 32],
                        help="finite keeper wages per world (default: 1,2,4,8,16,32)")
    parser.add_argument("--repeats", type=int, default=3,
                        help="independent worlds per control/candidate point (default: 3)")
    args = parser.parse_args()
    if (not args.receipts or any(type(value) is not int or not 1 <= value <= 128
                                 for value in args.receipts)
            or type(args.repeats) is not int or not 2 <= args.repeats <= 10):
        parser.error("receipts must be 1..128 and repeats must be 2..10")

    root = Path(__file__).resolve().parents[3]
    try:
        source_sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True,
            stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        source_sha = None
    print(json.dumps({
        "benchmark": "market-steward-payroll-history-v1",
        "source_sha": source_sha,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "scope": {
            "atomic_event_batch": True,
            "market_trades_per_receipt": 2,
            "opening_food_per_receipt": 3,
            "opening_operating_food": 1,
            "opening_copper_per_sale": 1,
            "systems": ["event-sourced market offers", "physical food trades",
                        "signed steward food payroll", "deterministic full replay"],
            "limits": ["synthetic finite benchmark genesis only",
                       "no engine rules or save schema changes",
                       "timings are diagnostic, not CI thresholds"],
        },
        "results": [measure(receipts, args.repeats) for receipts in args.receipts],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
