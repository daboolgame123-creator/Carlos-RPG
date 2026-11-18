"""P0: replay the unmodified real 72h village and prove one baker's earned meal.

Requires the existing CI original-13-NPC SQLite artifact, not invented initial
resources or an injected bakery loaf. The historical 72h state is immutable:
the experiment extends a copied event ledger for 6 actual simulation hours.
"""
from __future__ import annotations

import os
import shutil

import pytest

from carlos_sim import SQLiteEventStore
from carlos_sim.economic_diagnostics import audit_npc_economy
from play48_integrated_acceptance import WORLD, HOUR, advance_to


def test_original_persisted_baker_72h_can_work_and_eat_earned_food(tmp_path):
    from pathlib import Path
    source = Path("evidence/candidate.sqlite")
    # This is a REAL saved-world integration test, not a standard unit
    # fixture. The broad offline regression suite cannot download GitHub's
    # 72h artifact. Skip there only; the dedicated replay job explicitly
    # REQUIRES the evidence and fails if it is missing.
    if not source.is_file():
        if os.environ.get("PLAY48_REAL_72H_EVIDENCE_REQUIRED") == "1":
            pytest.fail("required original 72h SQLite evidence was not downloaded")
        pytest.skip("external original 72h SQLite evidence not mounted; see dedicated saved-real-baker CI")
    path = tmp_path / "replay-authentic-candidate.sqlite"
    shutil.copyfile(source, path)
    with SQLiteEventStore(path) as db:
        initial = db.verify(WORLD)
        assert initial.time == 72 * HOUR
        assert len(initial.npcs) == 13
        assert audit_npc_economy(initial)["copper_known_total"] == 12
        assert initial.resources["bakery"]["grain"] >= 1
        assert initial.resources["bakery"]["food"] == 0
        assert initial.npcs["basim"]["needs"]["hunger"] == 75
        earned_before = sum(
            j["site_id"] == "bakery" and "food_wage" in j
            for j in initial.production_jobs.values()
        )
        baked_before = sum(
            j["site_id"] == "bakery" and j["status"] == "completed"
            for j in initial.production_jobs.values()
        )
        eaten_before = sum(
            c["npc_id"] == "basim" for c in initial.consumptions.values()
        )
        assert earned_before == 1
        assert baked_before == 28
    result = advance_to(path, 78, candidate=True)
    with SQLiteEventStore(path) as db:
        state = db.verify(WORLD)
        assert state.time == 78 * HOUR
        assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert len(state.npcs) == 13
        assert audit_npc_economy(state)["copper_known_total"] == 12
        new_receipts = [
            j["food_wage"] for j in state.production_jobs.values()
            if j["site_id"] == "bakery" and "food_wage" in j
        ]
        assert len(new_receipts) > earned_before, "real baker still unpaid"
        assert any(
            row["site_before"] - row["site_after"] == row["amount"]
            and row["worker_after"] - row["worker_before"] == row["amount"] == 1
            for row in new_receipts
        ), "no authentic conserved earned food"
        meals = sum(c["npc_id"] == "basim" for c in state.consumptions.values())
        assert meals > eaten_before, "baker never ate an actually earned loaf"
        assert result["bread"] > baked_before, "bakery did not resume real production"
        assert result["copper"] == 12
