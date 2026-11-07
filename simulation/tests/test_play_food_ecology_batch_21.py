"""PLAY-21: opt-in ecology integration and finite survival accounting."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SIM = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SIM / 'scenarios' / 'test_village'))

from play_food_ecology import run_ecology, INITIAL_FOOD  # noqa: E402


@pytest.mark.parametrize('choice,own', [('observe', 0), ('compete', 1)])
def test_two_player_choices_produce_autonomous_foraging_without_free_food(
        tmp_path, choice, own):
    result = run_ecology(tmp_path / (choice + '.sqlite'), choice,
                         horizon_seconds=240)
    assert result['disposable_test'] and not result['canonical_story']
    assert result['player_visible']['time'] == 240
    assert result['test_audit_only']['npc_count'] == 7
    assert result['test_audit_only']['npc_foraging_attempts'] > 0
    assert result['test_audit_only']['npc_foraging_successes'] > 0
    assert result['test_audit_only']['npc_meals'] >= 2
    balances = result['test_audit_only']['finite_food_accounting']
    assert balances['player_food'] == own
    assert (balances['player_food'] + balances['npc_food']
            + balances['npc_food_eaten']
            + balances['wild_food_remaining']) == INITIAL_FOOD
    assert result['restart'] == {
        'verified_genesis_replay': True,
        'handoff_equal_on_reopen': True,
        'duplicate_and_stale_rejected_atomically': True,
        'time_after_explicit_resume': 250,
    }


def test_ecology_deterministic_across_independent_sqlite_files(tmp_path):
    a = run_ecology(tmp_path / 'first.sqlite', 'compete', horizon_seconds=240)
    b = run_ecology(tmp_path / 'second.sqlite', 'compete', horizon_seconds=240)
    assert a == b


def test_competing_player_removes_real_food_not_an_npc_inventory(tmp_path):
    a = run_ecology(tmp_path / 'observe.sqlite', 'observe', horizon_seconds=240)
    b = run_ecology(tmp_path / 'compete.sqlite', 'compete', horizon_seconds=240)
    assert b['test_audit_only']['finite_food_accounting']['player_food'] == 1
    assert a['test_audit_only']['finite_food_accounting']['player_food'] == 0
    assert b['player_visible']['handoff'] != a['player_visible']['handoff']


def test_ecology_handoff_has_no_omniscient_npc_or_private_audit(tmp_path):
    result = run_ecology(tmp_path / 'private.sqlite', 'observe',
                         horizon_seconds=180)
    public = json.dumps(result['player_visible'], ensure_ascii=False)
    for secret in (
        '"npcs"', '"foraging_attempts"', '"npc_foraging_successes"',
        '"npc_food_claims"', '"consumptions"', '"survival_progress"',
        '"test_audit_only"', '"obligations"',
    ):
        assert secret not in public


@pytest.mark.parametrize('choice,horizon', [
    ('invalid', 240), ('observe', 179),
    ('observe', 3601), ('observe', True), ('observe', '240'),
])
def test_invalid_ecology_input_fails_before_creating_sqlite(
        tmp_path, choice, horizon):
    path = tmp_path / 'should-not-exist.sqlite'
    with pytest.raises(ValueError):
        run_ecology(path, choice, horizon_seconds=horizon)
    assert not path.exists()


def test_ecology_rejects_wrong_mode_flags_but_preserves_older_worlds(tmp_path):
    from carlos_sim.resumable_play import ResumableTestSession
    from living_player_fixture import (
        WORLD, PLAYER, living_player_gateway, setup_living_npc_ecology_world,
        setup_living_npc_survival_world,
    )
    with ResumableTestSession.create(
        tmp_path / 'ecology.sqlite', WORLD, PLAYER,
        setup_living_npc_ecology_world, disposable_test=True
    ) as session:
        db = session.store
        state = db.load(WORLD).to_dict()
        for kwargs in ({}, {'npc_survival_demo': True},
                       {'npc_survival_demo': False, 'npc_ecology_demo': True},
                       {'npc_survival_demo': True, 'npc_ecology_demo': 1}):
            with pytest.raises(ValueError):
                living_player_gateway(db, session.clock, **kwargs)
        assert db.load(WORLD).to_dict() == state
        assert db.verify(WORLD).to_dict() == state
        assert living_player_gateway(
            db, session.clock,
            npc_survival_demo=True, npc_ecology_demo=True) is not None
    with ResumableTestSession.create(
        tmp_path / 'legacy-survival.sqlite', WORLD, PLAYER,
        setup_living_npc_survival_world, disposable_test=True
    ) as session:
        state = session.store.load(WORLD).to_dict()
        assert living_player_gateway(
            session.store, session.clock, npc_survival_demo=True) is not None
        with pytest.raises(ValueError):
            living_player_gateway(
                session.store, session.clock,
                npc_survival_demo=True, npc_ecology_demo=True)
        assert session.store.load(WORLD).to_dict() == state
