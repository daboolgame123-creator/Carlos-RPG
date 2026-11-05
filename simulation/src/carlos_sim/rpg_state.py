"""01-Y: opt-in player RPG ledger with unknown-safe values.

This is state/evidence infrastructure, NOT automatic XP, healing, items or combat.
Trusted test-rule vital adjustments demonstrate event replay; NPC algorithms and
the player's command gateway cannot choose or invoke these adjustments.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .domain import DomainEvent, _thaw

VITALS = frozenset(('hp', 'st', 'mp'))
PROFILE_FIELDS = frozenset((
    'vitals', 'xp_current', 'xp_goal', 'level',
    'attributes', 'inventory', 'equipment',
))
LIMIT = 2**31 - 1


def _known_nonnegative(x: Any) -> bool:
    return type(x) is int and 0 <= x <= LIMIT


def _maybe_nonnegative(x: Any) -> bool:
    return x is None or _known_nonnegative(x)


def validate_rpg_profile(profile: Any) -> None:
    if not isinstance(profile, Mapping) or set(profile) != PROFILE_FIELDS:
        raise ValueError('invalid RPG profile fields')
    vitals = profile['vitals']
    if not isinstance(vitals, Mapping) or set(vitals) != VITALS:
        raise ValueError('RPG vitals must contain hp, st and mp')
    for name in VITALS:
        pair = vitals[name]
        if not isinstance(pair, Mapping) or set(pair) != {'current', 'max'}:
            raise ValueError('invalid RPG vital record')
        current, upper = pair['current'], pair['max']
        if not _maybe_nonnegative(current) or not _maybe_nonnegative(upper):
            raise ValueError('invalid RPG vital quantity')
        if current is not None and (upper is None or current > upper):
            raise ValueError('RPG vital exceeds maximum or has no known maximum')
    if not _maybe_nonnegative(profile['xp_current']):
        raise ValueError('invalid XP')
    if not _maybe_nonnegative(profile['xp_goal']):
        raise ValueError('invalid XP goal')
    level = profile['level']
    if level is not None and (type(level) is not int or not 1 <= level <= LIMIT):
        raise ValueError('invalid RPG level')
    attrs = profile['attributes']
    if not isinstance(attrs, Mapping) or len(attrs) > 32:
        raise ValueError('invalid RPG attributes')
    for k, value in attrs.items():
        if (not isinstance(k, str) or not 1 <= len(k) <= 40
                or not k.isascii()
                or not all(c.isalnum() or c in '_-' for c in k)
                or not _maybe_nonnegative(value)):
            raise ValueError('invalid RPG attribute')
    # Inventory/equipment domain transfers are NOT implemented. Do not
    # insert fabricated item ownership or equipped items at bootstrap.
    if (not isinstance(profile['inventory'], Mapping) or profile['inventory']
            or not isinstance(profile['equipment'], Mapping) or profile['equipment']):
        raise ValueError('inventory and equipment require future ownership rules')


def validate_rpg_profiles(state: dict[str, Any]) -> None:
    for ident, profile in state['rpg_profiles'].items():
        if (ident not in state['entities']
                or state['entities'][ident]['controller'] != 'player'):
            raise ValueError('RPG profile must belong to player-controlled entity')
        validate_rpg_profile(profile)


def project_rpg_event(state: dict[str, Any], event: DomainEvent, *,
                      bootstrap: bool, rpg_authorized: bool) -> None:
    p = event.data
    if event.event_type == 'PlayerRPGInitialized':
        if (not bootstrap or state['time'] != 0 or event.actor_id is not None
                or set(p) != {'player_id', 'profile'}):
            raise ValueError('RPG initialization requires trusted time-zero bootstrap')
        who = p['player_id']
        if (not isinstance(who, str) or who not in state['entities']
                or state['entities'][who]['controller'] != 'player'
                or who in state['rpg_profiles']):
            raise ValueError('RPG initialization requires a new existing player')
        validate_rpg_profile(p['profile'])
        state['rpg_profiles'][who] = _thaw(p['profile'])
    elif event.event_type == 'PlayerVitalChanged':
        if (not rpg_authorized or event.actor_id is not None
                or set(p) != {'player_id', 'vital', 'previous', 'current', 'source'}
                or p['source'] != 'test-scenario'):
            raise ValueError('RPG vital changes require trusted explicit scenario rule')
        who, vital = p['player_id'], p['vital']
        if (not isinstance(who, str) or who not in state['rpg_profiles']
                or vital not in VITALS):
            raise ValueError('unknown RPG player or vital')
        pair = state['rpg_profiles'][who]['vitals'][vital]
        previous, current, upper = p['previous'], p['current'], pair['max']
        if (type(previous) is not int or type(current) is not int
                or pair['current'] != previous or current == previous
                or upper is None or current < 0 or current > upper):
            raise ValueError('invalid RPG change or previous value mismatch')
        pair['current'] = current
    else:
        raise ValueError('unsupported RPG event type')


def unknown_profile() -> dict[str, Any]:
    """Opt-in profile template: absence of evidence is unknown, not zero."""
    return {
        'vitals': {v: {'current': None, 'max': None} for v in ('hp', 'st', 'mp')},
        'xp_current': None, 'xp_goal': None, 'level': None,
        'attributes': {}, 'inventory': {}, 'equipment': {},
    }
