"""WORLD-02: short seven-NPC interaction of local knowledge and funded work.

The only post-setup inputs are explicit advances of game time. The finite food,
workshop materials, tool, employer cash, rumor and known road have recorded
causes in this disposable test world; this is not canonical story data.
"""
from __future__ import annotations

import json

from carlos_sim import (
    DomainEvent,
    LivingWorldEngine,
    NPCNavigationService,
    SQLiteEventStore,
    TimeEngine,
    canonical_hash,
    choose_food_route,
)


WORLD = "world02-seven-npc-autonomy"
PEOPLE = (
    ("adel", "village", "explorer", 82, 5, 85),
    ("huda", "village", "resident", 20, 5, 0),
    ("basim", "workshop", "carpenter", 15, 0, 0),
    ("nora", "remote", "farmer", 20, 5, 0),
    ("layla", "remote", "resident", 10, 5, 0),
    ("omar", "remote", "guard", 20, 5, 0),
    ("salma", "remote", "merchant", 10, 5, 0),
)


def _event(kind: str, data: dict, actor: str | None = None,
           at: int = 0) -> DomainEvent:
    return DomainEvent(kind, actor, "trusted disposable WORLD-02 setup", at, data)


def _bootstrap(store: SQLiteEventStore) -> None:
    store.create_world(WORLD)
    events = [
        _event("LocationCreated", {"id": site, "name": site.title()})
        for site in ("village", "grove", "workshop", "remote")
    ]
    events.append(_event("RouteCreated", {
        "id": "village-grove", "a": "village", "b": "grove",
        "seconds": 45,
    }))
    for npc_id, site, role, hunger, fatigue, explore in PEOPLE:
        events.extend((
            _event("EntityCreated", {
                "id": npc_id, "name": npc_id.title(),
                "location_id": site, "controller": "npc",
            }),
            _event("NPCConfigured", {
                "npc_id": npc_id, "role": role,
                "needs": {"hunger": hunger, "fatigue": fatigue, "safety": 0},
                "goals": {"earn": 30, "explore": explore, "survive": 30},
            }),
        ))
        for resource, amount in (
            ("food", 0), ("coin_copper", 0), ("labor_units", 0),
            ("investigation_attempts", 0),
        ):
            events.append(_event("ResourceChanged", {
                "owner_id": npc_id, "resource": resource, "previous": None,
                "current": amount, "source": "initialization",
            }))

    # One actual, finite production opportunity: the employer owns one wood,
    # one saw and exactly one copper to fund the recipe's wage.
    for resource, amount in (
        ("wood", 1), ("plank", 0), ("saw", 1), ("coin_copper", 1),
    ):
        events.append(_event("ResourceChanged", {
            "owner_id": "workshop", "resource": resource,
            "previous": None, "current": amount, "source": "initialization",
        }))
    events.extend((
        _event("NPCRoutineConfigured", {
            "npc_id": "basim", "home_id": "remote",
            "workplace_id": "workshop", "work_start": 0, "work_end": 900,
        }),
        _event("ProductionRecipeConfigured", {
            "id": "world02-board", "site_id": "workshop",
            "role": "carpenter", "input_resource": "wood",
            "input_amount": 1, "output_resource": "plank",
            "output_amount": 1, "tool_resource": "saw",
            "duration_seconds": 90, "wage_coin": 1,
        }),
        _event("ResourceChanged", {
            "owner_id": "grove", "resource": "wild_food",
            "previous": None, "current": 1, "source": "initialization",
        }),
    ))
    store.append(WORLD, "world02:bootstrap", 0, events, bootstrap=True)


def _share_recorded_rumor(store: SQLiteEventStore) -> None:
    state = store.load(WORLD)
    delivery_id = "world02:rumor:huda:adel:grove"
    # This is explicitly hearsay from a co-located NPC, not a world fact.
    store.append(WORLD, "world02:heard-rumor", state.revision, [
        _event("NPCInformationDelivered", {
            "npc_id": "adel", "delivery_id": delivery_id,
            "key": "food:grove",
            "claim": {
                "text": "food-state:present; observed_at=0",
                "source": "huda", "received_at": 0, "confidence": 60,
            },
            "sender_id": "huda", "location_id": "village", "method": "message",
        }, actor="huda"),
        _event("NPCBeliefReceived", {
            "npc_id": "adel", "key": "food:grove",
            "delivery_id": delivery_id,
        }, actor="adel"),
    ], npc_authorized=True)


def _engine(store: SQLiteEventStore, clock: TimeEngine) -> LivingWorldEngine:
    return LivingWorldEngine(
        store, clock,
        economic_enabled=True, agriculture_enabled=True,
        survival_enabled=True, consumption_enabled=True,
        navigation_enabled=True, routines_enabled=True,
        multi_professional_markets_enabled=True,
        compound_procurement_enabled=True,
        professional_full_life_enabled=True,
        knowledge_enabled=True, foraging_enabled=True,
        food_navigation_enabled=True,
        max_events_per_advance=5000,
    )


def _manifest(store: SQLiteEventStore) -> list[tuple[int, str, str, str]]:
    return list(store.db.execute(
        "SELECT seq, command_id, payload, hash FROM events "
        "WHERE world_id=? ORDER BY seq", (WORLD,),
    ).fetchall())


def _run_world(path) -> dict:
    with SQLiteEventStore(path) as store:
        _bootstrap(store)
        clock = TimeEngine(store)
        clock.open_session(WORLD)
        _share_recorded_rumor(store)
        NPCNavigationService(store, clock).survey(
            WORLD, "adel", command_id="world02:adel-surveys-village",
            expected_revision=store.load(WORLD).revision,
        )

        opening = store.load(WORLD)
        assert len(opening.npcs) == 7
        intent = choose_food_route(opening, "adel")
        assert intent is not None
        assert (intent.destination, intent.route_id, intent.total_seconds) == (
            "grove", "village-grove", 45,
        )
        # The rumor and route are personal. A co-located, satiated listener and
        # a hungry character at an unconnected place have no such route intent.
        assert choose_food_route(opening, "huda") is None
        assert choose_food_route(opening, "nora") is None

        engine = _engine(store, clock)
        for target in (45, 90, 135, 900):
            before = store.load(WORLD)
            result = engine.advance(
                WORLD, seconds=target - before.time,
                command_id=f"world02:time:{target}",
                expected_revision=before.revision,
            )
            assert result.state.time == target
            assert store.verify(WORLD).to_dict() == result.state.to_dict()

        final = store.load(WORLD)
        assert final.entities["adel"]["location_id"] == "grove"
        assert final.travels["auto-nav:adel:0"]["status"] == "arrived"
        assert final.travels["auto-nav:adel:0"]["due"] == 45
        assert final.npcs["adel"]["beliefs"]["food:grove"]["source"] == (
            "observation:grove"
        )
        foraging = [a for a in final.foraging_attempts.values()
                    if a["npc_id"] == "adel"]
        assert len(foraging) == 1
        assert foraging[0]["outcome"] == "collected"
        assert foraging[0]["quantity"] == 1
        assert all(t["npc_id"] == "adel" for t in final.travels.values())

        jobs = [job for job in final.production_jobs.values()
                if job["npc_id"] == "basim"]
        assert len(jobs) == 1
        job = jobs[0]
        assert job["status"] == "completed"
        assert job["recipe_id"] == "world02-board"
        assert job["work_wage"]["amount"] == 1
        assert job["work_wage"]["paid_at"] >= job["due"]
        assert final.resources["workshop"]["wood"] == 0
        assert final.resources["workshop"]["plank"] == 1
        assert final.resources["workshop"]["saw"] == 1
        assert final.resources["workshop"]["coin_copper"] == 0
        assert final.resources["basim"]["coin_copper"] == 1

        food_total = (
            sum(balance.get("food", 0) for balance in final.resources.values())
            + sum(meal["quantity"] for meal in final.consumptions.values())
            + sum(balance.get("wild_food", 0)
                  for balance in final.resources.values())
        )
        assert food_total == 1
        assert sum(balance.get("coin_copper", 0)
                   for balance in final.resources.values()) == 1
        assert sum(balance.get("wood", 0) + balance.get("plank", 0)
                   for balance in final.resources.values()) == 1

        saved_hash = canonical_hash(final.to_dict())
        event_manifest = _manifest(store)
        store.snapshot(WORLD)
        assert store.verify(WORLD).to_dict() == final.to_dict()
        clock.close_session(WORLD)

    with SQLiteEventStore(path) as reopened:
        loaded = reopened.load(WORLD)
        assert canonical_hash(loaded.to_dict()) == saved_hash
        assert reopened.verify(WORLD).to_dict() == loaded.to_dict()
        assert _manifest(reopened) == event_manifest
        assert reopened.db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    return {"state_hash": saved_hash, "events": event_manifest}


def test_seven_npc_local_knowledge_and_funded_work_replay_identically(tmp_path):
    first = _run_world(tmp_path / "world02-first.sqlite")
    second = _run_world(tmp_path / "world02-second.sqlite")
    assert first == second
