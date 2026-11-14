"""Operator-only cash tracing; this projection never grants a wage."""
from types import SimpleNamespace

from carlos_sim.economic_diagnostics import audit_npc_economy


def test_market_receipts_are_not_merchant_income_or_unpaid_worker_wages():
    state = SimpleNamespace(
        entities={"buyer": {}, "keeper": {}, "farmer": {}},
        locations={"market": {}, "farm": {}},
        resources={
            "buyer": {"coin_copper": 0},
            "keeper": {"coin_copper": 0},
            "farmer": {"coin_copper": 2},
            "market": {"coin_copper": 8},
            "farm": {"coin_copper": 2},
        },
        courier_provisions={},
        market_trades={"bread-sale": {
            "resource": "food", "payment_resource": "coin_copper",
            "buyer_id": "buyer", "seller_id": "keeper",
            "stock_owner_id": "market", "total_paid": 2,
        }},
        production_jobs={
            "paid": {"status": "completed", "work_wage": {
                "site_id": "farm", "worker_id": "farmer", "amount": 2}},
            "unpaid": {"status": "completed"},
        },
        travels={}, npcs={"buyer": {"needs": {"hunger": 100}}},
        world_id="test", time=3600, revision=1,
    )
    report = audit_npc_economy(state)
    assert report["copper_known_total"] == 12
    assert report["completed_without_wage_receipt"] == 1
    assert report["cash_flows_from_receipts"] == [
        {"from": "buyer", "to": "market", "cause": "sale", "copper": 2},
        {"from": "farm", "to": "farmer", "cause": "completed_job", "copper": 2},
    ]
    assert report["copper_known_by_owner"]["keeper"] == 0


def test_unknown_cash_is_not_a_zero_balance_or_funded_wage():
    state = SimpleNamespace(
        entities={"worker": {}}, locations={"market": {}},
        resources={"worker": {}, "market": {"coin_copper": 12}},
        courier_provisions={}, market_trades={}, production_jobs={},
        travels={}, npcs={}, world_id="test", time=0, revision=0,
    )
    report = audit_npc_economy(state)
    assert report["copper_unknown_owners"] == ("worker",)
    assert not report["copper_scope_complete"]
    assert report["cash_flows_from_receipts"] == []
