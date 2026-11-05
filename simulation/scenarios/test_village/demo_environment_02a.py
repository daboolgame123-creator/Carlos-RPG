"""02-A disposable 7-NPC demo: bounded environmental food restoration.

Only pre-initialized finite potential converts to wild food. NPCs still
require actual local search time before collecting it. No Carlos story data.
"""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from carlos_sim import DomainEvent, SQLiteEventStore, TimeEngine, LivingWorldEngine
from demo_gathering_autonomy import PROFILES, event


def run() -> dict:
    with TemporaryDirectory() as scratch, SQLiteEventStore(Path(scratch) / 'env.sqlite') as db:
        db.create_world('demo')
        setup = [
            event('LocationCreated', {'id': 'grove', 'name': 'Grove'}),
            event('LocationCreated', {'id': 'square', 'name': 'Square'}),
            event('ResourceChanged', {
                'owner_id': 'grove', 'resource': 'wild_food', 'previous': None,
                'current': 0, 'source': 'initialization',
            }),
            event('ResourceChanged', {
                'owner_id': 'grove', 'resource': 'regrowth_reserve', 'previous': None,
                'current': 2, 'source': 'initialization',
            }),
            event('ResourceChanged', {
                'owner_id': 'square', 'resource': 'wild_food', 'previous': None,
                'current': 0, 'source': 'initialization',
            }),
            event('EnvironmentalCycleConfigured', {
                'id': 'grove-cycle', 'site_id': 'grove', 'period_seconds': 60,
                'capacity': 2,
            }),
        ]
        for name, site, hunger, food in PROFILES:
            setup += [
                event('EntityCreated', {
                    'id': name, 'name': name, 'location_id': site,
                    'controller': 'npc',
                }),
                event('NPCConfigured', {
                    'npc_id': name, 'role': 'explorer',
                    'needs': {'fatigue': 5, 'hunger': hunger, 'safety': 0},
                    'goals': {'earn': 0, 'explore': 95, 'survive': 30},
                }),
            ]
            for resource, quantity in (
                ('food', food), ('labor_units', 0), ('investigation_attempts', 0),
            ):
                setup.append(event('ResourceChanged', {
                    'owner_id': name, 'resource': resource,
                    'previous': None, 'current': quantity,
                    'source': 'initialization',
                }))
        db.append('demo', 'bootstrap', 0, setup, bootstrap=True)
        clock = TimeEngine(db)
        clock.open_session('demo')
        recovered = clock.advance('demo', seconds=120,
            command_id='explicit-environment-time',
            expected_revision=db.load('demo').revision).state
        assert recovered.resources['grove']['wild_food'] == 2
        assert recovered.resources['grove']['regrowth_reserve'] == 0
        gathered = LivingWorldEngine(db, clock, gathering_enabled=True).advance(
            'demo', seconds=90, command_id='real-npc-actions',
            expected_revision=db.load('demo').revision)
        done = gathered.state
        assert len(done.npcs) == 7
        assert len(done.gatherings) == 2
        assert done.resources['grove']['wild_food'] == 0
        assert done.resources['grove']['regrowth_reserve'] == 0
        assert db.verify('demo').to_dict() == done.to_dict()
        return {
            'npc_count': 7, 'time': done.time,
            'initial_wild_food': 0, 'initial_finite_regrowth_reserve': 2,
            'converted_to_wild_food': recovered.environment_cycles['grove-cycle']['converted'],
            'wild_food_after_gathering': done.resources['grove']['wild_food'],
            'regrowth_reserve_remaining': done.resources['grove']['regrowth_reserve'],
            'gathered_units': len(done.gatherings),
            'replay_verified': True,
            'note': 'Finite seeded potential converted at 60-second ticks; no free reproduction or clock drift',
        }


if __name__ == '__main__':
    print(json.dumps(run(), indent=2, ensure_ascii=False))
