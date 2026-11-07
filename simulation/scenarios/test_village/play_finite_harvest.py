"""PLAY-25: disposable seven-NPC finite field-to-bread economy.

Only the player advances time after bootstrap. Nora independently harvests
initially ripe crop at the communal site; Basim bakes; Salma offers; Adel may
buy. No crop regrowth, no transport, and no NPC receives scripted job orders.
"""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from carlos_sim import DomainEvent, LivingWorldEngine, PlayerGateway
from carlos_sim.resumable_play import ResumableTestSession

WORLD = "play25-finite-field"
PLAYER = "carlos"
PEOPLE = (
    ("basim", "baker", 20, 20),
    ("salma", "merchant", 20, 10),
    ("adel", "guard", 80, 10),
    ("nora", "farmer", 20, 5),
    ("huda", "courier", 20, 30),
    ("omar", "explorer", 20, 10),
    ("layla", "resident", 20, 10),
)


def seed_finite_field(store, *, crop: int = 1, buyer_copper: int = 2,
                      sickle: int = 1, farmer_site: str = "square",
                      baker_site: str = "square",
                      farmer_shift: tuple[int, int] = (0, 600),
                      baker_shift: tuple[int, int] = (0, 600),
                      with_market: bool = True) -> None:
    """All resources explicitly owned and finite at time zero; never refill."""
    if type(crop) is not int or crop not in (0, 1, 2):
        raise ValueError("crop must be 0, 1, or 2")
    if type(buyer_copper) is not int or not 0 <= buyer_copper <= 4:
        raise ValueError("buyer copper must be 0..4")
    if type(sickle) is not int or sickle not in (0, 1):
        raise ValueError("sickle must be 0 or 1")
    if farmer_site not in ("square", "home") or baker_site not in ("square", "home"):
        raise ValueError("worker sites must be real test locations")
    store.create_world(WORLD)
    def e(kind, payload):
        return DomainEvent(kind, None, "trusted PLAY-25 test bootstrap", 0, payload)

    events = [
        e("LocationCreated", {"id": "square", "name": "Communal village worksite"}),
        e("LocationCreated", {"id": "home", "name": "Home"}),
        e("EntityCreated", {"id": PLAYER, "name": "Carlos",
                            "location_id": "home", "controller": "player"}),
    ]
    for who, role, hunger, fatigue in PEOPLE:
        site = (farmer_site if who == "nora"
                else baker_site if who == "basim" else "square")
        events.extend((
            e("EntityCreated", {"id": who, "name": who.capitalize(),
                                "location_id": site, "controller": "npc"}),
            e("NPCConfigured", {"npc_id": who, "role": role,
                                "needs": {"hunger": hunger, "fatigue": fatigue, "safety": 0},
                                "goals": {"earn": 10, "explore": 10, "survive": 30}}),
        ))
        for item in ("labor_units", "investigation_attempts", "food"):
            events.append(e("ResourceChanged", {
                "owner_id": who, "resource": item,
                "previous": None, "current": 0, "source": "initialization",
            }))

    for owner, item, amount in (
        ("square", "crop_ready", crop),
        ("square", "sickle", sickle),
        ("square", "grain", 0),
        ("square", "oven", 1),
        ("square", "food", 0),
        ("square", "coin_copper", 0),
        ("adel", "coin_copper", buyer_copper),
        (PLAYER, "coin_copper", 10),
    ):
        events.append(e("ResourceChanged", {
            "owner_id": owner, "resource": item,
            "previous": None, "current": amount, "source": "initialization",
        }))

    for who, shift in (("nora", farmer_shift), ("basim", baker_shift)):
        events.append(e("NPCRoutineConfigured", {
            "npc_id": who, "home_id": "home", "workplace_id": "square",
            "work_start": shift[0], "work_end": shift[1],
        }))
    events.extend((
        e("ProductionRecipeConfigured", {
            "id": "finite-harvest", "site_id": "square", "role": "farmer",
            "input_resource": "crop_ready", "input_amount": 1,
            "output_resource": "grain", "output_amount": 1,
            "tool_resource": "sickle", "duration_seconds": 60,
        }),
        e("ProductionRecipeConfigured", {
            "id": "grain-to-bread", "site_id": "square", "role": "baker",
            "input_resource": "grain", "input_amount": 1,
            "output_resource": "food", "output_amount": 1,
            "tool_resource": "oven", "duration_seconds": 90,
        }),
    ))
    if with_market:
        events.append(e("MarketStallConfigured", {
            "site_id": "square", "keeper_id": "salma",
        }))
    store.append(WORLD, "seed-play25", 0, events, bootstrap=True)


def physical_totals(state) -> dict[str, int]:
    """Conservation of crop equivalents and copper, including eaten food."""
    stock = state.resources
    edible = (stock["square"]["crop_ready"] + stock["square"]["grain"]
              + stock["square"]["food"]
              + sum(stock[who]["food"] for who, *_ in PEOPLE)
              + sum(meal["quantity"] for meal in state.consumptions.values()))
    # The production reducer consumes inputs at job START and delivers output
    # at its scheduled completion. Count physically reserved in-flight stock.
    edible += sum(state.production_recipes[job["recipe_id"]]["input_amount"]
                  for job in state.production_jobs.values()
                  if job["status"] == "running")
    copper = (stock["square"]["coin_copper"] + stock["adel"]["coin_copper"]
              + stock[PLAYER]["coin_copper"])
    return {"crop_food_equivalent": edible, "copper": copper}


def run_finite_field(path: str | Path, *, crop: int = 1,
                     buyer_copper: int = 2, sickle: int = 1,
                     with_market: bool = True) -> dict:
    def setup(store):
        seed_finite_field(store, crop=crop, buyer_copper=buyer_copper,
                          sickle=sickle, with_market=with_market)

    with ResumableTestSession.create(
        path, WORLD, PLAYER, setup, disposable_test=True,
    ) as session:
        db, clock = session.store, session.clock
        session.bind_gateway(PlayerGateway(
            db, clock, world_id=WORLD, player_id=PLAYER,
            engine=LivingWorldEngine(
                db, clock, economic_enabled=True,
                consumption_enabled=True, survival_enabled=True,
            ),
        ))
        initial = db.load(WORLD)
        assert len(initial.npcs) == len(PEOPLE) == 7
        assert physical_totals(initial) == {
            "crop_food_equivalent": crop, "copper": buyer_copper + 10,
        }
        # Explicit user time is the ONLY command after setup.
        for moment, seconds in ((60, 60), (150, 90), (300, 150)):
            answer = session.gateway.wait(
                seconds, command_id=f"play25-wait-{moment}",
                expected_revision=db.load(WORLD).revision,
            )
            assert answer.time == moment
            assert physical_totals(db.load(WORLD)) == physical_totals(initial)
        final = db.load(WORLD)
        assert db.verify(WORLD).to_dict() == final.to_dict()
        db.snapshot(WORLD)
        assert db.verify(WORLD).to_dict() == final.to_dict()
        player_view = session.handoff()
        rendered = json.dumps(player_view, ensure_ascii=False)
        for secret in ('"production_jobs"', '"market_trades"', '"npcs"',
                       '"consumptions"', '"npc_routines"', '"crop_ready"'):
            assert secret not in rendered

        harvest_jobs = [job for job in final.production_jobs.values()
                        if job["recipe_id"] == "finite-harvest"]
        bakery_jobs = [job for job in final.production_jobs.values()
                       if job["recipe_id"] == "grain-to-bread"]
        done = lambda jobs: sum(job["status"] == "completed" for job in jobs)
        audit = {
            "npcs": len(final.npcs),
            "harvests": done(harvest_jobs),
            "bakes": done(bakery_jobs),
            "offers": len(final.market_offers),
            "trades": len(final.market_trades),
            "buyers": sorted(trade["buyer_id"]
                             for trade in final.market_trades.values()),
            "meals": len(final.consumptions),
            "initial_crop": crop,
            "remaining_crop": final.resources["square"]["crop_ready"],
            "final_totals": physical_totals(final),
            "player_commanded_npc_actions": 0,
        }
        for bake in bakery_jobs:
            assert any(job["due"] <= bake["started_at"] for job in harvest_jobs)
        for trade in final.market_trades.values():
            assert any(job["due"] <= trade["executed_at"] for job in bakery_jobs)
        assert audit["harvests"] <= crop
        assert audit["bakes"] <= audit["harvests"]
        return {
            "format": "carlos-play25-finite-harvest-v1",
            "canonical_story": False,
            "disposable_test": True,
            "logical_seconds": 300,
            "player_view": player_view,
            "private_test_audit_only": audit,
            "verified_replay": True,
        }


def main() -> None:
    with TemporaryDirectory(prefix="carlos-play25-field-") as directory:
        cases = {
            "funded": run_finite_field(Path(directory) / "funded.sqlite"),
            "unfunded": run_finite_field(Path(directory) / "poor.sqlite", buyer_copper=0),
            "empty_field": run_finite_field(Path(directory) / "no-crop.sqlite", crop=0),
            "no_sickle": run_finite_field(Path(directory) / "no-sickle.sqlite", sickle=0),
        }
    for title, case in cases.items():
        audit = case["private_test_audit_only"]
        print(f"{title}: 7 NPC at t=300, harvests={audit['harvests']}, "
              f"bread={audit['bakes']}, offers={audit['offers']}, "
              f"trades={audit['trades']}, copper={audit['final_totals']['copper']}")
    print("PLAY25_JSON=" + json.dumps(cases, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
