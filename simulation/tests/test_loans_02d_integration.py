"""02-D cross-system 7-NPC loan / market / movement and save invariants.

Author-side probes, not an independent external approval.
"""
from __future__ import annotations

import pytest

from carlos_sim import (
    DomainEvent, SQLiteEventStore, TimeEngine, NPCLoanService,
    NPCMarketService, NPCMovementService, WorldState,
)
from carlos_sim.store import InvalidEvent, RevisionConflict
from carlos_sim.backup import (
    create_backup_bundle, verify_backup_bundle, restore_backup_bundle,
)
from test_loans_02d import prepare, ev, propose, accept, repay, tick, rev

BASE_SHA = "b1345f69041e76e20b53af26251fc92946eb7230"


def _interlocking_story(db, clock, svc):
    propose(db, svc)
    accept(db, svc)
    tick(db, clock, 60, "to-half")
    repay(db, svc, 3, "first-partial")
    market = NPCMarketService(db, clock)
    market.post("test", "huda", "huda", "village", "bread-for-sale",
                "bread", 1, "coin_copper", 2, expected_revision=rev(db))
    market.buy("test", "nora", "bread-purchase", "bread-for-sale",
               1, 2, expected_revision=rev(db))
    after = db.load("test")
    assert after.resources["nora"]["coin_copper"] == 3
    assert after.resources["nora"]["bread"] == 1
    assert after.loan_contracts["loan"]["remaining"] == 5
    NPCMovementService(db, clock).start(
        "test", "nora", "village-square", "nora-departs",
        expected_revision=rev(db))
    tick(db, clock, 50, "nora-arrives")
    before = db.load("test")
    assert before.time == 110
    assert before.loan_contracts["loan"]["remaining"] == 5
    overdue = tick(db, clock, 10, "miss-due")
    assert overdue.time == 120
    assert overdue.loan_contracts["loan"]["status"] == "overdue"
    assert overdue.loan_contracts["loan"]["remaining"] == 5
    assert overdue.entities["nora"]["location_id"] == "square"
    assert db.verify("test").to_dict() == overdue.to_dict()
    return overdue


def test_seven_characters_borrow_spend_escape_and_still_owe_after_deadline(tmp_path):
    with SQLiteEventStore(tmp_path / "story.sqlite") as db:
        prepare(db)
        clock = TimeEngine(db)
        clock.open_session("test")
        svc = NPCLoanService(db, clock)
        overdue = _interlocking_story(db, clock, svc)
        assert len(overdue.npcs) == 7
        assert overdue.resources["basim"]["coin_copper"] == 15
        assert overdue.resources["nora"]["coin_copper"] == 3
        assert overdue.resources["huda"]["coin_copper"] == 2
        assert overdue.resources["layla"]["coin_copper"] == 5
        assert overdue.loan_contracts["loan"]["repaid"] == 3
        assert overdue.loan_contracts["loan"]["defaulted_at"] == 120
        assert overdue.loan_repayments["first-partial"]["late"] is False


def test_debtor_later_sells_owned_bread_and_can_repay_real_coin_after_meeting(tmp_path):
    with SQLiteEventStore(tmp_path / "recovery.sqlite") as db:
        prepare(db)
        clock = TimeEngine(db)
        clock.open_session("test")
        svc = NPCLoanService(db, clock)
        _interlocking_story(db, clock, svc)
        # Nora's newly acquired bread is actually hers, and Layla has
        # preinitialized five coins in the square. No "reward" is invented.
        market = NPCMarketService(db, clock)
        market.post("test", "nora", "nora", "square", "nora-resells",
                    "bread", 1, "coin_copper", 2,
                    expected_revision=rev(db))
        market.buy("test", "layla", "buy-nora-bread", "nora-resells",
                   1, 2, expected_revision=rev(db))
        assert db.load("test").resources["nora"]["coin_copper"] == 5
        assert db.load("test").resources["nora"]["bread"] == 0
        assert db.load("test").resources["layla"]["bread"] == 1
        # Creditor must actually travel to square to receive repayment.
        with pytest.raises(InvalidEvent):
            repay(db, svc, 5, "remote-not-allowed")
        NPCMovementService(db, clock).start(
            "test", "basim", "village-square", "lender-follows",
            expected_revision=rev(db))
        tick(db, clock, 50, "lender-arrives")
        final = repay(db, svc, 5, "final-payment")
        assert final.time == 170
        assert final.loan_contracts["loan"]["status"] == "paid"
        assert final.loan_contracts["loan"]["remaining"] == 0
        assert final.loan_contracts["loan"]["defaulted_at"] == 120
        assert final.loan_contracts["loan"]["paid_at"] == 170
        assert final.loan_repayments["final-payment"]["late"] is True
        assert final.resources["basim"]["coin_copper"] == 20
        assert final.resources["nora"]["coin_copper"] == 0
        assert final.resources["huda"]["coin_copper"] == 2
        assert final.resources["layla"]["coin_copper"] == 3
        # Exactly the seeded 25 copper units remain in all 7 hands.
        assert sum(final.resources[npc]["coin_copper"] for npc in final.npcs) == 25
        assert db.verify("test").to_dict() == final.to_dict()


def test_restart_and_provenance_checked_backup_preserve_overdue_but_not_mint(tmp_path):
    path = tmp_path / "before-restart.sqlite"
    with SQLiteEventStore(path) as db:
        prepare(db)
        clock = TimeEngine(db)
        clock.open_session("test")
        svc = NPCLoanService(db, clock)
        propose(db, svc)
        accept(db, svc)
        repay(db, svc, 3, "early")
        frozen = db.load("test").to_dict()
        db.snapshot("test")
        assert db.verify("test").to_dict() == frozen
    with SQLiteEventStore(path) as db:
        clock = TimeEngine(db)
        clock.open_session("test")
        assert db.load("test").to_dict() == frozen
        due = tick(db, clock, 120, "after-restart")
        assert due.loan_contracts["loan"]["remaining"] == 5
        assert due.loan_contracts["loan"]["status"] == "overdue"
        bundle = tmp_path / "bundle"
        manifest = create_backup_bundle(db, "test", bundle, code_commit=BASE_SHA)
        assert (manifest["schema"], manifest["rules"]) == (31, 39)
        assert verify_backup_bundle(bundle) == manifest
        saved = due.to_dict()
    restored = tmp_path / "restored.sqlite"
    restore_backup_bundle(bundle, restored)
    with SQLiteEventStore(restored) as db:
        assert db.db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert db.verify("test").to_dict() == saved
        clock = TimeEngine(db)
        clock.open_session("test")
        assert tick(db, clock, 500, "after-restore").loan_contracts["loan"]["remaining"] == 5
        assert db.verify("test").loan_contracts["loan"]["status"] == "overdue"
    with SQLiteEventStore(path) as db:
        assert db.verify("test").to_dict() == saved


def test_two_due_at_same_tick_are_deterministic_and_no_overdue_charges(tmp_path):
    with SQLiteEventStore(tmp_path / "same-due.sqlite") as db:
        prepare(db)
        clock = TimeEngine(db)
        clock.open_session("test")
        svc = NPCLoanService(db, clock)
        propose(db, svc, cid="loan-nora", debtor="nora")
        accept(db, svc, cid="loan-nora", debtor="nora")
        propose(db, svc, cid="loan-salma", debtor="salma")
        accept(db, svc, cid="loan-salma", debtor="salma")
        assert db.load("test").resources["basim"]["coin_copper"] == 4
        end = tick(db, clock, 120, "both-due")
        assert end.loan_contracts["loan-nora"]["status"] == "overdue"
        assert end.loan_contracts["loan-salma"]["status"] == "overdue"
        assert end.loan_contracts["loan-nora"]["remaining"] == 8
        assert end.loan_contracts["loan-salma"]["remaining"] == 8
        assert end.resources["basim"]["coin_copper"] == 4
        assert end.resources["nora"]["coin_copper"] == 8
        assert end.resources["salma"]["coin_copper"] == 8
        assert db.verify("test").to_dict() == end.to_dict()


def test_full_vs_split_time_produces_same_due_status_and_money(tmp_path):
    output = []
    for label, waits in (("large", (120,)), ("tiny", (29, 31, 40, 20))):
        with SQLiteEventStore(tmp_path / f"{label}.sqlite") as db:
            prepare(db)
            clock = TimeEngine(db)
            clock.open_session("test")
            svc = NPCLoanService(db, clock)
            propose(db, svc)
            accept(db, svc)
            for i, dt in enumerate(waits):
                tick(db, clock, dt, f"{label}-{i}")
            state = db.verify("test")
            output.append({
                "time": state.time,
                "wallets": state.to_dict()["resources"],
                "contracts": state.to_dict()["loan_contracts"],
                "payments": state.to_dict()["loan_repayments"],
                "scheduled": state.to_dict()["scheduled"],
            })
    assert output[0] == output[1]


def test_outstanding_loans_do_not_touch_assistance_or_market_ledgers(tmp_path):
    with SQLiteEventStore(tmp_path / "separate-ledgers.sqlite") as db:
        prepare(db)
        clock = TimeEngine(db)
        clock.open_session("test")
        svc = NPCLoanService(db, clock)
        propose(db, svc)
        accept(db, svc)
        tick(db, clock, 120, "due")
        state = db.verify("test")
        assert state.loan_contracts["loan"]["status"] == "overdue"
        assert state.obligations == {}
        assert state.market_trades == {}
        assert state.social_messages == {}
        assert state.resources["nora"]["coin_copper"] == 8
        assert state.resources["basim"]["coin_copper"] == 12


def test_tamper_principal_or_missed_due_snapshot_rejected(tmp_path):
    with SQLiteEventStore(tmp_path / "tamper.sqlite") as db:
        prepare(db)
        clock = TimeEngine(db)
        clock.open_session("test")
        svc = NPCLoanService(db, clock)
        propose(db, svc)
        accept(db, svc)
        overdue = tick(db, clock, 120, "due")
        baseline = overdue.to_dict()
        for label in ("remainder", "default_time", "status", "due", "source", "missing"):
            d = overdue.to_dict()
            loan = d["loan_contracts"]["loan"]
            if label == "remainder":
                loan["remaining"] = 0
            elif label == "default_time":
                loan["defaulted_at"] = 0
            elif label == "status":
                loan["status"] = "active"
            elif label == "due":
                loan["due_at"] = 130
            elif label == "source":
                loan["disbursement"]["borrower_after"] += 1
            else:
                del d["loan_contracts"]
            with pytest.raises(ValueError):
                WorldState.from_dict(d)
        assert db.verify("test").to_dict() == baseline
