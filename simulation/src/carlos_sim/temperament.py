"""Phase 02-E: opt-in personality and verified private action experiences.

No invented memories, inferred skills, free resources or third-party knowledge.
All experiences are projected solely from successful scheduled NPC actions.
"""
from __future__ import annotations

from typing import Any
from .domain import DomainEvent, _json_copy

TRAITS = ("ambition", "curiosity", "caution", "discipline")
MEMORY_LIMIT = 8
VALID_ACTIONS = ("rest", "work", "investigate", "wait", "forage")


def configure_temperament(state: dict[str, Any], event: DomainEvent, *,
                          bootstrap: bool) -> None:
    p = _json_copy(event.data)
    if (not bootstrap or state["time"] != 0 or event.actor_id is not None
            or set(p) != {"npc_id", "traits"}):
        raise ValueError("NPC temperament requires trusted time-zero bootstrap")
    npc_id, traits = p["npc_id"], p["traits"]
    if (not isinstance(npc_id, str) or npc_id not in state["npcs"]
            or npc_id in state["npc_temperaments"]
            or not isinstance(traits, dict) or set(traits) != set(TRAITS)
            or any(type(traits[t]) is not int or not 0 <= traits[t] <= 100
                   for t in TRAITS)):
        raise ValueError("invalid, duplicate or ungrounded NPC traits")
    state["npc_temperaments"][npc_id] = {
        "traits": dict(traits), "memories": [],
    }


def remember_completed_action(state: dict[str, Any], action_id: str) -> None:
    action = state["actions"].get(action_id)
    if action is None or action["status"] != "completed":
        raise ValueError("psychology memory requires a genuinely completed action")
    profile = state["npc_temperaments"].get(action["npc_id"])
    if profile is None:
        return
    item = {
        "action_id": action_id,
        "action": action["action"],
        "completed_at": action["completed_at"],
        "effects": action["result"],
    }
    if any(memory["action_id"] == action_id for memory in profile["memories"]):
        raise ValueError("NPC cannot remember one completed action twice")
    profile["memories"].append(item)
    if len(profile["memories"]) > MEMORY_LIMIT:
        del profile["memories"][:-MEMORY_LIMIT]


def scoring_adjustments(profile: dict[str, Any] | None) -> tuple[dict[str, int], str] | None:
    if profile is None:
        return None
    t = profile["traits"]
    # The baseline policy is unchanged for NPCs without a trait profile.
    # Centered integer adjustments yield bounded, intelligible contrasts.
    deltas = {
        "rest": (t["caution"] - 50) // 6,
        "work": (t["ambition"] - 50) // 2 + (t["discipline"] - 50) // 5,
        "investigate": (t["curiosity"] - 50) // 2 - (t["caution"] - 50) // 2,
        "wait": (t["caution"] - 50) // 3,
    }
    last = profile["memories"][-1]["action"] if profile["memories"] else None
    if last in deltas:
        # A remembered recent action can affect a later choice, but memory
        # cannot override survival's severe -300 optional action gate.
        deltas[last] -= 12
    reason = (f"temperament[ambition={t['ambition']},curiosity={t['curiosity']},"
              f"caution={t['caution']},discipline={t['discipline']}]; "
              f"remembered_last={last or 'none'}; adjustment={deltas}")
    return deltas, reason


def validate_temperaments(state: dict[str, Any]) -> None:
    configured = state["npc_temperaments"]
    if not isinstance(configured, dict):
        raise ValueError("temperament ledger must be a mapping")
    for npc_id, profile in configured.items():
        if (npc_id not in state["npcs"] or not isinstance(profile, dict)
                or set(profile) != {"traits", "memories"}):
            raise ValueError("temperament owner missing or malformed")
        t, memories = profile["traits"], profile["memories"]
        if (not isinstance(t, dict) or set(t) != set(TRAITS)
                or any(type(t[k]) is not int or not 0 <= t[k] <= 100 for k in TRAITS)
                or not isinstance(memories, list) or len(memories) > MEMORY_LIMIT):
            raise ValueError("invalid immutable temperament or memory capacity")
        seen: set[str] = set()
        previous: tuple[int, str] | None = None
        for m in memories:
            if (not isinstance(m, dict) or set(m) !=
                    {"action_id", "action", "completed_at", "effects"}):
                raise ValueError("invalid NPC autobiographical memory record")
            ident = m["action_id"]
            action = state["actions"].get(ident) if isinstance(ident, str) else None
            if (action is None or ident in seen or action["npc_id"] != npc_id
                    or action["status"] != "completed"
                    or m["action"] != action["action"]
                    or m["completed_at"] != action["completed_at"]
                    or m["effects"] != action["result"]
                    or m["action"] not in VALID_ACTIONS):
                raise ValueError("memory must cite one exact completed own action")
            when = (m["completed_at"], ident)
            if previous is not None and when[0] < previous[0]:
                raise ValueError("memory chronology cannot go backward")
            seen.add(ident)
            previous = when
        # Per NPC, jobs cannot overlap: completed_at strictly orders its own
        # authoritative actions. A valid snapshot must remember the *exact*
        # newest eight, not a cherry-picked past action or an erased failure.
        completed = sorted(
            ((a["completed_at"], aid, a)
             for aid, a in state["actions"].items()
             if a["npc_id"] == npc_id and a["status"] == "completed"),
            key=lambda x: (x[0], x[1]),
        )
        expected = [
            {"action_id": aid, "action": action["action"],
             "completed_at": completed_at, "effects": action["result"]}
            for completed_at, aid, action in completed[-MEMORY_LIMIT:]
        ]
        if memories != expected:
            raise ValueError("autobiographical memory must equal latest real actions")
