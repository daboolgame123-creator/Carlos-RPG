"""SAVE-01: restore pending player work/rest from independent backup bundles."""
from __future__ import annotations

from hashlib import sha256

import pytest

from carlos_sim import DomainEvent, SQLiteEventStore
from carlos_sim.backup import restore_backup_bundle, verify_backup_bundle
from carlos_sim.domain import RULES_VERSION, SCHEMA_VERSION
from carlos_sim.resumable_play import ResumableTestSession
from carlos_sim.store import DuplicateCommand


WORLD = "save01-player"
PLAYER = "carlos"
BAKERY = "bakery"
RECIPE = "save01-bread"
CODE_COMMIT = "06d61da77c2df656cd5ac672bd4fd63f5557714b"


def _event(kind: str, data: dict, *, at: int = 0) -> DomainEvent:
    return DomainEvent(kind, None, "SAVE-01 disposable player fixture", at, data)


def _setup(store: SQLiteEventStore) -> None:
    store.create_world(WORLD)
    events = [
        _event("LocationCreated", {"id": BAKERY, "name": "Bakery"}),
        _event("EntityCreated", {
            "id": PLAYER, "name": "Carlos", "controller": "player",
            "location_id": BAKERY,
        }),
    ]
    for owner, resource, amount in (
        (BAKERY, "grain", 1), (BAKERY, "food", 0),
        (BAKERY, "oven", 1), (BAKERY, "coin_copper", 2),
        (PLAYER, "food", 0), (PLAYER, "coin_copper", 0),
    ):
        events.append(_event("ResourceChanged", {
            "owner_id": owner, "resource": resource, "previous": None,
            "current": amount, "source": "initialization",
        }))
    events.extend([
        _event("PlayerNeedsInitialized", {
            "player_id": PLAYER, "hunger": 50, "fatigue": 30,
        }),
        _event("ProductionRecipeConfigured", {
            "id": RECIPE, "site_id": BAKERY, "role": "baker",
            "input_resource": "grain", "input_amount": 1,
            "output_resource": "food", "output_amount": 2,
            "tool_resource": "oven", "duration_seconds": 90,
            "wage_coin": 2, "player_worker_id": PLAYER,
        }),
    ])
    store.append(WORLD, "save01-bootstrap", 0, events, bootstrap=True)


def _digest(path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def test_backup_restore_resumes_pending_player_work_and_pays_once(tmp_path):
    source = tmp_path / "player-work.sqlite"
    session = ResumableTestSession.create(
        source, WORLD, PLAYER, _setup, disposable_test=True)
    session.store.db.execute("PRAGMA journal_mode=WAL")
    started = session.gateway.work(
        RECIPE, command_id="save01-start-bake",
        expected_revision=session.store.load(WORLD).revision,
    )
    session.gateway.wait(
        30, command_id="save01-partial-work",
        expected_revision=session.store.load(WORLD).revision,
    )
    captured = session.store.verify(WORLD).to_dict()
    job_id = started.details["job_id"]
    assert captured["time"] == 30
    assert captured["production_jobs"][job_id]["status"] == "running"
    assert captured["production_jobs"][job_id]["due"] == 90
    assert captured["resources"][BAKERY]["grain"] == 0
    assert captured["resources"][BAKERY]["food"] == 0
    assert captured["resources"][PLAYER]["coin_copper"] == 0
    session.store.snapshot(WORLD)

    bundle = tmp_path / "pending-work-backup"
    manifest = session.checkpoint(bundle, code_commit=CODE_COMMIT)
    bundle_hash = _digest(bundle / "world.sqlite")
    assert manifest["schema"] == SCHEMA_VERSION
    assert manifest["rules"] == RULES_VERSION
    assert manifest["worlds"][0]["revision"] == captured["revision"]
    assert verify_backup_bundle(bundle) == manifest
    session.close()

    restored = tmp_path / "restored-work.sqlite"
    assert restore_backup_bundle(bundle, restored) == manifest
    with ResumableTestSession.resume(
            restored, WORLD, PLAYER, disposable_test=True) as resumed:
        state = resumed.store.verify(WORLD)
        assert state.to_dict() == captured
        with pytest.raises(DuplicateCommand):
            resumed.gateway.work(
                RECIPE, command_id="save01-start-bake",
                expected_revision=state.revision,
            )
        assert resumed.store.load(WORLD).to_dict() == captured

        resumed.gateway.wait(
            59, command_id="save01-work-to-89",
            expected_revision=state.revision,
        )
        almost = resumed.store.verify(WORLD)
        assert almost.time == 89
        assert almost.production_jobs[job_id]["status"] == "running"
        assert almost.resources[BAKERY]["food"] == 0
        assert almost.resources[PLAYER]["coin_copper"] == 0

        resumed.gateway.wait(
            1, command_id="save01-work-due",
            expected_revision=almost.revision,
        )
        finished = resumed.store.verify(WORLD)
        receipt = finished.production_jobs[job_id]
        assert finished.time == 90
        assert receipt["status"] == "completed"
        assert receipt["work_wage"]["worker_id"] == PLAYER
        assert receipt["work_wage"]["amount"] == 2
        assert finished.resources[BAKERY]["food"] == 2
        assert finished.resources[BAKERY]["coin_copper"] == 0
        assert finished.resources[PLAYER]["coin_copper"] == 2
        assert (finished.resources[BAKERY]["coin_copper"]
                + finished.resources[PLAYER]["coin_copper"]) == 2
        assert resumed.store.db.execute(
            "PRAGMA integrity_check").fetchone() == ("ok",)
        assert finished.to_dict() == resumed.store.load(WORLD).to_dict()

    # Restoring and finishing the copy did not advance or rewrite the source
    # or the independently published checkpoint.
    with SQLiteEventStore(source) as original:
        assert original.verify(WORLD).to_dict() == captured
    assert _digest(bundle / "world.sqlite") == bundle_hash
    assert verify_backup_bundle(bundle) == manifest


def test_backup_restore_preserves_partial_rest_until_its_original_due_time(tmp_path):
    source = tmp_path / "player-rest.sqlite"
    session = ResumableTestSession.create(
        source, WORLD, PLAYER, _setup, disposable_test=True)
    session.gateway.rest(
        command_id="save01-start-rest",
        expected_revision=session.store.load(WORLD).revision,
    )
    session.gateway.wait(
        900, command_id="save01-half-rest",
        expected_revision=session.store.load(WORLD).revision,
    )
    captured = session.store.verify(WORLD).to_dict()
    assert captured["time"] == 900
    assert captured["player_needs"][PLAYER]["fatigue"] == 30
    assert captured["player_needs"][PLAYER]["hunger"] == 53
    bundle = tmp_path / "partial-rest-backup"
    manifest = session.checkpoint(bundle, code_commit=CODE_COMMIT)
    session.close()

    restored = tmp_path / "restored-rest.sqlite"
    assert restore_backup_bundle(bundle, restored) == manifest
    with ResumableTestSession.resume(
            restored, WORLD, PLAYER, disposable_test=True) as resumed:
        assert resumed.store.verify(WORLD).to_dict() == captured
        activity = resumed.gateway.inspect().details["activity"]
        assert activity == {"kind": "resting", "remaining_seconds": 900}

        resumed.gateway.wait(
            899, command_id="save01-rest-to-1799",
            expected_revision=resumed.store.load(WORLD).revision,
        )
        almost = resumed.store.verify(WORLD)
        assert almost.time == 1_799
        assert almost.player_needs[PLAYER]["fatigue"] == 30
        assert almost.player_needs[PLAYER]["hunger"] == 55
        assert resumed.gateway.inspect().details["activity"]["remaining_seconds"] == 1

        resumed.gateway.wait(
            1, command_id="save01-rest-due",
            expected_revision=almost.revision,
        )
        rested = resumed.store.verify(WORLD)
        assert rested.time == 1_800
        assert rested.player_needs[PLAYER]["fatigue"] == 10
        assert rested.player_needs[PLAYER]["hunger"] == 56
        assert "activity" not in resumed.gateway.inspect().details
        assert rested.to_dict() == resumed.store.load(WORLD).to_dict()

    with SQLiteEventStore(source) as original:
        assert original.verify(WORLD).to_dict() == captured
    assert verify_backup_bundle(bundle) == manifest
