"""03-A7c baseline guards: injury truth is not automatically NPC knowledge.

These tests deliberately do not authorize a symptom event. A persisted,
causally justified visual-symptom source is still required for 03-A7c.
"""
from carlos_sim import DomainEvent, SQLiteEventStore
from carlos_sim.injury_behavior import assess_own_injuries
from test_property_02h1 import village


def setup_world(tmp_path, severity=65):
    db = SQLiteEventStore(tmp_path / "observation-guard.sqlite")
    village(db)
    before = db.load("v")
    db.append(
        "v", "bootstrap:nora-observation-guard", before.revision,
        [DomainEvent(
            "InjuryRecorded", None, "trusted time-zero test injury", before.time,
            {"injury_id": "nora-private", "subject_id": "nora",
             "severity": severity, "source": "trusted_test_bootstrap"},
        )], bootstrap=True,
    )
    return db


def test_peer_presence_never_auto_discloses_private_injury(tmp_path):
    with setup_world(tmp_path) as db:
        state = db.load("v")
        assert state.injuries["nora-private"]["severity"] == 65
        for peer in state.npcs:
            if peer == "nora":
                continue
            assert not any("injury" in key or "symptom" in key
                           for key in state.npcs[peer]["beliefs"])
            own = assess_own_injuries(state, peer)
            assert own.active_injury_count == 0
            assert own.maximum_severity == 0
            assert "nora-private" not in repr(own)
        assert db.verify("v").to_dict() == state.to_dict()


def test_injury_is_not_exposed_after_sqlite_reopen(tmp_path):
    path = tmp_path / "observation-guard.sqlite"
    with setup_world(tmp_path) as db:
        expected = db.load("v").to_dict()
    with SQLiteEventStore(path) as reopened:
        state = reopened.load("v")
        assert state.to_dict() == expected
        assert reopened.verify("v").to_dict() == expected
        assert state.injuries["nora-private"]["severity"] == 65
        assert all("nora-private" not in repr(npc["beliefs"])
                   for ident, npc in state.npcs.items() if ident != "nora")
