"""PLAY-34: two truly independent seven-NPC markets through one logical day.

Both worlds have identical global initial copper, food, land and water.
Only *ownership of the opening copper* changes; no mid-game gifts, wages,
NPC scripts, magical resources or access to the other's market state.
These are disposable internal audits, never player-visible NPC secrets.
"""
from __future__ import annotations

import json

from carlos_sim import LivingWorldEngine, SQLiteEventStore, TimeEngine
from play_physical_supply import (
    DAY, PEOPLE, WORLD, audit_physical_supply, seed_physical_supply,
)

STARTING_LOAVES = 3
CHECKPOINTS = (300, 3600, 21600, DAY)


def _audit(state, *, distributed):
    conserved = audit_physical_supply(
        state, seed=1, water=2, buyer_copper=2,
        personal_food=0, initial_market_food=STARTING_LOAVES,
    )
    assert conserved["copper"] == 12
    assert all(0 <= state.npcs[who]["needs"]["hunger"] <= 100 for who, *_ in PEOPLE)
    assert all(state.resources[who]["food"] >= 0 for who, *_ in PEOPLE)
    assert 0 <= state.resources["market"]["food"] <= STARTING_LOAVES + conserved["grown"] * 3
    assert len(state.npcs) == len(PEOPLE) == 7
    return {
        "t": state.time,
        "trades": len(state.market_trades),
        "meals": sum(m["quantity"] for m in state.consumptions.values()),
        "market_food": state.resources["market"]["food"],
        "market_copper": state.resources["market"]["coin_copper"],
        "buyer_ids": sorted({t["buyer_id"] for t in state.market_trades.values()}),
        "hunger_at_100": sum(npc["needs"]["hunger"] == 100
                             for npc in state.npcs.values()),
        "hunger_by_npc": {who: state.npcs[who]["needs"]["hunger"]
                          for who, *_ in PEOPLE},
        "coin_by_owner": {who: state.resources.get(who, {}).get("coin_copper", 0)
                          for who in ("adel", "omar", "layla", "carlos", "market")},
        "distributed": distributed,
        "crops_matured": conserved["grown"],
        "courier_deliveries": conserved["deliveries"],
    }


def _run(path, *, distributed):
    with SQLiteEventStore(path) as db:
        seed_physical_supply(
            db, personal_food=0, harvest_yield=3,
            market_wallets=distributed, initial_market_food=STARTING_LOAVES,
            hungry_market_buyers=True,
        )
        initial = db.load(WORLD)
        # Conservation includes separate owner balances, not a common wallet.
        assert _audit(initial, distributed=distributed)["market_copper"] == 0
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            engine = LivingWorldEngine(
                db, clock, max_events_per_advance=5000,
                decision_cooldown=3600, navigation_enabled=True,
                routines_enabled=True, survival_enabled=True,
                consumption_enabled=True, supply_enabled=True,
                economic_enabled=True, adaptive_market_enabled=True,
                agriculture_enabled=True, economy_only_enabled=True,
            )
            timeline = []
            for at in CHECKPOINTS:
                previous = db.load(WORLD)
                state = engine.advance(
                    WORLD, seconds=at - previous.time,
                    command_id=f"play34:{distributed}:{at}",
                    expected_revision=previous.revision,
                ).state
                assert state.time == at
                timeline.append(_audit(state, distributed=distributed))
                assert db.verify(WORLD).to_dict() == state.to_dict()
                db.snapshot(WORLD)
                assert db.verify(WORLD).to_dict() == state.to_dict()
            return timeline
        finally:
            clock.close_session(WORLD)


def test_two_disposable_villages_expose_economic_exclusion_over_a_day(tmp_path):
    concentrated = _run(tmp_path / "concentrated.sqlite", distributed=False)
    shared = _run(tmp_path / "distributed.sqlite", distributed=True)
    # Control at 300 seconds is already established by PLAY-30C:
    # same three loaves, but people own their individual budgets.
    assert concentrated[0]["buyer_ids"] == ["adel"]
    assert shared[0]["buyer_ids"] == ["adel", "layla", "omar"]
    assert concentrated[0]["trades"] == 1
    assert shared[0]["trades"] == 3
    assert concentrated[0]["market_copper"] == 2
    assert shared[0]["market_copper"] == 6
    # The two truly separate databases never gain cash or food at no cost.
    assert concentrated[-1]["t"] == shared[-1]["t"] == DAY
    assert all(row["t"] == at for row, at in zip(concentrated, CHECKPOINTS))
    assert all(row["t"] == at for row, at in zip(shared, CHECKPOINTS))
    assert all(row["hunger_at_100"] <= 7 for row in concentrated + shared)
    assert all(sum(row["coin_by_owner"].values()) == 12 for row in concentrated + shared)
    print("PLAY34_TWO_VILLAGES_DIFFERENT_WALLETS_24H",
          json.dumps({"concentrated": concentrated, "distributed": shared},
                     sort_keys=True))
