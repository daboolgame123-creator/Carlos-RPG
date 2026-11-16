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
