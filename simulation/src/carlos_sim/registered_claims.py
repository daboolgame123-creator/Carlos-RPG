"""04-A/J1c2a: consensual assignment of a *recorded historical claim*.

Not present legal title, not physical inventory, not permission to seize goods.
Distinct from J1c1 collection permission, an accepted assignment changes only
the holder of a quantified recorded historical claim on a registered origin.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from .domain import DomainEvent, WorldState
from .market import _id, _present, MAX_QUANTITY
from .store import SQLiteEventStore, RevisionConflict
from .time_engine import TimeEngine

MAX_OFFERS = 1000
MAX_DURATION = 7 * 24 * 3600
OFFER_KEYS = {"origin_id", "from_account", "proposer_id", "recipient_id",
              "quantity", "site_id", "opened_at", "expires_at", "status",
              "resolved_at"}
TRANSFER_KEYS = {"offer_id", "origin_id", "from_account", "recipient_id",
                 "quantity", "site_id", "accepted_at"}
TRANSFER_EVENTS = frozenset(("RegisteredClaimTransferOffered",
                             "RegisteredClaimTransferAccepted",
                             "RegisteredClaimTransferCancelled"))


def initialize_claim(state: dict[str, Any], origin_id: str) -> None:
    """Only invoked by an authenticated J1a original-registration event."""
    origin = state["property_title_origins"][origin_id]
    if origin_id in state["registered_claim_balances"]:
        raise ValueError("historical claim already initialized")
    state["registered_claim_balances"][origin_id] = {
        origin["recorded_beneficiary_id"]: origin["quantity"]
    }


def _represents(state: dict[str, Any], actor: str, account: str, site: str) -> bool:
    if not _id(actor) or not _id(account) or not _present(state, actor, site):
        return False
    if account in state["npcs"]:
        return actor == account
    stall = state["market_stalls"].get(account)
    return (account == site and account in state["locations"]
            and stall is not None and stall["keeper_id"] == actor)


def _reserved(state: dict[str, Any], origin: str, account: str) -> int:
    return sum(item["quantity"] for item in state["registered_claim_offers"].values()
               if item["origin_id"] == origin and item["from_account"] == account
               and item["status"] == "open"
               and item["expires_at"] > state["time"])


def offer_claim(state: dict[str, Any], event: DomainEvent, *,
                claim_transfer_authorized: bool) -> None:
    p = event.data
    if (not claim_transfer_authorized
            or set(p) != {"id", "origin_id", "from_account", "recipient_id",
                          "quantity", "expires_at"}
            or not _id(p["id"])
            or p["id"] in state["registered_claim_offers"]
            or len(state["registered_claim_offers"]) >= MAX_OFFERS
            or not _id(p["origin_id"]) or not _id(p["from_account"])
            or not _id(p["recipient_id"])
            or type(p["quantity"]) is not int
            or not 1 <= p["quantity"] <= MAX_QUANTITY
            or type(p["expires_at"]) is not int
            or not state["time"] < p["expires_at"] <=
                min(2**63 - 1, state["time"] + MAX_DURATION)):
        raise ValueError("invalid local quantified claim assignment offer")
    origin, account, recipient = p["origin_id"], p["from_account"], p["recipient_id"]
    if (origin not in state["registered_claim_balances"]
            or recipient not in state["npcs"] or account == recipient):
        raise ValueError("claim transfer requires a registered origin and distinct NPC recipient")
    site = state["entities"][event.actor_id]["location_id"] if event.actor_id in state["npcs"] else None
    if (site is None
            or not _represents(state, event.actor_id, account, site)
            or not _present(state, recipient, site)):
        raise ValueError("both actual parties must meet and proposer must represent the claim account")
    available = state["registered_claim_balances"][origin].get(account, 0)
    if type(available) is not int or available - _reserved(state, origin, account) < p["quantity"]:
        raise ValueError("historical claim transfer would double-assign reserved quantity")
    state["registered_claim_offers"][p["id"]] = {
        "origin_id": origin, "from_account": account,
        "proposer_id": event.actor_id, "recipient_id": recipient,
        "quantity": p["quantity"], "site_id": site,
        "opened_at": state["time"], "expires_at": p["expires_at"],
        "status": "open", "resolved_at": None,
    }


def accept_claim(state: dict[str, Any], event: DomainEvent, *,
                 claim_transfer_authorized: bool) -> None:
    p = event.data
    if not claim_transfer_authorized or set(p) != {"id"} or not _id(p["id"]):
        raise ValueError("claim acceptance requires trusted separate capability")
    item = state["registered_claim_offers"].get(p["id"])
    if (item is None or item["status"] != "open"
            or not item["opened_at"] <= state["time"] < item["expires_at"]
            or event.actor_id != item["recipient_id"]
            or not _present(state, item["recipient_id"], item["site_id"])
            or not _represents(state, item["proposer_id"],
                               item["from_account"], item["site_id"])):
        raise ValueError("claim can only transfer through actual recipient's local acceptance")
    balances = state["registered_claim_balances"][item["origin_id"]]
    old = balances.get(item["from_account"], 0)
    target = balances.get(item["recipient_id"], 0)
    if old < item["quantity"] or target + item["quantity"] > 2**31-1:
        raise ValueError("registered claim quantity unavailable at acceptance")
    balances[item["from_account"]] = old - item["quantity"]
    if balances[item["from_account"]] == 0:
        del balances[item["from_account"]]
    balances[item["recipient_id"]] = target + item["quantity"]
    item["status"] = "accepted"
    item["resolved_at"] = state["time"]
    if p["id"] in state["registered_claim_transfers"]:
        raise ValueError("accepted historical transfer already exists")
    state["registered_claim_transfers"][p["id"]] = {
        "offer_id": p["id"], "origin_id": item["origin_id"],
        "from_account": item["from_account"],
        "recipient_id": item["recipient_id"],
        "quantity": item["quantity"], "site_id": item["site_id"],
        "accepted_at": state["time"],
    }


def cancel_claim(state: dict[str, Any], event: DomainEvent, *,
                 claim_transfer_authorized: bool) -> None:
    p = event.data
    if not claim_transfer_authorized or set(p) != {"id"} or not _id(p["id"]):
        raise ValueError("claim offer cancellation requires trusted capability")
    item = state["registered_claim_offers"].get(p["id"])
    if (item is None or item["status"] != "open"
            or event.actor_id != item["proposer_id"]
            or not _represents(state, event.actor_id,
                               item["from_account"], item["site_id"])
            or not _present(state, item["recipient_id"], item["site_id"])):
        raise ValueError("claim offer may only be withdrawn locally by its issuer")
    item["status"] = "cancelled"
    item["resolved_at"] = state["time"]


def validate_claims(state: dict[str, Any]) -> None:
    """Derive balances from immutable origin plus accepted agreements.

    This checks current balances against transfer receipts, not legal title.
    Full event replay proves event order, prior presence and consent.
    """
    balances = state["registered_claim_balances"]
    offers = state["registered_claim_offers"]
    transfers = state["registered_claim_transfers"]
    origins = state["property_title_origins"]
    if (type(balances) is not dict or type(offers) is not dict
            or type(transfers) is not dict or set(balances) != set(origins)
            or len(offers) > MAX_OFFERS or len(transfers) > len(offers)):
        raise ValueError("invalid registered claim ledgers")
    expected = {
        origin_id: {row["recorded_beneficiary_id"]: row["quantity"]}
        for origin_id, row in origins.items()
    }
    all_sites = state["locations"]
    for ident, item in offers.items():
        if (not _id(ident) or type(item) is not dict or set(item) != OFFER_KEYS
                or item["origin_id"] not in origins
                or not _id(item["from_account"])
                or item["from_account"] not in state["npcs"]
                    and item["from_account"] not in all_sites
                or item["recipient_id"] not in state["npcs"]
                or item["from_account"] == item["recipient_id"]
                or item["proposer_id"] not in state["npcs"]
                or item["site_id"] not in all_sites
                or type(item["quantity"]) is not int
                or not 1 <= item["quantity"] <= origins[item["origin_id"]]["quantity"]
                or type(item["opened_at"]) is not int
                or not 0 <= item["opened_at"] <= state["time"]
                or type(item["expires_at"]) is not int
                or not item["opened_at"] < item["expires_at"] <=
                    item["opened_at"] + MAX_DURATION
                or item["expires_at"] > 2**63-1
                or item["status"] not in {"open", "accepted", "cancelled"}
                or (item["status"] == "open") != (item["resolved_at"] is None)
                or (item["resolved_at"] is not None
                    and (type(item["resolved_at"]) is not int
                         or not item["opened_at"] <= item["resolved_at"] <= state["time"]))
                or (item["status"] == "accepted"
                    and item["resolved_at"] >= item["expires_at"])
                or (item["from_account"] in all_sites and
                    (item["from_account"] != item["site_id"]
                     or state["market_stalls"].get(item["site_id"], {}).get("keeper_id")
                         != item["proposer_id"]))
                or (item["from_account"] in state["npcs"]
                    and item["proposer_id"] != item["from_account"])):
            raise ValueError("malformed registered claim agreement")
    for ident, transfer in transfers.items():
        if (ident not in offers or type(transfer) is not dict
                or set(transfer) != TRANSFER_KEYS
                or transfer["offer_id"] != ident
                or offers[ident]["status"] != "accepted"):
            raise ValueError("invalid registered claim assignment receipt")
        offered = offers[ident]
        if (any(transfer[k] != offered[k] for k in
                ("origin_id", "from_account", "recipient_id", "quantity", "site_id"))
                or transfer["accepted_at"] != offered["resolved_at"]):
            raise ValueError("claim transfer receipt contradicts acceptance")
        origin_id = offered["origin_id"]
        from_account, to_account, q = (offered["from_account"],
                                       offered["recipient_id"], offered["quantity"])
        from_balance = expected[origin_id].get(from_account, 0)
        # Cross-agreement chronological ordering is authoritative on full
        # event replay. Snapshot-only reconstruction is order-independent
        # for final balances, but must not reject valid intermediate transfers.
        expected[origin_id][from_account] = from_balance - q
        expected[origin_id][to_account] = expected[origin_id].get(to_account, 0) + q
    for ident, offer in offers.items():
        if (offer["status"] == "accepted") != (ident in transfers):
            raise ValueError("accepted claim has mismatched receipt")
    for origin_id, holders in balances.items():
        if (type(holders) is not dict or not holders
                or any(not _id(holder) or
                       holder not in state["npcs"] and holder not in all_sites
                       or type(q) is not int or q <= 0
                       for holder, q in holders.items())
                or sum(holders.values()) != origins[origin_id]["quantity"]):
            raise ValueError("registered claim conservation violated")
        expected_holders = {k: v for k, v in expected[origin_id].items() if v}
        if holders != expected_holders:
            raise ValueError("claim ledger differs from actual accepted agreement history")
    reserved = {}
    for offer in offers.values():
        if offer["status"] == "open" and offer["expires_at"] > state["time"]:
            key = (offer["origin_id"], offer["from_account"])
            reserved[key] = reserved.get(key, 0) + offer["quantity"]
    for (origin_id, account), quantity in reserved.items():
        if quantity > balances[origin_id].get(account, 0):
            raise ValueError("current claim proposals exceed account balance")


@dataclass(frozen=True)
class ClaimAssignmentResult:
    offer_id: str
    state: WorldState


class NPCRegisteredClaimService:
    """Trusted local handshake only: caller supplies authenticated NPC identity."""

    def __init__(self, store: SQLiteEventStore, clock: TimeEngine):
        if clock.store is not store:
            raise ValueError("claim assignment requires one shared clock/store")
        self.store, self.clock = store, clock

    def _write(self, world_id: str, actor: str, offer_id: str,
               event_type: str, fields: dict[str, Any], *,
               expected_revision: int) -> ClaimAssignmentResult:
        self.clock._require_session(world_id)
        previous = self.store.load(world_id)
        if type(expected_revision) is not int or expected_revision != previous.revision:
            raise RevisionConflict("stale registered claim agreement")
        current = self.store.append(world_id, "registered-claim:" + event_type + ":" + offer_id,
                                    expected_revision, [DomainEvent(
                                        event_type, actor,
                                        "in-person registered historical claim agreement",
                                        previous.time, {"id": offer_id, **fields})],
                                    claim_transfer_authorized=True)
        return ClaimAssignmentResult(offer_id, current)

    def offer(self, world_id: str, proposer_id: str, offer_id: str,
              origin_id: str, from_account: str, recipient_id: str,
              quantity: int, *, expires_at: int,
              expected_revision: int) -> ClaimAssignmentResult:
        return self._write(world_id, proposer_id, offer_id,
                           "RegisteredClaimTransferOffered", {
                               "origin_id": origin_id, "from_account": from_account,
                               "recipient_id": recipient_id, "quantity": quantity,
                               "expires_at": expires_at,
                           }, expected_revision=expected_revision)

    def accept(self, world_id: str, recipient_id: str, offer_id: str,
               *, expected_revision: int) -> ClaimAssignmentResult:
        return self._write(world_id, recipient_id, offer_id,
                           "RegisteredClaimTransferAccepted", {},
                           expected_revision=expected_revision)

    def cancel(self, world_id: str, proposer_id: str, offer_id: str,
               *, expected_revision: int) -> ClaimAssignmentResult:
        return self._write(world_id, proposer_id, offer_id,
                           "RegisteredClaimTransferCancelled", {},
                           expected_revision=expected_revision)
