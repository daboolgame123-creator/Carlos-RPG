"""PLAY-27: four actual sites with finite water, physical courier and seed economy.

Seven autonomous NPCs; only Carlos's player WAIT commands advance time.
The opt-in economic-mode endurance scenario is not a starvation survival proof.
"""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from carlos_sim import DomainEvent, LivingWorldEngine, PlayerGateway
from carlos_sim.resumable_play import ResumableTestSession

WORLD = "play27-real-four-site-supply"
PLAYER = "carlos"
DAY = 86400
PERIOD = 21600
TARGET = 3 * DAY + 1500
PEOPLE = (
    ("basim", "baker", "bakery", 0, 0),
    ("salma", "merchant", "market", 20, 10),
    ("adel", "guard", "market", 80, 10),
    ("nora", "farmer", "farm", 20, 5),
    ("huda", "courier", "well", 20, 5),
    ("omar", "explorer", "market", 20, 10),
    ("layla", "resident", "market", 20, 10),
)


def seed_physical_supply(store, *, water: int = 2, seed: int = 1,
                         hoe: int = 1, sickle: int = 1,
                         courier: bool = True, buyer_copper: int = 2,
                         courier_hunger: int = 20, personal_food: int = 0,
                         harvest_yield: int = 1, market_wallets: bool = False,
                         initial_market_food: int = 0,
                         hungry_market_buyers: bool = False,
                         staff_provisions: bool = False,
                         playable_demo: bool = False) -> None:
    if type(playable_demo) is not bool:
        raise ValueError('playable_demo must be a boolean trusted setup flag')
    if type(market_wallets) is not bool:
        raise ValueError('market_wallets must be a boolean trusted setup flag')
    if type(initial_market_food) is not int or not 0 <= initial_market_food <= 3:
        raise ValueError('initial_market_food must be a bounded integer (0-3)')
    if type(hungry_market_buyers) is not bool:
        raise ValueError('hungry_market_buyers must be a boolean trusted setup flag')
    if type(staff_provisions) is not bool:
        raise ValueError('staff_provisions must be a boolean trusted setup flag')
    # This is a time-zero ownership counterfactual, NOT a runtime allocation
    # or a teleporting food courier. The initial three market loaves become
    # three physically pre-positioned NPC loaves before logical time begins.
    if staff_provisions and (initial_market_food != 3 or personal_food != 0):
        raise ValueError('staff_provisions requires exactly 3 opening loaves and no personal_food')
    if type(personal_food) is not int or not 0 <= personal_food <= 20:
        raise ValueError('personal_food must be a finite nonnegative test allotment')
    # PLAY-30: this is a trusted test-world recipe choice, never a runtime yield cheat.
    if type(harvest_yield) is not int or harvest_yield not in (1, 2, 3):
        raise ValueError('harvest_yield must be a bounded integer of 1, 2 or 3')
    for key, value, valid in (
        ("water", water, (0, 1, 2)), ("seed", seed, (0, 1)),
        ("hoe", hoe, (0, 1)), ("sickle", sickle, (0, 1)),
        ("buyer_copper", buyer_copper, (0, 2)),
    ):
        if type(value) is not int or value not in valid:
            raise ValueError(f"{key} must be a known finite test choice")
    if type(courier) is not bool:
        raise ValueError("courier flag must be boolean")
    if type(courier_hunger) is not int or not 0 <= courier_hunger < 90:
        raise ValueError("courier hunger must be a bounded valid initial need")

    store.create_world(WORLD)
    def e(kind, data):
        return DomainEvent(kind, None, "trusted PLAY-27 test setup", 0, data)

    events = [
        *[e("LocationCreated", {"id": name, "name": name.title()})
          for name in ("well", "farm", "bakery", "market", "home")],
        *[e("RouteCreated", {"id": ident, "a": a, "b": b, "seconds": seconds})
          for ident, a, b, seconds in (
              ("well-farm", "well", "farm", 50),
              ("farm-bakery", "farm", "bakery", 60),
              ("bakery-market", "bakery", "market", 40),
          )],
        e("EntityCreated", {
            "id": PLAYER, "name": "Carlos", "location_id": "home",
            "controller": "player",
        }),
    ]
    if playable_demo:
        from carlos_sim.rpg_state import unknown_profile
        # A real road and a sample game status. No story-file import.
        events.append(e('RouteCreated', {
            'id': 'home-market', 'a': 'home', 'b': 'market', 'seconds': 90,
        }))
        demo_profile = unknown_profile()
        demo_profile['vitals']['hp'] = {'current': 12, 'max': 12}
        demo_profile['vitals']['st'] = {'current': 8, 'max': 8}
        events.append(e('PlayerRPGInitialized', {
            'player_id': PLAYER, 'profile': demo_profile,
        }))
        events.append(e('ResourceChanged', {
            'owner_id': PLAYER, 'resource': 'food',
            'previous': None, 'current': 0, 'source': 'initialization',
        }))
    for who, role, location, hunger, fatigue in PEOPLE:
        events.extend((
            e("EntityCreated", {
                "id": who, "name": who.title(), "location_id": location,
                "controller": "npc",
            }),
            e("NPCConfigured", {
                "npc_id": who, "role": role,
                "needs": {"hunger": (80 if hungry_market_buyers and who in ("omar", "layla")
                                      else courier_hunger if who == "huda" else hunger),
                          "fatigue": fatigue, "safety": 0},
                "goals": {"earn": 0 if who == "basim" else 10,
                          "explore": 0 if who == "basim" else 10,
                          "survive": 30},
            }),
        ))
        for resource in ("labor_units", "investigation_attempts", "food"):
            events.append(e("ResourceChanged", {
                "owner_id": who, "resource": resource, "previous": None,
                "current": (personal_food + int(staff_provisions and who in
                           ("nora", "basim", "huda"))) if resource == "food" else 0,
                "source": "initialization",
            }))
    stock = [
        ("well", "water", water),
        ("farm", "water", 0),
        ("farm", "seed", seed),
        ("farm", "crop_seeded", 0),
        ("farm", "crop_ready", 0),
        ("farm", "grain", 0),
        ("farm", "hoe", hoe),
        ("farm", "sickle", sickle),
        ("bakery", "grain", 0),
        ("bakery", "oven", 1),
        ("bakery", "food", 0),
        ("market", "food", initial_market_food - (3 if staff_provisions else 0)),
        ("market", "coin_copper", 0),
        ("adel", "coin_copper", buyer_copper),
        (PLAYER, "coin_copper", 2 if market_wallets else 10),
        ("huda", "water", 0),
        ("huda", "grain", 0),
    ]
    # In the budgeted *counterfactual* only, transfer eight of Carlos's
    # pre-existing ten coins at bootstrap: four each to Omar and Layla.
    # Original scenario is unchanged byte-for-byte when flag=False.
    if market_wallets:
        stock.extend((("omar", "coin_copper", 4), ("layla", "coin_copper", 4)))
    for owner, resource, amount in stock:
        events.append(e("ResourceChanged", {
            "owner_id": owner, "resource": resource,
            "previous": None, "current": amount, "source": "initialization",
        }))

    events.extend((
        e("NPCRoutineConfigured", {
            "npc_id": "nora", "home_id": "home",
            "workplace_id": "farm", "work_start": 0, "work_end": 3000,
        }),
        e("NPCRoutineConfigured", {
            "npc_id": "basim", "home_id": "home",
            "workplace_id": "bakery", "work_start": 0, "work_end": 30000,
        }),
        e("ProductionRecipeConfigured", {
            "id": "finite-harvest", "site_id": "farm", "role": "farmer",
            "input_resource": "crop_ready", "input_amount": 1,
            "output_resource": "grain", "output_amount": harvest_yield,
            "tool_resource": "sickle", "duration_seconds": 60,
        }),
        e("ProductionRecipeConfigured", {
            "id": "seed-planting", "site_id": "farm", "role": "farmer",
            "input_resource": "seed", "input_amount": 1,
            "output_resource": "crop_seeded", "output_amount": 1,
            "tool_resource": "hoe", "duration_seconds": 60,
        }),
        e("ProductionRecipeConfigured", {
            "id": "grain-to-bread", "site_id": "bakery", "role": "baker",
            "input_resource": "grain", "input_amount": 1,
            "output_resource": "food", "output_amount": 1,
            "tool_resource": "oven", "duration_seconds": 90,
        }),
        e("FarmPlotConfigured", {
            "site_id": "farm", "growth_seconds": DAY, "capacity": 1,
        }),
        e("MarketStallConfigured", {
            "site_id": "market", "keeper_id": "salma",
        }),
    ))
    if courier:
        events.append(e("SupplyCircuitConfigured", {
            "courier_id": "huda",
            "stops": ["well", "farm", "bakery", "market", "bakery", "farm", "well"],
            "route_ids": [
                "well-farm", "farm-bakery", "bakery-market",
                "bakery-market", "farm-bakery", "well-farm",
            ],
            "period_seconds": PERIOD,
        }))
    store.append(WORLD, "play27-physical-bootstrap", 0, events, bootstrap=True)


def audit_physical_supply(state, *, seed: int, water: int, buyer_copper: int,
                          personal_food: int = 0,
                          initial_market_food: int = 0) -> dict:
    rs = state.resources
    farm, well, bakery, market, huda = (
        rs["farm"], rs["well"], rs["bakery"], rs["market"], rs["huda"]
    )
    plot = state.farm_plots["farm"]
    growing = int(plot["status"] == "growing")
    planting = sum(1 for job in state.production_jobs.values()
                   if job["status"] == "running"
                   and state.production_recipes[job["recipe_id"]]["input_resource"] == "seed")
    assert farm["seed"] + farm["crop_seeded"] + planting + growing == seed
    assert well["water"] + farm["water"] + huda["water"] + plot["matured"] + growing == water

    # A ripe crop is a physical harvest lot, with a frozen, bounded grain yield.
    # Count the *potential grain* while it is ripe or reserved by the harvester;
    # never count both input and finished output when a job completes.
    harvest_yield = state.production_recipes["finite-harvest"]["output_amount"]
    assert type(harvest_yield) is int and harvest_yield in (1, 2, 3)
    in_flight = sum(
        state.production_recipes[job["recipe_id"]]["input_amount"]
        * (harvest_yield if state.production_recipes[job["recipe_id"]]["input_resource"]
           == "crop_ready" else 1)
        for job in state.production_jobs.values()
        if job["status"] == "running"
        and state.production_recipes[job["recipe_id"]]["input_resource"]
        in ("crop_ready", "grain")
    )
    food = (farm["crop_ready"] * harvest_yield + farm["grain"] + bakery["grain"]
            + bakery["food"] + market["food"] + huda["grain"]
            + in_flight
            + sum(rs[who]["food"] for who, *_ in PEOPLE)
            # In PLAY-31 the human can purchase physical market food. Include
            # only *initialized* player-owned food: missing is not a resource.
            + (rs.get(PLAYER, {}).get("food") or 0)
            + sum(m["quantity"] for m in state.consumptions.values()))
    assert food == (plot["matured"] * harvest_yield
                    + len(PEOPLE) * personal_food + initial_market_food)
    # Copper is conserved regardless of its owner: market, player or NPC.
    copper = sum(owner_stock["coin_copper"] for owner_stock in rs.values()
                 if "coin_copper" in owner_stock)
    assert copper == 10 + buyer_copper
    circuit = state.supply_circuits.get("huda")
    if circuit is not None:
        assert circuit["loads"] - circuit["deliveries"] == int(circuit["carry"] is not None)
    return {
        "grown": plot["matured"], "growing": growing,
        "initial_water": water, "well_water": well["water"],
        "farm_water": farm["water"], "carried_water": huda["water"],
        "seed": farm["seed"], "food_equivalent": food,
        "harvest_yield": harvest_yield,
        "copper": copper, "loads": circuit["loads"] if circuit else 0,
        "deliveries": circuit["deliveries"] if circuit else 0,
        "courier_rounds": circuit["rounds"] if circuit else 0,
    }


def run_physical_supply(path: str | Path, *, water: int = 2, seed: int = 1,
                        hoe: int = 1, sickle: int = 1, courier: bool = True,
                        buyer_copper: int = 2, metabolism: bool = False,
                        courier_hunger: int = 20, harvest_yield: int = 1,
                        target: int = TARGET) -> dict:
    def setup(store):
        seed_physical_supply(store, water=water, seed=seed, hoe=hoe,
                             sickle=sickle, courier=courier,
                             buyer_copper=buyer_copper, courier_hunger=courier_hunger,
                             harvest_yield=harvest_yield)
    with ResumableTestSession.create(
        path, WORLD, PLAYER, setup, disposable_test=True,
    ) as session:
        db, clock = session.store, session.clock
        session.bind_gateway(PlayerGateway(
            db, clock, world_id=WORLD, player_id=PLAYER,
            engine=LivingWorldEngine(
                db, clock, supply_enabled=True, agriculture_enabled=True,
                economic_enabled=True, economy_only_enabled=True,
                consumption_enabled=True, survival_enabled=metabolism,
            ),
        ))
        initial = db.load(WORLD)
        assert len(initial.npcs) == 7
        assert all(initial.resources[x].get(y, 0) == 0 for x, y in (
            ("farm", "water"), ("farm", "crop_ready"), ("farm", "grain"),
            ("bakery", "grain"), ("bakery", "food"), ("market", "food")
        ))
        audit_physical_supply(initial, seed=seed, water=water, buyer_copper=buyer_copper)
        step = 0
        while db.load(WORLD).time < target:
            now = db.load(WORLD).time
            t = min(target, now + PERIOD)
            step += 1
            response = session.gateway.wait(
                t-now, command_id=f"play27-advance-{step}",
                expected_revision=db.load(WORLD).revision,
            )
            assert response.time == t
            audit_physical_supply(db.load(WORLD), seed=seed, water=water,
                                  buyer_copper=buyer_copper)
        final = db.load(WORLD)
        assert db.verify(WORLD).to_dict() == final.to_dict()
        db.snapshot(WORLD)
        assert db.verify(WORLD).to_dict() == final.to_dict()
        player = session.handoff()
        exposed = json.dumps(player, ensure_ascii=False)
        for secret in ('"supply_circuits"', '"production_jobs"', '"market_trades"',
                       '"npcs"', '"farm_plots"', '"water"', '"grain"'):
            assert secret not in exposed
        stats = audit_physical_supply(final, seed=seed, water=water,
                                      buyer_copper=buyer_copper)
        stats.update({
            "npcs": len(final.npcs),
            "plantings": sum(j["recipe_id"] == "seed-planting" and
                             j["status"] == "completed"
                             for j in final.production_jobs.values()),
            "harvests": sum(j["recipe_id"] == "finite-harvest" and
                            j["status"] == "completed"
                            for j in final.production_jobs.values()),
            "bakes": sum(j["recipe_id"] == "grain-to-bread" and
                         j["status"] == "completed"
                         for j in final.production_jobs.values()),
            "trades": len(final.market_trades),
            "meals": len(final.consumptions),
            "farm_inventory":dict(final.resources["farm"]),
            "bakery_inventory":dict(final.resources["bakery"]),
            "plot":dict(final.farm_plots["farm"]),
            "nora_jobs":[dict(j) for j in final.production_jobs.values() if j["npc_id"] == "nora"],
            "max_hunger": max(npc["needs"]["hunger"] for npc in final.npcs.values()),
            "max_fatigue": max(npc["needs"]["fatigue"] for npc in final.npcs.values()),
            "player_issued_courier_orders": 0,
        })
        assert stats["bakes"] <= stats["harvests"] * harvest_yield
        assert stats["harvests"] <= stats["grown"] <= water
        assert stats["deliveries"] <= stats["loads"]
        return {
            "format": "carlos-play27-finite-physical-logistics-v1",
            "logical_seconds": target, "disposable_test": True,
            "canonical_story": False, "metabolism_enabled": metabolism,
            "verified_replay": True, "player_view": player,
            "private_test_audit_only": stats,
        }


def main() -> None:
    with TemporaryDirectory(prefix="play27-actual-sites-") as dirname:
        root = Path(dirname)
        cases = {
            "full_finite_supply": run_physical_supply(root / "full.sqlite"),
            "single_well_water": run_physical_supply(root / "one.sqlite", water=1),
            "dry_well": run_physical_supply(root / "dry.sqlite", water=0),
            "missing_seed": run_physical_supply(root / "no-seed.sqlite", seed=0),
            "absent_courier": run_physical_supply(root / "no-courier.sqlite",
                                                   courier=False),
            "metabolism_pressure": run_physical_supply(root / "real-hunger.sqlite",
                                                        metabolism=True),
        }
    for name, data in cases.items():
        a = data["private_test_audit_only"]
        print(f"{name}: 7 NPC / t={data['logical_seconds']}, "
              f"grown={a['grown']} harvests={a['harvests']} bakes={a['bakes']} "
              f"trades={a['trades']} loads={a['loads']} "
              f"deliveries={a['deliveries']} hunger={a['max_hunger']} "
              f"well={a['well_water']} copper={a['copper']}")
    print("PLAY27_JSON=" + json.dumps(cases, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
