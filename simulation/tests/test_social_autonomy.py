"""Phase 01-I: deterministic, consent-free but bounded NPC speech initiatives.

All speech is a typed fictional act; no actual help, goods, or combat is granted.
"""
import pytest
from carlos_sim import (DomainEvent, SQLiteEventStore, TimeEngine, LivingWorldEngine,
                        NPCSocialService, NPCMovementService, NPCService, NPCActionService,
                        choose_social_intent, MIN_SOCIAL_COOLDOWN, AdvanceLimitExceeded)
from carlos_sim.store import InvalidEvent


def ev(kind, data, actor=None):
    return DomainEvent(kind, actor, 'test', 0, data)


def make_world(db, *, names=('aaron', 'zora'), hunger=10, safety=10, separate=False):
    db.create_world('village')
    events = [ev('LocationCreated', {'id': 'square', 'name': 'Square'}),
              ev('LocationCreated', {'id': 'forest', 'name': 'Forest'}),
              ev('RouteCreated', {'id': 'path', 'a': 'square', 'b': 'forest', 'seconds': 90})]
    for i, name in enumerate(names):
        here = 'forest' if separate and i == 1 else 'square'
        events += [ev('EntityCreated', {'id': name, 'name': name,
                    'controller': 'npc', 'location_id': here}),
                   ev('NPCConfigured', {'npc_id': name, 'role': 'villager',
                    'needs': {'hunger': hunger, 'safety': safety, 'fatigue': 5},
                    'goals': {'earn': 90, 'explore': 10, 'survive': 30}})]
        for metric in ('labor_units', 'investigation_attempts'):
            events.append(ev('ResourceChanged', {'owner_id': name, 'resource': metric,
                            'previous': None, 'current': 0, 'source': 'initialization'}))
    events.append(ev('EntityCreated', {'id': 'carlos', 'name': 'Carlos',
                                      'controller': 'player', 'location_id': 'square'}))
    db.append('village', 'setup', 0, events, bootstrap=True)


@pytest.fixture
def world(tmp_path):
    with SQLiteEventStore(tmp_path / 'world.sqlite') as db:
        make_world(db)
        clock = TimeEngine(db)
        clock.open_session('village')
        yield db, clock, LivingWorldEngine(db, clock, social_enabled=True)


def advance(db, clock, secs, tag, **options):
    return LivingWorldEngine(db, clock, social_enabled=True, **options).advance(
        'village', seconds=secs, command_id=tag,
        expected_revision=db.load('village').revision)


def test_automatic_first_contact_is_directed_and_recorded(world):
    db, clock, engine = world
    out = engine.advance('village', seconds=1, command_id='first', expected_revision=db.load('village').revision)
    assert out.social_message_ids == ('auto-social:aaron:0',)
    message = out.state.social_messages[out.social_message_ids[0]]
    assert (message['sender'], message['recipient'], message['kind'], message['status']) == (
        'aaron', 'zora', 'greeting', 'received')
    assert out.state.relations['zora']['aaron'] == 1
    assert 'zora' not in out.state.relations.get('aaron', {})
    assert db.verify('village').to_dict() == out.state.to_dict()


def test_social_planner_is_opt_in(world):
    db, clock, _ = world
    result = LivingWorldEngine(db, clock).advance('village', seconds=1,
        command_id='off', expected_revision=db.load('village').revision)
    assert result.social_message_ids == ()
    assert result.state.social_messages == {}
    assert result.started_action_ids


def test_cooldown_limits_outgoing_messages_per_speaker(world):
    db, clock, engine = world
    first = engine.advance('village', seconds=20, command_id='twenty',
                           expected_revision=db.load('village').revision)
    second = engine.advance('village', seconds=110, command_id='more',
                            expected_revision=first.state.revision)
    assert first.social_message_ids == ('auto-social:aaron:0',)
    assert second.social_message_ids == ()
    assert len(second.state.social_messages) == 1


def test_social_happens_only_when_explicit_game_time_moves(world):
    db, clock, engine = world
    before = db.load('village').to_dict()
    clock.close_session('village')
    with pytest.raises(PermissionError):
        engine.advance('village', seconds=60, command_id='offline', expected_revision=before['revision'])
    assert db.load('village').to_dict() == before
    clock.open_session('village')
    result = engine.advance('village', seconds=1, command_id='return', expected_revision=before['revision'])
    assert result.social_message_ids


def test_no_automatic_social_contact_at_different_locations(tmp_path):
    with SQLiteEventStore(tmp_path / 'separate.db') as db:
        make_world(db, separate=True)
        clock = TimeEngine(db); clock.open_session('village')
        result = advance(db, clock, 20, 'separate')
        assert result.social_message_ids == ()
        assert result.state.social_messages == {}


def test_no_automatic_contact_with_player(world):
    db, clock, engine = world
    result = engine.advance('village', seconds=1, command_id='go',
                            expected_revision=db.load('village').revision)
    assert all(msg['recipient'] != 'carlos' and msg['sender'] != 'carlos'
               for msg in result.state.social_messages.values())
    assert 'carlos' not in result.state.npcs


def test_in_transit_sender_cannot_initiate_social(world):
    db, clock, _ = world
    mover = NPCMovementService(db, clock)
    mover.start('village', 'aaron', 'path', 'trip', expected_revision=db.load('village').revision)
    result = advance(db, clock, 1, 'walking')
    assert not any(m['sender'] == 'aaron' for m in result.state.social_messages.values())
    assert result.social_message_ids == ()


def test_busy_sender_not_initiated_or_targeted(world):
    db, clock, _ = world
    NPCService(db, clock).decide('village', 'aaron', command_id='plan',
                                 expected_revision=db.load('village').revision)
    NPCActionService(db, clock).start('village', 'aaron', 'work',
                                      expected_revision=db.load('village').revision)
    result = advance(db, clock, 1, 'busy')
    assert result.social_message_ids == ()
    assert result.state.social_messages == {}


def test_existing_manual_activity_intentions_not_overridden(world):
    db, clock, _ = world
    for name in ('aaron', 'zora'):
        NPCService(db, clock).decide('village', name, command_id='plan:'+name,
                                     expected_revision=db.load('village').revision)
    result = advance(db, clock, 1, 'intent')
    assert result.social_message_ids == ()
    assert {a['npc_id'] for a in result.state.actions.values()} == {'aaron','zora'}


def test_personal_need_prompts_request_help_not_actual_aid(tmp_path):
    with SQLiteEventStore(tmp_path / 'need.db') as db:
        make_world(db, hunger=85)
        c=TimeEngine(db);c.open_session('village')
        NPCSocialService(db,c).interact('village','zora','aaron',kind='greeting',text='Hi',
               message_id='known', expected_revision=db.load('village').revision)
        planned=choose_social_intent(db.load('village'),'aaron')
        assert planned is not None and planned.kind=='request_help'
        result=advance(db,c,1,'need')
        assert result.state.social_messages['auto-social:aaron:0']['kind']=='request_help'
        assert result.state.resources['aaron']['labor_units']==0
        assert 'request_help' not in result.state.actions


def test_prior_hostility_can_prompt_threat_without_knowing_peer_secrets(tmp_path):
    with SQLiteEventStore(tmp_path / 'hostility.db') as db:
        make_world(db)
        c=TimeEngine(db);c.open_session('village')
        svc=NPCSocialService(db,c)
        for i in range(4):
            svc.interact('village','zora','aaron',kind='threat',text='Go away',
                         message_id=f'past-{i}',expected_revision=db.load('village').revision)
            if i<3: c.advance('village',seconds=1,command_id=f'tick-{i}',expected_revision=db.load('village').revision)
        assert db.load('village').relations['aaron']['zora']==-48
        planned=choose_social_intent(db.load('village'),'aaron')
        assert planned and planned.kind=='threat'
        out=advance(db,c,1,'respond')
        assert out.state.social_messages[out.social_message_ids[0]]['kind']=='threat'


def test_positive_trust_can_motivate_offer_not_transfer_resources(tmp_path):
    with SQLiteEventStore(tmp_path / 'friend.db') as db:
        make_world(db)
        c=TimeEngine(db);c.open_session('village')
        svc=NPCSocialService(db,c)
        for i in range(14):
            svc.interact('village','zora','aaron',kind='offer_help',text='Offer',
                         message_id=f'prior-{i}',expected_revision=db.load('village').revision)
            if i<13: c.advance('village',seconds=1,command_id=f'tick-{i}',expected_revision=db.load('village').revision)
        assert db.load('village').relations['aaron']['zora']>=40
        planned=choose_social_intent(db.load('village'),'aaron')
        assert planned and planned.kind=='offer_help'
        before=db.load('village').resources['aaron']['labor_units']
        out=advance(db,c,1,'offer')
        assert out.state.social_messages[out.social_message_ids[0]]['kind']=='offer_help'
        assert out.state.resources['aaron']['labor_units']==before


def test_social_event_budget_is_atomic(world):
    db, clock, _ = world
    before=db.load('village').to_dict()
    with pytest.raises(AdvanceLimitExceeded):
        advance(db, clock, 100, 'over-budget', max_events_per_advance=1)
    assert db.load('village').to_dict()==before
    assert db.db.execute("SELECT count(*) FROM commands WHERE command_id='over-budget'").fetchone()[0]==0


def test_invalid_social_options_rejected(world):
    db, clock, _ = world
    for x in (False, True, 1, 179, None):
        with pytest.raises(ValueError):
            LivingWorldEngine(db, clock, social_enabled=True, social_cooldown=x)
    for x in (1, None, 'true'):
        with pytest.raises(ValueError):
            LivingWorldEngine(db, clock, social_enabled=x)
    with pytest.raises(ValueError): choose_social_intent(db.load('village'),'aaron',cooldown=100)
    assert MIN_SOCIAL_COOLDOWN==180


def test_zero_npcs_has_no_social_events(tmp_path):
    with SQLiteEventStore(tmp_path / 'empty.db') as db:
        db.create_world('village')
        clock=TimeEngine(db);clock.open_session('village')
        out=advance(db,clock,45,'empty')
        assert out.social_message_ids==() and out.state.time==45


def test_parallel_social_and_navigation_mode(world):
    db, clock, _ = world
    result=LivingWorldEngine(db,clock,navigation_enabled=True,social_enabled=True).advance(
        'village',seconds=5,command_id='both',expected_revision=db.load('village').revision)
    assert result.social_message_ids
    assert db.verify('village').to_dict()==result.state.to_dict()


def test_replay_and_snapshot_after_automatic_social(tmp_path):
    path=tmp_path / 'restart.db'
    with SQLiteEventStore(path) as db:
        make_world(db)
        c=TimeEngine(db);c.open_session('village')
        result=advance(db,c,120,'first')
        db.snapshot('village')
    with SQLiteEventStore(path) as db:
        assert db.verify('village').to_dict()==result.state.to_dict()
        c=TimeEngine(db)
        with pytest.raises(PermissionError):advance(db,c,1,'offline')
        c.open_session('village')
        resumed=advance(db,c,200,'resume')
        assert resumed.state.time==320
        assert db.verify('village').to_dict()==resumed.state.to_dict()


def test_deterministic_state_across_world_instances(tmp_path):
    results=[]
    for i in range(2):
        with SQLiteEventStore(tmp_path / f'{i}.sqlite') as db:
            make_world(db)
            c=TimeEngine(db);c.open_session('village')
            out=advance(db,c,500,'trial')
            results.append((out.state.to_dict(),out.social_message_ids))
    assert results[0]==results[1]


def test_split_and_single_time_steps_have_equal_semantic_state(tmp_path):
    results=[]
    for i, chunks in enumerate(((400,), (100,100,100,100))):
        with SQLiteEventStore(tmp_path / f'chunk{i}.db') as db:
            make_world(db)
            c=TimeEngine(db);c.open_session('village')
            for j, seconds in enumerate(chunks):advance(db,c,seconds,f'step{j}')
            state=db.verify('village').to_dict();state.pop('revision')
            results.append(state)
    assert results[0]==results[1]


def test_recipient_private_needs_do_not_influence_sender_choice(tmp_path):
    choices=[]
    for i, hunger in enumerate((0,99)):
        with SQLiteEventStore(tmp_path/f'private{i}.db') as db:
            make_world(db)
            c=TimeEngine(db);c.open_session('village')
            npc=db.load('village')
            if hunger:
                # This is a trusted private need event for the *recipient* only.
                db.append('village','private',npc.revision,[DomainEvent('NPCNeedChanged','zora',
                  'private fatigue',0,{'npc_id':'zora','need':'hunger','previous':10,'current':hunger})])
            choices.append(choose_social_intent(db.load('village'),'aaron'))
    assert choices[0]==choices[1]


def test_same_request_to_same_peer_needs_new_causal_interval(tmp_path):
    with SQLiteEventStore(tmp_path/'repeat.db') as db:
        make_world(db, hunger=85)
        c=TimeEngine(db);c.open_session('village')
        NPCSocialService(db,c).interact('village','zora','aaron',kind='greeting',text='Hello',
            message_id='prior',expected_revision=db.load('village').revision)
        first=advance(db,c,1,'first')
        assert first.state.social_messages['auto-social:aaron:0']['kind']=='request_help'
        c.advance('village',seconds=179,command_id='clock180',expected_revision=first.state.revision)
        assert choose_social_intent(db.load('village'),'aaron') is None
        c.advance('village',seconds=720,command_id='clock900',expected_revision=db.load('village').revision)
        intent=choose_social_intent(db.load('village'),'aaron')
        assert intent is not None and intent.kind=='request_help'


def test_peer_specific_topic_limit_does_not_block_new_contact(tmp_path):
    with SQLiteEventStore(tmp_path/'new-friend.db') as db:
        make_world(db,names=('aaron','bella','zora'),hunger=85)
        c=TimeEngine(db);c.open_session('village')
        NPCSocialService(db,c).interact('village','bella','aaron',kind='greeting',text='Hi',
              message_id='met-bella',expected_revision=db.load('village').revision)
        first=advance(db,c,1,'first')
        assert first.state.social_messages['auto-social:aaron:0']['recipient']=='bella'
        c.advance('village',seconds=179,command_id='to180',expected_revision=first.state.revision)
        intent=choose_social_intent(db.load('village'),'aaron')
        assert intent is not None and intent.kind=='greeting' and intent.recipient_id=='zora'
