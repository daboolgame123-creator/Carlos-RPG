"""PLAY48AA: actual grain-for-bread contract over bakery->farm road.

An explicitly time-zero signed farm bread share creates ONE pending claim only
on an authenticated farm-grain delivery to the bakery. Bakery may pay the
farm only with an already baked real loaf, physically carried by the same
courier on its bakery->farm return road instead of (NOT alongside) copper.

NO fake production, no new roads, no wage payments and no guarantee of
survival: this is the FIRST physical procurement leg, not an economic cure.
"""
from __future__ import annotations

import json
import pytest

from carlos_sim import DomainEvent, SQLiteEventStore
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.supply import (
    _signed_physical_lane, _bakery_return_unpromised_food, project_cargo,
)
from test_play47_closure_endurance import DAY, WORLD
from test_play47_joined_professions import _joined_bootstrap
from test_play48h3_early_market_wage import _run, _conserve
from test_play48s_authentic_courier_food_wages import _stats, _check_wage_receipts
import test_play38_multi_farm_couriers as east


def _bootstrap_for_share(enabled):
    assert type(enabled) is bool
    def _actual(db, *, initial_market_food, **options):
        assert initial_market_food == 3
        assert options == {
            "water": 2, "seed": 1, "harvest_yield": 3,
            "personal_food": 0, "market_wallets": True,
            "hungry_market_buyers": True,
            "one_hungry_market_buyer": False,
        }
        return _joined_bootstrap(
            db, initial_market_food=3, site_payroll_enabled=True,
            site_payroll_wage_coin=2, wood_charcoal_jobs_enabled=True,
            farm_opening_food_wage=True, farm_initial_food_loaves=2,
            farm_bread_share_enabled=enabled,
        )
    return _actual


def _seed_signed_share(path, *, share):
    with SQLiteEventStore(path) as db:
        east.seed_two_field_world(
            db, east_growth_seconds=DAY, east_grain_yield=12,
            initial_water=2, initial_market_food=3,
            market_wallets=True, hungry_market_buyers=True,
            cash_return=True, waged_harvest=True, harvest_wage_copper=2,
            bootstrap=_bootstrap_for_share(share),
        )
        original = db.load(WORLD)
        assert len(original.npcs) == 13
        assert original.resources["farm"]["food"] == 2
        assert original.resources["market"]["food"] == 1
        assert original.resources["bakery"]["food"] == 0
        original = db.append(WORLD, "aa:actual-season-and-consumption",
            original.revision, [
                DomainEvent("WaterSourceConfigured", None, "actual finite water", 0,
                    {"site_id": "well", "capacity": 8}),
                DomainEvent("MetabolismPolicyConfigured", None, "normal hunger", 0,
                    {"hunger_seconds_per_point": 3600,
                     "activity_hunger_percent": 20}),
            ], bootstrap=True)
        original = db.append(WORLD, "aa:preexisting-farm-worker-food",
            original.revision, [
                DomainEvent("CourierProvisionConfigured", None,
                    "signed original two employer-owned loaves only", 0,
                    {"id": "farm-water-huda", "courier_id": "huda",
                     "payer_site": "farm", "units": 2}),
            ], bootstrap=True)
        assert (original.schema_version, original.rules_version) == (45, 60)
        assert original.resources["farm"]["food"] == 0
        assert original.resources["market"]["food"] == 1
        assert _conserve(original) == 2
        assert audit_npc_economy(original)["copper_known_total"] == 12
        assert db.verify(WORLD).to_dict() == original.to_dict()
        return original


def test_signed_grain_share_created_without_grain_or_bread_grant(tmp_path):
    a = _seed_signed_share(tmp_path / "aa-signed.sqlite", share=True)
    b = _seed_signed_share(tmp_path / "aa-legacy.sqlite", share=False)
    assert len(a.npcs) == len(b.npcs) == 13
    assert len(a.courier_provisions) == 1
    assert a.resources == b.resources
    assert a.supply_circuits["huda"]["bread_share_earned"] == 0
    assert a.supply_circuits["huda"]["bread_share_delivered"] == 0
    assert "bread_share_earned" not in b.supply_circuits["huda"]
    assert "bread_share_earned" not in a.supply_circuits["hana"]
    assert a.resources["bakery"]["grain"] == b.resources["bakery"]["grain"] == 0
    assert a.resources["bakery"]["food"] == b.resources["bakery"]["food"] == 0
    assert a.resources["farm"]["food"] == b.resources["farm"]["food"] == 0
    assert a.resources["market"]["food"] == b.resources["market"]["food"] == 1
    assert sum(v.get("food", 0) for v in a.resources.values()) + sum(
        r["remaining"] for r in a.courier_provisions.values()
    ) == 3


def test_no_owed_grain_bread_or_invented_bakery_food_cannot_be_carried(tmp_path):
    state = _seed_signed_share(tmp_path / "aa-reject.sqlite", share=True)
    source = state.to_dict()
    huda = source["supply_circuits"]["huda"]
    huda["index"] = 4
    source["entities"]["huda"]["location_id"] = "bakery"
    # This is an ISOLATED attack fixture, not a persisted event or a real
    # NPC location change. The reducer independently rejects foreign cargo.
    forged = DomainEvent("SupplyCargoPicked", "huda", "forged bread load", 0,
        {"courier_id": "huda", "resource": "food"})
    with pytest.raises(ValueError, match="local planned shipping lane"):
        project_cargo(source, forged, supply_authorized=True)

    huda["bread_share_earned"] = 1
    assert _bakery_return_unpromised_food(source) == 0
    with pytest.raises(ValueError, match="local planned shipping lane"):
        project_cargo(source, forged, supply_authorized=True)

    source["resources"]["bakery"]["food"] = 2
    assert _signed_physical_lane(source, huda, "huda") == (
        "bakery", "farm", "food")
    # Real trusted cargo event would consume exactly one site-owned bakery
    # bread and place ONE consignment in courier's real physical slot.
    project_cargo(source, forged, supply_authorized=True)
    assert source["resources"]["bakery"]["food"] == 1
    assert source["resources"]["huda"]["food"] == 1
    assert huda["carry"] == {
        "source": "bakery", "destination": "farm", "resource": "food"}
    assert huda["bread_share_delivered"] == 0  # NOT paid until actual arrival.
    # A second pickup in the same leg cannot print or double-load bread.
    with pytest.raises(ValueError):
        project_cargo(source, forged, supply_authorized=True)


def test_true_48h_grain_for_bread_with_two_original_farm_wages(tmp_path):
    control_path = tmp_path / "aa-legacy-cash-only.sqlite"
    share_path = tmp_path / "aa-physical-farm-bread-share.sqlite"
    original = _seed_signed_share(control_path, share=False)
    treatment = _seed_signed_share(share_path, share=True)
    assert original.resources == treatment.resources
    checkpoints = []
    for day in (1, 2):
        a, _ = _run(control_path, day * DAY, early=True,
            hungry_woodcutter_work_enabled=True,
            retry_known_supplier_enabled=True)
        b, _ = _run(share_path, day * DAY, early=True,
            hungry_woodcutter_work_enabled=True,
            retry_known_supplier_enabled=True)
        assert a.time == b.time == day * DAY
        assert len(a.npcs) == len(b.npcs) == 13
        assert _conserve(a) >= 0 and _conserve(b) >= 0
        assert audit_npc_economy(a)["copper_known_total"] == 12
        assert audit_npc_economy(b)["copper_known_total"] == 12
        _check_wage_receipts(control_path, a)
        _check_wage_receipts(share_path, b)
        for path, world in ((control_path, a), (share_path, b)):
            with SQLiteEventStore(path) as db:
                assert db.verify(WORLD).to_dict() == world.to_dict()
                assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
                assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
        share_account = b.supply_circuits["huda"]
        assert share_account["bread_share_delivered"] <= share_account["bread_share_earned"]
        checkpoints.append({
            "day": day, "cash_only": _stats(a),
            "genuine_grain_bread_return": _stats(b),
            "grain_entitlements_after_real_grain_deliveries":
                share_account["bread_share_earned"],
            "actual_bread_returned_to_farm":
                share_account["bread_share_delivered"],
            "bakery_food": b.resources["bakery"]["food"],
            "farm_food": b.resources["farm"]["food"],
            "bakery_copper": b.resources["bakery"]["coin_copper"],
            "farm_copper": b.resources["farm"]["coin_copper"],
        })
    assert treatment.schema_version == 45 and treatment.rules_version == 60
    print("PLAY48AA_GENUINE_13NPC_BAKERY_TO_FARM_GRAIN_FOR_BREAD",
        json.dumps({
            "same_thirteen_people": True,
            "same_three_initial_loaves_and_real_twelve_copper": True,
            "only_signed_transport_barter_policy_differs_at_genesis": True,
            "one_claim_earned_per_real_grain_delivery": True,
            "bakery_farm_bread_must_cross_real_road": True,
            "cannot_use_same_trip_for_copper_and_bread": True,
            "physical_day_24_and_day_48": checkpoints,
            "full_seven_day_recovery_proven": False,
            "wage_refill_to_huda_implemented": False,
            "schema45_rules60_requires_separate_migration": True,
        }, sort_keys=True), flush=True)
