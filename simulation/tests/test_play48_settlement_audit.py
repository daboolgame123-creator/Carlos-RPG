"""Pure synthetic audit tests; no claim of living-village recovery."""
from types import SimpleNamespace
import pytest
from carlos_sim.settlement_audit import audit_completed_work_cash_settlement

def fixture(known_bakery=True):
    resources={
        "market":{"coin_copper":3},
        "bakery":({"coin_copper":1} if known_bakery else {}),
        "farm_east":{"coin_copper":0},
        "farid":{"coin_copper":2},"hana":{"coin_copper":1},
        "salma":{"coin_copper":2},"carlos":{"coin_copper":3},
    }
    return SimpleNamespace(
        world_id="synthetic-audit-only",time=7200,revision=3,
        entities={who:{} for who in ("farid","hana","salma","carlos")},
        npcs={who:{"needs":{"hunger":20}} for who in ("farid","hana","salma")},
        locations={site:{} for site in ("market","bakery","farm_east")},
        resources=resources,
        market_trades={"actual-sale":{"buyer_id":"carlos","stock_owner_id":"market",
            "seller_id":"salma","resource":"food","payment_resource":"coin_copper",
            "total_paid":2}},
        production_recipes={"job":{"wage_coin":2}},
        production_jobs={
            "unpaid-farid":{"site_id":"farm_east","recipe_id":"job",
                "status":"completed","npc_id":"farid"},
            "paid-salma":{"site_id":"market","recipe_id":"job",
                "status":"completed","npc_id":"salma",
                "work_wage":{"amount":2,"site_id":"market","worker_id":"salma"}}
        },
        supply_circuits={"hana":{"carry":{"resource":"coin_copper",
            "source":"market","destination":"farm_east"}}},
        courier_provisions={},travels={},
    )

def test_earned_unpaid_job_cannot_spend_same_cargo_twice():
    state=fixture()
    a=audit_completed_work_cash_settlement(state)
    assert a.total_known_copper==12 and a.copper_scope_complete
    assert a.npc_personal_copper==5 and a.site_owned_copper==4
    assert a.courier_cash_custody==1
    east=next(x for x in a.sites if x.site=="farm_east")
    market=next(x for x in a.sites if x.site=="market")
    assert east.known_copper==0 and east.completed_unpaid_signed_wages==2
    assert east.unpaid_job_ids==("unpaid-farid",)
    assert east.cash_shortfall_for_completed_wages==2
    assert east.physical_courier_cash_destined_here==1
    assert east.uncommitted_cash_estimate==0
    assert market.historical_site_customer_revenue==2
    assert market.historical_work_wages_paid==2
    assert market.historical_sale_service_wages_paid==0
    assert state.resources["farm_east"]["coin_copper"]==0

def test_unknown_cash_stays_unknown_not_assumed_zero():
    report=audit_completed_work_cash_settlement(fixture(False))
    assert not report.copper_scope_complete
    assert "bakery" in report.unknown_coin_owners
    assert report.total_known_copper==11
    b=next(x for x in report.sites if x.site=="bakery")
    assert b.known_copper is None and b.uncommitted_cash_estimate is None

@pytest.mark.parametrize("amount",[0,2,-1,None,"one"])
def test_only_one_actual_coin_in_physical_cargo(amount):
    state=fixture()
    state.resources["hana"]["coin_copper"]=amount
    pattern=("invalid amount" if amount in (-1,"one") else "one real carried unit")
    with pytest.raises(ValueError,match=pattern):
        audit_completed_work_cash_settlement(state)

def test_merchant_sales_not_equivalent_to_personal_wage():
    state=fixture()
    state.market_trades["actual-sale"]["keeper_commission_coin"]=1
    audit=audit_completed_work_cash_settlement(state)
    market=next(x for x in audit.sites if x.site=="market")
    assert market.historical_site_customer_revenue==2
    assert market.historical_sale_service_wages_paid==1
    assert market.known_copper==3
