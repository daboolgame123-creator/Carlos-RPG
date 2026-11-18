"""PLAY48 Rules71: genuine Huda in-kind service and farm grain sale can coexist.

The bakery owes the crop's owner *cash* only on physical grain shipment and
owes Huda food only on authenticated courier service. They are distinct.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from carlos_sim import DomainEvent, SQLiteEventStore
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.store import InvalidEvent

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scenarios" / "test_village"))
from play48_integrated_acceptance import WORLD, seed


def test_original_real_assets_and_separate_contracts(tmp_path):
    control = seed(tmp_path / "control.sqlite", candidate=False)
    candidate = seed(tmp_path / "candidate.sqlite", candidate=True)
    for field in ("resources", "entities", "npcs", "routes", "metabolism_policy", "farm_plots"):
        assert getattr(control, field) == getattr(candidate, field)
    assert len(candidate.npcs) == 13
    assert sum(stock.get("food", 0) for stock in candidate.resources.values()) == 3
    assert audit_npc_economy(candidate)["copper_known_total"] == 12
    assert candidate.courier_provisions["huda-future-bakery"] == control.courier_provisions["huda-future-bakery"]
    assert candidate.courier_provisions["huda-future-bakery"]["authorized_total_units"] == 2
    huda = candidate.supply_circuits["huda"]
    assert "food_payroll" not in huda
    assert huda["grain_purchase"]["unit_price"] == 1
    assert huda["grain_purchase"]["receipts"] == ()
    assert candidate.supply_circuits["hana"]["grain_purchase"]["unit_price"] == 1
    assert candidate.supply_circuits["hana"]["food_payroll"]["site_id"] == "market"
    assert candidate.production_recipes["finite-harvest"]["wage_coin"] == 2
    with SQLiteEventStore(tmp_path / "candidate.sqlite") as db:
        assert db.verify(WORLD).to_dict() == candidate.to_dict()


def test_huda_cannot_claim_unearned_food_or_double_sign(tmp_path):
    path = tmp_path / "candidate.sqlite"
    s = seed(path, candidate=True)
    with SQLiteEventStore(path) as db:
        with pytest.raises(InvalidEvent):
            db.append(WORLD, "forged-huda-loaf", s.revision, [
                DomainEvent("CourierBakeryDeferredFoodPaid", None, "false delivery",
                            0, {"id": "huda-future-bakery", "courier_id": "huda",
                                "service_deliveries": 1, "amount": 1}),
            ], supply_authorized=True, production_authorized=True)
        with pytest.raises(InvalidEvent):
            db.append(WORLD, "duplicate-huda-contract", s.revision, [
                DomainEvent("RecurringFreightWageSigned", None, "overlap", 0,
                            {"courier_id": "huda", "site_id": "bakery",
                             "resource": "grain", "interval_seconds": 18 * 3600}),
            ], bootstrap=True)
        assert db.verify(WORLD).to_dict() == s.to_dict()
