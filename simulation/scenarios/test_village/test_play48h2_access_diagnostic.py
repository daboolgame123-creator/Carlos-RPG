"""PLAY-48H2: forensic reachability and property audit, no remote NPC knowledge."""
from __future__ import annotations

from carlos_sim import SQLiteEventStore, WorldState
from carlos_sim.food_access_diagnostics import audit_food_access_barriers
from test_play47_closure_endurance import _seed, WORLD
from test_play48h1_funded_courier_provision import _sign


def _actor(report, npc_id):
    return next(x for x in report["actors"] if x["npc_id"] == npc_id)


def test_true_thirteen_npc_genesis_reports_custody_and_market_food_without_mutation(tmp_path):
    path = tmp_path / "original-13-causal-audit.sqlite"
    _seed(path)
    with SQLiteEventStore(path) as db:
        original = db.verify(WORLD)
        frozen = original.to_dict()
        report = audit_food_access_barriers(original)
        assert report["schema"] == 43 and report["rules"] == 58
        assert report["npc_count"] == 13
        assert report["market_saleable_food_known"] == 3
        assert report["market_site_owned_escrow_food"] == 0
        assert report["scope"].startswith("operator-only")
        assert set(x["npc_id"] for x in report["actors"]) == set(original.npcs)
        for who in ("huda", "hana"):
            row = _actor(report, who)
            assert row["known_personal_food"] == 0
            assert row["courier_reserved_cargo_food"] == 0
            assert row["signed_unearned_food_wage"] is None
            # Their copper may be an initialized entrusted slot (never
            # spendable personal currency) or missing (never implicit zero).
            assert row["copper_scope"] in {"consignment_only", "unknown"}
            assert row["personally_spendable_copper"] is None
        assert all(x["known_road_seconds_to_market"] is None or
                   x["known_road_seconds_to_market"] >= 0
                   for x in report["actors"])
        assert original.to_dict() == frozen
        assert db.load(WORLD).to_dict() == frozen


def test_signed_food_is_employer_escrow_not_market_inventory_or_npc_entitlement(tmp_path):
    path = tmp_path / "employer-funded-audit.sqlite"
    _seed(path)
    with SQLiteEventStore(path) as db:
        before = db.verify(WORLD)
        after = _sign(db, workers=("huda", "hana"), units=1)
        a = audit_food_access_barriers(before)
        b = audit_food_access_barriers(after)
        assert a["market_saleable_food_known"] == 3
        assert b["market_saleable_food_known"] == 1
        assert a["market_site_owned_escrow_food"] == 0
        assert b["market_site_owned_escrow_food"] == 2
        for who in ("huda", "hana"):
            row = _actor(b, who)
            assert row["known_personal_food"] == 0
            assert row["signed_unearned_food_wage"]["remaining"] == 1
            assert row["signed_unearned_food_wage"]["paid_receipts"] == 0
            assert row["locally_affordable_now"] is False
        assert after.to_dict() == db.verify(WORLD).to_dict()


def test_audit_empty_world_does_not_guess_stock_or_routes():
    state = WorldState("empty")
    original = state.to_dict()
    report = audit_food_access_barriers(state)
    assert report["npc_count"] == 0 and report["actors"] == []
    assert report["market_saleable_food_known"] is None
    assert report["market_site_owned_escrow_food"] == 0
    assert state.to_dict() == original


def test_audit_rejects_unverified_plain_dict():
    try:
        audit_food_access_barriers({"npcs": {}})
    except TypeError:
        return
    raise AssertionError("forensic audit must accept only a validated WorldState")
