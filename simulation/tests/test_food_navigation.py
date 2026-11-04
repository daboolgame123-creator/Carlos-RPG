"""Phase 01-U: remembered-food journeys, no global food/road omniscience."""
from __future__ import annotations

from dataclasses import replace

import pytest

from carlos_sim import (
    DomainEvent, LivingWorldEngine, NPCNavigationService, NPCService,
    SQLiteEventStore, TimeEngine, WorldState, choose_food_route,
)
from carlos_sim.store import DuplicateCommand
from carlos_sim.time_engine import AdvanceLimitExceeded, SessionClosed


NAMES = ("adel", "basim", "huda", "nora", "salma")


def event(kind, data, actor=None, time=0):
    return DomainEvent(kind, actor, "01-U synthetic village", time, data)


def make_world(db, *, grove_stock=2, market_stock=0, own_food=0,
               hunger=70, fatigue=5, safety=0, omit_own=False):
    db.create_world("village")
    events = []
    for site in ("market", "grove", "hill", "secret"):
        events.append(event("LocationCreated", {"id": site, "name": site}))
    for ident, a, b, seconds in (
        ("market-grove", "market", "grove", 50),
        ("market-hill", "market", "hill", 100),
        ("grove-secret", "grove", "secret", 25),
    ):
        events.append(event("RouteCreated", {
            "id": ident, "a": a, "b": b, "seconds": seconds
        }))
    for site, stock in (("market", market_stock),
                        ("grove", grove_stock), ("hill", 0), ("secret", 0)):
        if stock is not None:
            events.append(event("ResourceChanged", {
                "owner_id": site, "resource": "wild_food",
                "previous": None, "current": stock, "source": "initialization",
            }))
    for who in NAMES:
        events.extend((
            event("EntityCreated", {
                "id": who, "name": who, "controller": "npc",
                "location_id": "market",
            }),
            event("NPCConfigured", {
                "npc_id": who, "role": "explorer",
                "needs": {
                    "fatigue": fatigue if who == "adel" else 5,
                    "hunger": hunger if who == "adel" else 20,
                    "safety": safety if who == "adel" else 0,
                },
                "goals": {"earn": 0, "explore": 0, "survive": 30},
            }),
        ))
        for resource, quantity in (
            ("food", own_food if who == "adel" else 0),
            ("labor_units", 0), ("investigation_attempts", 0),
        ):
            if omit_own and who == "adel" and resource == "food":
                continue
            events.append(event("ResourceChanged", {
                "owner_id": who, "resource": resource,
                "previous": None, "current": quantity,
                "source": "initialization",
            }))
    db.append("village", "bootstrap", 0, events, bootstrap=True)


@pytest.fixture
def village(tmp_path):
    with SQLiteEventStore(tmp_path / "01u.sqlite") as db:
        make_world(db)
        clock = TimeEngine(db)
        clock.open_session("village")
        yield db, clock


def tell(db, *, site="grove", listener="adel", teller="basim",
         observed_at=0, status="present", confidence=60):
    s = db.load("village")
    key = "food:" + site
    payload = {
        "npc_id": listener,
        "delivery_id": f"rumor:{teller}:{listener}:{site}:{s.time}",
        "key": key,
        "claim": {
            "text": f"food-state:{status}; observed_at={observed_at}",
            "source": teller, "received_at": s.time,
            "confidence": confidence,
        },
        "sender_id": teller,
        "location_id": "market", "method": "message",
    }
    return db.append("village", "tell-" + payload["delivery_id"], s.revision, [
        event("NPCInformationDelivered", payload, actor=teller, time=s.time),
        event("NPCBeliefReceived", {
            "npc_id": listener, "key": key,
            "delivery_id": payload["delivery_id"],
        }, actor=listener, time=s.time),
    ], npc_authorized=True)


def learn_local_roads(db, clock):
    return NPCNavigationService(db, clock).survey(
        "village", "adel", command_id="survey-adel",
        expected_revision=db.load("village").revision,
    )


def advance(db, clock, seconds, command, *, food_navigation=True, budget=1000):
    return LivingWorldEngine(
        db, clock, navigation_enabled=True, knowledge_enabled=True,
        foraging_enabled=True, food_navigation_enabled=food_navigation,
        max_events_per_advance=budget,
    ).advance("village", seconds=seconds, command_id=command,
              expected_revision=db.load("village").revision)


def test_config_dependencies_are_explicit(village):
    db, clock = village
    for bad in (None, 0, 1, "true", [], {}):
        with pytest.raises(ValueError, match="food_navigation_enabled"):
            LivingWorldEngine(db, clock, food_navigation_enabled=bad)
    for missing in (
        {"navigation_enabled": True, "knowledge_enabled": True},
        {"foraging_enabled": True, "knowledge_enabled": True},
        {"navigation_enabled": True, "foraging_enabled": True},
    ):
        with pytest.raises(ValueError, match="food_navigation_enabled requires"):
            LivingWorldEngine(db, clock, food_navigation_enabled=True, **missing)


def test_chooses_cheapest_learned_route_ignoring_remote_truth_and_private_peers(village):
    db, clock = village
    tell(db, site="grove")
    tell(db, site="hill")
    learn_local_roads(db, clock)
    s = db.load("village")
    intent = choose_food_route(s, "adel")
    assert intent is not None
    assert (intent.destination, intent.route_id, intent.total_seconds) == (
        "grove", "market-grove", 50
    )
    assert intent.source == "basim"
    assert intent.observed_at == 0

    private = s.to_dict()
    private["resources"]["grove"]["wild_food"] = 0
    private["resources"]["hill"]["wild_food"] = 1000000
    private["npcs"]["nora"]["beliefs"]["food:secret"] = {
        "text": "food-state:present; observed_at=0",
        "source": "basim", "received_at": 0, "confidence": 60,
    }
    forged_remote = WorldState(**private)
    assert choose_food_route(forged_remote, "adel") == intent
    assert choose_food_route(s, "nora") is None


def test_false_hearsay_can_motivate_travel_but_direct_arrival_corrects_it(tmp_path):
    with SQLiteEventStore(tmp_path / "false-rumor.sqlite") as db:
        make_world(db, grove_stock=0)
        clock = TimeEngine(db)
        clock.open_session("village")
        tell(db)
        result = advance(db, clock, 50, "reach-empty")
        s = result.state
        assert s.entities["adel"]["location_id"] == "grove"
        assert s.travels["auto-nav:adel:0"]["status"] == "arrived"
        assert s.npcs["adel"]["beliefs"]["food:grove"]["text"] == (
            "food-state:empty; observed_at=50"
        )
        assert s.npcs["adel"]["beliefs"]["food:grove"]["source"] == "observation:grove"
        assert not any(v["npc_id"] == "adel" for v in s.foraging_attempts.values())
        assert s.resources["grove"]["wild_food"] == 0
        assert db.verify("village").to_dict() == s.to_dict()


def test_reachable_food_travel_then_forage_preserves_finite_resources(village):
    db, clock = village
    tell(db)
    result = advance(db, clock, 170, "reach-and-forage")
    s = result.state
    assert s.travels["auto-nav:adel:0"]["due"] == 50
    assert s.travels["auto-nav:adel:0"]["status"] == "arrived"
    assert s.foraging_attempts["auto:adel:50"]["outcome"] == "collected"
    assert s.foraging_attempts["auto:adel:50"]["quantity"] == 1
    assert s.resources["grove"]["wild_food"] == 1
    assert s.resources["adel"]["food"] == 1
    assert s.resources["grove"]["wild_food"] + s.resources["adel"]["food"] == 2
    assert db.verify("village").to_dict() == s.to_dict()


def test_unlearned_second_hop_is_not_invented(village):
    db, clock = village
    tell(db, site="secret")
    learn_local_roads(db, clock)
    s = db.load("village")
    assert "grove-secret" not in s.navigation["adel"]["known_routes"]
    assert choose_food_route(s, "adel") is None
    out = advance(db, clock, 1, "not-omniscient")
    assert not any(t["npc_id"] == "adel" for t in out.state.travels.values())
    assert db.verify("village").to_dict() == out.state.to_dict()


def test_unknown_personal_stock_does_not_mean_zero(tmp_path):
    with SQLiteEventStore(tmp_path / "unknown-owned.sqlite") as db:
        make_world(db, omit_own=True)
        clock = TimeEngine(db)
        clock.open_session("village")
        tell(db)
        learn_local_roads(db, clock)
        assert choose_food_route(db.load("village"), "adel") is None
        result = advance(db, clock, 1, "unknown-food-no-trip")
        assert not any(t["npc_id"] == "adel" for t in result.state.travels.values())


@pytest.mark.parametrize(("hunger", "fatigue", "safety", "owned"), (
    (64, 5, 0, 0), (70, 76, 0, 0), (70, 5, 71, 0), (70, 5, 0, 1),
))
def test_physical_and_owned_food_limits(hunger, fatigue, safety, owned, tmp_path):
    with SQLiteEventStore(tmp_path / "limits.sqlite") as db:
        make_world(db, hunger=hunger, fatigue=fatigue, safety=safety,
                   own_food=owned)
        clock = TimeEngine(db)
        clock.open_session("village")
        tell(db)
        learn_local_roads(db, clock)
        assert choose_food_route(db.load("village"), "adel") is None


def test_manual_target_keeps_priority_over_food_rumor(village):
    db, clock = village
    tell(db)
    learn_local_roads(db, clock)
    NPCNavigationService(db, clock).target(
        "village", "adel", "hill", command_id="explicit-target",
        expected_revision=db.load("village").revision,
    )
    assert choose_food_route(db.load("village"), "adel") is None
    result = advance(db, clock, 1, "respect-target")
    assert result.state.travels["auto-nav:adel:0"]["route_id"] == "market-hill"


def test_local_visible_food_forage_wins_before_remote_journey(tmp_path):
    with SQLiteEventStore(tmp_path / "local-wins.sqlite") as db:
        make_world(db, market_stock=1, grove_stock=20)
        clock = TimeEngine(db)
        clock.open_session("village")
        tell(db)
        result = advance(db, clock, 1, "local-forage")
        assert not any(t["npc_id"] == "adel" for t in result.state.travels.values())
        assert result.state.actions["auto:adel:0"]["action"] == "forage"
        assert result.state.resources["market"]["wild_food"] == 1


def test_food_route_honors_existing_decision_cooldown(village):
    db, clock = village
    tell(db)
    learn_local_roads(db, clock)
    NPCService(db, clock).decide(
        "village", "adel", command_id="decision-at-zero",
        expected_revision=db.load("village").revision,
    )
    clock.advance("village", seconds=1, command_id="to-one",
                  expected_revision=db.load("village").revision)
    before = advance(db, clock, 58, "before-next-decision")
    assert before.state.time == 59
    assert not any(t["npc_id"] == "adel" for t in before.state.travels.values())
    after = advance(db, clock, 1, "decision-released")
    assert after.state.time == 60
    assert after.state.travels["auto-nav:adel:60"]["status"] == "traveling"


def test_event_budget_rollback_of_knowledge_route(village):
    db, clock = village
    tell(db)
    before = db.load("village").to_dict()
    n_before = db.db.execute(
        "SELECT count(*) FROM events WHERE world_id='village'"
    ).fetchone()[0]
    with pytest.raises(AdvanceLimitExceeded, match="event budget"):
        advance(db, clock, 1, "budget-exhausted", budget=2)
    assert db.load("village").to_dict() == before
    assert db.db.execute(
        "SELECT count(*) FROM events WHERE world_id='village'"
    ).fetchone()[0] == n_before
    assert db.verify("village").to_dict() == before


def test_snapshot_reopen_and_idempotent_command_preserve_destination(tmp_path):
    path = tmp_path / "reopen-food-navigation.sqlite"
    with SQLiteEventStore(path) as db:
        make_world(db)
        clock = TimeEngine(db)
        clock.open_session("village")
        tell(db)
        first = advance(db, clock, 50, "first-journey")
        db.snapshot("village")
        expected = first.state.to_dict()
    with SQLiteEventStore(path) as db:
        clock = TimeEngine(db)
        clock.open_session("village")
        assert db.load("village").to_dict() == expected
        assert db.verify("village").to_dict() == expected
        with pytest.raises(DuplicateCommand):
            advance(db, clock, 1, "first-journey")
        assert db.load("village").to_dict() == expected


def test_default_off_mode_is_identical_to_explicit_false(tmp_path):
    paths = [tmp_path / "off1.sqlite", tmp_path / "off2.sqlite"]
    final = []
    for path in paths:
        with SQLiteEventStore(path) as db:
            make_world(db)
            clock = TimeEngine(db)
            clock.open_session("village")
            tell(db)
            result = LivingWorldEngine(
                db, clock, navigation_enabled=True, knowledge_enabled=True,
                foraging_enabled=True,
                **({"food_navigation_enabled": False} if path == paths[1] else {}),
            ).advance("village", seconds=20, command_id="identical",
                      expected_revision=db.load("village").revision)
            final.append((
                result.state.to_dict(),
                [row[0] for row in db.db.execute(
                    "SELECT payload FROM events WHERE world_id='village' ORDER BY seq"
                )],
            ))
    assert final[0] == final[1]


def test_uninitialized_remote_stock_remains_unknown_after_arrival(tmp_path):
    # A rumor is not evidence that the site actually has finite stock.
    with SQLiteEventStore(tmp_path / "unknown-destination.sqlite") as db:
        make_world(db, grove_stock=None)
        clock = TimeEngine(db)
        clock.open_session("village")
        tell(db)
        result = advance(db, clock, 50, "reach-unknown-source")
        s = result.state
        assert s.entities["adel"]["location_id"] == "grove"
        assert s.npcs["adel"]["beliefs"]["food:grove"]["text"] == (
            "food-state:present; observed_at=0"
        )  # Only unverified hearsay; no fabricated direct 'empty' claim.
        assert s.npcs["adel"]["beliefs"]["food:grove"]["source"] == "basim"
        assert "wild_food" not in s.resources.get("grove", {})
        assert not any(v["npc_id"] == "adel" for v in s.foraging_attempts.values())
        assert db.verify("village").to_dict() == s.to_dict()


def test_private_danger_warning_blocks_food_journey(village):
    db, clock = village
    tell(db)
    s = db.load("village")
    danger_id = "danger-from-basim"
    db.append("village", "warn-risk", s.revision, [
        event("NPCInformationDelivered", {
            "npc_id": "adel", "delivery_id": danger_id,
            "key": "danger",
            "claim": {
                "text": "road danger", "source": "basim",
                "received_at": s.time, "confidence": 80,
            },
            "sender_id": "basim", "location_id": "market",
            "method": "message",
        }, actor="basim"),
        event("NPCBeliefReceived", {
            "npc_id": "adel", "key": "danger",
            "delivery_id": danger_id,
        }, actor="adel"),
    ], npc_authorized=True)
    learn_local_roads(db, clock)
    assert choose_food_route(db.load("village"), "adel") is None
    result = advance(db, clock, 1, "risk-prevents-food-travel")
    assert not any(t["npc_id"] == "adel" for t in result.state.travels.values())


def test_learned_two_hop_route_is_followed_without_hidden_map(tmp_path):
    from carlos_sim import NPCMovementService

    with SQLiteEventStore(tmp_path / "two-hop.sqlite") as db:
        make_world(db, grove_stock=0)
        clock = TimeEngine(db)
        clock.open_session("village")
        learn_local_roads(db, clock)
        move = NPCMovementService(db, clock)
        move.start("village", "adel", "market-grove", "learn-outward",
                   expected_revision=db.load("village").revision)
        clock.advance("village", seconds=50, command_id="reach-grove-manual",
                      expected_revision=db.load("village").revision)
        NPCNavigationService(db, clock).survey(
            "village", "adel", command_id="learn-grove-roads",
            expected_revision=db.load("village").revision)
        move.start("village", "adel", "market-grove", "learn-return",
                   expected_revision=db.load("village").revision)
        clock.advance("village", seconds=50, command_id="return-market-manual",
                      expected_revision=db.load("village").revision)
        state = db.load("village")
        assert state.entities["adel"]["location_id"] == "market"
        assert "grove-secret" in state.navigation["adel"]["known_routes"]

        tell(db, site="secret")
        plan = choose_food_route(db.load("village"), "adel")
        assert (plan.destination, plan.route_id, plan.total_seconds) == (
            "secret", "market-grove", 75
        )
        out = advance(db, clock, 75, "travel-two-hops")
        s = out.state
        assert s.entities["adel"]["location_id"] == "secret"
        assert s.travels["auto-nav:adel:100"]["route_id"] == "market-grove"
        assert s.travels["auto-nav:adel:150"]["route_id"] == "grove-secret"
        assert s.npcs["adel"]["beliefs"]["food:secret"]["text"] == (
            "food-state:empty; observed_at=175"
        )
        assert db.verify("village").to_dict() == s.to_dict()


def test_split_time_advance_preserves_physical_outcome(tmp_path):
    def scenario(path, split):
        with SQLiteEventStore(path) as db:
            make_world(db)
            clock = TimeEngine(db)
            clock.open_session("village")
            tell(db)
            if split:
                advance(db, clock, 50, "first-fifty")
                result = advance(db, clock, 120, "then-one-twenty")
            else:
                result = advance(db, clock, 170, "one-seventy")
            assert db.verify("village").to_dict() == result.state.to_dict()
            return result.state.to_dict()

    assert scenario(tmp_path / "split.sqlite", True) == scenario(
        tmp_path / "single.sqlite", False
    )
