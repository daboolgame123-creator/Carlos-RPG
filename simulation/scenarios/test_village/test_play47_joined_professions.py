"""PLAY-47: one shared world with food needs and autonomous smith→repairer.

This is a temporary finite test world, not sustained medieval self-sufficiency.
NPCs decide; no script manually moves, buys, deposits, starts, or pays for them.
"""
from __future__ import annotations

import json

import pytest

from carlos_sim import DomainEvent, LivingWorldEngine, SQLiteEventStore, TimeEngine
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.supply_diagnostics import audit_courier
from play_physical_supply import PEOPLE, WORLD, audit_physical_supply, seed_physical_supply


def _e(kind, data):
    return DomainEvent(kind, None, "trusted combined world only at t=0", 0, data)


def _joined_bootstrap(
    db, *, smith_hunger=10, water=2, staff_provisions=False,
    repair_shift_end=20_000, initial_market_food=3,
    site_payroll_enabled=False, site_payroll_wage_coin=1,
    bakery_opening_food_wage=False, farm_opening_food_wage=False,
    farm_initial_food_loaves=1, farm_bread_share_enabled=False, wood_charcoal_jobs_enabled=False,
    food_for_work_bakery_enabled=False, wilderness_food_jobs_enabled=False,
    wilderness_food_peddler_enabled=False, finite_aquifer_work_enabled=False,
):
    """Build the *entire* eleven-NPC world in one trusted genesis event batch.

    No second bootstrap may reinterpret a known wallet or silently mint money.
    When site_payroll_enabled, TWO of Carlos's actual initial 2 copper
    are allocated at genesis as farm/bakery working capital, without adding
    any copper. The normal field/baker jobs get one-copper wage contracts.
    """
    if type(finite_aquifer_work_enabled) is not bool:
        raise ValueError("finite aquifer work must be a boolean opt-in")
    if (type(wilderness_food_jobs_enabled) is not bool
            or type(wilderness_food_peddler_enabled) is not bool
            or (wilderness_food_peddler_enabled and not wilderness_food_jobs_enabled)):
        raise ValueError("bounded peddler requires actual finite wilderness food sites")
    if (type(food_for_work_bakery_enabled) is not bool
            or (food_for_work_bakery_enabled and not bakery_opening_food_wage)):
        raise ValueError("bakery food-for-work requires an existing bakery-owned opening loaf")
    if type(site_payroll_enabled) is not bool:
        raise ValueError("site_payroll_enabled must be boolean")
    if type(farm_bread_share_enabled) is not bool:
        raise ValueError("signed grain-for-bread choice must be boolean")
    if type(wood_charcoal_jobs_enabled) is not bool:
        raise ValueError("wood_charcoal_jobs_enabled must be boolean")
    if wood_charcoal_jobs_enabled and not site_payroll_enabled:
        raise ValueError("wood/charcoal employment needs existing funded salary loop")
    if (type(bakery_opening_food_wage) is not bool
            or (bakery_opening_food_wage and initial_market_food != 3)
            or type(farm_opening_food_wage) is not bool
            or (farm_opening_food_wage and
                (initial_market_food != 3 or bakery_opening_food_wage))):
        raise ValueError("bakery payroll needs exactly three original opening loaves")
    # Controlled initial ownership variation: 1 or 2 of the same
    # 3 existing loaves start at the farm, never a time-running gift.
    if (type(farm_initial_food_loaves) is not int
            or farm_initial_food_loaves not in (1, 2)
            or (farm_initial_food_loaves != 1 and not farm_opening_food_wage)):
        raise ValueError("farm 2-loaf start requires signed farm provision")
    if (type(site_payroll_wage_coin) is not int
            or site_payroll_wage_coin not in (1, 2)
            or (not site_payroll_enabled and site_payroll_wage_coin != 1)):
        raise ValueError("site_payroll_wage_coin must be one or two existing copper")
    def extend(events):
        if wilderness_food_jobs_enabled:
            # Same 13 people: a market explorer and resident take two
            # real food-producing professions, and therefore are no longer
            # available in their former occupations. No 14th NPC appears.
            # The sites and roads must exist BEFORE their local entities.
            first_entity = next(
                i for i, e in enumerate(events) if e.event_type == "EntityCreated"
            )
            events[first_entity:first_entity] = [
                _e("LocationCreated", {"id": "hunting_woods",
                                       "name": "Hunting Woods"}),
                _e("LocationCreated", {"id": "riverbank",
                                       "name": "Fishing Riverbank"}),
                _e("RouteCreated", {"id": "market-woods",
                                    "a": "market", "b": "hunting_woods",
                                    "seconds": 240}),
                _e("RouteCreated", {"id": "well-river",
                                    "a": "well", "b": "riverbank",
                                    "seconds": 180}),
            ]
            updated = set()
            for i, e in enumerate(events):
                who = e.data.get("id") if e.event_type == "EntityCreated" else (
                    e.data.get("npc_id") if e.event_type == "NPCConfigured" else None
                )
                site_role = {"omar": ("hunting_woods", "hunter"),
                             "layla": ("riverbank", "fisher")}.get(who)
                if site_role is None:
                    continue
                d = dict(e.data)
                if e.event_type == "EntityCreated":
                    d["location_id"] = site_role[0]
                elif e.event_type == "NPCConfigured":
                    d["role"] = site_role[1]
                else:
                    continue
                events[i] = _e(e.event_type, d)
                updated.add((who, e.event_type))
            assert updated == {
                ("omar", "EntityCreated"), ("omar", "NPCConfigured"),
                ("layla", "EntityCreated"), ("layla", "NPCConfigured"),
            }
        if farm_opening_food_wage:
            # The original three opening loaves remain exactly THREE:
            # 2 in the market, 1 already physically stored at the field
            # before time zero. Its owner will pre-fund one real courier
            # wage. No runtime relief packet or fake well-to-market trip.
            saw_market = False
            for i, ev in enumerate(events):
                if (ev.event_type == "ResourceChanged"
                        and ev.data.get("owner_id") == "market"
                        and ev.data.get("resource") == "food"):
                    assert ev.data["previous"] is None
                    assert ev.data["current"] == 3 and not saw_market
                    replacement = dict(ev.data)
                    replacement["current"] = 3 - farm_initial_food_loaves
                    events[i] = _e("ResourceChanged", replacement)
                    saw_market = True
            assert saw_market
            events.append(_e("ResourceChanged", {
                "owner_id": "farm", "resource": "food",
                "previous": None, "current": farm_initial_food_loaves,
                "source": "initialization",
            }))
        if bakery_opening_food_wage:
            # This is a time-zero ownership experiment: ONE of the THREE
            # pre-existing market loaves instead starts in the baker's own
            # physical workshop. No bread is minted or moved after genesis.
            changed = set()
            for idx, ev in enumerate(events):
                if (ev.event_type == "ResourceChanged"
                        and ev.data.get("resource") == "food"
                        and ev.data.get("owner_id") in ("market", "bakery")):
                    original_food = 3 if ev.data["owner_id"] == "market" else 0
                    assert ev.data["current"] == original_food
                    updated = dict(ev.data)
                    updated["current"] = 2 if ev.data["owner_id"] == "market" else 1
                    events[idx] = _e("ResourceChanged", updated)
                    changed.add(ev.data["owner_id"])
            assert changed == {"market", "bakery"}
        # Redistribute four of the twelve existing opening copper coins BEFORE
        # the one and only authoritative genesis is committed.
        adjusted = set()
        for idx, event in enumerate(events):
            if (event.event_type == "ResourceChanged"
                    and event.data["resource"] == "coin_copper"
                    and event.data["owner_id"] in ("omar", "layla")):
                assert event.data["previous"] is None
                assert event.data["current"] == 4
                updated = dict(event.data)
                updated["current"] = 2
                events[idx] = _e("ResourceChanged", updated)
                adjusted.add(updated["owner_id"])
        assert adjusted == {"omar", "layla"}
        if site_payroll_enabled:
            # This is a deliberately DISTINCT genesis counterfactual.
            # Reallocate Carlos's two existing opening coins to the actual
            # two employer site treasuries. No new currency, no gifts after t=0.
            carlos_wallets = [
                (idx, ev) for idx, ev in enumerate(events)
                if ev.event_type == "ResourceChanged"
                and ev.data.get("owner_id") == "carlos"
                and ev.data.get("resource") == "coin_copper"
            ]
            assert len(carlos_wallets) == 1
            idx, old = carlos_wallets[0]
            assert old.data["current"] == 2 and old.data["previous"] is None
            funded = dict(old.data)
            funded["current"] = 0
            events[idx] = _e("ResourceChanged", funded)
            # Wage-bearing recipes are strictly validated *as they enter
            # the event stream*. Employer cash must already exist BEFORE
            # the first ProductionRecipeConfigured event is projected.
            first_recipe = next(i for i, ev in enumerate(events)
                                if ev.event_type == "ProductionRecipeConfigured")
            events[first_recipe:first_recipe] = [
                _e("ResourceChanged", {
                    "owner_id": site, "resource": "coin_copper",
                    "previous": None, "current": 1,
                    "source": "initialization",
                })
                for site in ("farm", "bakery")
            ]
            signed = set()
            for idx, ev in enumerate(events):
                if (ev.event_type == "ProductionRecipeConfigured"
                        and ev.data.get("id") in
                            ("finite-harvest", "grain-to-bread")):
                    assert "wage_coin" not in ev.data
                    terms = dict(ev.data)
                    terms["wage_coin"] = site_payroll_wage_coin
                    events[idx] = _e("ProductionRecipeConfigured", terms)
                    signed.add(terms["id"])
            assert signed == {"finite-harvest", "grain-to-bread"}

        if wilderness_food_jobs_enabled:
            # FINITE ecology: each site starts with TWO real food lots and
            # SIX units of pre-existing reserve converted by scheduled time
            # (one per two hours if below physical capacity). No invisible
            # animal/fish spawn or unlimited breeding is claimed.
            for site, tool, role in (
                ("hunting_woods", "bow", "hunter"),
                ("riverbank", "net", "fisher"),
            ):
                for resource, amount in (
                    ("wild_food", 2), ("regrowth_reserve", 6),
                    ("food", 0), ("coin_copper", 0), (tool, 1),
                ):
                    events.append(_e("ResourceChanged", {
                        "owner_id": site, "resource": resource,
                        "previous": None, "current": amount,
                        "source": "initialization",
                    }))
                events.append(_e("EnvironmentalCycleConfigured", {
                    "id": site + "-finite-ecology",
                    "site_id": site, "period_seconds": 7200,
                    "capacity": 3,
                }))
                events.append(_e("MarketStallConfigured", {
                    "site_id": site,
                    "keeper_id": "omar" if role == "hunter" else "layla",
                }))
                events.append(_e("ProductionRecipeConfigured", {
                    "id": "two-portions-" + role,
                    "site_id": site, "role": role,
                    "input_resource": "wild_food", "input_amount": 1,
                    "output_resource": "food", "output_amount": 2,
                    "tool_resource": tool, "duration_seconds": 3600,
                    "wage_food": 2,
                }))
            for who, site in (
                ("omar", "hunting_woods"),
                ("layla", "riverbank"),
            ):
                events.append(_e("NPCRoutineConfigured", {
                    "npc_id": who, "home_id": "market",
                    "workplace_id": site, "work_start": 0,
                    "work_end": 20_000,
                }))
        if food_for_work_bakery_enabled:
            # Only a real time-zero employer can sign this durable wage term.
            bakery_jobs = [
                (idx, ev) for idx, ev in enumerate(events)
                if ev.event_type == "ProductionRecipeConfigured"
                and ev.data.get("id") == "grain-to-bread"
            ]
            assert len(bakery_jobs) == 1
            idx, old = bakery_jobs[0]
            assert "wage_coin" not in old.data
            terms = dict(old.data)
            terms["wage_food"] = 1
            events[idx] = _e("ProductionRecipeConfigured", terms)
        if wood_charcoal_jobs_enabled:
            # ONE of the thirteen existing people, Layla, takes an actual
            # finite-timber job. The forest location is created before her
            # time-zero entity, not via unrecorded teleport later.
            layla_at = next(i for i, ev in enumerate(events)
                            if ev.event_type == "EntityCreated"
                            and ev.data.get("id") == "layla")
            events.insert(layla_at, _e("LocationCreated", {
                "id": "lumberyard", "name": "Lumberyard",
            }))
            changed = set()
            for i, ev in enumerate(events):
                if ev.data.get("owner_id") == "layla" and (
                        ev.event_type == "ResourceChanged"
                        and ev.data.get("resource") == "coin_copper"):
                    assert ev.data["current"] == 2
                    updated = dict(ev.data)
                    updated["current"] = 0
                    events[i] = _e(ev.event_type, updated)
                    changed.add("layla-wallet")
                if ev.event_type == "EntityCreated" and ev.data.get("id") == "layla":
                    updated = dict(ev.data)
                    updated["location_id"] = "lumberyard"
                    events[i] = _e(ev.event_type, updated)
                    changed.add("layla-location")
                if ev.event_type == "NPCConfigured" and ev.data.get("npc_id") == "layla":
                    updated = dict(ev.data)
                    updated["role"] = "woodcutter"
                    events[i] = _e(ev.event_type, updated)
                    changed.add("layla-role")
            assert changed == {"layla-wallet", "layla-location", "layla-role"}

        sites = ("smithy", "iron_mine", "charcoal_kiln", "repair_shop")
        staff = (
            ("smith", "blacksmith", "smithy"),
            ("miner", "well_pumper" if finite_aquifer_work_enabled else "miner",
             "well" if finite_aquifer_work_enabled else "iron_mine"),
            ("burner", "charcoal_burner", "charcoal_kiln"),
            ("repairman", "food_peddler" if wilderness_food_peddler_enabled else "repairer",
             "market" if wilderness_food_peddler_enabled else "repair_shop"),
        )
        events.extend(_e("LocationCreated", {"id": site, "name": site})
                      for site in sites)
        for rid, a, b, duration in (
            ("bakery-smithy", "bakery", "smithy", 60),
            ("smith-mine", "smithy", "iron_mine", 30),
            ("smith-kiln", "smithy", "charcoal_kiln", 40),
            ("smith-repair", "smithy", "repair_shop", 50),
            *((("kiln-lumberyard", "charcoal_kiln", "lumberyard", 35),
                ("market-lumberyard", "market", "lumberyard", 45))
              if wood_charcoal_jobs_enabled else ()),
        ):
            events.append(_e("RouteCreated", {
                "id": rid, "a": a, "b": b, "seconds": duration,
            }))
        for name, role, site in staff:
            events.extend((
                _e("EntityCreated", {
                    "id": name, "name": name.title(),
                    "location_id": site, "controller": "npc",
                }),
                _e("NPCConfigured", {
                    "npc_id": name, "role": role,
                    "needs": {"hunger": smith_hunger if name == "smith" else 10,
                              "fatigue": 0, "safety": 0},
                    "goals": {"earn": 10, "explore": 10, "survive": 30},
                }),
            ))

        resources = {
            "smithy": {"iron_ore": 0, "charcoal": 0, "anvil": 1,
                       "iron_fitting": 0},
            "iron_mine": {"iron_ore": 1},
            "charcoal_kiln": {"charcoal": 1},
            "repair_shop": {"iron_fitting": 0, "repaired_gear": 0,
                            "wrench": 1},
            "smith": {"iron_ore": 0, "charcoal": 0, "food": 0,
                      "coin_copper": 2, "labor_units": 0,
                      "investigation_attempts": 0},
            "repairman": {"iron_fitting": 0, "food": 0, "coin_copper": 2,
                          "labor_units": 0, "investigation_attempts": 0},
            "miner": {"food": 0, "labor_units": 0,
                      "investigation_attempts": 0},
            "burner": {"food": 0, "labor_units": 0,
                       "investigation_attempts": 0},
        }
        if finite_aquifer_work_enabled:
            # Two *already existing* smith-owned copper coins are held as
            # well employer working capital from time zero: never minted.
            # Paid pumping cannot exceed the employer's real local wallet.
            assert resources["smith"]["coin_copper"] == 2
            resources["smith"]["coin_copper"] = 0
        if wood_charcoal_jobs_enabled:
            # The two original coins of Layla are deposited as real employer
            # working capital at the forest. One of the repairer's coins is
            # likewise moved to the charcoal maker's purchasing wallet.
            # Neither money nor raw lumber appears after genesis.
            resources["lumberyard"] = {
                "standing_timber": 3, "wood": 0, "axe": 1,
                "coin_copper": 2,
            }
            resources["charcoal_kiln"] = {
                "wood": 0, "charcoal": 0, "kiln_tool": 1,
            }
            # A legitimate traveling buyer needs an initialized EMPTY
            # private bag slot; unknown material custody must not be guessed.
            resources["burner"]["wood"] = 0
            resources["burner"]["coin_copper"] = 1
            resources["repairman"]["coin_copper"] = 1
            # Old 1 charcoal unit is deliberately excluded from the
            # treatment: real charcoal must require actual purchased wood.
        for owner, owned in resources.items():
            for resource, amount in owned.items():
                events.append(_e("ResourceChanged", {
                    "owner_id": owner, "resource": resource,
                    "previous": None, "current": amount,
                    "source": "initialization",
                }))

        existing_wallets = {
            event.data["owner_id"] for event in events
            if event.event_type == "ResourceChanged"
            and event.data["resource"] == "coin_copper"
        }
        all_owners = (
            {who for who, *_ in PEOPLE}
            | {"carlos", "well", "farm", "bakery", "market", "home"}
            | set(sites) | {who for who, _, _ in staff}
        )
        for owner in sorted(all_owners - existing_wallets):
            events.append(_e("ResourceChanged", {
                "owner_id": owner, "resource": "coin_copper",
                "previous": None, "current": 0, "source": "initialization",
            }))

        if finite_aquifer_work_enabled:
            original_well_wallets = [
                (i, e) for i, e in enumerate(events)
                if e.event_type == "ResourceChanged"
                and e.data.get("owner_id") == "well"
                and e.data.get("resource") == "coin_copper"
            ]
            assert len(original_well_wallets) == 1
            idx, prior = original_well_wallets[0]
            assert prior.data["previous"] is None
            assert prior.data["current"] == 0
            events[idx] = _e("ResourceChanged", {
                **dict(prior.data), "current": 2,
            })
            # The literal physical reserve is *declared at genesis*, not
            # weather conjured later. Six finite groundwater units and one
            # hand pump must be present before the signed recipe can exist.
            for resource, number in (
                ("groundwater_reserve", 6), ("hand_pump", 1),
            ):
                events.append(_e("ResourceChanged", {
                    "owner_id": "well", "resource": resource,
                    "previous": None, "current": number,
                    "source": "initialization",
                }))
            events.append(_e("ProductionRecipeConfigured", {
                "id": "finite-aquifer-to-well",
                "site_id": "well", "role": "well_pumper",
                "input_resource": "groundwater_reserve", "input_amount": 1,
                "output_resource": "water", "output_amount": 1,
                "tool_resource": "hand_pump", "duration_seconds": 1800,
                "wage_coin": 1,
            }))
        if wood_charcoal_jobs_enabled:
            events.append(_e("NPCRoutineConfigured", {
                "npc_id": "layla", "home_id": "market",
                "workplace_id": "lumberyard", "work_start": 0,
                "work_end": 20_000,
            }))
        for owner, home, workplace, start in (
            ("smith", "iron_mine", "smithy", 0),
            ("miner", "bakery",
             "well" if finite_aquifer_work_enabled else "iron_mine", 0),
            ("burner", "bakery", "charcoal_kiln", 0),
            ("repairman", "market" if wilderness_food_peddler_enabled else "charcoal_kiln",
             "hunting_woods" if wilderness_food_peddler_enabled else "repair_shop",
             0 if wilderness_food_peddler_enabled else 250),
        ):
            events.append(_e("NPCRoutineConfigured", {
                "npc_id": owner, "home_id": home,
                "workplace_id": workplace,
                "work_start": start,
                "work_end": (72_000 if owner == "miner"
                             and finite_aquifer_work_enabled else
                             repair_shift_end if owner == "repairman"
                             and not wilderness_food_peddler_enabled else 20_000),
            }))
        for site, keeper in (
            ("iron_mine", "miner"),
            ("charcoal_kiln", "burner"),
            ("smithy", "smith"),
            *((("lumberyard", "layla"),) if wood_charcoal_jobs_enabled else ()),
        ):
            events.append(_e("MarketStallConfigured", {
                "site_id": site, "keeper_id": keeper,
            }))
        events.extend((
            _e("ProductionRecipeConfigured", {
                "id": "iron-plus-fuel", "site_id": "smithy",
                "role": "blacksmith",
                "inputs": [
                    {"resource": "iron_ore", "amount": 1},
                    {"resource": "charcoal", "amount": 1},
                ],
                "output_resource": "iron_fitting",
                "output_amount": 1,
                "tool_resource": "anvil", "duration_seconds": 90,
                "wage_coin": 1,
            }),
            _e("ProductionRecipeConfigured", {
                "id": "repair-tools", "site_id": "repair_shop",
                "role": "repairer", "input_resource": "iron_fitting",
                "input_amount": 1,
                "output_resource": "repaired_gear", "output_amount": 1,
                "tool_resource": "wrench", "duration_seconds": 90,
            }),
        ))
        if wood_charcoal_jobs_enabled:
            events.extend((
                _e("ProductionRecipeConfigured", {
                    "id": "finite-timber-cutting", "site_id": "lumberyard",
                    "role": "woodcutter", "input_resource": "standing_timber",
                    "input_amount": 1, "output_resource": "wood",
                    "output_amount": 1, "tool_resource": "axe",
                    "duration_seconds": 120, "wage_coin": 2,
                }),
                _e("ProductionRecipeConfigured", {
                    "id": "finite-wood-charcoal", "site_id": "charcoal_kiln",
                    "role": "charcoal_burner", "input_resource": "wood",
                    "input_amount": 1, "output_resource": "charcoal",
                    "output_amount": 1, "tool_resource": "kiln_tool",
                    "duration_seconds": 120, "wage_coin": 1,
                }),
            ))

        if farm_bread_share_enabled:
            signed = []
            for index, ev in enumerate(events):
                if (ev.event_type == "SupplyCircuitConfigured"
                        and ev.data.get("courier_id") == "huda"):
                    assert "farm_bread_share" not in ev.data
                    p = dict(ev.data, farm_bread_share=True)
                    events[index] = _e("SupplyCircuitConfigured", p)
                    signed.append("huda")
            assert signed == ["huda"]  # Site-specific trusted genesis.

    seed_physical_supply(
        db, water=water, harvest_yield=3,
        market_wallets=True, hungry_market_buyers=True,
        initial_market_food=initial_market_food, staff_provisions=staff_provisions,
        trusted_genesis_hook=extend,
    )
    state = db.load(WORLD)
    audit = audit_npc_economy(state)
    assert len(state.npcs) == 11
    assert state.resources["omar"]["coin_copper"] == 2
    assert state.resources["layla"]["coin_copper"] == (
        0 if wood_charcoal_jobs_enabled else 2
    )
    assert audit["copper_scope_complete"] is True
    assert audit["copper_known_total"] == 12
    if wood_charcoal_jobs_enabled:
        assert state.npcs["layla"]["role"] == "woodcutter"
        assert state.resources["lumberyard"]["standing_timber"] == 3
        assert state.resources["lumberyard"]["coin_copper"] == 2
        assert state.resources["burner"]["coin_copper"] == 1
        assert state.resources["repairman"]["coin_copper"] == 1
        assert state.resources["charcoal_kiln"]["charcoal"] == 0
    if site_payroll_enabled:
        assert state.resources["carlos"]["coin_copper"] == 0
        assert state.resources["farm"]["coin_copper"] == 1
        assert state.resources["bakery"]["coin_copper"] == 1
        for contract in ("finite-harvest", "grain-to-bread"):
            assert state.production_recipes[contract]["wage_coin"] == site_payroll_wage_coin
    assert db.verify(WORLD).to_dict() == state.to_dict()
    return state


def _engine(db, clock, full_life=True, *, shopping=False):
    return LivingWorldEngine(
        db, clock, max_events_per_advance=5000,
        decision_cooldown=3600,
        economic_enabled=True, agriculture_enabled=True,
        economy_only_enabled=not full_life,
        navigation_enabled=True, routines_enabled=True,
        consumption_enabled=full_life, survival_enabled=full_life,
        multi_professional_markets_enabled=True,
        compound_procurement_enabled=True,
        supply_enabled=True,
        shopping_routes_enabled=shopping,
        professional_full_life_enabled=full_life,
    )


@pytest.mark.parametrize("bad", [None, 0, 1, [], {}, "yes"])
def test_full_life_flag_rejects_non_boolean(bad, tmp_path):
    with SQLiteEventStore(tmp_path / "reject-flags.sqlite") as db:
        with pytest.raises(ValueError, match="professional_full_life_enabled"):
            LivingWorldEngine(db, TimeEngine(db),
                              professional_full_life_enabled=bad)


def test_full_life_flag_rejects_incompatible_modes(tmp_path):
    with SQLiteEventStore(tmp_path / "no-modes.sqlite") as db:
        with pytest.raises(ValueError, match="professional_full_life_enabled"):
            LivingWorldEngine(db, TimeEngine(db),
                              professional_full_life_enabled=True)


def test_joined_full_life_npcs_really_trade_smelt_and_get_hungry(tmp_path):
    with SQLiteEventStore(tmp_path / "joined-food-and-smith.sqlite") as db:
        start = _joined_bootstrap(db)
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            engine = _engine(db, clock)
            result = engine.advance(
                WORLD, seconds=900,
                command_id="play47:joined:900",
                expected_revision=start.revision,
            )
            state = result.state
            assert state.time == 900
            trades = {(t["buyer_id"], t["resource"])
                      for t in state.market_trades.values()}
            # Genuine autonomous multi-input smith procurement alongside food.
            assert ("smith", "iron_ore") in trades
            assert ("smith", "charcoal") in trades
            assert any(t["resource"] == "food"
                       for t in state.market_trades.values())
            completed = [j for j in state.production_jobs.values()
                         if j["status"] == "completed"]
            assert any(j["recipe_id"] == "iron-plus-fuel" for j in completed)
            assert state.npcs["basim"]["needs"]["hunger"] > 0
            circuit = state.supply_circuits["huda"]
            assert circuit["loads"] >= 1
            assert circuit["deliveries"] >= 1
            assert state.resources["well"]["water"] < 2
            assert state.farm_plots["farm"]["status"] == "growing"
            courier_observed = audit_courier(
                state, "huda", supply_enabled=True,
            )
            assert courier_observed["deliveries"] >= 1
            assert "engine_supply_flag_disabled" not in courier_observed["blocked_reasons"]
            # Independent physical conservation proof for water, seed,
            # grains, bread, owned meals and copper, despite the joined
            # smith's separate material/copper trade activities.
            audit_physical_supply(
                state, seed=1, water=2, buyer_copper=2,
                personal_food=0, initial_market_food=3,
            )
            audit = audit_npc_economy(state)
            assert audit["copper_scope_complete"] is True
            assert audit["copper_known_total"] == 12
            assert all(value >= 0
                       for stock in state.resources.values()
                       for value in stock.values()
                       if type(value) is int)
            assert db.verify(WORLD).to_dict() == state.to_dict()
            db.snapshot(WORLD)
            assert db.verify(WORLD).to_dict() == state.to_dict()
            assert db.db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            print("PLAY47_JOINED_FULL_LIFE", json.dumps({
                "npcs": len(state.npcs),
                "copper": audit["copper_known_total"],
                "trades": audit["trades_by_resource"],
                "jobs": audit["completed_jobs"],
                "hunger": audit["npc_hunger"],
                "wages": audit["wage_receipts"],
            }, sort_keys=True))
        finally:
            clock.close_session(WORLD)


def test_urgent_hunger_preempts_professional_ore_shopping(tmp_path):
    """Full-life NPC survival must win over nonessential professional travel."""
    with SQLiteEventStore(tmp_path / "play47-hungry-smith.sqlite") as db:
        initial = _joined_bootstrap(db, smith_hunger=80)
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            final = _engine(db, clock).advance(
                WORLD, seconds=180,
                command_id="play47:hungry:180",
                expected_revision=initial.revision,
            ).state
            assert final.time == 180
            assert not any(t["buyer_id"] == "smith"
                           for t in final.market_trades.values())
            assert not any(j["npc_id"] == "smith"
                           for j in final.production_jobs.values())
            assert not any(t["npc_id"] == "smith"
                           for t in final.travels.values())
            assert audit_npc_economy(final)["copper_known_total"] == 12
            assert db.verify(WORLD).to_dict() == final.to_dict()
        finally:
            clock.close_session(WORLD)


def test_off_shift_repairer_finishes_homeward_commute(tmp_path):
    with SQLiteEventStore(tmp_path / "repairer-commutes-home.sqlite") as db:
        start = _joined_bootstrap(db, repair_shift_end=600)
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            final = _engine(db, clock).advance(
                WORLD, seconds=900, command_id="play47:repairer-home",
                expected_revision=start.revision,
            ).state
            assert final.resources["repair_shop"]["repaired_gear"] == 1
            assert final.entities["repairman"]["location_id"] == "charcoal_kiln"
            assert sorted(
                (trip["origin"], trip["destination"], trip["status"])
                for trip in final.travels.values()
                if trip["npc_id"] == "repairman" and trip["start"] >= 600
            ) == [("repair_shop", "smithy", "arrived"),
                  ("smithy", "charcoal_kiln", "arrived")]
            assert db.verify(WORLD).to_dict() == final.to_dict()
        finally:
            clock.close_session(WORLD)


def test_joined_world_partitioned_clock_preserves_economic_receipts(tmp_path):
    """Compare actual finite trades and jobs, not command/revision metadata."""
    outcomes = []
    for label, checkpoints in (
        ("one", (900,)),
        ("segmented", (30, 100, 230, 450, 700, 900)),
    ):
        with SQLiteEventStore(tmp_path / f"{label}.sqlite") as db:
            start = _joined_bootstrap(db)
            clock = TimeEngine(db)
            clock.open_session(WORLD)
            try:
                engine = _engine(db, clock)
                current = start
                for point in checkpoints:
                    current = engine.advance(
                        WORLD, seconds=point-current.time,
                        command_id=f"play47:parity:{label}:{point}",
                        expected_revision=current.revision,
                    ).state
                    assert db.verify(WORLD).to_dict() == current.to_dict()
                receipts = sorted((
                    t["buyer_id"], t["resource"], t["site_id"],
                    t["executed_at"], t["total_paid"]
                ) for t in current.market_trades.values())
                jobs = sorted((
                    j["npc_id"], j["recipe_id"], j["started_at"],
                    j["finished_at"], j["status"]
                ) for j in current.production_jobs.values())
                audit = audit_npc_economy(current)
                outcomes.append((
                    receipts, jobs, audit["copper_known_total"],
                    audit["stock_known_by_resource"],
                    audit["npc_hunger"],
                    current.supply_circuits["huda"],
                    current.farm_plots["farm"],
                ))
            finally:
                clock.close_session(WORLD)
    assert outcomes[0] == outcomes[1]


def test_joined_eleven_npcs_reach_full_day_without_money_or_material_minting(tmp_path):
    """A bad famine is an observed world outcome, not a reason to add gifts."""
    with SQLiteEventStore(tmp_path / "play47-one-day-joined.sqlite") as db:
        state = _joined_bootstrap(db)
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            engine = _engine(db, clock)
            checkpoints = (900, 21600, 43200, 64800, 86400)
            readings = []
            for target in checkpoints:
                state = engine.advance(
                    WORLD, seconds=target-state.time,
                    command_id=f"play47:day:{target}",
                    expected_revision=state.revision,
                ).state
                audit = audit_npc_economy(state)
                assert audit["copper_scope_complete"]
                assert audit["copper_known_total"] == 12
                assert audit["trades"] >= 6
                assert len(state.npcs) == 11
                assert state.resources["iron_mine"]["iron_ore"] == 0
                assert state.resources["charcoal_kiln"]["charcoal"] == 0
                assert state.resources["repair_shop"]["repaired_gear"] == 1
                assert db.verify(WORLD).to_dict() == state.to_dict()
                readings.append({
                    "hour": target // 3600,
                    "hunger_at_100": sum(h == 100 for h in audit["npc_hunger"].values()),
                    "trades": audit["trades"],
                    "jobs": audit["completed_jobs"],
                    "wages": audit["wage_receipts"],
                    "copper": audit["copper_known_total"],
                })
            db.snapshot(WORLD)
            assert db.verify(WORLD).to_dict() == state.to_dict()
            assert db.db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            print("PLAY47_JOINED_FULL_DAY", json.dumps(readings, sort_keys=True))
        finally:
            clock.close_session(WORLD)


def test_joined_dry_world_courier_does_not_invent_water(tmp_path):
    """An empty actual well is not a reason for a courier to fabricate water."""
    with SQLiteEventStore(tmp_path / "play47-dry-courier.sqlite") as db:
        start = _joined_bootstrap(db, water=0)
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            state = _engine(db, clock).advance(
                WORLD, seconds=900,
                command_id="play47:dry-courier:900",
                expected_revision=start.revision,
            ).state
            report = audit_physical_supply(
                state, seed=1, water=0, buyer_copper=2,
                personal_food=0, initial_market_food=3,
            )
            assert report["initial_water"] == 0
            assert state.resources["well"]["water"] == 0
            assert state.resources["farm"]["water"] == 0
            assert state.resources["huda"]["water"] == 0
            assert state.farm_plots["farm"]["started"] == 0
            assert not any(
                job["recipe_id"] == "finite-harvest"
                for job in state.production_jobs.values()
                if job["status"] == "completed"
            )
            assert audit_npc_economy(state)["copper_known_total"] == 12
            assert db.verify(WORLD).to_dict() == state.to_dict()
        finally:
            clock.close_session(WORLD)
