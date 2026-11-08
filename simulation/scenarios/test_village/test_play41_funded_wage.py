"""PLAY-41: signed local work wages, funded by the *actual* market coins.

No minted payroll and no teleportation: real bakery/field copper reaches the
field on the PLAY-40 courier return road, then is paid only to the real
employee for one completed, pre-priced, local harvest.
"""
from __future__ import annotations

import json
import pytest

from carlos_sim import DomainEvent, InvalidEvent, LivingWorldEngine, SQLiteEventStore, TimeEngine
from test_play38_multi_farm_couriers import (
    WORLD, EAST, COURIER, FARMER, seed_two_field_world,
)


def _audit(state):
    cash = sum(bal.get("coin_copper", 0) for bal in state.resources.values())
    wages = {
        job_id: job["work_wage"]
        for job_id, job in state.production_jobs.items()
        if "work_wage" in job
    }
    total_sales = sum(t["total_paid"] for t in state.market_trades.values())
    paid = sum(row["amount"] for row in wages.values())
    assert cash == 12
    assert paid == state.resources[FARMER]["coin_copper"]
    assert paid + sum(
        state.resources[who]["coin_copper"]
        for who in ("market", "bakery", EAST, COURIER)
    ) == total_sales
    for job_id, receipt in wages.items():
        job = state.production_jobs[job_id]
        assert job["status"] == "completed"
        assert job["npc_id"] == FARMER
        assert job["site_id"] == EAST
        assert receipt["amount"] == 1
        assert receipt["site_before"] == receipt["site_after"] + 1
        assert receipt["worker_after"] == receipt["worker_before"] + 1
        assert receipt["paid_at"] >= job["finished_at"]
    return {
        "time": state.time, "copper_total": cash,
        "customer_payments": total_sales,
        "market_coins": state.resources["market"]["coin_copper"],
        "bakery_coins": state.resources["bakery"]["coin_copper"],
        "field_coins": state.resources[EAST]["coin_copper"],
        "courier_coins": state.resources[COURIER]["coin_copper"],
        "farmer_coins": state.resources[FARMER]["coin_copper"],
        "wage_receipts": len(wages),
        "completed_harvests": sum(
            j["status"] == "completed" and j["recipe_id"] == "east-finite-harvest"
            for j in state.production_jobs.values()
        ),
    }


def _engine(db, clock):
    return LivingWorldEngine(
        db, clock, max_events_per_advance=5000,
        decision_cooldown=3600, navigation_enabled=True,
        routines_enabled=True, survival_enabled=True,
        consumption_enabled=True, supply_enabled=True,
        economic_enabled=True, adaptive_market_enabled=True,
        agriculture_enabled=True, economy_only_enabled=True,
    )


def test_harvest_worker_earns_only_after_completed_work_and_real_copper(tmp_path):
    with SQLiteEventStore(tmp_path / "funded-wages.sqlite") as db:
        seed_two_field_world(
            db, cash_return=True, waged_harvest=True,
            market_wallets=True, hungry_market_buyers=True,
            initial_market_food=3,
        )
        state = db.verify(WORLD)
        assert state.resources[FARMER]["coin_copper"] == 0
        assert state.production_recipes["east-finite-harvest"]["wage_coin"] == 1
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            engine = _engine(db, clock)
            timeline = [_audit(state)]
            for when in (300, 1200, 3600, 3900, 7200, 12000):
                current = db.load(WORLD)
                state = engine.advance(
                    WORLD, seconds=when-current.time,
                    command_id=f"play41:paid:{when}",
                    expected_revision=current.revision,
                ).state
                assert state.time == when
                timeline.append(_audit(state))
                assert state.to_dict() == db.verify(WORLD).to_dict()
                db.snapshot(WORLD)
                assert state.to_dict() == db.verify(WORLD).to_dict()
            assert timeline[-1]["completed_harvests"] >= 1
            assert timeline[-1]["wage_receipts"] >= 1
            assert timeline[-1]["farmer_coins"] >= 1
            assert timeline[-1]["copper_total"] == 12
            assert timeline[0]["farmer_coins"] == 0

            paid_job = next(k for k, job in state.production_jobs.items()
                            if "work_wage" in job)
            before = db.verify(WORLD).to_dict()
            forged = DomainEvent(
                "ProductionWagePaid", None, "attempt duplicate salary", state.time,
                {"job_id": paid_job, "amount": 1},
            )
            for cid, event, authorized in (
                ("duplicate-wage", forged, True),
                ("unauthorized-wage", forged, False),
                ("wrong-job-price", DomainEvent(
                    "ProductionWagePaid", None, "counterfeit wage amount", state.time,
                    {"job_id": paid_job, "amount": 5}), True),
                ("impersonated-worker", DomainEvent(
                    "ProductionWagePaid", FARMER, "worker prints own salary", state.time,
                    {"job_id": paid_job, "amount": 1}), True),
            ):
                with pytest.raises(InvalidEvent):
                    db.append(
                        WORLD, cid, db.load(WORLD).revision, [event],
                        production_authorized=authorized,
                    )
                assert db.verify(WORLD).to_dict() == before
            print("PLAY41_FUNDED_HARVEST_WAGES",
                  json.dumps(timeline, sort_keys=True))
        finally:
            clock.close_session(WORLD)


def test_harvest_wages_remain_unpaid_if_employer_has_no_copper(tmp_path):
    with SQLiteEventStore(tmp_path / "unfunded-wages.sqlite") as db:
        seed_two_field_world(
            db, cash_return=True, waged_harvest=True,
            market_wallets=True, initial_market_food=0,
        )
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            engine = _engine(db, clock)
            current = db.load(WORLD)
            state = engine.advance(
                WORLD, seconds=3900, command_id="play41:unfunded:3900",
                expected_revision=current.revision,
            ).state
            completed = [
                k for k, job in state.production_jobs.items()
                if job["status"] == "completed"
                and job["recipe_id"] == "east-finite-harvest"
            ]
            assert completed
            assert state.resources[EAST]["coin_copper"] == 0
            assert state.resources[FARMER]["coin_copper"] == 0
            assert all("work_wage" not in state.production_jobs[k] for k in completed)
            unpaid = DomainEvent("ProductionWagePaid", None,
                "unfunded attempt", state.time,
                {"job_id": completed[0], "amount": 1})
            with pytest.raises(InvalidEvent):
                db.append(WORLD, "play41:pay-with-zero", state.revision,
                          [unpaid], production_authorized=True)
            assert db.verify(WORLD).to_dict() == state.to_dict()
        finally:
            clock.close_session(WORLD)


@pytest.mark.parametrize("invalid", [None, True, 0, 2, "yes", []])
def test_wage_contract_is_explicit_and_cannot_be_conjured(tmp_path, invalid):
    with SQLiteEventStore(tmp_path / "bad-setup.sqlite") as db:
        with pytest.raises(ValueError, match="waged_harvest"):
            seed_two_field_world(
                db, cash_return=False, waged_harvest=invalid,
                market_wallets=True, initial_market_food=3,
            )
