"""03-A persistence: old versions remain untouched; NPC injuries remain private."""
import pytest
from carlos_sim import SQLiteEventStore, DomainEvent
from carlos_sim.store import UnsupportedVersion
from test_property_02h1 import village


def make_injury():
    return DomainEvent(
        "InjuryRecorded", None, "trusted bootstrap scene", 0,
        {"injury_id": "nora-injury", "subject_id": "nora",
         "severity": 25, "source": "trusted_test_bootstrap"},
    )


def test_old_29_37_world_refused_without_rewrite(tmp_path):
    path = tmp_path / "old-version.sqlite"
    with SQLiteEventStore(path) as db:
        village(db)
        db.db.execute(
            "UPDATE worlds SET schema_version=29, rules_version=37 WHERE id='v'"
        )
        before_world = db.db.execute("SELECT * FROM worlds WHERE id='v'").fetchone()
        before_events = db.db.execute(
            "SELECT seq, payload, hash FROM events WHERE world_id='v' ORDER BY seq"
        ).fetchall()
        with pytest.raises(UnsupportedVersion):
            db.load("v")
        with pytest.raises(UnsupportedVersion):
            db.verify("v")
        assert db.db.execute("SELECT * FROM worlds WHERE id='v'").fetchone() == before_world
        assert db.db.execute(
            "SELECT seq, payload, hash FROM events WHERE world_id='v' ORDER BY seq"
        ).fetchall() == before_events


def test_private_npc_injury_not_revealed_by_store_player_view(tmp_path):
    with SQLiteEventStore(tmp_path / "private.sqlite") as db:
        village(db)
        state = db.load("v")
        db.append("v", "injury-init", state.revision, [make_injury()], bootstrap=True)
        assert db.load("v").injuries["nora-injury"]["severity"] == 25
        public = db.player_view("v")
        assert set(public) == {"world_id", "time", "revision"}
        assert "nora-injury" not in str(public)
        assert "severity" not in str(public)
        assert "injuries" not in str(public)


def test_bootstrap_injury_does_not_change_resources_or_player_vitals(tmp_path):
    with SQLiteEventStore(tmp_path / "world.sqlite") as db:
        village(db)
        before = db.load("v")
        after = db.append("v", "injury-init", before.revision,
                          [make_injury()], bootstrap=True)
        assert after.resources == before.resources
        assert after.rpg_profiles == before.rpg_profiles
        assert after.time == before.time
        assert db.verify("v").to_dict() == after.to_dict()


def test_previous_03a4_schema_30_rules_38_rejected_without_change(tmp_path):
    """The new SQLite commands column requires a distinct schema identity."""
    path = tmp_path / "previous-03a4.sqlite"
    with SQLiteEventStore(path) as db:
        village(db)
        db.db.execute(
            "UPDATE worlds SET schema_version=30, rules_version=38 WHERE id='v'"
        )
        rows_before = db.db.execute("SELECT * FROM worlds WHERE id='v'").fetchall()
        events_before = db.db.execute(
            "SELECT seq, command_id, payload, hash FROM events WHERE world_id='v' ORDER BY seq"
        ).fetchall()
        with pytest.raises(UnsupportedVersion):
            db.load("v")
        assert db.db.execute("SELECT * FROM worlds WHERE id='v'").fetchall() == rows_before
        assert db.db.execute(
            "SELECT seq, command_id, payload, hash FROM events WHERE world_id='v' ORDER BY seq"
        ).fetchall() == events_before
