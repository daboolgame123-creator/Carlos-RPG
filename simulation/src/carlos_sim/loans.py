"""02-D: consensual funded NPC loans, partial cash repayment, and recorded arrears.

An offer creates NO money and NO debt. Only actual borrower acceptance moves
known copper and creates the debt. A due signal marks nonpayment; it never
seizes wealth or automatically clears the account. No real-world legal claims.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .domain import DomainEvent, WorldState
from .store import SQLiteEventStore, RevisionConflict
from .time_engine import TimeEngine
from .market import _id, _balance, _present, MAX_AMOUNT, MONEY

MAX_LOAN = 10000
MAX_TERM = 30 * 24 * 3600
CONTRACT_KEYS = {
    "lender_id", "borrower_id", "site_id", "principal", "term_seconds",
    "proposed_at", "accepted_at", "due_at", "status", "repaid",
    "remaining", "defaulted_at", "paid_at", "closed_at", "disbursement",
}
TRANSFER_KEYS = {
    "lender_before", "lender_after", "borrower_before", "borrower_after",
}
PAYMENT_KEYS = {
    "contract_id", "borrower_id", "lender_id", "amount", "paid_at", "late",
    "debtor_before", "debtor_after", "creditor_before", "creditor_after",
}


def _positive(value: Any, limit: int) -> bool:
    return type(value) is int and 1 <= value <= limit


def _due_signal(contract_id: str) -> str:
    return "loan:due:" + contract_id


def _both_here(state: dict[str, Any], lender: str, borrower: str,
               site: str | None = None) -> bool:
    if (not isinstance(lender, str) or not isinstance(borrower, str)
            or not _id(lender) or not _id(borrower) or lender == borrower):
        return False
    entities = state["entities"]
    if lender not in entities or borrower not in entities:
        return False
    source_site = entities[lender]["location_id"]
    return (source_site == entities[borrower]["location_id"]
            and (site is None or source_site == site)
            and source_site in state["locations"]
            and _present(state, lender, source_site)
            and _present(state, borrower, source_site))


def _copper(state: dict[str, Any], who: str) -> int:
    balance = state["resources"].get(who, {}).get(MONEY)
    if not _balance(balance):
        raise ValueError("loan requires an explicitly known copper account")
    return balance


def propose_loan(state: dict[str, Any], event: DomainEvent, *,
                 loan_authorized: bool) -> None:
    p = event.data
    if (not loan_authorized
            or set(p) != {"id", "lender_id", "borrower_id",
                           "principal", "term_seconds"}
            or not _id(p["id"]) or p["id"] in state["loan_contracts"]):
        raise ValueError("loan offer needs trusted capability and unused contract ID")
    lender, borrower = p["lender_id"], p["borrower_id"]
    if (event.actor_id != lender
            or not _both_here(state, lender, borrower)
            or not _positive(p["principal"], MAX_LOAN)
            or not _positive(p["term_seconds"], MAX_TERM)):
        raise ValueError("loan terms require genuine local creditor and debtor")
    site = state["entities"][lender]["location_id"]
    state["loan_contracts"][p["id"]] = {
        "lender_id": lender, "borrower_id": borrower,
        "site_id": site, "principal": p["principal"],
        "term_seconds": p["term_seconds"], "proposed_at": state["time"],
        "accepted_at": None, "due_at": None, "status": "proposed",
        "repaid": 0, "remaining": None, "defaulted_at": None,
        "paid_at": None, "closed_at": None, "disbursement": None,
    }


def close_offer(state: dict[str, Any], event: DomainEvent, *,
                loan_authorized: bool) -> None:
    p = event.data
    if (not loan_authorized or set(p) != {"id", "decision"}
            or not _id(p["id"]) or p["decision"] not in ("withdrawn", "declined")):
        raise ValueError("invalid trusted loan-offer closure")
    loan = state["loan_contracts"].get(p["id"])
    if loan is None or loan["status"] != "proposed":
        raise ValueError("only pending unfunded offer can be withdrawn or declined")
    expected = loan["lender_id"] if p["decision"] == "withdrawn" else loan["borrower_id"]
    if (event.actor_id != expected or not _both_here(
            state, loan["lender_id"], loan["borrower_id"], loan["site_id"])):
        raise ValueError("only the local contracting party can reject or withdraw")
    loan["status"] = p["decision"]
    loan["closed_at"] = state["time"]


def accept_loan(state: dict[str, Any], event: DomainEvent, *,
                loan_authorized: bool) -> None:
    p = event.data
    if not loan_authorized or set(p) != {"id"} or not _id(p["id"]):
        raise ValueError("loan acceptance requires trusted authority and ID")
    contract = state["loan_contracts"].get(p["id"])
    if contract is None or contract["status"] != "proposed":
        raise ValueError("only a pending genuine loan can be accepted")
    lender, borrower = contract["lender_id"], contract["borrower_id"]
    if event.actor_id != borrower or not _both_here(
            state, lender, borrower, contract["site_id"]):
        raise ValueError("debtor must personally accept with creditor present")
    credit = _copper(state, lender)
    debit = _copper(state, borrower)
    principal = contract["principal"]
    due = state["time"] + contract["term_seconds"]
    sig = _due_signal(p["id"])
    if (credit < principal or debit + principal > MAX_AMOUNT
            or due > 2**63 - 1 or sig in state["scheduled"]):
        raise ValueError("real lender funds, borrower capacity and due are required")
    state["resources"][lender][MONEY] = credit - principal
    state["resources"][borrower][MONEY] = debit + principal
    contract["accepted_at"] = state["time"]
    contract["due_at"] = due
    contract["status"] = "active"
    contract["remaining"] = principal
    contract["disbursement"] = {
        "lender_before": credit, "lender_after": credit - principal,
        "borrower_before": debit, "borrower_after": debit + principal,
    }
    state["scheduled"][sig] = {
        "due": due, "order": state["next_schedule_order"],
        "kind": "signal", "interrupt": False,
        "payload": {"__loan_due": p["id"]},
    }
    state["next_schedule_order"] += 1


def repay_loan(state: dict[str, Any], event: DomainEvent, *,
               loan_authorized: bool) -> None:
    p = event.data
    if (not loan_authorized or set(p) != {"id", "contract_id", "amount"}
            or not _id(p["id"]) or p["id"] in state["loan_repayments"]
            or not _id(p["contract_id"]) or not _positive(p["amount"], MAX_LOAN)):
        raise ValueError("repayment requires trusted authority, positive amount and unique ID")
    contract = state["loan_contracts"].get(p["contract_id"])
    if contract is None or contract["status"] not in ("active", "overdue"):
        raise ValueError("repayment requires existing outstanding funded debt")
    borrower, lender = contract["borrower_id"], contract["lender_id"]
    if (event.actor_id != borrower or
            not _both_here(state, lender, borrower)):
        raise ValueError("real debtor and creditor must meet to exchange copper")
    amount = p["amount"]
    borrower_coins, lender_coins = _copper(state, borrower), _copper(state, lender)
    if (amount > contract["remaining"] or amount > borrower_coins
            or lender_coins + amount > MAX_AMOUNT):
        raise ValueError("cannot repay missing copper, excess debt or overflow creditor")
    late = contract["status"] == "overdue"
    state["resources"][borrower][MONEY] = borrower_coins - amount
    state["resources"][lender][MONEY] = lender_coins + amount
    contract["repaid"] += amount
    contract["remaining"] -= amount
    state["loan_repayments"][p["id"]] = {
        "contract_id": p["contract_id"], "borrower_id": borrower,
        "lender_id": lender, "amount": amount, "paid_at": state["time"],
        "late": late, "debtor_before": borrower_coins,
        "debtor_after": borrower_coins - amount,
        "creditor_before": lender_coins, "creditor_after": lender_coins + amount,
    }
    if contract["remaining"] == 0:
        contract["status"] = "paid"
        contract["paid_at"] = state["time"]
        contract["closed_at"] = state["time"]
        # Retire a legitimate due date on full early payment: only this
        # verified reducer may remove a protected due signal.
        state["scheduled"].pop(_due_signal(p["contract_id"]), None)


def mark_due(state: dict[str, Any], schedule_id: str,
             loan_id: Any, now: int) -> None:
    contract = state["loan_contracts"].get(loan_id) if isinstance(loan_id, str) else None
    if (contract is None or contract["status"] != "active"
            or contract["remaining"] <= 0
            or schedule_id != _due_signal(loan_id)
            or now != contract["due_at"]):
        raise ValueError("only exact scheduled outstanding loan can become overdue")
    contract["status"] = "overdue"
    contract["defaulted_at"] = now
    # NOT cancelled or forgiven: the full remaining loan persists.


def validate_loans(state: dict[str, Any]) -> None:
    contracts, repayments = state["loan_contracts"], state["loan_repayments"]
    if not isinstance(contracts, dict) or not isinstance(repayments, dict):
        raise ValueError("loan ledgers must be mappings")
    totals: dict[str, int] = {}
    for ident, p in repayments.items():
        if (not _id(ident) or not isinstance(p, dict) or set(p) != PAYMENT_KEYS
                or not _id(p["contract_id"]) or p["contract_id"] not in contracts):
            raise ValueError("invalid historic loan repayment")
        contract = contracts[p["contract_id"]]
        if (p["lender_id"] != contract["lender_id"]
                or p["borrower_id"] != contract["borrower_id"]
                or not _positive(p["amount"], MAX_LOAN)
                or type(p["paid_at"]) is not int or p["paid_at"] < 0
                or p["paid_at"] > state["time"]
                or contract["accepted_at"] is None
                or p["paid_at"] < contract["accepted_at"]
                or type(p["late"]) is not bool
                or p["late"] != (p["paid_at"] > contract["due_at"])):
            raise ValueError("repayment date/party inconsistent with loan contract")
        entries = [p[k] for k in ("debtor_before", "debtor_after",
                                  "creditor_before", "creditor_after")]
        if not all(_balance(x) for x in entries):
            raise ValueError("repayment lacks actual known copper balances")
        if (p["debtor_before"] - p["debtor_after"] != p["amount"]
                or p["creditor_after"] - p["creditor_before"] != p["amount"]):
            raise ValueError("repayment must conserve copper, not invent it")
        totals[p["contract_id"]] = totals.get(p["contract_id"], 0) + p["amount"]
    for ident, c in contracts.items():
        if (not _id(ident) or not isinstance(c, dict) or set(c) != CONTRACT_KEYS
                or not _id(c["lender_id"]) or c["lender_id"] not in state["npcs"]
                or not _id(c["borrower_id"]) or c["borrower_id"] not in state["npcs"]
                or c["lender_id"] == c["borrower_id"]
                or not _id(c["site_id"]) or c["site_id"] not in state["locations"]
                or not _positive(c["principal"], MAX_LOAN)
                or not _positive(c["term_seconds"], MAX_TERM)
                or type(c["proposed_at"]) is not int
                or not 0 <= c["proposed_at"] <= state["time"]
                or type(c["repaid"]) is not int or c["repaid"] < 0
                or c["repaid"] > c["principal"]
                or c["repaid"] != totals.get(ident, 0)
                or c["status"] not in ("proposed", "declined", "withdrawn",
                                      "active", "overdue", "paid")):
            raise ValueError("loan contract data/provenance inconsistent")
        if c["status"] in ("proposed", "declined", "withdrawn"):
            if (c["repaid"] != 0 or c["remaining"] is not None
                    or c["accepted_at"] is not None or c["due_at"] is not None
                    or c["disbursement"] is not None
                    or c["paid_at"] is not None or c["defaulted_at"] is not None
                    or _due_signal(ident) in state["scheduled"]):
                raise ValueError("unfunded offers cannot become actual debts")
            if c["status"] == "proposed":
                if c["closed_at"] is not None:
                    raise ValueError("proposed offer cannot have closure timestamp")
            elif (type(c["closed_at"]) is not int or
                  not c["proposed_at"] <= c["closed_at"] <= state["time"]):
                raise ValueError("decline/withdrawal requires actual closure")
            continue
        if (type(c["accepted_at"]) is not int
                or not c["proposed_at"] <= c["accepted_at"] <= state["time"]
                or type(c["due_at"]) is not int
                or c["due_at"] != c["accepted_at"] + c["term_seconds"]
                or not 0 <= c["remaining"] <= c["principal"]
                or c["remaining"] != c["principal"] - c["repaid"]
                or not isinstance(c["disbursement"], dict)
                or set(c["disbursement"]) != TRANSFER_KEYS):
            raise ValueError("funded loan requires coherent disbursement and due")
        transfer = c["disbursement"]
        if (not all(_balance(transfer[x]) for x in TRANSFER_KEYS)
                or transfer["lender_before"] - transfer["lender_after"]
                != c["principal"]
                or transfer["borrower_after"] - transfer["borrower_before"]
                != c["principal"]):
            raise ValueError("loan disbursement must conserve known copper")
        due_key = _due_signal(ident)
        if c["status"] == "active":
            sig = state["scheduled"].get(due_key)
            if (c["remaining"] <= 0 or c["due_at"] < state["time"]
                    or c["defaulted_at"] is not None or c["paid_at"] is not None
                    or c["closed_at"] is not None
                    or sig is None or sig["due"] != c["due_at"]
                    or sig["kind"] != "signal" or sig["interrupt"]
                    or sig["payload"] != {"__loan_due": ident}):
                raise ValueError("active loan requires exact future due appointment")
        elif c["status"] == "overdue":
            if (c["remaining"] <= 0 or c["due_at"] > state["time"]
                    or c["defaulted_at"] != c["due_at"]
                    or c["closed_at"] is not None or c["paid_at"] is not None
                    or due_key in state["scheduled"]):
                raise ValueError("overdue status cannot remove debt or rewrite due")
        else:  # paid
            if (c["remaining"] != 0 or c["repaid"] != c["principal"]
                    or type(c["paid_at"]) is not int
                    or c["paid_at"] < c["accepted_at"]
                    or c["paid_at"] > state["time"]
                    or c["closed_at"] != c["paid_at"]
                    or due_key in state["scheduled"]
                    or (c["defaulted_at"] is not None
                        and (c["defaulted_at"] != c["due_at"]
                             or c["paid_at"] < c["defaulted_at"]))
                    or (c["defaulted_at"] is None
                        and c["paid_at"] > c["due_at"])):
                raise ValueError("paid loan must have exact settlement and history")
    for sid, schedule in state["scheduled"].items():
        if "__loan_due" in schedule["payload"]:
            ident = schedule["payload"]["__loan_due"]
            if (not isinstance(ident, str) or sid != _due_signal(ident)
                    or ident not in contracts or contracts[ident]["status"] != "active"):
                raise ValueError("forged or orphaned loan due schedule")


@dataclass(frozen=True)
class LoanResult:
    contract_id: str
    state: WorldState


class NPCLoanService:
    """Explicit trusted-local consent/funding/repayment only; no autonomous debt AI."""

    def __init__(self, store: SQLiteEventStore, clock: TimeEngine):
        if clock.store is not store:
            raise ValueError("loan, clock and SQLite store must match")
        self.store, self.clock = store, clock

    def _event(self, world_id: str, contract_id: str, command_id: str,
               expected_revision: int, kind: str, actor: str,
               data: dict[str, Any]) -> LoanResult:
        self.clock._require_session(world_id)
        state = self.store.load(world_id)
        if type(expected_revision) is not int or expected_revision != state.revision:
            raise RevisionConflict("stale loan instruction")
        event = DomainEvent(kind, actor, "trusted local copper contract",
                            state.time, data)
        result = self.store.append(world_id, "loan:" + command_id,
                                   expected_revision, [event],
                                   loan_authorized=True)
        return LoanResult(contract_id, result)

    def propose(self, world_id: str, lender_id: str, borrower_id: str,
                contract_id: str, principal: int, term_seconds: int, *,
                expected_revision: int) -> LoanResult:
        return self._event(world_id, contract_id, "offer:" + contract_id,
                           expected_revision, "LoanProposed", lender_id,
                           {"id": contract_id, "lender_id": lender_id,
                            "borrower_id": borrower_id, "principal": principal,
                            "term_seconds": term_seconds})

    def accept(self, world_id: str, borrower_id: str, contract_id: str, *,
               expected_revision: int) -> LoanResult:
        return self._event(world_id, contract_id, "accept:" + contract_id,
                           expected_revision, "LoanAccepted", borrower_id,
                           {"id": contract_id})

    def close(self, world_id: str, actor_id: str, contract_id: str,
              decision: str, *, expected_revision: int) -> LoanResult:
        return self._event(world_id, contract_id, "close:" + contract_id,
                           expected_revision, "LoanClosed", actor_id,
                           {"id": contract_id, "decision": decision})

    def repay(self, world_id: str, borrower_id: str, contract_id: str,
              payment_id: str, amount: int, *, expected_revision: int) -> LoanResult:
        return self._event(world_id, contract_id, "payment:" + payment_id,
                           expected_revision, "LoanRepaid", borrower_id,
                           {"id": payment_id, "contract_id": contract_id,
                            "amount": amount})

    def my_loans(self, world_id: str, npc_id: str) -> tuple[dict[str, Any], ...]:
        self.clock._require_session(world_id)
        state = self.store.load(world_id)
        if npc_id not in state.npcs:
            raise PermissionError("local NPC contract identity required")
        result = []
        for ident, p in sorted(state.loan_contracts.items()):
            if npc_id not in (p["lender_id"], p["borrower_id"]):
                continue
            result.append({
                "id": ident,
                "role": "lender" if p["lender_id"] == npc_id else "borrower",
                "counterparty_id": (p["borrower_id"] if p["lender_id"] == npc_id
                                    else p["lender_id"]),
                "principal": p["principal"], "remaining": p["remaining"],
                "status": p["status"], "due_at": p["due_at"],
                "defaulted_at": p["defaulted_at"],
            })
        return tuple(result)
