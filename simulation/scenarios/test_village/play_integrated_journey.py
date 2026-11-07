"""PLAY-19: reproducible, test-only Carlos village journey (not story canon).

Runs real gateway commands across the seven-NPC living village. This exercise
is deterministic, time advances only on explicit waits, and player-facing
records are taken solely from PlayerGateway, never hidden NPC state.
Usage from simulation/:
  PYTHONPATH=src python scenarios/test_village/play_integrated_journey.py
"""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from carlos_sim import SQLiteEventStore
from carlos_sim.player_handoff import player_handoff
from carlos_sim.resumable_play import ResumableTestSession
from carlos_sim.store import DuplicateCommand, RevisionConflict

from living_player_fixture import (
    WORLD, PLAYER, PEOPLE, living_player_gateway, setup_living_foraging_world,
)


def run_integrated_journey(path: str | Path) -> dict[str, Any]:
    """Execute a fixed human decision sequence in a fresh disposable world.

    Reports contain two distinctly labelled scopes: an actual *player-visible*
    journal and internal test-only aggregate conservation checks. Never pass
    the internal audit or WorldState to a narrative-language-model adapter.
    """
    journey: list[dict[str, Any]] = []
    timeline: list[dict[str, Any]] = []

    with ResumableTestSession.create(
        path, WORLD, PLAYER, setup_living_foraging_world, disposable_test=True
    ) as session:
        session.bind_gateway(living_player_gateway(session.store, session.clock))
        db, player = session.store, session.gateway
        start = db.verify(WORLD)
        assert len(start.npcs) == len(PEOPLE) == 7
        assert start.entities[PLAYER]["location_id"] == "square"
        assert start.resources[PLAYER]["coin_copper"] == 10
        assert start.resources["salma"]["bread"] == 3
        initial_profile = player.status().details

        def choose(name: str, method, *args, **kwargs):
            revision = db.load(WORLD).revision
            result = method(*args, command_id="play19-" + name,
                            expected_revision=revision, **kwargs)
            timeline.append({"choice": name, "status": result.status,
                             "at": result.time})
            return result

        def sight(label: str) -> dict[str, Any]:
            view = player.inspect()
            assert view.status == "present"
            place = view.details["location_id"]
            row = {
                "place": place, "time": view.time,
                "visible_people": tuple(x["id"] for x in view.details["occupants"]),
                "visible_activities": view.details["activities"],
                "label": label,
            }
            journey.append(row)
            return row

        first = sight("arrival at village square")
        assert {"carlos", "basim", "salma", "adel"} <= set(first["visible_people"])
        choose("look-square", player.observe)
        answer = choose("ask-basim-food", player.ask_food, "basim", "square")
        assert answer.status == "asked_food" and answer.details["shared"] is True
        talk = choose("talk-basim", player.interact, "basim",
                      kind="greeting", text="Good morning")
        assert talk.status == "interacted"

        offers = player.offers().details["offers"]
        assert len(offers) == 1 and offers[0]["offer_id"] == "salma-bread"
        purchased = choose("buy-three", player.buy, "salma-bread", 3, 2)
        assert purchased.status == "purchased" and purchased.details["total_paid"] == 6
        gift = choose("gift-salma", player.give, "salma", "bread", 1)
        assert gift.status == "gifted"
        breakfast = choose("eat-bread", player.eat, "bread")
        assert breakfast.status == "ate" and breakfast.details["health_effect"] == "not_modeled"

        # A real NPC tick now begins: social exchanges/actions/travel are
        # decided by the world, not scripted for each actor.
        first_tick = choose("village-life", player.wait, 1)
        assert first_tick.time == 1
        choose("look-after-life", player.observe)
        sight("neighbors after one simulated second")
        assert len(db.load(WORLD).npcs) == 7

        # Carlos must physically walk to the bakery; no teleportation.
        choose("road-bakery", player.move, "square-bakery")
        assert player.inspect().status == "traveling"
        bakery_arrival = choose("reach-bakery", player.wait, 40)
        assert bakery_arrival.time == 41
        bakery = sight("at the bakery")
        assert bakery["place"] == "bakery"
        choose("look-bakery", player.observe)
        # Autonomous NPCs may move. Talk only if the character is genuinely
        # here; no conditional branch may fabricate a meeting at a distance.
        met_nora = "nora" in bakery["visible_people"]
        if met_nora:
            choose("talk-nora", player.interact, "nora",
                   kind="greeting", text="Hello Nora")

        choose("return-square", player.move, "square-bakery")
        back = choose("reach-square", player.wait, 40)
        assert back.time == 81
        sight("back in town")
        choose("road-woods", player.move, "square-woods")
        reached = choose("reach-woods", player.wait, 50)
        assert reached.time == 131
        woods = sight("enter the woods")
        assert woods["place"] == "woods"
        choose("look-woods", player.observe)
        assert player.offers().details["offers"] == ()
        assert player.check_food().details == {
            "location_id": "woods", "status": "present",
        }

        # The finite harvest is a 60-second action with no early resource
        # minting. An NPC can continue its own life during this wait.
        at_foraging_start = db.load(WORLD).resources["woods"]["wild_food"]
        forage = choose("search-woods", player.forage)
        assert forage.status == "foraging"
        assert db.load(WORLD).resources["woods"]["wild_food"] == at_foraging_start
        harvested = choose("finish-search", player.wait, 60)
        assert harvested.time == 191
        assert harvested.details["forage_result"] == "collected"
        after_search = db.load(WORLD)
        assert after_search.resources[PLAYER]["food"] == 1
        assert after_search.resources["woods"]["wild_food"] == at_foraging_start - 1
        woodland_meal = choose("eat-foraged-food", player.eat, "food")
        assert woodland_meal.status == "ate"

        frozen_view = session.handoff()
        frozen_world = db.verify(WORLD).to_dict()
        # Read-only adapters may not create time ticks or event writes.
        assert player_handoff(player) == frozen_view
        assert db.verify(WORLD).to_dict() == frozen_world
        assert player.status().details == initial_profile
        observed = tuple(frozen_view["player_memory"].get("witnessed_events", ()))
        assert frozen_view["player_memory"]["hearsay"]
        assert len(observed) <= 20
        assert frozen_view["player_purchases"]["total"] == 1
        assert frozen_view["player_gifts"]["total"] == 1
        assert frozen_view["player_meals"]["total"] == 2
        assert frozen_world["time"] == 191
        assert frozen_world["resources"][PLAYER]["coin_copper"] == 4
        assert frozen_world["resources"][PLAYER]["bread"] == 1
        assert frozen_world["resources"][PLAYER]["food"] == 0
        assert frozen_world["resources"]["salma"]["coin_copper"] == 6
        assert frozen_world["resources"]["salma"]["bread"] == 1
        # Initial 3 loaves: one held, one gifted back, one eaten.
        assert (frozen_world["resources"][PLAYER]["bread"]
                + frozen_world["resources"]["salma"]["bread"]
                + 1 == 3)
        assert (frozen_world["resources"][PLAYER]["coin_copper"]
                + frozen_world["resources"]["salma"]["coin_copper"] == 10)
        # A search withdraws exactly one unit from a known environmental site.
        assert (frozen_world["resources"]["woods"]["wild_food"]
                + 1 == at_foraging_start)
        assert len(frozen_world["npcs"]) == 7

        before_resume_revision = frozen_world["revision"]
        db.snapshot(WORLD)
        assert db.verify(WORLD).to_dict() == frozen_world

        report: dict[str, Any] = {
            "format": "carlos-play19-integrated-test-v1",
            "canonical_story": False,
            "disposable_test": True,
            "player_visible": {
                "route_sightings": tuple(journey),
                "chosen_actions": tuple(timeline),
                "own_wallet": frozen_view["player_supplies"]["balances"],
                "own_purchases": frozen_view["player_purchases"],
                "own_gifts": frozen_view["player_gifts"],
                "own_meals": frozen_view["player_meals"],
                "own_conversations": frozen_view["player_conversations"],
                "own_hearsay": frozen_view["player_memory"]["hearsay"],
                "witnessed_events": observed,
                "met_nora_in_person": met_nora,
                "time_at_checkpoint": frozen_world["time"],
            },
            "test_audit_only": {
                "npc_count": len(frozen_world["npcs"]),
                "npc_action_count": len(frozen_world["actions"]),
                "npc_travel_count": len(frozen_world["travels"]),
                "social_exchange_count": len(frozen_world["social_messages"]),
                "bread_conserved": True, "copper_conserved": True,
                "woods_food_conserved": True,
                "no_unsanctioned_player_health_effect": True,
                "verified_replay_matches_save": True,
            },
        }

    # Re-open the exact same SQLite file in a NEW process-local session;
    # world time is NOT advanced by closing/opening the application.
    with ResumableTestSession.resume(
        path, WORLD, PLAYER, disposable_test=True
    ) as session:
        session.bind_gateway(living_player_gateway(session.store, session.clock))
        db, player = session.store, session.gateway
        assert db.verify(WORLD).to_dict() == frozen_world
        assert session.handoff() == frozen_view
        assert player.inspect().time == 191
        untouched = db.load(WORLD).to_dict()
        try:
            player.eat("food", command_id="play19-eat-foraged-food",
                       expected_revision=untouched["revision"])
        except DuplicateCommand:
            pass
        else:
            raise AssertionError("replayed meal command must not consume twice")
        try:
            player.wait(1, command_id="play19-stale",
                        expected_revision=before_resume_revision - 1)
        except RevisionConflict:
            pass
        else:
            raise AssertionError("stale player command must be rejected")
        assert db.verify(WORLD).to_dict() == untouched
        after = player.wait(10, command_id="play19-after-resume",
                            expected_revision=untouched["revision"])
        assert after.time == 201 and after.status == "ready"
        assert db.verify(WORLD).to_dict() == db.load(WORLD).to_dict()
        assert len(db.load(WORLD).npcs) == 7
        report["restart"] = {
            "handoff_identical_before_new_action": True,
            "replayed_world_identical": True,
            "no_time_advanced_while_closed": True,
            "duplicate_meal_rejected": True,
            "stale_revision_rejected": True,
            "time_after_explicit_next_wait": after.time,
        }
    return report


def main() -> None:
    print("CARLOS — PLAY-19 seven-NPC integrated journey (disposable test only)")
    with TemporaryDirectory(prefix="carlos-play19-") as root:
        result = run_integrated_journey(Path(root) / "village.sqlite")
    player = result["player_visible"]
    for scene in player["route_sightings"]:
        print(
            f"t={scene['time']:3} | {scene['place']:<7} | "
            f"nearby: {', '.join(scene['visible_people'])}"
        )
    print("Carlos paid 6 copper for 3 bread; gave 1 to Salma; ate 1.")
    print("Carlos collected 1 wild food in the woods and ate it.")
    print(f"Own wallet after journey: {player['own_wallet']}")
    print(f"NPC-to-NPC activity actually witnessed: {tuple(player['witnessed_events'])}")
    print(f"Saved at t={player['time_at_checkpoint']}; resumed and waited until t={result['restart']['time_after_explicit_next_wait']}.")
    print("Audit: 7 NPCs retained; bread/coins/woods-food conserved; SQLite replay verified.")
    print("PLAY19_JSON=" + json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
