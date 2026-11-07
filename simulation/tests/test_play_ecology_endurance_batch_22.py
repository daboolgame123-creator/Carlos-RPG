"""PLAY-22 long-horizon ecology: finite stock, snapshots and honest limits."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SIM = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SIM / 'scenarios' / 'test_village'))
from play_ecology_endurance import run_endurance, CHECKPOINT_SECONDS  # noqa: E402


@pytest.mark.parametrize('choice,owned', [('observe', 0), ('compete', 1)])
def test_endurance_retains_conservation_under_autonomous_starvation_pressure(
        tmp_path, choice, owned):
    result = run_endurance(tmp_path / (choice + '.sqlite'), choice,
                           horizon_seconds=600)
    assert result['canonical_story'] is False
    assert result['player_visible']['time'] == 600
    audit = result['test_audit_only']
    assert audit['food_initial'] == 8
    assert not audit['production_connected_to_meals']
    assert not audit['npc_mortality_modeled']
    assert audit['wait_commands'] > 0
    assert len(audit['checkpoints']) == 1
    data = audit['checkpoints'][0]
    assert data['time_seconds'] == 600
    assert data['npc_count_not_mortality'] == 7
    assert data['npc_meals'] >= 2
    assert data['npc_foraging_successes'] >= 1
    assert data['npc_trips'] >= 1
    assert data['food_balances']['player_food'] == owned
    assert sum(data['food_balances'].values()) == 8
    assert result['restart'] == {
        'verified_genesis_replay': True,
        'handoff_unchanged_on_reopen': True,
        'duplicate_and_stale_rejected': True,
        'resume_time': 610,
    }


def test_milestones_monotone_and_resource_accounting_even_after_depletion(tmp_path):
    result = run_endurance(tmp_path / 'milestones.sqlite', 'compete',
                           horizon_seconds=1800)
    milestones = result['test_audit_only']['checkpoints']
    assert [x['time_seconds'] for x in milestones] == [600, 1800]
    assert all(sum(x['food_balances'].values()) == 8 for x in milestones)
    assert all(x['npc_count_not_mortality'] == 7 for x in milestones)
    assert all(x['npc_high_hunger_count_not_deaths'] <= 7 for x in milestones)
    assert all(a['npc_meals'] <= b['npc_meals'] for a,b in zip(milestones,milestones[1:]))
    assert all(a['event_revision'] < b['event_revision'] for a,b in zip(milestones,milestones[1:]))
    assert milestones[-1]['npc_foraging_failures'] >= milestones[0]['npc_foraging_failures']


def test_endurance_repeatable_in_two_independent_sqlite_files(tmp_path):
    a = run_endurance(tmp_path / 'first.sqlite', 'observe',
                      horizon_seconds=600)
    b = run_endurance(tmp_path / 'second.sqlite', 'observe',
                      horizon_seconds=600)
    assert a == b


def test_no_private_npc_global_facts_leak_into_player_projection(tmp_path):
    report = run_endurance(tmp_path / 'private.sqlite', 'observe',
                           horizon_seconds=600)
    published = json.dumps(report['player_visible'], ensure_ascii=False)
    for secret in ('"npcs"', '"beliefs"', '"goals"', '"needs"',
                   '"obligations"', '"consumptions"', '"survival_progress"',
                   '"foraging_attempts"', '"food_balances"',
                   '"npc_high_hunger_count_not_deaths"',
                   '"npc_assistance_records"', '"event_revision"'):
        assert secret not in published
    assert 'test_audit_only' not in report['player_visible']


@pytest.mark.parametrize('choice,horizon', [
    ('invalid', 600), ('observe', 599),
    ('observe', 7201), ('observe', True),
    ('compete', 600.0), ('compete', '600'),
])
def test_invalid_endurance_horizon_rejected_before_world_creation(tmp_path,choice,horizon):
    path=tmp_path/'no-world.sqlite'
    with pytest.raises(ValueError):
        run_endurance(path, choice, horizon_seconds=horizon)
    assert not path.exists()


def test_endurance_milestone_constants_are_strictly_sorted():
    assert CHECKPOINT_SECONDS == (600, 1800, 3600, 7200)
