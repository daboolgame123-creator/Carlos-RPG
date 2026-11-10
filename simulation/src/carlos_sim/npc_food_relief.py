"""PLAY-48: opt-in, one-loaf, personally financed NPC aid relay.

The donor knows of a request because the recipient asked while co-present.
It can only travel to a market it *personally visited* using previously
surveyed roads. Price/stock/merchant are checked ONLY after it reaches
the same physical tile. Every action uses old reducers; this planner does
not create contracts, food, money, routes, NPC memories or legal title.

No donor automatically uses its employer's or a courier's entrusted purse.
The requester must ask and the provider must separately accept later.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from .domain import WorldState
from .market import MONEY, MAX_AMOUNT, _present, reserved_trade_units, trade_receipt_allowed
from .navigation import shortest_known_route
from .npc import _injury_rest_decision

MAX_AID_PRICE = 2           # willing to give at most two OWN copper per loaf
MAX_REQUEST_AGE = 1800      # no endless supplier-hunting obligation
DONOR_MAX_HUNGER = 60
DONOR_MAX_FATIGUE = 69


@dataclass(frozen=True)
class AidRelayIntent:
    actor_id: str
    request_id: str
    kind: str               # "travel", "buy", "respond"
    route_id: str | None = None
    offer_id: str | None = None
    price: int | None = None


def event_id(prefix: str, npc: str, when: int) -> str:
    raw = f"aid-{prefix}-{npc}-{when}"
    if (len(raw) <= 64 and raw.isascii()
            and all(x.isalnum() or x in "._-" for x in raw)):
        return raw
    return "aid-" + prefix + "-" + sha256(raw.encode("utf-8")).hexdigest()[:48]


def _free(state: WorldState, who: str) -> bool:
    return not (
        any(trip["npc_id"] == who and trip["status"] == "traveling"
            for trip in state.travels.values())
        or any(job["npc_id"] == who and job["status"] == "running"
               for job in state.production_jobs.values())
        or any(action["npc_id"] == who and action["status"] == "running"
               for action in state.actions.values())
    )


def _known(v: object) -> bool:
    return type(v) is int and 0 <= v <= MAX_AMOUNT


def _known_market(state: WorldState, who: str, here: str) -> str | None:
    """Only physically visited shop locations, NEVER remote inventory/quotes."""
    nav = state.navigation.get(who)
    if nav is None or nav["target"] is not None:
        return None
    sites = [
        (sum(state.routes[r]["seconds"] for r in shortest_known_route(state, who, s)), s)
        for s in nav["visited"] if s in state.market_stalls
        and (s == here or shortest_known_route(state, who, s))
    ]
    return min(sites)[1] if sites else None


def choose_aid_relay(state: WorldState, who: str) -> AidRelayIntent | None:
    """One existing voluntary provider's request, no inferred remote need."""
    if (who not in state.npcs or who in state.supply_circuits
            or not _free(state, who)):
        return None
    actor = state.npcs[who]
    needs = actor["needs"]
    if (needs["hunger"] > DONOR_MAX_HUNGER
            or needs["fatigue"] > DONOR_MAX_FATIGUE
            or needs["safety"] >= 75
            or _injury_rest_decision(state.injuries, who) is not None):
        return None
    here = state.entities[who]["location_id"]
    owner = state.resources.get(who, {})
    own_food, own_copper = owner.get("food"), owner.get(MONEY)
    if not _known(own_food):
        return None
    already_promised = sum(
        item["quantity"] for item in state.obligations.values()
        if item["provider"] == who and item["resource"] == "food"
        and item["status"] == "promised"
    )
    # These are not legally escrowed, but an autonomous NPC must honor
    # its existing promise before making a competing one-loaf commitment.
    unpromised_food = own_food - already_promised
    if any(stall["keeper_id"] == who and site == here
           for site, stall in state.market_stalls.items()):
        return None     # a market steward must not abandon their own till
    nav = state.navigation.get(who)
    if nav is not None and nav["target"] is not None:
        return None     # respect an explicit, independent destination
    candidates = sorted(
        ((v["created_at"], oid, v)
         for oid, v in state.obligations.items()
         if v["provider"] == who and v["status"] == "requested"
         and v["resource"] == "food" and v["quantity"] == 1),
        key=lambda pair: (pair[0], pair[1]),
    )
    for created, oid, obligation in candidates:
        recipient = obligation["requester"]
        if state.relations.get(who, {}).get(recipient, 0) < 0:
            continue  # donor's own negative trust is not overruled
        place = obligation["location_id"]   # witnessed when the request was made
        age = state.time - created
        if unpromised_food >= 1:
            if here == place:
                if (state.entities[recipient]["location_id"] == here
                        and _free(state, recipient)):
                    return AidRelayIntent(who, oid, "respond")
                continue
            path = shortest_known_route(state, who, place)
            if path:
                return AidRelayIntent(who, oid, "travel", route_id=path[0])
            continue
        if own_food > 0 and unpromised_food < 1:
            # Never treat a loaf promised to a different requester as spare.
            # Existing unescrowed help must be fulfilled or cancelled first.
            continue
        if not _known(own_copper) or age >= MAX_REQUEST_AGE:
            # If already away from the requester when a shop ran out, return
            # physically so the normal assistance policy may decline locally.
            if here != place and age >= MAX_REQUEST_AGE:
                path = shortest_known_route(state, who, place)
                if path:
                    return AidRelayIntent(who, oid, "travel", route_id=path[0])
            continue
        usable = own_copper - reserved_trade_units(state.supply_circuits, who, MONEY)
        if usable < MAX_AID_PRICE:
            continue
        market = _known_market(state, who, here)
        if market is None:
            continue
        if here != market:
            path = shortest_known_route(state, who, market)
            if path:
                return AidRelayIntent(who, oid, "travel", route_id=path[0])
            continue
        # Local and witnessed only: inspect the actual posted offers and
        # physically present merchant, owner stock and copper receipts.
        raw = state.to_dict()
        if not _present(raw, who, here):
            continue
        viable = []
        for offer_id, offer in state.market_offers.items():
            if (offer["site_id"] != here or offer["status"] != "open"
                    or offer["resource"] != "food"
                    or offer["payment_resource"] != MONEY
                    or offer["remaining"] < 1
                    or offer["seller_id"] == who
                    or offer["stock_owner_id"] == who
                    or not _present(raw, offer["seller_id"], here)
                    or not trade_receipt_allowed(
                        state.supply_circuits, offer["stock_owner_id"], MONEY)):
                continue
            price = offer["unit_price"]
            source = state.resources.get(offer["stock_owner_id"], {})
            stock = source.get("food")
            destination_copper = source.get(MONEY)
            available_stock = (stock - reserved_trade_units(
                state.supply_circuits, offer["stock_owner_id"], "food")
                if _known(stock) else -1)
            if (_known(price) and 1 <= price <= min(MAX_AID_PRICE, usable)
                    and available_stock >= 1
                    and _known(destination_copper)
                    and destination_copper + price <= MAX_AMOUNT):
                viable.append((price, offer_id))
        if viable:
            price, offer_id = min(viable)
            return AidRelayIntent(
                who, oid, "buy", offer_id=offer_id, price=price)
    return None


def defer_regular_reply(state: WorldState, who: str) -> bool:
    """Don't auto-refuse a pending ONE-loaf request while relief is underway."""
    intent = choose_aid_relay(state, who)
    return intent is not None and intent.kind in ("travel", "buy")
