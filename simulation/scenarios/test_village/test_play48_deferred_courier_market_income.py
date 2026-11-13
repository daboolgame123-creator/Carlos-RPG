"""PLAY48: new genuinely *deferred* market courier wages (no opening stock escrow).

The market signs 0 up-front units and max 2 in a trusted, source-authenticated
time-zero contract, with original 13 NPC, 12 copper and 3 opening loaves.
This is only a contingent job: wages emerge from FUTURE delivered market
food, never from a stock/daily bonus. Compare exact same autonomous market,
biology, route schedule and engine config against control in one 48h A/B.
Even a successful market wage cannot alone prove 96/168h viability.
"""
from __future__ import annotations

import json
import pytest

from carlos_sim import DomainEvent, SQLiteEventStore, TimeEngine
from carlos_sim.store import InvalidEvent
from carlos_sim.economic_diagnostics import audit_npc_economy
from test_play38_multi_farm_couriers import WORLD
from test_play48_real_watch_income_24h import seed, engine, HOUR
from test_play48_finite_hunt_fish_roads import conserve_diverse
from test_play48_peddler_24h_diagnostic import measures


def signed_genesis(path, *, worker_ids=("hana", "huda")):
    opening = seed(path)
    assert len(opening.npcs) == 13
    assert opening.resources["market"]["food"] == 2
    with SQLiteEventStore(path) as db:
        original = db.verify(WORLD)
        events = [
            DomainEvent("CourierProvisionConfigured", None,
                "sign contingent market service - only later work can fund it", 0,
                {"id": "real-surplus-only-" + who, "courier_id": who,
                 "payer_site": "market", "units": 0, "authorized_total_units": 2})
            for who in worker_ids
        ]
        actual = db.append(WORLD, "signed-contingent-market-employment",
                           original.revision, events, bootstrap=True)
        assert actual.resources["market"]["food"] == 2
        assert actual.resources["bakery"]["food"] == 1
        assert sum(c["remaining"] for c in actual.courier_provisions.values()) == 0
        assert all(c["total_units"] == 0 and c["payments"] == ()
                   for c in actual.courier_provisions.values())
        assert audit_npc_economy(actual)["copper_known_total"] == 12
        assert db.verify(WORLD).to_dict() == actual.to_dict()
        conserve_diverse(actual)
        return actual


def _metrics(s):
    m = measures(s)
    m["hunger_of_couriers"] = {
        who: s.npcs[who]["needs"]["hunger"]
        for who in ("hana", "huda")
    }
    m["courier_meals"] = {
        who: sum(x["npc_id"] == who for x in s.consumptions.values())
        for who in ("hana", "huda")
    }
    m["wage_receipts"] = {
        who: [
            {"work_count": r["service_deliveries"], "paid_at": r["paid_at"]}
            for c in s.courier_provisions.values()
            if c["courier_id"] == who for r in c["payments"]
        ] for who in ("hana", "huda")
    }
    m["wage_escrow"] = {
        k: {"funded_total": c["total_units"],
            "remaining": c["remaining"],
            "ceiling": c["authorized_total_units"]}
        for k, c in sorted(s.courier_provisions.items())
    }
    m["personal_food"] = {
        who: s.resources[who]["food"]
        for who in ("hana", "huda")
    }
    m["market_food"] = s.resources["market"]["food"]
    m["bakery_food"] = s.resources["bakery"]["food"]
    return m


def _run(path, *, signed):
    initial = signed_genesis(path) if signed else seed(path)
    records = []
    with SQLiteEventStore(path) as db:
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            sim = engine(db, clock, reserve_trader_meal=True,
                         deferred_market_courier_wage=True)
            for hour in (6, 12, 24, 30, 36, 48):
                before = db.verify(WORLD)
                current = sim.advance(WORLD, seconds=hour*HOUR-before.time,
                    command_id=f"contingent-paid-courier:{signed}:{hour}",
                    expected_revision=before.revision).state
                conserve_diverse(current)
                assert db.verify(WORLD).to_dict() == current.to_dict()
                assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
                assert not db.db.execute("PRAGMA foreign_key_check").fetchall()
                audit = audit_npc_economy(current)
                assert audit["copper_scope_complete"]
                assert audit["copper_known_total"] == 12
                records.append(_metrics(current))
        finally:
            clock.close_session(WORLD)
    return initial, records


def test_48h_unpaid_initial_market_stall_preserved_then_true_revenue_earns_wage(tmp_path):
    original, control = _run(tmp_path / "control.sqlite", signed=False)
    promised, trial = _run(tmp_path / "deferred-funded-service.sqlite", signed=True)
    assert len(original.npcs) == len(promised.npcs) == 13
    assert audit_npc_economy(original)["copper_known_total"] == 12
    assert audit_npc_economy(promised)["copper_known_total"] == 12
    assert original.resources["market"]["food"] == promised.resources["market"]["food"] == 2
    assert original.resources["bakery"]["food"] == promised.resources["bakery"]["food"] == 1
    assert sum(p["remaining"] for p in promised.courier_provisions.values()) == 0
    print("PLAY48_DEFERRED_GENUINE_MARKET_COURIER_48H_AB " +
          json.dumps({"control":control,"contingent":trial},sort_keys=True),
          flush=True)
    assert trial[-1]["hour"] == 48
    assert trial[-1]["copper"] == 12
    assert trial[0]["food_eaten_meals"] == control[0]["food_eaten_meals"], (
        "zero-funded contracts must not remove existing starter meals"
    )
    assert trial[-1]["total_food_sales"] >= control[-1]["total_food_sales"], (
        "deferred salary must not choke authentic market sales"
    )
    # This may be a NEGATIVE outcome even if bookkeeping and replay pass:
    # a zero-funded contract can pay only if a new local unquoted surplus
    # arrives after genuine deliveries (never generate new goods).
    assert sum(len(v) for v in trial[-1]["wage_receipts"].values()) >= 1, (
        "no real signed market delivery produced a physically funded wage"
    )


def test_zero_funding_never_permits_rogue_receipt_or_nonmarket_employer(tmp_path):
    path = tmp_path / "forgery-no-loaf.sqlite"
    s = signed_genesis(path, worker_ids=("hana",))
    with SQLiteEventStore(path) as db:
        frozen = db.verify(WORLD).to_dict()
        with pytest.raises((ValueError, InvalidEvent)):
            db.append(WORLD, "fake-paid-no-service", s.revision, [
                DomainEvent("CourierProvisionPaid", None,
                    "pretend delivery to invent wage", 0,
                    {"id": "real-surplus-only-hana", "courier_id": "hana",
                     "service_deliveries": 1})
            ], supply_authorized=True)
        with pytest.raises((ValueError, InvalidEvent)):
            db.append(WORLD, "fake-funded-no-service", s.revision, [
                DomainEvent("CourierProvisionReplenished", None,
                    "pretend employer funding", 0,
                    {"id": "real-surplus-only-hana", "courier_id": "hana",
                     "service_deliveries": 1})
            ], supply_authorized=True)
        assert db.verify(WORLD).to_dict() == frozen
