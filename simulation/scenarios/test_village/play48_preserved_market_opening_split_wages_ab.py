"""PLAY48 finite physical opening-food split: protect first bread sales.

The CONTROL uses the genuine existing 13NPC fixture: initial 3 loaves,
2 reserved at farm for Huda and 1 SALEABLE at market, no Hana contract.

The CANDIDATE re-allocates precisely ONE of those same three physical loaves:
Huda farm's signed opening food contract 2 -> 1, Hana market contract 0 -> 1.
The single original saleable MARKET bread unit remains available unchanged.
No payroll/grain/copper minting, free food, added residents, new routes or
engine changes. This is a DIFFERENT genesis allocation, explicitly not the
same initial ownership; every other physically authored rule is identical.

True two-world sequential SQLite simulation to 24/48/72h. An automated CI
green run must NEVER be interpreted as survival recovery.
"""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from carlos_sim import DomainEvent, SQLiteEventStore
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.food_access_diagnostics import audit_food_access_barriers
from test_play48aa_actual_barter_bread_return import _seed_signed_share
from test_play47_joined_professions import _joined_bootstrap
from test_play48h3_early_market_wage import _conserve, _run
from test_play48_13npc_post72_relay import _stats
from test_play47_closure_endurance import DAY, WORLD
import test_play38_multi_farm_couriers as east

HOUR = 3600
CHECKPOINTS = (24, 48, 72)
HANA_CONTRACT = "market-hana-one-original-farm-loaf"


def _split_bootstrap(db, *, initial_market_food, **options):
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
        farm_opening_food_wage=True, farm_initial_food_loaves=1,
        farm_bread_share_enabled=True,
    )


def _seed_split(path):
    with SQLiteEventStore(path) as db:
        east.seed_two_field_world(
            db, east_growth_seconds=DAY, east_grain_yield=12,
            initial_water=2, initial_market_food=3,
            market_wallets=True, hungry_market_buyers=True,
            cash_return=True, waged_harvest=True,
            harvest_wage_copper=2, bootstrap=_split_bootstrap,
        )
        start = db.load(WORLD)
        assert len(start.npcs) == 13
        assert (start.schema_version, start.rules_version) == (45, 62)
        assert start.resources["market"]["food"] == 2
        assert start.resources["farm"]["food"] == 1
        start = db.append(
            WORLD, "split:water-and-metabolism", start.revision,
            [
                DomainEvent("WaterSourceConfigured", None,
                            "real finite original water capacity", 0,
                            {"site_id": "well", "capacity": 8}),
                DomainEvent("MetabolismPolicyConfigured", None,
                            "identical actual normal hunger", 0,
                            {"hunger_seconds_per_point": 3600,
                             "activity_hunger_percent": 20}),
            ],
            bootstrap=True,
        )
        start = db.append(
            WORLD, "split:authentic-huda-one-hana-one", start.revision,
            [
                DomainEvent("CourierProvisionConfigured", None,
                            "one truly existing original farm-owned loaf for Huda", 0,
                            {"id": "farm-water-huda", "courier_id": "huda",
                             "payer_site": "farm", "units": 1,
                             "authorized_total_units": 3}),
                DomainEvent("CourierProvisionConfigured", None,
                            "one truly existing original market-owned loaf for Hana", 0,
                            {"id": HANA_CONTRACT, "courier_id": "hana",
                             "payer_site": "market", "units": 1}),
            ],
            bootstrap=True,
        )
        assert start.resources["farm"]["food"] == 0
        assert start.resources["market"]["food"] == 1
        assert start.resources["hana"]["food"] == 0
        assert start.resources["huda"]["food"] == 0
        assert start.courier_provisions["farm-water-huda"]["remaining"] == 1
        assert start.courier_provisions[HANA_CONTRACT]["remaining"] == 1
        assert sum(c["remaining"] for c in start.courier_provisions.values()) == 2
        assert audit_npc_economy(start)["copper_scope_complete"]
        assert audit_npc_economy(start)["copper_known_total"] == 12
        assert db.verify(WORLD).to_dict() == start.to_dict()
        return start


def _signed_food_count(state, worker):
    return sum(
        len(contract["payments"])
        for contract in state.courier_provisions.values()
        if contract["courier_id"] == worker
    )


def _report(state):
    before = state.to_dict()
    a = audit_food_access_barriers(state)
    m = audit_npc_economy(state)
    assert len(a["actors"]) == 13
    assert (state.schema_version, state.rules_version) == (45, 62)
    assert m["copper_scope_complete"] and m["copper_known_total"] == 12
    result = {
        "stats": _stats(state),
        "individual_hunger": {p["npc_id"]: p["hunger"] for p in a["actors"]},
        "paid_in_real_food_by_worker": {
            who: _signed_food_count(state, who) for who in ("hana", "huda")
        },
        "actually_consumed_meals_by_worker": {
            who: sum(x["npc_id"] == who for x in state.consumptions.values())
            for who in ("hana", "huda")
        },
        "market_actual_food": state.resources["market"]["food"],
        "market_actual_cash": state.resources["market"]["coin_copper"],
        "bakery_actual_cash": state.resources["bakery"]["coin_copper"],
        "bakery_actual_food": state.resources["bakery"]["food"],
        "original_employer_remaining_escrow": {
            c["courier_id"]: c["remaining"]
            for c in state.courier_provisions.values()
        },
    }
    assert state.to_dict() == before, "operator data cannot influence NPCs"
    return result


def compare():
    with TemporaryDirectory(prefix="play48-preserve-first-sale-") as root:
        paths = {
            "original_huda_two": Path(root) / "original-huda-two.sqlite",
            "split_one_each": Path(root) / "one-huda-one-hana.sqlite",
        }
        a = _seed_signed_share(
            paths["original_huda_two"], share=True,
            farm_refill_authority=True,
        )
        b = _seed_split(paths["split_one_each"])
        assert a.resources["market"]["food"] == b.resources["market"]["food"] == 1
        assert a.resources["farm"]["food"] == b.resources["farm"]["food"] == 0
        assert len(a.npcs) == len(b.npcs) == 13
        assert sum(c["remaining"] for c in a.courier_provisions.values()) == 2
        assert sum(c["remaining"] for c in b.courier_provisions.values()) == 2
        assert audit_npc_economy(a)["copper_known_total"] == 12
        assert audit_npc_economy(b)["copper_known_total"] == 12

        for hour in CHECKPOINTS:
            row = {"hour": hour}
            for variant, path in paths.items():
                state, _ = _run(
                    path, hour * HOUR, early=True,
                    hungry_woodcutter_work_enabled=True,
                    retry_known_supplier_enabled=True,
                    farm_sourced_wage_refill_enabled=True,
                    remember_unbought_stalls_enabled=True,
                )
                _conserve(state)
                with SQLiteEventStore(path) as db:
                    assert db.verify(WORLD).to_dict() == state.to_dict()
                    assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
                    assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
                row[variant] = _report(state)
            print("PLAY48_TRUE_13NPC_PRESERVE_FIRST_SALE_FOOD_WAGE_AB " +
                  json.dumps(row, sort_keys=True), flush=True)

        control = row["original_huda_two"]
        candidate = row["split_one_each"]
        stats_a, stats_b = control["stats"], candidate["stats"]
        print("PLAY48_PRESERVED_FIRST_SALE_72H_RESULT " + json.dumps({
            "same_13_people_and_original_3_food_12_copper": True,
            "same_saleable_first_market_loaf": True,
            "genesis_ownership_change":
                "one originally farm-escrowed Huda wage is instead a physically market-escrowed Hana wage",
            "original_engine_policy_flags_identical": True,
            "copper_created": False, "food_created": False,
            "baseline_at72": stats_a, "candidate_at72": stats_b,
            "deltas": {
                k: stats_b[k] - stats_a[k]
                for k in ("jobs", "wages", "food_sales",
                          "meals", "hunger_cap", "trades")
            },
            "delivery_deltas": {
                who: stats_b["deliveries"][who] - stats_a["deliveries"][who]
                for who in ("hana", "huda")
            },
            "food_payments": [
                control["paid_in_real_food_by_worker"],
                candidate["paid_in_real_food_by_worker"],
            ],
            "meals_by_courier": [
                control["actually_consumed_meals_by_worker"],
                candidate["actually_consumed_meals_by_worker"],
            ],
            "bakery_actual_copper_at72": [
                control["bakery_actual_cash"],
                candidate["bakery_actual_cash"],
            ],
            "release_no_go": True, "168h_recovery_claimed": False,
        }, sort_keys=True), flush=True)


if __name__ == "__main__":
    compare()
