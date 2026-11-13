"""PLAY48 HARD RELEASE GATE: truly 13NPC 96h and 168h, not green-only checks.

Uses source-authenticated time-zero contingent food-service contracts, merchant
purchased two genuine portions, original 12 copper, 13 people, two genuine
farms, wild ecology finite16 original lots, and real roads. The test declares
one fixed PREDETERMINED EXTERNAL PHYSICAL RAIN input: 2 water units at
each day boundary until day six (no adaptive relief based on hungry residents).
Rain is NOT autonomous weather; every unit is a separately attested source
event under the existing dedicated hydrology authority and well capacity,
included in exact mass conservation. This *wet-season counterfactual* does
not establish default no-weather world endurance.

This assertion must FAIL / red CI if all-person nutrition and post72 real
production/delivery/sales/income cannot recover. Do not weaken thresholds to
get a green CI. No simulated market action/meal may be manually emitted.
"""
from __future__ import annotations

import json

from carlos_sim import SQLiteEventStore, TimeEngine
from carlos_sim.hydrology import FiniteWaterService
from carlos_sim.economic_diagnostics import audit_npc_economy
from test_play38_multi_farm_couriers import WORLD
from test_play48_real_watch_income_24h import engine, HOUR
from test_play48_deferred_courier_market_income import signed_genesis
from test_play48_finite_hunt_fish_roads import conserve_diverse
from test_play48_peddler_24h_diagnostic import measures

DAY = 24 * HOUR
CHECKPOINTS = (6,12,24,30,36,48,72,96,120,144,168)
ATTESTED_DAILY_RAIN_UNITS = 2
RAIN_DAYS = frozenset((1,2,3,4,5,6))


def _report(state):
    m = measures(state)
    m["owned_food_by_worker"] = {
        who: state.resources[who].get("food", 0) for who in sorted(state.npcs)
    }
    m["hunger_by_worker"] = {
        who: npc["needs"]["hunger"] for who,npc in sorted(state.npcs.items())
    }
    m["individually_consumed_meals"] = {
        who: sum(meal["npc_id"] == who for meal in state.consumptions.values())
        for who in sorted(state.npcs)
    }
    m["cash_owners"] = {
        k: amount
        for k,amount in audit_npc_economy(state)["copper_known_by_owner"].items()
        if amount > 0
    }
    m["water_rain_units_attested"] = (
        state.hydrology_sources["well"]["received_total"]
    )
    m["post72_jobs"] = sum(
        job["status"] == "completed"
        and job.get("completed_at", 0) > 72*HOUR
        for job in state.production_jobs.values()
    )
    m["post72_food_trades"] = sum(
        t["resource"] == "food" and t["executed_at"] > 72*HOUR
        for t in state.market_trades.values()
    )
    m["post72_meals"] = sum(
        meal["consumed_at"] > 72*HOUR for meal in state.consumptions.values()
    )
    m["post72_courier_wage_receipts"] = sum(
        receipt["paid_at"] > 72*HOUR
        for contract in state.courier_provisions.values()
        for receipt in contract["payments"]
    )
    return m


def test_exact_original_thirteen_real_wet_season_96_and_168_hour_release_gate(tmp_path):
    path = tmp_path / "no-fake-rescue-six-rain-attestations-168h.sqlite"
    start = signed_genesis(path)
    assert len(start.npcs) == 13
    assert audit_npc_economy(start)["copper_known_total"] == 12
    records = []
    with SQLiteEventStore(path) as db:
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            runner = engine(db, clock, reserve_trader_meal=True,
                            deferred_market_courier_wage=True)
            water_service = FiniteWaterService(db, clock)
            for hour in CHECKPOINTS:
                current = db.verify(WORLD)
                state = runner.advance(
                    WORLD, seconds=hour*HOUR-current.time,
                    command_id=f"real-external-wet-season-checkpoint:{hour}",
                    expected_revision=current.revision,
                ).state
                assert state.time == hour*HOUR
                conserve_diverse(state)
                assert len(state.npcs) == 13
                cash = audit_npc_economy(state)
                assert cash["copper_scope_complete"]
                assert cash["copper_known_total"] == 12
                assert db.verify(WORLD).to_dict() == state.to_dict()
                assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
                assert not db.db.execute("PRAGMA foreign_key_check").fetchall()
                row = _report(state)
                records.append(row)
                print("PLAY48_REAL_WET_SEASON_168H_MASS_BALANCED " +
                      json.dumps(row,sort_keys=True),flush=True)
                day = hour//24
                if hour%24==0 and day in RAIN_DAYS:
                    # THIS is an explicit physical/external rain measurement,
                    # precommitted from day1 irrespective of NPC needs.
                    observed = water_service.record(
                        WORLD,"well",f"fixed-day{day}-physical-rain",
                        ATTESTED_DAILY_RAIN_UNITS,
                        command_id=f"attested-dry-wet-input:{day}",
                        expected_revision=state.revision,
                    ).state
                    conserve_diverse(observed)
                    assert db.verify(WORLD).to_dict() == observed.to_dict()
            final = db.verify(WORLD)
            assert final.time == 168*HOUR
            assert final.hydrology_sources["well"]["received_total"] == (
                len(RAIN_DAYS)*ATTESTED_DAILY_RAIN_UNITS
            )
            print("PLAY48_96_168_EXPLICIT_ACCEPTANCE_GATES " +
                  json.dumps({
                    "at96":next(v for v in records if v["hour"]==96),
                    "at168":records[-1],
                    "recovered":(
                        all(v["hunger100"] == 0
                            for v in records if v["hour"]>=96)
                        and records[-1]["post72_jobs"] > 0
                        and records[-1]["post72_meals"] > 0
                        and records[-1]["post72_food_trades"] > 0
                        and records[-1]["post72_courier_wage_receipts"] > 0
                        and records[-1]["courier_deliveries"]["hana"] >
                            next(v for v in records if v["hour"]==72)["courier_deliveries"]["hana"]
                        and records[-1]["courier_deliveries"]["huda"] >
                            next(v for v in records if v["hour"]==72)["courier_deliveries"]["huda"]
                    ),
                },sort_keys=True),flush=True)
            assert all(v["hunger100"] == 0
                       for v in records if v["hour"]>=96), (
                "RELEASE_NO_GO: at least one original NPC still reaches hunger100 at 96-168h"
            )
            assert records[-1]["post72_jobs"] > 0, (
                "RELEASE_NO_GO: new real production did not persist beyond 72h"
            )
            assert records[-1]["post72_food_trades"] > 0, (
                "RELEASE_NO_GO: food sales did not persist beyond 72h"
            )
            assert records[-1]["post72_meals"] > 0, (
                "RELEASE_NO_GO: NPC meals did not persist beyond 72h"
            )
            assert records[-1]["post72_courier_wage_receipts"] > 0, (
                "RELEASE_NO_GO: not a single real delivery wage beyond 72h"
            )
            original = next(v for v in records if v["hour"]==72)
            for who in ("hana","huda"):
                assert (records[-1]["courier_deliveries"][who] >
                        original["courier_deliveries"][who]), (
                    f"RELEASE_NO_GO: courier {who} failed genuine post72 deliveries"
                )
        finally:
            clock.close_session(WORLD)
