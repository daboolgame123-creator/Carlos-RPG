"""Resource-boundary tests for prospective wages and early owned meals."""
from __future__ import annotations
import json
import sys
from pathlib import Path

import pytest

from carlos_sim import DomainEvent, SQLiteEventStore, TimeEngine, apply_event
from carlos_sim.domain import WorldState
from carlos_sim.store import InvalidEvent, IntegrityError
from carlos_sim.freight_payroll import choose_payment

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scenarios' / 'test_village'))
from play48_integrated_acceptance import seed, WORLD
from test_play48_real_watch_income_24h import engine


@pytest.fixture
def village(tmp_path):
    path = tmp_path / 'village.sqlite'
    s = seed(path, candidate=True)
    with SQLiteEventStore(path) as db:
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        sim = engine(db, clock, reserve_trader_meal=True)
        sim.integrated_livelihoods_enabled = True
        sim.merchant_food_wage_enabled = True
        yield db, clock, sim, s
        clock.close_session(WORLD)


def test_prospective_terms_do_not_create_assets_or_rewrite_existing_terms(village):
    db, clock, sim, s = village
    assert s.production_recipes['finite-harvest']['wage_coin'] == 2
    assert s.resources['farm']['coin_copper'] == 0
    for kind, data in (
        ('ProductionCashWageSigned', {'recipe_id': 'finite-harvest', 'amount': 3}),
        ('ProductionCashWageSigned', {'recipe_id': 'grain-to-bread', 'amount': 2}),
        ('RecurringFreightWageSigned', {'courier_id': 'hana', 'site_id': 'market',
                                       'resource': 'food', 'interval_seconds': 64800}),
        ('CourierProvisionConfigured', {'id': 'double', 'courier_id': 'hana',
                                        'payer_site': 'market', 'units': 1}),
    ):
        with pytest.raises(InvalidEvent):
            db.append(WORLD, kind, s.revision,
                      [DomainEvent(kind, None, 'invalid repeated terms', 0, data)], bootstrap=True)
    assert db.verify(WORLD).to_dict() == s.to_dict()


def test_unearned_unfunded_and_unauthorized_wages_reject_atomically(village):
    db, clock, sim, s = village
    wage = DomainEvent('RecurringFreightWagePaid', None, 'forged labor', 0,
                      {'courier_id': 'hana', 'delivery': 1})
    for authorized in (False, True):
        with pytest.raises(InvalidEvent):
            db.append(WORLD, f'forged:{authorized}', s.revision, [wage],
                      supply_authorized=authorized)
    with pytest.raises(InvalidEvent):
        db.append(WORLD, 'fake-job', s.revision,
                  [DomainEvent('ProductionWagePaid', None, 'no completed work', 0,
                               {'job_id': 'absent', 'amount': 2})], production_authorized=True)
    assert db.verify(WORLD).to_dict() == s.to_dict()
    assert db.db.execute('SELECT count(*) FROM commands WHERE command_id LIKE ?', ('forged:%',)).fetchone() == (0,)


def test_real_delivery_payment_is_once_only_and_replays(village):
    db, clock, sim, s = village
    s = sim.advance(WORLD, seconds=1200, command_id='real-trip', expected_revision=s.revision).state
    receipts = s.supply_circuits['hana']['food_payroll']['receipts']
    assert receipts and receipts[0]['payment'] is not None
    q = receipts[0]['payment']
    assert q['source_before'] - q['source_after'] == 1
    assert q['worker_after'] - q['worker_before'] == 1
    assert s.supply_circuits['hana']['deliveries'] >= receipts[0]['delivery']
    with pytest.raises(InvalidEvent):
        db.append(WORLD, 'double-pay', s.revision,
                  [DomainEvent('RecurringFreightWagePaid', None, 'duplicate', s.time,
                               {'courier_id': 'hana', 'delivery': receipts[0]['delivery']})],
                  supply_authorized=True)
    assert db.verify(WORLD).to_dict() == s.to_dict()
    assert db.snapshot(WORLD).to_dict() == s.to_dict()
    assert db.db.execute('PRAGMA integrity_check').fetchone() == ('ok',)


def test_quoted_cargo_and_absent_employer_food_cannot_pay(village):
    db, clock, sim, original = village
    # Synthetic negative probes isolate funding from actual-service rejection.
    # The positive physical proof is the separate real-trip test above.
    raw = original.to_dict()
    c = raw['supply_circuits']['hana']
    c.update(index=3, loads=1, deliveries=1)
    raw['entities']['hana']['location_id'] = 'market'
    c['food_payroll']['receipts'] = [{'delivery': 1, 'delivered_at': 0, 'payment': None}]
    for balance in (0, 2):
        raw['resources']['market']['food'] = balance
        raw['market_offers'] = ({'reserved': {
            'seller_id': 'salma', 'stock_owner_id': 'market', 'site_id': 'market',
            'resource': 'food', 'quantity': 2, 'remaining': 2,
            'payment_resource': 'coin_copper', 'unit_price': 2,
            'posted_at': 0, 'status': 'open', 'closed_at': None,
        }} if balance else {})
        s = WorldState.from_dict(raw)
        assert choose_payment(s, 'hana') is None
        with pytest.raises(ValueError):
            apply_event(s, DomainEvent('RecurringFreightWagePaid', None, 'reserved stock', 0,
                                      {'courier_id': 'hana', 'delivery': 1}), supply_authorized=True)
    assert db.verify(WORLD).to_dict() == original.to_dict()


def test_existing_history_cannot_be_changed_to_fake_service(village):
    db, clock, sim, s = village
    seq, payload = db.db.execute('SELECT seq,payload FROM events ORDER BY seq LIMIT 1').fetchone()
    event = json.loads(payload)
    event['cause'] = 'tampered evidence'
    db.db.execute('UPDATE events SET payload=? WHERE seq=?', (json.dumps(event), seq))
    with pytest.raises(IntegrityError, match='hash mismatch'):
        db.verify(WORLD)


def freight_fixture(path, *, bread=1, fatigue=0, hunger=65, period=1800):
    """Small boundary fixture; deliberately separate from 13-person acceptance."""
    db = SQLiteEventStore(path)
    s = db.create_world('freight')
    events = []
    def add(kind, data):
        events.append(DomainEvent(kind, None, 'isolated payroll boundary setup', 0, data))
    for site in ('well', 'farm', 'bakery', 'market'):
        add('LocationCreated', {'id': site, 'name': site})
    for rid, a, b in (('wf', 'well', 'farm'), ('fb', 'farm', 'bakery'), ('bm', 'bakery', 'market')):
        add('RouteCreated', {'id': rid, 'a': a, 'b': b, 'seconds': 30})
    for who, site, role in (('huda', 'well', 'courier'), ('salma', 'market', 'merchant')):
        add('EntityCreated', {'id': who, 'name': who, 'location_id': site, 'controller': 'npc'})
        add('NPCConfigured', {'npc_id': who, 'role': role,
                             'needs': {'hunger': hunger if who == 'huda' else 10,
                                       'fatigue': fatigue if who == 'huda' else 0, 'safety': 0},
                             'goals': {'earn': 10, 'survive': 30, 'explore': 10}})
    add('EntityCreated', {'id': 'carlos', 'name': 'Carlos', 'location_id': 'bakery', 'controller': 'player'})
    for owner in ('well', 'farm', 'bakery', 'market', 'huda', 'salma'):
        for resource in ('water', 'grain', 'food', 'coin_copper', 'labor_units', 'investigation_attempts'):
            quantity = bread if (owner, resource) == ('bakery', 'food') else 2 if (owner, resource) == ('farm', 'grain') else 0
            add('ResourceChanged', {'owner_id': owner, 'resource': resource,
                                   'previous': None, 'current': quantity, 'source': 'initialization'})
    add('MarketStallConfigured', {'site_id': 'market', 'keeper_id': 'salma'})
    add('SupplyCircuitConfigured', {'courier_id': 'huda',
                                   'stops': ['well', 'farm', 'bakery', 'market', 'bakery', 'farm', 'well'],
                                   'route_ids': ['wf', 'fb', 'bm', 'bm', 'fb', 'wf'], 'period_seconds': period})
    add('RecurringFreightWageSigned', {'courier_id': 'huda', 'site_id': 'bakery',
                                     'resource': 'grain', 'interval_seconds': 43200})
    add('MetabolismPolicyConfigured', {'hunger_seconds_per_point': 3600, 'activity_hunger_percent': 20})
    s = db.append('freight', 'setup', s.revision, events, bootstrap=True)
    clock = TimeEngine(db)
    clock.open_session('freight')
    sim = engine(db, clock)
    sim.integrated_livelihoods_enabled = True
    return db, clock, sim, s


def test_bakery_arrival_pays_before_loading_only_loaf_and_player_sees_owned_meal(tmp_path):
    db, clock, sim, s = freight_fixture(tmp_path / 'one-loaf.sqlite')
    with db:
        s = sim.advance('freight', seconds=60, command_id='player-wait:arrival',
                        expected_revision=s.revision, player_observer_id='carlos').state
        q = s.supply_circuits['huda']['food_payroll']['receipts'][0]
        assert q['payment'] is not None
        assert s.resources['bakery']['food'] == 0
        assert s.resources['huda']['food'] == 0
        assert s.npcs['huda']['needs']['hunger'] == 40
        events = [json.loads(row[0]) for row in db.db.execute('SELECT payload FROM events ORDER BY seq')]
        meal = next(i for i, e in enumerate(events) if e['event_type'] == 'NPCFoodConsumed')
        assert events[meal - 1]['event_type'] == 'PlayerObserved'
        assert events[meal - 1]['actor_id'] == 'carlos'
        assert db.verify('freight').to_dict() == s.to_dict()
        clock.close_session('freight')


def test_unpaid_wait_wakes_at_fatigue_boundary_independent_of_partition(tmp_path):
    states = []
    for arm, parts in (('whole', (1800,)), ('split', (600, 1200))):
        db, clock, sim, s = freight_fixture(tmp_path / f'{arm}.sqlite', bread=0, fatigue=69, hunger=20)
        with db:
            for i, seconds in enumerate(parts):
                s = sim.advance('freight', seconds=seconds, command_id=f'step:{i}', expected_revision=s.revision).state
            assert db.verify('freight').to_dict() == s.to_dict()
            raw = s.to_dict()
            raw.pop('revision')
            states.append(raw)
            clock.close_session('freight')
    assert states[0] == states[1]
    assert any(a['npc_id'] == 'huda' and a['action'] == 'rest' and a['start'] == 600
               for a in states[0]['actions'].values())


def test_recurring_wage_requires_second_interval_and_new_actual_delivery(tmp_path):
    db, clock, sim, s = freight_fixture(tmp_path / 'repeat.sqlite', bread=3, hunger=20, period=43200)
    with db:
        s = sim.advance('freight', seconds=43400, command_id='two-circuits', expected_revision=s.revision).state
        receipts = s.supply_circuits['huda']['food_payroll']['receipts']
        assert len(receipts) == 2
        assert all(r['payment'] is not None for r in receipts)
        assert receipts[1]['delivered_at'] - receipts[0]['delivered_at'] >= 43200
        assert receipts[1]['delivery'] > receipts[0]['delivery']
        assert db.verify('freight').to_dict() == s.to_dict()
        clock.close_session('freight')
