"""WORLD-01h: an NPC completes finite paid work during Carlos's own job."""
from __future__ import annotations

import json

from carlos_sim import (
    DomainEvent, LivingWorldEngine, PlayerGateway, SQLiteEventStore, TimeEngine,
)
from carlos_sim.domain import RULES_VERSION, SCHEMA_VERSION

WORLD = "world01h-npc-work-during-player-job"
PLAYER = "carlos"
WOODCUTTER = "independent_woodcutter"
HOME = "home"
MINE = "iron_mine"
FOREST = "lumberyard"
PLAYER_MINE_RECIPE = "carlos-finite-iron-miner"
NPC_WOOD_RECIPE = "independent-finite-timber-cutting"
OPENING_COPPER = 4


def _event(kind: str, data: dict) -> DomainEvent:
    return DomainEvent(kind, None, "WORLD-01h disposable integration setup", 0, data)


def _seed(store: SQLiteEventStore) -> None:
    store.create_world(WORLD)
    events = [
        *[_event("LocationCreated", {"id": site, "name": site})
          for site in (HOME, MINE, FOREST)],
        _event("RouteCreated", {
            "id": "home-mine", "a": HOME, "b": MINE, "seconds": 60,
        }),
        _event("EntityCreated", {
            "id": PLAYER, "name": "Carlos", "location_id": HOME,
            "controller": "player",
        }),
        _event("EntityCreated", {
            "id": WOODCUTTER, "name": "Lumber worker",
            "location_id": FOREST, "controller": "npc",
        }),
        _event("NPCConfigured", {
            "npc_id": WOODCUTTER, "role": "woodcutter",
            "needs": {"hunger": 10, "fatigue": 0, "safety": 0},
            "goals": {"earn": 10, "explore": 10, "survive": 30},
        }),
    ]
    for owner, stock in (
        (PLAYER, {"coin_copper": 2, "iron_ore": 0}),
        (MINE, {"iron_ore_reserve": 1, "iron_ore": 0,
                "pickaxe": 1, "coin_copper": 1}),
        (FOREST, {"standing_timber": 1, "wood": 0,
                  "axe": 1, "coin_copper": 1}),
        (WOODCUTTER, {"coin_copper": 0}),
    ):
        for resource, quantity in stock.items():
            events.append(_event("ResourceChanged", {
                "owner_id": owner, "resource": resource,
                "previous": None, "current": quantity,
                "source": "initialization",
            }))

    events.extend((
        _event("NPCRoutineConfigured", {
            "npc_id": WOODCUTTER, "home_id": HOME,
            "workplace_id": FOREST, "work_start": 0, "work_end": 20_000,
        }),
        _event("ProductionRecipeConfigured", {
            "id": PLAYER_MINE_RECIPE, "site_id": MINE, "role": "miner",
            "input_resource": "iron_ore_reserve", "input_amount": 1,
            "output_resource": "iron_ore", "output_amount": 1,
            "tool_resource": "pickaxe", "duration_seconds": 120,
            "wage_coin": 1, "player_worker_id": PLAYER,
        }),
        _event("ProductionRecipeConfigured", {
            "id": NPC_WOOD_RECIPE, "site_id": FOREST,
            "role": "woodcutter", "input_resource": "standing_timber",
            "input_amount": 1, "output_resource": "wood", "output_amount": 1,
            "tool_resource": "axe", "duration_seconds": 120,
            "wage_coin": 1,
        }),
    ))
    store.append(WORLD, "world01h:bootstrap", 0, events, bootstrap=True)


def _full_life_engine(store: SQLiteEventStore, clock: TimeEngine) -> LivingWorldEngine:
    return LivingWorldEngine(
        store, clock, max_events_per_advance=5000,
        economic_enabled=True, agriculture_enabled=True,
        economy_only_enabled=False, navigation_enabled=True, routines_enabled=True,
        multi_professional_markets_enabled=True, compound_procurement_enabled=True,
        consumption_enabled=True, survival_enabled=True, supply_enabled=True,
        professional_full_life_enabled=True,
    )


def _jobs(state, worker: str, recipe: str) -> list[dict]:
    return sorted((job for job in state.production_jobs.values()
                   if job["npc_id"] == worker and job["recipe_id"] == recipe),
                  key=lambda job: (job["started_at"], job["due"]))


def _copper_total(state) -> int:
    return sum(stock.get("coin_copper", 0)
               for stock in state.resources.values())


def _event_rows(store: SQLiteEventStore) -> tuple[tuple, ...]:
    return tuple(store.db.execute(
        "SELECT seq, command_id, payload, hash FROM events "
        "WHERE world_id=? ORDER BY seq", (WORLD,),
    ))


def _run_world(database) -> tuple[dict, tuple[tuple, ...]]:
    with SQLiteEventStore(database) as db:
        _seed(db)
        opening = db.verify(WORLD)
        assert opening.schema_version == SCHEMA_VERSION == 46
        assert opening.rules_version == RULES_VERSION == 73
        assert opening.entities[PLAYER]["controller"] == "player"
        assert PLAYER not in opening.npcs
        assert opening.production_jobs == {}
        assert opening.resources[MINE]["iron_ore_reserve"] == 1
        assert opening.resources[MINE]["iron_ore"] == 0
        assert opening.resources[FOREST]["standing_timber"] == 1
        assert opening.resources[FOREST]["wood"] == 0
        assert _copper_total(opening) == OPENING_COPPER

        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            gateway = PlayerGateway(
                db, clock, world_id=WORLD, player_id=PLAYER,
                engine=_full_life_engine(db, clock),
            )
            departure = gateway.move(
                "home-mine", command_id="carlos-to-mine",
                expected_revision=opening.revision,
            )
            assert departure.status == "traveling"
            gateway.wait(60, command_id="arrive-at-mine",
                         expected_revision=departure.revision)
            at_mine = db.verify(WORLD)
            npc_jobs = _jobs(at_mine, WOODCUTTER, NPC_WOOD_RECIPE)
            assert at_mine.time == 60
            assert at_mine.entities[PLAYER]["location_id"] == MINE
            assert len(npc_jobs) == 1
            npc_job = npc_jobs[0]
            npc_job_id = next(
                job_id for job_id, job in at_mine.production_jobs.items()
                if job["npc_id"] == WOODCUTTER
                and job["recipe_id"] == NPC_WOOD_RECIPE
            )
            assert npc_job["status"] == "running"
            assert (npc_job["started_at"], npc_job["due"]) == (0, 120)
            assert at_mine.resources[FOREST]["standing_timber"] == 0
            assert at_mine.resources[FOREST]["wood"] == 0
            assert at_mine.resources[FOREST]["coin_copper"] == 1
            assert at_mine.resources[WOODCUTTER]["coin_copper"] == 0
            assert _jobs(at_mine, PLAYER, PLAYER_MINE_RECIPE) == []

            player_start = gateway.work(
                PLAYER_MINE_RECIPE, command_id="carlos-starts-mining",
                expected_revision=at_mine.revision,
            )
            player_job_id = player_start.details["job_id"]
            while_both_work = db.verify(WORLD)
            assert while_both_work.time == 60
            assert while_both_work.production_jobs[player_job_id]["status"] == "running"
            assert while_both_work.production_jobs[player_job_id]["due"] == 180
            assert _jobs(while_both_work, WOODCUTTER, NPC_WOOD_RECIPE)[0]["status"] == "running"
            assert while_both_work.resources[MINE]["iron_ore_reserve"] == 0
            assert while_both_work.resources[MINE]["iron_ore"] == 0
            assert while_both_work.resources[MINE]["coin_copper"] == 1
            assert while_both_work.resources[PLAYER]["coin_copper"] == 2
            assert _copper_total(while_both_work) == OPENING_COPPER

            gateway.wait(60, command_id="wait-for-npc-output",
                         expected_revision=while_both_work.revision)
            npc_completed = db.verify(WORLD)
            npc_job = _jobs(npc_completed, WOODCUTTER, NPC_WOOD_RECIPE)[0]
            player_job = npc_completed.production_jobs[player_job_id]
            assert npc_completed.time == 120
            assert npc_job["status"] == "completed"
            assert npc_job["output_after"] == 1
            assert npc_job["work_wage"]["paid_at"] == 120
            assert npc_job["work_wage"]["amount"] == 1
            assert npc_completed.resources[FOREST]["standing_timber"] == 0
            assert npc_completed.resources[FOREST]["wood"] == 1
            assert npc_completed.resources[FOREST]["coin_copper"] == 0
            assert npc_completed.resources[WOODCUTTER]["coin_copper"] == 1
            assert player_job["status"] == "running"
            assert player_job["output_after"] is None
            assert "work_wage" not in player_job
            assert npc_completed.resources[MINE]["iron_ore"] == 0
            assert npc_completed.resources[MINE]["coin_copper"] == 1
            assert npc_completed.resources[PLAYER]["coin_copper"] == 2
            assert _copper_total(npc_completed) == OPENING_COPPER

            starts = [json.loads(row[2]) for row in _event_rows(db)]
            starts = [event for event in starts
                      if event["event_type"] == "ProductionStarted"]
            by_job_id = {event["data"]["id"]: event for event in starts}
            npc_start_event = by_job_id[npc_job_id]
            assert (npc_start_event["actor_id"], npc_start_event["time"]) == (
                WOODCUTTER, 0,
            )
            assert npc_start_event["cause"].startswith("autonomous production:")
            assert (by_job_id[player_job_id]["actor_id"],
                    by_job_id[player_job_id]["cause"],
                    by_job_id[player_job_id]["time"]) == (
                PLAYER, "player explicitly started contracted local production", 60,
            )

            gateway.wait(60, command_id="finish-carlos-mining",
                         expected_revision=npc_completed.revision)
            final = db.verify(WORLD)
            player_job = final.production_jobs[player_job_id]
            npc_job = _jobs(final, WOODCUTTER, NPC_WOOD_RECIPE)[0]
            assert final.time == 180
            assert player_job["status"] == "completed"
            assert player_job["output_after"] == 1
            assert player_job["work_wage"]["paid_at"] == 180
            assert player_job["work_wage"]["amount"] == 1
            assert final.resources[MINE]["iron_ore_reserve"] == 0
            assert final.resources[MINE]["iron_ore"] == 1
            assert final.resources[MINE]["coin_copper"] == 0
            assert final.resources[PLAYER]["coin_copper"] == 3
            assert final.resources[WOODCUTTER]["coin_copper"] == 1
            assert _copper_total(final) == OPENING_COPPER
            assert len(_jobs(final, PLAYER, PLAYER_MINE_RECIPE)) == 1
            assert len(_jobs(final, WOODCUTTER, NPC_WOOD_RECIPE)) == 1
            assert final.entities[PLAYER]["controller"] == "player"
            assert PLAYER not in final.npcs

            db.snapshot(WORLD)
            assert db.verify(WORLD).to_dict() == final.to_dict()
            assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
            rows = _event_rows(db)
            state_data = final.to_dict()
        finally:
            clock.close_session(WORLD)

    with SQLiteEventStore(database) as reopened:
        assert reopened.verify(WORLD).to_dict() == state_data
        assert reopened.load(WORLD).to_dict() == state_data
        assert reopened.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    return state_data, rows


def test_npc_finishes_finite_paid_work_during_carlos_mining_and_replays(
        tmp_path):
    first_state, first_events = _run_world(tmp_path / "world01h-first.sqlite")
    repeated_state, repeated_events = _run_world(tmp_path / "world01h-repeat.sqlite")

    assert repeated_state == first_state
    assert repeated_events == first_events
