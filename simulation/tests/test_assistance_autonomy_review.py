"""Phase 01-K review: causal ordering and robust invalid actor identifiers."""
from pathlib import Path

import pytest

from carlos_sim import (DomainEvent, SQLiteEventStore, TimeEngine,
                        NPCAssistanceService, NPCMovementService,
                        LivingWorldEngine, choose_assistance_intent)
from test_assistance import setup


def _two_claimants(db, *, accepted: bool) -> TimeEngine:
    """The earlier Nora request ID sorts *after* the newer Sara ID."""
    setup(db)
    clock = TimeEngine(db)
    clock.open_session('w')
    service = NPCAssistanceService(db, clock)
    service.request('w', 'nora', 'basim', 'food', 8, 'z-nora-first',
                    expected_revision=db.load('w').revision)
    if accepted:
        service.respond('w', 'basim', 'z-nora-first', accept=True,
                        command_id='accept-nora', expected_revision=db.load('w').revision)
    NPCMovementService(db, clock).start('w', 'sara', 'road', 'sara-arriving',
                                        expected_revision=db.load('w').revision)
    clock.advance('w', seconds=20, command_id='sara-reaches-market',
                  expected_revision=db.load('w').revision)
    service.request('w', 'sara', 'basim', 'food', 5, 'a-sara-second',
                    expected_revision=db.load('w').revision)
    if accepted:
        service.respond('w', 'basim', 'a-sara-second', accept=True,
                        command_id='accept-sara', expected_revision=db.load('w').revision)
        clock.advance('w', seconds=1, command_id='next-day-step',
                      expected_revision=db.load('w').revision)
    return clock


def test_oldest_promised_help_precedes_newer_lexically_first_id(tmp_path):
    with SQLiteEventStore(tmp_path/'promised.db') as db:
        clock = _two_claimants(db, accepted=True)
        state = db.load('w')
        choice = choose_assistance_intent(state, 'basim', 'settle')
        assert choice is not None
        assert choice.event_type == 'AssistanceFulfilled'
        assert choice.request_id == 'z-nora-first'
        updated = LivingWorldEngine(db, clock, assistance_enabled=True).advance(
            'w', seconds=1, command_id='honor-first', expected_revision=state.revision)
        assert updated.state.obligations['z-nora-first']['status'] == 'fulfilled'
        assert updated.state.resources['nora']['food'] == 9
        assert updated.state.resources['basim']['food'] == 2
        assert db.verify('w').to_dict() == updated.state.to_dict()


def test_oldest_pending_request_precedes_newer_lexically_first_id(tmp_path):
    with SQLiteEventStore(tmp_path/'requested.db') as db:
        _two_claimants(db, accepted=False)
        state = db.load('w')
        choice = choose_assistance_intent(state, 'basim', 'respond')
        assert choice is not None
        assert choice.request_id == 'z-nora-first'
        assert choice.fields == {'accept': True}


def test_oversized_legal_npc_id_cannot_block_entire_time_advance(tmp_path):
    long_id = 'q' * 125
    with SQLiteEventStore(tmp_path/'long-id.db') as db:
        setup(db)
        before = db.load('w')
        events = [
            DomainEvent('EntityCreated', None, 'test long NPC', 0, {
                'id': long_id, 'name': 'Long ID', 'location_id': 'market',
                'controller': 'npc'}),
            DomainEvent('NPCConfigured', None, 'test long NPC', 0, {
                'npc_id': long_id, 'role': 'needy',
                'needs': {'fatigue': 5, 'hunger': 90, 'safety': 0},
                'goals': {'earn': 10, 'explore': 0, 'survive': 10}}),
            DomainEvent('ResourceChanged', None, 'test long NPC', 0, {
                'owner_id': long_id, 'resource': 'food',
                'previous': None, 'current': 0, 'source': 'initialization'}),
            *[DomainEvent('ResourceChanged', None, 'test long NPC', 0, {
                'owner_id': long_id, 'resource': counter,
                'previous': None, 'current': 0, 'source': 'initialization'})
              for counter in ('labor_units', 'investigation_attempts')]
        ]
        db.append('w','add-long-npc', before.revision, events, bootstrap=True)
        clock = TimeEngine(db)
        clock.open_session('w')
        candidate = choose_assistance_intent(db.load('w'), long_id, 'request')
        assert candidate is not None
        assert candidate.actor_id == long_id
        assert candidate.event_type == 'AssistanceRequested'
        assert len(candidate.request_id) <= 128
        assert candidate.request_id.startswith('auto-help:')
        progressed = LivingWorldEngine(db, clock, assistance_enabled=True).advance(
            'w', seconds=1, command_id='progress',
            expected_revision=db.load('w').revision)
        assert progressed.state.time == 1
        assert candidate.request_id in progressed.state.obligations
        assert progressed.state.obligations[candidate.request_id]['requester'] == long_id
        assert db.verify('w').to_dict() == progressed.state.to_dict()
