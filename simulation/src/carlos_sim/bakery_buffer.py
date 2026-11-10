"""PLAY-48M: fixed bakery reserve target measured against REAL stock.

This is an honest LOCAL inventory policy, not a grain spawner or a purchasing
event. The baker starts with zero grain and must use existing genuine farm,
courier and procurement systems to accumulate stock. One nominal grain batch
per day and a fixed three-day target are explicitly scenario assumptions,
not a claim that 13 NPCs need only three loaves in three days.
"""
from __future__ import annotations
from .domain import WorldState

FIXED_DAYS = 3
PLANNED_GRAIN_BATCHES_PER_DAY = 1
GRAIN_TARGET = FIXED_DAYS * PLANNED_GRAIN_BATCHES_PER_DAY


def bakery_buffer_status(state: WorldState, *, target_days: int = FIXED_DAYS,
                         grain_per_day: int = PLANNED_GRAIN_BATCHES_PER_DAY
                         ) -> dict[str, int | bool]:
    if (type(target_days) is not int or not 1 <= target_days <= 7
            or type(grain_per_day) is not int or not 1 <= grain_per_day <= 30):
        raise ValueError("reserve must be a bounded fixed real-production target")
    bakery = state.resources.get("bakery", {})
    grain = bakery.get("grain")
    if type(grain) is not int or grain < 0:
        raise ValueError("bakery stock requires real initialized grain")
    target = target_days * grain_per_day
    return {
        "target_days": target_days,
        "planned_grain_per_day": grain_per_day,
        "target_grain": target,
        "owned_local_grain": grain,
        "missing_grain": max(0, target-grain),
        "coverage_full_days": grain // grain_per_day,
        "needs_restock": grain < target,
        "can_bake_one_batch_now": grain >= 1,
        "stock_filled": grain >= target,
    }
