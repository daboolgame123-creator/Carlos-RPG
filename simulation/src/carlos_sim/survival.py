"""Deterministic baseline metabolism during explicitly authorized simulated time.

Activity completion separately charges its *extra* effort; metabolism is the
background passage-of-time cost. No wall-clock ticks, implicit production,
health loss, starvation death or fabricated food.
"""
from __future__ import annotations

from typing import Any

# All values below are test-world parameters, not Carlos setting canon.
HUNGER_SECONDS_PER_POINT = 300
FATIGUE_SECONDS_PER_POINT = 600
CRITICAL_HUNGER = 90
# PLAY-29 alternatives are trusted setup-only and persisted in each world.
# Historical/default worlds continue with 300 s/point, unchanged.
ALLOWED_HUNGER_PERIODS = frozenset((300, 3600))
# Explicit test-world calibration only: actual activity costs remain positive.
ALLOWED_ACTIVITY_HUNGER_PERCENT = frozenset((20, 100))


def activity_hunger_percent(state: dict[str, Any]) -> int:
    return state['metabolism_policy'].get('activity_hunger_percent', 100)



def hunger_period(state: dict[str, Any]) -> int:
    policy = state['metabolism_policy']
    if not policy:
        return HUNGER_SECONDS_PER_POINT
    return policy['hunger_seconds_per_point']


def validate_metabolism_policy(state: dict[str, Any]) -> None:
    policy = state['metabolism_policy']
    if type(policy) is not dict or (policy and
            (set(policy) not in ({'hunger_seconds_per_point'},
                                 {'hunger_seconds_per_point', 'activity_hunger_percent'}) or
             type(policy['hunger_seconds_per_point']) is not int or
             policy['hunger_seconds_per_point'] not in ALLOWED_HUNGER_PERIODS or
             type(activity_hunger_percent(state)) is not int or
             activity_hunger_percent(state) not in ALLOWED_ACTIVITY_HUNGER_PERCENT)):
        raise ValueError('invalid frozen metabolism policy')


def configure_metabolism_policy(state: dict[str, Any], event, *, bootstrap: bool) -> None:
    p = event.data
    if (not bootstrap or event.actor_id is not None or state['time'] != 0
            or state['metabolism_policy'] or state['survival_progress']
            or set(p) not in ({'hunger_seconds_per_point'},
                               {'hunger_seconds_per_point', 'activity_hunger_percent'})):
        raise ValueError('metabolism policy requires a single trusted time-zero setup')
    period = p['hunger_seconds_per_point']
    if type(period) is not int or period not in ALLOWED_HUNGER_PERIODS:
        raise ValueError('unsupported metabolism period')
    percent = p.get('activity_hunger_percent', 100)
    if type(percent) is not int or percent not in ALLOWED_ACTIVITY_HUNGER_PERCENT:
        raise ValueError('unsupported activity hunger cost')
    state['metabolism_policy'] = {'hunger_seconds_per_point': period}
    if 'activity_hunger_percent' in p:
        state['metabolism_policy']['activity_hunger_percent'] = percent



def validate_survival_progress(state: dict[str, Any]) -> None:
    validate_metabolism_policy(state)
    rate = hunger_period(state)
    rows = state['survival_progress']
    if not isinstance(rows, dict):
        raise ValueError('invalid survival progress')
    for npc_id, progress in rows.items():
        if npc_id not in state['npcs'] or not isinstance(progress, dict) or set(progress) != {
                'hunger_seconds', 'fatigue_seconds'}:
            raise ValueError('invalid survival progress actor')
        h, f = progress['hunger_seconds'], progress['fatigue_seconds']
        if (type(h) is not int or not 0 <= h < rate
                or type(f) is not int or not 0 <= f < FATIGUE_SECONDS_PER_POINT):
            raise ValueError('invalid survival progress residuals')


def apply_survival_elapsed(state: dict[str, Any], seconds: int) -> None:
    """Add elapsed time once per TimeAdvanced event; split-step associative.

    Fatigue increases only outside an active rest action. Rest's fixed -20
    effect still applies at action completion, rather than being duplicated.
    """
    if type(seconds) is not int or seconds <= 0:
        raise ValueError('survival elapsed seconds must be positive')
    rate = hunger_period(state)
    resting = {a['npc_id'] for a in state['actions'].values()
               if a['status'] == 'running' and a['action'] == 'rest'}
    for npc_id in sorted(state['npcs']):
        progress = state['survival_progress'].setdefault(npc_id, {
            'hunger_seconds': 0, 'fatigue_seconds': 0})
        needs = state['npcs'][npc_id]['needs']
        hunger_points, hunger_rem = divmod(
            progress['hunger_seconds'] + seconds, rate)
        progress['hunger_seconds'] = hunger_rem
        needs['hunger'] = min(100, needs['hunger'] + hunger_points)
        if npc_id not in resting:
            fatigue_points, fatigue_rem = divmod(
                progress['fatigue_seconds'] + seconds, FATIGUE_SECONDS_PER_POINT)
            progress['fatigue_seconds'] = fatigue_rem
            needs['fatigue'] = min(100, needs['fatigue'] + fatigue_points)
