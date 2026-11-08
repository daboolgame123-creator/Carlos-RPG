"""Phase 01-T compatibility tests: version fail-closed and digest parity."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from carlos_sim import (DomainEvent, SQLiteEventStore, UnsupportedVersion,
                        TimeEngine, LivingWorldEngine, canonical_hash)
from carlos_sim.domain import SCHEMA_VERSION, RULES_VERSION
from test_gathering_autonomy import make_world, NAMES


def test_schema_and_rules_versions():
    assert SCHEMA_VERSION == 37
    assert RULES_VERSION == 49


def test_flag_off_no_new_knowledge_events_in_rules_26(tmp_path):
    with SQLiteEventStore(tmp_path / "flagoff.sqlite") as db:
        make_world(db)
        clock = TimeEngine(db)
        clock.open_session("r")
        result = LivingWorldEngine(db, clock, foraging_enabled=True,
                                   knowledge_enabled=False).advance(
            "r", seconds=120, command_id="go",
            expected_revision=db.load("r").revision)
        s = result.state
        assert s.rules_version == 49
        assert s.schema_version == 37
        # No knowledge events were emitted (flag off).
        payloads = db.db.execute("SELECT payload FROM events WHERE world_id='r'").fetchall()
        for (payload,) in payloads:
            et = json.loads(payload)["event_type"]
            assert et not in ("NPCInformationDelivered", "NPCBeliefReceived")


def test_real_13_17_world_rejected_rows_untouched(tmp_path):
    with SQLiteEventStore(tmp_path / "v1317.sqlite") as db:
        make_world(db)
        db.db.execute("UPDATE worlds SET schema_version=13, rules_version=17 WHERE id='r'")
        with pytest.raises(UnsupportedVersion):
            db.load("r")
    # No destructive migration: rows and history untouched.
    with SQLiteEventStore(tmp_path / "v1317.sqlite") as db:
        row = db.db.execute("SELECT schema_version, rules_version, revision FROM worlds WHERE id='r'").fetchone()
        assert row == (13, 17, 39)
        assert db.db.execute("SELECT count(*) FROM events WHERE world_id='r'").fetchone()[0] == 39
        assert db.db.execute("SELECT count(*) FROM snapshots WHERE world_id='r'").fetchone()[0] == 0


def test_real_12_16_world_rejected_rows_untouched(tmp_path):
    with SQLiteEventStore(tmp_path / "v1216.sqlite") as db:
        make_world(db)
        db.db.execute("UPDATE worlds SET schema_version=12, rules_version=16 WHERE id='r'")
        with pytest.raises(UnsupportedVersion):
            db.load("r")
    with SQLiteEventStore(tmp_path / "v1216.sqlite") as db:
        row = db.db.execute("SELECT schema_version, rules_version, revision FROM worlds WHERE id='r'").fetchone()
        assert row == (12, 16, 39)
        assert db.db.execute("SELECT count(*) FROM events WHERE world_id='r'").fetchone()[0] == 39


def test_parity_bench_strip_list_unchanged():
    """The parity bench must strip only schema/rules/foraging_attempts, never
    add a new strip for beliefs (which would hide knowledge divergence)."""
    from pathlib import Path
    src = Path(__file__).parent.parent / "scenarios" / "test_village" / "bench_event_parity.py"
    text = src.read_text()
    assert "foraging_attempts" in text
    assert "schema_version" in text
    assert "rules_version" in text
    assert "'beliefs'" not in text
    assert "'rpg_profiles'" in text
    assert "'environment_cycles'" in text
    assert "'production_recipes'" in text and "'production_jobs'" in text
    assert "'market_stalls'" in text and "'market_offers'" in text and "'market_trades'" in text
    assert "'loan_contracts'" in text and "'loan_repayments'" in text
    assert "'npc_temperaments'" in text
    assert "'local_institutions'" in text


def test_all_cross_version_parity_benches_strip_local_institutions():
    """J1c2b added an empty ``local_institutions`` collection.

    Every cross-version parity probe that compares a semantic state digest
    against a pre-Schema29 baseline must ignore that empty collection, or the
    legacy digest changes for schema-only reasons. Guard all three benches so
    the same omission cannot silently reappear.
    """
    root = Path(__file__).parent.parent / "scenarios" / "test_village"
    benches = (
        "bench_event_parity.py",
        "bench_food_knowledge_parity.py",
        "bench_scarcity_disabled_parity.py",
    )
    for name in benches:
        text = (root / name).read_text()
        assert "'local_institutions'" in text or '"local_institutions"' in text, name


def test_ci_parity_gates_pin_current_rules_version():
    """Keep explicit CI version pins in sync with RULES_VERSION.

    The 01-U and 01-V parity steps pin the baseline at Rules 18 and the
    candidate at the current rules version. A J1c2b version bump left these
    assertions at 36 and broke CI after the digest fix; this guard makes the
    next bump fail locally instead of in a later workflow step.
    """
    workflow = (Path(__file__).resolve().parents[2]
                / ".github" / "workflows" / "simulation-tests.yml")
    text = workflow.read_text()
    assert f"new['rules_version'] == {RULES_VERSION}" in text
    assert f"candidate['rules_version'] == {RULES_VERSION}" in text
