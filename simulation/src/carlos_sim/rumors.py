"""02-G: bounded, traceable LOCAL hearsay about actual received speech.

Evidence here is a real utterance, not the truth of anything stated within it.
No global reputation index, model interpretation or remote knowledge.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from .domain import DomainEvent, WorldState
from .movement import _in_transit

MAX_HOPS = 3
RESHARE_DELAY = 60
SPEAKER_COOLDOWN = 600
MAX_HEARD_PER_NPC = 64


def _source_record(state: dict[str, Any], speaker: str, original: str, parent: str | None):
    message = state["social_messages"].get(original)
    if not isinstance(original, str) or message is None or message["status"] != "received":
        raise ValueError("rumor must cite a genuinely received social message")
    if state["time"] <= message["sent_at"]:
        raise ValueError("original utterance cannot spread at the same tick")
    if parent is None:
        if speaker != message["recipient"]:
            raise ValueError("only the actual witness may originate first-hand hearsay")
        return message, 1, 70
    history = state["rumor_deliveries"].get(parent)
    if history is None or history["recipient"] != speaker or history["original_id"] != original:
        raise ValueError("rumor requires sender's own earlier parent delivery")
    if state["time"] - history["delivered_at"] < RESHARE_DELAY:
        raise ValueError("newly received hearsay cannot be instantly relayed")
    if history["hops"] >= MAX_HOPS:
        raise ValueError("rumor maximum hops reached")
    return message, history["hops"] + 1, max(20, history["confidence"] - 20)


def project_rumor_event(state: dict[str, Any], event: DomainEvent, *, social_authorized: bool):
    if not social_authorized or event.event_type != "RumorDelivered":
        raise ValueError("rumor requires trusted social delivery")
    p = event.data
    if set(p) != {"id", "recipient_id", "original_id", "parent_id"}:
        raise ValueError("invalid rumor event payload")
    sender = event.actor_id
    receiver = p["recipient_id"]
    ident = p["id"]
    if (type(ident) is not str or not 1 <= len(ident) <= 128
            or not ident.isascii() or not all(x.isalnum() or x in ":._-" for x in ident)
            or ident in state["rumor_deliveries"]):
        raise ValueError("invalid or duplicate rumor delivery ID")
    if (sender not in state["npcs"] or receiver not in state["npcs"]
            or sender == receiver or type(p["original_id"]) is not str
            or (p["parent_id"] is not None and type(p["parent_id"]) is not str)):
        raise ValueError("rumor delivery needs distinct real NPC participants")
    if (_in_transit(state, sender) or _in_transit(state, receiver)
            or state["entities"][sender]["location_id"] != state["entities"][receiver]["location_id"]):
        raise ValueError("rumor requires real co-located participants")
    original, hops, confidence = _source_record(state, sender, p["original_id"], p["parent_id"])
    if original["sender"] == receiver:
        raise ValueError("do not present a person's own utterance as new hearsay")
    if any(record["recipient"] == receiver and record["original_id"] == p["original_id"]
           for record in state["rumor_deliveries"].values()):
        raise ValueError("listener already heard this original rumor")
    if sum(record["recipient"] == receiver for record in state["rumor_deliveries"].values()) >= MAX_HEARD_PER_NPC:
        raise ValueError("bounded per-listener rumor history reached")
    if any(record["sender"] == sender and state["time"] - record["delivered_at"] < SPEAKER_COOLDOWN
           for record in state["rumor_deliveries"].values()):
        raise ValueError("rumor speaker cooldown")
    state["rumor_deliveries"][ident] = {
        "sender": sender, "recipient": receiver,
        "original_id": p["original_id"], "parent_id": p["parent_id"],
        "subject": original["sender"],
        "location_id": state["entities"][sender]["location_id"],
        "delivered_at": state["time"], "hops": hops,
        "confidence": confidence,
    }


def validate_rumors(state: dict[str, Any]) -> None:
    ledger = state["rumor_deliveries"]
    if not isinstance(ledger, dict):
        raise ValueError("invalid rumor ledger")
    for ident, row in ledger.items():
        if (type(ident) is not str or not 1 <= len(ident) <= 128
                or not ident.isascii() or not all(x.isalnum() or x in ":._-" for x in ident)
                or not isinstance(row, dict) or set(row) != {
                    "sender", "recipient", "original_id", "parent_id", "subject",
                    "location_id", "delivered_at", "hops", "confidence"
                }):
            raise ValueError("invalid rumor record shape")
        if (row["sender"] not in state["npcs"] or row["recipient"] not in state["npcs"]
                or row["sender"] == row["recipient"] or row["location_id"] not in state["locations"]
                or type(row["delivered_at"]) is not int or not 0 <= row["delivered_at"] <= state["time"]
                or type(row["hops"]) is not int or not 1 <= row["hops"] <= MAX_HOPS
                or type(row["confidence"]) is not int or not 0 <= row["confidence"] <= 100):
            raise ValueError("invalid rumor identity/timing")
        original = state["social_messages"].get(row["original_id"])
        if (original is None or original["status"] != "received"
                or row["subject"] != original["sender"] or row["delivered_at"] <= original["sent_at"]):
            raise ValueError("rumor lacks genuine original event")
        parent = row["parent_id"]
        if parent is None:
            if row["sender"] != original["recipient"] or row["hops"] != 1 or row["confidence"] != 70:
                raise ValueError("invalid first-hand rumor source")
        else:
            ancestor = ledger.get(parent)
            if (ancestor is None or ancestor["recipient"] != row["sender"]
                    or ancestor["original_id"] != row["original_id"]
                    or ancestor["delivered_at"] + RESHARE_DELAY > row["delivered_at"]
                    or row["hops"] != ancestor["hops"] + 1
                    or row["confidence"] != max(20, ancestor["confidence"] - 20)):
                raise ValueError("invalid linked rumor chain")
        if sum(x["recipient"] == row["recipient"] and x["original_id"] == row["original_id"]
               for x in ledger.values()) != 1:
            raise ValueError("duplicate recipient/original rumor")


def heard_rumors(state: WorldState, npc_id: str) -> tuple[dict[str, Any], ...]:
    """Only return this listener's testimony; no arbitrary other's private memory."""
    if npc_id not in state.npcs:
        raise ValueError("rumor view requires existing NPC")
    return tuple({"original_id": value["original_id"],
                  "subject": value["subject"],
                  "kind": state.social_messages[value["original_id"]]["kind"],
                  "speaker": value["sender"],
                  "hops": value["hops"],
                  "confidence": value["confidence"]}
                 for _, value in sorted(state.rumor_deliveries.items())
                 if value["recipient"] == npc_id)


def perceived_reputation(state: WorldState, npc_id: str, subject_id: str) -> dict[str, Any]:
    """Listener-specific unproven indication; NEVER a global identity or guilt verdict."""
    if npc_id not in state.npcs or subject_id not in state.entities:
        raise ValueError("unknown observer or subject")
    incidents = [x for x in heard_rumors(state, npc_id) if x["subject"] == subject_id]
    threats = [x for x in incidents if x["kind"] == "threat"]
    return {"observer": npc_id, "subject": subject_id,
            "heard_incidents": len(incidents), "reported_threats": len(threats),
            "caution_score": min(100, sum(x["confidence"] // 10 for x in threats)),
            "proven_misconduct": False}


@dataclass(frozen=True)
class RumorIntent:
    sender: str
    recipient: str
    original_id: str
    parent_id: str | None


def _available_for_gossip(snapshot: dict[str, Any], npc_id: str) -> bool:
    if _in_transit(snapshot, npc_id):
        return False
    if any(x["npc_id"] == npc_id and x["status"] == "running"
           for x in snapshot["actions"].values()):
        return False
    if any(x["npc_id"] == npc_id and x["status"] == "running"
           for x in snapshot["production_jobs"].values()):
        return False
    return True


def choose_rumor_round(state: WorldState) -> list[DomainEvent]:
    """Take a frozen snapshot: no same-tick echo, no invisible remote sources."""
    snapshot = state.to_dict()
    planned: list[DomainEvent] = []
    selected: set[tuple[str, str]] = set()
    for sender in sorted(state.npcs):
        if not _available_for_gossip(snapshot, sender):
            continue
        eligible: list[tuple[str, str | None]] = []
        for mid, msg in sorted(state.social_messages.items()):
            if (msg["kind"] == "threat" and msg["status"] == "received" and msg["recipient"] == sender
                    and state.time > msg["sent_at"]):
                eligible.append((mid, None))
        for ident, entry in sorted(state.rumor_deliveries.items()):
            if (entry["recipient"] == sender
                    and state.time - entry["delivered_at"] >= RESHARE_DELAY
                    and entry["hops"] < MAX_HOPS):
                eligible.append((entry["original_id"], ident))
        for original, parent in eligible:
            for receiver in sorted(state.npcs):
                if receiver == sender or not _available_for_gossip(snapshot, receiver):
                    continue
                if state.entities[receiver]["location_id"] != state.entities[sender]["location_id"]:
                    continue
                if (receiver, original) in selected or any(
                        x["recipient"] == receiver and x["original_id"] == original
                        for x in state.rumor_deliveries.values()):
                    continue
                ident = f"rumor:{sender}:{receiver}:{state.time}"
                if ident in state.rumor_deliveries:
                    continue
                ev = DomainEvent("RumorDelivered", sender,
                                 "local, traceable NPC hearsay", state.time,
                                 {"id": ident, "recipient_id": receiver,
                                  "original_id": original, "parent_id": parent})
                # Validate against the original snapshot, and do not force a message
                # when this speaker is cooling down or recipient's history is full.
                try:
                    from .domain import apply_event
                    apply_event(state, ev, social_authorized=True)
                except ValueError:
                    continue
                planned.append(ev)
                selected.add((receiver, original))
                break
            if planned and planned[-1].actor_id == sender:
                break
    return planned


class NPCRumorService:
    """Trusted in-process speech transmission; not exposed as an unauthenticated API."""

    def __init__(self, store, clock):
        if clock.store is not store:
            raise ValueError("rumor service and clock must share the same store")
        self.store, self.clock = store, clock

    def tell(self, world_id: str, sender: str, recipient: str, original_id: str,
             *, delivery_id: str, expected_revision: int, parent_id: str | None = None):
        from .store import RevisionConflict
        self.clock._require_session(world_id)
        state = self.store.load(world_id)
        if state.revision != expected_revision:
            raise RevisionConflict("stale rumor delivery revision")
        event = DomainEvent("RumorDelivered", sender, "NPC locally relays actual speech",
                            state.time, {"id": delivery_id, "recipient_id": recipient,
                                         "original_id": original_id, "parent_id": parent_id})
        return self.store.append(world_id, "rumor:" + delivery_id, expected_revision,
                                 [event], social_authorized=True)
