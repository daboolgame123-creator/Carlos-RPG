"""02-H2 adversarial seven-person village: perception is not accusation."""
import pytest
from carlos_sim import DomainEvent, SQLiteEventStore, TimeEngine, NPCPropertyService, personal_property_evidence
from carlos_sim.store import InvalidEvent, DuplicateCommand
from test_property_02h1 import village


@pytest.fixture
def scenario(tmp_path):
    with SQLiteEventStore(tmp_path / "h2.sqlite") as db:
        village(db)
        clock = TimeEngine(db)
        clock.open_session("v")
        yield db, clock, NPCPropertyService(db, clock)


def take(db, svc, *, witness=(), ident="t1"):
    return svc.take("v", "basim", ident, "bakery", "bakery", "bread", 1,
                    witnessed_by=witness, expected_revision=db.load("v").revision).state


def claim(db, svc, who="nora", ident="c1", kind="accusation", subject="adel",
          taking=None, site="bakery", resource="bread"):
    return svc.claim("v", who, ident, kind, site, resource, 1,
                     subject_id=subject, taking_id=taking,
                     expected_revision=db.load("v").revision).state


def test_unseen_taking_no_omniscient_witness(scenario):
    db, _, svc = scenario
    after = take(db, svc)
    assert after.resources["bakery"]["bread"] == 1
    assert not after.property_sightings
    for name in ("nora", "adel", "salma", "huda", "omar", "layla"):
        assert personal_property_evidence(after, name)["sightings"] == ()
    assert db.verify("v").to_dict() == after.to_dict()


def test_explicit_local_witness_only_learns_real_sighting(scenario):
    db, _, svc = scenario
    after = take(db, svc, witness=("salma",))
    seen = personal_property_evidence(after, "salma")["sightings"]
    assert len(seen) == 1
    assert seen[0]["actor_id"] == "basim"
    assert seen[0]["taking_id"] == "t1"
    assert personal_property_evidence(after, "nora")["sightings"] == ()
    assert personal_property_evidence(after, "omar")["sightings"] == ()
    assert db.verify("v").to_dict() == after.to_dict()


@pytest.mark.parametrize("witnesses", [("omar",), ("basim",), ("ghost",), ("salma","salma"), ("salma","omar")])
def test_remote_fake_duplicate_or_self_witness_rejected_atomically(scenario, witnesses):
    db, _, svc = scenario
    before = db.load("v").to_dict()
    with pytest.raises(InvalidEvent):
        take(db, svc, witness=witnesses)
    assert db.load("v").to_dict() == before


def test_false_accusation_coexists_with_true_firsthand_claim(scenario):
    db, _, svc = scenario
    take(db, svc, witness=("salma",))
    a = claim(db, svc, who="nora", ident="wrong", subject="adel")
    assert a.property_claims["wrong"]["basis"] == "unverified_statement"
    assert a.property_claims["wrong"]["status"] == "unverified"
    b = claim(db, svc, who="salma", ident="saw", subject="basim", taking="t1")
    assert b.property_claims["saw"]["basis"] == "direct_sighting"
    assert b.property_claims["wrong"]["subject_id"] == "adel"
    assert b.resources["bakery"]["bread"] == 1
    assert b.resources["basim"]["bread"] == 1
    assert personal_property_evidence(b, "nora")["claims"][0]["id"] == "wrong"
    assert personal_property_evidence(b, "nora")["sightings"] == ()
    assert personal_property_evidence(b, "omar")["claims"] == ()
    assert db.verify("v").to_dict() == b.to_dict()


def test_victim_can_report_loss_without_knowing_secret_taking_id(scenario):
    db, _, svc = scenario
    take(db, svc)
    state = claim(db, svc, who="adel", ident="missing", kind="loss",
                  subject=None, taking=None)
    assert state.property_claims["missing"]["taking_id"] is None
    assert state.property_claims["missing"]["status"] == "unverified"
    assert db.verify("v").to_dict() == state.to_dict()


@pytest.mark.parametrize("who,taking,site", [
    ("nora", "t1", "bakery"), ("omar", "t1", "square"),
    ("salma", "invented", "bakery"),
])
def test_unobserved_taking_id_is_not_public_knowledge(scenario, who, taking, site):
    db, _, svc = scenario
    take(db, svc, witness=("huda",))
    old = db.load("v").to_dict()
    with pytest.raises(InvalidEvent):
        claim(db, svc, who=who, taking=taking, site=site)
    assert db.load("v").to_dict() == old


def test_untrusted_claim_or_witness_forgery_cannot_mutate(scenario):
    db, _, svc = scenario
    old = db.load("v").to_dict()
    ev = DomainEvent("PropertyClaimFiled", "nora", "untrusted claim", 0, {
        "id": "forged", "claim_kind": "accusation", "subject_id": "basim",
        "site_id": "bakery", "resource": "bread", "quantity": 1, "taking_id": None})
    with pytest.raises(InvalidEvent):
        db.append("v", "forged", db.load("v").revision, [ev])
    assert db.load("v").to_dict() == old


def test_same_id_claim_rejected_with_no_late_change(scenario):
    db, _, svc = scenario
    claim(db, svc)
    before = db.load("v").to_dict()
    with pytest.raises(DuplicateCommand):
        claim(db, svc)
    assert db.load("v").to_dict() == before
