"""Deterministic, knowledge-limited NPC planning and event-sourced NPC state.

Only an NPC's documented beliefs may influence its plans. This module contains
no world-clock, network calls or language-model generation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .domain import DomainEvent, WorldState, _json_copy
from .survival import CRITICAL_HUNGER
from .store import SQLiteEventStore
from .time_engine import TimeEngine

BASE_ACTIONS = ("rest", "work", "investigate", "wait")
ACTIONS = BASE_ACTIONS + ("forage",)
NEEDS = ("fatigue", "hunger", "safety")
GOALS = ("earn", "explore", "survive")
MIN_DECISION_COOLDOWN = 60


def _integer(value: Any, *, minimum: int = 0, maximum: int = 100) -> bool:
    return type(value) is int and minimum <= value <= maximum


def _validate_claim(claim: Any) -> None:
    if not isinstance(claim, dict) or set(claim) != {"text", "source", "received_at", "confidence"}:
        raise ValueError("invalid NPC claim shape")
    if not all(isinstance(claim[k], str) and claim[k] for k in ("text", "source")):
        raise ValueError("claim requires text and source")
    if not _integer(claim["received_at"], maximum=2**63 - 1) or not _integer(claim["confidence"]):
        raise ValueError("invalid claim time/confidence")


def validate_npc_state(npc: Any) -> None:
    if not isinstance(npc, dict) or set(npc) != {"role", "needs", "goals", "beliefs", "inbox", "delivery_history", "next_decision_at", "last_decision"}:
        raise ValueError("invalid NPC state")
    if not isinstance(npc["role"], str) or not npc["role"]:
        raise ValueError("invalid NPC role")
    if not isinstance(npc["needs"], dict) or set(npc["needs"]) != set(NEEDS) or not all(_integer(x) for x in npc["needs"].values()):
        raise ValueError("invalid NPC needs")
    if not isinstance(npc["goals"], dict) or set(npc["goals"]) != set(GOALS) or not all(_integer(x) for x in npc["goals"].values()):
        raise ValueError("invalid NPC goals")
    if not isinstance(npc["beliefs"], dict) or any(not isinstance(k, str) or not k for k in npc["beliefs"]):
        raise ValueError("invalid NPC knowledge")
    for claim in npc["beliefs"].values():
        _validate_claim(claim)
    if not isinstance(npc["delivery_history"], list) or any(not isinstance(x, str) or not x for x in npc["delivery_history"]) or len(set(npc["delivery_history"])) != len(npc["delivery_history"]):
        raise ValueError("invalid delivery history")
    if not isinstance(npc["inbox"], dict):
        raise ValueError("invalid NPC inbox")
    for delivery_id, item in npc["inbox"].items():
        if not isinstance(delivery_id, str) or not delivery_id or not isinstance(item, dict) or set(item) != {"key", "claim", "sender_id", "location_id", "method"}:
            raise ValueError("invalid pending delivery")
        if not isinstance(item["key"], str) or not item["key"] or not isinstance(item["sender_id"], str) or not item["sender_id"] or not isinstance(item["location_id"], str) or not item["location_id"] or item["method"] not in ("message", "observation"):
            raise ValueError("invalid delivery provenance")
        _validate_claim(item["claim"])
    if not _integer(npc["next_decision_at"], maximum=2**63 - 1):
        raise ValueError("invalid decision schedule")
    last = npc["last_decision"]
    if last is not None:
        if not isinstance(last, dict) or set(last) != {"action", "score", "reason", "at"}:
            raise ValueError("invalid decision record")
        if last["action"] not in ACTIONS or type(last["score"]) is not int or not isinstance(last["reason"], str) or not _integer(last["at"], maximum=2**63 - 1):
            raise ValueError("invalid recorded decision")


def project_npc_event(state: dict[str, Any], event: DomainEvent, *, bootstrap: bool,
                      survival_authorized: bool = False,
                      action_authorized: bool = False) -> None:
    p = _json_copy(event.data)
    ident = p.get("npc_id")
    if not isinstance(ident, str) or not ident or ident not in state["entities"] or state["entities"][ident]["controller"] != "npc":
        raise ValueError("NPC events may target only existing autonomous entities")
    if event.event_type == "NPCConfigured":
        if set(p) != {"npc_id", "role", "needs", "goals"} or ident in state["npcs"]:
            raise ValueError("invalid or duplicate NPC configuration")
        if not bootstrap or state["time"] != 0 or event.actor_id is not None:
            raise ValueError("NPC setup requires trusted bootstrap")
        profile = {"role": p["role"], "needs": p["needs"], "goals": p["goals"],
                   "beliefs": {}, "inbox": {}, "delivery_history": [], "next_decision_at": 0, "last_decision": None}
        validate_npc_state(profile)
        state["npcs"][ident] = _json_copy(profile)
        return
    if ident not in state["npcs"]:
        raise ValueError("NPC not configured")
    npc = state["npcs"][ident]
    if event.event_type == "NPCInformationDelivered":
        if set(p) != {"npc_id", "delivery_id", "key", "claim", "sender_id", "location_id", "method"}:
            raise ValueError("invalid information delivery")
        delivery_id = p["delivery_id"]
        if not isinstance(delivery_id, str) or not delivery_id or delivery_id in npc["delivery_history"]:
            raise ValueError("invalid or duplicate delivery ID")
        if not isinstance(p["key"], str) or not p["key"] or p["method"] not in ("message", "observation"):
            raise ValueError("invalid delivery kind/key")
        _validate_claim(p["claim"])
        sender = p["sender_id"]
        if not isinstance(sender, str) or sender not in state["entities"] or event.actor_id != sender:
            raise ValueError("delivery must be attributed to a real sender")
        # Entity location_id remains the departure endpoint during a trip for
        # deterministic persistence; it does not mean the traveler is present.
        from .movement import _in_transit
        if _in_transit(state, ident) or _in_transit(state, sender):
            raise ValueError("local information delivery cannot involve a traveler in transit")
        location = state["entities"][ident]["location_id"]
        if p["location_id"] != location or state["entities"][sender]["location_id"] != location:
            raise ValueError("sender and recipient must share the recorded location")
        if p["claim"]["received_at"] != state["time"]:
            raise ValueError("delivery must happen at current world time")
        if p["method"] == "message":
            if sender == ident or p["claim"]["source"] != sender:
                raise ValueError("message must identify another character as source")
        elif sender != ident or p["claim"]["source"] != "observation:" + location:
            raise ValueError("observation must belong to the perceiving NPC and location")
        # --- 01-T: namespaced food-key verification (reducer is the boundary) ---
        if p["key"].startswith("food:"):
            from .knowledge import (
                validate_food_claim_text, validate_food_claim_timing,
                parse_food_claim, food_site_from_key,
            )
            validate_food_claim_text(p["claim"]["text"])
            validate_food_claim_timing(p["claim"]["text"], p["claim"]["received_at"])
            food_state, _observed_at = parse_food_claim(p["claim"]["text"])
            site = food_site_from_key(p["key"])
            if site not in state["locations"]:
                raise ValueError("food claim must refer to an existing site")
            if p["method"] == "observation":
                if _observed_at != state["time"]:
                    raise ValueError("direct observation must be made at current world time")
                # You can only observe food where you stand; the claim must match
                # the real initialized stock at the actor's location.
                if site != location:
                    raise ValueError("food observation site must equal the actor's location")
                actual = state["resources"].get(site, {}).get("wild_food")
                if type(actual) is not int:
                    raise ValueError("cannot observe food at an uninitialized site")
                if food_state == "present" and actual < 1:
                    raise ValueError("cannot report present food when stock is zero")
                if food_state == "empty" and actual != 0:
                    raise ValueError("cannot report empty food when stock is positive")
            else:  # method == "message"
                # Hearsay can never masquerade as a direct sighting.
                if p["claim"]["source"].startswith("observation:"):
                    raise ValueError("hearsay cannot masquerade as an observation")
        npc["inbox"][delivery_id] = {k: _json_copy(p[k]) for k in ("key", "claim", "sender_id", "location_id", "method")}
        npc["delivery_history"].append(delivery_id)
    elif event.event_type == "NPCBeliefReceived":
        if set(p) != {"npc_id", "key", "delivery_id"} or event.actor_id != ident:
            raise ValueError("belief requires recipient acknowledgement of prior delivery")
        delivery = npc["inbox"].get(p["delivery_id"])
        if delivery is None or delivery["key"] != p["key"]:
            raise ValueError("belief has no matching pending information delivery")
        key = p["key"]
        claim = delivery["claim"]
        now = state["time"]
        if key.startswith("food:"):
            from .knowledge import should_adopt
            existing = npc["beliefs"].get(key)
            if not should_adopt(existing, claim, now):
                # Ack always consumes the delivery; the belief is replaced only
                # when should_adopt accepts. Otherwise keep the existing belief
                # and do not roll back (rollback is for malformed/forged data).
                del npc["inbox"][p["delivery_id"]]
                return
        npc["beliefs"][p["key"]] = delivery["claim"]
        del npc["inbox"][p["delivery_id"]]
    elif event.event_type == "NPCNeedChanged":
        if set(p) != {"npc_id", "need", "previous", "current"} or p["need"] not in NEEDS:
            raise ValueError("invalid need change")
        if event.actor_id not in (None, ident):
            raise ValueError("unrelated actor cannot change NPC needs")
        if npc["needs"][p["need"]] != p["previous"] or not _integer(p["current"]) or p["current"] == p["previous"]:
            raise ValueError("invalid need transition")
        npc["needs"][p["need"]] = p["current"]
    elif event.event_type == "NPCDecisionRecorded":
        legacy_fields = {"npc_id", "action", "score", "reason", "next_decision_at"}
        forage_policy = p.get("action") == "forage"
        if (set(p) != (legacy_fields | {"policy"} if forage_policy else legacy_fields)
                or event.actor_id != ident):
            raise ValueError("invalid NPC decision event")
        if forage_policy and (p["policy"] != "local-forage-v1" or not action_authorized):
            raise ValueError("foraging decisions require a trusted, recorded policy")
        if any(t['npc_id'] == ident and t['status'] == 'traveling' for t in state['travels'].values()):
            raise ValueError("NPC cannot decide a new activity while traveling")
        if any(a['npc_id'] == ident and a['status'] == 'running' for a in state['actions'].values()):
            raise ValueError("NPC cannot decide a new activity while busy")
        if event.time < npc["next_decision_at"]:
            raise ValueError("NPC decision attempted before next allowed time")
        if p["action"] not in ACTIONS or type(p["score"]) is not int or not isinstance(p["reason"], str) or not p["reason"]:
            raise ValueError("invalid decision contents")
        if not _integer(p["next_decision_at"], maximum=2**63-1) or p["next_decision_at"] < state["time"] + MIN_DECISION_COOLDOWN:
            raise ValueError("next decision must be in future")
        injury_decision = _injury_rest_decision(state["injuries"], ident)
        if injury_decision is not None:
            expected = injury_decision
        elif forage_policy:
            from .foraging import choose_local_foraging
            site = state["entities"][ident]["location_id"]
            choice = choose_local_foraging(ident, npc, site, state["resources"])
            if choice is None:
                raise ValueError("foraging decision lacks known local food or personal need")
            expected = Decision(ident, "forage", choice[0], choice[1])
        else:
            expected = _score_choice(npc, ident, survival_active=survival_authorized,
                                     temperament=state["npc_temperaments"].get(ident))
        if (p["action"], p["score"], p["reason"]) != (expected.action, expected.score, expected.reason):
            raise ValueError("NPC decision does not match deterministic utility policy")
        # Event records an intention, never silently changes HP, resources or position.
        npc["last_decision"] = {"action": p["action"], "score": p["score"], "reason": p["reason"], "at": event.time}
        npc["next_decision_at"] = p["next_decision_at"]
    else:
        raise ValueError("unsupported NPC event")


@dataclass(frozen=True)
class Decision:
    npc_id: str
    action: str
    score: int
    reason: str


def _injury_rest_decision(injuries: Mapping[str, Mapping[str, Any]],
                          npc_id: str) -> Decision | None:
    """Self-only severe injury overrides effort, not the recovery rules."""
    from .injury_behavior import SELF_CARE_THRESHOLD
    severity = max((r["severity"] for r in injuries.values()
                    if r["subject_id"] == npc_id and r["status"] == "active"),
                   default=0)
    if severity < SELF_CARE_THRESHOLD:
        return None
    score = 200 + severity
    return Decision(npc_id, "rest", score,
                    f"self_active_injury_rest; severity={severity}; npc={npc_id}")


def _score_choice(npc: Mapping[str, Any], npc_id: str, *, survival_active: bool = False,
                  temperament: Mapping[str, Any] | None = None) -> Decision:
    """Pure utility scoring based only on a single NPC profile."""
    needs, goals, beliefs = npc["needs"], npc["goals"], npc["beliefs"]
    danger = beliefs.get("danger")
    perceived_risk = danger["confidence"] if danger is not None else 0
    scores = {
        "rest": needs["fatigue"] * 2 + needs["safety"] // 5,
        "work": goals["earn"] + needs["hunger"] - needs["fatigue"] - perceived_risk,
        "investigate": goals["explore"] + perceived_risk // 2 - needs["fatigue"] - needs["safety"],
        "wait": 10 + needs["safety"] + perceived_risk,
    }
    temperament_explanation = None
    if temperament is not None:
        from .temperament import scoring_adjustments
        adjustments, temperament_explanation = scoring_adjustments(temperament)
        for action, extra in adjustments.items():
            scores[action] += extra
    # A character in the explicit survival mode must not continue seeking work
    # at the cost of critical hunger. Conserving energy is not a magic rescue:
    # it does not conjure food, remove debt or cure starvation.
    if survival_active and needs["hunger"] >= CRITICAL_HUNGER:
        scores["work"] -= 300
        scores["investigate"] -= 300
    # No random draw or unordered iteration. Stable tie preference makes replay deterministic.
    action = sorted(BASE_ACTIONS, key=lambda a: (-scores[a], BASE_ACTIONS.index(a)))[0]
    reason = f"utility[{action}]={scores[action]}; belief_danger={perceived_risk}; npc={npc_id}"
    if temperament_explanation is not None:
        reason += "; " + temperament_explanation
    return Decision(npc_id, action, scores[action], reason)


def choose_action(state: WorldState, npc_id: str, *, survival_enabled: bool = False,
                  foraging_enabled: bool = False) -> Decision | None:
    """Return an explainable recommendation based ONLY on one NPC's knowledge.

    Beliefs are not asserted as facts; a false report may still change a decision.
    """
    npc = state.npcs.get(npc_id)
    if npc is None or state.entities[npc_id]["controller"] != "npc":
        return None
    if any(t['npc_id'] == npc_id and t['status'] == 'traveling' for t in state.travels.values()):
        return None
    if any(a['npc_id'] == npc_id and a['status'] == 'running' for a in state.actions.values()):
        return None
    if state.time < npc["next_decision_at"]:
        return None
    self_injury = _injury_rest_decision(state.injuries, npc_id)
    if self_injury is not None:
        return self_injury
    if foraging_enabled:
        from .foraging import choose_local_foraging
        site = state.entities[npc_id]["location_id"]
        choice = choose_local_foraging(npc_id, npc, site, state.resources)
        if choice is not None:
            return Decision(npc_id, "forage", choice[0], choice[1])
    return _score_choice(npc, npc_id, survival_active=survival_enabled,
                         temperament=state.npc_temperaments.get(npc_id))


class NPCService:
    """Explicit deterministic decision step. Does not advance the world clock.

    A TimeEngine session must be active before any decision can be recorded.
    This stage does not yet execute actions; that requires action resolvers.
    """
    def __init__(self, store: SQLiteEventStore, clock: "TimeEngine", *,
                 decision_cooldown: int = 60, survival_enabled: bool = False,
                 foraging_enabled: bool = False):
        if type(decision_cooldown) is not int or decision_cooldown < MIN_DECISION_COOLDOWN:
            raise ValueError("decision cooldown must be at least 60 simulation seconds")
        if type(survival_enabled) is not bool:
            raise ValueError("survival_enabled must be boolean")
        self.store = store
        self.clock = clock
        if clock.store is not store:
            raise ValueError("NPC service and clock must use the same store")
        self.cooldown = decision_cooldown
        self.survival_enabled = survival_enabled
        if type(foraging_enabled) is not bool:
            raise ValueError("foraging_enabled must be boolean")
        self.foraging_enabled = foraging_enabled

    def decide(self, world_id: str, npc_id: str, *, command_id: str, expected_revision: int) -> Decision | None:
        self.clock._require_session(world_id)
        state = self.store.load(world_id)
        if state.revision != expected_revision:
            from .store import RevisionConflict
            raise RevisionConflict("stale NPC decision request")
        candidate = choose_action(state, npc_id, survival_enabled=self.survival_enabled,
                                  foraging_enabled=self.foraging_enabled)
        if candidate is None:
            return None
        event = DomainEvent("NPCDecisionRecorded", npc_id, "local utility policy", state.time,
                            {"npc_id": npc_id, "action": candidate.action, "score": candidate.score,
                             "reason": candidate.reason, "next_decision_at": state.time + self.cooldown,
                             **({"policy": "local-forage-v1"} if candidate.action == "forage" else {})})
        # The survival policy is evaluated using the same explicit mode as
        # LivingWorldEngine. Persist that capability for deterministic replay.
        # No TimeAdvanced event is emitted: the clock flag only authorizes the
        # survival-mode decision projection in the trusted local store.
        self.store.append(world_id, command_id, expected_revision, [event],
                          npc_authorized=True,
                          action_authorized=candidate.action == "forage",
                          clock_authorized=self.survival_enabled,
                          survival_authorized=self.survival_enabled)
        return candidate
