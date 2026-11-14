"""Real 13NPC, 12-copper market-service payroll, 6/12h independent A/B.

The ONLY initial difference is the opt-in t0 signed sale-service contract.
No extra opening food, coins or forced work. This is NOT a 168h acceptance.
"""
import json
import pytest

from carlos_sim import DomainEvent, SQLiteEventStore, TimeEngine
from carlos_sim.store import InvalidEvent
from carlos_sim.economic_diagnostics import audit_npc_economy
from test_play48_real_watch_income_24h import seed, engine, WORLD, HOUR
from test_play48_finite_hunt_fish_roads import conserve_diverse


def _paychecks(state):
    return [(ident, trade) for ident, trade in sorted(state.market_trades.items())
            if "keeper_commission_coin" in trade]


def _run(path, enabled):
    start=seed(path, sale_backed_keeper_commission_enabled=enabled)
    assert len(start.npcs)==13
    assert sum(r.get("coin_copper",0) for r in start.resources.values())==12
    assert sum(r.get("food",0) for r in start.resources.values())==3
    assert start.market_stalls["market"].get("keeper_commission_coin")==(1 if enabled else None)
    seen=[]
    with SQLiteEventStore(path) as db:
        clock=TimeEngine(db)
        clock.open_session(WORLD)
        try:
            runner=engine(db,clock,reserve_trader_meal=True,
                          deferred_market_courier_wage=True)
            for hour in (6,12):
                old=db.verify(WORLD)
                state=runner.advance(WORLD,seconds=hour*HOUR-old.time,
                   expected_revision=old.revision,
                   command_id=f"earned-market-work:{enabled}:{hour}").state
                assert len(state.npcs)==13
                conserve_diverse(state)
                audit=audit_npc_economy(state)
                assert audit["copper_scope_complete"] and audit["copper_known_total"]==12
                assert db.verify(WORLD).to_dict()==state.to_dict()
                assert db.db.execute("PRAGMA integrity_check").fetchone()==("ok",)
                assert db.db.execute("PRAGMA foreign_key_check").fetchall()==[]
                rows=_paychecks(state)
                for ident,t in rows:
                    assert t["seller_id"]=="salma"
                    assert t["stock_owner_id"]==t["site_id"]=="market"
                    assert t["payment_resource"]=="coin_copper"
                    assert t["total_paid"]>=2
                    assert t["keeper_commission_coin"]==1
                    assert t["keeper_coin_after"]-t["keeper_coin_before"]==1
                    assert t["pay_target_after"]-t["site_coin_after_commission"]==1
                point={
                   "hour":hour,"cash":audit["copper_known_total"],
                   "salma_coin":state.resources["salma"]["coin_copper"],
                   "market_coin":state.resources["market"]["coin_copper"],
                   "food_sales":sum(t["resource"]=="food" for t in state.market_trades.values()),
                   "meals":len(state.consumptions),
                   "hunger100":sum(x["needs"]["hunger"]==100 for x in state.npcs.values()),
                   "hana":state.supply_circuits["hana"]["deliveries"],
                   "huda":state.supply_circuits["huda"]["deliveries"],
                   "paid_sales":len(rows),
                }
                seen.append(point)
                print("PLAY48_SALE_BACKED_13NPC_12H_ROW "+
                      json.dumps({"treatment":enabled,"point":point},sort_keys=True),
                      flush=True)
            if enabled:
                assert _paychecks(state), "RELEASE_NO_GO: no real sale funded a keeper wage"
                before=db.verify(WORLD).to_dict()
                forged=DomainEvent("MarketTradeExecuted","salma",
                    "attempt counterfeit worker's salary",state.time,{
                    "id":"fake-repeat-service","offer_id":"not-a-real-offer",
                    "buyer_id":"salma","quantity":1,"expected_unit_price":2})
                with pytest.raises(InvalidEvent):
                    db.append(WORLD,"attempt-counterfeit-seller-commission",
                              state.revision,[forged],market_authorized=True)
                assert db.verify(WORLD).to_dict()==before
            else:
                assert not _paychecks(state)
        finally:
            clock.close_session(WORLD)
    return start,seen


def test_authentic_paid_retail_service_has_no_early_source_regression(tmp_path):
    original, control=_run(tmp_path/"original.sqlite",False)
    treatment, paid=_run(tmp_path/"signed-retail.sqlite",True)
    assert original.resources==treatment.resources
    assert original.npcs==treatment.npcs
    assert original.routes==treatment.routes
    assert original.production_recipes==treatment.production_recipes
    assert original.courier_provisions==treatment.courier_provisions
    for a,b in zip(control,paid):
        assert a["hour"]==b["hour"]
        assert b["food_sales"]>=a["food_sales"], "RELEASE_NO_GO: real sales declined"
        assert b["meals"]>=a["meals"], "RELEASE_NO_GO: residents ate less"
        assert b["hana"]>=a["hana"], "RELEASE_NO_GO: Hana's real freight regressed"
        assert b["huda"]>=a["huda"], "RELEASE_NO_GO: Huda's real freight regressed"
        assert b["hunger100"]<=a["hunger100"], "RELEASE_NO_GO: new starvation"
    assert paid[-1]["paid_sales"]>=1
    print("PLAY48_SALE_SERVICE_13NPC_12H_AB "+json.dumps({
        "control":control,"treatment":paid,
        "does_not_prove_72_or_168h_recovery":True
    },sort_keys=True),flush=True)
