"""PLAY-24: seven independently acting NPCs, with a real local food economy.

The two 90-second waits are the *only* commands made after bootstrap.
No coordinator commands any NPC to produce, post, buy or eat.
Navigation and wild-food ecology are intentionally OFF in this bounded
economic trial; the NPCs still autonomously choose/rest/work/investigate.
"""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from carlos_sim import DomainEvent, LivingWorldEngine, PlayerGateway
from carlos_sim.resumable_play import ResumableTestSession

from living_player_fixture import WORLD, PLAYER, PEOPLE
from play_food_chain import setup_living_food_chain_world, _resources


def _setup(store, *, grain: int, buyer_copper: int) -> None:
    setup_living_food_chain_world(store, grain=grain, buyer_copper=buyer_copper)
    store.append(WORLD, "play24-real-work-shift", store.load(WORLD).revision,
                 [DomainEvent("NPCRoutineConfigured", None,
                              "PLAY-24 disposable baker shift", 0, {
                     "npc_id": "basim", "home_id": "bakery",
                     "workplace_id": "square", "work_start": 0, "work_end": 600,
                 })], bootstrap=True)


def run_economic_village(path: str | Path, *, grain: int = 1,
                         buyer_copper: int = 2) -> dict:
    """One frozen test-world inventory; economy emerges from 7 NPC ticks."""
    if type(grain) is not int or grain not in (0, 1):
        raise ValueError("trial grain must be zero or one")
    if type(buyer_copper) is not int or not 0 <= buyer_copper <= 2:
        raise ValueError("trial copper must be 0, 1 or 2")
    def setup(store):
        _setup(store, grain=grain, buyer_copper=buyer_copper)
    with ResumableTestSession.create(
        path, WORLD, PLAYER, setup, disposable_test=True,
    ) as session:
        db, clock = session.store, session.clock
        session.bind_gateway(PlayerGateway(
            db, clock, world_id=WORLD, player_id=PLAYER,
            engine=LivingWorldEngine(
                db, clock, economic_enabled=True, consumption_enabled=True,
                survival_enabled=True,
            ),
        ))
        assert len(db.load(WORLD).npcs) == len(PEOPLE) == 7
        initial = _resources(db.load(WORLD), seeded_grain=grain,
                             seeded_copper=buyer_copper)
        for tick in (90, 180):
            result = session.gateway.wait(
                90, command_id=f"play24-wait-{tick}",
                expected_revision=db.load(WORLD).revision)
            assert result.time == tick
            _resources(db.load(WORLD), seeded_grain=grain,
                       seeded_copper=buyer_copper)
        final = db.load(WORLD)
        assert db.verify(WORLD).to_dict() == final.to_dict()
        db.snapshot(WORLD)
        assert db.verify(WORLD).to_dict() == final.to_dict()
        handoff = session.handoff()
        rendered = json.dumps(handoff, ensure_ascii=False)
        for secret in ('"production_jobs"', '"market_trades"', '"npcs"',
                       '"consumptions"', '"npc_routines"'):
            assert secret not in rendered
        audit = {
            "npcs": len(final.npcs),
            "jobs": len(final.production_jobs),
            "finished_jobs": sum(j["status"] == "completed" for j in final.production_jobs.values()),
            "offers": sum(o["resource"] == "food" for o in final.market_offers.values()),
            "trades": sum(t["resource"] == "food" for t in final.market_trades.values()),
            "buyers": sorted(t["buyer_id"] for t in final.market_trades.values() if t["resource"] == "food"),
            "meals": len(final.consumptions),
            "copper_total": initial["copper_total"],
            "final_food_and_coins": _resources(
                final, seeded_grain=grain, seeded_copper=buyer_copper),
            "autonomous_actions": len(final.actions),
            "player_commanded_npc_actions": 0,
        }
        assert audit["copper_total"] == audit["final_food_and_coins"]["copper_total"]
        result = {
            "format": "carlos-play24-seven-npc-local-economy-v1",
            "canonical_story": False, "disposable_test": True,
            "grain": grain, "buyer_copper": buyer_copper,
            "logical_seconds": 180, "player_view": handoff,
            "private_test_audit_only": audit,
            "verified_replay": True,
        }
    return result


def main() -> None:
    with TemporaryDirectory(prefix="carlos-play24-economic-") as folder:
        cases = {
            "funded": run_economic_village(Path(folder) / "funded.sqlite"),
            "poor": run_economic_village(Path(folder) / "poor.sqlite", buyer_copper=1),
            "no_grain": run_economic_village(Path(folder) / "empty.sqlite", grain=0),
        }
    for title, item in cases.items():
        stats = item["private_test_audit_only"]
        print(f"{title}: 7 NPC, t=180, jobs={stats['finished_jobs']}, "
              f"offers={stats['offers']}, trades={stats['trades']}, "
              f"NPC meals={stats['meals']}, copper={stats['copper_total']}")
    print("PLAY24_JSON=" + json.dumps(cases, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
