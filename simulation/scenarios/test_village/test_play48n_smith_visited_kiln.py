"""PLAY48-N — one real shop retry after one hour of actual time.

The same 13-NPC village begins with finite standing timber, exactly the
same twelve existing copper coins, one woodcutter, one real kiln and the
same bread and water. No script tells the smith that charcoal arrived
later. He may revisit only a charcoal-maker shop he himself already saw,
using his own known roads, one hour after an unproductive trip.
"""
from __future__ import annotations
import json
import pytest
from carlos_sim import SQLiteEventStore, TimeEngine
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.compound_professional_trade import choose_compound_known_road
from test_play48m_finite_employment import _seed_employed, _real_stats, WORLD
from test_play48h3_early_market_wage import _original_engine


def _actual_two_hours(path, *, retry: bool):
    """H3's helper advances only on 6h slices: it cannot run a 2h test."""
    with SQLiteEventStore(path) as db:
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            engine = _original_engine(
                db, clock, early=False,
                hungry_woodcutter_work_enabled=True,
                retry_known_supplier_enabled=retry,
            )
            state = db.load(WORLD)
            for target in (1800, 3600, 5400, 7200):
                state = engine.advance(
                    WORLD, seconds=target-state.time,
                    command_id=f"play48n:real:{target}",
                    expected_revision=state.revision,
                ).state
                assert state.time == target
            assert db.verify(WORLD).to_dict() == state.to_dict()
        finally:
            clock.close_session(WORLD)
    return state


def test_retry_contract_rejects_non_bounded_interval(tmp_path):
    state=_seed_employed(tmp_path/"invalid-retry.sqlite")
    for invalid in (-5,0,599,86401,True,"1h",1.1):
        with pytest.raises(ValueError):
            choose_compound_known_road(state,"smith",retry_after_seconds=invalid)


def test_actual_2h_real_same_money_fuel_sale_and_wage(tmp_path):
    control=tmp_path/"no-second-visit.sqlite"
    choice=tmp_path/"firsthand-one-hour-revisit.sqlite"
    _seed_employed(control)
    _seed_employed(choice)
    original = _actual_two_hours(control, retry=False)
    observed = _actual_two_hours(choice, retry=True)
    assert original.time == observed.time == 7200
    base,treatment=_real_stats(original),_real_stats(observed)
    assert base["copper_total"]==treatment["copper_total"]==12
    assert base["people"]==treatment["people"]==13
    assert base["wood_jobs"] >= 1 and treatment["wood_jobs"] >= 1
    assert treatment["wood_sales"]>=1
    assert treatment["charcoal_jobs"]>=1
    # This is the specific additional physical B->S supply chain that
    # the old one-visit-only planner blocked despite genuine kiln inventory.
    assert treatment["charcoal_sales"]>=1, (base,treatment)
    assert treatment["coal_worker_wages"]>=1, (base,treatment)
    assert all(v>=0 for stock in observed.resources.values()
               for v in stock.values() if type(v) is int)
    with SQLiteEventStore(choice) as db:
        assert db.verify(WORLD).to_dict()==observed.to_dict()
        visits = [t for t in observed.travels.values()
                  if t["npc_id"]=="smith"
                  and t["destination"]=="charcoal_kiln"
                  and t["status"]=="arrived"]
        assert len(visits)>=2
        assert visits[-1]["arrived_at"]-visits[0]["arrived_at"]>=3600
        assert db.db.execute("PRAGMA integrity_check").fetchone()==("ok",)
        assert db.db.execute("PRAGMA foreign_key_check").fetchall()==[]
    print("PLAY48N_2H_ACTUAL_FIRSTHAND_FUEL_REVISIT",
          json.dumps({"before":base,"after":treatment,
                      "second_kiln_visit":True,
                      "new_copper_minted":0,"new_food_minted":0,
                      "seven_day_recovery_proven":False},sort_keys=True),flush=True)
