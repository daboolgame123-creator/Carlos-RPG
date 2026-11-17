"""Structural tests for the read-only PLAY48 saved-world evidence inspector.

Tiny synthetic SQLite files validate parsing and refusal only. They are NOT
claimed to replace the original 60h captured original-village evidence.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from play48_saved_income_preflight import inspect


def evidence(path: Path, *, rules: int = 70, paid: bool = False) -> None:
    with sqlite3.connect(path) as db:
        db.executescript("""
            CREATE TABLE worlds (id TEXT, revision INT, sim_time INT,
                                 schema_version INT, rules_version INT);
            CREATE TABLE snapshots (world_id TEXT, revision INT, state TEXT);
            CREATE TABLE events (world_id TEXT, seq INT, payload TEXT);
        """)
        data = {
            "world_id": "test_world", "revision": 1, "time": 60 * 3600,
            "npcs": {"nora": {"needs": {"hunger": 100}},
                     "huda": {"needs": {"hunger": 100}},
                     **{f"resident-{i}": {"needs": {"hunger": 0}} for i in range(11)}},
            "resources": {"farm": {"coin_copper": 1},
                          "bakery": {"coin_copper": 1},
                          "market": {"coin_copper": 8, "food": 16},
                          "nora": {"coin_copper": 0, "food": 0},
                          "huda": {"coin_copper": 0, "food": 0},
                          "home": {"coin_copper": 2}},
            "production_recipes": {"harvest": {"wage_coin": 2}},
            "production_jobs": {"job": {"site_id": "farm", "status": "completed",
                                         "npc_id": "nora", "recipe_id": "harvest",
                                         **({"work_wage": {"amount": 2}} if paid else {})}},
            "market_trades": {}, "consumptions": {},
        }
        db.execute("INSERT INTO worlds VALUES (?,?,?,?,?)",
                   ("test_world", 1, 60 * 3600, 45, rules))
        db.execute("INSERT INTO snapshots VALUES (?,?,?)",
                   ("test_world", 1, json.dumps(data)))
        db.execute("INSERT INTO events VALUES (?,?,?)",
                   ("test_world", 1, json.dumps({
                       "event_type": "SupplyCargoDelivered", "actor_id": "huda",
                       "time": 36 * 3600,
                       "data": {"resource": "grain", "courier_id": "huda"},
                   })))


def test_funded_causal_blockers_and_no_mutation(tmp_path):
    path = tmp_path / "world.sqlite"
    evidence(path)
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    result = inspect(path)
    assert result["copper"] == 12
    assert result["original_npcs"] == 13
    assert result["farm_unpaid_copper_due"] == 2
    assert result["huda"]["last_delivery_at"] == 36 * 3600
    assert result["huda"]["delivery_resources"] == [[36 * 3600, "grain"]] or result["huda"]["delivery_resources"] == [(36 * 3600, "grain")]
    assert {"earned_farm_wages_not_funded",
            "farm_harvest_without_grain_sale_receipt",
            "nora_has_no_real_food_access",
            "huda_freight_stalled_12h_with_hunger"}.issubset(result["blockers"])
    assert result["economic_release_go"] is False
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before


def test_no_false_unpaid_claim_if_pay_receipt_exists(tmp_path):
    path = tmp_path / "paid.sqlite"
    evidence(path, paid=True)
    result = inspect(path)
    assert result["farm_unpaid_copper_due"] == 0
    assert "earned_farm_wages_not_funded" not in result["blockers"]
    assert "farm_harvest_without_grain_sale_receipt" not in result["blockers"]


def test_reject_unsupported_rules_without_edit(tmp_path):
    path = tmp_path / "old.sqlite"
    evidence(path, rules=69)
    before = path.read_bytes()
    with pytest.raises(ValueError, match="unsupported audit-only"):
        inspect(path)
    assert path.read_bytes() == before


def test_reject_incomplete_current_snapshot(tmp_path):
    path = tmp_path / "partial.sqlite"
    evidence(path)
    with sqlite3.connect(path) as db:
        db.execute("UPDATE worlds SET revision=2")
    with pytest.raises(ValueError, match="current snapshot"):
        inspect(path)
