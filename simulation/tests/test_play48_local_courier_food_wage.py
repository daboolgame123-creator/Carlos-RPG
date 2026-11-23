"""P10: two real co-present people may sign only FUTURE earned market food.

Old Huda's separate bounded bakery debt remains intact, as do customer
quotes, 13-person population, and 12 real copper. No food moves at signing.
"""
from __future__ import annotations

import pytest

from carlos_sim import DomainEvent, InvalidEvent
from carlos_sim.domain import WorldState, apply_event
from carlos_sim.freight_payroll import (
    choose_local_market_freight_agreement,
    choose_market_wage_quote_retirement, pay_wage,
)
from test_play48_hunter_well_visit import hunter_state as hunter


def market_candidate(tmp_path):
    d = hunter(tmp_path)
    d["entities"]["huda"]["location_id"] = "market"
    d["npcs"]["huda"]["needs"].update(hunger=76, fatigue=30, safety=0)
    d["supply_circuits"]["huda"]["index"] = 3
    d["supply_circuits"]["huda"]["carry"] = None
    d["resources"]["market"]["food"] = max(2, d["resources"]["market"]["food"])
    assert "food_payroll" not in d["supply_circuits"]["huda"]
    return d


def offer(d):
    return DomainEvent(
        "LocalFreightFoodAgreementSigned", "salma",
        "prospective food wage agreed in person at owner stall",
        d["time"], {"courier_id": "huda", "site_id": "market",
                    "resource": "food", "interval_seconds": 12 * 3600})


def test_real_local_offer_requires_both_employer_and_worker_present(tmp_path):
    d = market_candidate(tmp_path)
    s = WorldState.from_dict(d)
    assert choose_local_market_freight_agreement(s, "huda")
    before = s.resources["market"]["food"]
    signed = apply_event(s, offer(d), supply_authorized=True,
                         market_authorized=True)
    assert signed.resources["market"]["food"] == before
    assert signed.resources["huda"]["food"] == 0
    assert signed.supply_circuits["huda"]["food_payroll"]["signed_at"] == d["time"]
    assert not signed.supply_circuits["huda"]["food_payroll"]["receipts"]
    assert not choose_local_market_freight_agreement(signed, "huda")
    assert choose_market_wage_quote_retirement(signed, "huda") is None
    assert len(signed.npcs) == 13


@pytest.mark.parametrize("change", [
    lambda d: (d["entities"]["huda"].update(location_id="bakery"), d["supply_circuits"]["huda"].update(index=2)),
    lambda d: d["entities"]["salma"].update(location_id="bakery"),
    lambda d: d["npcs"]["huda"]["needs"].update(hunger=92),
    lambda d: d["npcs"]["huda"]["needs"].update(fatigue=72),
    lambda d: d["resources"]["market"].update(food=0),
    lambda d: (d["entities"]["huda"].update(location_id="bakery"), d["supply_circuits"]["huda"].update(index=2)),
])
def test_never_automatically_sign_without_real_consent_or_stock(tmp_path, change):
    d=market_candidate(tmp_path)
    change(d)
    state=WorldState.from_dict(d)
    assert not choose_local_market_freight_agreement(state, "huda")


def test_no_salary_for_presence_or_unproved_cargo(tmp_path):
    d=market_candidate(tmp_path)
    signed=apply_event(WorldState.from_dict(d),offer(d),
                       supply_authorized=True,market_authorized=True)
    for act in [
        lambda: apply_event(WorldState.from_dict(d), offer(d),
                            supply_authorized=True,market_authorized=False),
        lambda: apply_event(WorldState.from_dict(d), offer(d),
                            supply_authorized=False,market_authorized=True),
        lambda: apply_event(WorldState.from_dict(d),
                            DomainEvent(offer(d).event_type,"huda","forged",d["time"],offer(d).data),
                            supply_authorized=True,market_authorized=True),
        lambda: apply_event(signed,offer(d),
                            supply_authorized=True,market_authorized=True),
    ]:
        with pytest.raises((ValueError, InvalidEvent)):
            act()
    before=signed.to_dict()
    with pytest.raises(ValueError):
        pay_wage(before,DomainEvent("RecurringFreightWagePaid",None,"fake",d["time"],
                                  {"courier_id":"huda","delivery":1}),supply_authorized=True)
    assert signed.to_dict()["resources"]["market"]["food"] == d["resources"]["market"]["food"]
