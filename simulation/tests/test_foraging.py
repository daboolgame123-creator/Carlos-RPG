"""Phase 01-S: self-initiated local forage with finite outcomes and replay."""
from __future__ import annotations

import pytest
from carlos_sim import (
    DomainEvent, WorldState, SQLiteEventStore, TimeEngine, LivingWorldEngine,
    NPCService, NPCActionService, choose_action, canonical_hash,
)
from carlos_sim.store import InvalidEvent, RevisionConflict, UnsupportedVersion
from carlos_sim.time_engine import SessionClosed, AdvanceLimitExceeded
from test_gathering_autonomy import make_world, NAMES


def ev(kind, data, actor=None, time=0):
    return DomainEvent(kind, actor, "01-S isolated test", time, data)


@pytest.fixture
def village(tmp_path):
    with SQLiteEventStore(tmp_path / "01s.sqlite") as db:
        make_world(db)  # seven characters; two natural units at grove
        clock = TimeEngine(db)
        clock.open_session("r")
        yield db, clock


def advance(db, clock, *, seconds=120, command="go", forage=True,
            gather=False, consume=False, survival=False, budget=1000):
    return LivingWorldEngine(
        db, clock, foraging_enabled=forage, gathering_enabled=gather,
        consumption_enabled=consume, survival_enabled=survival,
        max_events_per_advance=budget
    ).advance("r", seconds=seconds, command_id=command,
              expected_revision=db.load("r").revision)


def configure_need(db, who, key, value):
    current = db.load("r")
    before = current.npcs[who]["needs"][key]
    return db.append("r", "need:" + who + ":" + key, current.revision, [
        ev("NPCNeedChanged", {"npc_id": who, "need": key,
                              "previous": before, "current": value}, actor=who)
    ], npc_authorized=True)


def test_seven_people_choose_reasoned_forage_and_compete_for_two_units(village):
    db, clock = village
    outcome = advance(db, clock)
    s = outcome.state
    assert s.time == 120 and len(s.npcs) == 7
    expected = {"auto:adel:0", "auto:basim:0", "auto:nora:0", "auto:salma:0"}
    assert set(s.foraging_attempts) == expected
    assert {a["outcome"] for a in s.foraging_attempts.values()} == {"collected", "depleted"}
    assert sum(a["quantity"] for a in s.foraging_attempts.values()) == 2
    assert sum(a["outcome"] == "depleted" for a in s.foraging_attempts.values()) == 2
    assert s.foraging_attempts["auto:adel:0"]["outcome"] == "collected"
    assert s.foraging_attempts["auto:basim:0"]["outcome"] == "collected"
    assert s.foraging_attempts["auto:nora:0"]["outcome"] == "depleted"
    assert s.foraging_attempts["auto:salma:0"]["outcome"] == "depleted"
    assert s.resources["grove"]["wild_food"] == 0
    assert s.resources["adel"]["food"] == s.resources["basim"]["food"] == 1
    assert s.resources["nora"]["food"] == s.resources["salma"]["food"] == 0
    assert s.resources["layla"]["food"] == 2
    assert s.resources["omar"]["food"] == 0
    assert s.resources["huda"]["food"] == 0
    assert sum(s.resources[n]["food"] for n in NAMES) + s.resources["grove"]["wild_food"] == 4
    assert s.actions["auto:adel:0"]["due"] == 120
    assert s.actions["auto:adel:0"]["result"]["needs"]["fatigue"] == (5, 17)
    assert s.actions["auto:adel:0"]["result"]["needs"]["hunger"] == (70, 75)
    assert s.npcs["adel"]["last_decision"]["action"] == "forage"
    assert "local-forage-v1" in s.npcs["adel"]["last_decision"]["reason"]
    assert db.verify("r").to_dict() == s.to_dict()


def test_forage_is_opt_in_and_legacy_behavior_stays_identical(village):
    db, clock = village
    old = advance(db, clock, forage=False)
    assert old.state.foraging_attempts == {}
    assert old.state.resources["grove"]["wild_food"] == 2
    assert old.state.actions["auto:adel:0"]["action"] == "investigate"
    assert old.state.npcs["adel"]["last_decision"]["action"] == "investigate"
    assert db.verify("r").to_dict() == old.state.to_dict()


def test_forge_policy_requires_correct_boolean_flag(village):
    db, clock = village
    for value in (1, 0, "true", [], None, {}):
        with pytest.raises(ValueError, match="foraging_enabled"):
            LivingWorldEngine(db, clock, foraging_enabled=value)
        with pytest.raises(ValueError, match="foraging_enabled"):
            NPCService(db, clock, foraging_enabled=value)


def test_hunger_critical_with_survival_mode_still_searches_known_food(village):
    db, clock = village
    configure_need(db, "nora", "hunger", 95)
    choice = choose_action(db.load("r"), "nora", survival_enabled=True,
                           foraging_enabled=True)
    assert choice.action == "forage"
    result = advance(db, clock, survival=True)
    assert result.state.foraging_attempts["auto:nora:0"]["outcome"] == "depleted"
    assert db.verify("r").to_dict() == result.state.to_dict()


def test_tired_character_does_not_forget_physical_limits(village):
    db, clock = village
    configure_need(db, "nora", "fatigue", 95)
    choice = choose_action(db.load("r"), "nora", foraging_enabled=True)
    assert choice.action != "forage"
    result = advance(db, clock)
    assert "auto:nora:0" not in result.state.foraging_attempts


def test_frightened_character_does_not_forage_without_safety(village):
    db, clock = village
    configure_need(db, "nora", "safety", 90)
    assert choose_action(db.load("r"), "nora", foraging_enabled=True).action != "forage"
    outcome = advance(db, clock)
    assert "auto:nora:0" not in outcome.state.foraging_attempts


def test_person_with_owned_food_does_not_seek_new_food(village):
    db, clock = village
    state = db.load("r")
    assert choose_action(state, "layla", foraging_enabled=True).action != "forage"
    result = advance(db, clock)
    assert "auto:layla:0" not in result.state.foraging_attempts


def test_unknown_personal_stock_cannot_be_treated_as_zero(tmp_path):
    with SQLiteEventStore(tmp_path / "missing-personal.sqlite") as db:
        make_world(db, omit_nora_food=True)
        clock = TimeEngine(db); clock.open_session("r")
        assert choose_action(db.load("r"), "nora", foraging_enabled=True).action != "forage"
        result = advance(db, clock)
        assert "auto:nora:0" not in result.state.foraging_attempts
        assert result.state.resources["nora"].get("food") is None


def test_unknown_natural_stock_is_not_magic_food(tmp_path):
    with SQLiteEventStore(tmp_path / "unknown-natural.sqlite") as db:
        make_world(db, omit_grove=True)
        clock = TimeEngine(db); clock.open_session("r")
        for who in ("adel", "basim", "nora", "salma"):
            assert choose_action(db.load("r"), who, foraging_enabled=True).action != "forage"
        result = advance(db, clock)
        assert result.state.foraging_attempts == {}
        assert result.state.resources.get("grove", {}).get("wild_food") is None


def test_remote_abundance_does_not_make_local_actor_forage(tmp_path):
    with SQLiteEventStore(tmp_path / "remote.sqlite") as db:
        make_world(db, grove_stock=0, square_stock=100)
        clock = TimeEngine(db); clock.open_session("r")
        for who in ("adel", "basim", "nora", "salma"):
            assert choose_action(db.load("r"), who, foraging_enabled=True).action != "forage"
        result = advance(db, clock)
        assert all(record["site_id"] == "square" for record in result.state.foraging_attempts.values())
        assert result.state.resources["grove"]["wild_food"] == 0
        assert result.state.resources["square"]["wild_food"] == 99
        assert result.state.resources["omar"]["food"] == 1


def test_distant_inventory_change_does_not_affect_local_foraging_choice(village):
    db, clock = village
    first = choose_action(db.load("r"), "nora", foraging_enabled=True)
    d = db.load("r").to_dict()
    d["resources"]["square"]["wild_food"] = 500
    d["resources"]["layla"]["food"] = 20
    other = choose_action(WorldState.from_dict(d), "nora", foraging_enabled=True)
    assert first == other


def test_trusted_manual_decision_and_clock_resolve_forage_without_living_world(village):
    db, clock = village
    npc = NPCService(db, clock, foraging_enabled=True)
    proposed = npc.decide("r", "nora", command_id="decide", expected_revision=db.load("r").revision)
    assert proposed.action == "forage"
    start = NPCActionService(db, clock).start("r", "nora", "manual-forage",
                                               expected_revision=db.load("r").revision)
    assert start.action == "forage" and start.due == 120
    before = db.load("r")
    assert before.resources["grove"]["wild_food"] == 2
    end = clock.advance("r", seconds=120, command_id="clock",
                        expected_revision=before.revision).state
    assert end.foraging_attempts["manual-forage"]["outcome"] == "collected"
    assert end.resources["grove"]["wild_food"] == 1
    assert end.resources["nora"]["food"] == 1
    assert db.verify("r").to_dict() == end.to_dict()


def test_cannot_forge_forage_decision_without_trusted_capability(village):
    db, clock = village
    before = db.load("r")
    choice = choose_action(before, "nora", foraging_enabled=True)
    forged = ev("NPCDecisionRecorded", {
        "npc_id": "nora", "action": "forage", "score": choice.score,
        "reason": choice.reason, "next_decision_at": 60,
        "policy": "local-forage-v1",
    }, actor="nora")
    with pytest.raises(InvalidEvent, match="foraging decisions require trusted"):
        db.append("r", "fake", before.revision, [forged], npc_authorized=True)
    assert db.load("r").to_dict() == before.to_dict()


def test_cannot_forge_reason_or_undocumented_policy(village):
    db, clock = village
    before = db.load("r")
    choice = choose_action(before, "nora", foraging_enabled=True)
    data = {"npc_id": "nora", "action": "forage", "score": choice.score,
            "reason": choice.reason, "next_decision_at": 60,
            "policy": "local-forage-v1"}
    for altered in ({"score": -99}, {"reason": "I already know where all food is"},
                    {"policy": "secret-v9"}, {"policy": None}, {"unknown": "extra"}):
        invalid = {**data, **altered}
        before2 = db.load("r")
        with pytest.raises(InvalidEvent):
            db.append("r", "fake:" + str(altered), before2.revision,
                      [ev("NPCDecisionRecorded", invalid, actor="nora")],
                      npc_authorized=True, action_authorized=True)
        assert db.load("r").to_dict() == before2.to_dict()


def test_unstarted_forage_not_free_and_costs_time(village):
    db, clock = village
    first = advance(db, clock, seconds=50)
    assert first.state.foraging_attempts == {}
    assert first.state.resources["grove"]["wild_food"] == 2
    assert any(a["action"] == "forage" and a["status"] == "running"
               for a in first.state.actions.values())
    assert db.verify("r").to_dict() == first.state.to_dict()


def test_session_closed_rejects_forage_and_time(village):
    db, clock = village
    before = db.load("r")
    clock.close_session("r")
    with pytest.raises(SessionClosed):
        advance(db, clock)
    assert db.load("r").to_dict() == before.to_dict()


def test_atomic_rollback_on_small_event_budget(village):
    db, clock = village
    before = db.load("r")
    with pytest.raises(AdvanceLimitExceeded):
        advance(db, clock, budget=12, command="abort")
    assert db.load("r").to_dict() == before.to_dict()
    assert db.db.execute(
        "SELECT count(*) FROM commands WHERE command_id='abort'"
    ).fetchone()[0] == 0


def test_split_and_single_time_advances_have_same_physical_outcomes(tmp_path):
    results = []
    for name, timeline in (("single", (120,)), ("split", (40, 80))):
        with SQLiteEventStore(tmp_path / f"{name}.sqlite") as db:
            make_world(db)
            clock = TimeEngine(db); clock.open_session("r")
            for i, duration in enumerate(timeline):
                advance(db, clock, seconds=duration, command=name + str(i))
            state = db.verify("r")
            results.append({"attempts": state.to_dict()["foraging_attempts"],
                            "resources": state.to_dict()["resources"],
                            "hunger": {k: v["needs"]["hunger"] for k,v in state.npcs.items()},
                            "time": state.time})
    assert results[0] == results[1]


def test_forage_continues_after_toggling_feature_off_mid_action(village):
    db, clock = village
    first = advance(db, clock, seconds=1, command="start", forage=True)
    after = advance(db, clock, seconds=119, command="finish", forage=False)
    assert len(after.state.foraging_attempts) == 4
    assert after.state.resources["grove"]["wild_food"] == 0
    assert db.verify("r").to_dict() == after.state.to_dict()


def test_snapshot_restart_replay_and_negative_snapshot_validation(tmp_path):
    path = tmp_path / "restart.sqlite"
    with SQLiteEventStore(path) as db:
        make_world(db)
        clock = TimeEngine(db); clock.open_session("r")
        outcome = advance(db, clock)
        db.snapshot("r")
        expected = outcome.state.to_dict()
    with SQLiteEventStore(path) as restored:
        assert restored.load("r").to_dict() == expected
        assert restored.load("r", use_snapshot=False).to_dict() == expected
        assert restored.verify("r").to_dict() == expected
    forged = expected.copy()
    forged["foraging_attempts"] = {k: dict(v) for k,v in expected["foraging_attempts"].items()}
    forged["foraging_attempts"]["auto:adel:0"]["food_after"] = 10000
    with pytest.raises(ValueError, match="conservation"):
        WorldState.from_dict(forged)


def test_rules_and_schema_reject_an_old_saved_world(tmp_path):
    path = tmp_path / "version.sqlite"
    with SQLiteEventStore(path) as db:
        make_world(db)
        db.db.execute("UPDATE worlds SET schema_version=12,rules_version=16 WHERE id='r'")
        with pytest.raises(UnsupportedVersion):
            db.load("r")
    # No automatic destructive migration or rewrite was performed.
    with SQLiteEventStore(path) as db:
        row = db.db.execute("SELECT schema_version,rules_version FROM worlds WHERE id='r'").fetchone()
        assert row == (12, 16)


def test_deterministic_repeatability_with_seven_characters(tmp_path):
    hashes = []
    for i in range(2):
        with SQLiteEventStore(tmp_path / f"same-{i}.sqlite") as db:
            make_world(db)
            clock = TimeEngine(db); clock.open_session("r")
            result = advance(db, clock)
            hashes.append(canonical_hash(result.state.to_dict()))
            assert db.verify("r").to_dict() == result.state.to_dict()
    assert hashes[0] == hashes[1]


def test_forage_and_eating_are_distinct_and_replayable(village):
    db, clock = village
    outcome = advance(db, clock, consume=True)
    s = outcome.state
    assert sum(a["quantity"] for a in s.foraging_attempts.values()) == 2
    assert any(c["npc_id"] == "adel" for c in s.consumptions.values())
    assert any(c["npc_id"] == "basim" for c in s.consumptions.values())
    assert s.resources["adel"]["food"] == s.resources["basim"]["food"] == 0
    assert db.verify("r").to_dict() == s.to_dict()


def test_explicit_interruption_stops_before_forage_completion(village):
    db, clock = village
    schedule = clock.schedule_signal("r", "player-interrupt", due=60,
                                     interrupt=True, expected_revision=db.load("r").revision)
    result = advance(db, clock, seconds=120)
    assert result.interrupted and result.state.time == 60
    assert result.state.foraging_attempts == {}
    resumed = advance(db, clock, seconds=60, command="resume")
    assert not resumed.interrupted and resumed.state.time == 120
    assert len(resumed.state.foraging_attempts) == 4
    assert db.verify("r").to_dict() == resumed.state.to_dict()
