"""Phase 01-M: deterministic elapsed-time needs, privacy and survival decisions."""
import pytest

from carlos_sim import (DomainEvent, WorldState, SQLiteEventStore, TimeEngine,
                        LivingWorldEngine, NPCService, NPCActionService)
from carlos_sim.store import InvalidEvent, RevisionConflict
from carlos_sim.time_engine import AdvanceLimitExceeded, SessionClosed
from carlos_sim.survival import (HUNGER_SECONDS_PER_POINT, FATIGUE_SECONDS_PER_POINT,
                                CRITICAL_HUNGER)
from test_living_world import build, ev


def make(db, *, hunger=20, fatigue=5, names=('nora',)):
    build(db, npcs=names, fatigue=fatigue)
    clock = TimeEngine(db)
    clock.open_session('test')
    if hunger != 20:
        db.append('test', 'adjust-hunger', db.load('test').revision, [
            ev('NPCNeedChanged', {'npc_id': name, 'need': 'hunger',
                                  'previous': 20, 'current': hunger}, actor=name)
            for name in names], npc_authorized=hunger < 20)
    return clock


def tick(db, seconds, cmd='tick', *, enabled=True):
    state = db.load('test')
    return db.append('test', cmd, state.revision, [
        DomainEvent('TimeAdvanced', None, 'explicit authorized elapsed time',
                    state.time + seconds, {'from': state.time, 'to': state.time + seconds})],
                     clock_authorized=True, survival_authorized=enabled)


@pytest.fixture
def single(tmp_path):
    with SQLiteEventStore(tmp_path / 'needs.sqlite') as db:
        clock = make(db)
        yield db, clock


def test_new_mode_off_keeps_existing_time_engine_behavior(single):
    db, clock = single
    before = db.load('test').npcs['nora']['needs'].copy()
    after = clock.advance('test', seconds=3600, command_id='ordinary-clock',
                          expected_revision=db.load('test').revision)
    assert after.state.npcs['nora']['needs'] == before
    assert after.state.survival_progress == {}


def test_time_progress_is_opt_in_even_on_low_level_clock(single):
    db, clock = single
    ordinary = tick(db, 299, 'off', enabled=False)
    assert ordinary.npcs['nora']['needs']['hunger'] == 20
    assert ordinary.survival_progress == {}
    switched = tick(db, 299, 'on')
    assert switched.npcs['nora']['needs']['hunger'] == 20
    assert switched.survival_progress['nora']['hunger_seconds'] == 299
    full = tick(db, 1, 'boundary')
    assert full.npcs['nora']['needs']['hunger'] == 21
    assert full.survival_progress['nora']['hunger_seconds'] == 0


def test_basic_intervals_and_residuals(single):
    db, clock = single
    assert HUNGER_SECONDS_PER_POINT == 300
    assert FATIGUE_SECONDS_PER_POINT == 600
    one = tick(db, 299)
    assert one.npcs['nora']['needs']['hunger'] == 20
    assert one.npcs['nora']['needs']['fatigue'] == 5
    assert one.survival_progress['nora'] == {'hunger_seconds': 299, 'fatigue_seconds': 299}
    two = tick(db, 1, '300')
    assert two.npcs['nora']['needs']['hunger'] == 21
    assert two.survival_progress['nora'] == {'hunger_seconds': 0, 'fatigue_seconds': 300}
    three = tick(db, 300, '600')
    assert three.npcs['nora']['needs']['hunger'] == 22
    assert three.npcs['nora']['needs']['fatigue'] == 6
    assert three.survival_progress['nora'] == {'hunger_seconds': 0, 'fatigue_seconds': 0}
    assert db.verify('test').to_dict() == three.to_dict()


def test_single_large_step_equals_split_steps(tmp_path):
    outcomes = []
    for i, chunks in enumerate(((3600,), (299, 1, 300, 600, 1200, 1200), (900, 900, 900, 900))):
        with SQLiteEventStore(tmp_path / f'{i}.sqlite') as db:
            make(db, names=('nora', 'basim'))
            for j, seconds in enumerate(chunks):
                tick(db, seconds, f'chunk-{j}')
            state = db.verify('test').to_dict()
            state.pop('revision')
            outcomes.append(state)
    assert outcomes[0] == outcomes[1] == outcomes[2]


def test_hunger_and_fatigue_are_clamped_without_created_food(tmp_path):
    with SQLiteEventStore(tmp_path / 'limits.db') as db:
        make(db, hunger=99, fatigue=99)
        before = db.load('test').resources['nora'].copy()
        out = tick(db, 100000)
        assert out.npcs['nora']['needs']['hunger'] == 100
        assert out.npcs['nora']['needs']['fatigue'] == 100
        assert out.resources['nora'] == before
        assert out.consumptions == {}
        assert out.survival_progress['nora']['hunger_seconds'] == 100000 % 300


def test_replay_and_snapshot_through_restart(tmp_path):
    path = tmp_path / 'restart.sqlite'
    with SQLiteEventStore(path) as db:
        make(db)
        first = tick(db, 359, 'first')
        db.snapshot('test')
    with SQLiteEventStore(path) as db:
        assert db.verify('test').to_dict() == first.to_dict()
        clock = TimeEngine(db)
        with pytest.raises(SessionClosed):
            clock.advance('test', seconds=1, command_id='offline', expected_revision=first.revision)
        clock.open_session('test')
        second = tick(db, 241, 'second')
        assert second.npcs['nora']['needs']['hunger'] == 22
        assert second.npcs['nora']['needs']['fatigue'] == 6
        assert db.verify('test').to_dict() == second.to_dict()


def test_low_level_flag_requires_trusted_clock(single):
    db, clock = single
    before = db.load('test')
    event = DomainEvent('TimeAdvanced', None, 'untrusted', 600, {'from': 0, 'to': 600})
    with pytest.raises(InvalidEvent, match='trusted clock'):
        db.append('test', 'illicit', before.revision, [event], survival_authorized=True)
    assert db.load('test').to_dict() == before.to_dict()


def test_low_level_flag_cannot_advance_offline(single):
    db, clock = single
    clock.close_session('test')
    before = db.load('test')
    with pytest.raises(InvalidEvent, match='active play session'):
        tick(db, 300)
    assert db.load('test').to_dict() == before.to_dict()


def test_invalid_toggle_types_rejected(single):
    db, clock = single
    for invalid in (0, 1, None, 'yes', []):
        with pytest.raises(ValueError):
            LivingWorldEngine(db, clock, survival_enabled=invalid)
        with pytest.raises(ValueError):
            db.append('test', 'invalid', db.load('test').revision,
                [DomainEvent('TimeAdvanced', None, 'invalid', 10, {'from': 0, 'to': 10})],
                clock_authorized=True, survival_authorized=invalid)


def test_survival_progress_snapshot_is_strictly_validated(single):
    db, clock = single
    state = tick(db, 1)
    for corrupted in ({'nora': {'hunger_seconds': -1, 'fatigue_seconds': 1}},
                      {'nora': {'hunger_seconds': 300, 'fatigue_seconds': 0}},
                      {'nora': {'hunger_seconds': 0, 'fatigue_seconds': True}},
                      {'unknown': {'hunger_seconds': 0, 'fatigue_seconds': 0}}):
        data = state.to_dict()
        data['survival_progress'] = corrupted
        with pytest.raises(ValueError):
            WorldState.from_dict(data)


def test_active_rest_temporarily_pauses_baseline_fatigue(tmp_path):
    with SQLiteEventStore(tmp_path/'rest.db') as db:
        clock = make(db, fatigue=95)
        first = LivingWorldEngine(db, clock, survival_enabled=True).advance(
            'test', seconds=120, command_id='rest-and-wake',
            expected_revision=db.load('test').revision)
        activity = first.state.actions['auto:nora:0']
        assert activity['action'] == 'rest'
        assert activity['status'] == 'completed'
        # -20 from the actual rest action, never +1 fatigue while resting.
        assert first.state.npcs['nora']['needs']['fatigue'] == 75
        assert first.state.survival_progress['nora']['fatigue_seconds'] == 0
        assert first.state.survival_progress['nora']['hunger_seconds'] == 120
        assert db.verify('test').to_dict() == first.state.to_dict()


def test_work_activity_surcharge_is_separate_from_background_cost(single):
    db, clock = single
    first = LivingWorldEngine(db, clock, survival_enabled=True).advance(
        'test', seconds=180, command_id='work-once',
        expected_revision=db.load('test').revision)
    assert first.state.actions['auto:nora:0']['action'] == 'work'
    # The 180-second activity charges +10 hunger at its completion; its
    # baseline 180 seconds are saved as a fraction, not a second +10.
    assert first.state.npcs['nora']['needs']['hunger'] == 30
    assert first.state.survival_progress['nora']['hunger_seconds'] == 180
    assert first.state.resources['nora']['labor_units'] == 1


def test_critical_hunger_reprioritizes_work_only_in_survival_mode(tmp_path):
    for flag in (False, True):
        with SQLiteEventStore(tmp_path / f'{flag}.sqlite') as db:
            clock = make(db, hunger=90)
            out = LivingWorldEngine(db, clock, survival_enabled=flag).advance(
                'test', seconds=181, command_id='prioritize',
                expected_revision=db.load('test').revision)
            first = out.state.actions['auto:nora:0']
            assert first['action'] == ('rest' if flag else 'work')
            # Survival-mode distress is effective from the first decision.
            if flag:
                assert out.state.actions['auto:nora:120']['action'] in ('rest', 'wait')
            else:
                assert out.state.actions['auto:nora:180']['action'] == 'work'
            assert (len(out.state.survival_progress) > 0) == flag


def test_event_budget_rolls_back_survival_updates(single):
    db, clock = single
    before = db.load('test').to_dict()
    with pytest.raises(AdvanceLimitExceeded):
        LivingWorldEngine(db, clock, survival_enabled=True, max_events_per_advance=1).advance(
            'test', seconds=700, command_id='over-budget', expected_revision=before['revision'])
    assert db.load('test').to_dict() == before
    assert db.db.execute("SELECT count(*) FROM commands WHERE command_id='over-budget'").fetchone()[0] == 0


def test_interrupt_charges_only_elapsed_time(single):
    db, clock = single
    clock.schedule_signal('test', 'interrupt', due=90, interrupt=True,
                          expected_revision=db.load('test').revision)
    out = LivingWorldEngine(db, clock, survival_enabled=True).advance(
        'test', seconds=600, command_id='until-interrupt', expected_revision=db.load('test').revision)
    assert out.interrupted and out.state.time == 90
    assert out.state.survival_progress['nora']['hunger_seconds'] == 90
    resumed = LivingWorldEngine(db, clock, survival_enabled=True).advance(
        'test', seconds=510, command_id='resume', expected_revision=out.state.revision)
    assert resumed.state.time == 600
    assert resumed.state.survival_progress['nora']['hunger_seconds'] == 0
    assert db.verify('test').to_dict() == resumed.state.to_dict()


def test_separate_survival_mode_does_not_modify_player(single):
    db, clock = single
    before = db.load('test')
    assert 'carlos' not in before.npcs
    out = tick(db, 3600)
    assert set(out.survival_progress) == {'nora'}
    assert out.resources == before.resources
    assert out.entities == before.entities
    assert 'survival_progress' not in db.player_view('test')


def test_elapsed_time_changes_only_own_needs_not_relationships(tmp_path):
    with SQLiteEventStore(tmp_path/'private.db') as db:
        make(db, names=('nora', 'basim'))
        before = db.load('test')
        after = tick(db, 600)
        assert after.relations == before.relations == {}
        assert after.obligations == before.obligations == {}
        assert after.npcs['nora']['needs'] == after.npcs['basim']['needs']
        assert len(after.survival_progress) == 2


def test_no_time_retroactivity_when_mode_enabled_later(single):
    db, clock = single
    clock.advance('test', seconds=2000, command_id='off',
                  expected_revision=db.load('test').revision)
    after = tick(db, 100, 'on')
    assert after.npcs['nora']['needs']['hunger'] == 20
    assert after.survival_progress['nora']['hunger_seconds'] == 100


def test_instantaneous_consumption_does_not_add_baseline_elapsed_time(single):
    db, clock = single
    state = tick(db, 299)
    assert state.survival_progress['nora']['hunger_seconds'] == 299
    # An instantaneous trusted hunger adjustment at exactly the same tick
    # does not silently cause a second baseline update.
    current = db.append('test', 'hunger-neutral', state.revision, [
        ev('NPCNeedChanged', {'npc_id':'nora','need':'hunger', 'previous':20,'current':21},
            actor='nora', at=299)])
    assert current.survival_progress['nora']['hunger_seconds'] == 299
    after = tick(db, 1, 'next-second')
    assert after.npcs['nora']['needs']['hunger'] == 22


def test_disabling_survival_after_progress_restores_ordinary_decisions(tmp_path):
    with SQLiteEventStore(tmp_path/'toggle.db') as db:
        clock = make(db, hunger=90)
        tick(db, 1, 'survival-on')
        # Residual survival history is retained for replay, but the policy
        # itself must not leak into a subsequently disabled mode.
        from carlos_sim import choose_action
        normal = choose_action(db.load('test'), 'nora')
        survival = choose_action(db.load('test'), 'nora', survival_enabled=True)
        assert normal.action == 'work'
        assert survival.action in ('rest', 'wait')
        ordinary = LivingWorldEngine(db, clock, survival_enabled=False).advance(
            'test', seconds=1, command_id='off', expected_revision=db.load('test').revision)
        assert ordinary.state.actions['auto:nora:1']['action'] == 'work'
        assert ordinary.state.survival_progress['nora']['hunger_seconds'] == 1
        assert db.verify('test').to_dict() == ordinary.state.to_dict()


def test_survival_assistance_consumption_together_preserve_food_conservation(tmp_path):
    from test_assistance_autonomy import world_with_needy_person
    with SQLiteEventStore(tmp_path/'all-modes.sqlite') as db:
        clock=world_with_needy_person(db, provider_food=10, requester_food=0,
                                      requester_hunger=90)
        initial = db.load('w')
        engine=LivingWorldEngine(db,clock,survival_enabled=True,
                                 assistance_enabled=True,consumption_enabled=True)
        out=engine.advance('w',seconds=600,command_id='all-modes',
                           expected_revision=initial.revision)
        assert out.state.time==600
        aid = out.state.obligations['auto-help:nora:0']
        assert aid['status']=='fulfilled'
        assert out.state.consumptions
        # Food may be eaten (destroyed) but it must never be created by aid.
        assert out.state.resources['nora']['food'] + out.state.resources['basim']['food'] <= 10
        assert out.state.resources['nora']['food'] >= 0
        assert out.state.resources['basim']['food'] >= 0
        assert out.state.npcs['nora']['needs']['hunger'] < 100
        assert db.verify('w').to_dict()==out.state.to_dict()


def test_full_living_world_split_steps_match_with_metabolism(tmp_path):
    states=[]
    for i,chunks in enumerate(((600,), (100, 100, 100, 100, 100, 100))):
        with SQLiteEventStore(tmp_path/f'{i}.db') as db:
            clock=make(db)
            engine=LivingWorldEngine(db, clock, survival_enabled=True)
            for j,seconds in enumerate(chunks):
                engine.advance('test',seconds=seconds,command_id=f'chunk{j}',
                               expected_revision=db.load('test').revision)
            state=db.verify('test').to_dict()
            state.pop('revision')
            states.append(state)
    assert states[0]==states[1]
