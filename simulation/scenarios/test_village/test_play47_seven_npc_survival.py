"""PLAY-47: real seven-NPC food economy, 24h needs and scarcity pilot.

Not a complete joined smith+farmer village: multi-professional procurement is
currently economy-only, while this scenario deliberately enables full life.
No NPC shopping or deliveries are scripted after trusted time-zero genesis.
"""
from __future__ import annotations

import json

from carlos_sim import LivingWorldEngine, SQLiteEventStore, TimeEngine
from carlos_sim.economic_diagnostics import audit_npc_economy
from play_physical_supply import (
    DAY, PEOPLE, WORLD, audit_physical_supply, seed_physical_supply,
)


def _run_survival(db, *, water: int, target: int, label: str):
    """Advance one verified 7-NPC world in bounded, real in-world time."""
    seed_physical_supply(
        db, water=water, initial_market_food=3, personal_food=0,
        harvest_yield=3, market_wallets=True,
        hungry_market_buyers=True,
    )
    start = db.load(WORLD)
    assert len(start.npcs) == len(PEOPLE) == 7
    assert sum(1 for owner in start.entities.values()
               if owner["controller"] == "player") == 1
    initial = audit_npc_economy(start)
    assert initial["copper_known_total"] == 12
    clock = TimeEngine(db)
    clock.open_session(WORLD)
    try:
        engine = LivingWorldEngine(
            db, clock, max_events_per_advance=5000,
            decision_cooldown=3600, navigation_enabled=True,
            routines_enabled=True, survival_enabled=True,
            consumption_enabled=True, supply_enabled=True,
            economic_enabled=True, adaptive_market_enabled=True,
            agriculture_enabled=True, economy_only_enabled=False,
        )
        audit = [initial]
        current = start
        while current.time < target:
            next_time = min(current.time + DAY // 4, target)
            current = engine.advance(
                WORLD, seconds=next_time-current.time,
                command_id=f"play47:survival:{label}:{current.time}",
                expected_revision=current.revision,
            ).state
            assert current.time == next_time
            audit_physical_supply(
                current, seed=1, water=water, buyer_copper=2,
                personal_food=0, initial_market_food=3,
            )
            point = audit_npc_economy(current)
            assert point["copper_known_total"] == initial["copper_known_total"]
            assert point["copper_unknown_owners"] == initial["copper_unknown_owners"]
            assert set(point["npc_hunger"]) == {p[0] for p in PEOPLE}
            assert all(type(h) is int and 0 <= h <= 100
                       for h in point["npc_hunger"].values())
            assert db.verify(WORLD).to_dict() == current.to_dict()
            audit.append(point)
        db.snapshot(WORLD)
        assert db.verify(WORLD).to_dict() == current.to_dict()
        assert db.db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        return current, audit
    finally:
        clock.close_session(WORLD)


def test_seven_autonomous_people_24h_food_and_money_audit(tmp_path):
    """Prove that hunger advances in full life, unlike economy-only mode."""
    with SQLiteEventStore(tmp_path / "play47-seven-people.sqlite") as db:
        state, audit = _run_survival(db, water=2, target=DAY, label="seven")
        assert state.time == DAY and len(state.npcs) == 7
        assert audit[-1]["copper_known_total"] == 12
        assert any(audit[-1]["npc_hunger"][who] != audit[0]["npc_hunger"][who]
                   for who in audit[0]["npc_hunger"])
        assert all(row["completed_jobs"] >= 0
                   and row["trades"] >= 0 and row["wage_receipts"] >= 0
                   for row in audit)
        # Observe without mandating sustainability or free supply.
        print("PLAY47_SEVEN_NPC_FULL_LIFE_24H", json.dumps(
            [{"time": a["time"], "hunger": a["npc_hunger"],
              "trades": a["trades"], "jobs": a["completed_jobs"],
              "wages": a["wage_receipts"],
              "copper": a["copper_known_total"],
              "unknown_wallets": a["copper_unknown_owners"]}
             for a in audit], sort_keys=True))


def test_no_water_does_not_create_free_harvest_in_seven_npc_village(tmp_path):
    """Resource infeasibility is a valid deterministic economic observation."""
    with SQLiteEventStore(tmp_path / "play47-no-water.sqlite") as db:
        state, audit = _run_survival(
            db, water=0, target=DAY // 4, label="dry"
        )
        assert state.resources["well"]["water"] == 0
        assert state.resources["farm"]["water"] == 0
        assert all(j["recipe_id"] != "finite-harvest"
                   or j["status"] != "completed"
                   for j in state.production_jobs.values())
        assert audit[-1]["copper_known_total"] == 12
        # The three physical opening loaves may be sold/eaten. That is
        # deliberately not the same as fresh water-funded harvest.
