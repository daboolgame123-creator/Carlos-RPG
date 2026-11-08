"""Auditable NPC food consumption; ownership is not the same as satiation.

One atomic event both debits *known owned food* and reduces that NPC's hunger.
This is a prototype, not timed chewing, spoilage, nutrition or medical logic.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from .domain import DomainEvent, WorldState
from .store import RevisionConflict, SQLiteEventStore
from .time_engine import TimeEngine

HUNGER_RELIEF_PER_FOOD = 25
AUTONOMOUS_EATING_THRESHOLD = 50
MAX_MEAL_QUANTITY = 3


def _reserved_food(circuits: Any, npc_id: str) -> int:
    """Contract ownership has priority over the courier's food balance."""
    contract = circuits.get(npc_id)
    parcel = contract["carry"] if contract is not None else None
    return int(parcel is not None and parcel["resource"] == "food")


def _available(state: Any, npc_id: str) -> bool:
    if npc_id not in state.npcs:
        return False
    if any(t['npc_id'] == npc_id and t['status'] == 'traveling'
           for t in state.travels.values()):
        return False
    if any(a['npc_id'] == npc_id and a['status'] == 'running'
           for a in state.actions.values()):
        return False
    if any(j['npc_id'] == npc_id and j['status'] == 'running'
           for j in state.production_jobs.values()):
        return False
    return True


def _meal_id(npc_id: str, at: int) -> str:
    name = f'meal:{npc_id}:{at}'
    return name if len(name) <= 128 else 'meal:' + sha256(name.encode('utf-8')).hexdigest()


def validate_consumptions(state: dict[str, Any]) -> None:
    seen: set[tuple[str, int]] = set()
    for ident, meal in state['consumptions'].items():
        if (not isinstance(ident, str) or not ident or len(ident) > 128
                or not isinstance(meal, dict) or set(meal) != {
                    'npc_id', 'resource', 'quantity', 'location_id', 'consumed_at',
                    'food_before', 'food_after', 'hunger_before', 'hunger_after'}):
            raise ValueError('invalid meal ledger record')
        npc = meal['npc_id']
        if (npc not in state['npcs'] or meal['resource'] != 'food'
                or meal['location_id'] not in state['locations']
                or type(meal['consumed_at']) is not int
                or not 0 <= meal['consumed_at'] <= state['time']
                or type(meal['quantity']) is not int
                or not 1 <= meal['quantity'] <= MAX_MEAL_QUANTITY):
            raise ValueError('invalid meal actor or timing')
        if (npc, meal['consumed_at']) in seen:
            raise ValueError('an NPC can eat at most once per logical tick')
        seen.add((npc, meal['consumed_at']))
        before, after = meal['food_before'], meal['food_after']
        hungry, fed = meal['hunger_before'], meal['hunger_after']
        if (any(type(x) is not int for x in (before, after, hungry, fed))
                or before < meal['quantity'] or after < 0
                or not 0 < hungry <= 100 or not 0 <= fed <= 100
                or after != before - meal['quantity']
                or fed != max(0, hungry - HUNGER_RELIEF_PER_FOOD * meal['quantity'])
                or meal['quantity'] > (hungry + HUNGER_RELIEF_PER_FOOD - 1) // HUNGER_RELIEF_PER_FOOD):
            raise ValueError('invalid consumption conservation or hunger effect')


def project_food_consumed(state: dict[str, Any], event: DomainEvent, *, consumption_authorized: bool) -> None:
    payload = event.data
    if not consumption_authorized or set(payload) != {'id', 'npc_id', 'quantity'}:
        raise ValueError('eating requires a trusted food-consumption capability')
    npc_id, meal_id, quantity = payload['npc_id'], payload['id'], payload['quantity']
    if (not isinstance(npc_id, str) or npc_id not in state['npcs']
            or event.actor_id != npc_id or not isinstance(meal_id, str)
            or not meal_id or len(meal_id) > 128
            or type(quantity) is not int or not 1 <= quantity <= MAX_MEAL_QUANTITY):
        raise ValueError('invalid food-consumption actor, meal ID or quantity')
    if meal_id != _meal_id(npc_id, state['time']):
        raise ValueError('meal ID must match the NPC and current logical time')
    if (any(t['npc_id'] == npc_id and t['status'] == 'traveling'
            for t in state['travels'].values())
            or any(a['npc_id'] == npc_id and a['status'] == 'running'
                   for a in state['actions'].values())
            or any(j['npc_id'] == npc_id and j['status'] == 'running'
                   for j in state['production_jobs'].values())):
        raise ValueError('NPC cannot eat while traveling or actively busy')
    if any(m['npc_id'] == npc_id and m['consumed_at'] == state['time']
           for m in state['consumptions'].values()):
        raise ValueError('cannot eat twice in the same simulation tick')
    if meal_id in state['consumptions']:
        raise ValueError('duplicate meal ID')
    available = state['resources'].get(npc_id, {}).get('food')
    hunger = state['npcs'][npc_id]['needs']['hunger']
    reserved = _reserved_food(state['supply_circuits'], npc_id)
    if type(available) is not int or available - reserved < quantity:
        raise ValueError('eating requires sufficient initialized, unreserved owned food')
    if hunger <= 0 or quantity > (hunger + HUNGER_RELIEF_PER_FOOD - 1) // HUNGER_RELIEF_PER_FOOD:
        raise ValueError('cannot consume more meals than current hunger warrants')
    new_hunger = max(0, hunger - HUNGER_RELIEF_PER_FOOD * quantity)
    state['resources'][npc_id]['food'] = available - quantity
    state['npcs'][npc_id]['needs']['hunger'] = new_hunger
    state['consumptions'][meal_id] = {
        'npc_id': npc_id, 'resource': 'food', 'quantity': quantity,
        'location_id': state['entities'][npc_id]['location_id'],
        'consumed_at': state['time'], 'food_before': available,
        'food_after': available - quantity, 'hunger_before': hunger,
        'hunger_after': new_hunger,
    }


def choose_food_consumption(state: WorldState, npc_id: str) -> int | None:
    """Pure self-need/own-stock policy. Never inspects any peer's inventory."""
    if not _available(state, npc_id):
        return None
    profile = state.npcs[npc_id]
    own_intention = profile['last_decision']
    if own_intention is not None and own_intention['at'] == state.time:
        return None
    hunger = profile['needs']['hunger']
    stock = state.resources.get(npc_id, {}).get('food')
    if (hunger < AUTONOMOUS_EATING_THRESHOLD or type(stock) is not int
            or stock <= _reserved_food(state.supply_circuits, npc_id)):
        return None
    if any(m['npc_id'] == npc_id and m['consumed_at'] == state.time
           for m in state.consumptions.values()):
        return None
    return 1


@dataclass(frozen=True)
class ConsumptionResult:
    id: str
    consumed_quantity: int
    new_hunger: int
    state: WorldState


class NPCConsumptionService:
    """Trusted local food-eating command; never operates while play is paused."""

    def __init__(self, store: SQLiteEventStore, clock: TimeEngine):
        if clock.store is not store:
            raise ValueError('food consumption and clock must share a store')
        self.store, self.clock = store, clock

    def eat(self, world_id: str, npc_id: str, quantity: int, *, command_id: str,
            expected_revision: int) -> ConsumptionResult:
        self.clock._require_session(world_id)
        state = self.store.load(world_id)
        if state.revision != expected_revision:
            raise RevisionConflict('stale food-consumption revision')
        meal_id = _meal_id(npc_id, state.time)
        saved = self.store.append(world_id, command_id, expected_revision,
            [DomainEvent('NPCFoodConsumed', npc_id, 'NPC ate food from their own inventory',
                         state.time, {'id': meal_id, 'npc_id': npc_id, 'quantity': quantity})],
            consumption_authorized=True)
        return ConsumptionResult(meal_id, quantity, saved.npcs[npc_id]['needs']['hunger'], saved)
