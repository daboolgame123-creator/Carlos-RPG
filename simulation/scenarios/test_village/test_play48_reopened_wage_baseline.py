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
