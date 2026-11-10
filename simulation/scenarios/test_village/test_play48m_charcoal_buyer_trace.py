"""Actual finite charcoal buyer, no fake NPC errands."""
import json
from carlos_sim import SQLiteEventStore, TimeEngine
from test_play48m_finite_employment import _seed_employed, WORLD
from test_play48h3_early_market_wage import _original_engine


def test_actual_cash_backed_smith_wood_to_charcoal_first_hour(tmp_path):
    path=tmp_path/"charcoal-smith.sqlite"
    _seed_employed(path)
    rows=[]
    with SQLiteEventStore(path) as db:
        clock=TimeEngine(db)
        clock.open_session(WORLD)
        try:
            engine=_original_engine(db,clock,early=False,
                        hungry_woodcutter_work_enabled=True)
            state=db.load(WORLD)
            for t in (1,35,70,120,240,300,400,600,900,1200,2400,3600):
                state=engine.advance(WORLD,seconds=t-state.time,
                     command_id=f"coal:read:{t}",
                     expected_revision=state.revision).state
                rows.append({
                  "sec":t,
                  "burner":state.entities["burner"]["location_id"],
                  "burner_cash":state.resources["burner"]["coin_copper"],
                  "smith":state.entities["smith"]["location_id"],
                  "smith_cash":state.resources["smith"]["coin_copper"],
                  "smith_has_charcoal":state.resources["smith"]["charcoal"],
                  "forest_wood":state.resources["lumberyard"]["wood"],
                  "kiln_charcoal":state.resources["charcoal_kiln"]["charcoal"],
                  "coal_quote":len([x for x in state.market_offers.values()
                                   if x["resource"]=="charcoal" and x["status"]=="open"]),
                  "wood_sales":sum(x["resource"]=="wood" for x in state.market_trades.values()),
                  "coal_sales":sum(x["resource"]=="charcoal" for x in state.market_trades.values()),
                  "coal_making":sum(x["recipe_id"]=="finite-wood-charcoal"
                                    and x["status"]=="completed"
                                    for x in state.production_jobs.values()),
                  "smith_trips":len([x for x in state.travels.values()
                                     if x["npc_id"]=="smith"]),
                })
            assert db.verify(WORLD).to_dict()==state.to_dict()
        finally:
            clock.close_session(WORLD)
    print("PLAY48M_REAL_SMITH_FUEL_PURCHASE_CHRONOLOGY",json.dumps(rows,sort_keys=True),flush=True)
