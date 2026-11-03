import sqlite3
import pytest
from carlos_sim import SQLiteEventStore, DomainEvent, apply_event, WorldState, canonical_hash
from carlos_sim import InvalidEvent, IntegrityError, RevisionConflict, DuplicateCommand, UnsupportedVersion


def ev(kind, data, time=0, cause="test"):
    return DomainEvent(kind, None, cause, time, data)


@pytest.fixture
def store(tmp_path):
    with SQLiteEventStore(tmp_path / "world.sqlite") as db:
        db.create_world("test-world")
        yield db


def location(): return ev("LocationCreated", {"id":"market","name":"Market"})
def npc(): return ev("EntityCreated", {"id":"npc1","name":"Nora","location_id":"market","controller":"npc"})
def resource(old,new): return DomainEvent("ResourceChanged", "npc1" if old is not None else None, "test", 0, {"owner_id":"npc1","resource":"grain","previous":old,"current":new,"source":"consumption" if old is not None else "initialization"})


def test_genesis(store):
    state=store.load("test-world")
    assert state.revision==0 and state.time==0 and state.resources=={}


def test_projection_and_replay(store):
    s=store.append("test-world","initial",0,[location(), npc(), resource(None,3)],bootstrap=True)
    assert s.revision==3 and s.resources["npc1"]["grain"]==3
    assert store.verify("test-world").to_dict()==s.to_dict()


def test_unknown_is_not_zero(store):
    store.append("test-world","init",0,[location(),npc()])
    with pytest.raises(InvalidEvent): store.append("test-world","bad",2,[resource(0,2)])
    assert store.load("test-world").resources=={}
    assert store.append("test-world","good",2,[resource(None,0)],bootstrap=True).resources["npc1"]["grain"]==0


def test_invalid_event_is_atomic(store):
    with pytest.raises(InvalidEvent):store.append("test-world","broken",0,[location(),ev("Nonexistent",{})])
    assert store.load("test-world").revision==0
    assert store.db.execute("SELECT count(*) FROM events").fetchone()[0]==0


def test_idempotency_and_conflict(store):
    events=[location()]
    assert store.append("test-world","cmd",0,events).revision==1
    assert store.append("test-world","cmd",0,events).revision==1
    with pytest.raises(DuplicateCommand):store.append("test-world","cmd",0,[ev("LocationCreated",{"id":"x","name":"X"})])
    with pytest.raises(RevisionConflict):store.append("test-world","cmd2",0,[npc()])
    assert store.load("test-world").revision==1


def test_snapshot_and_tail(store):
    store.append("test-world","init",0,[location(),npc(),resource(None,10)],bootstrap=True)
    store.snapshot("test-world")
    store.append("test-world","update",3,[resource(10,7),ev("TimeAdvanced",{"from":0,"to":12},12)],clock_authorized=True)
    assert store.load("test-world").to_dict()==store.load("test-world",use_snapshot=False).to_dict()
    assert store.verify("test-world").time==12


def test_snapshot_tampering_detected(store):
    store.snapshot("test-world")
    store.db.execute("UPDATE snapshots SET state='{}'")
    with pytest.raises(IntegrityError):store.load("test-world")


def test_unsupported_schema(store):
    store.db.execute("UPDATE worlds SET schema_version=999")
    with pytest.raises(UnsupportedVersion):store.load("test-world")


def test_event_tampering_detected(store):
    store.append("test-world","init",0,[location()])
    store.db.execute("UPDATE events SET payload='{}'")
    with pytest.raises(IntegrityError):store.load("test-world")


def test_no_time_passage_on_read_save(store):
    store.append("test-world","init",0,[location()])
    for _ in range(3):
        store.load("test-world");store.snapshot("test-world")
    assert store.load("test-world").time==0


def test_time_advance_validation(store):
    with pytest.raises(InvalidEvent):store.append("test-world","bad",0,[ev("TimeAdvanced",{"from":0,"to":5},4)],clock_authorized=True)
    assert store.append("test-world","good",0,[ev("TimeAdvanced",{"from":0,"to":5},5)],clock_authorized=True).time==5
    with pytest.raises(InvalidEvent):store.append("test-world","bad2",1,[location()])


def test_no_hidden_data_in_player_view(store):
    store.append("test-world","init",0,[location(),npc(),resource(None,44)],bootstrap=True)
    assert store.player_view("test-world")=={"world_id":"test-world","time":0,"revision":3}


def test_external_mutation_does_not_affect_projection():
    s=WorldState("w")
    data={"id":"v","name":"Village"}
    e=ev("LocationCreated",data)
    result=apply_event(s,e)
    data["name"]="CHANGED"
    assert result.locations["v"]["name"]=="Village" and s.locations=={}


def test_stable_hash(store):
    a={"a":1,"b":2}
    b={"b":2,"a":1}
    assert canonical_hash(a)==canonical_hash(b)
    store.append("test-world","init",0,[location()])
    assert canonical_hash(store.load("test-world").to_dict())==canonical_hash(store.verify("test-world").to_dict())


def test_invalid_resource_balance(store):
    store.append("test-world","init",0,[location(),npc(),resource(None,2)],bootstrap=True)
    with pytest.raises(InvalidEvent):store.append("test-world","bad",3,[resource(2,-1)])
    assert store.load("test-world").resources["npc1"]["grain"]==2


def test_persists_after_reopening(tmp_path):
    p=tmp_path/"world.db"
    with SQLiteEventStore(p) as s:
        s.create_world("w")
        s.append("w","init",0,[location()])
        s.snapshot("w")
    with SQLiteEventStore(p) as s:
        assert s.verify("w").locations["market"]["name"]=="Market"


def test_immutable_internal_state(store):
    s=store.append("test-world","init",0,[location(),npc(),resource(None,2)],bootstrap=True)
    with pytest.raises(TypeError):
        s.resources["npc1"]["grain"]=999
    e=ev("ResourceChanged", {"owner_id":"npc1","resource":"grain","previous":2,"current":3})
    with pytest.raises(TypeError):
        e.data["current"]=999


def test_snapshot_cannot_rewrite_world_head(store):
    store.append("test-world","init",0,[location()])
    store.snapshot("test-world")
    store.db.execute("UPDATE snapshots SET revision=999 WHERE world_id='test-world'")
    with pytest.raises(IntegrityError):
        store.load("test-world")


def test_duplicate_world_rejected(store):
    with pytest.raises(sqlite3.IntegrityError):
        store.create_world("test-world")


def test_replay_is_deterministic_across_stores(tmp_path):
    states=[]
    for i in range(2):
        with SQLiteEventStore(tmp_path / f"{i}.db") as store:
            store.create_world("sample")
            store.append("sample","init",0,[location(), npc(), resource(None,5)],bootstrap=True)
            store.append("sample","time",3,[ev("TimeAdvanced",{"from":0,"to":120},120)],clock_authorized=True)
            states.append(canonical_hash(store.verify("sample").to_dict()))
    assert states[0]==states[1]


def test_transaction_rollback_on_insert_error(store):
    store.db.execute("CREATE TRIGGER reject_event BEFORE INSERT ON events BEGIN SELECT RAISE(FAIL,'test failure'); END")
    with pytest.raises(sqlite3.IntegrityError):
        store.append("test-world","init",0,[location()])
    assert store.load("test-world").revision==0
    assert store.db.execute("SELECT count(*) FROM commands").fetchone()[0]==0

def test_normal_event_cannot_change_clock(store):
    with pytest.raises(InvalidEvent, match="ordinary event"):
        store.append("test-world", "time-cheat", 0, [ev("LocationCreated", {"id":"x", "name":"X"}, 3600)])
    assert store.load("test-world").time == 0


def test_unknown_actor_rejected(store):
    actor = DomainEvent("LocationCreated", "ghost", "test", 0, {"id":"x","name":"X"})
    with pytest.raises(InvalidEvent, match="actor"):
        store.append("test-world", "ghost", 0, [actor])


def test_resource_creation_not_allowed_during_play(store):
    store.append("test-world", "init", 0, [location(), npc()], bootstrap=True)
    with pytest.raises(InvalidEvent, match="bootstrap"):
        store.append("test-world", "unauthorized", 2, [resource(None, 1000000)])
    assert store.load("test-world").resources == {}


def test_resource_bootstrap_replay_and_provenance(store):
    store.append("test-world", "init", 0, [location(), npc(), resource(None, 10)], bootstrap=True)
    store.snapshot("test-world")
    store.append("test-world", "consume", 3, [resource(10, 7)])
    assert store.verify("test-world").resources["npc1"]["grain"] == 7


def test_cannot_increase_resource_by_consumption(store):
    store.append("test-world", "init", 0, [location(), npc(), resource(None, 10)], bootstrap=True)
    with pytest.raises(InvalidEvent, match="decrease"):
        store.append("test-world", "mint", 3, [resource(10, 1000000)])


def test_consume_other_entity_resources_rejected(store):
    store.append("test-world", "init", 0, [location(), npc(), resource(None, 10)], bootstrap=True)
    bad = DomainEvent("ResourceChanged", "npc1", "test", 0, {"owner_id":"market","resource":"grain","previous":None,"current":5,"source":"consumption"})
    with pytest.raises(InvalidEvent):
        store.append("test-world", "steal", 3, [bad])


def test_bootstrap_after_clock_advanced_rejected(store):
    store.append("test-world", "init", 0, [location(), npc()], bootstrap=True)
    store.append("test-world", "time", 2, [ev("TimeAdvanced", {"from":0,"to":60},60)],clock_authorized=True)
    with pytest.raises(InvalidEvent):
        store.append("test-world", "late-init", 3, [DomainEvent("ResourceChanged", None, "test", 60, {"owner_id":"npc1", "resource":"gold", "previous":None, "current":5,"source":"initialization"})],bootstrap=True)


def test_bootstrap_flag_is_part_of_idempotency(store):
    store.append("test-world", "first", 0, [location()], bootstrap=True)
    with pytest.raises(DuplicateCommand):
        store.append("test-world", "first", 0, [location()], bootstrap=False)
