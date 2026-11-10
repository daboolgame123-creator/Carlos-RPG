"""PLAY-48H0: read-only contract preflight on the ORIGINAL thirteen-person world.

This deliberately does not pay a courier, reserve food, alter a controller,
bootstrap extra stock, or claim economic recovery. Event seq is the only
available immutable, uniquely attributable proof of physical deliveries.
"""
import json

from carlos_sim import SQLiteEventStore
from carlos_sim.economic_diagnostics import audit_npc_economy
from test_play47_closure_endurance import _seed, _day, _reading, DAY, WORLD


def _verified_food_service_events(db):
    rows = db.db.execute(
        """SELECT e.seq, e.payload, c.supply_authorized
           FROM events AS e JOIN commands AS c
             ON e.world_id=c.world_id AND e.command_id=c.command_id
           WHERE e.world_id=? ORDER BY e.seq""", (WORLD,)
    ).fetchall()
    receipts = []
    for seq, raw, supply_authorized in rows:
        event = json.loads(raw)
        if event["event_type"] != "SupplyCargoDelivered" or event["data"]["resource"] != "food":
            continue
        who = event["data"]["courier_id"]
        assert supply_authorized == 1
        assert event["actor_id"] == who
        assert who in ("huda", "hana")
        receipts.append({"revision": seq, "courier": who, "delivered_at": event["time"]})
    assert len(set(x["revision"] for x in receipts)) == len(receipts)
    return receipts


def test_real_thirteen_npc_preventive_contract_funding_and_service_evidence(tmp_path):
    path = tmp_path / "genuine-13npc-preventive-preflight.sqlite"
    initial = _seed(path)
    assert len(initial.npcs) == 13
    assert initial.resources["market"]["food"] == 3
    assert initial.schema_version == 43 and initial.rules_version == 58
    assert audit_npc_economy(initial)["copper_known_total"] == 12
    # A hypothetical two-ration escrow MUST subtract from this finite stock;
    # the present unmodified market has no such reservation.
    assert initial.resources["market"]["food"] - 2 == 1
    assert all("provision_contract" not in rec for rec in initial.supply_circuits.values())

    report = []
    for day in range(1, 4):
        current = _day(path, day * DAY, rain=True)
        audit = audit_npc_economy(current)
        assert audit["copper_scope_complete"]
        assert audit["copper_known_total"] == 12
        _reading(current)
        report.append({
            "day": day, "market_site_owned_food": current.resources["market"]["food"],
            "huda_hunger": current.npcs["huda"]["needs"]["hunger"],
            "hana_hunger": current.npcs["hana"]["needs"]["hunger"],
            "huda_deliveries": current.supply_circuits["huda"]["deliveries"],
            "hana_deliveries": current.supply_circuits["hana"]["deliveries"],
            "production_wages": audit["wage_receipts"],
        })

    with SQLiteEventStore(path) as db:
        receipts = _verified_food_service_events(db)
        persisted = db.load(WORLD)
        assert db.verify(WORLD).to_dict() == persisted.to_dict()
        assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []

    assert receipts, "No real market-food delivery exists to support the proposed wage"
    assert all(0 <= rec["delivered_at"] <= 3 * DAY for rec in receipts)
    # Having performed a service does not confer self-awarded payment rights:
    # the existing 42/57 ledger has neither a signed market wage agreement
    # nor a service-specific, once-only entitlement for either courier.
    assert all("provision_contract" not in rec for rec in persisted.supply_circuits.values())
    assert persisted.resources["huda"]["coin_copper"] == 0
    assert persisted.resources["hana"]["coin_copper"] == 0
    assert persisted.resources["market"]["food"] == 5
    assert persisted.npcs["huda"]["needs"]["hunger"] == 100
    assert persisted.npcs["hana"]["needs"]["hunger"] == 100
    print("PLAY48H_PREVENTIVE_PREFLIGHT", json.dumps({
        "initial_market_food": 3,
        "hypothetical_two_loaf_escrow_remaining_market_stock": 1,
        "actual_physical_food_delivery_receipts": receipts,
        "daily_snapshots": report,
        "courier_wage_contract_present": False,
        "automatic_provisioning_performed": False,
        "recovery_claim": False,
    }, sort_keys=True))
