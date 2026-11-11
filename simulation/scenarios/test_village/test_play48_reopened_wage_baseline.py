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
