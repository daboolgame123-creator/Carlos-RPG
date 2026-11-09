"""PLAY-46: true atomic ore+charcoal smelting and old-recipe parity."""
from __future__ import annotations

import copy
import pytest
from carlos_sim import DomainEvent, SQLiteEventStore, TimeEngine, WorldState
from carlos_sim.production import NPCProductionService
from carlos_sim.store import InvalidEvent

WORLD = "play46-multiinput"
FORGE = "forge"
HOME = "home"
SMITH = "smith"


def _event(kind, fields):
    return DomainEvent(kind, None, "finite trusted multi-input fixture", 0, fields)


def _recipe(*, compound=True, wage=False):
    common = {"id": "smelt-iron" if compound else "old-iron",
              "site_id": FORGE, "role": "blacksmith",
              "output_resource": "iron_fitting", "output_amount": 1,
              "tool_resource": "anvil", "duration_seconds": 90}
    if compound:
        common["inputs"] = [{"resource": "iron_ore", "amount": 1},
                            {"resource": "charcoal", "amount": 1}]
    else:
        common.update(input_resource="iron_ore", input_amount=1)
    if wage:
        common["wage_coin"] = 1
    return common


def _seed(db, *, ore=1, coal=1, compound=True, wage=False, second=False,
          recipe_override=None):
    db.create_world(WORLD)
    events = [
        _event("LocationCreated", {"id": FORGE, "name": "Forge"}),
        _event("LocationCreated", {"id": HOME, "name": "Home"}),
    ]
    for npc_id in (("smith", "smith2") if second else ("smith",)):
        events.extend([
            _event("EntityCreated", {
                "id": npc_id, "name": npc_id,
                "location_id": FORGE, "controller": "npc",
            }),
            _event("NPCConfigured", {
                "npc_id": npc_id, "role": "blacksmith",
                "needs": {"hunger": 10, "fatigue": 0, "safety": 0},
                "goals": {"earn": 10, "explore": 10, "survive": 30},
            }),
        ])
    for owner, stock in {
        FORGE: {"iron_ore": ore, "charcoal": coal, "anvil": 1,
                "iron_fitting": 0, "coin_copper": 1 if wage else 0},
        SMITH: {"coin_copper": 0},
    }.items():
        for item, current in stock.items():
            events.append(_event("ResourceChanged", {
                "owner_id": owner, "resource": item, "previous": None,
                "current": current, "source": "initialization",
            }))
    events.append(_event("ProductionRecipeConfigured",
                         recipe_override if recipe_override is not None
                         else _recipe(compound=compound, wage=wage)))
    return db.append(WORLD, "play46:boot", 0, events, bootstrap=True)


def test_compound_both_inputs_are_consumed_with_two_real_receipts(tmp_path):
    with SQLiteEventStore(tmp_path / "smelting.sqlite") as db:
        _seed(db, wage=True)
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            first = NPCProductionService(db, clock).start(
                WORLD, SMITH, "smelt-iron", "one-smelting-job",
                expected_revision=db.load(WORLD).revision,
            ).state
            assert first.resources[FORGE]["iron_ore"] == 0
            assert first.resources[FORGE]["charcoal"] == 0
            assert first.resources[FORGE]["iron_fitting"] == 0
            job = first.production_jobs["one-smelting-job"]
            assert set(job) & {"input_before", "input_after"} == set()
            assert dict(job["input_before_by_resource"]) == {
                "iron_ore": 1, "charcoal": 1,
            }
            assert dict(job["input_after_by_resource"]) == {
                "iron_ore": 0, "charcoal": 0,
            }
            state = clock.advance(
                WORLD, seconds=90, command_id="play46:finish",
                expected_revision=first.revision,
            ).state
            assert state.resources[FORGE]["iron_fitting"] == 1
            assert state.production_jobs["one-smelting-job"]["status"] == "completed"
            assert db.verify(WORLD).to_dict() == state.to_dict()
            db.snapshot(WORLD)
            assert db.verify(WORLD).to_dict() == state.to_dict()
            assert db.db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        finally:
            clock.close_session(WORLD)


@pytest.mark.parametrize("ore,coal", [(0, 1), (1, 0), (0, 0)])
def test_compound_all_or_nothing_underflow_and_revision_unchanged(tmp_path, ore, coal):
    with SQLiteEventStore(tmp_path / "empty.sqlite") as db:
        _seed(db, ore=ore, coal=coal)
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            old = db.load(WORLD)
            with pytest.raises(InvalidEvent):
                NPCProductionService(db, clock).start(
                    WORLD, SMITH, "smelt-iron", "should-not-exist",
                    expected_revision=old.revision,
                )
            assert db.load(WORLD).to_dict() == old.to_dict()
            assert db.verify(WORLD).to_dict() == old.to_dict()
            assert not db.load(WORLD).production_jobs
        finally:
            clock.close_session(WORLD)


@pytest.mark.parametrize("change", [
    lambda x: x["inputs"].append({"resource": "water", "amount": 1}),
    lambda x: x["inputs"].__setitem__(1, {"resource": "iron_ore", "amount": 1}),
    lambda x: x["inputs"].__setitem__(1, {"resource": "coin_copper", "amount": 1}),
    lambda x: x["inputs"].__setitem__(1, {"resource": "anvil", "amount": 1}),
    lambda x: x["inputs"].__setitem__(1, {"resource": "iron_fitting", "amount": 1}),
    lambda x: x["inputs"].__setitem__(1, {"resource": "charcoal", "amount": 0}),
    lambda x: x["inputs"].__setitem__(1, {"resource": "charcoal", "amount": True}),
    lambda x: x["inputs"].__setitem__(1, {"resource": "unknown", "amount": 1}),
    lambda x: x["inputs"].clear(),
    lambda x: x.update(input_resource="charcoal"),
    lambda x: x.update(inputs="charcoal"),
])
def test_invalid_compound_recipe_rejected_at_bootstrap_without_events(tmp_path, change):
    recipe = copy.deepcopy(_recipe())
    change(recipe)
    with SQLiteEventStore(tmp_path / "invalid-recipe.sqlite") as db:
        with pytest.raises(InvalidEvent):
            _seed(db, recipe_override=recipe)
        assert db.load(WORLD).revision == 0
        assert db.verify(WORLD).revision == 0


def test_job_receipt_tampering_cannot_be_restored(tmp_path):
    with SQLiteEventStore(tmp_path / "bad-receipt.sqlite") as db:
        _seed(db)
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            good = NPCProductionService(db, clock).start(
                WORLD, SMITH, "smelt-iron", "sealed-job",
                expected_revision=db.load(WORLD).revision,
            ).state
            for change in ("wrong-amount", "forged-resource", "missing-receipt"):
                raw = good.to_dict()
                job = raw["production_jobs"]["sealed-job"]
                if change == "wrong-amount":
                    job["input_after_by_resource"]["charcoal"] = 1
                elif change == "forged-resource":
                    job["input_before_by_resource"]["coin_copper"] = 1
                else:
                    del job["input_after_by_resource"]
                with pytest.raises(ValueError):
                    WorldState.from_dict(raw)
            assert db.verify(WORLD).to_dict() == good.to_dict()
        finally:
            clock.close_session(WORLD)


def test_legacy_single_input_retains_original_receipt_keys_and_products(tmp_path):
    with SQLiteEventStore(tmp_path / "legacy.sqlite") as db:
        _seed(db, compound=False, coal=0)
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            state = NPCProductionService(db, clock).start(
                WORLD, SMITH, "old-iron", "old-job",
                expected_revision=db.load(WORLD).revision,
            ).state
            job = state.production_jobs["old-job"]
            assert job["input_before"] == 1
            assert job["input_after"] == 0
            assert "input_before_by_resource" not in job
            assert state.resources[FORGE]["charcoal"] == 0
            state = clock.advance(WORLD, seconds=90,
                                  command_id="play46:old-finish",
                                  expected_revision=state.revision).state
            assert state.resources[FORGE]["iron_fitting"] == 1
            assert db.verify(WORLD).to_dict() == state.to_dict()
        finally:
            clock.close_session(WORLD)


def test_one_anvil_cannot_start_two_concurrent_compound_jobs(tmp_path):
    with SQLiteEventStore(tmp_path / "one-tool.sqlite") as db:
        _seed(db, ore=2, coal=2, second=True)
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            state = NPCProductionService(db, clock).start(
                WORLD, SMITH, "smelt-iron", "first",
                expected_revision=db.load(WORLD).revision,
            ).state
            with pytest.raises(InvalidEvent):
                NPCProductionService(db, clock).start(
                    WORLD, "smith2", "smelt-iron", "second",
                    expected_revision=state.revision,
                )
            assert db.load(WORLD).revision == state.revision
            assert state.resources[FORGE]["iron_ore"] == 1
            assert state.resources[FORGE]["charcoal"] == 1
        finally:
            clock.close_session(WORLD)


def test_unauthorized_compound_start_is_rejected(tmp_path):
    with SQLiteEventStore(tmp_path / "unauthorized.sqlite") as db:
        state = _seed(db)
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            with pytest.raises(InvalidEvent):
                db.append(WORLD, "forged-start", state.revision, [
                    DomainEvent("ProductionStarted", SMITH,
                        "forged production", 0,
                        {"id": "forged", "recipe_id": "smelt-iron", "npc_id": SMITH}),
                ])
            assert db.verify(WORLD).to_dict() == state.to_dict()
        finally:
            clock.close_session(WORLD)
