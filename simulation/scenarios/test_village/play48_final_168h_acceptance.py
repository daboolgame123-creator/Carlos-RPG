"""PLAY48 final bounded acceptance: one genuine 13-NPC world to 168h.

The world is the PLAY48 PR #90 candidate (one original farm loaf signed to
Huda, one original market loaf signed to Hana, twelve conserved copper).
Nothing is minted, teleported or granted by this harness.  It only advances
the ordinary engine in six-hour slices, records the physical ledger and
checks SQLite persistence, replay, conservation and payment provenance.

A green run is NOT evidence of economic recovery by itself.  The verdict is
driven by post-72h production, deliveries, wages, sales, meals and whether
any resident is still physically able to buy bread at 168h.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from carlos_sim import SQLiteEventStore
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.food_access_diagnostics import audit_food_access_barriers
from play48_preserved_market_opening_split_wages_ab import _seed_split
from test_play48_13npc_post72_relay import _stats
from test_play48h3_early_market_wage import _conserve, _run
from test_play47_closure_endurance import DAY, WORLD

HOUR = 3600
CHECKPOINTS = (24, 48, 72, 96, 168)


def _production_since(state, since: int) -> dict:
    food_units = grain_units = 0
    food_jobs = grain_jobs = 0
    for job in state.production_jobs.values():
        if job["status"] != "completed" or job["finished_at"] is None:
            continue
        if job["finished_at"] <= since:
            continue
        recipe = state.production_recipes[job["recipe_id"]]
        if recipe["output_resource"] == "food":
            food_jobs += 1
            food_units += recipe["output_amount"]
        elif recipe["output_resource"] == "grain":
            grain_jobs += 1
            grain_units += recipe["output_amount"]
    return {
        "bread_jobs": food_jobs,
        "bread_units": food_units,
        "grain_jobs": grain_jobs,
        "grain_units": grain_units,
    }


def _resource_ledgers(state) -> dict:
    food = {owner: stock.get("food", 0)
            for owner, stock in sorted(state.resources.items())
            if stock.get("food", 0)}
    coin = {owner: stock.get("coin_copper", 0)
            for owner, stock in sorted(state.resources.items())
            if stock.get("coin_copper", 0)}
    grain = {owner: stock.get("grain", 0)
             for owner, stock in sorted(state.resources.items())
             if stock.get("grain", 0)}
    water = {owner: stock.get("water", 0)
             for owner, stock in sorted(state.resources.items())
             if stock.get("water", 0)}
    return {
        "food_by_owner": food,
        "coin_by_owner": coin,
        "grain_by_owner": grain,
        "water_by_owner": water,
        "food_total": sum(food.values()),
        "coin_total": sum(coin.values()),
        "grain_total": sum(grain.values()),
        "water_total": sum(water.values()),
        "food_in_courier_escrow": sum(
            c["remaining"] for c in state.courier_provisions.values()),
    }


def _per_npc(state) -> list[dict]:
    audit = audit_food_access_barriers(state)
    return [{
        "npc": actor["npc_id"],
        "role": actor["role"],
        "location": actor["location"],
        "hunger": actor["hunger"],
        "fatigue": actor["fatigue"],
        "personal_food": actor["known_personal_food"],
        "copper_slot": actor["copper_slot"],
        "copper_scope": actor["copper_scope"],
        "spendable_copper": actor["personally_spendable_copper"],
        "at_market": actor["at_market"],
        "known_route_to_market": actor["known_road_path_to_market"],
        "affordable_bread_now": actor["locally_affordable_now"],
    } for actor in audit["actors"]]


def _snapshot(state, since: int) -> dict:
    stats = _stats(state)
    food_audit = audit_food_access_barriers(state)
    return {
        "time_hours": state.time / HOUR,
        "stats": stats,
        "production_since_previous": _production_since(state, since),
        "hunger_at_100": food_audit["hunger_at_100"],
        "residents_with_any_food": sum(
            (actor["known_personal_food"] or 0) > 0
            for actor in food_audit["actors"]),
        "residents_personally_affordable_now": sum(
            actor["locally_affordable_now"] for actor in food_audit["actors"]),
        "open_food_offers": food_audit["opening_food_offer_count_currently_open"],
        "per_npc": _per_npc(state),
        "ledger": _resource_ledgers(state),
        "signed_food_wages_paid": {
            worker: sum(len(c["payments"])
                        for c in state.courier_provisions.values()
                        if c["courier_id"] == worker)
            for worker in ("hana", "huda")},
        "copper_audit": audit_npc_economy(state),
    }


def _db_checks(path: Path, expected) -> dict:
    with SQLiteEventStore(path) as db:
        assert db.verify(WORLD).to_dict() == expected.to_dict()
        integrity = db.db.execute("PRAGMA integrity_check").fetchone()
        foreign = db.db.execute("PRAGMA foreign_key_check").fetchall()
        events = [json.loads(row[0]) for row in db.db.execute(
            "SELECT payload FROM events WHERE world_id=? ORDER BY seq",
            (WORLD,))]
    paid = [e for e in events if e["event_type"] == "CourierProvisionPaid"]
    delivered = [e for e in events
                 if e["event_type"] == "SupplyCargoDelivered"]
    for n, event in enumerate(events):
        if event["event_type"] != "CourierProvisionPaid":
            continue
        earlier = [e for e in events[:n]
                   if e["event_type"] == "SupplyCargoDelivered"
                   and e["data"]["courier_id"] == event["data"]["courier_id"]
                   and e["time"] <= event["time"]]
        assert earlier, "food wage paid without a real delivery"
        assert event["data"]["service_deliveries"] <= len(earlier)
    return {
        "integrity_check": integrity[0] if integrity else None,
        "foreign_key_violations": len(foreign),
        "event_rows": len(events),
        "courier_food_payments": len(paid),
        "real_deliveries_logged": len(delivered),
    }


def _verdict(rows: list[dict], final) -> dict:
    stats = final["stats"]
    # The first checkpoint is 24h; always have a real pre-72 baseline.
    at72 = next((row for row in rows if row["time_hours"] == 72.0), rows[0])
    baseline_hour = at72["time_hours"]
    stats72 = at72["stats"]

    # Cumulative counters: subtract the real 72h reading, never mint a baseline.
    def delta(key):
        return stats[key] - stats72.get(key, 0)

    post = {
        "jobs": delta("jobs"),
        "wages": delta("wages"),
        "food_sales": delta("food_sales"),
        "meals": delta("meals"),
        "trades": delta("trades"),
        "hana_deliveries": (stats["deliveries"]["hana"]
                            - stats72.get("deliveries", {}).get("hana", 0)),
        "huda_deliveries": (stats["deliveries"]["huda"]
                            - stats72.get("deliveries", {}).get("huda", 0)),
        "bread_units": sum(
            row["production_since_previous"]["bread_units"]
            for row in rows if row["time_hours"] > baseline_hour),
        "grain_units": sum(
            row["production_since_previous"]["grain_units"]
            for row in rows if row["time_hours"] > baseline_hour),
    }
    gates = {
        "post72_bread_or_grain_production":
            post["bread_units"] + post["grain_units"] > 0,
        "post72_meals": post["meals"] > 0,
        "post72_food_sales": post["food_sales"] > 0,
        "post72_wages": post["wages"] > 0,
        "post72_courier_deliveries":
            post["hana_deliveries"] + post["huda_deliveries"] > 0,
        "no_resident_starving_at_168": final["hunger_at_100"] == 0,
        "some_resident_can_buy_bread_at_168":
            final["residents_personally_affordable_now"] > 0,
        "copper_conserved_12":
            final["copper_audit"].get("copper_known_total") == 12,
        "food_not_minted": True,  # asserted by _conserve on every slice
    }
    return {
        "post72_deltas": post,
        "gates": gates,
        "go": all(gates.values()),
        "basis": "physical engine counters and ledgers, not CI green",
    }


def run(path: Path, hours: int) -> None:
    path = path.resolve()
    seeded = False
    if path.exists():
        try:
            with SQLiteEventStore(path) as db:
                first = db.load(WORLD).time // HOUR
            seeded = True
        except KeyError:
            seeded = False
    if not seeded:
        _seed_split(path)
        first = 0
    rows: list[dict] = []
    previous_hour = first
    for hour in (h for h in CHECKPOINTS if first < h <= hours):
        state, _ = _run(
            path, hour * HOUR, early=True,
            hungry_woodcutter_work_enabled=True,
            retry_known_supplier_enabled=True,
            farm_sourced_wage_refill_enabled=True,
            remember_unbought_stalls_enabled=True,
        )
        _conserve(state)
        checks = _db_checks(path, state)
        row = _snapshot(state, previous_hour * HOUR)
        row["db"] = checks
        rows.append(row)
        print("PLAY48_FINAL_168H_CHECKPOINT " + json.dumps(row,
              sort_keys=True), flush=True)
        previous_hour = hour
    if not rows:
        raise SystemExit("no checkpoint reached; pass a larger --hours")
    verdict = _verdict(rows, rows[-1])
    verdict.update({
        "world": str(path),
        "checkpoints": [row["time_hours"] for row in rows],
        "npcs": len(rows[-1]["per_npc"]),
        "python": __import__("sys").version.split()[0],
    })
    print("PLAY48_FINAL_168H_VERDICT " + json.dumps(verdict,
          sort_keys=True), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="play48_final_168h.sqlite")
    parser.add_argument("--hours", type=int, default=168)
    args = parser.parse_args()
    run(Path(args.db), args.hours)
