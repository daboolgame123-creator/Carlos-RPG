"""Independent PLAY48 pilot: preserve previously working Huda food livelihood.

No new physics or additional starting goods. Long-run economic acceptances
remain the authoritative original 13-NPC A/B gates, not these seed tests.
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


@pytest.fixture
def arms(tmp_path):
    control = seed(tmp_path / "control.sqlite", candidate=False)
    candidate = seed(tmp_path / "candidate.sqlite", candidate=True)
    return tmp_path, control, candidate


def test_opening_owned_assets_and_huda_provision_match_control(arms):
    _, a, b = arms
    for field in ("resources", "entities", "npcs", "routes",
                  "metabolism_policy", "farm_plots"):
        assert getattr(a, field) == getattr(b, field)
    assert len(a.npcs) == len(b.npcs) == 13
    assert audit_npc_economy(a)["copper_known_total"] == 12
    assert audit_npc_economy(b)["copper_known_total"] == 12
    assert a.supply_circuits["huda"] == b.supply_circuits["huda"]
    assert "food_payroll" not in b.supply_circuits["huda"]
    for w in (a, b):
        old = w.courier_provisions["huda-future-bakery"]
        assert old["courier_id"] == "huda"
        assert old["payer_site"] == "bakery"
        assert old["authorized_total_units"] == 2
        # The persisted projection stores *the earned service ledger*, not
        # the bootstrap-only option name; frozen sequences become tuples.
        assert "deferred_bakery_grain" not in old
        assert old["payments"] == ()
        assert old["deferred_grain_services"] == ()


def test_nora_and_hana_independent_without_double_claim(arms):
    _, a, b = arms
    assert "wage_coin" not in a.production_recipes["finite-harvest"]
    assert b.production_recipes["finite-harvest"]["wage_coin"] == 2
    assert "food_payroll" not in a.supply_circuits["hana"]
    assert b.supply_circuits["hana"]["food_payroll"] == {
        "site_id": "market", "resource": "food",
        "interval_seconds": 18 * 3600, "receipts": (),
    }
    assert sum(x.get("food", 0) for x in b.resources.values()) == 3


def test_no_forged_huda_grain_wage_or_overlapping_recurring_contract(arms):
    tmp, _, s = arms
    with SQLiteEventStore(tmp / "candidate.sqlite") as db:
        with pytest.raises(InvalidEvent):
            db.append(WORLD, "fake-huda-grain-wage", s.revision, [
                DomainEvent("CourierBakeryDeferredFoodPaid", None, "no grain delivered",
                            0, {"id": "fake", "courier_id": "huda",
                                "service_deliveries": 1, "amount": 1}),
            ], supply_authorized=True, production_authorized=True)
        with pytest.raises(InvalidEvent):
            db.append(WORLD, "double-huda-contract", s.revision, [
                DomainEvent("RecurringFreightWageSigned", None, "overlap",
                            0, {"courier_id": "huda", "site_id": "bakery",
                                "resource": "grain", "interval_seconds": 18 * 3600}),
            ], bootstrap=True)
        assert db.verify(WORLD).to_dict() == s.to_dict()
