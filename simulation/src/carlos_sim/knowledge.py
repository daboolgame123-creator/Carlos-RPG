"""Phase 01-T: per-NPC knowledge of food-source locations (Option A).

Pure, deterministic policy for namespaced food beliefs ``food:<site>`` stored in
``npcs[*].beliefs``. No world clock, no remote resource access, no new entities.
All constants are named, unit-tested, and adjustable without re-baselining.
"""
from __future__ import annotations

import re
from typing import Any

from .domain import DomainEvent

FOOD_KEY_PREFIX = "food:"
OBS_SOURCE_PREFIX = "observation:"

FOOD_STATE_PRESENT = "present"
FOOD_STATE_EMPTY = "empty"

# Experimental confidence constants (D3), not canon.
OBS_BASE_CONFIDENCE = 90  # direct sighting
HEARSAY_BASE_CONFIDENCE = 60  # message received from another NPC
MAX_RESHARE_BASE = 60  # confidence ceiling for a re-shared hearsay claim

# Age tiers derived exclusively from observed_at (received_at never ages a fact).
AGE_SHORT = 600  # <= 600s  -> 100%
AGE_MEDIUM = 1800  # <= 1800s -> 60%
AGE_LONG_PCT = 30  # > 1800s -> 30%

OBSERVATION_PROTECTION_AGE = 1800  # recent direct sighting resists hearsay

# Sharing limits (sharing limits, never decision delays).
SHARE_PAIR_COOLDOWN = 600  # seconds per sender/recipient/site

_FOOD_CLAIM_RE = re.compile(r"^food-state:(present|empty); observed_at=(0|[1-9][0-9]*)$")


def _mapping(state: Any) -> dict[str, Any]:
    """Accept either a plain dict state or a frozen WorldState projection."""
    if isinstance(state, dict):
        return state
    return state.to_dict()


def is_food_key(key: Any) -> bool:
    return isinstance(key, str) and key.startswith(FOOD_KEY_PREFIX)


def food_site_from_key(key: str) -> str:
    return key[len(FOOD_KEY_PREFIX):]


def is_observation_source(source: Any) -> bool:
    return isinstance(source, str) and source.startswith(OBS_SOURCE_PREFIX)


def encode_food_claim(food_state: str, observed_at: int) -> str:
    if food_state not in (FOOD_STATE_PRESENT, FOOD_STATE_EMPTY):
        raise ValueError("invalid food state")
    if type(observed_at) is not int or observed_at < 0 or observed_at > 2**63 - 1:
        raise ValueError("invalid observed_at")
    return f"food-state:{food_state}; observed_at={observed_at}"


def parse_food_claim(text: Any) -> tuple[str, int] | None:
    """Return ``(food_state, observed_at)`` for a strict food claim, else None."""
    if not isinstance(text, str):
        return None
    m = _FOOD_CLAIM_RE.match(text)
    if m is None:
        return None
    # Parsed timestamps are persisted as signed 64-bit logical-clock values.
    # Bound-check the decimal *before* int() to reject oversized or malicious
    # strings identically on Python 3.10 and 3.13 (the latter has a digit cap).
    digits = m.group(2)
    limit = str(2**63 - 1)
    if len(digits) > len(limit) or (len(digits) == len(limit) and digits > limit):
        return None
    return m.group(1), int(digits)


def validate_food_claim_text(text: Any) -> None:
    if parse_food_claim(text) is None:
        raise ValueError("invalid food claim text")


def validate_food_claim_timing(text: Any, received_at: int) -> tuple[str, int]:
    """Parse a food claim and enforce ``observed_at <= received_at``."""
    parsed = parse_food_claim(text)
    if parsed is None:
        raise ValueError("invalid food claim text")
    food_state, observed_at = parsed
    if type(received_at) is not int or received_at < 0:
        raise ValueError("invalid received_at")
    if observed_at > received_at:
        raise ValueError("food observation cannot occur after its delivery")
    return food_state, observed_at


def effective_confidence(claim: dict[str, Any], now: int) -> int:
    """Effective confidence of a food claim at ``now``, from fact age only.

    ``received_at`` is never an input: a re-shared fact is still evaluated by
    the age of the underlying observation. The stored ``confidence`` caps the
    result (re-shares lower it per hop).
    """
    if type(now) is not int or now < 0:
        raise ValueError("invalid now")
    parsed = parse_food_claim(claim["text"])
    if parsed is None:
        return 0
    _food_state, observed_at = parsed
    age = now - observed_at
    if age < 0:
        age = 0
    if age <= AGE_SHORT:
        tier = 100
    elif age <= AGE_MEDIUM:
        tier = 60
    else:
        tier = AGE_LONG_PCT
    base = OBS_BASE_CONFIDENCE if is_observation_source(claim["source"]) else HEARSAY_BASE_CONFIDENCE
    return min(claim["confidence"], base * tier // 100)


def should_adopt(existing: dict[str, Any] | None, incoming: dict[str, Any], now: int) -> bool:
    """Adoption precedence for successive food beliefs about one site.

    Pure function of ``(existing, incoming, now)``; identical under replay.
    """
    if type(now) is not int or now < 0:
        raise ValueError("invalid now")
    # R1: first knowledge about the site.
    if existing is None:
        return True

    incoming_obs = is_observation_source(incoming["source"])
    existing_obs = is_observation_source(existing["source"])

    i_parsed = parse_food_claim(incoming["text"])
    e_parsed = parse_food_claim(existing["text"])
    if i_parsed is None or e_parsed is None:
        return False
    _i_state, i_at = i_parsed
    _e_state, e_at = e_parsed

    # R7: a direct sighting never moves knowledge backward.
    if incoming_obs and i_at < e_at:
        return False

    # R2: a direct observation supersedes (after the R7 monotonic check).
    if incoming_obs:
        return True

    # Existing is a direct observation.
    if existing_obs:
        age = now - e_at
        if age < 0:
            age = 0
        # R3: a recent direct sighting (<= 1800s) is protected; hearsay does not
        # silently erase it just because protection lapsed is not true here.
        if age <= OBSERVATION_PROTECTION_AGE:
            return False
        # R4: protection lapsed -> fall through to the R5 comparison.

    # R5: hearsay vs hearsay (or a stale observation vs hearsay).
    eff_in = effective_confidence(incoming, now)
    eff_ex = effective_confidence(existing, now)
    if eff_in > eff_ex:
        return True
    if eff_in == eff_ex:
        # Larger observed_at = newer fact.
        return i_at > e_at
    return False


def _physically_unavailable(state: dict[str, Any], npc_id: str) -> bool:
    if npc_id not in state["npcs"]:
        return True
    if any(t["npc_id"] == npc_id and t["status"] == "traveling"
           for t in state["travels"].values()):
        return True
    if any(a["npc_id"] == npc_id and a["status"] == "running"
           for a in state["actions"].values()):
        return True
    return False


def known_food_sites(state: dict[str, Any], npc_id: str) -> list[str]:
    """Read-only recall: sites this NPC believes have present food.

    Only the named NPC's own beliefs are consulted; no remote site or another
    NPC's beliefs are read.
    """
    state = _mapping(state)
    npc = state["npcs"].get(npc_id)
    if npc is None:
        return []
    sites: list[str] = []
    for key, claim in npc["beliefs"].items():
        if is_food_key(key):
            parsed = parse_food_claim(claim["text"])
            if parsed is not None and parsed[0] == FOOD_STATE_PRESENT:
                sites.append(food_site_from_key(key))
    return sorted(sites)


def _share_claim(sender_belief: dict[str, Any], now: int) -> dict[str, Any]:
    """Build the hearsay claim a sender attaches when sharing one belief."""
    parsed = parse_food_claim(sender_belief["text"])
    if parsed is None:
        raise ValueError("sender belief is not a valid food claim")
    _food_state, observed_at = parsed
    sender_eff = effective_confidence(sender_belief, now)
    return {
        "text": encode_food_claim(_food_state, observed_at),
        "source": "",  # filled by the caller (immediate teller)
        "received_at": now,
        "confidence": min(MAX_RESHARE_BASE, sender_eff // 2),
    }


def choose_food_sharing(state: dict[str, Any], sender_id: str) -> list[DomainEvent]:
    """Choose food-knowledge deliveries from one sender to co-located peers.
    """
    state = _mapping(state)
    events: list[DomainEvent] = []
    sender = state["npcs"].get(sender_id)
    if sender is None or _physically_unavailable(state, sender_id):
        return events
    location = state["entities"][sender_id]["location_id"]
    now = state["time"]
    shared_pairs: set[str] = set()
    # Share both positive and negative local memories: an empty site is
    # information, not an unknown site. Never consult remote food balances.
    for key in sorted(sender["beliefs"]):
        if not is_food_key(key):
            continue
        site = food_site_from_key(key)
        belief = sender["beliefs"][key]
        if parse_food_claim(belief["text"]) is None:
            continue
        claim = _share_claim(belief, now)
        claim["source"] = sender_id
        for recipient_id in sorted(state["npcs"]):
            if recipient_id == sender_id or recipient_id in shared_pairs:
                continue
            if state["entities"][recipient_id]["location_id"] != location:
                continue
            if _physically_unavailable(state, recipient_id):
                continue
            delivery_id = f"food-share:{sender_id}:{recipient_id}:{site}:{now}"
            recipient = state["npcs"][recipient_id]
            # Delivery IDs are recorded on the RECIPIENT, never the sender.
            # Respect the documented per-sender/recipient/site cooldown.
            prefix = f"food-share:{sender_id}:{recipient_id}:{site}:"
            recent = False
            for old_id in recipient["delivery_history"]:
                if old_id.startswith(prefix):
                    old_tick = old_id[len(prefix):]
                    if old_tick.isascii() and old_tick.isdecimal():
                        delta = now - int(old_tick)
                        if 0 <= delta < SHARE_PAIR_COOLDOWN:
                            recent = True
                            break
            if recent:
                continue
            # Never inspect a recipient's private beliefs when deciding to
            # speak. The recipient's reducer alone applies should_adopt during
            # acknowledgement; a rejected update still consumes the message.
            delivery = DomainEvent(
                "NPCInformationDelivered", sender_id,
                "autonomous food knowledge sharing", now,
                {"npc_id": recipient_id, "delivery_id": delivery_id, "key": key,
                 "claim": claim, "sender_id": sender_id, "location_id": location,
                 "method": "message"},
            )
            ack = DomainEvent(
                "NPCBeliefReceived", recipient_id,
                "recipient acknowledges shared food knowledge", now,
                {"npc_id": recipient_id, "key": key, "delivery_id": delivery_id},
            )
            events.append(delivery)
            events.append(ack)
            shared_pairs.add(recipient_id)
    return events


def make_observation_events(state: dict[str, Any], npc_id: str, site: str,
                            time: int, trigger: str) -> list[DomainEvent]:
    """Build delivery+ack for a direct food observation by ``npc_id`` at ``site``.
    """
    state = _mapping(state)
    actual = state["resources"].get(site, {}).get("wild_food")
    if type(actual) is not int:
        return []
    food_state = FOOD_STATE_PRESENT if actual >= 1 else FOOD_STATE_EMPTY
    claim = {
        "text": encode_food_claim(food_state, time),
        "source": OBS_SOURCE_PREFIX + site,
        "received_at": time,
        "confidence": OBS_BASE_CONFIDENCE,
    }
    key = FOOD_KEY_PREFIX + site
    delivery_id = f"food-obs:{npc_id}:{site}:{time}:{trigger}"
    delivery = DomainEvent(
        "NPCInformationDelivered", npc_id, "direct food observation", time,
        {"npc_id": npc_id, "delivery_id": delivery_id, "key": key, "claim": claim,
         "sender_id": npc_id, "location_id": site, "method": "observation"},
    )
    ack = DomainEvent(
        "NPCBeliefReceived", npc_id, "acknowledge direct food observation", time,
        {"npc_id": npc_id, "key": key, "delivery_id": delivery_id},
    )
    return [delivery, ack]
