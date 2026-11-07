"""PLAY-07: bounded, physically received human-to-NPC resource gifts.

The event is an atomic conservation transfer, not an invented social favor,
legal property judgment, RPG item, or auto-healing event. No NPC is forced
to accept a gift while unavailable or actively distrustful of the player.
"""
from __future__ import annotations

from typing import Any

from .domain import DomainEvent
from .market import _balance, _id, _present, FORBIDDEN, MAX_AMOUNT, MAX_QUANTITY
from .movement import _in_transit
from .social import decision


def deliver_player_gift(state: dict[str, Any], event: DomainEvent, *,
                        gift_authorized: bool) -> None:
    """Reduce one trusted, physical gift without minting goods or changing trust."""
    p = event.data
    if not gift_authorized or set(p) != {"recipient_id", "resource", "quantity"}:
        raise ValueError("player gift requires dedicated capability and exact fields")
    donor, recipient = event.actor_id, p["recipient_id"]
    resource, quantity = p["resource"], p["quantity"]
    if (not isinstance(donor, str) or donor not in state["entities"]
            or state["entities"][donor]["controller"] != "player"
            or not _id(recipient) or recipient not in state["npcs"]
            or donor == recipient or not _id(resource)
            or resource in FORBIDDEN
            or type(quantity) is not int or not 1 <= quantity <= MAX_QUANTITY):
        raise ValueError("only the actual player can gift a bounded owned resource to an NPC")
    site = state["entities"][donor]["location_id"]
    if (_in_transit(state, donor) or not _present(state, recipient, site)):
        raise ValueError("gift requires physically available co-located participants")
    # Reuse the NPC's already established deterministic voluntary response
    # to an offer of help. This changes neither trust nor hunger.
    trust = state["relations"].get(recipient, {}).get(donor, 0)
    reaction, _ = decision("offer_help", trust)
    if reaction != "welcomed":
        raise ValueError("recipient did not accept the local gift")

    giver_before = state["resources"].get(donor, {}).get(resource)
    receiver_before = state["resources"].get(recipient, {}).get(resource)
    if (not _balance(giver_before) or not _balance(receiver_before)
            or giver_before < quantity or receiver_before + quantity > MAX_AMOUNT):
        raise ValueError("gift requires initialized balances, owned stock and no overflow")
    state["resources"][donor][resource] = giver_before - quantity
    state["resources"][recipient][resource] = receiver_before + quantity
