"""PLAY-48Z gate: prove existing courier lanes cannot magically refill farm food.

The six physical contracted legs have a real bakery->farm road but reserve
that trip for the return copper consignment. This test is intentionally
operator-only and does NOT authorize new goods or silently reroute workers.
"""
from __future__ import annotations

from carlos_sim import SQLiteEventStore
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.supply import _lane
from test_play48y_huda_farm_worksite_food_wage import _seed_farm_two_prepaid


def test_real_bakery_to_farm_road_is_cash_lane_not_food_lane(tmp_path):
    s = _seed_farm_two_prepaid(tmp_path / "z-real-route.sqlite")
    before = s.to_dict()
    all_lanes = {}
    for who, rec in sorted(s.supply_circuits.items()):
        per_worker = []
        for idx in range(len(rec["route_ids"])):
            edited = dict(rec, index=idx)
            lane = _lane(edited, cash_enabled="coin_copper" in s.resources[who])
            per_worker.append(lane)
            if idx == 4:
                assert rec["stops"][idx:idx+2] == ["bakery", rec["stops"][1]]
                rid = rec["route_ids"][idx]
                road = s.routes[rid]
                assert {road["a"], road["b"]} == {
                    "bakery", rec["stops"][1]}
                assert lane == ("bakery", rec["stops"][1], "coin_copper")
            if idx == 2:
                assert lane == ("bakery", "market", "food")
        all_lanes[who] = per_worker
    assert len(all_lanes) == 2
    assert all(
        lane is None or not (lane[1] in ("farm", "farm_east")
                             and lane[2] == "food")
        for lanes in all_lanes.values() for lane in lanes
    )
    assert s.to_dict() == before, "read-only contract analysis mutated world"


def test_farm_contract_cannot_be_auto_refunded_as_market_wage(tmp_path):
    from carlos_sim.courier_provisions import (
        choose_market_owned_food_refill,
    )
    s = _seed_farm_two_prepaid(tmp_path / "z-real-escrow.sqlite")
    assert s.resources["farm"]["food"] == 0
    assert s.courier_provisions["farm-water-huda"]["remaining"] == 2
    assert s.courier_provisions["farm-water-huda"]["authorized_total_units"] == 2
    assert s.courier_provisions["farm-water-huda"]["total_units"] == 2
    assert choose_market_owned_food_refill(s, "huda") is None
    assert sum(owner.get("food", 0) for owner in s.resources.values()) + sum(
        c["remaining"] for c in s.courier_provisions.values()
    ) == 3
    assert audit_npc_economy(s)["copper_known_total"] == 12
    with SQLiteEventStore(tmp_path / "z-store-separate.sqlite") as db:
        assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
