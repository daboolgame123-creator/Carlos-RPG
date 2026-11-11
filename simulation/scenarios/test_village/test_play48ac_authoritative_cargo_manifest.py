"""PLAY48AC: world controller must record the exact reducer-approved cargo.

Synthetic snapshots are intentionally not persisted; true world 48h A/B is
separately responsible for actual causal effects and event-log replay.
"""
from __future__ import annotations

from carlos_sim import WorldState
from carlos_sim.supply import choose_cargo_manifest
from test_play48aa_actual_barter_bread_return import _seed_signed_share


def _local_bakery_state(tmp_path, *, round_number=0, bread=1, claim=1):
    original = _seed_signed_share(tmp_path / "manifest-seed.sqlite", share=True)
    d = original.to_dict()
    courier = d["supply_circuits"]["huda"]
    courier["index"] = 4
    courier["rounds"] = round_number
    courier["bread_share_earned"] = claim
    courier["bread_share_delivered"] = 0
    d["entities"]["huda"]["location_id"] = "bakery"
    d["resources"]["bakery"]["food"] = bread
    d["resources"]["bakery"]["coin_copper"] = 5
    return WorldState(**d)


def test_bakery_farm_return_uses_owned_bread_not_fixed_old_coin_index(tmp_path):
    state = _local_bakery_state(tmp_path)
    before = state.to_dict()
    assert choose_cargo_manifest(state, "huda") == ("SupplyCargoPicked", "food")
    assert state.to_dict() == before


def test_next_return_still_uses_real_copper_when_alternating(tmp_path):
    state = _local_bakery_state(tmp_path, round_number=1)
    assert choose_cargo_manifest(state, "huda") == (
        "SupplyCargoPicked", "coin_copper"
    )


def test_unearned_claim_cannot_generate_return_bread(tmp_path):
    state = _local_bakery_state(tmp_path, claim=0)
    assert choose_cargo_manifest(state, "huda") == (
        "SupplyCargoPicked", "coin_copper"
    )


def test_courier_has_no_food_to_pick_up_or_is_exhausted(tmp_path):
    state = _local_bakery_state(tmp_path, bread=0)
    assert choose_cargo_manifest(state, "huda") == (
        "SupplyCargoPicked", "coin_copper"
    )
    d = state.to_dict()
    d["npcs"]["huda"]["needs"]["hunger"] = 90
    assert choose_cargo_manifest(WorldState(**d), "huda") is None


def test_market_freight_protects_last_owed_real_bakery_loaf(tmp_path):
    state = _local_bakery_state(tmp_path, bread=1)
    d = state.to_dict()
    d["supply_circuits"]["hana"]["index"] = 2
    d["entities"]["hana"]["location_id"] = "bakery"
    assert choose_cargo_manifest(WorldState(**d), "hana") is None
    d["resources"]["bakery"]["food"] = 2
    assert choose_cargo_manifest(WorldState(**d), "hana") == (
        "SupplyCargoPicked", "food"
    )
