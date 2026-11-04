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


def validate_survival_progress(state: dict[str, Any]) -> None:
    rows = state['survival_progress']
    if not isinstance(rows, dict):
        raise ValueError('invalid survival progress')
    for npc_id, progress in rows.items():
        if npc_id not in state['npcs'] or not isinstance(progress, dict) or set(progress) != {
                'hunger_seconds', 'fatigue_seconds'}:
            raise ValueError('invalid survival progress actor')
        h, f = progress['hunger_seconds'], progress['fatigue_seconds']
        if (type(h) is not int or not 0 <= h < HUNGER_SECONDS_PER_POINT
                or type(f) is not int or not 0 <= f < FATIGUE_SECONDS_PER_POINT):
            raise ValueError('invalid survival progress residuals')


def apply_survival_elapsed(state: dict[str, Any], seconds: int) -> None:
    """Add elapsed time once per TimeAdvanced event; split-step associative.

    Fatigue increases only outside an active rest action. Rest's fixed -20
    effect still applies at action completion, rather than being duplicated.
    """
    if type(seconds) is not int or seconds <= 0:
        raise ValueError('survival elapsed seconds must be positive')
    resting = {a['npc_id'] for a in state['actions'].values()
               if a['status'] == 'running' and a['action'] == 'rest'}
    for npc_id in sorted(state['npcs']):
        progress = state['survival_progress'].setdefault(npc_id, {
            'hunger_seconds': 0, 'fatigue_seconds': 0})
        needs = state['npcs'][npc_id]['needs']
        hunger_points, hunger_rem = divmod(
            progress['hunger_seconds'] + seconds, HUNGER_SECONDS_PER_POINT)
        progress['hunger_seconds'] = hunger_rem
        needs['hunger'] = min(100, needs['hunger'] + hunger_points)
        if npc_id not in resting:
            fatigue_points, fatigue_rem = divmod(
                progress['fatigue_seconds'] + seconds, FATIGUE_SECONDS_PER_POINT)
            progress['fatigue_seconds'] = fatigue_rem
            needs['fatigue'] = min(100, needs['fatigue'] + fatigue_points)
