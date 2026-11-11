"""PLAY-48 reopened: causal contract baseline, not an economic recovery claim.

This regression test intentionally uses the genuine thirteen-person scenario
rather than constructing a new favorable village.
"""
from __future__ import annotations

from carlos_sim import SQLiteEventStore
from test_play48aa_actual_barter_bread_return import _seed_signed_share
from test_play47_closure_endurance import WORLD


def test_farm_bread_share_is_not_automatically_personal_wage(tmp_path):
    path = tmp_path / "play48-reopened-baseline.sqlite"
    state = _seed_signed_share(path, share=True)
    assert len(state.npcs) == 13
    assert state.resources["farm"]["food"] == 0
    assert state.courier_provisions["farm-water-huda"]["remaining"] == 2
    assert state.supply_circuits["huda"]["bread_share_delivered"] == 0
    # Two original loaves are ALREADY held in the original wage escrow.
    # Future bakery returns must remain FARM property until separately
    # authorized; an existing escrow must not silently increase.
    with SQLiteEventStore(path) as db:
        assert db.verify(WORLD).to_dict() == state.to_dict()


def test_genuine_returned_bread_remains_farm_owned_not_worker_wage(tmp_path):
    """48h genuine 13-NPC physical return: prove the missing renewal link."""
    from test_play48h3_early_market_wage import _run
    from carlos_sim.economic_diagnostics import audit_npc_economy
    path = tmp_path / "play48-reopened-48h.sqlite"
    _seed_signed_share(path, share=True)
    state, _ = _run(path, 48 * 3600, early=True,
                    hungry_woodcutter_work_enabled=True,
                    retry_known_supplier_enabled=True)
    assert len(state.npcs) == 13
    account = state.supply_circuits["huda"]
    assert account["bread_share_delivered"] >= 1, (
        "physical bakery-to-farm return absent: wage renewal cannot be tested"
    )
    assert account["bread_share_delivered"] <= account["bread_share_earned"]
    # Real returned bread belongs to FARM, not to the worker or wage escrow.
    # This is the existing deficiency to repair under a new signed authority.
    contract = state.courier_provisions["farm-water-huda"]
    assert contract["total_units"] == 2
    assert contract["authorized_total_units"] == 2
    assert audit_npc_economy(state)["copper_known_total"] == 12
    with SQLiteEventStore(path) as db:
        assert db.verify(WORLD).to_dict() == state.to_dict()


def test_new_farm_payroll_requires_explicitly_signed_ceiling(tmp_path):
    original = _seed_signed_share(tmp_path / "no-extra.sqlite", share=True)
    approved = _seed_signed_share(
        tmp_path / "signed-extra.sqlite", share=True, farm_refill_authority=True)
    assert original.resources == approved.resources
    assert original.courier_provisions["farm-water-huda"]["authorized_total_units"] == 2
    assert approved.courier_provisions["farm-water-huda"]["authorized_total_units"] == 3
    assert approved.courier_provisions["farm-water-huda"]["total_units"] == 2
    assert approved.courier_provisions["farm-water-huda"]["remaining"] == 2


def test_farm_refill_cannot_be_forged_without_real_same_command_delivery(tmp_path):
    import pytest
    from carlos_sim import DomainEvent, TimeEngine
    from carlos_sim.store import InvalidEvent
    path = tmp_path / "no-teleport.sqlite"
    state = _seed_signed_share(path, share=True, farm_refill_authority=True)
    with SQLiteEventStore(path) as db:
        TimeEngine(db).open_session(WORLD)
        fake = DomainEvent("CourierFarmProvisionReplenished", None,
            "attempt to grab food without physical bakery arrival", state.time,
            {"id": "farm-water-huda", "courier_id": "huda",
             "service_deliveries": 1})
        with pytest.raises(InvalidEvent, match="preceding food arrival"):
            db.append(WORLD, "attack:no-arrival", state.revision,
                      [fake], supply_authorized=True)
        assert db.verify(WORLD).to_dict() == state.to_dict()


def test_farm_reducer_escrows_only_real_local_stock_once_and_with_ceiling(tmp_path):
    import pytest
    from carlos_sim import DomainEvent
    from carlos_sim.courier_provisions import (
        replenish_farm_provision_from_returned_bread,
        validate_courier_provisions,
    )
    state = _seed_signed_share(
        tmp_path / "reducer-check.sqlite", share=True,
        farm_refill_authority=True)
    # Synthetic adversarial reducer fixture: NEVER interpreted as an
    # actual delivery or independently verified income in a real village.
    d = state.to_dict()
    circuit = d["supply_circuits"]["huda"]
    assert circuit["stops"][1] == circuit["stops"][5] == "farm"
    circuit["index"] = 5
    circuit["deliveries"] = 4
    circuit["bread_share_delivered"] = 1
    circuit["bread_share_earned"] = 1
    d["entities"]["huda"]["location_id"] = "farm"
    d["resources"]["farm"]["food"] = 1
    receipt = DomainEvent("CourierFarmProvisionReplenished", None,
        "authenticated farm return in real caller", d["time"],
        {"id": "farm-water-huda", "courier_id": "huda",
         "service_deliveries": 4})
    replenish_farm_provision_from_returned_bread(
        d, receipt, supply_authorized=True)
    assert d["resources"]["farm"]["food"] == 0
    contract = d["courier_provisions"]["farm-water-huda"]
    assert (contract["total_units"], contract["remaining"]) == (3, 3)
    assert not contract["payments"]  # An escrow is NOT the courier's wage.
    validate_courier_provisions(d)
    with pytest.raises(ValueError, match="signed return"):
        replenish_farm_provision_from_returned_bread(
            d, receipt, supply_authorized=True)


def test_genuine_13npc_return_can_escrow_one_future_farm_wage(tmp_path):
    """Same 13 people and owned stock, only candidate's opt-in differs."""
    from test_play48h3_early_market_wage import _run, _conserve
    from carlos_sim.economic_diagnostics import audit_npc_economy
    import json
    control_path = tmp_path / "same-world-policy-off.sqlite"
    enabled_path = tmp_path / "same-world-policy-on.sqlite"
    a = _seed_signed_share(control_path, share=True, farm_refill_authority=True)
    b = _seed_signed_share(enabled_path, share=True, farm_refill_authority=True)
    assert a.to_dict() == b.to_dict()  # Strict identical genesis.
    control, _ = _run(
        control_path, 48 * 3600, early=True,
        hungry_woodcutter_work_enabled=True,
        retry_known_supplier_enabled=True)
    candidate, _ = _run(
        enabled_path, 48 * 3600, early=True,
        hungry_woodcutter_work_enabled=True,
        retry_known_supplier_enabled=True,
        farm_sourced_wage_refill_enabled=True)
    assert len(candidate.npcs) == 13
    assert candidate.supply_circuits["huda"]["bread_share_delivered"] >= 1
    c = control.courier_provisions["farm-water-huda"]
    w = candidate.courier_provisions["farm-water-huda"]
    assert c["total_units"] == 2 and w["authorized_total_units"] == 3
    assert w["total_units"] == 3, (
        "real returned FARM loaf did not enter the specifically signed escrow")
    assert candidate.resources["huda"]["food"] >= 0
    assert _conserve(control) >= 0 and _conserve(candidate) >= 0
    for path, state in [(control_path, control), (enabled_path, candidate)]:
        assert audit_npc_economy(state)["copper_known_total"] == 12
        with SQLiteEventStore(path) as db:
            assert db.verify(WORLD).to_dict() == state.to_dict()
    print("PLAY48_REOPENED_REAL_FARM_ESCROW_48H", json.dumps({
        "control_real_bread_return": control.supply_circuits["huda"]["bread_share_delivered"],
        "candidate_real_bread_return": candidate.supply_circuits["huda"]["bread_share_delivered"],
        "control_signed_wage_total": c["total_units"],
        "candidate_signed_wage_total": w["total_units"],
        "candidate_paid_wages": len(w["payments"]),
        "candidate_remaining_real_escrow": w["remaining"],
        "economic_96h_or_168h_recovery_proven": False,
    }, sort_keys=True), flush=True)
