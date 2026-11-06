"""03-A2: injury intake is read-only and never self-authorizes persistence."""
import pytest
from carlos_sim.domain import WorldState
from carlos_sim.injury_intake import assess_injury_intake as assess


def world():
    return WorldState(world_id="test", time=5,
                      entities={"nora": {"controller": "npc", "location_id": "square", "name": "Nora"},
                                "carlos": {"controller": "player", "location_id": "square", "name": "Carlos"}},
                      locations={"square": {"name": "Square"}},
                      rpg_profiles={"carlos": {
                          "vitals": {"hp": {"current": 90, "max": 100},
                                     "st": {"current": None, "max": None},
                                     "mp": {"current": None, "max": None}},
                          "xp_current": None, "xp_goal": None, "level": None,
                          "attributes": {}, "inventory": {}, "equipment": {},
                      }})


def proposal(w, **updates):
    args = dict(subject_id="nora", injury_id="injury-1", severity=20,
                source_kind="trusted_test_scenario",
                source_reference="scenario-1", onset_time=5)
    args.update(updates)
    return assess(w, **args)


def test_npc_injury_proposal_does_not_forge_hp_or_commit():
    w = world()
    before = w.to_dict()
    p = proposal(w)
    assert p["controller"] == "npc"
    assert p["hp_current_known"] is False
    assert p["hp_adjustment"] is None
    assert p["injury_recorded"] is False
    assert p["source_provenance_verified"] is False
    assert p["commit_authorized"] is False
    assert w.to_dict() == before


def test_player_known_hp_does_not_imply_injury_or_hp_change():
    w = world()
    before = w.to_dict()
    p = proposal(w, subject_id="carlos")
    assert p["hp_current_known"] is True
    assert p["hp_adjustment"] is None
    assert p["world_mutated"] is False
    assert w.to_dict() == before


@pytest.mark.parametrize("changes", [
    {"subject_id": "ghost"}, {"subject_id": True},
    {"injury_id": "bad id"}, {"severity": True},
    {"severity": 0}, {"severity": 101},
    {"source_kind": "combat"}, {"source_reference": ""},
    {"onset_time": True}, {"onset_time": 4}, {"onset_time": 6},
])
def test_bad_intake_rejected_without_mutation(changes):
    w = world()
    before = w.to_dict()
    with pytest.raises(ValueError):
        proposal(w, **changes)
    assert w.to_dict() == before


def test_detached_result_and_repeatable_assessment():
    w = world()
    result = proposal(w)
    result["severity_proposed"] = 100
    assert proposal(w)["severity_proposed"] == 20
