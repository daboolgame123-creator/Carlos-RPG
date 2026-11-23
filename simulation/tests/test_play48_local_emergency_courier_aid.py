"""PLAY48 P9: a local starving courier and healthy owner of one actual loaf.

The policy proposes no gifts. The existing assistance reducer must authenticate
the three events, and ordinary consumption must record a real meal.
"""
import pytest

from carlos_sim.domain import WorldState
from carlos_sim.local_emergency_aid import choose_local_emergency_courier_help
from test_play48_real_watch_income_24h import seed


def sample(tmp_path):
    d = seed(tmp_path / "p9-genesis.sqlite").to_dict()
    d["time"] = 234 * 3600
    d["entities"]["layla"]["location_id"] = "well"
    d["npcs"]["layla"]["needs"].update(hunger=32, fatigue=40, safety=0)
    d["resources"]["layla"]["food"] = 1
    d["resources"]["layla"]["coin_copper"] = 1
    for who in ("hana", "huda"):
        d["entities"][who]["location_id"] = "well"
        d["npcs"][who]["needs"].update(hunger=100, fatigue=5, safety=0)
        d["resources"][who]["food"] = 0
    return d


def test_only_physical_starving_courier_and_safely_funded_willing_donor(tmp_path):
    d = sample(tmp_path)
    before = WorldState(**d).to_dict()
    assert choose_local_emergency_courier_help(WorldState(**d)) == ("hana", "layla")
    assert WorldState(**d).to_dict() == before


@pytest.mark.parametrize("mutate", [
    lambda d: d["entities"]["layla"].update(location_id="riverbank"),
    lambda d: d["npcs"]["layla"]["needs"].update(hunger=41),
    lambda d: d["npcs"]["layla"]["needs"].update(fatigue=70),
    lambda d: d["npcs"]["layla"]["needs"].update(safety=75),
    lambda d: d["resources"]["layla"].update(food=0),
    lambda d: d["resources"]["layla"].update(coin_copper=0),
    lambda d: d["relations"].setdefault("layla", {}).update(hana=-1, huda=-1),
    lambda d: d["npcs"]["hana"]["needs"].update(hunger=89),
])
def test_decline_unsafe_unknown_or_unfunded_help(tmp_path, mutate):
    d = sample(tmp_path)
    mutate(d)
    result = choose_local_emergency_courier_help(WorldState(**d))
    if result is not None:
        # One courier may still need food even if Hana's need drops below 90.
        assert result == ("huda", "layla") and d["npcs"]["hana"]["needs"]["hunger"] == 89
    else:
        assert result is None


def test_no_teleport_from_other_site_or_donation_from_quoted_market(tmp_path):
    d = sample(tmp_path)
    d["resources"]["layla"]["food"] = 0
    d["resources"]["market"]["food"] = 100
    assert choose_local_emergency_courier_help(WorldState(**d)) is None


def test_do_not_double_commit_last_owned_loaf(tmp_path):
    d = sample(tmp_path)
    d["obligations"]["prior-promise"] = {
        "requester": "nora", "provider": "layla", "resource": "food",
        "quantity": 1, "location_id": "well", "created_at": d["time"],
        "status": "promised", "responded_at": d["time"],
        "resolved_at": None, "reason": None,
        "trust_before": None, "trust_after": None, "transfer": None,
    }
    assert choose_local_emergency_courier_help(WorldState(**d)) is None


def test_no_other_donor_will_fake_presence_when_actual_helper_leaves(tmp_path):
    d = sample(tmp_path)
    d["entities"]["layla"]["location_id"] = "riverbank"
    assert choose_local_emergency_courier_help(WorldState(**d)) is None
