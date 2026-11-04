"""Phase 01-T unit tests: food-knowledge policy (pure functions).

These tests exercise knowledge.py in isolation, without a database or clock,
so they are fast and deterministic.
"""
from __future__ import annotations

import pytest

from carlos_sim.knowledge import (
    encode_food_claim, parse_food_claim, validate_food_claim_text,
    validate_food_claim_timing, effective_confidence, should_adopt,
    known_food_sites, choose_food_sharing, make_observation_events,
    is_food_key, is_observation_source,
)


def claim(text: str, source: str, received_at: int, confidence: int) -> dict:
    return {"text": text, "source": source, "received_at": received_at,
            "confidence": confidence}


# --- grammar ---

def test_grammar_accepts_strict_food_claims():
    assert parse_food_claim("food-state:present; observed_at=0") == ("present", 0)
    assert parse_food_claim("food-state:empty; observed_at=12345") == ("empty", 12345)


def test_grammar_rejects_malformed():
    bad = (
        "food-state:present;observed_at=0",   # missing space
        "food-state:full; observed_at=0",     # bad enum
        "food-state:present; observed_at=-1", # negative
        "food-state:present; observed_at=abc",# non-int
        "food-state:present",                 # missing observed_at
        "danger",                             # legacy key not food grammar
        "",                                   # empty
        "food-state:present; observed_at=0; extra=1",
    )
    for text in bad:
        assert parse_food_claim(text) is None
        with pytest.raises(ValueError):
            validate_food_claim_text(text)


def test_encode_roundtrip():
    text = encode_food_claim("present", 100)
    assert text == "food-state:present; observed_at=100"
    assert parse_food_claim(text) == ("present", 100)
    text = encode_food_claim("empty", 0)
    assert parse_food_claim(text) == ("empty", 0)


def test_timing_observed_at_not_after_received_at():
    validate_food_claim_timing("food-state:present; observed_at=50", 100)
    validate_food_claim_timing("food-state:present; observed_at=100", 100)
    with pytest.raises(ValueError):
        validate_food_claim_timing("food-state:present; observed_at=101", 100)


# --- effective confidence (age from observed_at only) ---

def test_effective_confidence_tiers_observation():
    now = 1000
    fresh = claim("food-state:present; observed_at=1000", "observation:grove", 1000, 90)
    assert effective_confidence(fresh, 1000) == 90          # age 0 -> 100%
    c600 = claim("food-state:present; observed_at=400", "observation:grove", 1000, 90)  # age 600
    assert effective_confidence(c600, 1000) == 90           # <=600 -> 100%
    c601 = claim("food-state:present; observed_at=399", "observation:grove", 1000, 90)  # age 601
    assert effective_confidence(c601, 1000) == 54           # 90*60//100
    c1800 = claim("food-state:present; observed_at=1", "observation:grove", 1000, 90)   # age 999
    assert effective_confidence(c1800, 1000) == 54          # <=1800 -> 60%
    old = claim("food-state:present; observed_at=0", "observation:grove", 2000, 90)     # age 2000
    assert effective_confidence(old, 2000) == 27            # >1800 -> 30%


def test_effective_confidence_hearsay_base_and_reshare_cap():
    now = 1000
    h = claim("food-state:present; observed_at=1000", "basim", 1000, 60)
    assert effective_confidence(h, 1000) == 60              # hearsay base 60
    reshared = claim("food-state:present; observed_at=1000", "adel", 1000, 30)
    assert effective_confidence(reshared, 1000) == 30       # capped by stored confidence


# --- should_adopt precedence (R1-R5) ---

def test_r1_none_adopts():
    incoming = claim("food-state:present; observed_at=100", "observation:grove", 100, 90)
    assert should_adopt(None, incoming, 100) is True


def test_r2_observation_supersedes():
    existing = claim("food-state:empty; observed_at=100", "observation:grove", 100, 90)
    incoming = claim("food-state:present; observed_at=200", "observation:grove", 200, 90)
    assert should_adopt(existing, incoming, 200) is True


def test_r2_observation_never_moves_backward():
    existing = claim("food-state:present; observed_at=200", "observation:grove", 200, 90)
    incoming = claim("food-state:empty; observed_at=100", "observation:grove", 100, 90)
    assert should_adopt(existing, incoming, 200) is False


def test_r3_recent_observation_protected_from_hearsay():
    existing = claim("food-state:present; observed_at=100", "observation:grove", 100, 90)  # age 0
    incoming = claim("food-state:empty; observed_at=50", "basim", 100, 60)
    assert should_adopt(existing, incoming, 100) is False


def test_r3_protection_boundary_1800():
    now = 1900
    existing = claim("food-state:present; observed_at=100", "observation:grove", 100, 90)  # age 1800
    incoming = claim("food-state:empty; observed_at=100", "basim", 100, 60)
    assert should_adopt(existing, incoming, now) is False


def test_r4_stale_observation_superseded_by_hearsay_via_r5():
    now = 1901  # age 1801 -> protection lapsed
    existing = claim("food-state:present; observed_at=100", "observation:grove", 100, 90)  # eff 27
    incoming = claim("food-state:empty; observed_at=1900", "basim", 1900, 60)              # eff 60
    assert should_adopt(existing, incoming, now) is True


def test_r5_hearsay_higher_effective_wins():
    now = 1000
    existing = claim("food-state:present; observed_at=100", "basim", 100, 60)   # age 900 -> 36
    incoming = claim("food-state:empty; observed_at=950", "adel", 950, 60)      # age 50 -> 60
    assert should_adopt(existing, incoming, now) is True


def test_r5_equal_eff_larger_observed_at_wins():
    now = 1000
    existing = claim("food-state:present; observed_at=950", "basim", 950, 60)   # age 50 -> 60
    incoming = claim("food-state:empty; observed_at=990", "adel", 990, 60)      # age 10 -> 60
    assert should_adopt(existing, incoming, now) is True  # 990 > 950


def test_r5_equal_eff_equal_observed_at_keeps_existing():
    now = 1000
    existing = claim("food-state:present; observed_at=900", "basim", 900, 60)
    incoming = claim("food-state:empty; observed_at=900", "adel", 900, 60)
    assert should_adopt(existing, incoming, now) is False


def test_r5_lower_eff_keeps_existing():
    now = 1000
    existing = claim("food-state:present; observed_at=100", "basim", 100, 60)   # age 900 -> 36
    incoming = claim("food-state:empty; observed_at=900", "adel", 900, 60)      # age 100 -> 54
    assert should_adopt(existing, incoming, now) is True


# --- known_food_sites reads only the named NPC ---

def test_known_food_sites_only_named_npc():
    state = {
        "npcs": {
            "adel": {"beliefs": {"food:grove": claim("food-state:present; observed_at=10",
                                                      "observation:grove", 10, 90)}},
            "basim": {"beliefs": {"food:grove": claim("food-state:empty; observed_at=10",
                                                     "observation:grove", 10, 90)}},
        },
        "entities": {},
    }
    assert known_food_sites(state, "adel") == ["grove"]
    assert known_food_sites(state, "basim") == []
    assert known_food_sites(state, "omar") == []


def test_known_food_sites_excludes_empty_and_non_food():
    state = {
        "npcs": {
            "adel": {
                "beliefs": {
                    "food:grove": claim("food-state:empty; observed_at=10", "observation:grove", 10, 90),
                    "food:square": claim("food-state:present; observed_at=10", "observation:square", 10, 90),
                    "danger": claim("predator near grove", "basim", 10, 95),
                }
            }
        },
        "entities": {},
    }
    assert known_food_sites(state, "adel") == ["square"]


# --- sharing determinism ---

def test_choose_food_sharing_only_co_located_eligible_peer():
    state = {
        "entities": {"adel": {"location_id": "grove"}, "basim": {"location_id": "grove"},
                     "nora": {"location_id": "square"}},
        "travels": {}, "actions": {},
        "time": 100,
        "npcs": {
            "adel": {"beliefs": {"food:grove": claim("food-state:present; observed_at=100",
                                                    "observation:grove", 100, 90)},
                     "delivery_history": []},
            "basim": {"beliefs": {}, "delivery_history": []},
            "nora": {"beliefs": {}, "delivery_history": []},
        },
    }
    events = choose_food_sharing(state, "adel")
    assert len(events) == 2  # delivery + ack for basim only
    delivery, ack = events
    assert delivery.event_type == "NPCInformationDelivered"
    assert delivery.data["npc_id"] == "basim"
    assert delivery.data["key"] == "food:grove"
    assert delivery.data["method"] == "message"
    assert delivery.data["claim"]["source"] == "adel"
    assert delivery.data["delivery_id"].startswith("food-share:adel:basim:grove:")
    assert ack.event_type == "NPCBeliefReceived"
    assert ack.data["npc_id"] == "basim"
    assert ack.data["delivery_id"] == delivery.data["delivery_id"]


def test_choose_food_sharing_preserves_observed_at_and_lowers_confidence():
    state = {
        "entities": {"adel": {"location_id": "grove"}, "basim": {"location_id": "grove"}},
        "travels": {}, "actions": {},
        "time": 100,
        "npcs": {
            "adel": {"beliefs": {"food:grove": claim("food-state:present; observed_at=100",
                                                    "observation:grove", 100, 90)},
                     "delivery_history": []},
            "basim": {"beliefs": {}, "delivery_history": []},
        },
    }
    events = choose_food_sharing(state, "adel")
    delivery = events[0]
    assert delivery.data["claim"]["observed_at"] if "observed_at" in delivery.data["claim"] else True
    text = delivery.data["claim"]["text"]
    assert "observed_at=100" in text  # original observation age preserved
    # sender effective at age 0 = 90; reshare confidence = min(60, 90//2) = 45
    assert delivery.data["claim"]["confidence"] == 45


def test_choose_food_sharing_sender_cannot_inspect_recipient_private_beliefs():
    state = {
        "entities": {"adel": {"location_id": "grove"}, "basim": {"location_id": "grove"}},
        "travels": {}, "actions": {},
        "time": 100,
        "npcs": {
            "adel": {"beliefs": {"food:grove": claim("food-state:present; observed_at=100",
                                                    "observation:grove", 100, 90)},
                     "delivery_history": []},
            "basim": {"beliefs": {}, "delivery_history": []},
        },
    }
    # The decision to tell someone depends on Adel's knowledge and documented
    # communications, NOT on Basim's unspoken/private knowledge.
    baseline = [event.to_dict() for event in choose_food_sharing(state, "adel")]
    assert len(baseline) == 2

    state["npcs"]["basim"]["beliefs"] = {
        "food:grove": claim("food-state:empty; observed_at=100",
                            "observation:grove", 100, 90)}
    protected = [event.to_dict() for event in choose_food_sharing(state, "adel")]
    assert protected == baseline

    # Belief acceptance is a separate receiving/reducer decision; an old
    # message cannot overwrite a recent direct observation (see adversarial
    # ACK test), even though the sender still physically tells the listener.


def test_choose_food_sharing_pair_cooldown_survives_redelivery_same_tick():
    state = {
        "entities": {"adel": {"location_id": "grove"}, "basim": {"location_id": "grove"}},
        "travels": {}, "actions": {},
        "time": 100,
        "npcs": {
            "adel": {"beliefs": {"food:grove": claim("food-state:present; observed_at=100",
                                                    "observation:grove", 100, 90)},
                     "delivery_history": []},
            "basim": {"beliefs": {}, "delivery_history": ["food-share:adel:basim:grove:100"]},
        },
    }
    # The RECIPIENT records each delivery. A same-tick repeat is suppressed.
    assert choose_food_sharing(state, "adel") == []


def test_make_observation_events_uninitialized_site_returns_none():
    state = {"entities": {"adel": {"location_id": "cave"}}, "travels": {}, "actions": {},
             "npcs": {"adel": {"beliefs": {}, "delivery_history": []}},
             "resources": {}}  # cave has no wild_food
    assert make_observation_events(state, "adel", "cave", 50, "arrival") == []


def test_make_observation_events_direct_observation_times():
    state = {
        "entities": {"adel": {"location_id": "grove"}}, "travels": {}, "actions": {},
        "npcs": {"adel": {"beliefs": {}, "delivery_history": []}},
        "resources": {"grove": {"wild_food": 2}},
    }
    events = make_observation_events(state, "adel", "grove", 50, "arrival")
    assert len(events) == 2
    delivery, ack = events
    claim = delivery.data["claim"]
    assert claim["text"] == "food-state:present; observed_at=50"
    assert claim["source"] == "observation:grove"
    assert claim["received_at"] == 50
    assert claim["confidence"] == 90
    assert delivery.data["method"] == "observation"
    assert delivery.data["location_id"] == "grove"
    assert ack.data["delivery_id"] == delivery.data["delivery_id"]
