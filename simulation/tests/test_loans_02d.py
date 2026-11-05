"""02-D funded consensual loans, default and real local copper repayment."""
from __future__ import annotations

import pytest

from carlos_sim import (
    DomainEvent, SQLiteEventStore, TimeEngine, NPCLoanService,
    NPCMarketService, NPCMovementService, WorldState, apply_event,
)
from carlos_sim.domain import SCHEMA_VERSION, RULES_VERSION
from carlos_sim.store import InvalidEvent, RevisionConflict, DuplicateCommand
from carlos_sim.time_engine import SessionClosed, AdvanceLimitExceeded

PEOPLE = ("basim", "nora", "adel", "salma", "huda", "omar", "layla")


def ev(kind, data, actor=None, at=0):
    return DomainEvent(kind, actor, "02-D disposable debt fixture", at, data)


def prepare(db, *, lender=20, borrower=0, missing=None):
    db.create_world("test")
    events = [
        ev("LocationCreated", {"id": "village", "name": "Village"}),
        ev("LocationCreated", {"id": "square", "name": "Square"}),
        ev("RouteCreated", {
            "id": "village-square", "a": "village", "b": "square", "seconds": 50,
        }),
    ]
    for npc in PEOPLE:
        site = "square" if npc == "layla" else "village"
        events += [
            ev("EntityCreated", {
                "id": npc, "name": npc, "location_id": site, "controller": "npc",
            }),
            ev("NPCConfigured", {
                "npc_id": npc, "role": "resident",
                "needs": {"hunger": 10, "fatigue": 5, "safety": 0},
                "goals": {"earn": 40, "explore": 10, "survive": 30},
            }),
        ]
        money = lender if npc == "basim" else borrower if npc == "nora" else (
            5 if npc == "layla" else 0
        )
        owned = {"bread": 2 if npc == "huda" else 0, "coin_copper": money}
        if npc == "huda":
            owned["coin_copper"] = 0
        if missing == (npc, "coin_copper"):
            del owned["coin_copper"]
        for item, amount in owned.items():
            events.append(ev("ResourceChanged", {
                "owner_id": npc, "resource": item,
                "previous": None, "current": amount, "source": "initialization",
            }))
    db.append("test", "bootstrap", 0, events, bootstrap=True)


@pytest.fixture
def world(tmp_path):
    with SQLiteEventStore(tmp_path / "loans.sqlite") as db:
        prepare(db)
        clock = TimeEngine(db)
        clock.open_session("test")
        yield db, clock, NPCLoanService(db, clock)


def rev(db):
    return db.load("test").revision


def tick(db, clock, seconds, ident):
    return clock.advance("test", seconds=seconds, command_id=ident,
                         expected_revision=rev(db)).state


def propose(db, svc, cid="loan", principal=8, term=120,
            creditor="basim", debtor="nora"):
    return svc.propose("test", creditor, debtor, cid, principal, term,
                       expected_revision=rev(db)).state


def accept(db, svc, cid="loan", debtor="nora"):
    return svc.accept("test", debtor, cid, expected_revision=rev(db)).state


def repay(db, svc, amount, pid, cid="loan", debtor="nora"):
    return svc.repay("test", debtor, cid, pid, amount,
                     expected_revision=rev(db)).state


def test_opt_in_no_loan_state_and_version(tmp_path):
    assert (SCHEMA_VERSION, RULES_VERSION) == (25, 33)
    with SQLiteEventStore(tmp_path / "off.sqlite") as db:
        prepare(db)
        clock = TimeEngine(db)
        clock.open_session("test")
        end = tick(db, clock, 300, "clock")
        assert not end.loan_contracts and not end.loan_repayments
        assert end.resources["basim"]["coin_copper"] == 20
        assert end.resources["nora"]["coin_copper"] == 0
        assert db.verify("test").to_dict() == end.to_dict()


def test_proposal_is_not_a_loan_and_only_acceptance_funds_it(world):
    db, clock, svc = world
    old = db.load("test").to_dict()
    offered = propose(db, svc)
    c = offered.loan_contracts["loan"]
    assert c["status"] == "proposed"
    assert c["remaining"] is None and c["due_at"] is None
    assert offered.resources == db.load("test").resources
    assert offered.resources["basim"]["coin_copper"] == old["resources"]["basim"]["coin_copper"]
    assert offered.resources["nora"]["coin_copper"] == old["resources"]["nora"]["coin_copper"]
    assert not offered.scheduled
    accepted = accept(db, svc)
    c = accepted.loan_contracts["loan"]
    assert c["status"] == "active"
    assert c["principal"] == 8 and c["remaining"] == 8 and c["repaid"] == 0
    assert c["accepted_at"] == 0 and c["due_at"] == 120
    assert c["disbursement"] == {
        "lender_before": 20, "lender_after": 12,
        "borrower_before": 0, "borrower_after": 8,
    }
    assert accepted.resources["basim"]["coin_copper"] == 12
    assert accepted.resources["nora"]["coin_copper"] == 8
    assert accepted.scheduled["loan:due:loan"]["due"] == 120
    assert db.verify("test").to_dict() == accepted.to_dict()


def test_partial_repayment_leaves_exact_debt_then_due_causes_default(world):
    db, clock, svc = world
    propose(db, svc)
    accept(db, svc)
    tick(db, clock, 60, "halfway")
    part = repay(db, svc, 3, "part")
    c = part.loan_contracts["loan"]
    assert c["remaining"] == 5 and c["repaid"] == 3 and c["status"] == "active"
    assert part.resources["nora"]["coin_copper"] == 5
    assert part.resources["basim"]["coin_copper"] == 15
    assert part.loan_repayments["part"]["late"] is False
    before = tick(db, clock, 59, "before-due")
    assert before.time == 119 and before.loan_contracts["loan"]["status"] == "active"
    late = tick(db, clock, 1, "deadline")
    c = late.loan_contracts["loan"]
    assert c["status"] == "overdue" and c["defaulted_at"] == 120
    assert c["remaining"] == 5 and c["repaid"] == 3
    assert "loan:due:loan" not in late.scheduled
    assert late.resources["nora"]["coin_copper"] == 5
    assert late.resources["basim"]["coin_copper"] == 15
    assert db.verify("test").to_dict() == late.to_dict()


def test_exact_due_early_repayment_cancels_deadline_without_default(world):
    db, clock, svc = world
    propose(db, svc)
    accept(db, svc)
    # A scheduled signal at due does not count as fired before the clock
    # explicitly processes it; repayment at t=0 retires it legitimately.
    paid = repay(db, svc, 8, "early")
    c = paid.loan_contracts["loan"]
    assert c["status"] == "paid" and c["remaining"] == 0
    assert c["paid_at"] == 0 and c["defaulted_at"] is None
    assert not paid.scheduled
    finished = tick(db, clock, 500, "no-default")
    assert finished.loan_contracts["loan"]["status"] == "paid"
    assert finished.resources["basim"]["coin_copper"] == 20
    assert finished.resources["nora"]["coin_copper"] == 0
    assert db.verify("test").to_dict() == finished.to_dict()


def test_after_deadline_late_repayment_preserves_default_history(world):
    db, clock, svc = world
    propose(db, svc)
    accept(db, svc)
    overdue = tick(db, clock, 120, "missed")
    assert overdue.loan_contracts["loan"]["status"] == "overdue"
    paid = repay(db, svc, 8, "late")
    c = paid.loan_contracts["loan"]
    assert c["status"] == "paid" and c["remaining"] == 0
    assert c["defaulted_at"] == 120 and c["paid_at"] == 120
    assert paid.loan_repayments["late"]["late"] is True
    assert paid.resources["nora"]["coin_copper"] == 0
    assert paid.resources["basim"]["coin_copper"] == 20
    assert db.verify("test").to_dict() == paid.to_dict()


def test_withdraw_and_decline_offer_never_create_funded_debt(tmp_path):
    for role, decision in (("basim", "withdrawn"), ("nora", "declined")):
        with SQLiteEventStore(tmp_path / f"{role}.sqlite") as db:
            prepare(db)
            clock = TimeEngine(db)
            clock.open_session("test")
            svc = NPCLoanService(db, clock)
            propose(db, svc)
            result = svc.close("test", role, "loan", decision,
                               expected_revision=rev(db)).state
            c = result.loan_contracts["loan"]
            assert c["status"] == decision and c["remaining"] is None
            assert c["accepted_at"] is None and c["closed_at"] == 0
            assert not result.scheduled
            assert result.resources["basim"]["coin_copper"] == 20
            with pytest.raises(InvalidEvent):
                accept(db, svc)
            assert db.verify("test").to_dict() == result.to_dict()


def test_fake_lender_and_impostor_borrower_rejected_without_transfer(world):
    db, clock, svc = world
    with pytest.raises(InvalidEvent):
        propose(db, svc, creditor="nora", debtor="nora")
    old = db.load("test").to_dict()
    with pytest.raises(InvalidEvent):
        db.append("test", "spoof-proposal", old["revision"], [
            ev("LoanProposed", {
                "id": "fake", "lender_id": "basim", "borrower_id": "nora",
                "principal": 8, "term_seconds": 120,
            }, actor="huda")], loan_authorized=True)
    assert db.load("test").to_dict() == old
    propose(db, svc)
    current = db.load("test").to_dict()
    with pytest.raises(InvalidEvent):
        accept(db, svc, debtor="huda")
    assert db.load("test").to_dict() == current


def test_unknown_and_insufficient_lender_or_borrower_wallet_never_invents_copper(tmp_path):
    cases = [
        {"missing": ("basim", "coin_copper")},
        {"missing": ("nora", "coin_copper")},
        {"lender": 3}, {"borrower": 2**31 - 2},
    ]
    for i, cfg in enumerate(cases):
        with SQLiteEventStore(tmp_path / f"wallet-{i}.sqlite") as db:
            prepare(db, **cfg)
            clock = TimeEngine(db)
            clock.open_session("test")
            svc = NPCLoanService(db, clock)
            propose(db, svc)
            old = db.load("test").to_dict()
            with pytest.raises(InvalidEvent):
                accept(db, svc)
            assert db.load("test").to_dict() == old


def test_invalid_principal_term_and_bool_values_never_become_credit(world):
    db, clock, svc = world
    for index, principal in enumerate((0, -1, True, 10001, 2**31)):
        with pytest.raises(InvalidEvent):
            propose(db, svc, cid=f"bad-money-{index}", principal=principal)
    for index, term in enumerate((0, -1, True, 30*24*3600 + 1)):
        with pytest.raises(InvalidEvent):
            propose(db, svc, cid=f"bad-term-{index}", term=term)
    assert db.load("test").loan_contracts == {}


def test_cannot_repay_more_than_remaining_or_unowned_cash(world):
    db, clock, svc = world
    propose(db, svc)
    accept(db, svc)
    before = db.load("test").to_dict()
    for amt in (9, 0, -2, True):
        with pytest.raises(InvalidEvent):
            repay(db, svc, amt, f"invalid-{amt}")
    assert db.load("test").to_dict() == before
    repay(db, svc, 7, "seven")
    before_last = db.load("test").to_dict()
    with pytest.raises(InvalidEvent):
        repay(db, svc, 2, "too-big")
    assert db.load("test").to_dict() == before_last


def test_generic_clock_schedule_forgery_early_fire_and_cancel_blocked(world):
    db, clock, svc = world
    propose(db, svc)
    accept(db, svc)
    prior = db.load("test")
    forged = ev("ScheduledEventCreated", {
        "id": "loan:due:fake", "due": 10,
        "order": prior.next_schedule_order, "kind": "signal",
        "interrupt": False, "payload": {"__loan_due": "loan"},
    })
    with pytest.raises(InvalidEvent, match="protected"):
        db.append("test", "forge-clock", prior.revision, [forged],
                  loan_authorized=True)
    with pytest.raises(InvalidEvent, match="cannot cancel"):
        clock.cancel("test", "loan:due:loan", command_id="cancel",
                     expected_revision=prior.revision)
    with pytest.raises(InvalidEvent):
        db.append("test", "fire-early", prior.revision, [
            ev("ScheduledEventFired", {"id": "loan:due:loan"}),
        ], clock_authorized=True)
    assert db.load("test").to_dict() == prior.to_dict()


def test_loan_privacy_returns_only_participants_not_random_npcs(world):
    db, clock, svc = world
    propose(db, svc)
    accept(db, svc)
    lender = svc.my_loans("test", "basim")
    debtor = svc.my_loans("test", "nora")
    stranger = svc.my_loans("test", "omar")
    assert len(lender) == len(debtor) == 1
    assert lender[0]["role"] == "lender"
    assert debtor[0]["role"] == "borrower"
    assert lender[0]["remaining"] == debtor[0]["remaining"] == 8
    assert stranger == ()
    with pytest.raises(PermissionError):
        svc.my_loans("test", "fake")


def test_debtor_travel_does_not_delete_debt_or_allow_remote_repay(world):
    db, clock, svc = world
    propose(db, svc)
    accept(db, svc)
    NPCMovementService(db, clock).start(
        "test", "nora", "village-square", "escape",
        expected_revision=rev(db))
    assert db.load("test").loan_contracts["loan"]["remaining"] == 8
    with pytest.raises(InvalidEvent):
        repay(db, svc, 1, "during-travel")
    tick(db, clock, 50, "arrive")
    assert db.load("test").entities["nora"]["location_id"] == "square"
    with pytest.raises(InvalidEvent):
        repay(db, svc, 1, "distant")
    state = tick(db, clock, 70, "deadline")
    assert state.loan_contracts["loan"]["remaining"] == 8
    assert state.loan_contracts["loan"]["status"] == "overdue"
    assert state.resources["nora"]["coin_copper"] == 8
    assert db.verify("test").to_dict() == state.to_dict()


def test_duplicate_payment_and_stale_revision_no_double_transfer(world):
    db, clock, svc = world
    propose(db, svc)
    accept(db, svc)
    before = db.load("test")
    first = repay(db, svc, 2, "once")
    with pytest.raises(DuplicateCommand):
        repay(db, svc, 2, "once")
    with pytest.raises(RevisionConflict):
        svc.repay("test", "nora", "loan", "old", 1,
                  expected_revision=before.revision)
    assert db.load("test").to_dict() == first.to_dict()
    assert first.loan_contracts["loan"]["remaining"] == 6


def test_bad_event_after_funding_in_batch_rolls_back_every_coin(world):
    db, clock, svc = world
    propose(db, svc)
    prior = db.load("test").to_dict()
    evs = [
        ev("LoanAccepted", {"id": "loan"}, actor="nora"),
        ev("LoanRepaid", {"id": "bad", "contract_id": "loan", "amount": 9},
           actor="nora"),
    ]
    with pytest.raises(InvalidEvent):
        db.append("test", "atomic-invalid", prior["revision"], evs,
                  loan_authorized=True)
    assert db.load("test").to_dict() == prior
    assert db.db.execute(
        "SELECT count(*) FROM commands WHERE command_id='atomic-invalid'"
    ).fetchone()[0] == 0


def test_closed_session_does_not_advance_due_or_allow_new_loan(world):
    db, clock, svc = world
    propose(db, svc)
    accept(db, svc)
    old = db.load("test").to_dict()
    clock.close_session("test")
    with pytest.raises(SessionClosed):
        tick(db, clock, 120, "offline")
    with pytest.raises(SessionClosed):
        repay(db, svc, 1, "offline-pay")
    with pytest.raises(InvalidEvent, match="active"):
        db.append("test", "offline-direct", old["revision"], [
            ev("LoanRepaid", {
                "id": "false", "contract_id": "loan", "amount": 1
            }, actor="nora")], loan_authorized=True)
    assert db.load("test").to_dict() == old
    clock.open_session("test")
    final = tick(db, clock, 120, "resumed")
    assert final.loan_contracts["loan"]["status"] == "overdue"


def test_insufficient_clock_event_budget_rolls_back_default(world):
    db, clock, svc = world
    propose(db, svc)
    accept(db, svc)
    old = db.load("test").to_dict()
    limited = TimeEngine(db, max_events_per_advance=1)
    with pytest.raises(AdvanceLimitExceeded):
        limited.advance("test", seconds=120, command_id="too-little",
                        expected_revision=old["revision"])
    assert db.load("test").to_dict() == old
    final = tick(db, clock, 120, "normal")
    assert final.loan_contracts["loan"]["status"] == "overdue"
    assert db.verify("test").to_dict() == final.to_dict()


def test_forged_snapshot_breaches_repayment_math_or_due_time(world):
    db, clock, svc = world
    propose(db, svc)
    accept(db, svc)
    repay(db, svc, 2, "part")
    before = db.load("test")
    for mode in ("missing", "fake-money", "wrong-principal",
                 "wrong-repaid", "fake-due", "lost-schedule", "fake-parties"):
        changed = before.to_dict()
        c = changed["loan_contracts"]["loan"]
        if mode == "missing":
            del changed["loan_repayments"]
        elif mode == "fake-money":
            changed["loan_repayments"]["part"]["creditor_after"] += 4
        elif mode == "wrong-principal":
            c["principal"] += 1
        elif mode == "wrong-repaid":
            c["repaid"] += 1
        elif mode == "fake-due":
            c["due_at"] += 90
        elif mode == "lost-schedule":
            del changed["scheduled"]["loan:due:loan"]
        else:
            changed["loan_repayments"]["part"]["lender_id"] = "huda"
        with pytest.raises(ValueError):
            WorldState.from_dict(changed)
    assert db.verify("test").to_dict() == before.to_dict()


def test_exact_due_second_partial_payment_before_clock_signal_remains_on_time(world):
    db, clock, svc = world
    propose(db, svc)
    accept(db, svc)
    # Clock can advance exactly TO the deadline without skipping its
    # appointment. The payment event occurs before due-signal firing.
    old = db.load("test")
    advanced = db.append("test", "clock-to-boundary", old.revision, [
        ev("TimeAdvanced", {"from": 0, "to": 120}, at=120),
    ], clock_authorized=True)
    assert advanced.time == 120
    partial = repay(db, svc, 3, "at-boundary")
    assert partial.loan_repayments["at-boundary"]["late"] is False
    assert partial.loan_contracts["loan"]["remaining"] == 5
    fired = db.append("test", "fire-on-boundary", rev(db), [
        ev("ScheduledEventFired", {"id": "loan:due:loan"}, at=120),
    ], clock_authorized=True)
    assert fired.loan_contracts["loan"]["status"] == "overdue"
    assert fired.loan_contracts["loan"]["defaulted_at"] == 120
    assert fired.loan_repayments["at-boundary"]["late"] is False
    assert db.verify("test").to_dict() == fired.to_dict()


def test_exact_due_second_full_payment_before_clock_signal_clears_deadline(world):
    db, clock, svc = world
    propose(db, svc)
    accept(db, svc)
    old = db.load("test")
    db.append("test", "clock-to-due", old.revision, [
        ev("TimeAdvanced", {"from": 0, "to": 120}, at=120),
    ], clock_authorized=True)
    settled = repay(db, svc, 8, "paid-at-due")
    assert settled.loan_contracts["loan"]["status"] == "paid"
    assert settled.loan_contracts["loan"]["defaulted_at"] is None
    assert settled.loan_repayments["paid-at-due"]["late"] is False
    assert "loan:due:loan" not in settled.scheduled
    assert db.verify("test").to_dict() == settled.to_dict()
