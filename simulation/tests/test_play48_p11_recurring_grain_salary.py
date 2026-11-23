"""P11: no new freight food without real later physical grain delivery.

These are focused reducer-policy tests; only genuine saved-world Actions is
allowed to establish actual simulation success and conservation.
"""
from __future__ import annotations

import pytest

from carlos_sim.domain import WorldState, apply_event
from carlos_sim.freight_payroll import record_delivery, validate_contract
from test_play48_local_courier_food_wage import market_candidate, offer


def signed(tmp_path):
    d=market_candidate(tmp_path)
    s=apply_event(WorldState.from_dict(d),offer(d),
                  supply_authorized=True,market_authorized=True)
    assert not s.supply_circuits["huda"]["food_payroll"]["receipts"]
    d=s.to_dict()
    # Isolated projection fixture: the original tiny genesis does not sign
    # a grain-purchase account. Add only the record slot read by the pure
    # freight proof policy; the genuine event-ledger test stays separate.
    d["supply_circuits"]["huda"]["grain_purchase"]={"receipts":[]}
    return d


def test_future_food_salary_requires_real_later_grain_receipt(tmp_path):
    d=signed(tmp_path)
    c=d["supply_circuits"]["huda"]
    original_deliveries=c["deliveries"]
    assert "grain_purchase" in c
    d["time"]+=13*3600
    d["entities"]["huda"]["location_id"]="bakery"
    c["index"]=2
    c["deliveries"]=original_deliveries+1
    record_delivery(d,"huda","grain")
    assert c["food_payroll"]["receipts"]==[], "presence cannot mint service"
    c["grain_purchase"]["receipts"].append({
        "delivery":c["deliveries"],"delivered_at":d["time"],
        "loaded_at":None,"received_at":None,
    })
    record_delivery(d,"huda","water")
    assert c["food_payroll"]["receipts"]==[]
    record_delivery(d,"huda","grain")
    assert c["food_payroll"]["receipts"]==[{
        "delivery":c["deliveries"],"delivered_at":d["time"],"payment":None
    }]
    validate_contract(d,"huda",c)
    record_delivery(d,"huda","grain")
    assert len(c["food_payroll"]["receipts"])==1
    # Fraudulent replacement no longer replays because the delivery ledger
    # itself is the authority, not a caller-supplied service number.
    c["grain_purchase"]["receipts"].pop()
    with pytest.raises(ValueError,match="authentic grain"):
        validate_contract(d,"huda",c)


def test_no_retroactive_or_double_bakery_salary_on_new_market_contract(tmp_path):
    d=signed(tmp_path)
    c=d["supply_circuits"]["huda"]
    d["time"]+=13*3600
    d["entities"]["huda"]["location_id"]="bakery"
    c["index"]=2
    c["deliveries"]+=1
    service=c["deliveries"]
    c["grain_purchase"]["receipts"].append({
        "delivery":service,"delivered_at":d["time"],
        "loaded_at":None,"received_at":None})
    # Existing bakery service is a distinct creditor. Do not pay it again,
    # even if its historical bakery payment is still pending.
    d["courier_provisions"]["prior-claim-test"]={
        "courier_id":"huda",
        "deferred_grain_services":[{
            "service_deliveries":service,"earned_at":d["time"],
            "paid_at":None,
        }],
    }
    record_delivery(d,"huda","grain")
    assert c["food_payroll"]["receipts"]==[], "one freight delivery cannot earn twice"


def test_old_quote_age_kept_after_subsequent_paid_wage():
    """A second REAL wage cannot reset an old aid listing's clock."""
    from types import SimpleNamespace
    from carlos_sim.community_food import (
        _aged_quote_relisted_after_paid_market_freight,
    )
    due=900000
    old={
        "status":"closed","site_id":"market","stock_owner_id":"market",
        "resource":"food","posted_at":due-7*3600,"closed_at":due,
    }
    contract={
        "site_id":"market","resource":"food","signed_at":due-14*3600,
        "receipts":[{"payment":{"paid_at":due}}],
    }
    state=SimpleNamespace(
        supply_circuits={"huda":{"food_payroll":contract}},
        market_offers={"old":old},
    )
    assert _aged_quote_relisted_after_paid_market_freight(
        state,{"posted_at":due})
    assert not _aged_quote_relisted_after_paid_market_freight(
        state,{"posted_at":due+1})
    old["posted_at"]=due-5*3600
    assert not _aged_quote_relisted_after_paid_market_freight(
        state,{"posted_at":due})
    old["posted_at"]=due-7*3600
    contract["receipts"][0]["payment"]=None
    assert not _aged_quote_relisted_after_paid_market_freight(
        state,{"posted_at":due})
