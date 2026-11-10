"""Read-only time series of two ACTUAL inhabitants; no forced decisions."""
import json
from carlos_sim import SQLiteEventStore, TimeEngine
from test_play48m_finite_employment import _seed_employed, WORLD
from test_play48h3_early_market_wage import _original_engine


def test_real_wood_producer_buyer_arrival_and_offer(tmp_path):
    path = tmp_path / "actual-wood-buyer-short.sqlite"
    _seed_employed(path)
    observations = []
    with SQLiteEventStore(path) as db:
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            eng = _original_engine(db, clock, early=False,
                                   hungry_woodcutter_work_enabled=True)
            state = db.load(WORLD)
            for t in (1,35,50,70,119,120,121,150,240,400,700):
                state=eng.advance(WORLD,seconds=t-state.time,
                                  command_id=f"m:buyer:{t}",
                                  expected_revision=state.revision).state
                rec = next((j for j in state.production_jobs.values()
                            if j["recipe_id"]=="finite-timber-cutting"),None)
                observations.append({
                    "time":t,
                    "layla_here":state.entities["layla"]["location_id"],
                    "layla_hunger":state.npcs["layla"]["needs"]["hunger"],
                    "layla_cash":state.resources["layla"]["coin_copper"],
                    "burner_here":state.entities["burner"]["location_id"],
                    "burner_hunger":state.npcs["burner"]["needs"]["hunger"],
                    "burner_cash":state.resources["burner"]["coin_copper"],
                    "forest_wood":state.resources["lumberyard"]["wood"],
                    "wood_job_status":rec["status"] if rec else None,
                    "wood_job_due":rec["due"] if rec else None,
                    "wood_quotes":len([o for o in state.market_offers.values()
                                       if o["resource"]=="wood" and o["status"]=="open"]),
                    "wood_sales":len([o for o in state.market_trades.values()
                                       if o["resource"]=="wood"]),
                    "burner_trips":len([v for v in state.travels.values()
                                        if v["npc_id"]=="burner"]),
                })
            assert db.verify(WORLD).to_dict()==state.to_dict()
        finally:
            clock.close_session(WORLD)
    print("PLAY48M_REAL_WOOD_TRADING_FIRST_700S",json.dumps(observations,sort_keys=True),flush=True)
