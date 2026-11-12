"""READ-ONLY operator audit: why existing physically stocked market bread remains unsold.

The 13-person market-funded Hana one-loaf experiment removes the single
original SALEABLE bread at time zero and places it into signed, employer-owned
courier wage escrow. This script investigates any resulting zero-sales loop
without changing engine rules, NPC beliefs, market prices, roads or supplies.
"""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from carlos_sim import SQLiteEventStore
from carlos_sim.economic_autonomy import (
    choose_local_food_offer, choose_local_food_purchase, _free,
)
from carlos_sim.market import _present
from carlos_sim.food_access_diagnostics import audit_food_access_barriers
from play48_hana_market_real_wage_ab import _seed
from test_play48h3_early_market_wage import _run, _conserve
from test_play48_13npc_post72_relay import _stats
from test_play47_closure_endurance import WORLD

HOUR = 3600


def audit(state):
    before = state.to_dict()
    assert len(state.npcs) == 13
    assert (state.schema_version, state.rules_version) == (45, 62)
    assert sum(v.get("coin_copper", 0) for v in state.resources.values()) == 12
    keeper = state.market_stalls["market"]["keeper_id"]
    entry = state.entities[keeper]
    chosen_quote = choose_local_food_offer(state, keeper)
    r = state.resources["market"]
    all_listings = []
    for offer_id, offer in sorted(state.market_offers.items()):
        if offer["site_id"] != "market" or offer["resource"] != "food":
            continue
        all_listings.append({
            "id": offer_id, "status": offer["status"],
            "seller": offer["seller_id"],
            "stock_owner": offer["stock_owner_id"],
            "posted_at": offer["posted_at"],
            "remaining": offer["remaining"],
            "price": offer["unit_price"],
        })
    buyers = []
    for who, npc in sorted(state.npcs.items()):
        here = state.entities[who]["location_id"]
        if here != "market":
            continue
        local_purchase = choose_local_food_purchase(state, who)
        buyers.append({
            "npc": who, "role": npc["role"],
            "hunger": npc["needs"]["hunger"],
            "food": state.resources.get(who, {}).get("food"),
            "copper_slot": state.resources.get(who, {}).get("coin_copper"),
            "in_courier_consignment": who in state.supply_circuits,
            "physically_idle": _free(state, who),
            "next_decision_at": npc["next_decision_at"],
            "can_buy_local_quote": local_purchase is not None,
        })
    root = audit_food_access_barriers(state)
    value = {
        "hour": state.time // HOUR, "time": state.time,
        "stats": _stats(state),
        "market_real_site_food": r["food"],
        "market_cash": r.get("coin_copper"),
        "market_signed_escrow_food": sum(
            c["remaining"] for c in state.courier_provisions.values()
            if c["payer_site"] == "market"
        ),
        "market_keeper": keeper,
        "keeper_location": entry["location_id"],
        "keeper_physically_free": _free(state, keeper),
        "keeper_physically_present": _present(state.to_dict(), keeper, "market"),
        "new_local_food_quote_eligible": chosen_quote is not None,
        "new_local_food_quote_quantity": (
            chosen_quote.quantity if chosen_quote is not None else None
        ),
        "market_all_current_food_offers": all_listings,
        "people_physically_at_market": buyers,
        "locally_affordable_buyer_count": sum(
            x["locally_affordable_now"] for x in root["actors"]
            if x["location"] == "market"
        ),
    }
    assert state.to_dict() == before
    return value


def main():
    with TemporaryDirectory(prefix="play48-market-zero-opening-") as temp:
        path = Path(temp) / "signed-hana-from-original-market.sqlite"
        initial = _seed(path, market_hana_signed=True)
        assert initial.resources["market"]["food"] == 0
        print("PLAY48_ZERO_MARKET_STALL_QUOTE_GATES " +
              json.dumps(audit(initial), sort_keys=True), flush=True)
        for hour in (24, 36, 48):
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
            print("PLAY48_ZERO_MARKET_STALL_QUOTE_GATES " +
                  json.dumps(audit(state), sort_keys=True), flush=True)
        print("PLAY48_MARKET_STALL_READONLY_DIAG_DONE_NOT_APPROVAL", flush=True)


if __name__ == "__main__":
    main()
