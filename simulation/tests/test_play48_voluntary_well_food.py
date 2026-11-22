"""P8 food at well is a voluntary, physically carried fisher loaf, not a grant.

Only current co-located neighbors may request assistance through existing
01-J consent and receipt reducer. All untouched old NPCs retain default rules.
"""
from __future__ import annotations
import pytest
from carlos_sim import DomainEvent
from carlos_sim.domain import WorldState, apply_event
from carlos_sim.voluntary_well_food import (
    choose_volunteer_well_visit,
    choose_local_well_request, choose_local_well_settlement,
)
from test_play48_real_watch_income_24h import seed


def scenario(tmp_path, *, at_well=False):
    tmp_path.mkdir(parents=True, exist_ok=True)
    original = seed(tmp_path / "original-genesis.sqlite")
    d = original.to_dict()
    d["time"] = 3600
    d["entities"]["layla"]["location_id"] = "well" if at_well else "riverbank"
    d["npcs"]["layla"]["needs"].update(hunger=25, fatigue=20, safety=0)
    d["resources"]["layla"]["food"] = 1
    d["npcs"]["hana"]["needs"].update(hunger=100, fatigue=20, safety=0)
    d["resources"]["hana"]["food"] = 0
    d["entities"]["hana"]["location_id"] = "well"
    d["npcs"]["huda"]["needs"].update(hunger=100, fatigue=20, safety=0)
    d["resources"]["huda"]["food"] = 0
    d["entities"]["huda"]["location_id"] = "well"
    nav = d["navigation"].setdefault(
        "layla", {"known_routes": [], "visited": [], "target": None})
    nav["known_routes"] = sorted(set(nav["known_routes"]) | {"well-river"})
    nav["visited"] = sorted(set(nav["visited"]) | {"riverbank"})
    nav["target"] = None
    return d


def test_visit_is_single_real_learned_leg_without_remote_courier_or_stock_oracle(tmp_path):
    d = scenario(tmp_path)
    before = WorldState(**d).to_dict()
    walk = choose_volunteer_well_visit(WorldState(**d), "layla")
    assert walk is not None and walk.route_id == "well-river"
    # Removing recipients changes nothing in the decision to visit well.
    d["entities"]["hana"]["location_id"] = "farm"
    d["entities"]["huda"]["location_id"] = "farm"
    assert choose_volunteer_well_visit(WorldState(**d), "layla") == walk
    assert before["resources"]["layla"]["food"] == 1


@pytest.mark.parametrize("mutation", [
    lambda d: d["resources"]["layla"].update(food=0),
    lambda d: d["npcs"]["layla"]["needs"].update(hunger=60),
    lambda d: d["npcs"]["layla"]["needs"].update(fatigue=70),
    lambda d: d["npcs"]["layla"]["needs"].update(safety=75),
    lambda d: d["npcs"]["layla"].update(role="merchant"),
    lambda d: d["navigation"]["layla"].update(known_routes=[]),
    lambda d: d["navigation"]["layla"].update(target="market"),
])
def test_never_visit_if_unfed_unsafe_unsigned_or_road_unknown(tmp_path, mutation):
    d = scenario(tmp_path)
    mutation(d)
    assert choose_volunteer_well_visit(WorldState(**d), "layla") is None


def test_physically_present_request_separate_acceptance_and_conserved_receipt(tmp_path):
    d = scenario(tmp_path, at_well=True)
    s = WorldState(**d)
    ask = choose_local_well_request(s)
    assert ask is not None and ask.donor == "layla" and ask.recipient == "hana"
    assert choose_local_well_settlement(s) is None
    s = apply_event(s, DomainEvent("AssistanceRequested", "hana",
        "one real loaf requested on-site", s.time,
        {"id": ask.request_id, "provider": "layla",
         "resource": "food", "quantity": 1}), assistance_authorized=True)
    s = apply_event(s, DomainEvent("AssistanceResponded", "layla",
        "voluntary acceptance at local well", s.time,
        {"id": ask.request_id, "accept": True}), assistance_authorized=True)
    assert choose_local_well_settlement(s) is None
    d2 = s.to_dict()
    d2["time"] += 1
    s = WorldState(**d2)
    claim = choose_local_well_settlement(s)
    assert claim is not None and claim.request_id == ask.request_id
    delivered = apply_event(s, DomainEvent("AssistanceFulfilled", "layla",
        "physical loaf handover", s.time, {"id": claim.request_id}),
        assistance_authorized=True)
    assert delivered.resources["layla"]["food"] == 0
    assert delivered.resources["hana"]["food"] == 1
    assert delivered.resources["huda"]["food"] == 0
    receipt = delivered.obligations[ask.request_id]
    assert receipt["status"] == "fulfilled"
    assert receipt["transfer"]["provider_before"] - receipt["transfer"]["provider_after"] == 1
    assert receipt["transfer"]["requester_after"] - receipt["transfer"]["requester_before"] == 1


def test_no_request_without_needy_present_partner_or_fisher_consent(tmp_path):
    d = scenario(tmp_path, at_well=True)
    d["npcs"]["hana"]["needs"]["hunger"] = 60
    d["npcs"]["huda"]["needs"]["hunger"] = 50
    assert choose_local_well_request(WorldState(**d)) is None
    d = scenario(tmp_path / "other", at_well=True)
    d["entities"]["layla"]["location_id"] = "riverbank"
    assert choose_local_well_request(WorldState(**d)) is None
    d = scenario(tmp_path / "trust", at_well=True)
    d["relations"].setdefault("layla", {})["hana"] = -25
    d["relations"].setdefault("layla", {})["huda"] = -25
    assert choose_local_well_request(WorldState(**d)) is None
