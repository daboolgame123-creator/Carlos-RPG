"""Human-selected rest, honest player views, and atomic busy-action rejection."""
from __future__ import annotations

import pytest

from carlos_sim import LivingWorldEngine, PlayerGateway, SQLiteEventStore, TimeEngine
from carlos_sim.player_needs import REST_SECONDS
from carlos_sim.store import DuplicateCommand, RevisionConflict
from carlos_sim.time_engine import SessionClosed
from test_player_needs import PLAYER, WORLD, _setup


@pytest.fixture
def gateway_world(tmp_path):
    with SQLiteEventStore(tmp_path / "needs-gateway.sqlite") as db:
        clock = _setup(db)
        gateway = PlayerGateway(
            db, clock, world_id=WORLD, player_id=PLAYER,
            engine=LivingWorldEngine(db, clock, decision_cooldown=3600),
        )
        yield db, clock, gateway


def test_own_needs_view_is_readonly_and_never_borrows_another_player(gateway_world):
    db, clock, gateway = gateway_world
    before = db.load(WORLD).to_dict()
    needs = gateway.needs().details
    assert (needs['hunger'], needs['fatigue']) == (60, 40)
    assert needs['last_meal'] is None
    needs['hunger'] = 0
    assert gateway.needs().details['hunger'] == 60
    other = PlayerGateway(db, clock, world_id=WORLD, player_id='elena')
    assert other.needs().details['hunger'] == 'not_modeled'
    assert 'fatigue' not in other.needs().details
    assert 'nora' not in str(gateway.needs().details)
    assert 'elena' not in str(gateway.needs().details)
    assert db.verify(WORLD).to_dict() == before


def test_concurrent_same_tick_meal_cannot_mix_revisions_in_needs_view(gateway_world, monkeypatch):
    db, _, gateway = gateway_world
    before = db.load(WORLD)
    path = db.db.execute('PRAGMA database_list').fetchone()[2]
    verify = db.verify
    with SQLiteEventStore(path) as writer:
        clock = TimeEngine(writer)
        clock.open_session(WORLD)
        other = PlayerGateway(writer, clock, world_id=WORLD, player_id=PLAYER)

        def verify_then_commit(world_id):
            checked = verify(world_id)
            other.eat('food', command_id='concurrent-meal',
                      expected_revision=checked.revision)
            return checked

        with monkeypatch.context() as patch:
            patch.setattr(db, 'verify', verify_then_commit)
            view = gateway.needs()
        assert view.revision == before.revision
        assert view.details['hunger'] == 60
        assert view.details['owned_edible']['food'] == 3
        assert view.details['last_meal'] is None
    actual = db.verify(WORLD)
    assert actual.time == before.time
    assert actual.revision == before.revision + 1
    assert actual.player_needs[PLAYER]['hunger'] == 25
    assert actual.resources[PLAYER]['food'] == 2


def test_gateway_rest_tracks_partial_completion_and_keeps_npc_time(gateway_world):
    db, _, gateway = gateway_world
    before = db.load(WORLD)
    started = gateway.rest(command_id='rest', expected_revision=before.revision)
    assert started.status == 'resting'
    assert started.details == {'site_id': 'home', 'remaining_seconds': REST_SECONDS}
    assert started.time == before.time
    assert started.revision == before.revision + 1
    assert gateway.inspect().details['activity'] == {
        'kind': 'resting', 'remaining_seconds': REST_SECONDS,
    }
    partial = gateway.wait(REST_SECONDS - 1, command_id='partial',
                           expected_revision=started.revision)
    assert partial.status == 'resting'
    assert partial.details['rest_remaining_seconds'] == 1
    assert 'rest_result' not in partial.details
    assert gateway.needs().details['fatigue'] == 40
    finished = gateway.wait(1, command_id='finish', expected_revision=partial.revision)
    assert finished.status == 'ready'
    assert finished.details['rest_result'] == 'completed'
    assert finished.details['rest_site_id'] == 'home'
    assert 'activity' not in gateway.inspect().details
    assert (gateway.needs().details['hunger'], gateway.needs().details['fatigue']) == (66, 20)
    after = db.verify(WORLD)
    assert after.resources['nora']['labor_units'] > before.resources['nora']['labor_units']
    assert after.resources[PLAYER] == before.resources[PLAYER]
    assert after.rpg_profiles == before.rpg_profiles


def test_all_mutating_gateway_actions_are_atomic_while_resting(gateway_world):
    db, _, gateway = gateway_world
    gateway.rest(command_id='rest', expected_revision=db.load(WORLD).revision)
    before = db.load(WORLD).to_dict()
    kwargs = {'command_id': 'busy', 'expected_revision': before['revision']}
    operations = (
        lambda: gateway.observe(**kwargs),
        lambda: gateway.move('home-woods', **kwargs),
        lambda: gateway.forage(**kwargs),
        lambda: gateway.eat('food', **kwargs),
        lambda: gateway.rest(**kwargs),
        lambda: gateway.interact('nora', kind='greeting', text='Hello', **kwargs),
        lambda: gateway.ask_food('nora', 'home', **kwargs),
        lambda: gateway.buy('missing', 1, 1, **kwargs),
        lambda: gateway.give('nora', 'food', 1, **kwargs),
        lambda: gateway.accept_quest('missing', **kwargs),
        lambda: gateway.claim_quest('missing', **kwargs),
    )
    for operation in operations:
        with pytest.raises(ValueError, match='resting'):
            operation()
        assert db.verify(WORLD).to_dict() == before
    assert gateway.offers().details['offers'] == ()
    assert gateway.supplies().details['balances']['food'] == 3


def test_rest_duplicate_stale_and_closed_session_cannot_recover_twice(gateway_world):
    db, clock, gateway = gateway_world
    revision = db.load(WORLD).revision
    started = gateway.rest(command_id='one', expected_revision=revision)
    with pytest.raises(DuplicateCommand):
        gateway.rest(command_id='one', expected_revision=started.revision)
    with pytest.raises(RevisionConflict):
        gateway.rest(command_id='stale', expected_revision=revision)
    gateway.wait(REST_SECONDS, command_id='finish', expected_revision=started.revision)
    before = db.verify(WORLD).to_dict()
    with pytest.raises(DuplicateCommand):
        gateway.rest(command_id='one', expected_revision=before['revision'])
    clock.close_session(WORLD)
    with pytest.raises(SessionClosed):
        gateway.rest(command_id='offline', expected_revision=before['revision'])
    assert db.verify(WORLD).to_dict() == before


def test_unconfigured_gateway_rest_fails_without_adding_physiology(tmp_path):
    with SQLiteEventStore(tmp_path / 'unconfigured.sqlite') as db:
        clock = _setup(db, configured=False)
        gateway = PlayerGateway(db, clock, world_id=WORLD, player_id=PLAYER)
        before = db.load(WORLD).to_dict()
        with pytest.raises(ValueError, match='not configured'):
            gateway.rest(command_id='unsupported', expected_revision=before['revision'])
        assert db.verify(WORLD).to_dict() == before


def test_foraging_scene_exposes_the_actual_busy_time(gateway_world):
    db, _, gateway = gateway_world
    started = gateway.forage(command_id='food', expected_revision=db.load(WORLD).revision)
    scene = gateway.inspect()
    assert scene.status == 'present'
    assert scene.details['activity'] == {'kind': 'foraging', 'remaining_seconds': 60}
    assert scene.revision == started.revision
    with pytest.raises(ValueError, match='foraging'):
        gateway.rest(command_id='overlap', expected_revision=started.revision)
    assert db.verify(WORLD).revision == started.revision
