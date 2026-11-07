"""PLAY-22: two physically bounded long-horizon, finite-food NPC ecology trials.

Zero canonical story data. All choices for Carlos are human-authored.
NPC hunger cannot kill anybody in current rules: no long-horizon claim of survival.
"""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter
from typing import Any

from carlos_sim.resumable_play import ResumableTestSession
from carlos_sim.store import DuplicateCommand, RevisionConflict

from living_player_fixture import (
    WORLD, PLAYER, PEOPLE, living_player_gateway, setup_living_npc_ecology_world,
)
from play_food_ecology import INITIAL_FOOD, _conserved


CHECKPOINT_SECONDS = (600, 1800, 3600, 7200)
MAX_WAIT_SECONDS = 120


def _command(session, ident: str, method, *args):
    previous = session.store.load(WORLD)
    return method(*args, command_id=ident, expected_revision=previous.revision)


def _audit(state) -> dict[str, Any]:
    """Private evidence: never return any NPC attributes through player_visible."""
    balances = _conserved(state)
    hungry = sum(npc['needs']['hunger'] >= 90 for npc in state.npcs.values())
    attempts = tuple(state.foraging_attempts.values())
    successes = sum(row['quantity'] for row in attempts)
    failures = sum(row['quantity'] == 0 for row in attempts)
    assert len(attempts) == successes + failures
    assert successes >= 0 and failures >= 0
    assert balances['npc_food_eaten'] == sum(
        meal['quantity'] for meal in state.consumptions.values())
    assert (balances['npc_food_eaten'] + balances['npc_food'] +
            balances['player_food'] + balances['wild_food_remaining'] ==
            INITIAL_FOOD)
    assert len(state.npcs) == len(PEOPLE) == 7
    for trip in state.travels.values():
        route = state.routes[trip['route_id']]
        assert trip['due'] - trip['start'] == route['seconds']
    return {
        'time_seconds': state.time,
        'event_revision': state.revision,
        'npc_count_not_mortality': len(state.npcs),
        'npc_high_hunger_count_not_deaths': hungry,
        'npc_meals': len(state.consumptions),
        'npc_foraging_successes': successes,
        'npc_foraging_failures': failures,
        'npc_trips': len(state.travels),
        'npc_assistance_records': len(state.obligations),
        'food_balances': balances,
    }


def run_endurance(path: str | Path, choice: str = 'observe',
                  *, horizon_seconds: int = 3600) -> dict[str, Any]:
    """Advance an actual seven-NPC world, conserving the eight original foods.

    Only the player chooses whether to forage first. NPC decisions use the
    existing independent planner, history, local forage and help rules.
    """
    if choice not in ('observe', 'compete'):
        raise ValueError('choice must be observe or compete')
    if type(horizon_seconds) is not int or not 600 <= horizon_seconds <= 7200:
        raise ValueError('endurance horizon must be an integer 600..7200')
    milestones = tuple(sorted(set(
        (horizon_seconds,) +
        tuple(t for t in CHECKPOINT_SECONDS if t <= horizon_seconds)
    )))
    with ResumableTestSession.create(
        path, WORLD, PLAYER, setup_living_npc_ecology_world, disposable_test=True,
    ) as session:
        session.bind_gateway(living_player_gateway(
            session.store, session.clock,
            npc_survival_demo=True, npc_ecology_demo=True))
        db, g = session.store, session.gateway
        start = db.load(WORLD)
        assert start.time == 0
        assert _conserved(start)['npc_food_eaten'] == 0

        if choice == 'compete':
            assert _command(session, 'endurance-player-forage', g.forage).status == 'foraging'
        assert _command(session, 'endurance-initial-wait', g.wait, 60).time == 60
        assert db.load(WORLD).resources[PLAYER]['food'] == (
            1 if choice == 'compete' else 0)
        db.snapshot(WORLD)

        samples: list[dict[str, Any]] = []
        chunks = 0
        for milestone in milestones:
            while db.load(WORLD).time < milestone:
                old = db.load(WORLD)
                elapsed = min(MAX_WAIT_SECONDS, milestone - old.time)
                assert 0 < elapsed <= MAX_WAIT_SECONDS
                advanced = _command(
                    session, f'endurance-{choice}-wait-{chunks}', g.wait, elapsed)
                assert advanced.time == old.time + elapsed
                _conserved(db.load(WORLD))
                chunks += 1
                if chunks % 3 == 0:
                    state_before = db.load(WORLD).to_dict()
                    db.snapshot(WORLD)
                    assert db.load(WORLD).to_dict() == state_before
            snapshot = db.load(WORLD)
            assert snapshot.time == milestone
            sample = _audit(snapshot)
            samples.append(sample)
            db.snapshot(WORLD)

        full = db.verify(WORLD)
        assert full.to_dict() == db.load(WORLD).to_dict()
        assert full.time == horizon_seconds
        assert full.revision == db.db.execute(
            'SELECT COUNT(*) FROM events WHERE world_id=?',
            (WORLD,)).fetchone()[0]
        assert samples[-1] == _audit(full)
        assert samples[-1]['npc_foraging_successes'] >= 1
        assert samples[-1]['npc_meals'] >= 2
        assert samples[-1]['npc_trips'] >= 1

        public = session.handoff()
        assert public['canonical_story'] is False
        assert public['time'] == horizon_seconds
        published = json.dumps(public, ensure_ascii=False)
        for secret in ('"npcs"', '"beliefs"', '"goals"', '"needs"',
                       '"obligations"', '"consumptions"',
                       '"survival_progress"', '"foraging_attempts"',
                       '"npc_high_hunger_count_not_deaths"', '"food_balances"'):
            assert secret not in published
        final = full.to_dict()
        assert db.verify(WORLD).to_dict() == final

    with ResumableTestSession.resume(
        path, WORLD, PLAYER, disposable_test=True,
    ) as session:
        session.bind_gateway(living_player_gateway(
            session.store, session.clock,
            npc_survival_demo=True, npc_ecology_demo=True))
        db, g = session.store, session.gateway
        assert db.verify(WORLD).to_dict() == final
        assert session.handoff() == public
        before = db.load(WORLD).to_dict()
        try:
            g.wait(1, command_id='endurance-initial-wait',
                   expected_revision=before['revision'])
        except DuplicateCommand:
            pass
        else:
            raise AssertionError('repeat clock command was accepted')
        try:
            g.wait(1, command_id='endurance-stale',
                   expected_revision=before['revision'] - 1)
        except RevisionConflict:
            pass
        else:
            raise AssertionError('stale revision was accepted')
        assert db.load(WORLD).to_dict() == before
        assert _command(session, 'endurance-resume', g.wait, 10).time == (
            horizon_seconds + 10)
        _conserved(db.verify(WORLD))

    return {
        'format': 'carlos-play22-endurance-test-v1',
        'canonical_story': False,
        'disposable_test': True,
        'choice': choice,
        'player_visible': {'handoff_at_horizon': public, 'time': horizon_seconds},
        'test_audit_only': {
            'checkpoints': samples,
            'wait_commands': chunks,
            'food_initial': INITIAL_FOOD,
            'production_connected_to_meals': False,
            'npc_mortality_modeled': False,
        },
        'restart': {
            'verified_genesis_replay': True,
            'handoff_unchanged_on_reopen': True,
            'duplicate_and_stale_rejected': True,
            'resume_time': horizon_seconds + 10,
        },
    }


def main() -> None:
    print('CARLOS — PLAY-22: actual 3600-second food ecology, two worlds')
    with TemporaryDirectory(prefix='carlos-play22-') as folder:
        reports = {}
        for choice in ('observe', 'compete'):
            started = perf_counter()
            report = run_endurance(
                Path(folder) / (choice + '.sqlite'), choice,
                horizon_seconds=3600)
            wall_seconds = perf_counter() - started
            reports[choice] = report
            final = report['test_audit_only']['checkpoints'][-1]
            print(
                f'{choice}: logical={final["time_seconds"]}s, '
                f'NPC meals={final["npc_meals"]}, forage='
                f'{final["npc_foraging_successes"]}, '
                f'failed={final["npc_foraging_failures"]}, '
                f'events={final["event_revision"]}, '
                f'wall_seconds={wall_seconds:.2f} (diagnostic only)',
                flush=True)
    print('PLAY22_JSON=' + json.dumps(reports, ensure_ascii=False, sort_keys=True))


if __name__ == '__main__':
    main()
