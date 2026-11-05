"""02-D seven-NPC disposable example: fund -> partial pay -> spend -> flee -> default.

No debt is created by speech alone. No legal enforcement or arbitrary penalties.
"""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from carlos_sim import (
    DomainEvent, SQLiteEventStore, TimeEngine, NPCLoanService,
    NPCMarketService, NPCMovementService,
)

PEOPLE = ("basim", "nora", "adel", "salma", "huda", "omar", "layla")


def e(kind, p):
    return DomainEvent(kind, None, "02-D synthetic economic village", 0, p)


def run() -> dict:
    with TemporaryDirectory() as directory, SQLiteEventStore(
            Path(directory) / "village.sqlite") as db:
        db.create_world("village")
        events = [
            e("LocationCreated", {"id": "village", "name": "Village"}),
            e("LocationCreated", {"id": "square", "name": "Square"}),
            e("RouteCreated", {
                "id": "village-square", "a": "village", "b": "square",
                "seconds": 50,
            }),
        ]
        for name in PEOPLE:
            events.extend([
                e("EntityCreated", {
                    "id": name, "name": name,
                    "location_id": "square" if name == "layla" else "village",
                    "controller": "npc",
                }),
                e("NPCConfigured", {
                    "npc_id": name, "role": "resident",
                    "needs": {"hunger": 10, "fatigue": 5, "safety": 0},
                    "goals": {"earn": 40, "explore": 10, "survive": 30},
                }),
            ])
            coins = 20 if name == "basim" else 5 if name == "layla" else 0
            bread = 2 if name == "huda" else 0
            for kind, qty in (("coin_copper", coins), ("bread", bread)):
                events.append(e("ResourceChanged", {
                    "owner_id": name, "resource": kind, "previous": None,
                    "current": qty, "source": "initialization",
                }))
        db.append("village", "genesis", 0, events, bootstrap=True)
        clock = TimeEngine(db)
        clock.open_session("village")
        loans = NPCLoanService(db, clock)
        market = NPCMarketService(db, clock)
        travel = NPCMovementService(db, clock)

        def rev():
            return db.load("village").revision

        def wait(sec, cid):
            return clock.advance(
                "village", seconds=sec, command_id=cid,
                expected_revision=rev()).state

        proposed = loans.propose(
            "village", "basim", "nora", "loan-01", 8, 120,
            expected_revision=rev()).state
        assert proposed.resources["basim"]["coin_copper"] == 20
        assert proposed.resources["nora"]["coin_copper"] == 0
        assert proposed.loan_contracts["loan-01"]["remaining"] is None
        funded = loans.accept("village", "nora", "loan-01",
                              expected_revision=rev()).state
        assert funded.resources["basim"]["coin_copper"] == 12
        assert funded.resources["nora"]["coin_copper"] == 8
        wait(60, "halfway")
        part = loans.repay("village", "nora", "loan-01",
                           "first-payment", 3, expected_revision=rev()).state
        assert part.loan_contracts["loan-01"]["remaining"] == 5

        market.post("village", "huda", "huda", "village", "bread-offer",
                    "bread", 1, "coin_copper", 2,
                    expected_revision=rev())
        bought = market.buy("village", "nora", "bread-trade", "bread-offer",
                            1, 2, expected_revision=rev()).state
        assert bought.resources["nora"]["coin_copper"] == 3
        assert bought.resources["nora"]["bread"] == 1

        travel.start("village", "nora", "village-square", "leave-village",
                     expected_revision=rev())
        wait(50, "arrive-square")
        overdue = wait(10, "due-date")
        assert overdue.time == 120
        assert overdue.entities["nora"]["location_id"] == "square"
        assert overdue.loan_contracts["loan-01"]["status"] == "overdue"
        assert overdue.loan_contracts["loan-01"]["remaining"] == 5
        assert overdue.resources["nora"]["coin_copper"] == 3
        assert db.verify("village").to_dict() == overdue.to_dict()

        # A physically owned bread unit can be sold in the square for two
        # genuine pre-seeded Layla coins. Meeting lender later permits payment.
        market.post("village", "nora", "nora", "square", "nora-bread",
                    "bread", 1, "coin_copper", 2,
                    expected_revision=rev())
        market.buy("village", "layla", "nora-sale", "nora-bread",
                   1, 2, expected_revision=rev())
        assert db.load("village").resources["nora"]["coin_copper"] == 5
        travel.start("village", "basim", "village-square", "lender-travel",
                     expected_revision=rev())
        wait(50, "lender-arrive")
        final = loans.repay("village", "nora", "loan-01",
                            "late-final", 5, expected_revision=rev()).state
        assert final.time == 170
        assert final.loan_contracts["loan-01"]["status"] == "paid"
        assert final.loan_contracts["loan-01"]["remaining"] == 0
        assert final.loan_contracts["loan-01"]["defaulted_at"] == 120
        assert final.loan_repayments["late-final"]["late"] is True
        assert sum(final.resources[n]["coin_copper"] for n in PEOPLE) == 25
        assert db.verify("village").to_dict() == final.to_dict()
        return {
            "npc_count": len(final.npcs),
            "principal_copper": 8,
            "partial_repayment_copper": 3,
            "copper_after_bread_purchase": 3,
            "debtor_escaped_to": "square",
            "default_time_seconds": 120,
            "outstanding_at_default_copper": 5,
            "later_real_earned_copper": 2,
            "settlement_time_seconds": 170,
            "final_outstanding_copper": 0,
            "recorded_default_preserved": 120,
            "total_copper_units_preserved": 25,
            "replay_verified": True,
            "note": "Explicit, actual copper funding/payments; never automatic forfeiture or minted credit.",
        }


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
