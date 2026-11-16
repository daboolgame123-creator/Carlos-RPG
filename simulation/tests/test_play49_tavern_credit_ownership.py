"""PLAY49-F: legitimate local NPC loans cannot launder site-owned revenue.

Separate diagnostic: loans move existing NPC copper by genuine consent,
not workshop site money. Do not mistake a private loan for employer-financed
cash procurement or solve recurring food supply by issuing fake debt.
"""
from __future__ import annotations

import pytest

from carlos_sim import (
    SQLiteEventStore, TimeEngine, NPCMarketService, NPCProductionService,
)
from carlos_sim.loans import NPCLoanService
from carlos_sim.store import InvalidEvent
from test_market_02c import prepare, _rev
from test_play49_fruit_stall_contract import WORLD, add_orchard, copper
from test_play49_dairy_stall_contract import add_dairy
from test_play49_tavern_trade_provenance import add_tavern
from test_play49_tavern_cooked_meal import (
    add_actual_kitchen, source_and_buy_for_cook, deposit_ingredients,
    finish_sale_wage_and_eat,
)


def world(tmp_path):
    path = tmp_path / "tavern-finance.sqlite"
    db = SQLiteEventStore(path)
    prepare(db, copper_buyer=5)
    add_orchard(db)
    add_dairy(db)
    add_tavern(db)
    add_actual_kitchen(db)
    clock = TimeEngine(db)
    clock.open_session(WORLD)
    market = NPCMarketService(db, clock)
    start = db.load(WORLD)
    source_and_buy_for_cook(db, clock, market)
    deposit_ingredients(db, clock)
    done = finish_sale_wage_and_eat(db, clock, market, start)
    assert done.resources["tavern"]["coin_copper"] == 2
    assert done.resources["tavern_cook"]["coin_copper"] == 1
    assert done.resources["huda"]["coin_copper"] == 12
    assert done.resources["tavern_host"]["coin_copper"] == 0
    assert done.resources["tavern"]["food"] == 0
    assert done.resources["orchard"]["fruit"] == 0
    assert done.resources["dairy"]["milk"] == 0
    assert done.resources["dairy"]["cheese"] == 0
    return db, clock, NPCLoanService(db, clock)


def test_revenue_belongs_to_site_and_cannot_be_loaned_by_cashless_host(tmp_path):
    db, clock, loans = world(tmp_path)
    try:
        start = db.load(WORLD)
        assert start.resources["tavern"]["coin_copper"] == 2
        assert start.resources["tavern_host"]["coin_copper"] == 0
        assert copper(start) == 22

        # A site is not a human NPC and cannot impersonate a lender.
        with pytest.raises(InvalidEvent):
            loans.propose(
                WORLD, "tavern", "tavern_cook", "venue-fake-personal-loan",
                2, 3600, expected_revision=_rev(db))
        assert db.verify(WORLD).to_dict() == start.to_dict()

        # Genuine host present but with ZERO personal balance may propose;
        # never debit the site's real revenue on loan acceptance.
        loans.propose(WORLD, "tavern_host", "tavern_cook",
                      "host-loan-offer", 2, 3600, expected_revision=_rev(db))
        proposal = db.load(WORLD)
        assert proposal.loan_contracts["host-loan-offer"]["status"] == "proposed"
        with pytest.raises(InvalidEvent):
            loans.accept(WORLD, "tavern_cook", "host-loan-offer",
                         expected_revision=_rev(db))
        after = db.load(WORLD)
        assert after.resources["tavern"]["coin_copper"] == 2
        assert after.resources["tavern_host"]["coin_copper"] == 0
        assert after.resources["tavern_cook"]["coin_copper"] == 1
        assert after.loan_contracts["host-loan-offer"]["status"] == "proposed"
        assert copper(after) == copper(start)
        assert db.verify(WORLD).to_dict() == after.to_dict()
    finally:
        clock.close_session(WORLD)
        db.close()


def test_real_private_loan_preserves_cash_but_cannot_refill_empty_inputs(tmp_path):
    db, clock, loans = world(tmp_path)
    try:
        opening = db.load(WORLD)
        assert opening.resources["huda"]["coin_copper"] == 12
        assert opening.resources["tavern_cook"]["coin_copper"] == 1
        assert opening.resources["tavern"]["coin_copper"] == 2
        loan = loans.propose(WORLD, "huda", "tavern_cook",
                             "real-private-cook-credit", 4, 3600,
                             expected_revision=_rev(db))
        assert loan.state.resources["huda"]["coin_copper"] == 12
        assert loan.state.resources["tavern_cook"]["coin_copper"] == 1
        borrowed = loans.accept(WORLD, "tavern_cook",
                                "real-private-cook-credit",
                                expected_revision=_rev(db)).state
        assert borrowed.resources["huda"]["coin_copper"] == 8
        assert borrowed.resources["tavern_cook"]["coin_copper"] == 5
        assert borrowed.resources["tavern"]["coin_copper"] == 2
        assert borrowed.loan_contracts["real-private-cook-credit"]["remaining"] == 4
        assert copper(borrowed) == copper(opening)

        # This is NOT a sustainable inventory solution: genuine milk and
        # fruit were consumed in the first meal, and no new stock appears.
        with pytest.raises(InvalidEvent):
            NPCProductionService(db, clock).start(
                WORLD, "tavern_cook", "fruit-cheese-hot-plate",
                "loan-does-not-create-fruit", expected_revision=_rev(db))
        assert db.verify(WORLD).to_dict() == borrowed.to_dict()

        # The outstanding debt remains real; no automatic site cash sweep.
        before_due = db.load(WORLD)
        clock.advance(WORLD, seconds=3600, command_id="loan-reaches-due",
                      expected_revision=_rev(db))
        overdue = db.load(WORLD)
        assert overdue.loan_contracts["real-private-cook-credit"]["status"] == "overdue"
        assert overdue.loan_contracts["real-private-cook-credit"]["remaining"] == 4
        assert overdue.resources["tavern"]["coin_copper"] == 2
        assert overdue.resources["huda"]["coin_copper"] == 8
        assert overdue.resources["tavern_cook"]["coin_copper"] == 5
        assert copper(overdue) == copper(before_due)
        assert db.verify(WORLD).to_dict() == overdue.to_dict()
        db.snapshot(WORLD)
        assert db.verify(WORLD).to_dict() == overdue.to_dict()
        assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert not db.db.execute("PRAGMA foreign_key_check").fetchall()
    finally:
        clock.close_session(WORLD)
        db.close()


def test_private_loan_repayment_is_real_and_cannot_double_collect(tmp_path):
    db, clock, loans = world(tmp_path)
    try:
        start = db.load(WORLD)
        loans.propose(WORLD, "huda", "tavern_cook", "funded-loan",
                      4, 3600, expected_revision=_rev(db))
        loans.accept(WORLD, "tavern_cook", "funded-loan", expected_revision=_rev(db))
        repaid = loans.repay(WORLD, "tavern_cook", "funded-loan", "real-repay",
                             4, expected_revision=_rev(db)).state
        assert repaid.resources["huda"]["coin_copper"] == start.resources["huda"]["coin_copper"]
        assert repaid.resources["tavern_cook"]["coin_copper"] == start.resources["tavern_cook"]["coin_copper"]
        assert repaid.resources["tavern"]["coin_copper"] == 2
        assert repaid.loan_contracts["funded-loan"]["status"] == "paid"
        assert repaid.loan_contracts["funded-loan"]["remaining"] == 0
        with pytest.raises(InvalidEvent):
            loans.repay(WORLD, "tavern_cook", "funded-loan", "double-repay",
                        1, expected_revision=_rev(db))
        assert copper(repaid) == copper(start)
        assert db.verify(WORLD).to_dict() == repaid.to_dict()
    finally:
        clock.close_session(WORLD)
        db.close()
