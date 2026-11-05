"""04-A/J1b: loss-aware, strictly physical provenance for fungible commodities.

NEVER a current legal-title register or judicial proof. Tracking is opt-in by
J1a trusted original-entitlement registration. Only unequivocal physical
transfers have a certified successor; mixed partial removals lose certainty.
"""
from __future__ import annotations

from typing import Any
from .domain import DomainEvent, WorldState
from .market import _id, _balance, MAX_AMOUNT

LOT_KEYS = {"origin_id", "resource", "original_quantity", "known_holders",
            "unresolved_quantity", "exited_quantity"}
MOVE_KEYS = {"origin_id", "resource", "source_holder", "target_holder",
             "quantity", "kind", "event_kind", "event_revision", "at"}
KINDS = {"transferred", "unresolved", "exited"}
MAX_MOVES = 100000


def initialize_lot(state: dict[str, Any], origin_id: str) -> None:
    """Only called from J1a authenticated time-zero registration reducer."""
    origin = state["property_title_origins"][origin_id]
    if origin_id in state["property_custody_lots"]:
        raise ValueError("origin custody lot already exists")
    state["property_custody_lots"][origin_id] = {
        "origin_id": origin_id, "resource": origin["resource"],
        "original_quantity": origin["quantity"],
        "known_holders": {origin["source_owner_id"]: origin["quantity"]},
        "unresolved_quantity": 0, "exited_quantity": 0,
    }


def _transfers(event: DomainEvent, before: WorldState) -> tuple[tuple[str, str, str, int], ...]:
    """Explicit, independently validated physical transfer legs.

    A market barter carries TWO resources in opposite directions, not just
    the commodity. Coin is never a J1a tracked resource, but a bartered
    tracked food/tool can have a real custody history.
    """
    p, kind = event.data, event.event_type
    if kind == "PropertyTaken":
        return ((p["source_owner_id"], event.actor_id, p["resource"], p["quantity"]),)
    if kind == "MarketTradeExecuted":
        offer = before.market_offers[p["offer_id"]]
        q = p["quantity"]
        return (
            (offer["stock_owner_id"], p["buyer_id"], offer["resource"], q),
            (p["buyer_id"], offer["stock_owner_id"], offer["payment_resource"],
             q * offer["unit_price"]),
        )
    if kind == "AssistanceFulfilled":
        obligation = before.obligations[p["id"]]
        return ((obligation["provider"], obligation["requester"],
                 obligation["resource"], obligation["quantity"]),)
    return ()


def reconcile_lots(state: dict[str, Any], before: WorldState,
                   event: DomainEvent) -> None:
    """Run AFTER the existing reducer, BEFORE snapshot validation, for ALL events.

    It is not an optional caller switch: every stock mutation is inspected.
    This is a pure in-memory projection, committed by the existing atomic store.
    """
    lots = state["property_custody_lots"]
    if not lots:
        return
    transfers = {(source, resource): (dest, q)
                 for source, dest, resource, q in _transfers(event, before)}
    rev, at = before.revision + 1, state["time"]
    stock_before, stock_after = before.resources, state["resources"]
    touched = {(holder, lot["resource"])
               for lot in lots.values() for holder in lot["known_holders"]}
    # The destination may hold previously certified units and will be covered
    # by the final validation after we update its known amount.
    seq = 0

    def log(origin_id: str, source: str, target: str | None,
            q: int, kind: str) -> None:
        nonlocal seq
        if len(state["property_custody_moves"]) >= MAX_MOVES:
            raise ValueError("custody audit capacity reached; refusing silent loss")
        seq += 1
        key = str(rev) + ":" + str(seq)
        state["property_custody_moves"][key] = {
            "origin_id": origin_id, "resource": lots[origin_id]["resource"],
            "source_holder": source, "target_holder": target,
            "quantity": q, "kind": kind, "event_kind": event.event_type,
            "event_revision": rev, "at": at,
        }

    def reduce_origin(ident: str, source: str, n: int, *,
                      target: str | None, kind: str) -> None:
        lot = lots[ident]
        current = lot["known_holders"].get(source, 0)
        if n <= 0 or n > current:
            raise ValueError("internal custody reduction violates known stock")
        if n == current:
            del lot["known_holders"][source]
        else:
            lot["known_holders"][source] = current - n
        if kind == "transferred":
            if target is None or target == source:
                raise ValueError("transfer must change custodians")
            lot["known_holders"][target] = lot["known_holders"].get(target, 0) + n
        elif kind == "exited":
            lot["exited_quantity"] += n
        elif kind == "unresolved":
            lot["unresolved_quantity"] += n
        else:
            raise ValueError("unrecognized custody transition")
        log(ident, source, target if kind == "transferred" else None, n, kind)

    for source, item in sorted(touched):
        original = stock_before.get(source, {}).get(item)
        current = stock_after.get(source, {}).get(item)
        if not _balance(original) or not _balance(current):
            # A verified origin guarantees initialized stock while its units
            # are certified there. Unknown/negative stock is never guessed.
            raise ValueError("known custody cannot inhabit unknown balances")
        if current >= original:
            continue
        n = original - current
        relevant = sorted((ident, lot["known_holders"][source])
                          for ident, lot in lots.items()
                          if lot["resource"] == item and source in lot["known_holders"])
        total_certified = sum(q for _, q in relevant)
        if total_certified > original:
            raise ValueError("certified lot stock exceeds physical stock")
        is_transfer = (source, item) in transfers
        if is_transfer:
            dest, quantity = transfers[(source, item)]
            res = item
            if (n != quantity
                    or stock_after.get(dest, {}).get(res)
                    != before.resources.get(dest, {}).get(res, -1) + quantity):
                raise ValueError("physical transfer does not match tracked balances")
            # Transfer whole stock, including all registered lots, or the
            # entire source is a single known origin. Otherwise ambiguity.
            unequivocal = n == original or (
                len(relevant) == 1 and total_certified == original)
            if unequivocal:
                for ident, q in relevant:
                    reduce_origin(ident, source, min(n, q), target=dest,
                                  kind="transferred")
            else:
                for ident, q in relevant:
                    reduce_origin(ident, source, q, target=None, kind="unresolved")
            continue

        # Recognized physical destruction/transformation. If provenance is
        # mixed or unregistered, do NOT assert the destroyed unit's origin.
        is_exit = (event.event_type in {"NPCFoodConsumed", "ProductionStarted"}
                   or (event.event_type == "ResourceChanged"
                       and event.data.get("source") == "consumption"))
        unequivocal = n == original or (
            len(relevant) == 1 and total_certified == original)
        for ident, q in relevant:
            if unequivocal and is_exit:
                reduce_origin(ident, source, min(n, q),
                              target=None, kind="exited")
            else:
                reduce_origin(ident, source, q,
                              target=None, kind="unresolved")


def validate_lots(state: dict[str, Any]) -> None:
    lots, movements = state["property_custody_lots"], state["property_custody_moves"]
    origins = state["property_title_origins"]
    if (type(lots) is not dict or type(movements) is not dict
            or len(lots) != len(origins) or len(movements) > MAX_MOVES
            or set(lots) != set(origins)):
        raise ValueError("origin and physical custody ledgers must correspond")
    per_balance: dict[tuple[str, str], int] = {}
    for ident, lot in lots.items():
        origin = origins[ident]
        if (not _id(ident) or type(lot) is not dict or set(lot) != LOT_KEYS
                or lot["origin_id"] != ident or lot["resource"] != origin["resource"]
                or lot["original_quantity"] != origin["quantity"]
                or type(lot["known_holders"]) is not dict
                or type(lot["unresolved_quantity"]) is not int
                or type(lot["exited_quantity"]) is not int
                or min(lot["unresolved_quantity"], lot["exited_quantity"]) < 0):
            raise ValueError("invalid custody lot")
        seen = lot["unresolved_quantity"] + lot["exited_quantity"]
        for holder, amount in lot["known_holders"].items():
            if (not _id(holder) or holder not in state["resources"]
                    or type(amount) is not int or amount <= 0):
                raise ValueError("custody holder must carry positive known stock")
            key = (holder, lot["resource"])
            per_balance[key] = per_balance.get(key, 0) + amount
            seen += amount
        if seen != origin["quantity"]:
            raise ValueError("origin quantity must be conserved across custody knowledge")
    for (holder, resource), certified in per_balance.items():
        if (not _balance(state["resources"][holder].get(resource))
                or certified > state["resources"][holder][resource]):
            raise ValueError("certified physical custody exceeds actual inventory")
    for ident, row in movements.items():
        if (not isinstance(ident, str) or not ident or len(ident) > 128
                or type(row) is not dict or set(row) != MOVE_KEYS
                or row["origin_id"] not in lots
                or row["resource"] != lots[row["origin_id"]]["resource"]
                or row["kind"] not in KINDS
                or not _id(row["source_holder"])
                or row["source_holder"] not in state["resources"]
                or (row["target_holder"] is not None
                    and (not _id(row["target_holder"])
                         or row["target_holder"] not in state["resources"]))
                or (row["kind"] == "transferred") != (row["target_holder"] is not None)
                or type(row["quantity"]) is not int or row["quantity"] <= 0
                or row["quantity"] > lots[row["origin_id"]]["original_quantity"]
                or type(row["event_revision"]) is not int
                or not 0 < row["event_revision"] <= state["revision"]
                or not ident.startswith(str(row["event_revision"]) + ":")
                or type(row["at"]) is not int or not 0 <= row["at"] <= state["time"]
                or not isinstance(row["event_kind"], str) or not row["event_kind"]):
            raise ValueError("invalid custody change provenance")


def custody_audit(world: WorldState, *, origin_id: str | None = None) -> dict:
    """Trusted auditor only. Must never be exposed to a normal NPC/player."""
    if origin_id is not None and origin_id not in world.property_custody_lots:
        raise ValueError("unknown registered origin")
    selected = (world.property_custody_lots.items() if origin_id is None
                else ((origin_id, world.property_custody_lots[origin_id]),))
    return {
        "lots": {k: dict(v) | {"known_holders": dict(v["known_holders"])}
                 for k, v in selected},
        "movements": tuple({"id": k, **dict(row)}
                           for k, row in world.property_custody_moves.items()
                           if origin_id is None or row["origin_id"] == origin_id),
    }
