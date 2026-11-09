"""Bounded, atomic autonomous NPC lifecycle during explicitly requested play time.

This coordinator is opt-in: the ordinary TimeEngine remains a manual clock.
No wall-clock tasks, hidden knowledge, arbitrary scripts or real Carlos story data.
"""
from __future__ import annotations

from dataclasses import dataclass

from .actions import DURATIONS
from .domain import DomainEvent, WorldState, apply_event
from .npc import MIN_DECISION_COOLDOWN, choose_action
from .store import DuplicateCommand, InvalidEvent, SQLiteEventStore
from .time_engine import AdvanceLimitExceeded, TimeEngine
from .navigation import next_route, needs_survey
from .social_autonomy import MIN_SOCIAL_COOLDOWN, choose_social_intent
from .assistance_autonomy import choose_assistance_intent
from .consumption import choose_food_consumption, _meal_id
from .gathering import choose_gathering_intent
from .knowledge import make_observation_events, choose_food_sharing_round, known_food_sites
from .food_navigation import choose_food_route
from .market_navigation import (choose_known_market_walk, choose_known_market_return,
                                wants_local_market)
from .routines import choose_routine_route, routine_allows_work, next_routine_boundary
from .rumors import choose_rumor_round
from .agriculture import choose_local_growth
from .supply import choose_cargo, choose_courier_leg, next_courier_departure
from .production import choose_local_production_wage
from .economic_autonomy import (choose_local_production, choose_local_food_offer,
                                choose_local_food_purchase, choose_local_offer_retirement)


@dataclass(frozen=True)
class LivingAdvanceResult:
    state: WorldState
    requested_seconds: int
    elapsed_seconds: int
    remaining_seconds: int
    started_action_ids: tuple[str, ...]
    completed_action_ids: tuple[str, ...]
    fired_ids: tuple[str, ...]
    interrupted: bool
    event_count: int
    social_message_ids: tuple[str, ...] = ()
    assistance_transitions: tuple[tuple[str, str], ...] = ()
    meals_consumed: tuple[str, ...] = ()
    gathered_action_ids: tuple[str, ...] = ()
    knowledge_shares: tuple[str, ...] = ()
    economic_jobs: tuple[str, ...] = ()
    economic_offers: tuple[str, ...] = ()
    economic_trades: tuple[str, ...] = ()


class LivingWorldEngine:
    """Run NPC intentions/actions alongside an explicit in-world time command.

    One clock request is simulated in memory, then persisted as a single atomic
    event batch. An interruption commits *only* the portion through that signal.
    An event limit failure commits nothing, including any NPC decisions.
    """

    def __init__(self, store: SQLiteEventStore, clock: TimeEngine, *,
                 max_events_per_advance: int = 1000,
                 decision_cooldown: int = MIN_DECISION_COOLDOWN,
                 navigation_enabled: bool = False, social_enabled: bool = False,
                 social_cooldown: int = MIN_SOCIAL_COOLDOWN,
                 assistance_enabled: bool = False, consumption_enabled: bool = False,
                 survival_enabled: bool = False, gathering_enabled: bool = False,
                 foraging_enabled: bool = False, knowledge_enabled: bool = False,
                 food_navigation_enabled: bool = False,
                 scarcity_enabled: bool = False,
                 routines_enabled: bool = False,
                 rumors_enabled: bool = False,
                 economic_enabled: bool = False,
                 adaptive_market_enabled: bool = False,
                 agriculture_enabled: bool = False,
                 economy_only_enabled: bool = False,
                 shopping_routes_enabled: bool = False,
                 supply_enabled: bool = False,
                 professional_procurement_enabled: bool = False,
                 multi_professional_markets_enabled: bool = False,
                 compound_procurement_enabled: bool = False):
        if clock.store is not store:
            raise ValueError('the clock and living-world coordinator must share a store')
        if type(max_events_per_advance) is not int or max_events_per_advance < 1:
            raise ValueError('max_events_per_advance must be a positive integer')
        if type(decision_cooldown) is not int or decision_cooldown < MIN_DECISION_COOLDOWN:
            raise ValueError('decision_cooldown must be at least 60 simulation seconds')
        self.store = store
        self.clock = clock
        self.max_events_per_advance = max_events_per_advance
        if type(navigation_enabled) is not bool:
            raise ValueError("navigation_enabled must be boolean")
        self.decision_cooldown = decision_cooldown
        self.navigation_enabled = navigation_enabled
        if type(social_enabled) is not bool:
            raise ValueError("social_enabled must be a boolean")
        if type(social_cooldown) is not int or social_cooldown < MIN_SOCIAL_COOLDOWN:
            raise ValueError("social_cooldown must be at least 180 simulated seconds")
        self.social_enabled = social_enabled
        self.social_cooldown = social_cooldown
        if type(assistance_enabled) is not bool:
            raise ValueError("assistance_enabled must be boolean")
        self.assistance_enabled = assistance_enabled
        if type(consumption_enabled) is not bool:
            raise ValueError("consumption_enabled must be boolean")
        self.consumption_enabled = consumption_enabled
        if type(survival_enabled) is not bool:
            raise ValueError("survival_enabled must be boolean")
        self.survival_enabled = survival_enabled
        if type(gathering_enabled) is not bool:
            raise ValueError("gathering_enabled must be boolean")
        self.gathering_enabled = gathering_enabled
        if type(foraging_enabled) is not bool:
            raise ValueError("foraging_enabled must be boolean")
        self.foraging_enabled = foraging_enabled
        if type(knowledge_enabled) is not bool:
            raise ValueError("knowledge_enabled must be boolean")
        self.knowledge_enabled = knowledge_enabled
        if type(food_navigation_enabled) is not bool:
            raise ValueError("food_navigation_enabled must be boolean")
        if food_navigation_enabled and not (
                self.navigation_enabled and self.knowledge_enabled
                and self.foraging_enabled):
            raise ValueError(
                "food_navigation_enabled requires navigation_enabled, "
                "knowledge_enabled and foraging_enabled"
            )
        self.food_navigation_enabled = food_navigation_enabled
        if type(scarcity_enabled) is not bool:
            raise ValueError("scarcity_enabled must be boolean")
        if scarcity_enabled and not (self.food_navigation_enabled
                                    and self.assistance_enabled):
            raise ValueError(
                "scarcity_enabled requires food_navigation_enabled and assistance_enabled"
            )
        self.scarcity_enabled = scarcity_enabled
        if type(routines_enabled) is not bool:
            raise ValueError('routines_enabled must be boolean')
        if routines_enabled and not navigation_enabled:
            raise ValueError('routines_enabled requires navigation_enabled')
        self.routines_enabled = routines_enabled
        if type(rumors_enabled) is not bool:
            raise ValueError('rumors_enabled must be boolean')
        self.rumors_enabled = rumors_enabled
        if type(economic_enabled) is not bool:
            raise ValueError('economic_enabled must be boolean')
        self.economic_enabled = economic_enabled
        if type(adaptive_market_enabled) is not bool or (adaptive_market_enabled and not economic_enabled):
            raise ValueError("adaptive_market_enabled requires economic_enabled=True")
        self.adaptive_market_enabled = adaptive_market_enabled
        if type(agriculture_enabled) is not bool or (agriculture_enabled and not economic_enabled):
            raise ValueError("agriculture_enabled requires boolean economic_enabled=True")
        if type(economy_only_enabled) is not bool or (economy_only_enabled and not agriculture_enabled):
            raise ValueError("economy_only_enabled requires agriculture_enabled")
        self.agriculture_enabled = agriculture_enabled
        self.economy_only_enabled = economy_only_enabled
        if type(shopping_routes_enabled) is not bool or (shopping_routes_enabled and not (
                economy_only_enabled and navigation_enabled
                and consumption_enabled and survival_enabled)):
            raise ValueError('shopping_routes_enabled requires focused economy, navigation, consumption and survival')
        self.shopping_routes_enabled = shopping_routes_enabled
        if (type(professional_procurement_enabled) is not bool or
                (professional_procurement_enabled and not (
                    economic_enabled and agriculture_enabled and economy_only_enabled
                    and navigation_enabled and routines_enabled
                    and not shopping_routes_enabled))):
            raise ValueError(
                "professional_procurement_enabled requires focused economic "
                "simulation, navigation, routines, and no concurrent hunger shopping"
            )
        self.professional_procurement_enabled = professional_procurement_enabled
        if (type(multi_professional_markets_enabled) is not bool or
                (multi_professional_markets_enabled and not (
                    economic_enabled and agriculture_enabled and economy_only_enabled
                    and navigation_enabled and routines_enabled
                    and not shopping_routes_enabled
                    and not professional_procurement_enabled))):
            raise ValueError(
                'multi_professional_markets_enabled requires focused economic '
                'simulation and cannot share another professional/shopping planner'
            )
        self.multi_professional_markets_enabled = multi_professional_markets_enabled
        if (type(compound_procurement_enabled) is not bool or
                (compound_procurement_enabled and
                 not multi_professional_markets_enabled)):
            raise ValueError(
                "compound_procurement_enabled requires "
                "multi_professional_markets_enabled=True"
            )
        self.compound_procurement_enabled = compound_procurement_enabled
        if type(supply_enabled) is not bool or (supply_enabled and not agriculture_enabled):
            raise ValueError("supply_enabled requires opt-in agriculture_enabled")
        self.supply_enabled = supply_enabled

    def advance(self, world_id: str, *, seconds: int, command_id: str,
                expected_revision: int,
                player_observer_id: str | None = None) -> LivingAdvanceResult:
        self.clock._require_session(world_id)
        if type(seconds) is not int or seconds <= 0:
            raise ValueError('seconds must be a positive integer')
        if not isinstance(command_id, str) or not command_id:
            raise ValueError('command ID is required')
        if type(expected_revision) is not int or expected_revision < 0:
            raise ValueError('expected revision must be nonnegative')
        if self.store.db.execute('SELECT 1 FROM commands WHERE world_id=? AND command_id=?',
                                 (world_id, command_id)).fetchone():
            raise DuplicateCommand('living-world command already executed')
        original = self.store.load(world_id)
        if original.revision != expected_revision:
            from .store import RevisionConflict
            raise RevisionConflict(f'expected {expected_revision}, current {original.revision}')
        if player_observer_id is not None:
            if (type(player_observer_id) is not str
                    or not command_id.startswith('player-wait:')
                    or player_observer_id not in original.entities
                    or original.entities[player_observer_id]['controller'] != 'player'):
                raise PermissionError('witness must be an existing player during their wait')
        target = original.time + seconds
        current = original
        events: list[DomainEvent] = []
        started: list[str] = []
        completed: list[str] = []
        fired: list[str] = []
        interrupted = False
        social_messages: list[str] = []
        assistance_transitions: list[tuple[str, str]] = []
        meals_consumed: list[str] = []
        recorded_player_sighting = False
        gathered_actions: list[str] = []
        knowledge_shares: list[str] = []
        economic_jobs: list[str] = []
        economic_offers: list[str] = []
        economic_trades: list[str] = []

        def append(event: DomainEvent, *, action_capability: bool = False,
                   movement_capability: bool = False,
                   social_capability: bool = False,
                   assistance_capability: bool = False,
                   consumption_capability: bool = False,
                   survival_capability: bool = False,
                   production_capability: bool = False,
                   market_capability: bool = False,
                   agriculture_capability: bool = False,
                   supply_capability: bool = False) -> None:
            nonlocal current
            # Keep the entire high-level command fail-closed and bounded.
            if len(events) >= self.max_events_per_advance:
                raise AdvanceLimitExceeded('autonomous simulation event budget exhausted')
            try:
                current = apply_event(current, event, action_authorized=action_capability,
                                      movement_authorized=movement_capability,
                                      social_authorized=social_capability,
                                      assistance_authorized=assistance_capability,
                                      consumption_authorized=consumption_capability,
                                      survival_authorized=survival_capability,
                                      production_authorized=production_capability,
                                      market_authorized=market_capability,
                                      agriculture_authorized=agriculture_capability,
                                      supply_authorized=supply_capability)
            except (ValueError, TypeError) as exc:
                raise InvalidEvent(str(exc)) from exc
            events.append(event)

        while True:
            # Scheduled occurrences at the current tick always have priority
            # over newly planned NPC decisions. Stable ordering is persisted.
            due = sorted(((ident, item) for ident, item in current.scheduled.items()
                          if item['due'] == current.time),
                         key=lambda x: (x[1]['order'], x[0]))
            if due:
                ident, item = due[0]
                append(DomainEvent('ScheduledEventFired', None,
                                   'scheduled signal became due', current.time, {'id': ident}))
                fired.append(ident)
                if '__npc_action_id' in item['payload']:
                    finished_id = item['payload']['__npc_action_id']
                    completed.append(finished_id)
                    if self.gathering_enabled:
                        # The scheduled investigate completion is authoritative:
                        # its event has already projected effort and time cost.
                        # Each contender now observes ONLY the remaining food
                        # at its own site, in durable due-signal order.
                        intent = choose_gathering_intent(current, finished_id)
                        if intent is not None:
                            append(DomainEvent(
                                'NPCFoodGathered', intent.npc_id,
                                'autonomous local recovery after completed investigation',
                                current.time,
                                {'npc_id': intent.npc_id,
                                 'action_id': intent.action_id,
                                 'site_id': intent.site_id}),
                                action_capability=True)
                            gathered_actions.append(intent.action_id)
                    if self.knowledge_enabled:
                        action_info = current.actions.get(finished_id) if isinstance(finished_id, str) else None
                        if (action_info is not None and action_info["action"] == "forage"
                                and action_info["status"] == "completed"):
                            who = action_info["npc_id"]
                            site = current.entities[who]["location_id"]
                            for event in make_observation_events(current, who, site, current.time, 'forage'):
                                append(event)
                                if event.event_type == 'NPCInformationDelivered':
                                    knowledge_shares.append(event.data['delivery_id'])
                # A travel completion has a "__npc_travel_id" payload, never
                # "__npc_action_id". Handle it as a sibling of action completion
                # so arrival observations cannot be skipped.
                if '__npc_travel_id' in item['payload'] and self.knowledge_enabled:
                    travel_id = item['payload']['__npc_travel_id']
                    travel = current.travels.get(travel_id) if isinstance(travel_id, str) else None
                    if (travel is not None and travel['status'] == 'arrived'
                            and travel['arrived_at'] == current.time):
                        who = travel['npc_id']
                        site = current.entities[who]['location_id']
                        for event in make_observation_events(current, who, site, current.time, 'arrival'):
                            append(event)
                            if event.event_type == 'NPCInformationDelivered':
                                knowledge_shares.append(event.data['delivery_id'])
                if item['interrupt']:
                    interrupted = True
                    break
                continue

            busy = {a['npc_id'] for a in current.actions.values()
                    if a['status'] == 'running'}
            busy.update(t['npc_id'] for t in current.travels.values()
                        if t['status'] == 'traveling')
            busy.update(j['npc_id'] for j in current.production_jobs.values()
                        if j['status'] == 'running')
            if self.supply_enabled:
                # A courier may transfer exactly one local unit at an authentic
                # stop and then traverse a physically configured adjacent road.
                for courier in sorted(current.supply_circuits):
                    for _ in range(2):
                        act = choose_cargo(current, courier)
                        if act is None:
                            break
                        rec = current.supply_circuits[courier]
                        if act == "SupplyCargoDelivered":
                            resource = rec["carry"]["resource"]
                        else:
                            resource = {0:"water", 1:"grain", 2:"food",
                                        3:"coin_copper", 4:"coin_copper"}[rec["index"]]
                        append(DomainEvent(act, courier,
                                           "courier physically transfers known local owned cargo",
                                           current.time,
                                           {"courier_id": courier,
                                            "resource": resource}),
                               supply_capability=True)
                    # Survey only the currently visible adjacent roads
                    # BEFORE selecting the next leg. Otherwise an existing
                    # navigation profile blocks discovery of the next road.
                    if needs_survey(current, courier):
                        append(DomainEvent("NPCNavigationSurveyed", courier,
                            "courier learns locally adjacent professional road",
                            current.time, {"npc_id": courier}),
                            movement_capability=True)
                    journey = choose_courier_leg(current, courier)
                    if journey is None:
                        continue
                    rid, origin, destination, due_at = journey
                    tid = f"supply-trip:{courier}:{current.time}"
                    sid = "npc-travel:" + tid
                    if tid in current.travels or sid in current.scheduled:
                        raise InvalidEvent("duplicate professional cargo journey")
                    append(DomainEvent("ScheduledEventCreated", None,
                        "authentic scheduled courier arrival", current.time,
                        {"id": sid, "due": due_at,
                         "order": current.next_schedule_order, "kind": "signal",
                         "payload": {"__npc_travel_id": tid},
                         "interrupt": False}), movement_capability=True)
                    append(DomainEvent("NPCTravelStarted", courier,
                        "courier traverses one surveyed adjacent road", current.time,
                        {"id": tid, "npc_id": courier,
                         "route_id": rid, "origin": origin,
                         "destination": destination, "due": due_at,
                         "schedule_id": sid}), movement_capability=True)
                    busy.add(courier)
            if self.economic_enabled:
                # PLAY-41: money already walked by a real courier can pay
                # *one completed, pre-agreed job* locally. A job remains
                # unpaid without site funds or a physically present worker.
                # Settlement happens before new production reservations.
                for job_id in sorted(current.production_jobs):
                    wage = choose_local_production_wage(current, job_id)
                    if wage is None:
                        continue
                    append(DomainEvent("ProductionWagePaid", None,
                        "locally funded, one-time completed labor receipt",
                        current.time, {"job_id": job_id, "amount": wage}),
                        production_capability=True)
                if (self.professional_procurement_enabled or
                        self.multi_professional_markets_enabled):
                    from .professional_trade import choose_workshop_input_deposit
                    if self.multi_professional_markets_enabled:
                        from .multi_professional_trade import (
                            choose_workshop_material_deposit as choose_workshop_input_deposit)
                    if self.compound_procurement_enabled:
                        from .compound_professional_trade import (
                            has_compound_recipe, choose_compound_deposit)
                        old_deposit = choose_workshop_input_deposit
                        def choose_workshop_input_deposit(state, worker):
                            return (choose_compound_deposit(state, worker)
                                    if has_compound_recipe(state, worker)
                                    else old_deposit(state, worker))
                    # A purchased bag item is still private property until
                    # physically deposited; only then may ordinary production
                    # consume workshop-owned grain on the same local tick.
                    for worker_id in sorted(current.npcs):
                        intent = choose_workshop_input_deposit(current, worker_id)
                        if intent is None:
                            continue
                        append(DomainEvent('WorkshopMaterialDeposited', worker_id,
                            'autonomous physically delivered professional input',
                            current.time,
                            {'site_id': intent.site_id, 'resource': intent.resource,
                             'quantity': intent.quantity}),
                            production_capability=True, market_capability=True)
                # PLAY-24: pure NPC proposals, executed through the SAME reducer
                # capabilities as explicit local production and market commands.
                # Each pass sees only state already changed by previous events.
                for worker_id in sorted(current.npcs):
                    intent = choose_local_production(current, worker_id,
                                                     agriculture_enabled=self.agriculture_enabled)
                    if intent is None:
                        continue
                    append(DomainEvent('ProductionStarted', worker_id,
                                       'autonomous production: ' + intent.reason,
                                       current.time,
                                       {'id': intent.job_id, 'recipe_id': intent.recipe_id,
                                        'npc_id': worker_id}), production_capability=True)
                    economic_jobs.append(intent.job_id)
                    busy.add(worker_id)
                if self.agriculture_enabled:
                    for site in sorted(current.farm_plots):
                        if choose_local_growth(current, site):
                            append(DomainEvent("CropGrowthStarted", None,
                                "local seedling grows using finite water and time",
                                current.time, {"site_id": site}),
                                agriculture_capability=True)
                if self.adaptive_market_enabled:
                    for keeper_id in sorted(current.npcs):
                        stale = choose_local_offer_retirement(current, keeper_id)
                        if stale is not None:
                            append(DomainEvent('MarketOfferClosed', keeper_id,
                                    'autonomous retired impossible quote: ' + stale.reason,
                                    current.time, {'id': stale.offer_id}),
                                    market_capability=True)
                if (self.professional_procurement_enabled or
                        self.multi_professional_markets_enabled):
                    from .professional_trade import choose_local_grain_offer
                    if self.multi_professional_markets_enabled:
                        from .multi_professional_trade import (
                            choose_local_material_offer as choose_local_grain_offer)
                    if self.compound_procurement_enabled:
                        from .compound_professional_trade import choose_charcoal_offer
                        old_offer = choose_local_grain_offer
                        def choose_local_grain_offer(state, keeper):
                            return (old_offer(state, keeper)
                                    or choose_charcoal_offer(state, keeper))
                    for keeper_id in sorted(current.npcs):
                        grain = choose_local_grain_offer(current, keeper_id)
                        if grain is None:
                            continue
                        append(DomainEvent('MarketOfferPosted', keeper_id,
                            'real farmer offers locally owned grain; ' + grain.reason,
                            current.time,
                            {'id': grain.offer_id, 'seller_id': keeper_id,
                             'stock_owner_id': grain.site_id,
                             'site_id': grain.site_id,
                             'resource': (grain.resource if self.multi_professional_markets_enabled
                                          else 'grain'),
                             'quantity': grain.quantity,
                             'payment_resource': 'coin_copper',
                             'unit_price': grain.unit_price}),
                             market_capability=True)
                        economic_offers.append(grain.offer_id)
                for keeper_id in sorted(current.npcs):
                    quote = choose_local_food_offer(
                        current, keeper_id, adaptive=self.adaptive_market_enabled)
                    if quote is None:
                        continue
                    append(DomainEvent('MarketOfferPosted', keeper_id,
                                       'autonomous market: ' + quote.reason,
                                       current.time,
                                       {'id': quote.offer_id, 'seller_id': keeper_id,
                                        'stock_owner_id': quote.site_id,
                                        'site_id': quote.site_id, 'resource': 'food',
                                        'quantity': quote.quantity,
                                        'payment_resource': 'coin_copper',
                                        'unit_price': quote.unit_price}),
                           market_capability=True)
                    economic_offers.append(quote.offer_id)
                for buyer_id in sorted(current.npcs):
                    purchase = choose_local_food_purchase(
                        current, buyer_id, adaptive=self.adaptive_market_enabled)
                    if purchase is None:
                        continue
                    append(DomainEvent('MarketTradeExecuted', buyer_id,
                                       'autonomous purchase: ' + purchase.reason,
                                       current.time,
                                       {'id': purchase.trade_id,
                                        'offer_id': purchase.offer_id,
                                        'buyer_id': buyer_id, 'quantity': 1,
                                        'expected_unit_price': purchase.price}),
                           market_capability=True)
                    economic_trades.append(purchase.trade_id)
                if (self.professional_procurement_enabled or
                        self.multi_professional_markets_enabled):
                    from .professional_trade import choose_local_grain_purchase
                    if self.multi_professional_markets_enabled:
                        from .multi_professional_trade import (
                            choose_local_material_purchase as choose_local_grain_purchase)
                    if self.compound_procurement_enabled:
                        from .compound_professional_trade import (
                            has_compound_recipe, choose_compound_purchase)
                        old_purchase = choose_local_grain_purchase
                        def choose_local_grain_purchase(state, buyer):
                            return (choose_compound_purchase(state, buyer)
                                    if has_compound_recipe(state, buyer)
                                    else old_purchase(state, buyer))
                    for buyer_id in sorted(current.npcs):
                        grain_buy = choose_local_grain_purchase(current, buyer_id)
                        if grain_buy is None:
                            continue
                        append(DomainEvent('MarketTradeExecuted', buyer_id,
                            'on-site professional grain purchase; ' + grain_buy.reason,
                            current.time,
                            {'id': grain_buy.trade_id,
                             'offer_id': grain_buy.offer_id, 'buyer_id': buyer_id,
                             'quantity': 1,
                             'expected_unit_price': grain_buy.unit_price}),
                             market_capability=True)
                        economic_trades.append(grain_buy.trade_id)
                    # A baker paid only after its real bread sale must receive
                    # those earnings at the sale's SAME logical tick. Otherwise
                    # a single 900-second wait delays wage/procurement to 900,
                    # while many short waits pay at 211 and start a second job.
                    # Keep this second pass strictly behind the opt-in flag;
                    # it uses the same existing once-only production reducer.
                    for job_id in sorted(current.production_jobs):
                        wage = choose_local_production_wage(current, job_id)
                        if wage is None:
                            continue
                        append(DomainEvent('ProductionWagePaid', None,
                            'same-tick sale-backed professional wage',
                            current.time, {'job_id': job_id, 'amount': wage}),
                            production_capability=True)
            if self.assistance_enabled:
                # The fixed passes are independent of lexical NPC ID ordering:
                # settle old promises, then respond, request, and respond to
                # requests created in this tick. A provider can only make one
                # choice per tick; physical delivery requires a later tick.
                acted: set[str] = {
                    j['npc_id'] for j in current.production_jobs.values()
                    if j['status'] == 'running'
                }
                for phase in ('settle', 'respond', 'request', 'respond'):
                    for actor_id in sorted(current.npcs):
                        if actor_id in acted:
                            continue
                        intent = choose_assistance_intent(
                            current, actor_id, phase,
                            scarcity_enabled=self.scarcity_enabled)
                        if intent is None:
                            continue
                        append(DomainEvent(intent.event_type, actor_id,
                            'autonomous assistance: ' + intent.reason, current.time,
                            {'id': intent.request_id, **intent.fields}),
                            assistance_capability=True)
                        acted.add(actor_id)
                        assistance_transitions.append((intent.request_id,
                                                       current.obligations[intent.request_id]['status']))
            if self.consumption_enabled:
                # An actual meal debits food and relieves that NPC's hunger in
                # one event. Do not mistake inventory ownership for eating.
                for npc_id in sorted(current.npcs):
                    # A worker cannot eat during the very production job that
                    # physically occupies them in this opt-in economic mode.
                    # Older survival worlds keep their existing decision order.
                    if self.economic_enabled and any(
                            job['npc_id'] == npc_id and job['status'] == 'running'
                            for job in current.production_jobs.values()):
                        continue
                    # The consumption policy and reducer subtract any consigned
                    # food parcel before checking personal ownership. A courier
                    # may eat only their own surplus, never customer cargo.
                    quantity = choose_food_consumption(current, npc_id)
                    if quantity is None:
                        continue
                    meal_id = _meal_id(npc_id, current.time)
                    # PLAY-16: record an adjacent verified sighting only when
                    # a human player is actually present at this meal's tick.
                    if player_observer_id is not None:
                        from .movement import _in_transit, _visible
                        visible_state = current.to_dict()
                        place = visible_state['entities'][player_observer_id]['location_id']
                        if (not _in_transit(visible_state, player_observer_id)
                                and not _in_transit(visible_state, npc_id)
                                and place == visible_state['entities'][npc_id]['location_id']):
                            append(DomainEvent('PlayerObserved', player_observer_id,
                                               'player witnessed a nearby NPC eating',
                                               current.time,
                                               {'location_id': place,
                                                'occupants': _visible(visible_state, place)}),
                                   movement_capability=True)
                            recorded_player_sighting = True
                    append(DomainEvent('NPCFoodConsumed', npc_id,
                                       'NPC ate owned food to relieve personal hunger',
                                       current.time,
                                       {'id': meal_id, 'npc_id': npc_id, 'quantity': quantity}),
                           consumption_capability=True)
                    meals_consumed.append(meal_id)
            if (self.professional_procurement_enabled or
                    self.multi_professional_markets_enabled):
                from .professional_trade import (has_workshop_recipe,
                    choose_professional_known_road)
                if self.multi_professional_markets_enabled:
                    from .multi_professional_trade import (
                        has_material_workshop_recipe as has_workshop_recipe,
                        choose_material_known_road as choose_professional_known_road)
                if self.compound_procurement_enabled:
                    from .compound_professional_trade import (
                        has_compound_recipe, choose_compound_known_road)
                    old_has, old_walk = has_workshop_recipe, choose_professional_known_road
                    def has_workshop_recipe(state, worker):
                        return (has_compound_recipe(state, worker)
                                or old_has(state, worker))
                    def choose_professional_known_road(state, worker):
                        return (choose_compound_known_road(state, worker)
                                if has_compound_recipe(state, worker)
                                else old_walk(state, worker))
                for buyer_id in sorted(current.npcs):
                    if buyer_id in busy or not has_workshop_recipe(current, buyer_id):
                        continue
                    if needs_survey(current, buyer_id):
                        append(DomainEvent('NPCNavigationSurveyed', buyer_id,
                            'professional learns only roads visible from current site',
                            current.time, {'npc_id': buyer_id}),
                            movement_capability=True)
                    journey = choose_professional_known_road(current, buyer_id)
                    if journey is None:
                        continue
                    edge = current.routes[journey.route_id]
                    here = current.entities[buyer_id]['location_id']
                    there = edge['b'] if edge['a'] == here else edge['a']
                    tid = f'auto-nav:{buyer_id}:{current.time}'
                    sid = 'npc-travel:' + tid
                    if tid in current.travels or sid in current.scheduled:
                        raise InvalidEvent('duplicate professional travel identifier')
                    append(DomainEvent('ScheduledEventCreated', None,
                        'professional known-road journey arrival',
                        current.time,
                        {'id': sid, 'due': current.time + edge['seconds'],
                         'order': current.next_schedule_order, 'kind': 'signal',
                         'payload': {'__npc_travel_id': tid}, 'interrupt': False}),
                         movement_capability=True)
                    append(DomainEvent('NPCTravelStarted', buyer_id,
                        'professional input procurement; ' + journey.reason,
                        current.time,
                        {'id': tid, 'npc_id': buyer_id,
                         'route_id': journey.route_id,
                         'origin': here, 'destination': there,
                         'due': current.time + edge['seconds'],
                         'schedule_id': sid}),
                         movement_capability=True)
                    busy.add(buyer_id)
            if self.shopping_routes_enabled:
                # PLAY-42: only hungry solvent NPCs look for a LOCAL market.
                # An unvisited road can be surveyed only from their real site;
                # each physical leg has a deterministic clock cost. This
                # pass neither reads a distant quote nor reserves food.
                for shopper_id in sorted(current.npcs):
                    # Physically reaching a market is a FIRST-HAND visit even
                    # if the buyer cannot afford anything. Record its nearby
                    # roads and visited tile once, preventing a hungry worker
                    # from rediscovering the same market after returning home.
                    market_here = current.entities[shopper_id]['location_id']
                    if (shopper_id not in busy and market_here in current.market_stalls
                            and any(t['npc_id'] == shopper_id
                                    and t['status'] == 'arrived'
                                    and t['destination'] == market_here
                                    for t in current.travels.values())
                            and needs_survey(current, shopper_id)):
                        append(DomainEvent('NPCNavigationSurveyed', shopper_id,
                            'shopper surveys the physically reached local market',
                            current.time, {'npc_id': shopper_id}),
                            movement_capability=True)
                    # An initiated homeward journey has priority over a
                    # second hungry exploration impulse at each intermediate
                    # road tile. This remains a pure projection of completed
                    # physical travel history; no teleport or new schema.
                    walk = choose_known_market_return(current, shopper_id)
                    if walk is None and wants_local_market(current, shopper_id):
                        if needs_survey(current, shopper_id):
                            append(DomainEvent('NPCNavigationSurveyed', shopper_id,
                                'shopper sees roads adjoining their physical location',
                                current.time, {'npc_id': shopper_id}),
                                movement_capability=True)
                        walk = choose_known_market_walk(current, shopper_id)
                    if walk is None:
                        continue
                    route = current.routes[walk.route_id]
                    here = current.entities[shopper_id]['location_id']
                    there = route['b'] if route['a'] == here else route['a']
                    tid = f'auto-nav:{shopper_id}:{current.time}'
                    if tid in current.travels:
                        raise InvalidEvent('duplicate market shopping travel ID')
                    due_at = current.time + route['seconds']
                    sid = 'npc-travel:' + tid
                    append(DomainEvent('ScheduledEventCreated', None,
                        'physical market search arrival appointment', current.time,
                        {'id': sid, 'due': due_at,
                         'order': current.next_schedule_order, 'kind': 'signal',
                         'payload': {'__npc_travel_id': tid}, 'interrupt': False}),
                         movement_capability=True)
                    append(DomainEvent('NPCTravelStarted', shopper_id,
                        walk.reason, current.time,
                        {'id': tid, 'npc_id': shopper_id, 'route_id': walk.route_id,
                         'origin': here, 'destination': there, 'due': due_at,
                         'schedule_id': sid}), movement_capability=True)
                    busy.add(shopper_id)
            if self.knowledge_enabled:
                # Bounded, deterministic food-knowledge sharing pass. Never
                # touches next_decision_at, never adds to busy, never emits a
                # decision; it is a pure sharing limit, not a decision delay.
                busy_now = {a['npc_id'] for a in current.actions.values()
                            if a['status'] == 'running'}
                busy_now.update(t['npc_id'] for t in current.travels.values()
                                if t['status'] == 'traveling')
                # One frozen per-round proposal, one recipient/site delivery.
                # No instantaneous re-sharing of newly acquired hearsay.
                for event in choose_food_sharing_round(current):
                    append(event)
                    if event.event_type == "NPCInformationDelivered":
                        knowledge_shares.append(event.data["delivery_id"])
            if self.rumors_enabled:
                # Frozen-source planning: no same-tick rumor amplification.
                for event in choose_rumor_round(current):
                    append(event, social_capability=True)
            # Deterministic tie breaking between independently eligible NPCs.
            for npc_id in sorted(current.npcs):
                if self.economy_only_enabled:
                    break  # Focused economic endurance, not full village life.
                if npc_id in busy:
                    continue
                existing = current.npcs[npc_id]['last_decision']
                pending_action = existing is not None and existing['at'] == current.time
                # A social exchange is an instantaneous *speech act*, not an
                # executed favor. Both events share this one authorized command.
                if self.social_enabled and not pending_action:
                    intent = choose_social_intent(current, npc_id,
                                                  cooldown=self.social_cooldown)
                    if intent is not None:
                        message_id = f'auto-social:{npc_id}:{current.time}'
                        if message_id in current.social_messages:
                            raise InvalidEvent('autonomous social message ID collision')
                        # PLAY-18: the waiting human witnesses only that two
                        # physically nearby NPCs spoke, never their words,
                        # intentions or private relationship changes.
                        if player_observer_id is not None:
                            from .movement import _in_transit, _visible
                            visible_state = current.to_dict()
                            place = visible_state['entities'][player_observer_id]['location_id']
                            if (not _in_transit(visible_state, player_observer_id)
                                    and not _in_transit(visible_state, npc_id)
                                    and not _in_transit(visible_state, intent.recipient_id)
                                    and place == visible_state['entities'][npc_id]['location_id']
                                    == visible_state['entities'][intent.recipient_id]['location_id']):
                                append(DomainEvent('PlayerObserved', player_observer_id,
                                    'player witnessed nearby NPCs speaking', current.time,
                                    {'location_id': place,
                                     'occupants': _visible(visible_state, place)}),
                                    movement_capability=True)
                                recorded_player_sighting = True
                        append(DomainEvent('SocialMessageSent', npc_id,
                            f'autonomous social initiative: {intent.reason}', current.time,
                            {'id': message_id, 'recipient': intent.recipient_id,
                             'kind': intent.kind, 'text': intent.text}), social_capability=True)
                        append(DomainEvent('SocialMessageReceived', intent.recipient_id,
                            'autonomous local recipient acknowledges the speech act',
                            current.time, {'id': message_id}), social_capability=True)
                        social_messages.append(message_id)
                # New 01-S survival intent must be considered before starting
                # optional autonomous exploration/travel. Otherwise a hungry
                # NPC ignores visible food here whenever a road is available.
                # The same pure predicate is used later by choose_action and
                # event replay; it inspects this NPC plus this site only.
                from .npc import _injury_rest_decision
                injury_requires_rest = (
                    _injury_rest_decision(current.injuries, npc_id) is not None)
                local_forage_wins = False
                if self.foraging_enabled and not pending_action and not injury_requires_rest:
                    from .foraging import choose_local_foraging
                    local_site = current.entities[npc_id]['location_id']
                    local_forage_wins = choose_local_foraging(
                        npc_id, current.npcs[npc_id], local_site,
                        current.resources) is not None
                if (self.navigation_enabled and not pending_action
                        and not local_forage_wins and not injury_requires_rest
                        and not (self.routines_enabled and npc_id in current.npc_routines
                                 and (current.npcs[npc_id]["needs"]["fatigue"] >= 70
                                      or current.npcs[npc_id]["needs"]["hunger"] >= 75
                                      or current.npcs[npc_id]["needs"]["safety"] >= 75))):
                    if needs_survey(current, npc_id):
                        append(DomainEvent('NPCNavigationSurveyed', npc_id,
                            'NPC surveys locally observable roads', current.time,
                            {'npc_id': npc_id}), movement_capability=True)
                    food_intent = (
                        choose_food_route(current, npc_id,
                                          scarcity_enabled=self.scarcity_enabled)
                        if self.food_navigation_enabled else None
                    )
                    if (self.food_navigation_enabled
                            and current.time < current.npcs[npc_id]['next_decision_at']):
                        # U-3: both fallback exploration and hungry food travel
                        # respect the previous decision cooldown in opt-in mode.
                        continue
                    routine_intent = (choose_routine_route(current, npc_id)
                                      if self.routines_enabled and food_intent is None
                                      else None)
                    route_id = (food_intent.route_id if food_intent is not None
                                else routine_intent.route_id if routine_intent is not None
                                else (None if self.routines_enabled and npc_id in current.npc_routines
                                      else next_route(current, npc_id)))
                    if route_id is not None:
                        route = current.routes[route_id]
                        here = current.entities[npc_id]['location_id']
                        there = route['b'] if route['a'] == here else route['a']
                        travel_id = f'auto-nav:{npc_id}:{current.time}'
                        if travel_id in current.travels:
                            raise InvalidEvent('autonomous journey identifier collision')
                        due_at = current.time + route['seconds']
                        schedule_id = 'npc-travel:' + travel_id
                        travel_reason = 'autonomous movement over a learned road'
                        if routine_intent is not None:
                            travel_reason = (f'{routine_intent.reason}; '
                                             f'destination={routine_intent.destination}')
                        if food_intent is not None:
                            travel_reason = (
                                f'autonomous food journey; belief_site={food_intent.destination}; '
                                f'source={food_intent.source}; observed_at={food_intent.observed_at}; '
                                f'effective_confidence={food_intent.confidence}; '
                                f'known_cost_seconds={food_intent.total_seconds}'
                            )
                        append(DomainEvent('ScheduledEventCreated', None,
                            'scheduled autonomous travel arrival', current.time,
                            {'id': schedule_id, 'due': due_at,
                             'order': current.next_schedule_order, 'kind': 'signal',
                             'payload': {'__npc_travel_id': travel_id}, 'interrupt': False}),
                             movement_capability=True)
                        append(DomainEvent('NPCTravelStarted', npc_id,
                            travel_reason, current.time,
                            {'id': travel_id, 'npc_id': npc_id, 'route_id': route_id,
                             'origin': here, 'destination': there, 'due': due_at,
                             'schedule_id': schedule_id}), movement_capability=True)
                        busy.add(npc_id)
                        continue
                # A prior NPCService.decide call can leave a valid, unstarted
                # intention at this exact tick. Execute it rather than waiting
                # for its decision cooldown and silently leaving the NPC idle.
                profile = current.npcs[npc_id]
                pending = profile['last_decision']
                if pending is not None and pending['at'] == current.time:
                    verb = pending['action']
                else:
                    decision = choose_action(current, npc_id, survival_enabled=self.survival_enabled,
                                             foraging_enabled=self.foraging_enabled)
                    if decision is None:
                        continue
                    verb = decision.action
                if (verb == 'work' and not routine_allows_work(current, npc_id)):
                    # The strict action reducer checks configured work shifts even
                    # when autonomous routine/navigation planning is disabled.
                    # Mirror that invariant here to avoid aborting a whole
                    # atomic world advance for an otherwise harmless choice.
                    continue
                # The deterministic ID may not be reused, even after completion.
                action_id = f'auto:{npc_id}:{current.time}'
                if action_id in current.actions:
                    raise InvalidEvent('autonomous action identifier collision')
                if pending is None or pending['at'] != current.time:
                    append(DomainEvent('NPCDecisionRecorded', npc_id,
                                       'deterministic autonomous NPC policy', current.time,
                                       {'npc_id': npc_id, 'action': decision.action,
                                        'score': decision.score, 'reason': decision.reason,
                                        'next_decision_at': current.time + self.decision_cooldown,
                                        **({'policy': 'local-forage-v1'}
                                           if decision.action == 'forage' else {})}),
                           survival_capability=self.survival_enabled,
                           action_capability=decision.action == 'forage')
                schedule_id = 'npc-action:' + action_id
                action_due = current.time + DURATIONS[verb]
                append(DomainEvent('ScheduledEventCreated', None,
                                   'autonomous NPC action completion appointment', current.time,
                                   {'id': schedule_id, 'due': action_due,
                                    'order': current.next_schedule_order, 'kind': 'signal',
                                    'payload': {'__npc_action_id': action_id},
                                    'interrupt': False}), action_capability=True)
                append(DomainEvent('NPCActionStarted', npc_id,
                                   'autonomous NPC action began', current.time,
                                   {'action_id': action_id, 'npc_id': npc_id,
                                    'action': verb, 'schedule_id': schedule_id,
                                    'due': action_due}), action_capability=True)
                started.append(action_id)
                busy.add(npc_id)

            if current.time >= target:
                break
            # Schedule both completed actions and re-evaluations of idle NPCs.
            next_ticks = [target]
            next_ticks.extend(item['due'] for item in current.scheduled.values())
            if self.supply_enabled:
                resume = next_courier_departure(current)
                if resume is not None:
                    next_ticks.append(resume)
            if self.routines_enabled or self.agriculture_enabled:
                next_boundary = next_routine_boundary(current)
                if next_boundary is not None:
                    next_ticks.append(next_boundary)
            if not self.economy_only_enabled:
                next_ticks.extend(profile['next_decision_at'] for npc_id, profile
                                  in current.npcs.items()
                                  if npc_id not in busy
                                  and profile['next_decision_at'] > current.time)
            next_tick = min(t for t in next_ticks if t > current.time)
            append(DomainEvent('TimeAdvanced', None, 'authorized player time',
                               next_tick, {'from': current.time, 'to': next_tick}),
                   survival_capability=self.survival_enabled)

        # A complete unit of work: no partial SQLite commits for multiple NPCs.
        committed = self.store.append(world_id, command_id, expected_revision, events,
                                      clock_authorized=True, npc_authorized=True,
                                      action_authorized=True,
                                      movement_authorized=(self.navigation_enabled or self.supply_enabled or recorded_player_sighting),
                                      social_authorized=(self.social_enabled or self.rumors_enabled),
                                      assistance_authorized=self.assistance_enabled,
                                      consumption_authorized=self.consumption_enabled,
                                      survival_authorized=self.survival_enabled,
                                      production_authorized=self.economic_enabled,
                                      market_authorized=self.economic_enabled,
                                      agriculture_authorized=self.agriculture_enabled,
                                      supply_authorized=self.supply_enabled)
        elapsed = committed.time - original.time
        return LivingAdvanceResult(committed, seconds, elapsed, seconds - elapsed,
                                   tuple(started), tuple(completed), tuple(fired),
                                   interrupted, len(events), tuple(social_messages),
                                   tuple(assistance_transitions), tuple(meals_consumed),
                                   tuple(gathered_actions), tuple(knowledge_shares),
                                   tuple(economic_jobs), tuple(economic_offers),
                                   tuple(economic_trades))
