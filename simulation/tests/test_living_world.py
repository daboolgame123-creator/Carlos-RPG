"""Phase 01-E regression tests for truly repeated NPC action lifecycles."""
import json
import pytest

from carlos_sim import (DomainEvent, SQLiteEventStore, TimeEngine,
                        LivingWorldEngine, AdvanceLimitExceeded)
from carlos_sim.store import DuplicateCommand, RevisionConflict, InvalidEvent


def ev(kind, data, actor=None, at=0):
    return DomainEvent(kind, actor, 'test setup', at, data)


def build(db, *, npcs=('nora', 'basim'), counters=True, fatigue=5,
          goal_earn=90, goal_explore=5):
    db.create_world('test')
    events = [ev('LocationCreated', {'id': 'village', 'name': 'Test Village'})]
    for name in npcs:
        events += [
            ev('EntityCreated', {'id': name, 'name': name, 'location_id': 'village',
                                 'controller': 'npc'}),
            ev('NPCConfigured', {'npc_id': name, 'role': 'worker',
                                 'needs': {'fatigue': fatigue, 'hunger': 20, 'safety': 0},
                                 'goals': {'earn': goal_earn, 'explore': goal_explore,
                                           'survive': 30}}),
        ]
        if counters:
            for resource in ('labor_units', 'investigation_attempts'):
                events.append(ev('ResourceChanged', {'owner_id': name,
                    'resource': resource, 'previous': None, 'current': 0,
                    'source': 'initialization'}))
    db.append('test', 'setup', 0, events, bootstrap=True)


@pytest.fixture
def world(tmp_path):
    with SQLiteEventStore(tmp_path / 'simulation.db') as db:
        build(db)
        clock = TimeEngine(db)
        clock.open_session('test')
        yield db, clock, LivingWorldEngine(db, clock)


def test_single_request_repeats_work_after_completion(world):
    db, _, engine = world
    result = engine.advance('test', seconds=400, command_id='travel',
                            expected_revision=db.load('test').revision)
    assert result.state.time == 400
    assert len(result.started_action_ids) >= 4
    assert len(result.completed_action_ids) >= 4
    assert all(a['npc_id'] in ('nora', 'basim') for a in result.state.actions.values())
    assert all(result.state.actions[ident]['status'] == 'completed'
               for ident in result.completed_action_ids)
    assert db.verify('test').to_dict() == result.state.to_dict()


def test_first_short_step_starts_actions_without_finishing(world):
    db, _, engine = world
    result = engine.advance('test', seconds=10, command_id='short', expected_revision=db.load('test').revision)
    assert result.state.time == 10
    assert result.started_action_ids == ('auto:basim:0', 'auto:nora:0')
    assert result.completed_action_ids == ()
    assert all(a['status'] == 'running' for a in result.state.actions.values())


def test_two_npcs_progress_simultaneously(world):
    db, _, engine = world
    result = engine.advance('test', seconds=180, command_id='both', expected_revision=db.load('test').revision)
    assert result.state.resources['nora']['labor_units'] == 1
    assert result.state.resources['basim']['labor_units'] == 1
    assert result.completed_action_ids == ('auto:basim:0', 'auto:nora:0')
    assert any(a['status'] == 'running' for a in result.state.actions.values())  # new cycle at t=180


def test_player_interrupt_stops_next_autonomy_tick(world):
    db, clock, engine = world
    state = clock.schedule_signal('test', 'player-warning', due=90,
                                  interrupt=True, expected_revision=db.load('test').revision)
    result = engine.advance('test', seconds=400, command_id='walk', expected_revision=state.revision)
    assert (result.state.time, result.remaining_seconds, result.interrupted) == (90, 310, True)
    assert result.completed_action_ids == ()
    continued = engine.advance('test', seconds=result.remaining_seconds, command_id='resume',
                               expected_revision=result.state.revision)
    assert continued.state.time == 400
    assert continued.completed_action_ids


def test_noninterrupting_external_signal_does_not_stop_player(world):
    db, clock, engine = world
    clock.schedule_signal('test', 'bell', due=70,
                          interrupt=False, expected_revision=db.load('test').revision)
    result = engine.advance('test', seconds=100, command_id='cross', expected_revision=db.load('test').revision)
    assert 'bell' in result.fired_ids and not result.interrupted and result.state.time == 100


def test_same_due_time_interrupt_priority_is_deterministic(world):
    db, clock, engine = world
    clock.schedule_signal('test', 'interrupt', due=180,
                          interrupt=True, expected_revision=db.load('test').revision)
    result = engine.advance('test', seconds=200, command_id='first', expected_revision=db.load('test').revision)
    # The older signal fires first at t=180, before NPC actions scheduled at t=0.
    assert result.fired_ids == ('interrupt',)
    assert result.state.time == 180
    assert result.state.actions['auto:nora:0']['status'] == 'running'
    next_result = engine.advance('test', seconds=20, command_id='second', expected_revision=result.state.revision)
    assert next_result.completed_action_ids == ('auto:basim:0', 'auto:nora:0')


def test_no_real_world_background_time_on_pause(world):
    db, clock, engine = world
    result = engine.advance('test', seconds=12, command_id='first', expected_revision=db.load('test').revision)
    clock.close_session('test')
    old = db.load('test').to_dict()
    with pytest.raises(PermissionError):
        engine.advance('test', seconds=100, command_id='offline', expected_revision=result.state.revision)
    assert db.load('test').to_dict() == old
    clock.open_session('test')
    resumed = engine.advance('test', seconds=1, command_id='resumed', expected_revision=result.state.revision)
    assert resumed.state.time == 13


def test_restart_replay_and_continued_lifecycle(tmp_path):
    path = tmp_path / 'restart.db'
    with SQLiteEventStore(path) as db:
        build(db, npcs=('nora',))
        clock = TimeEngine(db)
        clock.open_session('test')
        first = LivingWorldEngine(db, clock).advance('test', seconds=100,
                    command_id='first', expected_revision=db.load('test').revision)
        db.snapshot('test')
    with SQLiteEventStore(path) as db:
        clock = TimeEngine(db)
        assert db.verify('test').time == 100
        with pytest.raises(PermissionError):
            LivingWorldEngine(db, clock).advance('test', seconds=80,
                 command_id='offline', expected_revision=first.state.revision)
        assert db.load('test').time == 100
        clock.open_session('test')
        done = LivingWorldEngine(db, clock).advance('test', seconds=200,
                   command_id='resume', expected_revision=first.state.revision)
        assert done.state.time == 300
        assert len(done.completed_action_ids) >= 1
        assert db.verify('test').to_dict() == done.state.to_dict()


def test_event_budget_exhaustion_is_atomic(world):
    db, clock, _ = world
    prior = db.load('test').to_dict()
    with pytest.raises(AdvanceLimitExceeded):
        LivingWorldEngine(db, clock, max_events_per_advance=3).advance('test',
             seconds=400, command_id='overflow', expected_revision=prior['revision'])
    assert db.load('test').to_dict() == prior
    assert db.db.execute('SELECT count(*) FROM commands WHERE command_id=?', ('overflow',)).fetchone()[0] == 0


def test_missing_resource_fails_without_partial_state(tmp_path):
    with SQLiteEventStore(tmp_path/'missing.db') as db:
        build(db, npcs=('nora',), counters=False)
        clock = TimeEngine(db); clock.open_session('test')
        original = db.load('test').to_dict()
        with pytest.raises(InvalidEvent, match='initialized'):
            LivingWorldEngine(db, clock).advance('test', seconds=300,
                  command_id='bad', expected_revision=original['revision'])
        assert db.load('test').to_dict() == original


def test_invalid_parameters_and_store_mismatch(world, tmp_path):
    db, clock, engine = world
    for invalid in (0, -1, True, 0.2):
        with pytest.raises(ValueError):
            engine.advance('test', seconds=invalid, command_id='bad', expected_revision=db.load('test').revision)
    with pytest.raises(ValueError): LivingWorldEngine(db, clock, max_events_per_advance=0)
    with pytest.raises(ValueError): LivingWorldEngine(db, clock, decision_cooldown=10)
    with SQLiteEventStore(tmp_path/'other.db') as other:
        with pytest.raises(ValueError): LivingWorldEngine(other, clock)


def test_duplicate_command_and_stale_revision(world):
    db, clock, engine = world
    prior = db.load('test').revision
    engine.advance('test', seconds=5, command_id='same', expected_revision=prior)
    with pytest.raises(DuplicateCommand):
        engine.advance('test', seconds=50, command_id='same', expected_revision=prior)
    with pytest.raises(RevisionConflict):
        engine.advance('test', seconds=50, command_id='stale', expected_revision=prior)


def test_no_npcs_only_advances_time(tmp_path):
    with SQLiteEventStore(tmp_path/'empty.db') as db:
        db.create_world('test')
        clock=TimeEngine(db);clock.open_session('test')
        result=LivingWorldEngine(db,clock).advance('test',seconds=200,
                         command_id='empty',expected_revision=0)
        assert result.state.time==200 and result.started_action_ids==()
        assert db.verify('test').to_dict()==result.state.to_dict()


def test_decisions_are_not_repeated_every_second(world):
    db, _, engine=world
    result=engine.advance('test',seconds=100,command_id='hundred',expected_revision=db.load('test').revision)
    assert len(result.started_action_ids)==2 and len(result.completed_action_ids)==0


def test_determinism_independent_of_seed_and_runtimes(tmp_path):
    results=[]
    for n in (0, 1):
        with SQLiteEventStore(tmp_path/f'{n}.db') as db:
            build(db)
            clock=TimeEngine(db);clock.open_session('test')
            output=LivingWorldEngine(db,clock).advance('test',seconds=500,
                         command_id='run',expected_revision=db.load('test').revision)
            results.append((output.state.to_dict(), output.fired_ids, output.started_action_ids))
    assert results[0]==results[1]


def test_separate_commands_same_result_as_single_command(tmp_path):
    results=[]
    for i, chunks in enumerate(((400,), (100,100,100,100))):
        with SQLiteEventStore(tmp_path/f'chunk{i}.db') as db:
            build(db)
            clock=TimeEngine(db);clock.open_session('test')
            engine=LivingWorldEngine(db,clock)
            for n, seconds in enumerate(chunks):
                engine.advance('test',seconds=seconds,command_id=f'chunk{n}',
                               expected_revision=db.load('test').revision)
            state=db.verify('test').to_dict()
            for attr in ('revision',):
                state.pop(attr)
            results.append(state)
    # Splitting commands can add time-boundary events; semantic state (excluding
    # revision/event count) must not depend on grouping of player actions.
    assert results[0]==results[1]


def test_long_run_bounded_at_1200_seconds(world):
    db, _, engine=world
    result=engine.advance('test',seconds=1200,command_id='long',expected_revision=db.load('test').revision)
    assert result.state.time==1200
    assert len(result.completed_action_ids)>=8
    assert result.event_count<1000
    assert db.verify('test').to_dict()==result.state.to_dict()


def test_no_player_entities_are_autonomous(tmp_path):
    with SQLiteEventStore(tmp_path/'player.db') as db:
        build(db, npcs=('nora',))
        db.append('test', 'player', db.load('test').revision,
           [ev('EntityCreated', {'id':'carlos','name':'Carlos',
                 'location_id':'village','controller':'player'})])
        clock=TimeEngine(db);clock.open_session('test')
        engine=LivingWorldEngine(db,clock)
        result=engine.advance('test',seconds=200,command_id='go',
                                expected_revision=db.load('test').revision)
        assert all(a['npc_id'] != 'carlos' for a in result.state.actions.values())
        assert all('carlos' not in action_id for action_id in result.started_action_ids)


def test_break_on_due_interrupt_leaves_other_due_events_pending(world):
    db, clock, engine=world
    clock.schedule_signal('test','warning',due=180,interrupt=True,
                          expected_revision=db.load('test').revision)
    result=engine.advance('test',seconds=181,command_id='first',
                          expected_revision=db.load('test').revision)
    assert result.state.time==180 and result.interrupted
    assert any(a['status']=='running' for a in result.state.actions.values())
    continued=engine.advance('test',seconds=1,command_id='later',
                    expected_revision=result.state.revision)
    assert len(continued.completed_action_ids)==2
    assert db.verify('test').to_dict()==continued.state.to_dict()


def test_snapshot_determinism_after_several_restarts(tmp_path):
    path=tmp_path/'stability.sqlite'
    with SQLiteEventStore(path) as db:
        build(db, npcs=('nora',))
    for n in range(3):
        with SQLiteEventStore(path) as db:
            clock=TimeEngine(db);clock.open_session('test')
            LivingWorldEngine(db,clock).advance('test',seconds=100,
                              command_id=f'step{n}',expected_revision=db.load('test').revision)
            db.snapshot('test')
            assert db.verify('test').to_dict()==db.load('test').to_dict()
    with SQLiteEventStore(path) as db:
        assert db.load('test').time==300
        assert db.verify('test').to_dict()==db.load('test').to_dict()


def test_prior_npc_service_decision_is_started_on_same_tick(tmp_path):
    from carlos_sim import NPCService
    with SQLiteEventStore(tmp_path / 'handoff.db') as db:
        build(db, npcs=('nora',))
        clock = TimeEngine(db)
        clock.open_session('test')
        manual = NPCService(db, clock).decide('test', 'nora',
            command_id='manual-decision', expected_revision=db.load('test').revision)
        assert manual.action == 'work'
        prior = db.load('test')
        assert prior.npcs['nora']['next_decision_at'] == 60
        result = LivingWorldEngine(db, clock).advance('test', seconds=10,
            command_id='handoff', expected_revision=prior.revision)
        assert result.started_action_ids == ('auto:nora:0',)
        assert result.state.actions['auto:nora:0']['action'] == 'work'
        assert result.state.npcs['nora']['last_decision']['at'] == 0
        assert db.verify('test').to_dict() == result.state.to_dict()


def test_preexisting_decision_is_not_recorded_twice(tmp_path):
    from carlos_sim import NPCService
    with SQLiteEventStore(tmp_path / 'handoff2.db') as db:
        build(db, npcs=('nora',))
        clock = TimeEngine(db)
        clock.open_session('test')
        NPCService(db, clock).decide('test', 'nora',
            command_id='manual', expected_revision=db.load('test').revision)
        result = LivingWorldEngine(db, clock).advance('test', seconds=180,
            command_id='go', expected_revision=db.load('test').revision)
        counts = [row[0] for row in db.db.execute('SELECT payload FROM events')
                  if '"event_type":"NPCDecisionRecorded"' in row[0]]
        assert len(counts) == 2  # manual at t=0; autonomous decision at t=180
        assert result.completed_action_ids == ('auto:nora:0',)
