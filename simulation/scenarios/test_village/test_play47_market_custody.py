"""Local quote probes: seller identity does not change payment ownership."""
import pytest

from carlos_sim import DomainEvent, SQLiteEventStore, WorldState
from carlos_sim.compound_professional_trade import choose_compound_purchase
from carlos_sim.multi_professional_trade import choose_local_material_purchase
from carlos_sim.market import post_offer, execute_trade
from carlos_sim.supply import validate_supply_circuits
from test_play47_joined_professions import _joined_bootstrap
from play_physical_supply import WORLD


@pytest.mark.parametrize("compound", [False, True])
def test_material_buyer_skips_personal_courier_quote_but_can_pay_the_site(tmp_path, compound):
    with SQLiteEventStore(tmp_path / "material-custody.sqlite") as db:
        raw = _joined_bootstrap(db).to_dict()
    # Isolated local selector/reducer boundary, not an autonomous travel claim.
    raw["entities"]["huda"]["location_id"] = "bakery"
    raw["supply_circuits"]["huda"]["index"] = 2
    raw["entities"]["smith"]["location_id"] = "bakery"
    raw["market_stalls"]["bakery"] = {"keeper_id": "huda"}
    raw["resources"]["iron_mine"]["iron_ore"] -= 1
    raw["resources"]["huda"]["iron_ore"] = 1
    if not compound:
        rec = raw["production_recipes"]["iron-plus-fuel"]
        rec.pop("inputs")
        rec.update(input_resource="iron_ore", input_amount=1)
    choose = choose_compound_purchase if compound else choose_local_material_purchase
    validate_supply_circuits(raw)

    def offer(ident, owner):
        post_offer(raw, DomainEvent("MarketOfferPosted", "huda", "visible ore", 0, {
            "id": ident, "seller_id": "huda", "stock_owner_id": owner,
            "site_id": "bakery", "resource": "iron_ore", "quantity": 1,
            "payment_resource": "coin_copper", "unit_price": 1,
        }), market_authorized=True)

    offer("personal-ore", "huda")
    assert choose(WorldState.from_dict(raw), "smith") is None
    # The same physical seller may steward site stock. Money then belongs to
    # the site, so settlement no longer pollutes the courier's custody slot.
    raw["resources"]["huda"]["iron_ore"] -= 1
    raw["resources"]["bakery"]["iron_ore"] = 1
    offer("site-ore", "bakery")
    purchase = choose(WorldState.from_dict(raw), "smith")
    assert purchase is not None and purchase.offer_id == "site-ore"
    execute_trade(raw, DomainEvent("MarketTradeExecuted", "smith", "local ore", 0, {
        "id": "site-purchase", "offer_id": "site-ore", "buyer_id": "smith",
        "quantity": 1, "expected_unit_price": 1,
    }), market_authorized=True)
    assert raw["resources"]["huda"]["coin_copper"] == 0
    assert raw["resources"]["bakery"]["coin_copper"] == 1
    assert raw["resources"]["smith"]["iron_ore"] == 1
    assert sum(v.get("coin_copper", 0) for v in raw["resources"].values()) == 12
    validate_supply_circuits(raw)
