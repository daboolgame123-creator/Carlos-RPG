"""02-B adversarial persistence, replay, and production authorization probes."""
from __future__ import annotations

import pytest

from carlos_sim import (
    DomainEvent, SQLiteEventStore, TimeEngine, NPCProductionService,
    WorldState, apply_event,
)
from carlos_sim.domain import SCHEMA_VERSION, RULES_VERSION
from carlos_sim.store import InvalidEvent, RevisionConflict, DuplicateCommand
from carlos_sim.time_engine import SessionClosed, AdvanceLimitExceeded
from carlos_sim.backup import (
    create_backup_bundle, verify_backup_bundle, restore_backup_bundle,
)
from test_production_02b import ev, setup, start, advance, RECIPE

COMMIT = "fdf6162c65d6947507d1b4e4516c17d851873c29"


def test_replay_and_snapshot_after_reopen_during_work(tmp_path):
    path = tmp_path / "continuity.sqlite"
    with SQLiteEventStore(path) as db:
        setup(db)
        clock = TimeEngine(db)
        clock.open_session("test")
        start(db, clock)
        state = db.load("test").to_dict()
        db.snapshot("test")
        assert db.verify("test").to_dict() == state
    with SQLiteEventStore(path) as db:
        clock = TimeEngine(db)
        clock.open_session("test")
        assert db.verify("test").to_dict() == state
        done = advance(db, clock, 90, "complete-on-restart")
        assert done.resources["bakery"]["bread"] == 1
        assert done.production_jobs["batch"]["finished_at"] == 90
        assert db.verify("test").to_dict() == done.to_dict()


def test_isolated_backup_restore_preserves_once_only_finished_product(tmp_path):
    path = tmp_path / "source.sqlite"
    with SQLiteEventStore(path) as db:
        setup(db)
        clock = TimeEngine(db)
        clock.open_session("test")
        start(db, clock)
        result = advance(db, clock, 90, "finish")
        bundle = tmp_path / "backup"
        manifest = create_backup_bundle(db, "test", bundle, code_commit=COMMIT)
        assert manifest["schema"] == 18 and manifest["rules"] == 25
        assert verify_backup_bundle(bundle) == manifest
        frozen = result.to_dict()
    restored = tmp_path / "restore.sqlite"
    restore_backup_bundle(bundle, restored)
    with SQLiteEventStore(restored) as db:
        assert db.db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert db.verify("test").to_dict() == frozen
        clock = TimeEngine(db)
        clock.open_session("test")
        after = advance(db, clock, 500, "extra-time")
        assert after.resources["bakery"]["bread"] == 1
        assert after.resources["bakery"]["grain"] == 4
        assert after.production_jobs["batch"]["status"] == "completed"


def test_batch_rollback_keeps_materials_and_slot_if_later_event_invalid(tmp_path):
    with SQLiteEventStore(tmp_path / "atomic.sqlite") as db:
        setup(db)
        clock = TimeEngine(db)
        clock.open_session("test")
        before = db.load("test").to_dict()
        a = ev("ProductionStarted", {
            "id": "a", "recipe_id": "bread", "npc_id": "basim",
        }, actor="basim")
        bad = ev("ProductionStarted", {
            "id": "b", "recipe_id": "bread", "npc_id": "basim",
        }, actor="basim")
        with pytest.raises(InvalidEvent):
            db.append("test", "atomic", before["revision"], [a, bad],
                      production_authorized=True)
        assert db.load("test").to_dict() == before
        assert db.db.execute(
            "SELECT count(*) FROM commands WHERE command_id='atomic'"
        ).fetchone()[0] == 0


def test_untrusted_capability_paused_session_duplicate_and_stale(tmp_path):
    with SQLiteEventStore(tmp_path / "capabilities.sqlite") as db:
        setup(db)
        clock = TimeEngine(db)
        clock.open_session("test")
        before = db.load("test")
        event = ev("ProductionStarted", {
            "id": "not-trusted", "npc_id": "basim", "recipe_id": "bread",
        }, actor="basim")
        with pytest.raises(InvalidEvent, match="trusted"):
            db.append("test", "forged", before.revision, [event])
        with pytest.raises(ValueError, match="trusted"):
            apply_event(before, event)
        clock.close_session("test")
        with pytest.raises(InvalidEvent, match="active"):
            db.append("test", "closed", before.revision, [event],
                      production_authorized=True)
        with pytest.raises(SessionClosed):
            start(db, clock)
        assert db.load("test").to_dict() == before.to_dict()
        clock.open_session("test")
        start(db, clock, "basim", "once")
        committed = db.load("test").to_dict()
        with pytest.raises(DuplicateCommand):
            start(db, clock, "basim", "once")
        with pytest.raises(RevisionConflict):
            NPCProductionService(db, clock).start(
                "test", "nora", "bread", "stale",
                expected_revision=before.revision)
        assert db.load("test").to_dict() == committed


def test_clock_budget_abort_and_paused_clock_no_work_completion(tmp_path):
    with SQLiteEventStore(tmp_path / "budget.sqlite") as db:
        setup(db)
        clock = TimeEngine(db)
        clock.open_session("test")
        start(db, clock)
        s = db.load("test").to_dict()
        cap = TimeEngine(db, max_events_per_advance=1)
        with pytest.raises(AdvanceLimitExceeded):
            cap.advance("test", seconds=90, command_id="overbudget",
                        expected_revision=s["revision"])
        assert db.load("test").to_dict() == s
        clock.close_session("test")
        with pytest.raises(SessionClosed):
            advance(db, clock, 90, "closed")
        assert db.load("test").to_dict() == s
        clock.open_session("test")
        assert advance(db, clock, 90, "completed").resources["bakery"]["bread"] == 1


def test_corrupted_recipe_job_or_schedule_snapshot_is_rejected(tmp_path):
    with SQLiteEventStore(tmp_path / "snapshot.sqlite") as db:
        setup(db)
        clock = TimeEngine(db)
        clock.open_session("test")
        start(db, clock)
        initial = db.load("test")
        for case in ("missing", "recipe", "tool", "job", "signal", "worker"):
            damaged = initial.to_dict()
            if case == "missing":
                del damaged["production_jobs"]
            elif case == "recipe":
                damaged["production_recipes"]["bread"]["input_amount"] = 0
            elif case == "tool":
                damaged["resources"]["bakery"]["oven"] = 0
            elif case == "job":
                damaged["production_jobs"]["batch"]["input_after"] = 999
            elif case == "signal":
                damaged["scheduled"]["production:batch"]["payload"]["__production_job"] = "other"
            else:
                damaged["npcs"]["basim"]["role"] = "guard"
            with pytest.raises(ValueError):
                WorldState.from_dict(damaged)
        assert db.load("test").to_dict() == initial.to_dict()


def test_split_time_vs_lumped_time_same_product_and_job_ledger(tmp_path):
    results = []
    for name, waits in (("one", (90,)), ("split", (20, 30, 40))):
        with SQLiteEventStore(tmp_path / f"{name}.sqlite") as db:
            setup(db)
            clock = TimeEngine(db)
            clock.open_session("test")
            start(db, clock)
            for i, value in enumerate(waits):
                advance(db, clock, value, f"{name}-{i}")
            state = db.verify("test")
            results.append({
                "resources": state.to_dict()["resources"],
                "jobs": state.to_dict()["production_jobs"],
                "time": state.time,
                "scheduled": state.to_dict()["scheduled"],
            })
    assert results[0] == results[1]


def test_missing_bootstrap_or_invalid_recipe_cannot_mint_tools_or_goods(tmp_path):
    for n, field in enumerate(("input_amount", "output_amount",
                               "duration_seconds", "role", "site_id")):
        with SQLiteEventStore(tmp_path / f"recipe-{n}.sqlite") as db:
            db.create_world("test")
            old = db.load("test").to_dict()
            invalid = dict(RECIPE)
            invalid[field] = (False if field in (
                "input_amount", "output_amount", "duration_seconds") else "missing")
            events = [ev("LocationCreated", {"id": "bakery", "name": "Bakery"}),
                      ev("ProductionRecipeConfigured", invalid)]
            with pytest.raises(InvalidEvent):
                db.append("test", "invalid-config", 0, events, bootstrap=True)
            assert db.load("test").to_dict() == old
    with SQLiteEventStore(tmp_path / "late.sqlite") as db:
        setup(db, recipe=False)
        before = db.load("test").to_dict()
        with pytest.raises(InvalidEvent, match="bootstrap"):
            db.append("test", "not-initialization", before["revision"],
                      [ev("ProductionRecipeConfigured", RECIPE)])
        assert db.load("test").to_dict() == before
