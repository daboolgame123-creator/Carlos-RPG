"""04-A/J1a: historical original-entitlement registration only.

An origin is not contemporary legal title, transferable ownership, or a
determination about theft. No physical balance changes in this module.
"""
from __future__ import annotations

from typing import Any
from .domain import DomainEvent
from .market import _id, _balance, MONEY, FORBIDDEN, MAX_QUANTITY

MAX_ORIGINS = 1000
ORIGIN_KEYS = {"source_owner_id", "recorded_beneficiary_id", "resource",
               "quantity", "site_id", "registered_at", "record_kind",
               "source_balance_at_registration"}


def register_origin(state: dict[str, Any], event: DomainEvent, *,
                    bootstrap: bool) -> None:
    p = event.data
    if (not bootstrap or state["time"] != 0 or event.actor_id is not None
            or set(p) != {"id", "source_owner_id", "recorded_beneficiary_id",
                          "resource", "quantity", "site_id"}
            or not _id(p.get("id")) or p["id"] in state["property_title_origins"]
            or len(state["property_title_origins"]) >= MAX_ORIGINS):
        raise ValueError("initial entitlement record requires unique trusted bootstrap")
    source, beneficiary, site = (
        p["source_owner_id"], p["recorded_beneficiary_id"], p["site_id"])
    resource, quantity = p["resource"], p["quantity"]
    if (not _id(source) or not _id(beneficiary) or not _id(site)
            or site not in state["locations"]
            or source not in state["npcs"] and source not in state["locations"]
            or beneficiary not in state["npcs"] and beneficiary not in state["locations"]
            or not _id(resource) or resource == MONEY or resource in FORBIDDEN
            or type(quantity) is not int or not 1 <= quantity <= MAX_QUANTITY):
        raise ValueError("invalid physical origin or bounded resource")
    if source == site:
        steward = state["market_stalls"].get(site)
        if steward is None or beneficiary != site:
            raise ValueError("site-origin entitlement requires registered steward and site beneficiary")
    elif source not in state["npcs"] or beneficiary != source:
        # Do not invent title in a third party by changing the label.
        raise ValueError("personal origin beneficiary must be its original account holder")
    elif state["entities"][source]["location_id"] != site:
        raise ValueError("personal origin must be registered at the holder's existing site")
    balance = state["resources"].get(source, {}).get(resource)
    used = sum(row["quantity"] for row in state["property_title_origins"].values()
               if row["source_owner_id"] == source and row["resource"] == resource)
    if not _balance(balance) or used + quantity > balance:
        raise ValueError("cannot record original entitlement beyond actual known stock")
    state["property_title_origins"][p["id"]] = {
        "source_owner_id": source,
        "recorded_beneficiary_id": beneficiary,
        "resource": resource, "quantity": quantity, "site_id": site,
        "registered_at": 0, "record_kind": "historical_origin_only",
        "source_balance_at_registration": balance,
    }


def validate_origins(state: dict[str, Any]) -> None:
    records = state["property_title_origins"]
    if not isinstance(records, dict) or len(records) > MAX_ORIGINS:
        raise ValueError("invalid entitlement-origin collection")
    for ident, row in records.items():
        if (not _id(ident) or not isinstance(row, dict)
                or set(row) != ORIGIN_KEYS
                or row["source_owner_id"] not in state["npcs"]
                    and row["source_owner_id"] not in state["locations"]
                or row["recorded_beneficiary_id"] not in state["npcs"]
                    and row["recorded_beneficiary_id"] not in state["locations"]
                or row["site_id"] not in state["locations"]
                or not _id(row["resource"]) or row["resource"] == MONEY
                or row["resource"] in FORBIDDEN
                or type(row["quantity"]) is not int
                or not 1 <= row["quantity"] <= MAX_QUANTITY
                or not _balance(row["source_balance_at_registration"])
                or row["quantity"] > row["source_balance_at_registration"]
                or row["registered_at"] != 0
                or row["record_kind"] != "historical_origin_only"):
            raise ValueError("invalid origin evidence record")
        if row["source_owner_id"] == row["site_id"]:
            if (row["source_owner_id"] not in state["market_stalls"]
                    or row["recorded_beneficiary_id"] != row["site_id"]):
                raise ValueError("site origin lacks steward")
        elif (row["source_owner_id"] not in state["npcs"]
              or row["recorded_beneficiary_id"] != row["source_owner_id"]):
            raise ValueError("personal origin lacks original holder")
    allocation: dict[tuple[str, str], tuple[int, int]] = {}
    for row in records.values():
        key = (row["source_owner_id"], row["resource"])
        previous = allocation.get(key)
        if previous is not None and previous[1] != row["source_balance_at_registration"]:
            raise ValueError("historical source balance must be consistent")
        allocation[key] = ((previous[0] if previous else 0) + row["quantity"],
                           row["source_balance_at_registration"])
    if any(quantity > balance for quantity, balance in allocation.values()):
        raise ValueError("overlapping origin records exceed starting physical stock")
    # Do NOT compare historical origins to today's stock: goods may be eaten,
    # sold or taken later. Replaying initial event verifies stock at time zero.


def origin_history(world, *, source_owner_id: str | None = None) -> tuple[dict, ...]:
    """Trusted internal audit; this is NOT an NPC/player-facing query."""
    return tuple({"id": ident, **dict(row)}
                 for ident, row in world.property_title_origins.items()
                 if source_owner_id is None or row["source_owner_id"] == source_owner_id)
