"""PLAY48: first-hand missed-market recall, opt-in, never free purchases.

The selector fixture starts with REAL witnessed road arrivals and a REAL
initial paid job. A detached hypothetical second wage tests intent logic;
the synthetic change is NEVER committed or reported as an earned payment.
Full 13-NPC economic effects belong to play48_market_memory_ab.py.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

from carlos_sim import LivingWorldEngine, SQLiteEventStore, TimeEngine
from carlos_sim.market_navigation import choose_known_market_walk
from test_play42_market_shopping import _advance, _engine
from test_play38_multi_farm_couriers import (
    WORLD, FARMER, EAST, seed_two_field_world,
)


def _real_first_hand_failed_market_visit(tmp_path):
    path = tmp_path / "real-prior-unaffordable-visit.sqlite"
    with SQLiteEventStore(path) as db:
        seed_two_field_world(
            db, cash_return=True, waged_harvest=True,
            hungry_waged_farmer=True, harvest_wage_copper=1,
            market_wallets=True, hungry_market_buyers=False,
            one_hungry_market_buyer=False, initial_market_food=3,
        )
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            state = _advance(db, _engine(db, clock, full_life=True), 12000)
        finally:
            clock.close_session(WORLD)
        assert db.verify(WORLD).to_dict() == state.to_dict()
    assert state.entities[FARMER]["location_id"] == EAST
    assert state.resources[FARMER]["coin_copper"] == 1
    assert not [t for t in state.market_trades.values() if t["buyer_id"] == FARMER]
    assert any(t["npc_id"] == FARMER and t["destination"] == "market"
               and t["status"] == "arrived" for t in state.travels.values())
    assert any(t["npc_id"] == FARMER and "work_wage" in t
               for t in state.production_jobs.values())
    return state


def _detached_new_wage_selector_only(real, *, remove_visits=False,
                                    hide_prior_stall=False):
    raw = real.to_dict()
    # A deliberately isolated PURE SELECTOR counterfactual. This is NOT
    # an authentic production event or recorded income/monetary conservation.
    raw["time"] += 3
    raw["npcs"][FARMER]["needs"]["hunger"] = 75
    raw["resources"][FARMER]["coin_copper"] = 2
    wage_at = real.time + 1
    for job in raw["production_jobs"].values():
        if job["npc_id"] == FARMER and "work_wage" in job:
            job["work_wage"]["paid_at"] = wage_at
    if remove_visits:
        raw["travels"] = {
            key: trip for key, trip in raw["travels"].items()
            if not (trip["npc_id"] == FARMER and
                    trip["destination"] == "market")
        }
    if hide_prior_stall:
        # A quote posted only AFTER physical arrival was never witnessed.
        for offer in raw["market_offers"].values():
            if offer["site_id"] == "market" and offer["resource"] == "food":
                offer["posted_at"] = real.time + 2
    return replace(real, **{
        name: raw[name] for name in
        ("time", "npcs", "resources", "production_jobs",
         "travels", "market_offers")
    })


def test_funded_worker_remembers_only_first_hand_failed_market_after_new_wage(tmp_path):
    genuine = _real_first_hand_failed_market_visit(tmp_path)
    mock = _detached_new_wage_selector_only(genuine)
    off = choose_known_market_walk(mock, FARMER, repeat_errands=True)
    on = choose_known_market_walk(
        mock, FARMER, repeat_errands=True,
        remember_unbought_stalls=True)
    assert on is not None and on.destination == "market"
    assert on.route_id in mock.navigation[FARMER]["known_routes"]
    assert off is None or off.destination != "market"
    assert genuine.resources[FARMER]["coin_copper"] == 1
    assert all(t["buyer_id"] != FARMER for t in genuine.market_trades.values())
    with pytest.raises(ValueError, match="requires repeat errands"):
        choose_known_market_walk(
            mock, FARMER, remember_unbought_stalls=True)


@pytest.mark.parametrize("variant", ["never_visited", "not_yet_posted"])
def test_forged_unwitnessed_food_stall_does_not_become_remote_knowledge(tmp_path, variant):
    genuine = _real_first_hand_failed_market_visit(tmp_path)
    mock = _detached_new_wage_selector_only(
        genuine,
        remove_visits=variant == "never_visited",
        hide_prior_stall=variant == "not_yet_posted")
    proposed = choose_known_market_walk(
        mock, FARMER, repeat_errands=True,
        remember_unbought_stalls=True)
    assert proposed is None or proposed.destination != "market"


def test_market_memory_opt_in_requires_full_life_and_shopping(tmp_path):
    with SQLiteEventStore(tmp_path / "invalid-flag.sqlite") as db:
        clock = TimeEngine(db)
        with pytest.raises(ValueError, match="remember_unbought_stalls_enabled"):
            LivingWorldEngine(db, clock,
                              remember_unbought_stalls_enabled=True)
        with pytest.raises(ValueError, match="remember_unbought_stalls_enabled"):
            LivingWorldEngine(db, clock,
                              remember_unbought_stalls_enabled="true")
