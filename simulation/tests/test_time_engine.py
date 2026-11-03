import pytest
from carlos_sim import DomainEvent, SQLiteEventStore
from carlos_sim.store import InvalidEvent, RevisionConflict, DuplicateCommand
from carlos_sim.time_engine import TimeEngine, SessionClosed, AdvanceLimitExceeded


@pytest.fixture
def env(tmp_path):
    with SQLiteEventStore(tmp_path / "clock.db") as db:
        db.create_world("village")
        yield db, TimeEngine(db)


def test_session_required_and_time_frozen(env):
    db, clock = env
    with pytest.raises(SessionClosed):
        clock.advance("village", seconds=100, command_id="a", expected_revision=0)
    clock.open_session("village")
    clock.close_session("village")
    assert db.load("village").time == 0
    with pytest.raises(SessionClosed):
        clock.schedule_signal("village", "a", due=10, payload={}, expected_revision=0)


def test_explicit_advance_and_read_do_not_tick(env):
    db, clock = env
    clock.open_session("village")
    result = clock.advance("village", seconds=30, command_id="move", expected_revision=0)
    assert (result.elapsed_seconds, result.remaining_seconds, result.interrupted) == (30,0,False)
    assert db.load("village").time == 30
    db.snapshot("village")
    assert db.verify("village").time == 30


def test_schedule_fires_at_due_and_preserves_order(env):
    db,clock=env
    clock.open_session("village")
    clock.schedule_signal("village","b",due=20,payload={"msg":"b"},expected_revision=0)
    clock.schedule_signal("village","a",due=20,payload={"msg":"a"},expected_revision=1)
    result=clock.advance("village",seconds=25,command_id="walk",expected_revision=2)
    assert result.fired_ids == ("b","a")
    assert result.state.time == 25 and result.state.scheduled == {}
    assert db.verify("village").to_dict() == result.state.to_dict()


def test_interruption_leaves_remaining_time(env):
    db,clock=env
    clock.open_session("village")
    clock.schedule_signal("village","alarm",due=10,payload={},interrupt=True,expected_revision=0)
    result=clock.advance("village",seconds=50,command_id="wait",expected_revision=1)
    assert (result.state.time,result.remaining_seconds,result.interrupted,result.fired_ids)==(10,40,True,("alarm",))
    result2=clock.advance("village",seconds=result.remaining_seconds,command_id="continue",expected_revision=result.state.revision)
    assert result2.state.time==50 and not result2.interrupted


def test_same_time_second_signal_after_interruption(env):
    db,clock=env
    clock.open_session("village")
    clock.schedule_signal("village","first",due=10,payload={},interrupt=True,expected_revision=0)
    clock.schedule_signal("village","second",due=10,payload={},interrupt=False,expected_revision=1)
    first=clock.advance("village",seconds=20,command_id="step1",expected_revision=2)
    assert first.fired_ids==("first",)
    second=clock.advance("village",seconds=10,command_id="step2",expected_revision=first.state.revision)
    assert second.fired_ids==("second",) and second.state.time==20


def test_cancelled_not_fired(env):
    db,clock=env
    clock.open_session("village")
    clock.schedule_signal("village","x",due=10,payload={},expected_revision=0)
    clock.cancel("village","x",command_id="cancel",expected_revision=1)
    result=clock.advance("village",seconds=20,command_id="wait",expected_revision=2)
    assert result.fired_ids==() and result.state.time==20


def test_no_clock_skipping_due_event_via_store(env):
    db,clock=env
    clock.open_session("village")
    clock.schedule_signal("village","x",due=10,payload={},expected_revision=0)
    ev=DomainEvent("TimeAdvanced",None,"manual",20,{"from":0,"to":20})
    with pytest.raises(InvalidEvent,match="skip"):
        db.append("village","illegal",1,[ev],clock_authorized=True)
    assert db.load("village").time==0


def test_direct_clock_without_capability_rejected(env):
    db,_=env
    ev=DomainEvent("TimeAdvanced",None,"manual",10,{"from":0,"to":10})
    with pytest.raises(InvalidEvent, match="capability"):
        db.append("village","bad",0,[ev])


def test_no_schedule_in_past_or_at_now(env):
    db,clock=env
    clock.open_session("village")
    for due in (0,-1):
        with pytest.raises(InvalidEvent):
            clock.schedule_signal("village",f"bad{due}",due=due,payload={},expected_revision=0)


def test_invalid_action_payload(env):
    _,clock=env
    clock.open_session("village")
    with pytest.raises(ValueError):
        clock.schedule_signal("village","bad",due=10,payload={"bad":object()},expected_revision=0)


def test_reopen_does_not_advance_until_authorized(tmp_path):
    path=tmp_path/"state.db"
    with SQLiteEventStore(path) as db:
        db.create_world("v")
        clock=TimeEngine(db);clock.open_session("v")
        clock.schedule_signal("v","x",due=60,payload={"secret":True},expected_revision=0)
        db.snapshot("v")
    with SQLiteEventStore(path) as db:
        new_clock=TimeEngine(db)
        assert db.verify("v").time==0
        with pytest.raises(SessionClosed):
            new_clock.advance("v",seconds=70,command_id="resume",expected_revision=1)
        new_clock.open_session("v")
        result=new_clock.advance("v",seconds=70,command_id="resume",expected_revision=1)
        assert result.state.time==70 and result.fired_ids==("x",)


def test_corrupt_snapshot_tampering_detected(env):
    db,clock=env
    clock.open_session("village")
    clock.schedule_signal("village","x",due=10,payload={},expected_revision=0)
    db.snapshot("village")
    db.db.execute("UPDATE snapshots SET state='{}'")
    from carlos_sim import IntegrityError
    with pytest.raises(IntegrityError):db.load("village")


def test_bounded_event_processing_atomic(env):
    db,clock=env
    clock.open_session("village")
    clock.schedule_signal("village","a",due=10,payload={},expected_revision=0)
    clock.schedule_signal("village","b",due=20,payload={},expected_revision=1)
    tight=TimeEngine(db,max_events_per_advance=2)
    tight.open_session("village")
    with pytest.raises(AdvanceLimitExceeded):
        tight.advance("village",seconds=30,command_id="overflow",expected_revision=2)
    assert db.load("village").time==0 and len(db.load("village").scheduled)==2


def test_invalid_due_type_or_reused_command(env):
    db,clock=env
    clock.open_session("village")
    with pytest.raises(ValueError):
        clock.schedule_signal("village","x",due=True,payload={},expected_revision=0)
    clock.advance("village",seconds=2,command_id="x",expected_revision=0)
    with pytest.raises(DuplicateCommand):
        clock.advance("village",seconds=3,command_id="x",expected_revision=1)


def test_revision_conflict_schedule(env):
    db,clock=env
    clock.open_session("village")
    clock.schedule_signal("village","a",due=10,payload={},expected_revision=0)
    with pytest.raises(RevisionConflict):
        clock.schedule_signal("village","b",due=20,payload={},expected_revision=0)


def test_direct_firing_wrong_order_refused(env):
    db,clock=env
    clock.open_session("village")
    clock.schedule_signal("village","a",due=10,payload={},expected_revision=0)
    clock.schedule_signal("village","b",due=10,payload={},expected_revision=1)
    with pytest.raises(InvalidEvent):
        db.append("village","illegal",2,[DomainEvent("ScheduledEventFired",None,"test",0,{"id":"b"})],clock_authorized=True)


def test_zero_and_negative_wait_rejected(env):
    _,clock=env;clock.open_session("village")
    for s in (0,-1,True):
        with pytest.raises(ValueError):clock.advance("village",seconds=s,command_id="x",expected_revision=0)


def test_replay_deterministic_across_two_fresh_worlds(tmp_path):
    states=[]
    for index in range(2):
        with SQLiteEventStore(tmp_path/f"world-{index}.sqlite") as db:
            db.create_world("test")
            clock=TimeEngine(db)
            clock.open_session("test")
            clock.schedule_signal("test","s1",due=6,payload={"label":"one"},expected_revision=0)
            clock.schedule_signal("test","s2",due=6,payload={"label":"two"},expected_revision=1)
            result=clock.advance("test",seconds=13,command_id="advance",expected_revision=2)
            states.append(db.verify("test").to_dict())
            assert result.fired_ids == ("s1","s2")
    assert states[0] == states[1]


def test_firing_cannot_impersonate_npc(env):
    db,clock=env
    clock.open_session("village")
    db.append("village","loc",0,[DomainEvent("LocationCreated",None,"setup",0,{"id":"v","name":"Village"}),
                                    DomainEvent("EntityCreated",None,"setup",0,{"id":"n","name":"Nora","location_id":"v","controller":"npc"})])
    clock.schedule_signal("village","signal",due=10,payload={},expected_revision=2)
    db.append("village","time",3,[DomainEvent("TimeAdvanced",None,"test",10,{"from":0,"to":10})],clock_authorized=True)
    with pytest.raises(InvalidEvent, match="impersonate"):
        db.append("village","badfire",4,[DomainEvent("ScheduledEventFired","n","fake",10,{"id":"signal"})],clock_authorized=True)
