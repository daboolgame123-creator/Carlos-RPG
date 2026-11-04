"""Local end-to-end event-engine sample (not a production capacity forecast).

Includes world bootstrap, one 60-second autonomous command and SQLite commit.
Reports setup and advance separately. Each run uses an isolated database,
with an intentionally trivial village and independent work-oriented NPCs.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter

from carlos_sim import (DomainEvent, SQLiteEventStore, TimeEngine, LivingWorldEngine)


def measure(count: int) -> dict:
    if type(count) is not int or count < 1:
        raise ValueError('count must be positive integer')
    with TemporaryDirectory() as tmp, SQLiteEventStore(Path(tmp) / 'performance.sqlite') as store:
        store.create_world('village')
        events = [DomainEvent('LocationCreated', None, 'fixture', 0,
                              {'id': 'market', 'name': 'Market'})]
        for i in range(count):
            npc_id = f'npc-{i:05d}'
            events.extend([
                DomainEvent('EntityCreated', None, 'fixture', 0,
                            {'id': npc_id, 'name': npc_id, 'location_id': 'market',
                             'controller': 'npc'}),
                DomainEvent('NPCConfigured', None, 'fixture', 0,
                            {'npc_id': npc_id, 'role': 'worker',
                             'needs': {'fatigue': 5, 'hunger': 20, 'safety': 0},
                             'goals': {'earn': 90, 'explore': 5, 'survive': 30}}),
            ])
            for resource in ('labor_units', 'investigation_attempts'):
                events.append(DomainEvent('ResourceChanged', None, 'fixture', 0,
                              {'owner_id': npc_id, 'resource': resource,
                               'previous': None, 'current': 0,
                               'source': 'initialization'}))
        started = perf_counter()
        store.append('village', 'setup', 0, events, bootstrap=True)
        setup_seconds = perf_counter() - started
        clock = TimeEngine(store)
        clock.open_session('village')
        started = perf_counter()
        result = LivingWorldEngine(store, clock, survival_enabled=True).advance(
            'village', seconds=60, command_id='minute',
            expected_revision=store.load('village').revision)
        advance_seconds = perf_counter() - started
        return {'npcs': count, 'setup_seconds': round(setup_seconds, 4),
                'advance_seconds': round(advance_seconds, 4),
                'advance_events': result.event_count,
                'actual_simulated_seconds': result.state.time}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--counts', nargs='+', type=int, default=[10, 25, 50])
    args = parser.parse_args()
    print(json.dumps({
        'scope': 'one full local command with SQLite, 60s simulated time; '
                 'not representative of all game systems or sustained throughput',
        'results': [measure(count) for count in args.counts],
    }, indent=2))


if __name__ == '__main__':
    main()
