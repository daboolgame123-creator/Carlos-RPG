"""Focused, reproducible CPU benchmark for the opt-in survival reducer.

This measures one pure TimeAdvanced reducer event, NOT SQLite bootstrapping,
full audit replay, working NPC decisions, network latency, or 1000 NPC actions.
Do not extrapolate to production simulation throughput.
"""
from __future__ import annotations

import argparse
import json
from time import perf_counter
from statistics import median

from carlos_sim import DomainEvent, WorldState, apply_event


def world_with_npcs(count: int) -> WorldState:
    if type(count) is not int or count < 1:
        raise ValueError('count must be a positive integer')
    template = {
        'role': 'worker',
        'needs': {'hunger': 20, 'fatigue': 5, 'safety': 0},
        'goals': {'earn': 30, 'explore': 5, 'survive': 50},
        'beliefs': {}, 'inbox': {}, 'delivery_history': [],
        'next_decision_at': 0, 'last_decision': None,
    }
    npcs = {f'npc-{i:05d}': template for i in range(count)}
    entities = {ident: {'name': ident, 'location_id': 'market', 'controller': 'npc'}
                for ident in npcs}
    return WorldState('benchmark', npcs=npcs, entities=entities,
                      locations={'market': {'name': 'Market'}})


def bench_once(count: int, *, repeat: int = 3) -> dict:
    base = world_with_npcs(count)
    event = DomainEvent('TimeAdvanced', None, 'performance sample', 600,
                        {'from': 0, 'to': 600})
    durations = []
    for _ in range(repeat):
        began = perf_counter()
        advanced = apply_event(base, event, survival_authorized=True)
        durations.append(perf_counter() - began)
        assert len(advanced.survival_progress) == count
        assert advanced.npcs['npc-00000']['needs']['hunger'] == 22
        assert advanced.npcs['npc-00000']['needs']['fatigue'] == 6
    return {'npcs': count, 'median_reducer_seconds': round(median(durations), 5),
            'samples_seconds': [round(x, 5) for x in durations]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--counts', type=int, nargs='+', default=[10, 100, 1000])
    parser.add_argument('--repeat', type=int, default=3)
    args = parser.parse_args()
    if args.repeat < 1:
        parser.error('--repeat must be positive')
    print(json.dumps({'scope': 'pure Python reducer; not full engine throughput',
                      'results': [bench_once(x, repeat=args.repeat) for x in args.counts]},
                     indent=2))


if __name__ == '__main__':
    main()
