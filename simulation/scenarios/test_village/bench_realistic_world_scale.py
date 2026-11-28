"""Repeatable multi-sector benchmark for the event-sourced living world.

This is an opt-in local benchmark, not a gameplay test or a capacity promise.
Each isolated sector has a finite woodcutting -> charcoal supply chain, funded
piece-rate wages, one real road, owned food for eating, and two co-located
residents for recorded NPC speech. The sector bootstrap is explicit and all
runtime changes still pass through the normal SQLite event engine.

Run from ``simulation`` with::

    PYTHONPATH=src python scenarios/test_village/bench_realistic_world_scale.py

Timings have no hardware-dependent pass threshold. Compare runs on the same
machine, Python build, source SHA, sector count, and simulated duration.
"""
from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from collections import Counter
from pathlib import Path
from statistics import median
from tempfile import TemporaryDirectory
from time import perf_counter

from carlos_sim import DomainEvent, LivingWorldEngine, SQLiteEventStore, TimeEngine
from carlos_sim import canonical_hash

WORLD = "realistic-world-scale"


def _event(kind: str, data: dict, actor: str | None = None) -> DomainEvent:
    return DomainEvent(kind, actor, "finite benchmark scenario bootstrap", 0, data)


def _ids(sector: int) -> dict[str, str]:
    prefix = f"sector-{sector:03d}"
    return {
        "square": f"{prefix}-square",
        "forest": f"{prefix}-forest",
        "kiln": f"{prefix}-kiln",
        "woodcutter": f"{prefix}-woodcutter",
        "burner": f"{prefix}-charcoal-burner",
        "resident_a": f"{prefix}-resident-a",
        "resident_b": f"{prefix}-resident-b",
        "forest_route": f"{prefix}-forest-kiln-road",
        "wood_recipe": f"{prefix}-finite-wood",
        "charcoal_recipe": f"{prefix}-finite-charcoal",
    }


def seed_world(store: SQLiteEventStore, sectors: int, batch_units: int) -> None:
    """Create isolated, equally funded sectors using only time-zero seed stock."""
    store.create_world(WORLD)
    events: list[DomainEvent] = []
    for index in range(sectors):
        ident = _ids(index)
        for key, label in (("square", "sector square"), ("forest", "finite forest"),
                           ("kiln", "charcoal kiln")):
            events.append(_event("LocationCreated", {
                "id": ident[key], "name": f"{label} {index + 1}",
            }))
        events.append(_event("RouteCreated", {
            "id": ident["forest_route"], "a": ident["forest"],
            "b": ident["kiln"], "seconds": 35,
        }))
        people = (
            ("woodcutter", "woodcutter", ident["forest"]),
            ("burner", "charcoal_burner", ident["kiln"]),
            ("resident_a", "villager", ident["square"]),
            ("resident_b", "villager", ident["square"]),
        )
        for key, role, location in people:
            npc_id = ident[key]
            events.extend((
                _event("EntityCreated", {
                    "id": npc_id, "name": npc_id, "location_id": location,
                    "controller": "npc",
                }),
                _event("NPCConfigured", {
                    "npc_id": npc_id, "role": role,
                    "needs": {"hunger": 60, "fatigue": 5, "safety": 0},
                    "goals": {"earn": 10, "explore": 5, "survive": 30},
                }),
            ))
            initial = {
                "food": 1,
                "labor_units": 0,
                "investigation_attempts": 0,
            }
            for resource, quantity in initial.items():
                events.append(_event("ResourceChanged", {
                    "owner_id": npc_id, "resource": resource,
                    "previous": None, "current": quantity,
                    "source": "initialization",
                }))

        # The forest can fund exactly batch_units woodcutting jobs at 2 copper
        # each. The kiln can fund exactly batch_units charcoal jobs at 1 each;
        # the burner starts with enough finite copper to buy each wood unit.
        for owner, stock in (
            (ident["forest"], {
                "standing_timber": batch_units, "wood": 0, "axe": 1,
                "coin_copper": 2 * batch_units,
            }),
            (ident["kiln"], {
                "wood": 0, "charcoal": 0, "kiln_tool": 1,
                "coin_copper": batch_units,
            }),
            (ident["woodcutter"], {"coin_copper": 0}),
            (ident["burner"], {"wood": 0, "coin_copper": batch_units}),
        ):
            for resource, quantity in stock.items():
                events.append(_event("ResourceChanged", {
                    "owner_id": owner, "resource": resource,
                    "previous": None, "current": quantity,
                    "source": "initialization",
                }))

        events.extend((
            _event("MarketStallConfigured", {
                "site_id": ident["forest"], "keeper_id": ident["woodcutter"],
            }),
            _event("MarketStallConfigured", {
                "site_id": ident["kiln"], "keeper_id": ident["burner"],
            }),
            _event("NPCRoutineConfigured", {
                "npc_id": ident["woodcutter"], "home_id": ident["square"],
                "workplace_id": ident["forest"], "work_start": 0,
                "work_end": 20_000,
            }),
            _event("NPCRoutineConfigured", {
                "npc_id": ident["burner"], "home_id": ident["square"],
                "workplace_id": ident["kiln"], "work_start": 0,
                "work_end": 20_000,
            }),
            _event("ProductionRecipeConfigured", {
                "id": ident["wood_recipe"], "site_id": ident["forest"],
                "role": "woodcutter", "input_resource": "standing_timber",
                "input_amount": 1, "output_resource": "wood",
                "output_amount": 1, "tool_resource": "axe",
                "duration_seconds": 120, "wage_coin": 2,
            }),
            _event("ProductionRecipeConfigured", {
                "id": ident["charcoal_recipe"], "site_id": ident["kiln"],
                "role": "charcoal_burner", "input_resource": "wood",
                "input_amount": 1, "output_resource": "charcoal",
                "output_amount": 1, "tool_resource": "kiln_tool",
                "duration_seconds": 120, "wage_coin": 1,
            }),
        ))

    # One player entity keeps the world shape relevant to Carlos's simulation
    # while the benchmark measures population as NPC count (4 per sector).
    first_square = _ids(0)["square"]
    events.append(_event("EntityCreated", {
        "id": "carlos", "name": "Carlos", "location_id": first_square,
        "controller": "player",
    }))
    store.append(WORLD, "benchmark:bootstrap", 0, events, bootstrap=True)


def _event_manifest(store: SQLiteEventStore) -> list[dict]:
    return [
        {"seq": seq, "command_id": command_id,
         "event": json.loads(payload), "hash": event_hash}
        for seq, command_id, payload, event_hash in store.db.execute(
            "SELECT seq, command_id, payload, hash FROM events "
            "WHERE world_id=? ORDER BY seq", (WORLD,),
        )
    ]


def _write_statement_count(statements: list[str]) -> int:
    writes = ("INSERT ", "UPDATE ", "DELETE ", "REPLACE ")
    return sum(statement.lstrip().upper().startswith(writes) for statement in statements)


def _total_resource(state, resource: str) -> int:
    return sum(balance.get(resource, 0) for balance in state.resources.values())


def run_sample(sectors: int, seconds: int, batch_units: int,
               checkpoint_seconds: int) -> dict:
    npc_count = sectors * 4
    with TemporaryDirectory(prefix="carlos-world-scale-") as temp:
        database = Path(temp) / "world.sqlite"
        with SQLiteEventStore(database) as store:
            seed_world(store, sectors, batch_units)
            clock = TimeEngine(store)
            clock.open_session(WORLD)
            engine = LivingWorldEngine(
                store, clock, max_events_per_advance=100_000,
                economic_enabled=True, agriculture_enabled=True,
                economy_only_enabled=False, navigation_enabled=True,
                routines_enabled=True, multi_professional_markets_enabled=True,
                compound_procurement_enabled=True, consumption_enabled=True,
                survival_enabled=True, supply_enabled=True,
                professional_full_life_enabled=True, social_enabled=True,
            )
            opening = store.load(WORLD)
            opening_copper = _total_resource(opening, "coin_copper")
            opening_personal_food = sum(
                opening.resources.get(npc_id, {}).get("food", 0)
                for npc_id in opening.npcs
            )
            trace: list[str] = []
            advance_seconds = 0.0
            advance_rows = 0
            snapshot_seconds = 0.0
            snapshot_rows = 0
            advance_commands = 0
            checkpoint_count = 0
            current = opening
            outcome = None
            while current.time < seconds:
                target = min(seconds, current.time + checkpoint_seconds)
                command_id = ("benchmark:advance" if advance_commands == 0 and target == seconds
                              else f"benchmark:advance:{target}")
                rows_before = store.db.total_changes
                store.db.set_trace_callback(trace.append)
                started = perf_counter()
                try:
                    outcome = engine.advance(
                        WORLD, seconds=target - current.time,
                        command_id=command_id,
                        expected_revision=current.revision,
                    )
                finally:
                    advance_seconds += perf_counter() - started
                    store.db.set_trace_callback(None)
                advance_rows += store.db.total_changes - rows_before
                advance_commands += 1
                current = outcome.state

                # A derived snapshot bounds replay for the next interval.
                # The independent genesis verification below remains intact.
                snapshot_rows_before = store.db.total_changes
                snapshot_started = perf_counter()
                store.snapshot(WORLD)
                snapshot_seconds += perf_counter() - snapshot_started
                snapshot_rows += store.db.total_changes - snapshot_rows_before
                checkpoint_count += 1
            if outcome is None:
                raise AssertionError("benchmark must advance positive logical time")
            advance_statements = _write_statement_count(trace)

            load_started = perf_counter()
            snapshot_state = store.load(WORLD)
            snapshot_load_seconds = perf_counter() - load_started
            if snapshot_state.to_dict() != outcome.state.to_dict():
                raise AssertionError("snapshot load changed the simulated world")

            replay_started = perf_counter()
            replay_state = store.verify(WORLD)
            full_replay_seconds = perf_counter() - replay_started
            if replay_state.to_dict() != outcome.state.to_dict():
                raise AssertionError("full event replay differs from advanced state")
            integrity = store.db.execute("PRAGMA integrity_check").fetchone()[0]
            if integrity != "ok":
                raise AssertionError(f"SQLite integrity_check returned {integrity!r}")

            final_copper = _total_resource(replay_state, "coin_copper")
            final_personal_food = sum(
                replay_state.resources.get(npc_id, {}).get("food", 0)
                for npc_id in replay_state.npcs
            )
            eaten_food = sum(meal["quantity"]
                             for meal in replay_state.consumptions.values())
            if final_copper != opening_copper:
                raise AssertionError("world copper changed during the benchmark")
            if final_personal_food + eaten_food != opening_personal_food:
                raise AssertionError("personal food was created or lost outside meals")

            manifest = _event_manifest(store)
            event_types = Counter(row["event"]["event_type"] for row in manifest)
            activity = {
                "npc_decisions": event_types["NPCDecisionRecorded"],
                "production_started": event_types["ProductionStarted"],
                "production_completed": sum(
                    job["status"] == "completed"
                    for job in outcome.state.production_jobs.values()
                ),
                "wages_paid": event_types["ProductionWagePaid"],
                "market_trades": event_types["MarketTradeExecuted"],
                "food_consumed": event_types["NPCFoodConsumed"],
                "social_messages_sent": event_types["SocialMessageSent"],
                "npc_travel_started": event_types["NPCTravelStarted"],
                "npc_travel_completed": sum(
                    trip["status"] == "arrived"
                    for trip in outcome.state.travels.values()
                ),
            }
            result = {
                "sectors": sectors,
                "npcs": npc_count,
                "locations": len(outcome.state.locations),
                "simulated_seconds": outcome.state.time,
                "revision": outcome.state.revision,
                "events": len(manifest),
                "activity": activity,
                "advance_commands": advance_commands,
                "snapshot_checkpoints": checkpoint_count,
                "opening_copper": opening_copper,
                "final_copper": final_copper,
                "opening_personal_food": opening_personal_food,
                "food_remaining_plus_eaten": final_personal_food + eaten_food,
                "state_digest": canonical_hash(outcome.state.to_dict()),
                "event_ledger_digest": canonical_hash(manifest),
                "advance_seconds": round(advance_seconds, 6),
                "advance_sqlite_rows_changed": advance_rows,
                "advance_sqlite_write_statements": advance_statements,
                "snapshot_write_seconds": round(snapshot_seconds, 6),
                "snapshot_sqlite_rows_changed": snapshot_rows,
                "snapshot_load_seconds": round(snapshot_load_seconds, 6),
                "full_replay_seconds": round(full_replay_seconds, 6),
                "sqlite_database_bytes": database.stat().st_size,
                "sqlite_integrity": integrity,
            }
            if not activity["npc_decisions"]:
                raise AssertionError("sample produced no autonomous NPC decisions")
            if not activity["production_completed"] or not activity["wages_paid"]:
                raise AssertionError(
                    "sample did not complete funded production work: "
                    f"activity={activity}, event_types={dict(event_types)}"
                )
            if not activity["market_trades"] or not activity["npc_travel_completed"]:
                raise AssertionError("sample did not exercise a real local material route")
            if not activity["food_consumed"] or not activity["social_messages_sent"]:
                raise AssertionError("sample did not exercise eating and recorded speech")
            return result


def measure(sectors: int, seconds: int, batch_units: int,
            checkpoint_seconds: int, repeats: int) -> dict:
    samples = [run_sample(sectors, seconds, batch_units, checkpoint_seconds)
               for _ in range(repeats)]
    for key in ("state_digest", "event_ledger_digest", "events", "activity"):
        if any(sample[key] != samples[0][key] for sample in samples[1:]):
            raise AssertionError(f"independent runs diverged for {key} at {sectors} sectors")
    return {
        "sectors": sectors,
        "npcs": sectors * 4,
        "advance_commands": samples[0]["advance_commands"],
        "snapshot_checkpoints": samples[0]["snapshot_checkpoints"],
        "repeats": repeats,
        "repeatability_verified": True,
        "state_digest": samples[0]["state_digest"],
        "event_ledger_digest": samples[0]["event_ledger_digest"],
        "events": samples[0]["events"],
        "activity": samples[0]["activity"],
        "median_advance_seconds": round(median(s["advance_seconds"] for s in samples), 6),
        "median_snapshot_load_seconds": round(median(s["snapshot_load_seconds"] for s in samples), 6),
        "median_full_replay_seconds": round(median(s["full_replay_seconds"] for s in samples), 6),
        "median_snapshot_write_seconds": round(median(s["snapshot_write_seconds"] for s in samples), 6),
        "advance_sqlite_rows_changed": samples[0]["advance_sqlite_rows_changed"],
        "advance_sqlite_write_statements": samples[0]["advance_sqlite_write_statements"],
        "snapshot_sqlite_rows_changed": samples[0]["snapshot_sqlite_rows_changed"],
        "sqlite_database_bytes": samples[0]["sqlite_database_bytes"],
        "simulated_seconds": seconds,
    }


def source_sha() -> str | None:
    repo_root = Path(__file__).resolve().parents[3]
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repo_root,
            text=True, stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sectors", nargs="+", type=int, default=[1, 2, 4, 8])
    parser.add_argument("--seconds", type=int, default=900,
                        help="fixed logical duration for every population (default: 900)")
    parser.add_argument("--batch-units", type=int, default=3,
                        help="finite timber units and exactly funded job cycles per sector")
    parser.add_argument("--checkpoint-seconds", type=int, default=21_600,
                        help="maximum logical seconds per advance before a derived snapshot (default: 6 hours)")
    parser.add_argument("--repeats", type=int, default=2,
                        help="fresh SQLite worlds per scale point; digests must match")
    args = parser.parse_args()
    if (not args.sectors or any(type(value) is not int or value < 1 for value in args.sectors)
            or type(args.seconds) is not int or args.seconds < 1
            or type(args.batch_units) is not int or not 1 <= args.batch_units <= 20
            or type(args.checkpoint_seconds) is not int or args.checkpoint_seconds < 1
            or type(args.repeats) is not int or args.repeats < 2):
        parser.error("sectors/seconds/checkpoint must be positive, batch-units 1..20, repeats at least 2")
    root = Path(__file__).resolve().parents[3]
    report = {
        "benchmark": "realistic-world-scale-v1",
        "source_sha": source_sha(),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "scope": {
            "duration_seconds": args.seconds,
            "checkpoint_interval_seconds": args.checkpoint_seconds,
            "npcs_per_sector": 4,
            "finite_timber_and_funded_job_cycles_per_sector": args.batch_units,
            "systems": ["autonomous decisions", "production", "funded wages",
                        "local material market", "road travel", "owned-food consumption",
                        "recorded NPC speech", "SQLite event replay and snapshot"],
            "limits": ["independent repeated sectors", "no shared-market contention",
                       "not a production capacity claim"],
        },
        "results": [
            measure(sectors, args.seconds, args.batch_units,
                    args.checkpoint_seconds, args.repeats)
            for sectors in args.sectors
        ],
    }
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
