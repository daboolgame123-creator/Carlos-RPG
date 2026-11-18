"""PLAY48 scarce cash: source-fair local dispatch without false funds.

Tests ONLY the bakery-visible receipt ordering. Actual delivery, payroll,
conservation and forgery are tested by physical-supply and grain-sale suites.
"""
from copy import deepcopy

from carlos_sim.grain_purchase import cash_minimum, pending_claims


def _receipt(number, when, *, loaded=None):
    return {"delivery": number, "delivered_at": when,
            "loaded_at": loaded, "received_at": None}


def _ledger(fast_receipts, slow_receipts):
    fast = {"index": 4, "grain_purchase": {
        "unit_price": 1, "receipts": fast_receipts}}
    slow = {"index": 4, "grain_purchase": {
        "unit_price": 1, "receipts": slow_receipts}}
    return {"supply_circuits": {"fast": fast, "slow": slow},
            "resources": {"bakery": {"coin_copper": 2}},
            "market_offers": {}, "production_jobs": {},
            "production_recipes": {}, "time": 100}, fast, slow


def test_first_claim_from_each_source_precedes_second_from_fast_farm():
    state, fast, slow = _ledger(
        [_receipt(1, 10), _receipt(2, 20), _receipt(3, 30)],
        [_receipt(1, 40), _receipt(2, 70)])
    original = deepcopy(state)
    # First signed source claim goes first; real coin may settle to zero.
    assert cash_minimum(state, fast) == 1
    assert cash_minimum(state, slow) == 2
    # After that first coin leaves bakery in a physically loaded parcel,
    # the slower source has first-round priority over the fast farm's backlog.
    fast["grain_purchase"]["receipts"][0]["loaded_at"] = 50
    assert cash_minimum(state, slow) == 1
    assert cash_minimum(state, fast) == 2
    assert pending_claims(state)[0][2] == "slow"
    assert original["resources"] == state["resources"]
    assert state["resources"]["bakery"]["coin_copper"] == 2


def test_never_skip_own_earlier_unpaid_claim_or_promised_cash():
    state, fast, slow = _ledger(
        [_receipt(1, 10, loaded=15), _receipt(2, 20), _receipt(3, 25)],
        [_receipt(1, 40, loaded=45), _receipt(2, 55)])
    # Both farms have a first-round remittance already in flight; only their
    # second genuine grain receipts compete, in documented arrival order.
    assert cash_minimum(state, fast) == 1
    assert cash_minimum(state, slow) == 2
    # A bakery owed 2 copper for already completed bakery work cannot remit
    # either source's coin until that local senior promise is protected.
    state["production_jobs"]["done"] = {
        "site_id": "bakery", "status": "completed", "recipe_id": "bread"}
    state["production_recipes"]["bread"] = {"wage_coin": 2}
    assert cash_minimum(state, fast) == 3
    assert cash_minimum(state, slow) == 4
    state["market_offers"]["quote"] = {
        "status": "open", "stock_owner_id": "bakery",
        "resource": "coin_copper", "remaining": 1}
    assert cash_minimum(state, fast) == 4
    assert cash_minimum(state, slow) == 5
