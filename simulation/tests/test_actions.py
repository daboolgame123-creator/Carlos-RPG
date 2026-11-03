"""Phase 01-D: durable, deterministic effects and no NPC action during downtime."""
import json
import pytest
from carlos_sim import DomainEvent, NPCService, TimeEngine, SQLiteEventStore
from carlos_sim.store import InvalidEvent, RevisionConflict, IntegrityError, DuplicateCommand
from carlos_sim.actions import NPCActionService, DURATIONS


def ev(kind, data, actor=None, time=0):
    return DomainEvent(kind, actor, "test fixture", time, data)


def setup(store, *, fatigue=5, hunger=20, safety=0, earn=80, explore=0, initial_counters=True):
    store.create_world("world")
    events = [ev("LocationCreated", {"id":"square", "name":"Square"})]
    for name in ("nora", "basim"):
        events.extend([
            ev("EntityCreated", {"id":name,"name":name,"location_id":"square","controller":"npc"}),
            ev("NPCConfigured", {"npc_id":name,"role":"worker", "needs":{"fatigue":fatigue,"hunger":hunger,"safety":safety},
                "goals":{"earn":earn,"explore":explore,"survive":20}}),
        ])
        if initial_counters:
            for metric in ("labor_units", "investigation_attempts"):
                events.append(ev("ResourceChanged", {"owner_id":name,"resource":metric,"previous":None,
                    "current":0,"source":"initialization"}))
    return store.append("world", "setup", 0, events, bootstrap=True)


@pytest.fixture
def app(tmp_path):
    with SQLiteEventStore(tmp_path/"actions.sqlite") as db:
        setup(db)
        clock = TimeEngine(db)
        clock.open_session("world")
        yield db, clock, NPCService(db, clock), NPCActionService(db,clock)


def choose_start(app, who="nora", ident="first"):
    db, clock, npc, actions=app
    state=db.load("world")
    npc.decide("world",who,command_id="decide:"+ident,expected_revision=state.revision)
    state=db.load("world")
    return actions.start("world",who,ident,expected_revision=state.revision)


def test_work_completion_applies_fixed_effects(app):
    db,clock,*_=app
    started=choose_start(app)
    assert started.action=="work" and started.due==180
    before=db.load("world")
    assert before.npcs["nora"]["needs"]["fatigue"]==5
    assert before.resources["nora"]["labor_units"]==0
    receipt=clock.advance("world",seconds=180,command_id="advance",expected_revision=before.revision)
    result=receipt.state
    assert result.time==180
    assert result.actions["first"]["status"]=="completed"
    assert result.resources["nora"]["labor_units"]==1
    assert result.npcs["nora"]["needs"]["fatigue"]==20
    assert result.npcs["nora"]["needs"]["hunger"]==30
    assert result.actions["first"]["result"]["counters"]["labor_units"] == (0,1)
    assert db.verify("world").to_dict()==result.to_dict()


def test_concurrent_actions_progress_together(app):
    db,clock,*_=app
    a=choose_start(app,"nora","work-a")
    b=choose_start(app,"basim","work-b")
    assert a.due==b.due==180
    state=db.load("world")
    receipt=clock.advance("world",seconds=180,command_id="both",expected_revision=state.revision)
    assert receipt.fired_ids==("npc-action:work-a","npc-action:work-b")
    assert all(receipt.state.resources[k]["labor_units"]==1 for k in ("nora","basim"))


def test_wait_and_rest_have_real_time_and_needs(tmp_path):
    for fatigue, expected, duration in [(0,"work",180),(90,"rest",120)]:
        with SQLiteEventStore(tmp_path/f"{fatigue}.db") as db:
            setup(db,fatigue=fatigue)
            clock=TimeEngine(db);clock.open_session("world")
            npc=NPCService(db,clock);actions=NPCActionService(db,clock)
            decision=npc.decide("world","nora",command_id="plan",expected_revision=db.load("world").revision)
            assert decision.action==expected
            started=actions.start("world","nora","a",expected_revision=db.load("world").revision)
            assert started.due==duration
            before=db.load("world").npcs["nora"]["needs"]["fatigue"]
            after=clock.advance("world",seconds=duration,command_id="pass",expected_revision=db.load("world").revision).state
            if expected=="rest":assert after.npcs["nora"]["needs"]["fatigue"]==70
            else:assert after.npcs["nora"]["needs"]["fatigue"]==15
            assert after.actions["a"]["status"]=="completed"


def test_investigate_records_attempt_not_true_discovery(tmp_path):
    with SQLiteEventStore(tmp_path/"i.db") as db:
        setup(db,earn=0,explore=95)
        clock=TimeEngine(db);clock.open_session("world")
        npc=NPCService(db,clock);actions=NPCActionService(db,clock)
        d=npc.decide("world","nora",command_id="decision",expected_revision=db.load("world").revision)
        assert d.action=="investigate"
        action=actions.start("world","nora","inspect",expected_revision=db.load("world").revision)
        done=clock.advance("world",seconds=action.due,command_id="move",expected_revision=action.state.revision).state
        assert done.resources["nora"]["investigation_attempts"]==1
        assert done.npcs["nora"]["beliefs"]=={}


def test_long_advance_processes_actions_without_interrupting_player(app):
    db,clock,*_=app
    started=choose_start(app)
    result=clock.advance("world",seconds=600,command_id="long",expected_revision=started.state.revision)
    assert result.state.time==600 and not result.interrupted
    assert result.fired_ids==("npc-action:first",)
    assert result.state.actions["first"]["completed_at"]==180


def test_external_interrupt_still_stops_player(app):
    db,clock,*_=app
    started=choose_start(app)
    state=clock.schedule_signal("world","warning",due=100,interrupt=True,expected_revision=started.state.revision)
    first=clock.advance("world",seconds=600,command_id="wait",expected_revision=state.revision)
    assert first.state.time==100 and first.remaining_seconds==500
    assert first.state.actions["first"]["status"]=="running"
    second=clock.advance("world",seconds=500,command_id="resume",expected_revision=first.state.revision)
    assert second.state.actions["first"]["status"]=="completed" and second.state.time==600


def test_replay_after_snapshot_and_restart(tmp_path):
    path=tmp_path/"restart.sqlite"
    with SQLiteEventStore(path) as db:
        setup(db)
        c=TimeEngine(db);c.open_session("world")
        n=NPCService(db,c);n.decide("world","nora",command_id="n",expected_revision=db.load("world").revision)
        start=NPCActionService(db,c).start("world","nora","w",expected_revision=db.load("world").revision)
        db.snapshot("world")
    with SQLiteEventStore(path) as db:
        assert db.verify("world").actions["w"]["status"]=="running"
        c=TimeEngine(db)
        with pytest.raises(Exception): c.advance("world",seconds=180,command_id="closed",expected_revision=start.state.revision)
        assert db.load("world").time==0
        c.open_session("world")
        finished=c.advance("world",seconds=180,command_id="resume",expected_revision=start.state.revision).state
        db.snapshot("world")
        assert finished.resources["nora"]["labor_units"]==1
    with SQLiteEventStore(path) as db:
        assert db.verify("world").actions["w"]["status"]=="completed"


def test_offline_low_level_clock_stopped(app):
    db,clock,*_=app
    a=choose_start(app)
    clock.close_session("world")
    before=db.load("world").to_dict()
    with pytest.raises(InvalidEvent,match="active play session"):
        db.append("world","offline",a.state.revision,[ev("TimeAdvanced",{"from":0,"to":180},time=180)],clock_authorized=True)
    assert db.load("world").to_dict()==before


def test_cancel_running_action_signal_rejected(app):
    db,clock,*_=app
    a=choose_start(app)
    with pytest.raises(InvalidEvent,match="cannot cancel"):
        clock.cancel("world","npc-action:first",command_id="cancel",expected_revision=a.state.revision)
    assert db.load("world").actions["first"]["status"]=="running"


def test_direct_action_start_without_capability_rejected(app):
    db,clock,npc,service=app
    npc.decide("world","nora",command_id="n",expected_revision=db.load("world").revision)
    state=db.load("world")
    with pytest.raises(InvalidEvent,match="action capability"):
        db.append("world","raw",state.revision,[ev("NPCActionStarted",{"action_id":"fake"},actor="nora")])


def test_no_second_action_for_busy_npc(app):
    db,clock,npc,actions=app
    started=choose_start(app)
    old=db.load("world")
    with pytest.raises(InvalidEvent,match="busy|multiple"):
        actions.start("world","nora","second",expected_revision=old.revision)
    assert db.load("world").revision==old.revision


def test_action_cannot_start_from_missing_decision(app):
    db,clock,npc,actions=app
    with pytest.raises(ValueError,match="choose"):
        actions.start("world","nora","missing",expected_revision=db.load("world").revision)


def test_duplicate_action_id_rejected(app):
    db,clock,npc,actions=app
    choose_start(app)
    npc.decide("world", "basim", command_id="decide:basim", expected_revision=db.load("world").revision)
    original=db.load("world")
    with pytest.raises(DuplicateCommand):
        actions.start("world","basim","first",expected_revision=original.revision)
    assert db.load("world").to_dict()==original.to_dict()


def test_uninitialized_counter_refuses_start_before_time_progress(tmp_path):
    with SQLiteEventStore(tmp_path/"missing.db") as db:
        setup(db,initial_counters=False)
        clock=TimeEngine(db);clock.open_session("world")
        npc=NPCService(db,clock)
        npc.decide("world","nora",command_id="decision",expected_revision=db.load("world").revision)
        before=db.load("world")
        with pytest.raises(InvalidEvent,match="initialized"):
            NPCActionService(db,clock).start("world","nora","missing",expected_revision=before.revision)
        assert db.load("world").to_dict()==before.to_dict()


def test_direct_resource_mint_not_allowed(app):
    db,clock,*_=app
    before=db.load("world")
    bad=ev("ResourceChanged",{"owner_id":"nora","resource":"labor_units","previous":0,
            "current":10000,"source":"consumption"},actor="nora")
    with pytest.raises(InvalidEvent,match="counters"):
        db.append("world","mint",before.revision,[bad])
    assert db.load("world").resources["nora"]["labor_units"]==0


def test_action_scheduling_reserved_payload_cannot_be_forged(app):
    db,clock,*_=app
    before=db.load("world")
    with pytest.raises(InvalidEvent,match="action capability"):
        clock.schedule_signal("world","fake",due=80,payload={"__npc_action_id":"ghost"},expected_revision=before.revision)
    assert db.load("world").to_dict()==before.to_dict()


def test_stale_revision_rejected(app):
    db,clock,npc,svc=app
    a=choose_start(app)
    with pytest.raises(RevisionConflict):
        svc.start("world","basim","new",expected_revision=a.state.revision-1)


def test_valid_session_cannot_forge_early_completion(app):
    db,clock,*_=app
    started=choose_start(app)
    original=started.state.to_dict()
    with pytest.raises(InvalidEvent,match="due time"):
        db.append("world","early",started.state.revision,[ev("ScheduledEventFired",{"id":"npc-action:first"})],clock_authorized=True)
    assert db.load("world").to_dict()==original


def test_no_arbitrary_repetition_of_action_effects(app):
    db,clock,*_=app
    a=choose_start(app)
    done=clock.advance("world",seconds=180,command_id="advance",expected_revision=a.state.revision).state
    assert done.resources["nora"]["labor_units"]==1
    with pytest.raises(InvalidEvent):
        db.append("world","again",done.revision,[ev("ScheduledEventFired",{"id":"npc-action:first"},time=180)],clock_authorized=True)
    assert db.load("world").resources["nora"]["labor_units"]==1


def test_decision_is_not_automatically_repeated(app):
    db,clock,*_=app
    a=choose_start(app)
    done=clock.advance("world",seconds=1000,command_id="many",expected_revision=a.state.revision).state
    assert len(done.actions)==1 and done.npcs["nora"]["last_decision"]["at"]==0


def test_world_validation_rejects_corrupt_action_snapshot(app):
    db,clock,*_=app
    a=choose_start(app)
    db.snapshot("world")
    db.db.execute("UPDATE snapshots SET state='{}'")
    with pytest.raises(IntegrityError):db.load("world")


def test_full_replay_matches_two_independent_worlds(tmp_path):
    results=[]
    for idx in range(2):
        with SQLiteEventStore(tmp_path/f"{idx}.db") as db:
            setup(db)
            clock=TimeEngine(db);clock.open_session("world")
            npc=NPCService(db,clock); action=NPCActionService(db,clock)
            for who in ("nora","basim"):
                npc.decide("world",who,command_id="plan:"+who,expected_revision=db.load("world").revision)
                action.start("world",who,"start:"+who,expected_revision=db.load("world").revision)
            clock.advance("world",seconds=200,command_id="clock",expected_revision=db.load("world").revision)
            results.append(db.verify("world").to_dict())
    assert results[0]==results[1]


def test_action_effects_are_recorded_not_hidden(app):
    db,clock,*_=app
    a=choose_start(app)
    done=clock.advance("world",seconds=180,command_id="c",expected_revision=a.state.revision).state
    assert done.actions["first"]["result"]["needs"]["fatigue"]==(5,20)
    types=[json.loads(row[0])["event_type"] for row in db.db.execute("SELECT payload FROM events ORDER BY seq")]
    assert types[-1]=="ScheduledEventFired" and "NPCActionStarted" in types


def test_actions_do_not_touch_player_state(app):
    db,clock,*_=app
    state=db.load("world")
    assert "carlos" not in state.entities
    a=choose_start(app)
    after=clock.advance("world",seconds=180,command_id="advance",expected_revision=a.state.revision).state
    assert "carlos" not in after.entities and "carlos" not in after.npcs


def test_wait_uses_time_and_changes_hunger_without_fabricated_resources(tmp_path):
    with SQLiteEventStore(tmp_path/"wait.db") as db:
        setup(db,fatigue=0,hunger=0,safety=100,earn=0,explore=0)
        clock=TimeEngine(db);clock.open_session("world")
        npc=NPCService(db,clock);action=NPCActionService(db,clock)
        decision=npc.decide("world","nora",command_id="wait",expected_revision=db.load("world").revision)
        assert decision.action == "wait"
        started=action.start("world","nora","w",expected_revision=db.load("world").revision)
        assert started.due == DURATIONS["wait"] == 60
        result=clock.advance("world",seconds=60,command_id="advance",expected_revision=started.state.revision).state
        assert result.actions["w"]["status"]=="completed"
        assert result.npcs["nora"]["needs"]["hunger"]==5
        assert result.resources["nora"]["labor_units"]==0
        assert result.actions["w"]["result"]["counters"]=={}


def test_paused_world_cannot_fire_action_even_with_clock_capability(app):
    db,clock,*_=app
    started=choose_start(app)
    clock.close_session("world")
    with pytest.raises(InvalidEvent,match="active play session"):
        db.append("world","forced",started.state.revision,[ev("ScheduledEventFired",
            {"id":"npc-action:first"})],clock_authorized=True)
    assert db.load("world").actions["first"]["status"]=="running"


def test_reserved_action_schedule_cannot_be_orphaned(app):
    db, clock, *_ = app
    before = db.load('world')
    orphan = ev('ScheduledEventCreated', {'id':'npc-action:orphan', 'due':10,
        'order':before.next_schedule_order, 'kind':'signal',
        'payload':{'__npc_action_id':'orphan'}, 'interrupt':False})
    with pytest.raises(InvalidEvent, match='orphaned'):
        db.append('world','orphan',before.revision,[orphan], action_authorized=True)
    assert db.load('world').to_dict() == before.to_dict()
    assert db.db.execute("SELECT count(*) FROM commands WHERE command_id='orphan'").fetchone()[0] == 0


def test_reserved_signal_requires_matching_action_within_same_atomic_batch(app):
    db, clock, npc, _ = app
    npc.decide('world','nora',command_id='decide',expected_revision=db.load('world').revision)
    before = db.load('world')
    e = ev('ScheduledEventCreated', {'id':'npc-action:orphan2', 'due':180,
        'order':before.next_schedule_order, 'kind':'signal',
        'payload':{'__npc_action_id':'orphan2'}, 'interrupt':False})
    with pytest.raises(InvalidEvent, match='orphaned'):
        db.append('world','single',before.revision,[e],action_authorized=True)
    from carlos_sim.actions import NPCActionService
    started = NPCActionService(db, clock).start('world','nora','valid',expected_revision=before.revision)
    assert started.state.actions['valid']['status'] == 'running'
    assert db.verify('world').to_dict() == started.state.to_dict()
