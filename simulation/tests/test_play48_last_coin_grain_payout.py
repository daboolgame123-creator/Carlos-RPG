"""PLAY48: a bakery may actually pay the last coin of a signed grain invoice.

Only the prospective, authenticated grain-purchase pilot can do this. An
optional liquidity cushion is not a claim senior to real delivered crops.
"""
from carlos_sim.economic_diagnostics import audit_npc_economy
from test_play48_integrated_income import freight_fixture


def test_sole_real_bakery_coin_moves_to_source_only_after_grain(tmp_path):
    db, clock, sim, initial = freight_fixture(
        tmp_path / "last-copper.sqlite", grain_purchase=True,
        bakery_copper=1, hunger=20)
    with db:
        assert initial.resources["bakery"]["coin_copper"] == 1
        assert initial.resources["farm"]["coin_copper"] == 0
        s = sim.advance("freight", seconds=180, command_id="one-real-invoice",
                        expected_revision=initial.revision).state
        receipt = s.supply_circuits["huda"]["grain_purchase"]["receipts"][0]
        assert receipt["loaded_at"] is not None and receipt["received_at"] is not None
        assert s.resources["bakery"]["coin_copper"] == 0
        assert s.resources["farm"]["coin_copper"] == 1
        assert s.resources["huda"]["coin_copper"] == 0
        assert db.verify("freight").to_dict() == s.to_dict()
        clock.close_session("freight")


def test_two_actual_last_coin_invoices_fund_agreed_two_copper_harvest(tmp_path):
    db, clock, sim, start = freight_fixture(
        tmp_path / "earned-two-copper.sqlite", bakery_copper=2,
        grain_purchase=True, harvest_wage=True, hunger=20)
    with db:
        s = sim.advance("freight", seconds=4000, command_id="two-bakery-sales",
                        expected_revision=start.revision).state
        completed = [j for j in s.production_jobs.values()
                     if j["npc_id"] == "nora" and j["status"] == "completed"]
        assert len(completed) == 1
        assert completed[0]["work_wage"]["amount"] == 2
        receipt = s.supply_circuits["huda"]["grain_purchase"]["receipts"]
        assert sum(x["received_at"] is not None for x in receipt) == 2
        assert s.resources["farm"]["coin_copper"] == 0
        assert s.resources["bakery"]["coin_copper"] == 0
        assert s.resources["nora"]["coin_copper"] == 2
        assert s.resources["huda"]["coin_copper"] == 0
        assert db.verify("freight").to_dict() == s.to_dict()
        clock.close_session("freight")
