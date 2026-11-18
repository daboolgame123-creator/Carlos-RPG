"""Original PR133 village: unchanged resources, prospective paid livelihoods.

This is an execution/acceptance runner, not a synthetic state intervention.
Control uses the original finite contracts and policies; treatment signs Nora's
prospective cash harvest, recurring actual freight and Salma's existing terms.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from carlos_sim import DomainEvent, SQLiteEventStore, TimeEngine
from carlos_sim.economic_diagnostics import audit_npc_economy, audit_production_wages
from carlos_sim.hydrology import FiniteWaterService
from test_play48_real_watch_income_24h import seed as original_seed, engine, HOUR
from test_play38_multi_farm_couriers import WORLD
from test_play48_finite_hunt_fish_roads import conserve_diverse

CHECKPOINTS = (24, 48, 60, 72, 96, 168)


def seed(path, *, candidate, community_food=False):
    original = original_seed(path)
    def event(kind, data):
        return DomainEvent(kind, None, 'prospective original-site employment terms', 0, data)
    if candidate:
        events = [
            *([event('MarketCommunityRationsSigned',
                     {'site_id': 'market', 'keeper_id': 'salma', 'daily_limit': 2})]
              if community_food else []),
            event('ProductionCashWageSigned', {'recipe_id': 'finite-harvest', 'amount': 2}),
            *[event('GrainPurchaseSigned', {'courier_id': who, 'unit_price': 1})
              for who in ('hana', 'huda')],
            event('MarketStewardFoodContractSigned',
                  {'site_id': 'market', 'keeper_id': 'salma', 'sales_per_wage': 2}),
            # Preserve Huda's genuine original bounded two-grain-service food
            # wage. Rules71's distinct one-coin/source grain purchase stays
            # signed: the crop owner and the courier are different creditors.
            event('CourierProvisionConfigured',
                  {'id': 'huda-future-bakery', 'courier_id': 'huda',
                   'payer_site': 'bakery', 'units': 0, 'authorized_total_units': 2,
                   'deferred_bakery_grain': True}),
            # Hana keeps the independently funded recurring market wage.
            event('RecurringFreightWageSigned',
                  {'courier_id': 'hana', 'site_id': 'market', 'resource': 'food',
                   'interval_seconds': 18 * HOUR}),
        ]
    else:
        events = [
            event('CourierProvisionConfigured',
                  {'id': 'real-surplus-only-hana', 'courier_id': 'hana',
                   'payer_site': 'market', 'units': 0, 'authorized_total_units': 2}),
            event('CourierProvisionConfigured',
                  {'id': 'huda-future-bakery', 'courier_id': 'huda',
                   'payer_site': 'bakery', 'units': 0, 'authorized_total_units': 2,
                   'deferred_bakery_grain': True}),
        ]
    with SQLiteEventStore(path) as db:
        current = db.append(WORLD, 'integrated-terms', original.revision, events, bootstrap=True)
        for field in ('resources', 'entities', 'npcs', 'routes', 'metabolism_policy', 'farm_plots'):
            assert getattr(current, field) == getattr(original, field), field
        assert len(current.npcs) == 13
        assert sum(r.get('food', 0) for r in current.resources.values()) == 3
        assert audit_npc_economy(current)['copper_known_total'] == 12
        assert db.verify(WORLD).to_dict() == current.to_dict()
    return current


def metrics(s):
    audit = audit_npc_economy(s)
    assert audit['copper_scope_complete'] and audit['copper_known_total'] == 12
    return {
        'hour': s.time // HOUR, 'copper': audit['copper_known_total'],
        'copper_by_owner': audit['copper_known_by_owner'],
        'bread': sum(j['status'] == 'completed' and j['site_id'] == 'bakery'
                     for j in s.production_jobs.values()),
        'meals': len(s.consumptions),
        'sales': sum(t['resource'] == 'food' for t in s.market_trades.values()),
        'starving': sum(n['needs']['hunger'] == 100 for n in s.npcs.values()),
        'deliveries': {who: c['deliveries'] for who, c in s.supply_circuits.items()},
        'cash_wages': audit_production_wages(s)['coin_paid'],
        'freight_wages': sum(r['payment'] is not None for c in s.supply_circuits.values()
                             for r in c.get('food_payroll', {}).get('receipts', ())),
        'grain_settlements': {who: {
            'received_grain': len(c.get('grain_purchase', {}).get('receipts', ())),
            'farm_received_copper': sum(r['received_at'] is not None
                for r in c.get('grain_purchase', {}).get('receipts', ())),
        } for who, c in s.supply_circuits.items()},
        'courier_generic_work': {who: sum(a['npc_id'] == who and a['action'] == 'work'
                                          for a in s.actions.values())
                                  for who in s.supply_circuits},
        'npcs': {who: {'hunger': n['needs']['hunger'], 'fatigue': n['needs']['fatigue'],
                       'site': s.entities[who]['location_id'],
                       'cash': s.resources[who].get('coin_copper'),
                       'food': s.resources[who]['food'],
                       'meals': sum(m['npc_id'] == who for m in s.consumptions.values()),
                       'purchases': sum(t['buyer_id'] == who and t['resource'] == 'food'
                                        for t in s.market_trades.values())}
                 for who, n in s.npcs.items()},
    }


def advance_to(path, hour, *, candidate, community_food=False):
    with SQLiteEventStore(path) as db:
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        sim = engine(db, clock, reserve_trader_meal=True, deferred_market_courier_wage=True)
        sim.merchant_food_wage_enabled = True
        sim.community_food_enabled = community_food
        sim.deferred_bakery_grain_wage_enabled = True  # Huda's authentic two-service original wage in both arms
        sim.integrated_livelihoods_enabled = candidate
        sim.remember_unbought_stalls_enabled = candidate
        s = db.load(WORLD)
        try:
            while s.time < hour * HOUR:
                # Fixed 6h partitions in both arms. Rain is exogenous and equal.
                target = min(hour * HOUR, ((s.time // (6 * HOUR)) + 1) * 6 * HOUR)
                s = sim.advance(WORLD, seconds=target - s.time,
                                command_id=f'advance:{target}', expected_revision=s.revision).state
                conserve_diverse(s)
                if s.time % (24 * HOUR) == 0 and s.time < 168 * HOUR:
                    day = s.time // (24 * HOUR)
                    s = FiniteWaterService(db, clock).record(
                        WORLD, 'well', f'fixed-external-rain-day{day}', 2,
                        command_id=f'real-attributed-source-day{day}', expected_revision=s.revision).state
                db.snapshot(WORLD)
            assert db.verify(WORLD).to_dict() == s.to_dict()
            assert db.db.execute('PRAGMA integrity_check').fetchone() == ('ok',)
            assert db.db.execute('PRAGMA foreign_key_check').fetchall() == []
        finally:
            clock.close_session(WORLD)
    with SQLiteEventStore(path) as db:
        assert db.verify(WORLD).to_dict() == s.to_dict()
    return metrics(s)


def gate(rows, hour):
    a, b = rows[str(hour)]['control'], rows[str(hour)]['candidate']
    if hour >= 60:
        assert b['starving'] < a['starving'], 'no sustained starvation improvement'
        assert b['npcs']['nora']['purchases'] > a['npcs']['nora']['purchases'], 'Nora earned no additional purchased food'
        assert b['npcs']['nora']['meals'] > a['npcs']['nora']['meals'], 'purchased food never eaten'
        assert b['cash_wages'] > a['cash_wages'], 'no new real cash payroll'
        for key in ('bread', 'meals', 'sales'):
            assert b[key] >= a[key], (key, a[key], b[key])
        if hour > 60:
            assert b['starving'] <= rows['60']['candidate']['starving'], 'recovery deteriorated after h60'
            prior_hour = max(int(h) for h in rows if int(h) < hour)
            prior = rows[str(prior_hour)]['candidate']
            for key in ('bread', 'meals', 'sales'):
                assert b[key] > prior[key], f'{key} stopped after {prior_hour}h'
            for who in b['deliveries']:
                assert b['deliveries'][who] > prior['deliveries'][who], f'{who} stopped delivering'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--hours', type=int, choices=CHECKPOINTS, default=60)
    args = parser.parse_args()
    args.directory.mkdir(parents=True, exist_ok=False)
    for candidate in (False, True):
        seed(args.directory / ('candidate.sqlite' if candidate else 'control.sqlite'), candidate=candidate)
    rows = {}
    for hour in CHECKPOINTS:
        if hour > args.hours:
            break
        rows[str(hour)] = {}
        for arm in ('control', 'candidate'):
            row = advance_to(args.directory / f'{arm}.sqlite', hour, candidate=arm == 'candidate')
            rows[str(hour)][arm] = row
            (args.directory / 'results.json').write_text(json.dumps(rows, indent=2), encoding='utf8')
            print('PLAY48_INTEGRATED ' + json.dumps({'arm': arm, **row}, sort_keys=True), flush=True)
        gate(rows, hour)


if __name__ == '__main__':
    main()
