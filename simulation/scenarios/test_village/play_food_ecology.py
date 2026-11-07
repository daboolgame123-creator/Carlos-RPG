"""PLAY-21: bounded, opt-in seven-NPC ecology integration (disposable only).

Existing NPC foraging, meals, food knowledge/navigation, assistance and scarcity
run together. Two real Carlos choices compete for limited food. This is NOT a
model of death, a sustainable economy, or the original canonical story.
"""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from carlos_sim.resumable_play import ResumableTestSession
from carlos_sim.store import DuplicateCommand, RevisionConflict

from living_player_fixture import (
    WORLD, PLAYER, PEOPLE, living_player_gateway, setup_living_npc_ecology_world,
)

INITIAL_FOOD = 2 + 2 + 4  # NPC-owned + square deposit + woods deposit


def _command(session, label, method, *args):
    return method(*args, command_id=label,
                  expected_revision=session.store.load(WORLD).revision)


def _conserved(state) -> dict[str, int]:
    stocks = state.resources
    npc_food = sum(stocks[who]['food'] for who, *_ in PEOPLE)
    npc_eaten = sum(meal['quantity'] for meal in state.consumptions.values())
    wild = sum(stocks[place]['wild_food'] for place in ('square', 'woods', 'bakery'))
    player_food = stocks[PLAYER]['food']
    assert all(x >= 0 for x in (npc_food, npc_eaten, wild, player_food))
    assert npc_food + npc_eaten + wild + player_food == INITIAL_FOOD, (
        'every meal and recovery must be backed by real finite food')
    assert stocks['salma']['bread'] == 3
    assert stocks[PLAYER]['coin_copper'] == 10
    return {'npc_food': npc_food, 'npc_food_eaten': npc_eaten,
            'wild_food_remaining': wild, 'player_food': player_food}


def run_ecology(path: str | Path, choice: str = 'observe',
                *, horizon_seconds: int = 360) -> dict[str, Any]:
    """Human observes or physically collects 1 square unit before NPC forage.

    Short bounded waits are actual engine events. Logical time does not advance
    during SQLite close/reopen. Private NPC audit never enters player handoff.
    """
    if choice not in ('observe', 'compete'):
        raise ValueError('choice must be observe or compete')
    if type(horizon_seconds) is not int or not 180 <= horizon_seconds <= 3600:
        raise ValueError('ecology horizon must be 180..3600 seconds')
    with ResumableTestSession.create(
        path, WORLD, PLAYER, setup_living_npc_ecology_world,
        disposable_test=True,
    ) as session:
        session.bind_gateway(living_player_gateway(
            session.store, session.clock,
            npc_survival_demo=True, npc_ecology_demo=True))
        db, g = session.store, session.gateway
        assert len(db.load(WORLD).npcs) == len(PEOPLE) == 7
        assert db.load(WORLD).time == 0

        if choice == 'compete':
            assert _command(session, 'ecology-compete-forage', g.forage).status == 'foraging'
        assert _command(session, f'ecology-{choice}-first-wait', g.wait, 60).time == 60
        if choice == 'compete':
            assert db.load(WORLD).resources[PLAYER]['food'] == 1
        else:
            assert db.load(WORLD).resources[PLAYER]['food'] == 0
        _conserved(db.load(WORLD))
        db.snapshot(WORLD)

        chunk = 0
        while db.load(WORLD).time < horizon_seconds:
            old = db.load(WORLD)
            elapsed = min(120, horizon_seconds - old.time)
            result = _command(session, f'ecology-{choice}-wait-{chunk}', g.wait, elapsed)
            assert result.time == old.time + elapsed
            _conserved(db.load(WORLD))
            chunk += 1
            # Snapshot limits replay cost. Full genesis replay is checked below.
            if chunk % 2 == 0:
                db.snapshot(WORLD)

        state = db.verify(WORLD)
        assert state.time == horizon_seconds
        assert len(state.npcs) == len(PEOPLE)
        assert len(state.foraging_attempts) >= 1, (
            'integration must actually produce autonomous NPC forage')
        assert any(row['quantity'] == 1 for row in state.foraging_attempts.values()), (
            'at least one NPC should physically collect natural food')
        assert len(state.consumptions) >= 2
        balances = _conserved(state)
        for trip in state.travels.values():
            route = state.routes[trip['route_id']]
            assert trip['due'] - trip['start'] == route['seconds']
        public = session.handoff()
        assert public['time'] == horizon_seconds
        assert public['canonical_story'] is False
        public_json = json.dumps(public, ensure_ascii=False)
        for private in ('"npcs"', '"beliefs"', '"goals"', '"needs"',
                        '"foraging_attempts"', '"consumptions"',
                        '"survival_progress"', '"obligations"'):
            assert private not in public_json
        db.snapshot(WORLD)
        assert db.verify(WORLD).to_dict() == state.to_dict()
        audit = {
            'npc_count': 7,
            'npc_foraging_attempts': len(state.foraging_attempts),
            'npc_foraging_successes': sum(
                row['quantity'] for row in state.foraging_attempts.values()),
            'npc_foraging_failures': sum(
                row['quantity'] == 0 for row in state.foraging_attempts.values()),
            'npc_meals': len(state.consumptions),
            'npc_travels': len(state.travels),
            'npc_assistance_obligations': len(state.obligations),
            'npc_food_claims': sum(
                len(npc['beliefs']) for npc in state.npcs.values()),
            'finite_food_accounting': balances,
            'player_and_vendor_money_unchanged': True,
        }
        final_dict = state.to_dict()

    with ResumableTestSession.resume(
        path, WORLD, PLAYER, disposable_test=True,
    ) as session:
        session.bind_gateway(living_player_gateway(
            session.store, session.clock,
            npc_survival_demo=True, npc_ecology_demo=True))
        db, g = session.store, session.gateway
        assert db.verify(WORLD).to_dict() == final_dict
        assert session.handoff() == public
        before = db.load(WORLD).to_dict()
        try:
            g.wait(1, command_id=f'ecology-{choice}-first-wait',
                   expected_revision=before['revision'])
        except DuplicateCommand:
            pass
        else:
            raise AssertionError('duplicate clock command was accepted')
        assert db.load(WORLD).to_dict() == before
        try:
            g.wait(1, command_id=f'ecology-{choice}-stale-wait',
                   expected_revision=before['revision'] - 1)
        except RevisionConflict:
            pass
        else:
            raise AssertionError('stale wait was accepted')
        assert db.load(WORLD).to_dict() == before
        assert _command(session, f'ecology-{choice}-resume', g.wait, 10).time == (
            horizon_seconds + 10)
        _conserved(db.verify(WORLD))

    return {
        'format': 'carlos-play21-ecology-test-v1',
        'canonical_story': False,
        'disposable_test': True,
        'choice': choice,
        'player_visible': {'handoff': public, 'time': horizon_seconds},
        'test_audit_only': audit,
        'restart': {
            'verified_genesis_replay': True,
            'handoff_equal_on_reopen': True,
            'duplicate_and_stale_rejected_atomically': True,
            'time_after_explicit_resume': horizon_seconds + 10,
        },
    }


def main() -> None:
    print('CARLOS — PLAY-21 bounded ecological village (test-only)')
    with TemporaryDirectory(prefix='carlos-play21-') as temp:
        a = run_ecology(Path(temp) / 'observe.sqlite', 'observe')
        b = run_ecology(Path(temp) / 'compete.sqlite', 'compete')
    for result in (a, b):
        print(result['choice'], 't=', result['player_visible']['time'],
              'NPC forage=', result['test_audit_only']['npc_foraging_successes'],
              'meals=', result['test_audit_only']['npc_meals'])
    print('PLAY21_JSON=' + json.dumps(
        {'observe': a, 'compete': b}, ensure_ascii=False, sort_keys=True))


if __name__ == '__main__':
    main()
