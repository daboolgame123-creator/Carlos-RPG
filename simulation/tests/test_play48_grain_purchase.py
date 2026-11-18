"""Signed grain price, source claims and actual farm cash custody boundaries."""
import pytest

from carlos_sim import DomainEvent, apply_event
from carlos_sim.domain import WorldState
from carlos_sim.grain_purchase import cash_minimum
from carlos_sim.store import InvalidEvent
from carlos_sim.supply import choose_cargo_manifest
from test_play48_integrated_income import freight_fixture
from play48_integrated_acceptance import seed


def test_grain_receipt_settles_only_via_actual_return_cargo_once(tmp_path):
    db, clock, sim, s = freight_fixture(tmp_path / 'purchase.sqlite', hunger=20,
                                       grain_purchase=True, bakery_copper=3)
    with db:
        s = sim.advance('freight', seconds=60, command_id='grain-arrival', expected_revision=s.revision).state
        receipt = s.supply_circuits['huda']['grain_purchase']['receipts'][0]
        assert dict(receipt) == {'delivery': 1, 'delivered_at': 60,
                                 'loaded_at': None, 'received_at': None}
        assert s.resources['farm']['coin_copper'] == 0
        s = sim.advance('freight', seconds=120, command_id='physical-return', expected_revision=s.revision).state
        receipt = s.supply_circuits['huda']['grain_purchase']['receipts'][0]
        assert receipt['loaded_at'] == 120 and receipt['received_at'] == 150
        assert s.resources['farm']['coin_copper'] == 1
        assert s.resources['bakery']['coin_copper'] == 2
        assert s.resources['huda']['coin_copper'] == 0
        with pytest.raises(InvalidEvent):
            db.append('freight', 'duplicate-return', s.revision,
                      [DomainEvent('SupplyCargoDelivered', 'huda', 'forged remittance', s.time,
                                   {'courier_id': 'huda', 'resource': 'coin_copper'})],
                      supply_authorized=True)
        assert db.verify('freight').to_dict() == s.to_dict()
        clock.close_session('freight')


def test_no_grain_means_no_cash_and_insolvent_bakery_cannot_mint_payment(tmp_path):
    db, clock, sim, original = freight_fixture(tmp_path / 'insolvent.sqlite', hunger=20,
                                              grain_purchase=True, bakery_copper=0)
    with db:
        s = sim.advance('freight', seconds=180, command_id='real-unfunded-grain',
                        expected_revision=original.revision).state
        assert len(s.supply_circuits['huda']['grain_purchase']['receipts']) == 1
        assert s.supply_circuits['huda']['grain_purchase']['receipts'][0]['loaded_at'] is None
        assert s.resources['farm']['coin_copper'] == 0
        assert s.resources['bakery']['coin_copper'] == 0
        raw = s.to_dict()
        raw['supply_circuits']['huda'].update(index=4)
        raw['entities']['huda']['location_id'] = 'bakery'
        raw['resources']['bakery']['coin_copper'] = 10
        raw['supply_circuits']['huda']['grain_purchase']['receipts'] = []
        synthetic = WorldState.from_dict(raw)
        assert choose_cargo_manifest(synthetic, 'huda') is None
        with pytest.raises(ValueError):
            apply_event(synthetic, DomainEvent('SupplyCargoPicked', 'huda', 'no grain proof', s.time,
                                              {'courier_id': 'huda', 'resource': 'coin_copper'}),
                        supply_authorized=True)
        assert db.verify('freight').to_dict() == s.to_dict()
        clock.close_session('freight')


def test_earlier_source_claim_reserves_copper_against_fast_circuit():
    # Pure local bakery dispatch fixture: no remote farm resources are read.
    earlier = {'index': 4, 'grain_purchase': {'receipts': [
        {'delivery': 1, 'delivered_at': 60, 'loaded_at': None}]}}
    faster = {'index': 4, 'grain_purchase': {'receipts': [
        {'delivery': 1, 'delivered_at': 90, 'loaded_at': None}]}}
    state = {'supply_circuits': {'slow': earlier, 'fast': faster}, 'resources': {},
             'market_offers': {}, 'time': 100, 'production_jobs': {}, 'production_recipes': {}}
    assert cash_minimum(state, earlier) == 1
    assert cash_minimum(state, faster) == 2
    # The second courier cannot take the earlier farm's only available coin.
    assert 1 < cash_minimum(state, faster)
    state['market_offers']['reserved-coin'] = {'status': 'open', 'stock_owner_id': 'bakery',
                                               'resource': 'coin_copper', 'remaining': 2}
    assert cash_minimum(state, earlier) == 3
    assert cash_minimum(state, faster) == 4
    # This source claim has loaded and therefore no longer reserves bakery cash.
    earlier['grain_purchase']['receipts'][0]['loaded_at'] = 100
    assert cash_minimum(state, faster) == 3
    # Already earned local bakery labor is senior to unshipped grain cash.
    state['production_recipes']['bread'] = {'wage_coin': 2}
    state['production_jobs']['completed-batch'] = {
        'site_id': 'bakery', 'status': 'completed', 'recipe_id': 'bread'}
    assert cash_minimum(state, faster) == 5
    state['production_jobs']['completed-batch']['work_wage'] = {'amount': 2}
    assert cash_minimum(state, faster) == 3


def test_unsigned_late_and_repeated_purchase_contracts_reject(tmp_path):
    db, clock, sim, s = freight_fixture(tmp_path / 'terms.sqlite', grain_purchase=True)
    with db:
        for bootstrap, actor, price in ((True, None, 1), (False, None, 1),
                                        (True, 'huda', 1), (True, None, True), (True, None, 2)):
            with pytest.raises(InvalidEvent):
                db.append('freight', f'bad:{bootstrap}:{actor}:{price!r}', s.revision,
                          [DomainEvent('GrainPurchaseSigned', actor, 'cannot rewrite settlement', 0,
                                       {'courier_id': 'huda', 'unit_price': price})], bootstrap=bootstrap)
        assert db.verify('freight').to_dict() == s.to_dict()
        clock.close_session('freight')


def test_forged_arrival_without_custody_is_rejected(tmp_path):
    db, clock, sim, s = freight_fixture(tmp_path / 'proof.sqlite', grain_purchase=True)
    with db:
        for resource in ('grain', 'coin_copper'):
            with pytest.raises(InvalidEvent):
                db.append('freight', f'no-custody:{resource}', s.revision,
                          [DomainEvent('SupplyCargoDelivered', 'huda', 'invented service', 0,
                                       {'courier_id': 'huda', 'resource': resource})], supply_authorized=True)
        raw = s.to_dict()
        raw['supply_circuits']['huda']['grain_purchase']['receipts'] = [
            {'delivery': 1, 'delivered_at': 0, 'loaded_at': None, 'received_at': 0}]
        with pytest.raises(ValueError):
            WorldState.from_dict(raw)
        assert db.verify('freight').to_dict() == s.to_dict()
        clock.close_session('freight')


def test_two_real_grain_payments_fund_one_completed_harvest_wage(tmp_path):
    db, clock, sim, s = freight_fixture(tmp_path / 'labor-funded.sqlite', hunger=20,
                                       grain_purchase=True, bakery_copper=3, harvest_wage=True)
    with db:
        s = sim.advance('freight', seconds=2000, command_id='first-coin', expected_revision=s.revision).state
        jobs = [j for j in s.production_jobs.values() if j['npc_id'] == 'nora']
        assert len(jobs) == 1 and jobs[0]['status'] == 'completed'
        assert 'work_wage' not in jobs[0]
        assert s.resources['farm']['coin_copper'] == 1
        assert s.resources['nora']['coin_copper'] == 0
        s = sim.advance('freight', seconds=2000, command_id='second-coin', expected_revision=s.revision).state
        jobs = [j for j in s.production_jobs.values() if j['npc_id'] == 'nora']
        assert len(jobs) == 1 and jobs[0]['work_wage']['amount'] == 2
        assert s.resources['farm']['coin_copper'] == 0
        assert s.resources['bakery']['coin_copper'] == 1
        assert s.resources['nora']['coin_copper'] == 2
        assert sum(r['received_at'] is not None for r in
                   s.supply_circuits['huda']['grain_purchase']['receipts']) == 2
        assert db.verify('freight').to_dict() == s.to_dict()
        clock.close_session('freight')


def test_fast_courier_cannot_load_earlier_farms_reserved_coin(tmp_path):
    # Synthetic dispatch rejection probe only. Real receipt generation and
    # physical positive return are tested above; this does not seed acceptance.
    raw = seed(tmp_path / 'source.sqlite', candidate=True).to_dict()
    raw['time'] = 1
    for who, delivered_at in (('huda', 0), ('hana', 1)):
        raw['entities'][who]['location_id'] = 'bakery'
        c = raw['supply_circuits'][who]
        c.update(index=4, loads=1, deliveries=1)
        c['grain_purchase']['receipts'] = [{'delivery': 1, 'delivered_at': delivered_at,
                                           'loaded_at': None, 'received_at': None}]
    # Move already existing setup cash into the bakery for this negative probe.
    raw['resources']['watch_post']['coin_copper'] -= 1
    raw['resources']['bakery']['coin_copper'] += 1
    state = WorldState.from_dict(raw)
    assert choose_cargo_manifest(state, 'hana') is None
    attempted = DomainEvent('SupplyCargoPicked', 'hana', 'wrong source claim', 1,
                            {'courier_id': 'hana', 'resource': 'coin_copper'})
    with pytest.raises(ValueError):
        apply_event(state, attempted, supply_authorized=True)
    assert choose_cargo_manifest(state, 'huda') == ('SupplyCargoPicked', 'coin_copper')
    loaded = apply_event(state, DomainEvent('SupplyCargoPicked', 'huda', 'earlier actual claim', 1,
                                           {'courier_id': 'huda', 'resource': 'coin_copper'}),
                         supply_authorized=True)
    assert loaded.resources['huda']['coin_copper'] == 1
    assert loaded.resources['bakery']['coin_copper'] == 0
    assert choose_cargo_manifest(loaded, 'hana') is None


@pytest.mark.parametrize('contract', [None, {'unit_price': 1, 'receipts': [
    {'delivery': 1, 'delivered_at': -1, 'loaded_at': None, 'received_at': None}]}])
def test_malformed_snapshot_purchase_contract_rejects(tmp_path, contract):
    db, clock, sim, s = freight_fixture(tmp_path / 'malformed.sqlite', grain_purchase=True)
    with db:
        raw = s.to_dict()
        raw['supply_circuits']['huda'].update(loads=1, deliveries=1, grain_purchase=contract)
        with pytest.raises(ValueError):
            WorldState.from_dict(raw)
        assert db.verify('freight').to_dict() == s.to_dict()
        clock.close_session('freight')


def test_grain_settlement_whole_and_split_are_semantically_equal(tmp_path):
    states = []
    for arm, parts in (('whole', (2000,)), ('split', (1, 59, 120, 1820))):
        db, clock, sim, s = freight_fixture(tmp_path / f'cash-{arm}.sqlite', hunger=20,
                                           grain_purchase=True, bakery_copper=3)
        with db:
            for i, seconds in enumerate(parts):
                s = sim.advance('freight', seconds=seconds, command_id=f'step:{i}',
                                expected_revision=s.revision).state
            assert db.verify('freight').to_dict() == s.to_dict()
            raw = s.to_dict()
            raw.pop('revision')
            states.append(raw)
            clock.close_session('freight')
    assert states[0] == states[1]
    assert states[0]['resources']['farm']['coin_copper'] == 2
