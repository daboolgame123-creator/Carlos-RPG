"""PLAY-26: two independently planted seasons, seven NPCs, three logical days.

Explicit human waits are the ONLY runtime player actions. Economy-only mode
skips unrelated generic NPC activities and survival deterioration; this is a
bounded agricultural/economic endurance test, not proof of starvation survival.
"""
from __future__ import annotations
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from carlos_sim import DomainEvent, LivingWorldEngine, PlayerGateway
from carlos_sim.resumable_play import ResumableTestSession
from play_finite_harvest import seed_finite_field, WORLD, PLAYER, PEOPLE

DAY = 86400
TARGET = 2 * DAY + 500


def setup_planted_world(store, *, seed: int = 1, water: int = 2,
                        hoe: int = 1, sickle: int = 1, copper: int = 2,
                        farmer_shift: tuple[int, int] = (0, 600)):
    if type(seed) is not int or seed not in (0, 1):
        raise ValueError("seed must be zero or one")
    if type(water) is not int or water not in (0, 1, 2):
        raise ValueError("water is a finite 0..2 initial test stock")
    if type(hoe) is not int or hoe not in (0, 1):
        raise ValueError("hoe must be zero or one")
    seed_finite_field(store, crop=0, buyer_copper=copper, sickle=sickle,
                      farmer_shift=farmer_shift)
    def e(kind, fields):
        return DomainEvent(kind, None, "trusted PLAY-26 finite farm setup", 0, fields)
    events = [
        *[e("ResourceChanged", {
            "owner_id": "square", "resource": name, "previous": None,
            "current": amount, "source": "initialization",
        }) for name, amount in (
            ("seed", seed), ("crop_seeded", 0), ("water", water), ("hoe", hoe)
        )],
        e("ProductionRecipeConfigured", {
            "id": "seed-planting", "site_id": "square", "role": "farmer",
            "input_resource": "seed", "input_amount": 1,
            "output_resource": "crop_seeded", "output_amount": 1,
            "tool_resource": "hoe", "duration_seconds": 60,
        }),
        e("FarmPlotConfigured", {
            "site_id": "square", "growth_seconds": DAY, "capacity": 1,
        }),
    ]
    store.append(WORLD, "play26-seed-water-plot", store.load(WORLD).revision,
                 events, bootstrap=True)


def conserved_audit(state, *, initial_seed: int, initial_water: int,
                    initial_copper: int):
    stock = state.resources["square"]
    plot = state.farm_plots["square"]
    growing = int(plot["status"] == "growing")
    pending_plant = sum(
        1 for job in state.production_jobs.values()
        if job["status"] == "running"
        and state.production_recipes[job["recipe_id"]]["input_resource"] == "seed"
    )
    # The seed either exists, is physically inside the planting job,
    # is the completed seedling, or is inside a growing plant. Maturity
    # returns one biological seed; it cannot emerge elsewhere.
    assert stock["seed"] + stock["crop_seeded"] + pending_plant + growing == initial_seed
    assert stock["water"] + plot["matured"] + growing == initial_water
    outstanding = sum(
        state.production_recipes[j["recipe_id"]]["input_amount"]
        for j in state.production_jobs.values()
        if j["status"] == "running"
        and state.production_recipes[j["recipe_id"]]["input_resource"] in ("crop_ready", "grain")
    )
    eaten = sum(m["quantity"] for m in state.consumptions.values())
    food_eq = (stock["crop_ready"] + stock["grain"] + stock["food"] + outstanding
               + eaten + sum(state.resources[who]["food"] for who, *_ in PEOPLE))
    assert food_eq == plot["matured"]
    copper = (stock["coin_copper"] + state.resources["adel"]["coin_copper"]
              + state.resources[PLAYER]["coin_copper"])
    assert copper == initial_copper
    return {
        "grown": plot["matured"], "growing": growing,
        "remaining_water": stock["water"], "remaining_seed": stock["seed"],
        "food_equivalent": food_eq, "copper": copper,
    }


def run_planted_village(path: str | Path, *, seed: int = 1,
                        water: int = 2, hoe: int = 1, sickle: int = 1,
                        copper: int = 2) -> dict:
    def setup(store):
        setup_planted_world(store, seed=seed, water=water, hoe=hoe,
                            sickle=sickle, copper=copper)

    with ResumableTestSession.create(
        path, WORLD, PLAYER, setup, disposable_test=True,
    ) as session:
        db, clock = session.store, session.clock
        session.bind_gateway(PlayerGateway(
            db, clock, world_id=WORLD, player_id=PLAYER,
            engine=LivingWorldEngine(
                db, clock, economic_enabled=True, agriculture_enabled=True,
                economy_only_enabled=True, consumption_enabled=True,
            ),
        ))
        start = db.load(WORLD)
        assert len(start.npcs) == len(PEOPLE) == 7
        assert start.resources["square"]["grain"] == 0
        assert start.resources["square"]["crop_ready"] == 0
        assert conserved_audit(
            start, initial_seed=seed, initial_water=water,
            initial_copper=10 + copper,
        )["grown"] == 0

        for t in (60, DAY + 60, DAY + 120, DAY + 210,
                  2 * DAY + 180, TARGET):
            delta = t - db.load(WORLD).time
            answer = session.gateway.wait(
                delta, command_id=f"play26-wait-{t}",
                expected_revision=db.load(WORLD).revision,
            )
            assert answer.time == t
            state = db.load(WORLD)
            conserved_audit(state, initial_seed=seed, initial_water=water,
                            initial_copper=10 + copper)
        state = db.load(WORLD)
        audit = conserved_audit(state, initial_seed=seed, initial_water=water,
                                initial_copper=10 + copper)
        audit.update({
            "npcs": len(state.npcs),
            "harvests": sum(j["status"] == "completed" and
                            j["recipe_id"] == "finite-harvest"
                            for j in state.production_jobs.values()),
            "plantings": sum(j["status"] == "completed" and
                             j["recipe_id"] == "seed-planting"
                             for j in state.production_jobs.values()),
            "bakes": sum(j["status"] == "completed" and
                         j["recipe_id"] == "grain-to-bread"
                         for j in state.production_jobs.values()),
            "trades": len(state.market_trades),
            "meals": len(state.consumptions),
            "player_issued_npc_orders": 0,
        })
        assert audit["grown"] <= water
        assert audit["harvests"] <= audit["grown"]
        assert audit["bakes"] <= audit["harvests"]
        assert db.verify(WORLD).to_dict() == state.to_dict()
        db.snapshot(WORLD)
        assert db.verify(WORLD).to_dict() == state.to_dict()
        handoff = session.handoff()
        rendered = json.dumps(handoff, ensure_ascii=False)
        for forbidden in ('"farm_plots"', '"production_jobs"', '"market_trades"',
                          '"npcs"', '"water"', '"seed"'):
            assert forbidden not in rendered
        return {
            "format": "carlos-play26-true-planted-finite-season-v1",
            "logical_seconds": TARGET, "disposable_test": True,
            "canonical_story": False,
            "verified_replay": True,
            "player_view": handoff,
            "private_test_audit_only": audit,
        }


def main():
    with TemporaryDirectory(prefix="carlos-play26-seasons-") as directory:
        variants = {
            "two_wet_seasons": run_planted_village(Path(directory) / "wet.sqlite"),
            "one_water": run_planted_village(Path(directory) / "dry_after_one.sqlite",
                                             water=1),
            "no_water": run_planted_village(Path(directory) / "dry.sqlite", water=0),
            "no_seed": run_planted_village(Path(directory) / "seedless.sqlite", seed=0),
            "no_hoe": run_planted_village(Path(directory) / "tool-less.sqlite", hoe=0),
        }
    for key, world in variants.items():
        s = world["private_test_audit_only"]
        print(f"{key}: 7 NPC / t={TARGET}, grown={s['grown']}, "
              f"harvests={s['harvests']}, bakes={s['bakes']}, trades={s['trades']}, "
              f"water={s['remaining_water']}, copper={s['copper']}")
    print("PLAY26_JSON=" + json.dumps(variants, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
