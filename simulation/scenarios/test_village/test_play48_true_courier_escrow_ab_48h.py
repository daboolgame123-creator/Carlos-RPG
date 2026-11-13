"""PLAY48: can two genuinely pre-funded couriers earn edible food before 48h?

Diagnostic-only exact-source A/B. The 13 NPC, physical food totals (3
initial loaves), two-farm land and 12 initial copper are identical.
Treatment signs TWO separate one-loaf work contracts against actual site-
owned food: 1 real market loaf for Hana's delivered market food, and
1 bakery loaf for Huda's actually delivered bakery grain. No free wage,
fake trade, pre-scripted delivery or replenishment. The alternate
stock/escrow allocation is disclosed. Negative economics => NO MERGE.
"""
from __future__ import annotations

import json
import pytest

from carlos_sim import DomainEvent, SQLiteEventStore, TimeEngine
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.store import InvalidEvent
from test_play38_multi_farm_couriers import WORLD
from test_play48_real_watch_income_24h import seed, engine, HOUR
from test_play48_finite_hunt_fish_roads import conserve_diverse
from test_play48_peddler_24h_diagnostic import measures


def _sign_funded_work(path):
    opening = seed(path)
    assert opening.resources["market"]["food"] == 2
    assert opening.resources["bakery"]["food"] == 1
    assert opening.courier_provisions == {}
    with SQLiteEventStore(path) as db:
        start = db.verify(WORLD)
        signed = db.append(
            WORLD, "signed-real-site-courier-escrows", start.revision,
            [DomainEvent(
                "CourierProvisionConfigured", None,
                "pre-funded local authentic market food-delivery service", 0,
                {"id": "signed-hana-market", "courier_id": "hana",
                 "payer_site": "market", "units": 1},
            ), DomainEvent(
                "CourierProvisionConfigured", None,
                "pre-funded local authentic bakery grain-delivery service", 0,
                {"id": "signed-huda-bakery", "courier_id": "huda",
                 "payer_site": "bakery", "units": 1},
            )], bootstrap=True,
        )
        assert signed.resources["market"]["food"] == 1
        assert signed.resources["bakery"]["food"] == 0
        assert sum(c["remaining"] for c in signed.courier_provisions.values()) == 2
        assert sum(b.get("food", 0) for b in signed.resources.values()) + 2 == 3
        assert audit_npc_economy(signed)["copper_known_total"] == 12
        conserve_diverse(signed)
        assert db.verify(WORLD).to_dict() == signed.to_dict()
        return signed


def _measure(s):
    out = measures(s)
    out["courier_hunger"] = {
        who: s.npcs[who]["needs"]["hunger"] for who in ("hana", "huda")
    }
    out["courier_personal_food"] = {
        who: s.resources[who].get("food", 0) for who in ("hana", "huda")
    }
    out["courier_meals"] = {
        who: sum(m["npc_id"] == who for m in s.consumptions.values())
        for who in ("hana", "huda")
    }
    out["real_courier_salary_receipts"] = {
        who: [
            {"contract": ident, "service": row["service_deliveries"],
             "paid_at": row["paid_at"]}
            for ident, c in sorted(s.courier_provisions.items())
            if c["courier_id"] == who for row in c["payments"]
        ] for who in ("hana", "huda")
    }
    out["signed_work_escrow"] = {
        cid: {"remaining": c["remaining"], "total": c["total_units"]}
        for cid, c in sorted(s.courier_provisions.items())
    }
    out["market_site_food"] = s.resources["market"]["food"]
    out["bakery_site_food"] = s.resources["bakery"]["food"]
    return out


def _run(path, *, signed):
    if signed:
        opening = _sign_funded_work(path)
    else:
        opening = seed(path)
    rows = []
    with SQLiteEventStore(path) as db:
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            # Identical engine and flags in both worlds. With no signed
            # provisions the control cannot earn imaginary courier wages.
            world = engine(db, clock, reserve_trader_meal=True)
            world.early_courier_food_wage_enabled = True
            for hour in (6, 12, 24, 30, 36, 48):
                prev = db.verify(WORLD)
                s = world.advance(
                    WORLD, seconds=hour*HOUR-prev.time,
                    command_id=f"site-funded-courier-a-b:{signed}:{hour}",
                    expected_revision=prev.revision,
                ).state
                assert s.time == hour*HOUR
                assert len(s.npcs) == 13
                conserve_diverse(s)
                cash = audit_npc_economy(s)
                assert cash["copper_scope_complete"]
                assert cash["copper_known_total"] == 12
                assert db.verify(WORLD).to_dict() == s.to_dict()
                assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
                assert not db.db.execute("PRAGMA foreign_key_check").fetchall()
                rows.append(_measure(s))
        finally:
            clock.close_session(WORLD)
    return opening, rows


def test_48h_same_physical_budgets_early_signed_service_payments(tmp_path):
    orig, control = _run(tmp_path / "original-owned-food.sqlite", signed=False)
    treatment_start, treatment = _run(
        tmp_path / "signed-real-food-wage.sqlite", signed=True)
    assert set(orig.npcs) == set(treatment_start.npcs)
    assert audit_npc_economy(orig)["copper_known_total"] == 12
    assert audit_npc_economy(treatment_start)["copper_known_total"] == 12
    assert sum(b.get("food", 0) for b in orig.resources.values()) == 3
    assert (sum(b.get("food", 0) for b in
                treatment_start.resources.values()) +
            sum(c["remaining"] for c in
                treatment_start.courier_provisions.values())) == 3
    print("PLAY48_ACTUAL_SITE_FUNDED_TWO_COURIERS_48H_AB " +
          json.dumps({"control": control, "funded": treatment},
                     sort_keys=True), flush=True)
    assert treatment[-1]["copper"] == 12
    assert treatment[-1]["hour"] == 48
    # Hard acceptance gate: a signed promise without any real delivered
    # service cannot count as livelihood recovery.
    assert any(treatment[-1]["real_courier_salary_receipts"][w]
               for w in ("hana", "huda")), (
        "neither courier earned a real delivery-backed food wage by 48h"
    )


def test_fake_courier_wage_without_completed_delivery_fails_closed(tmp_path):
    path = tmp_path / "fake-courier-wage.sqlite"
    _sign_funded_work(path)
    with SQLiteEventStore(path) as db:
        s = db.verify(WORLD)
        with pytest.raises((ValueError, InvalidEvent)):
            db.append(WORLD, "fake-wage-no-real-truck", s.revision, [
                DomainEvent(
                    "CourierProvisionPaid", None, "counterfeit service", 0,
                    {"id": "signed-hana-market", "courier_id": "hana",
                     "service_deliveries": 1},
                )
            ], supply_authorized=True)
        assert db.verify(WORLD).to_dict() == s.to_dict()
