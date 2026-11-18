"""Signed one-copper grain procurement, physically settled at the source farm.

Every claim comes from the cargo reducer's real farm->bakery grain receipt.
No credit, new coins or remote farm-wallet inspection. Bakery cash stays local
until one existing coin travels in custody on that farm's actual return leg.
Earlier receipts reserve scarce surplus before faster couriers can take it.
"""
from __future__ import annotations

from .domain import DomainEvent, WorldState


def _fields(state):
    return ((state.supply_circuits, state.resources, state.market_offers, state.time)
            if isinstance(state, WorldState) else
            (state['supply_circuits'], state['resources'], state['market_offers'], state['time']))


def sign_contract(state: dict, event: DomainEvent, *, bootstrap: bool) -> None:
    p = event.data
    if (not bootstrap or state['time'] != 0 or event.actor_id is not None
            or set(p) != {'courier_id', 'unit_price'}
            or type(p['courier_id']) is not str
            or type(p['unit_price']) is not int or p['unit_price'] != 1):
        raise ValueError('grain price requires explicit trusted prospective one-copper terms')
    c = state['supply_circuits'].get(p['courier_id'])
    if (c is None or 'grain_purchase' in c or 'bread_share_earned' in c
            or c['deliveries'] != 0 or c['carry'] is not None
            or state['resources'].get(p['courier_id'], {}).get('coin_copper') != 0):
        raise ValueError('grain purchase requires a new real cash circuit without overlapping barter')
    c['grain_purchase'] = {'unit_price': 1, 'receipts': []}


def pending_claims(state):
    """Source-fair round robin for actual outstanding, chronologically signed sales.

    A fast farm must not take every scarce payment while a slower farm has a
    legitimate first receipt: settle the first unpaid *service round* for
    each farm before funding another source's later round. Earlier claims
    within a farm still have priority; same-round ties keep actual receipt
    time and ID order. No claim is created, funded or remotely inspected.
    """
    circuits, _, _, _ = _fields(state)
    return sorted((round_number, r['delivered_at'], who, r['delivery'])
                  for who, c in circuits.items() if 'grain_purchase' in c
                  for round_number, r in enumerate(c['grain_purchase']['receipts'])
                  if r['loaded_at'] is None)


def cash_minimum(state, record) -> int:
    """Reserve operating cash, quoted stock, earned wages, and earlier grain."""
    from .supply import _local_unpaid_bakery_wage_reserve
    circuits, _, offers, _ = _fields(state)
    base = 1 + _local_unpaid_bakery_wage_reserve(state)
    base += sum(o['remaining'] for o in offers.values()
                if o['status'] == 'open' and o['stock_owner_id'] == 'bakery'
                and o['resource'] == 'coin_copper')
    queue = pending_claims(state)
    who = next((who for who, c in circuits.items() if c is record), None)
    # Projected and frozen records both retain identity within their own state.
    if who is not None and 'grain_purchase' in record:
        position = next((i for i, (_, _, worker, _) in enumerate(queue) if worker == who), None)
        return base + position + 1 if position is not None else 2**63
    return base + len(queue) + 1


def record_pickup(state: dict, who: str, resource: str) -> None:
    c = state['supply_circuits'][who]
    if 'grain_purchase' not in c or c['index'] != 4 or resource != 'coin_copper':
        return
    receipt = next((r for r in c['grain_purchase']['receipts'] if r['loaded_at'] is None), None)
    if receipt is None:
        raise ValueError('cannot remit copper without actual delivered grain')
    receipt['loaded_at'] = state['time']


def record_delivery(state: dict, who: str, resource: str) -> None:
    c = state['supply_circuits'][who]
    if 'grain_purchase' not in c:
        return
    receipts = c['grain_purchase']['receipts']
    if c['index'] == 2 and resource == 'grain':
        receipts.append({'delivery': c['deliveries'], 'delivered_at': state['time'],
                         'loaded_at': None, 'received_at': None})
    elif c['index'] == 5 and resource == 'coin_copper':
        receipt = next((r for r in receipts if r['loaded_at'] is not None
                        and r['received_at'] is None), None)
        if receipt is None:
            raise ValueError('farm settlement requires its exact in-flight grain payment')
        receipt['received_at'] = state['time']


def validate_contract(state: dict, who: str, circuit: dict) -> None:
    if 'grain_purchase' not in circuit:
        return
    contract = circuit['grain_purchase']
    if (type(contract) is not dict or set(contract) != {'unit_price', 'receipts'}
            or type(contract['unit_price']) is not int or contract['unit_price'] != 1
            or type(contract['receipts']) is not list or 'bread_share_earned' in circuit
            or type(state['resources'].get(who, {}).get('coin_copper')) is not int):
        raise ValueError('invalid signed grain price or overlapping barter')
    last_delivery, last_time, in_flight, unshipped = 0, -1, 0, False
    for r in contract['receipts']:
        if (type(r) is not dict or set(r) != {'delivery', 'delivered_at', 'loaded_at', 'received_at'}
                or type(r['delivery']) is not int
                or not last_delivery < r['delivery'] <= circuit['deliveries']
                or type(r['delivered_at']) is not int
                or not 0 <= r['delivered_at'] <= state['time']
                or r['delivered_at'] < last_time):
            raise ValueError('invalid physical grain purchase evidence')
        loaded, received = r['loaded_at'], r['received_at']
        if loaded is None:
            if received is not None:
                raise ValueError('grain payment cannot arrive without physical pickup')
            unshipped = True
        else:
            if (unshipped or type(loaded) is not int
                    or not r['delivered_at'] <= loaded <= state['time']):
                raise ValueError('grain remittances must load in receipt order')
            if received is None:
                in_flight += 1
            elif type(received) is not int or not loaded <= received <= state['time']:
                raise ValueError('invalid physical grain settlement time')
        last_delivery, last_time = r['delivery'], r['delivered_at']
    cargo = circuit['carry']
    expected = int(cargo is not None and cargo['source'] == 'bakery'
                   and cargo['destination'] == circuit['stops'][5]
                   and cargo['resource'] == 'coin_copper')
    if in_flight != expected:
        raise ValueError('grain settlement must match the actual copper parcel')
