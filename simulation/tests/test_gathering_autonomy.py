"""Phase 01-R: autonomous, local, hunger-limited food recovery with seven NPCs."""
from __future__ import annotations

import json
import pytest

from carlos_sim import (
    DomainEvent, SQLiteEventStore, TimeEngine, LivingWorldEngine,
    choose_gathering_intent, canonical_hash,
)
from carlos_sim.time_engine import SessionClosed, AdvanceLimitExceeded


NAMES = ("adel", "basim", "huda", "layla", "nora", "omar", "salma")


def ev(kind, payload, actor=None, at=0):
    return DomainEvent(kind, actor, "synthetic seven-person test site", at, payload)


def make_world(db, *, grove_stock=2, square_stock=0, omit_grove=False,
               omit_nora_food=False):
    """Four hungry, one satiated, one already stocked, one remote explorer."""
    db.create_world("r")
    events = [
        ev("LocationCreated", {"id": "grove", "name": "Forest grove"}),
        ev("LocationCreated", {"id": "square", "name": "Village square"}),
    ]
    for loc, stock in (("grove", grove_stock), ("square", square_stock)):
        if loc == "grove" and omit_grove:
            continue
        events.append(ev("ResourceChanged", {
            "owner_id": loc, "resource": "wild_food", "previous": None,
            "current": stock, "source": "initialization",
        }))
    for name in NAMES:
        location = "square" if name == "omar" else "grove"
        hunger = 30 if name == "huda" else 70
        owned_food = 2 if name == "layla" else 0
        events.extend([
            ev("EntityCreated", {"id": name, "name": name, "location_id": location,
                                 "controller": "npc"}),
            ev("NPCConfigured", {"npc_id": name, "role": "explorer",
                                 "needs": {"fatigue": 5, "hunger": hunger, "safety": 0},
                                 "goals": {"earn": 0, "explore": 95, "survive": 30}}),
        ])
        for resource, quantity in (("food", owned_food),
                                    ("labor_units", 0),
                                    ("investigation_attempts", 0)):
            if name == "nora" and resource == "food" and omit_nora_food:
                continue
            events.append(ev("ResourceChanged", {
                "owner_id": name, "resource": resource, "previous": None,
                "current": quantity, "source": "initialization",
            }))
    db.append("r", "bootstrap", 0, events, bootstrap=True)


@pytest.fixture
def village(tmp_path):
    with SQLiteEventStore(tmp_path / "seven.sqlite") as db:
        make_world(db)
        clock = TimeEngine(db)
        clock.open_session("r")
        yield db, clock


def advance(db, clock, *, gather=True, seconds=90, command="step", cap=1000,
            consumption=False):
    return LivingWorldEngine(
        db, clock, gathering_enabled=gather,
        consumption_enabled=consumption,
        max_events_per_advance=cap,
    ).advance("r", seconds=seconds, command_id=command,
              expected_revision=db.load("r").revision)


def test_seven_npcs_only_eligible_local_characters_compete_for_two_food(village):
    db, clock = village
    result = advance(db, clock)
    s = result.state
    assert s.time == 90
    assert len(s.npcs) == 7
    assert result.gathered_action_ids == ("auto:adel:0", "auto:basim:0")
    assert set(s.gatherings) == set(result.gathered_action_ids)
    assert s.resources["grove"]["wild_food"] == 0
    assert s.resources["square"]["wild_food"] == 0
    assert s.resources["adel"]["food"] == 1
    assert s.resources["basim"]["food"] == 1
    assert s.resources["nora"]["food"] == 0
    assert s.resources["salma"]["food"] == 0
    assert s.resources["huda"]["food"] == 0
    assert s.resources["layla"]["food"] == 2
    assert s.resources["omar"]["food"] == 0
    assert sum(s.resources[n]["food"] for n in NAMES) + s.resources["grove"]["wild_food"] == 4
    assert db.verify("r").to_dict() == s.to_dict()
    assert len(db.db.execute(
        "SELECT payload FROM events WHERE world_id='r' "
        "AND json_extract(payload,'$.event_type')='NPCFoodGathered'"
    ).fetchall()) == 2


def test_gathering_is_fully_opt_in(village):
    db, clock = village
    result = advance(db, clock, gather=False)
    assert result.gathered_action_ids == ()
    assert result.state.gatherings == {}
    assert result.state.resources["grove"]["wild_food"] == 2
    assert all(result.state.resources[x]["food"] == 0 for x in ("adel", "basim"))
    assert db.verify("r").to_dict() == result.state.to_dict()


def test_opt_in_and_opt_out_reject_non_boolean_option(village):
    db, clock = village
    for value in (None, 0, 1, "true", [], {}):
        with pytest.raises(ValueError, match="gathering_enabled"):
            LivingWorldEngine(db, clock, gathering_enabled=value)


def test_no_distant_stock_or_private_peer_inventory_used(tmp_path):
    with SQLiteEventStore(tmp_path / "remote.sqlite") as db:
        make_world(db, grove_stock=0, square_stock=100)
        clock = TimeEngine(db)
        clock.open_session("r")
        result = advance(db, clock)
        # The square has food but no character in the grove teleports it.
        assert all(record["site_id"] == "square" for record in result.state.gatherings.values())
        assert result.state.resources["grove"]["wild_food"] == 0
        assert result.state.resources["square"]["wild_food"] == 99
        assert result.state.resources["omar"]["food"] == 1
        assert all(result.state.resources[n]["food"] == 0
                   for n in ("adel", "basim", "nora", "salma"))


def test_no_autonomous_food_creation_when_deposit_unknown(tmp_path):
    with SQLiteEventStore(tmp_path / "unknown.sqlite") as db:
        make_world(db, omit_grove=True, square_stock=0)
        clock = TimeEngine(db)
        clock.open_session("r")
        result = advance(db, clock)
        assert result.gathered_action_ids == ()
        assert result.state.gatherings == {}
        assert result.state.resources.get("grove", {}).get("wild_food") is None


def test_no_autonomous_gathering_into_unknown_owned_inventory(tmp_path):
    with SQLiteEventStore(tmp_path / "missing-inventory.sqlite") as db:
        make_world(db, grove_stock=3, omit_nora_food=True)
        clock = TimeEngine(db)
        clock.open_session("r")
        result = advance(db, clock)
        assert "auto:nora:0" not in result.state.gatherings
        assert result.state.resources["nora"].get("food") is None
        assert len(result.state.gatherings) == 3
        assert result.state.resources["grove"]["wild_food"] == 0


def test_autonomous_policy_only_reads_own_need_and_local_deposit(village):
    db, clock = village
    from carlos_sim import NPCService, NPCActionService
    # Construct one real completed investigation at t=90, without gathering.
    npc = NPCService(db, clock)
    npc.decide("r", "nora", command_id="manual-plan",
               expected_revision=db.load("r").revision)
    actions = NPCActionService(db, clock)
    started = actions.start("r", "nora", "nora-search",
                            expected_revision=db.load("r").revision)
    finished = clock.advance("r", seconds=90, command_id="complete",
                             expected_revision=started.state.revision).state
    choice = choose_gathering_intent(finished, "nora-search")
    assert choice is not None and choice.site_id == "grove"
    # Mutating a *remote site* without advancing time cannot affect local choice.
    changed = finished.to_dict()
    changed["resources"]["square"]["wild_food"] = 200
    from carlos_sim import WorldState
    changed = WorldState.from_dict(changed)
    assert choose_gathering_intent(changed, "nora-search") == choice
    # Another actor's private inventory changes are also irrelevant.
    changed2 = finished.to_dict()
    changed2["resources"]["basim"]["food"] = 100
    assert choose_gathering_intent(WorldState.from_dict(changed2), "nora-search") == choice


def test_full_batch_rollback_when_event_budget_exhausted(village):
    db, clock = village
    before = db.load("r").to_dict()
    with pytest.raises(AdvanceLimitExceeded):
        advance(db, clock, cap=23, command="too-many")
    assert db.load("r").to_dict() == before
    assert db.db.execute("SELECT count(*) FROM commands WHERE command_id='too-many'").fetchone()[0] == 0


def test_paused_session_cannot_autogather(village):
    db, clock = village
    before = db.load("r")
    clock.close_session("r")
    with pytest.raises(SessionClosed):
        advance(db, clock)
    assert db.load("r").to_dict() == before.to_dict()


def test_split_advance_matches_one_step_physical_outcomes(tmp_path):
    results = []
    for suffix, steps in (("full", (90,)), ("split", (35, 55))):
        with SQLiteEventStore(tmp_path / f"{suffix}.sqlite") as db:
            make_world(db)
            clock = TimeEngine(db)
            clock.open_session("r")
            for index, count in enumerate(steps):
                advance(db, clock, seconds=count, command=f"{suffix}-{index}")
            s = db.verify("r")
            results.append({
                "time": s.time, "gatherings": s.to_dict()["gatherings"],
                "resources": s.to_dict()["resources"],
                "npcs_hunger": {k: v["needs"]["hunger"] for k,v in s.npcs.items()},
            })
    assert results[0] == results[1]


def test_seven_character_run_is_repeatable(tmp_path):
    hashes = []
    for num in range(2):
        with SQLiteEventStore(tmp_path / f"repeat-{num}.sqlite") as db:
            make_world(db)
            clock=TimeEngine(db)
            clock.open_session("r")
            result=advance(db, clock)
            hashes.append(canonical_hash(result.state.to_dict()))
            assert db.verify("r").to_dict() == result.state.to_dict()
    assert hashes[0] == hashes[1]


def test_completed_search_does_not_gather_twice_after_time_moves(village):
    db, clock = village
    first = advance(db, clock, seconds=90)
    assert len(first.state.gatherings) == 2
    later = advance(db, clock, seconds=1, command="later")
    assert len(later.state.gatherings) == 2
    assert later.gathered_action_ids == ()
    assert db.verify("r").to_dict() == later.state.to_dict()


def test_gathering_and_autonomous_eating_can_chain_without_conjuring_food(village):
    db, clock = village
    result = advance(db, clock, consumption=True)
    assert result.gathered_action_ids == ("auto:adel:0", "auto:basim:0")
    # Collection happens just after investigation ends; the eating pass
    # later in the same tick may consume exactly the food just gathered.
    meals = result.state.consumptions
    # Layla was already carrying food at t=0, so autonomous eating also
    # creates her own independent meals. The two newly gathered portions
    # must be traceable to their own collectors, not to a fixed total.
    assert len(meals) == 4
    for npc in ("adel", "basim"):
        assert result.state.resources[npc]["food"] == 0
        assert any(m["npc_id"] == npc for m in meals.values())
    assert result.state.resources["grove"]["wild_food"] == 0
    assert db.verify("r").to_dict() == result.state.to_dict()
