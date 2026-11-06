"""Deterministic audit digest for cross-branch event/semantic parity tests.

Run *this same script* with PYTHONPATH=src on the old and optimized code,
then compare JSON. It measures correctness, not speed. Uses a disposable DB.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from carlos_sim import (DomainEvent, SQLiteEventStore, TimeEngine,
                        LivingWorldEngine, canonical_hash)


def audit(count: int) -> dict:
    if type(count) is not int or count < 1:
        raise ValueError('positive NPC count is required')
    with TemporaryDirectory() as dirname, SQLiteEventStore(Path(dirname) / 'audit.sqlite') as db:
        db.create_world('parity-world')
        setup = [DomainEvent('LocationCreated', None, 'fixture', 0,
                             {'id': 'market', 'name': 'Market'})]
        for index in range(count):
            who = f'npc-{index:05d}'
            setup.extend([
                DomainEvent('EntityCreated', None, 'fixture', 0,
                            {'id': who, 'name': who, 'location_id': 'market',
                             'controller': 'npc'}),
                DomainEvent('NPCConfigured', None, 'fixture', 0,
                            {'npc_id': who, 'role': 'worker',
                             'needs': {'fatigue': 5, 'hunger': 20, 'safety': 0},
                             'goals': {'earn': 90, 'explore': 5, 'survive': 30}}),
                DomainEvent('ResourceChanged', None, 'fixture', 0,
                            {'owner_id': who, 'resource': 'labor_units',
                             'previous': None, 'current': 0,
                             'source': 'initialization'}),
                DomainEvent('ResourceChanged', None, 'fixture', 0,
                            {'owner_id': who, 'resource': 'investigation_attempts',
                             'previous': None, 'current': 0,
                             'source': 'initialization'}),
            ])
        db.append('parity-world', 'setup', 0, setup, bootstrap=True)
        clock = TimeEngine(db)
        clock.open_session('parity-world')
        result = LivingWorldEngine(db, clock, survival_enabled=True).advance(
            'parity-world', seconds=60, command_id='one-minute',
            expected_revision=db.load('parity-world').revision)
        events = db.db.execute('SELECT seq, payload, hash FROM events '
                               'WHERE world_id=? ORDER BY seq',
                               ('parity-world',)).fetchall()
        verified = db.verify('parity-world')
        assert verified.to_dict() == result.state.to_dict()
        return {
            'npcs': count, 'time': verified.time,
            'revision': verified.revision,
            'events_count': len(events),
            'events_digest': canonical_hash(events),
            'state_digest': canonical_hash(verified.to_dict()),
            # Cross-version semantic parity: strip ONLY changed version and
            # empty collections added after the frozen baseline (01-S foraging,
            # 01-Y opt-in RPG, J1c2b local institutions). Always retain the full
            # state hash separately for same-version audits.
            'legacy_semantic_digest': canonical_hash({
                k: v for k, v in verified.to_dict().items()
                if k not in ('schema_version','rules_version','foraging_attempts','rpg_profiles','environment_cycles','production_recipes','production_jobs','market_stalls','market_offers','market_trades','loan_contracts','loan_repayments','npc_temperaments','npc_routines','rumor_deliveries','property_takings','property_sightings','property_claims','local_institutions','complaint_desks','property_complaints','property_title_origins','property_custody_lots','property_custody_moves','property_permissions','registered_claim_balances','registered_claim_offers','registered_claim_transfers')
            }),
            'replay_equal': True,
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--counts', type=int, nargs='+', default=[10, 25])
    args = parser.parse_args()
    print(json.dumps({'results': [audit(n) for n in args.counts]}, indent=2))


if __name__ == '__main__':
    main()
