"""Bounded, deterministic NPC-initiated social intents for explicit play time.

Only the prospective speaker's own needs, directed trust and recorded
face-to-face encounters influence speech-act selection. The other NPC's private
needs, beliefs and goals are never consulted. No language model or real-world clock.
"""
from __future__ import annotations

from dataclasses import dataclass
from .domain import WorldState

MIN_SOCIAL_COOLDOWN = 180  # simulation seconds, not wall-clock time
SAME_TOPIC_COOLDOWN = 900  # do not repeat an unchanged request to one peer every 3 minutes
SOCIAL_TEXT = {
    'greeting': 'Hello.',
    'request_help': 'Could you help me?',
    'offer_help': 'I can offer help if needed.',
    'threat': 'Stay away from me.',
}
_PRIORITY = {'request_help': 0, 'threat': 1, 'offer_help': 2, 'greeting': 3}


@dataclass(frozen=True)
class SocialIntent:
    sender_id: str
    recipient_id: str
    kind: str
    text: str
    reason: str


def _physically_unavailable(state: WorldState, npc_id: str) -> bool:
    if npc_id not in state.npcs:
        return True
    if any(t['npc_id'] == npc_id and t['status'] == 'traveling'
           for t in state.travels.values()):
        return True
    if any(a['npc_id'] == npc_id and a['status'] == 'running'
           for a in state.actions.values()):
        return True
    return False


def choose_social_intent(state: WorldState, npc_id: str, *, cooldown: int = MIN_SOCIAL_COOLDOWN) -> SocialIntent | None:
    """Produce at most one traceable, co-located social intention per speaker.

    The caller must still commit matching SocialMessageSent/Received events in
    a single trusted transaction. This pure function never changes state.
    """
    if type(cooldown) is not int or cooldown < MIN_SOCIAL_COOLDOWN:
        raise ValueError('social cooldown must be >= 180 simulated seconds')
    if _physically_unavailable(state, npc_id):
        return None
    # The sender may use their own private intention to defer social action.
    own_decision = state.npcs[npc_id]['last_decision']
    if own_decision is not None and own_decision['at'] == state.time:
        return None
    history = state.social_messages
    # The actor cannot spam many recipients to evade the per-speaker cooldown.
    latest = max((m['sent_at'] for m in history.values() if m['sender'] == npc_id), default=None)
    if latest is not None and state.time - latest < cooldown:
        return None
    location = state.entities[npc_id]['location_id']
    own = state.npcs[npc_id]
    candidates: list[tuple[int, str, str, str]] = []
    for peer_id in sorted(state.npcs):
        if peer_id == npc_id or _physically_unavailable(state, peer_id):
            continue
        if state.entities[peer_id]['location_id'] != location:
            continue
        # Previous exchanges between these two actors are known to both.
        acquainted = any((m['sender'] == npc_id and m['recipient'] == peer_id)
                          or (m['sender'] == peer_id and m['recipient'] == npc_id)
                          for m in history.values() if m['status'] == 'received')
        trust = state.relations.get(npc_id, {}).get(peer_id, 0)  # own view ONLY
        kind: str | None = None
        reason: str | None = None
        if not acquainted:
            kind, reason = 'greeting', 'first_contact'
        elif (own['needs']['hunger'] >= 70 or own['needs']['safety'] >= 70) and trust >= 0:
            kind, reason = 'request_help', 'personal_need'
        elif trust <= -40 and own['needs']['safety'] <= 40:
            kind, reason = 'threat', 'personal_hostility'
        elif trust >= 40 and own['needs']['fatigue'] < 40 and own['needs']['hunger'] < 50:
            kind, reason = 'offer_help', 'personal_goodwill'
        if kind is not None:
            # Without an actual fulfilled promise/need change model, repeated
            # words alone must not mine unlimited trust from the same peer.
            if any(m['sender'] == npc_id and m['recipient'] == peer_id
                   and m['kind'] == kind and state.time - m['sent_at'] < SAME_TOPIC_COOLDOWN
                   for m in history.values()):
                continue
            candidates.append((_PRIORITY[kind], peer_id, kind, reason))
    if not candidates:
        return None
    _, peer_id, kind, reason = min(candidates)
    return SocialIntent(npc_id, peer_id, kind, SOCIAL_TEXT[kind], reason)
