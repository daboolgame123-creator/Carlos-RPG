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
    choose_local_market_employment,LOCAL_MARKET_HIRE_INTERVAL)
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
    if not choose_local_market_employment(s,"huda"):
        from carlos_sim.freight_payroll import _previous_wages_fully_satisfied
        from carlos_sim.food_for_work import _available_site_food,_worker_present_and_free
        from carlos_sim.market import _present
        print("P10_MOCK_MEETING_DIAGNOSTIC", {
            "previous_wages_settled":_previous_wages_fully_satisfied(s.to_dict(),"huda"),
            "huda_at_market_free":_worker_present_and_free(s,"huda","market"),
            "salma_at_market_free":_worker_present_and_free(s,"salma","market"),
            "salma_market_present":_present(s.to_dict(),"salma","market"),
            "unquoted_market_food":_available_site_food(s,"market"),
            "circuit":dict(s.supply_circuits["huda"]),
            "salma_running_actions":[dict(a) for a in s.actions.values() if a["npc_id"]=="salma" and a["status"]=="running"],
            "huda_running_actions":[dict(a) for a in s.actions.values() if a["npc_id"]=="huda" and a["status"]=="running"],
        },flush=True)
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
