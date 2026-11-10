"""PLAY-48H1: real escrowed food wage proof on the genuine thirteen-person world.

The professional courier's market delivery is the service proof. The market
contributes existing food to a time-zero contract, with no extra wallets,
harvests, actors or helper routes. A green 24h prototype is NOT 96h recovery.
"""
from __future__ import annotations

import json

import pytest

from carlos_sim import DomainEvent, LivingWorldEngine, SQLiteEventStore, TimeEngine
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.food_security_audit import audit_food_security
from carlos_sim.hydrology import FiniteWaterService
import test_play39_rain_drought_real_day as reference
from carlos_sim.store import InvalidEvent, DuplicateCommand
from test_play47_closure_endurance import _seed, WORLD, DAY
from test_play47_joined_professions import _engine


def _sign(db, *, workers=("huda", "hana"), units=1):
    start = db.load(WORLD)
    assert start.time == 0
    events = [
        DomainEvent("CourierProvisionConfigured", None,
                    "explicit employer-owned pre-funded time-zero food contract", 0,
                    {"id": "food-wage-" + who,
                     "courier_id": who, "payer_site": "market",
                     "units": units})
        for who in workers
    ]
    return db.append(WORLD, "h1:funded-contract", start.revision,
                     events, bootstrap=True)


def test_h1_two_real_courier_contracts_reserve_existing_market_bread(tmp_path):
    path = tmp_path / "real-13npc-provision-wages.sqlite"
    # _seed initializes and closes the original 13-NPC physical world.
    initial = _seed(path)
    assert initial.resources["market"]["food"] == 3
    assert len(initial.npcs) == 13
    with SQLiteEventStore(path) as db:
        ready = _sign(db)
        assert ready.resources["market"]["food"] == 1
        assert sum(c["remaining"] for c in ready.courier_provisions.values()) == 2
        assert audit_npc_economy(ready)["copper_known_total"] == 12
        assert audit_food_security(ready).known_site_food_units >= 3
        assert db.verify(WORLD).to_dict() == ready.to_dict()
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            engine = _engine(db, clock, shopping=True)
            # Genuine food-delivery receipts first appear after 24h rain.
            for target in (DAY, DAY + DAY // 4, DAY + DAY // 2):
                state = db.load(WORLD)
                state = engine.advance(
                    WORLD, seconds=target - state.time,
                    command_id=f"h1:progress:{target}",
                    expected_revision=state.revision).state
                assert state.time == target
                if target == DAY:
                    state = FiniteWaterService(db, clock).record(
                        WORLD, "well", f"observed-rain-{DAY}", 2,
                        command_id=f"rain-{DAY}", expected_revision=state.revision,
                    ).state
                assert audit_npc_economy(state)["copper_known_total"] == 12
                assert db.snapshot(WORLD).to_dict() == state.to_dict()
        finally:
            clock.close_session(WORLD)
        stored = db.verify(WORLD)
        assert stored.to_dict() == state.to_dict()
        paid = [(cid, receipt) for cid, c in stored.courier_provisions.items()
                for receipt in c["payments"]]
        assert paid, "No real market food delivery earned a food wage by 36h"
        for cid, receipt in paid:
            c = stored.courier_provisions[cid]
            assert receipt["service_deliveries"] <= stored.supply_circuits[c["courier_id"]]["deliveries"]
            assert receipt["worker_food_after"] == receipt["worker_food_before"] + 1
        reserved = sum(c["remaining"] for c in stored.courier_provisions.values())
        assert reserved + len(paid) == 2
        # An independent event-log check proves every wage immediately follows
        # a legitimate courier food-delivery event, with matching actor/time.
        recorded = [json.loads(row[0]) for row in db.db.execute(
            "SELECT payload FROM events WHERE world_id=? ORDER BY seq", (WORLD,)
        )]
        payment_events = [i for i, event in enumerate(recorded)
                          if event["event_type"] == "CourierProvisionPaid"]
        assert len(payment_events) == len(paid)
        for i in payment_events:
            assert i > 0
            delivery, wage = recorded[i - 1], recorded[i]
            assert delivery["event_type"] == "SupplyCargoDelivered"
            assert delivery["data"]["resource"] == "food"
            assert delivery["data"]["courier_id"] == wage["data"]["courier_id"]
            assert delivery["time"] == wage["time"]
        # The employer's withheld escrow still exists, but no longer sits in
        # the saleable market resource slot. Include it exactly once.
        stock = stored.resources
        food = sum(bal.get("food", 0) for bal in stock.values()) + reserved
        grain = sum(bal.get("grain", 0) for bal in stock.values())
        consumed = sum(m["quantity"] for m in stored.consumptions.values())
        pending_bakes = sum(
            stored.production_recipes[j["recipe_id"]]["input_amount"]
            for j in stored.production_jobs.values()
            if j["status"] == "running"
            and stored.production_recipes[j["recipe_id"]]["output_resource"] == "food")
        reserved_harvest = sum(
            reference.CROP_YIELD[j["site_id"]]
            for j in stored.production_jobs.values()
            if j["status"] == "running"
            and stored.production_recipes[j["recipe_id"]]["input_resource"] == "crop_ready")
        ripe = sum(stock[field]["crop_ready"] * reference.CROP_YIELD[field]
                   for field in reference.CROP_YIELD)
        grown = sum(plot["matured"] * reference.CROP_YIELD[field]
                    for field, plot in stored.farm_plots.items())
        assert food + grain + consumed + pending_bakes + reserved_harvest + ripe == reference.START_FOOD + grown
        assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
    with SQLiteEventStore(path) as db:
        assert db.verify(WORLD).to_dict() == stored.to_dict()
    print("PLAY48H1_EARLY_SERVICE", json.dumps({
        "real_worker_wage_count": len(paid),
        "signed_escrow_units": 2,
        "unpaid_escrow_units": sum(c["remaining"] for c in stored.courier_provisions.values()),
        "post72_recovery_proven": False,
        "copper": audit_npc_economy(stored)["copper_known_total"],
    }, sort_keys=True))


@pytest.mark.parametrize("bad_workers,bad_units", [
    (("huda", "hana"), 2),     # would cost 4 when only 3 site loaves exist
    (("huda",), 4),           # unbounded employment promise
    (("huda", "huda"), 1),    # duplicate worker entitlement
    (("unknown",), 1),       # fabricated worker
])
def test_h1_invalid_contracts_are_atomic(tmp_path, bad_workers, bad_units):
    path = tmp_path / "bad-contract.sqlite"
    _seed(path)
    with SQLiteEventStore(path) as db:
        before = db.verify(WORLD).to_dict()
        with pytest.raises((InvalidEvent, ValueError)):
            _sign(db, workers=bad_workers, units=bad_units)
        assert db.verify(WORLD).to_dict() == before


def test_h1_wage_requires_same_command_delivery_and_trusted_supply(tmp_path):
    path = tmp_path / "forgery.sqlite"
    _seed(path)
    with SQLiteEventStore(path) as db:
        s = _sign(db, workers=("huda",))
        before = db.verify(WORLD).to_dict()
        forged = DomainEvent("CourierProvisionPaid", None,
                             "try to fabricate an already-paid delivery", 0,
                             {"id": "food-wage-huda", "courier_id": "huda",
                              "service_deliveries": 3})
        with pytest.raises((InvalidEvent, ValueError)):
            db.append(WORLD, "forged-service-proof", s.revision, [forged],
                      supply_authorized=True)
        assert db.verify(WORLD).to_dict() == before
        assert s.resources["market"]["food"] == 2


def test_h1_genuine_old_42_57_save_refused_untouched(tmp_path, monkeypatch):
    """CI supplies a REAL 42/57 engine checkout; no fake version-header edits."""
    import os
    import sys
    import hashlib
    import subprocess
    from carlos_sim.store import UnsupportedVersion

    src = os.environ.get("PLAY48H_LEGACY_SRC")
    if not src:
        pytest.skip("genuine old runtime supplied by targeted Actions checkout")
    path = tmp_path / "old-42-57.sqlite"
    code = ("from carlos_sim import SQLiteEventStore; "
            f"db=SQLiteEventStore({str(path)!r}); "
            "db.create_world('old-historical'); db.close()")
    env = dict(os.environ, PYTHONPATH=src)
    subprocess.run([sys.executable, "-c", code], env=env, check=True)
    original = hashlib.sha256(path.read_bytes()).hexdigest()
    with SQLiteEventStore(path) as db:
        with pytest.raises(UnsupportedVersion):
            db.load("old-historical")
    assert hashlib.sha256(path.read_bytes()).hexdigest() == original
