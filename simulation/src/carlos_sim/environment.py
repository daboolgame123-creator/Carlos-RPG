"""02-A: finite opt-in site replenishment, driven by scheduled *game* time.

This intentionally does not model photosynthesis or create food: at most one
unit of the explicitly initialized finite 'regrowth_reserve' converts to one
'wild_food' per period, within capacity. Neither NPC nor player can author a
renewal event. The preconfigured scheduled clock is the only authority.
"""
from __future__ import annotations

from typing import Any

from .domain import DomainEvent

RESERVE = 'regrowth_reserve'
WILD = 'wild_food'
MAX_VALUE = 2**31 - 1
MAX_ID = 64


def _nonnegative(value: Any) -> bool:
    return type(value) is int and 0 <= value <= MAX_VALUE


def _positive(value: Any) -> bool:
    return type(value) is int and 1 <= value <= MAX_VALUE


def _schedule_id(ident: str, ordinal: int) -> str:
    return f'environment:{ident}:{ordinal}'


def configure_environment_cycle(state: dict[str, Any], event: DomainEvent,
                                *, bootstrap: bool) -> None:
    payload = event.data
    if (not bootstrap or state['time'] != 0 or event.actor_id is not None
            or set(payload) != {'id', 'site_id', 'period_seconds', 'capacity'}):
        raise ValueError('environment cycle requires explicit time-zero bootstrap')
    ident, site_id = payload['id'], payload['site_id']
    if (not isinstance(ident, str) or not 1 <= len(ident) <= MAX_ID
            or not ident.isascii()
            or not all(c.isalnum() or c in '._-' for c in ident)
            or not isinstance(site_id, str) or site_id not in state['locations']
            or ident in state['environment_cycles']
            or any(item['site_id'] == site_id for item in state['environment_cycles'].values())):
        raise ValueError('invalid or duplicate environmental site/cycle')
    period, capacity = payload['period_seconds'], payload['capacity']
    if not _positive(period) or not _positive(capacity):
        raise ValueError('environment period and capacity must be positive bounded integers')
    reserve, wild = (
        state['resources'].get(site_id, {}).get(RESERVE),
        state['resources'].get(site_id, {}).get(WILD),
    )
    if (not _nonnegative(reserve) or not _nonnegative(wild)
            or wild > capacity):
        raise ValueError('site must have known finite reserve and wild food within capacity')
    schedule_id = _schedule_id(ident, 1)
    if schedule_id in state['scheduled']:
        raise ValueError('environment schedule collides with an existing appointment')
    state['environment_cycles'][ident] = {
        'site_id': site_id, 'period_seconds': period, 'capacity': capacity,
        'ticks': 0, 'converted': 0, 'last_due': None,
        'next_due': period if reserve > 0 else None,
    }
    # Empty reserves cannot grow new material; avoid scheduling immortal
    # no-op events. There is deliberately no rule that refills the reserve.
    if reserve > 0:
        state['scheduled'][schedule_id] = {
            'due': period, 'order': state['next_schedule_order'],
            'kind': 'signal', 'interrupt': False,
            'payload': {'__environment_cycle': ident, 'tick': 1},
        }
        state['next_schedule_order'] += 1


def complete_environment_cycle(state: dict[str, Any], schedule_id: str,
                               payload: dict[str, Any], now: int) -> None:
    if set(payload) != {'__environment_cycle', 'tick'}:
        raise ValueError('environment appointment has invalid fields')
    ident, tick = payload['__environment_cycle'], payload['tick']
    cycle = state['environment_cycles'].get(ident) if isinstance(ident, str) else None
    if (cycle is None or type(tick) is not int or tick != cycle['ticks'] + 1
            or schedule_id != _schedule_id(ident, tick)
            or now != cycle['next_due']):
        raise ValueError('environment renewal needs its exact due appointment')
    site = cycle['site_id']
    reserve, wild = (
        state['resources'][site][RESERVE], state['resources'][site][WILD],
    )
    if _nonnegative(reserve) and reserve > 0 and _nonnegative(wild) and wild < cycle['capacity']:
        state['resources'][site][RESERVE] = reserve - 1
        state['resources'][site][WILD] = wild + 1
        cycle['converted'] += 1
    cycle['ticks'] += 1
    cycle['last_due'] = now
    # No permanent chain of empty ticks after the finite source is depleted.
    # A full food site retains its schedule only when reserve remains positive
    # (gathering at a later time may open capacity for genuine replenishment).
    if state['resources'][site][RESERVE] > 0:
        cycle['next_due'] = now + cycle['period_seconds']
        next_id = _schedule_id(ident, cycle['ticks'] + 1)
        if next_id in state['scheduled']:
            raise ValueError('environment renewal conflicts with next appointment')
        state['scheduled'][next_id] = {
            'due': cycle['next_due'], 'order': state['next_schedule_order'],
            'kind': 'signal', 'interrupt': False,
            'payload': {'__environment_cycle': ident, 'tick': cycle['ticks'] + 1},
        }
        state['next_schedule_order'] += 1
    else:
        cycle['next_due'] = None


def validate_environment_cycles(state: dict[str, Any]) -> None:
    cycles = state['environment_cycles']
    if not isinstance(cycles, dict):
        raise ValueError('environment cycles must be a mapping')
    seen_sites: set[str] = set()
    expected_ids: set[str] = set()
    for ident, record in cycles.items():
        if (not isinstance(ident, str) or not 1 <= len(ident) <= MAX_ID
                or not ident.isascii()
                or not all(c.isalnum() or c in '._-' for c in ident)
                or not isinstance(record, dict)
                or set(record) != {
                    'site_id', 'period_seconds', 'capacity', 'ticks', 'converted',
                    'last_due', 'next_due',
                }):
            raise ValueError('invalid environmental cycle record')
        site = record['site_id']
        if (not isinstance(site, str) or site not in state['locations']
                or site in seen_sites
                or not _positive(record['period_seconds'])
                or not _positive(record['capacity'])
                or not _nonnegative(record['ticks'])
                or not _nonnegative(record['converted'])
                or record['converted'] > record['ticks']):
            raise ValueError('environment cycle has invalid site or counters')
        seen_sites.add(site)
        ticks, period = record['ticks'], record['period_seconds']
        expected_last = ticks * period if ticks else None
        reserve, wild = (
            state['resources'].get(site, {}).get(RESERVE),
            state['resources'].get(site, {}).get(WILD),
        )
        if not _nonnegative(reserve) or not _nonnegative(wild) or wild > record['capacity']:
            raise ValueError('environment must conserve known limited site stocks')
        expected_next = (ticks + 1) * period if reserve > 0 else None
        if (record['last_due'] != expected_last
                or record['next_due'] != expected_next
                or (expected_last is not None and expected_last > state['time'])
                or (expected_next is not None and state['time'] > expected_next)):
            raise ValueError('environment cycle time no longer matches scheduled progression')
        if reserve > 0:
            sid = _schedule_id(ident, ticks + 1)
            schedule = state['scheduled'].get(sid)
            if (schedule is None or schedule['due'] != expected_next
                    or schedule['kind'] != 'signal' or schedule['interrupt']
                    or schedule['payload'] != {'__environment_cycle': ident, 'tick': ticks + 1}):
                raise ValueError('active environment must own exactly one future appointment')
            expected_ids.add(sid)
    for sid, schedule in state['scheduled'].items():
        if '__environment_cycle' in schedule['payload'] and sid not in expected_ids:
            raise ValueError('forged environment schedule')
