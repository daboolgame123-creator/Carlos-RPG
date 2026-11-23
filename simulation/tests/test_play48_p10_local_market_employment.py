"""P10 legal new food-work agreement: genuine P9 h244 evidence + local mocks.

No change to the preserved world is ever written by these tests. The success
fixture is EXPLICITLY hypothetical co-location; only scenario acceptance
may establish that such a contract occurred autonomously in the real world.
"""
from pathlib import Path
import pytest
from carlos_sim import SQLiteEventStore,DomainEvent,InvalidEvent
from carlos_sim.domain import WorldState,apply_event
from carlos_sim.freight_payroll import (
    choose_local_market_employment,waits_for_local_market_hire,
    LOCAL_MARKET_HIRE_INTERVAL,LOCAL_MARKET_MEETING_MAX_WAIT)
from play48_integrated_acceptance import WORLD,HOUR

SOURCE=Path("evidence/p9_real244")


@pytest.fixture
def authentic_world():
    matches=sorted(SOURCE.rglob("P9_hunter_visited_well.sqlite"))
    assert len(matches)==1,matches
    with SQLiteEventStore(matches[0]) as db:
        s=db.load(WORLD)
        assert s.time==244*HOUR and len(s.npcs)==13
    assert s.resources["market"]["food"]==12
    assert s.supply_circuits["huda"]["deliveries"]==23
    assert "food_payroll" not in s.supply_circuits["huda"]
    yield s


@pytest.fixture
def local_work_meeting(authentic_world):
    d=authentic_world.to_dict()
    # A HYPOTHETICAL, separate immutable-state rights test: no such change
    # is ever saved or attributed to the genuine world. Requires actual
    # travel and eating to obtain these values in the acceptance simulation.
    d["entities"]["huda"]["location_id"]="market"
    d["npcs"]["huda"]["needs"]["hunger"]=78
    d["npcs"]["huda"]["needs"]["fatigue"]=15
    d["supply_circuits"]["huda"]["index"]=3
    d["supply_circuits"]["huda"]["carry"]=None
    # At genuine h244 Salma is in a scheduled rest action: she MUST NOT
    # be treated as freely consenting. This hypothetical fixture models a
    # completed/rested availability window instead. No saved-world change.
    for ident, action in list(d["actions"].items()):
        if action["npc_id"]=="salma" and action["status"]=="running":
            d["scheduled"].pop(action["schedule_id"],None)
            del d["actions"][ident]
    return WorldState.from_dict(d)


def event(s,actor="salma",courier="huda"):
    return DomainEvent("LocalMarketFreightEmploymentSigned",actor,
        "prospective future physical freight food wage",s.time,
        {"courier_id":courier,"site_id":"market","resource":"food",
         "interval_seconds":LOCAL_MARKET_HIRE_INTERVAL})


def test_h244_no_retrospective_contract_or_food_without_a_real_meeting(authentic_world):
    assert not choose_local_market_employment(authentic_world,"huda")
    before=authentic_world.to_dict()
    with pytest.raises(ValueError):
        apply_event(authentic_world,event(authentic_world),
                    market_authorized=True,supply_authorized=True)
    assert authentic_world.to_dict()==before


def test_new_market_job_has_strict_real_local_dual_authority(local_work_meeting):
    s=local_work_meeting
    assert choose_local_market_employment(s,"huda")
    for market,supply,actor in ((False,False,"salma"),
                                (True,False,"salma"),
                                (False,True,"salma"),
                                (True,True,"huda")):
        with pytest.raises(ValueError):
            apply_event(s,event(s,actor=actor),market_authorized=market,
                        supply_authorized=supply)
    after=apply_event(s,event(s),market_authorized=True,supply_authorized=True)
    contract=after.supply_circuits["huda"]["food_payroll"]
    assert contract["interval_seconds"]==12*HOUR
    assert contract["site_id"]=="market"
    assert contract["receipts"]==()
    assert after.resources==s.resources
    assert after.supply_circuits["huda"]["deliveries"]==s.supply_circuits["huda"]["deliveries"]
    with pytest.raises(ValueError):
        apply_event(after,event(after),market_authorized=True,supply_authorized=True)


@pytest.mark.parametrize("change",[
    lambda d:d["entities"]["huda"].update(location_id="well"),
    lambda d:d["npcs"]["huda"]["needs"].update(hunger=95),
    lambda d:d["npcs"]["huda"]["needs"].update(fatigue=75),
    lambda d:d["supply_circuits"]["huda"].update(index=0),
    lambda d:d["resources"]["market"].update(food=4),
    lambda d:d["courier_provisions"]["huda-future-bakery"]["deferred_grain_services"][0].update(paid_at=None),
    lambda d:d["npcs"]["salma"].update(role="farmer"),
])
def test_no_hire_without_real_local_surplus_safe_worker_and_old_pay_resolved(local_work_meeting,change):
    d=local_work_meeting.to_dict()
    change(d)
    assert not choose_local_market_employment(WorldState(**d),"huda")


def test_new_signed_contract_cannot_be_paid_without_future_physical_delivery(local_work_meeting):
    s=apply_event(local_work_meeting,event(local_work_meeting),
                  market_authorized=True,supply_authorized=True)
    with pytest.raises(ValueError):
        apply_event(s,DomainEvent("RecurringFreightWagePaid",None,
            "forged work before future cargo",s.time,
            {"courier_id":"huda","delivery":23}),supply_authorized=True)
    assert s.resources["market"]["food"]==12
    assert s.resources["huda"]["food"]==0


def test_recent_real_market_arrival_allows_bounded_wait_until_salma_finishes_rest(authentic_world):
    d=authentic_world.to_dict()
    d["entities"]["huda"]["location_id"]="market"
    d["npcs"]["huda"]["needs"]["hunger"]=78
    d["supply_circuits"]["huda"]["index"]=3
    d["supply_circuits"]["huda"]["carry"]=None
    # This is a deliberately hypothetical rights fixture (not real history):
    # model one previously arrived physical market journey, and use the
    # original genuine 244h Salma rest due at +120 seconds.
    d["travels"]["hypothetical-market-arrival"]={
        "npc_id":"huda","status":"arrived","destination":"market",
        "arrived_at":d["time"]-120,
    }
    mock=WorldState(**d)
    assert not choose_local_market_employment(mock,"huda")
    assert waits_for_local_market_hire(mock,"huda")
    time_expired=mock.to_dict()
    time_expired["time"]+=LOCAL_MARKET_MEETING_MAX_WAIT
    assert not waits_for_local_market_hire(WorldState(**time_expired),"huda")
    out_of_food=mock.to_dict()
    out_of_food["resources"]["market"]["food"]=0
    assert not waits_for_local_market_hire(WorldState(**out_of_food),"huda")
    unresolved_old_wage=mock.to_dict()
    unresolved_old_wage["courier_provisions"]["huda-future-bakery"]["deferred_grain_services"][0]["paid_at"]=None
    assert not waits_for_local_market_hire(WorldState(**unresolved_old_wage),"huda")
