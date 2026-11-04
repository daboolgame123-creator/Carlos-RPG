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


