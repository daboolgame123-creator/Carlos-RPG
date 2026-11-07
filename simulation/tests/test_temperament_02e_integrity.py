"""02-E integration: bounded real memory, replay/restart and trust boundaries."""
from __future__ import annotations

import pytest

from carlos_sim import (
    DomainEvent, SQLiteEventStore, TimeEngine, NPCService, NPCActionService,
    LivingWorldEngine, WorldState, choose_action,
)
from carlos_sim.store import InvalidEvent, RevisionConflict
from carlos_sim.backup import create_backup_bundle, verify_backup_bundle, restore_backup_bundle
from test_temperament_02e import setup, ev, decide, step, rev

SOURCE_SHA = "65c567e9f4c94672b3f29e2c7ddad3e448cae224"


def test_private_memories_remember_exact_latest_eight_real_actions(tmp_path):
    with SQLiteEventStore(tmp_path / "memory.sqlite") as db:
        setup(db, members=("basim", "nora"))
        clock = TimeEngine(db)
        clock.open_session("test")
        action = NPCActionService(db, clock)
        for k in range(10):
            selected = decide(db, clock, "basim", f"decide-{k}")
            started = action.start("test", "basim", f"performed-{k}",
                                   expected_revision=rev(db))
            done = step(db, clock, started.due - db.load("test").time, f"finish-{k}")
            memory = done.npc_temperaments["basim"]["memories"]
            assert len(memory) == min(k + 1, 8)
            assert memory[-1]["action_id"] == f"performed-{k}"
            assert memory[-1]["action"] == selected.action
            assert len(set(x["action_id"] for x in memory)) == len(memory)
            assert db.verify("test").to_dict() == done.to_dict()
        end = db.load("test")
        assert [x["action_id"] for x in end.npc_temperaments["basim"]["memories"]] == [
            f"performed-{k}" for k in range(2, 10)
        ]
        damaged = end.to_dict()
        damaged["npc_temperaments"]["basim"]["memories"].pop(1)
        with pytest.raises(ValueError, match="latest real"):
            WorldState.from_dict(damaged)
        changed = end.to_dict()
        changed["npc_temperaments"]["basim"]["memories"].reverse()
        with pytest.raises(ValueError):
            WorldState.from_dict(changed)


def test_memory_survives_snapshot_restore_and_matches_event_replay(tmp_path):
    original = tmp_path / "personality.sqlite"
    with SQLiteEventStore(original) as db:
        setup(db, members=("basim", "nora"))
        clock = TimeEngine(db)
        clock.open_session("test")
        decide(db, clock, "nora", "nora-decide")
        act = NPCActionService(db, clock).start(
            "test", "nora", "observed-action", expected_revision=rev(db))
        pending = db.load("test").to_dict()
        db.snapshot("test")
        assert db.verify("test").to_dict() == pending
    with SQLiteEventStore(original) as db:
        clock = TimeEngine(db)
        clock.open_session("test")
        assert db.load("test").to_dict() == pending
        done = step(db, clock, act.due, "completed-after-reopen")
        assert len(done.npc_temperaments["nora"]["memories"]) == 1
        assert db.verify("test").to_dict() == done.to_dict()
        bundle = tmp_path / "bundle"
        manifest = create_backup_bundle(db, "test", bundle, code_commit=SOURCE_SHA)
        assert (manifest["schema"], manifest["rules"]) == (36, 48)
        assert verify_backup_bundle(bundle) == manifest
        saved = done.to_dict()
    restored_path = tmp_path / "restored.sqlite"
    restore_backup_bundle(bundle, restored_path)
    with SQLiteEventStore(restored_path) as db:
        assert db.db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert db.verify("test").to_dict() == saved
        assert db.load("test").npc_temperaments["nora"]["memories"][0]["action_id"] == "observed-action"


def test_seven_autonomous_npcs_keep_history_without_forced_trait_changes(tmp_path):
    with SQLiteEventStore(tmp_path / "living.sqlite") as db:
        setup(db)
        clock = TimeEngine(db)
        clock.open_session("test")
        engine = LivingWorldEngine(db, clock)
        result = engine.advance("test", seconds=220, command_id="living-round",
                                expected_revision=rev(db))
        assert len(result.state.npcs) == 7
        assert set(result.state.npc_temperaments) == {"basim", "nora"}
        memory_b = result.state.npc_temperaments["basim"]["memories"]
        memory_n = result.state.npc_temperaments["nora"]["memories"]
        assert memory_b and memory_n
        assert all(m["action_id"] in result.state.actions for m in (*memory_b, *memory_n))
        assert len(result.state.npc_temperaments) == 2
        assert db.verify("test").to_dict() == result.state.to_dict()


def test_bootstrap_flags_and_atomic_invalid_followup_do_not_insert_traits(tmp_path):
    with SQLiteEventStore(tmp_path / "atomic.sqlite") as db:
        setup(db, configured=False, members=("basim", "nora"))
        baseline = db.load("test")
        valid = ev("NPCTemperamentConfigured", {
            "npc_id": "basim", "traits": {
                "ambition": 80, "curiosity": 20, "caution": 50, "discipline": 50
            },
        })
        invalid = ev("NPCTemperamentConfigured", {
            "npc_id": "basim", "traits": {
                "ambition": 101, "curiosity": 20, "caution": 50, "discipline": 50
            },
        })
        with pytest.raises(InvalidEvent):
            db.append("test", "batch-fail", baseline.revision, [valid, invalid],
                      bootstrap=True)
        assert db.load("test").to_dict() == baseline.to_dict()
        assert db.db.execute(
            "SELECT COUNT(*) FROM commands WHERE command_id='batch-fail'"
        ).fetchone()[0] == 0


def test_forged_decision_ignoring_memory_adjustment_fails(tmp_path):
    with SQLiteEventStore(tmp_path / "replay-guard.sqlite") as db:
        setup(db, members=("basim",), traits={"basim": {
            "ambition": 100, "curiosity": 0, "caution": 100, "discipline": 100
        }})
        clock = TimeEngine(db)
        clock.open_session("test")
        decide(db, clock, "basim", "first")
        result = NPCActionService(db, clock).start(
            "test", "basim", "genuine", expected_revision=rev(db))
        step(db, clock, result.due, "action-due")
        current = db.load("test")
        answer = choose_action(current, "basim")
        assert "remembered_last=work" in answer.reason
        forged = ev("NPCDecisionRecorded", {
            "npc_id": "basim", "action": answer.action,
            "score": answer.score + 12, "reason": answer.reason.replace(
                "remembered_last=work", "remembered_last=none"),
            "next_decision_at": current.time + 60,
        }, who="basim", at=current.time)
        with pytest.raises(InvalidEvent):
            db.append("test", "fake-amnesia", current.revision, [forged],
                      npc_authorized=True)
        assert db.load("test").to_dict() == current.to_dict()


def test_real_work_memory_changes_followup_choice_with_same_current_needs(tmp_path):
    from carlos_sim.npc import _score_choice
    neutral = {"ambition": 50, "curiosity": 50,
               "caution": 50, "discipline": 50}
    with SQLiteEventStore(tmp_path / "experienced.sqlite") as db:
        setup(db, members=("basim",), traits={"basim": neutral}, fatigue=0, earn=41, explore=46)
        clock = TimeEngine(db)
        clock.open_session("test")
        first = decide(db, clock, "basim", "first")
        assert first.action == "work"
        started = NPCActionService(db, clock).start(
            "test", "basim", "actual-work", expected_revision=rev(db))
        completed = step(db, clock, started.due, "finish-work")
        has_memory = choose_action(completed, "basim")
        no_memory_hypothetical = _score_choice(
            completed.npcs["basim"], "basim",
            temperament={"traits": neutral, "memories": []})
        # Exactly the same present needs and goals; the counterfactual differs
        # only by a memory which the normal engine cannot erase.
        assert no_memory_hypothetical.action == "work"
        assert has_memory.action == "investigate"
        assert "remembered_last=work" in has_memory.reason
        assert db.verify("test").to_dict() == completed.to_dict()
