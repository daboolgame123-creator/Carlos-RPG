"""PLAY-20 adversarial tests: seven autonomous NPCs, finite food, two choices."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SIM = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SIM / 'scenarios' / 'test_village'))
from play_adversity import run_adversity  # noqa: E402


@pytest.mark.parametrize('choice,expected', [
    ('stockpile', {'bread': 2, 'coin_copper': 4, 'food': 0}),
    ('share', {'bread': 0, 'coin_copper': 8, 'food': 0}),
])
def test_counterfactual_choices_keep_seven_npcs_and_do_not_mint_food(
        tmp_path, choice, expected):
    result = run_adversity(tmp_path / (choice + '.sqlite'),
                           choice, horizon_seconds=600)
    assert result['canonical_story'] is False
    assert result['disposable_test'] is True
    own = result['player_visible']['handoff_at_checkpoint']
    assert own['time'] == 600
    assert own['player_supplies']['balances'] == expected
    audit = result['test_audit_only']
    assert audit['npc_count'] == 7
    assert audit['npc_meals'] == 2
    assert audit['npc_food_left'] == 0
    assert audit['forest_wild_food_left'] == 0
    assert audit['square_wild_food_left'] == 2
    assert audit['npc_actions'] >= 7
    assert audit['bread_and_coin_conserved']
    assert audit['wild_food_conserved']
    assert audit['npc_owned_food_conserved']
    assert audit['forage_depletion_accepted']
    assert all(audit['denials_without_state_mutation'][kind] for kind in (
        'busy_or_exhausted_seller', 'trade_during_travel',
        'remote_trade', 'fifth_forage', 'fifth_meal',
        'repeated_meal_command', 'stale_revision'))
    assert result['restart'] == {
        'sqlite_verified': True, 'handoff_unchanged_on_reopen': True,
        'no_wall_clock_advance': True,
        'no_duplicate_meal': True, 'no_stale_revision': True,
        'time_after_explicit_resume_wait': 610,
    }


def test_one_world_is_deterministic_across_independent_sqlite_files(tmp_path):
    a = run_adversity(tmp_path / 'a.sqlite', 'stockpile', horizon_seconds=600)
    b = run_adversity(tmp_path / 'b.sqlite', 'stockpile', horizon_seconds=600)
    assert a == b


def test_adversity_player_handoff_excludes_private_npc_state(tmp_path):
    report = run_adversity(tmp_path / 'privacy.sqlite', 'share',
                           horizon_seconds=600)
    view = json.dumps(report['player_visible'], ensure_ascii=False)
    for hidden in (
        '"npcs"', '"beliefs"', '"goals"', '"needs"',
        '"relations"', '"injuries"', '"market_trades"',
        '"consumptions"', '"survival_progress"',
        '"npc_food_left"', '"npc_actions"', '"npc_meals"',
    ):
        assert hidden not in view
    assert report['test_audit_only']['npc_count'] == 7


@pytest.mark.parametrize('bad_choice,bad_seconds', [
    ('not-a-path', 600), ('share', 290),
    ('share', 86401), ('share', True), ('share', '600'),
])
def test_adversity_rejects_invalid_horizon_or_choice_before_world_creation(
        tmp_path, bad_choice, bad_seconds):
    path = tmp_path / 'not-created.sqlite'
    with pytest.raises(ValueError):
        run_adversity(path, bad_choice, horizon_seconds=bad_seconds)
    assert not path.exists()
