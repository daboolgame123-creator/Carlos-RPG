"""01-V: scarcity policy consequences grounded in actual NPC experience."""
from __future__ import annotations

import pytest

from carlos_sim import (
    DomainEvent, LivingWorldEngine, NPCAssistanceService,
    SQLiteEventStore, TimeEngine, WorldState,
    choose_food_route, choose_assistance_intent,
    recent_personal_depletion, recently_refused_by,
)
from carlos_sim.scarcity import (
    FAILED_SITE_RETRY_SECONDS, REFUSED_PROVIDER_RETRY_SECONDS,
)
from carlos_sim.store import DuplicateCommand
from carlos_sim.time_engine import AdvanceLimitExceeded

from test_food_navigation import make_world, tell, learn_local_roads


@pytest.fixture
def village(tmp_path):
    with SQLiteEventStore(tmp_path / "scarcity.sqlite") as db:
        make_world(db, hunger=85)
        clock = TimeEngine(db)
        clock.open_session("village")
        yield db, clock


def option_engine(db, clock, *, budget=1000, **overrides):
    options = dict(navigation_enabled=True, knowledge_enabled=True,
                   foraging_enabled=True, food_navigation_enabled=True,
                   assistance_enabled=True, scarcity_enabled=True,
                   max_events_per_advance=budget)
    options.update(overrides)
    return LivingWorldEngine(db, clock, **options)


def fail_history_state(base: WorldState, *, owner="adel", at=0) -> WorldState:
    data = base.to_dict()
    # A pure policy probe: this is a fixture representing a projected
    # historical failure, never inserted or claimed to be an authentic event.
    data["foraging_attempts"]["failed-at-grove"] = {
        "npc_id": owner, "site_id": "grove", "at": at,
        "outcome": "depleted",
    }
    return WorldState(**data)


@pytest.mark.parametrize("invalid", [None, 1, 0, "true", [], {}])
def test_scarcity_flag_requires_real_boolean(village, invalid):
    db, clock = village
    with pytest.raises(ValueError, match="scarcity_enabled"):
        option_engine(db, clock, scarcity_enabled=invalid)


@pytest.mark.parametrize("omit", ["food_navigation_enabled", "assistance_enabled"])
def test_scarcity_dependencies_are_explicit(village, omit):
    db, clock = village
    with pytest.raises(ValueError, match="scarcity_enabled requires"):
        option_engine(db, clock, **{omit: False})


def test_personal_failed_source_loses_to_known_alternative(village):
    db, clock = village
    tell(db, site="grove")
    tell(db, site="hill")
    learn_local_roads(db, clock)
    original = db.load("village")
    assert choose_food_route(original, "adel").destination == "grove"
    own_failure = fail_history_state(original)
    assert recent_personal_depletion(
        own_failure, "adel", "grove",
        own_failure.npcs["adel"]["beliefs"]["food:grove"]
    )
    assert choose_food_route(own_failure, "adel").destination == "grove"
    alternative = choose_food_route(own_failure, "adel", scarcity_enabled=True)
    assert alternative is not None
    assert (alternative.destination, alternative.route_id, alternative.total_seconds) == (
        "hill", "market-hill", 100
    )
    # Neither a distant true stock change nor another NPC's private belief
    # may alter this actor's subjective alternative.
    poisoned = own_failure.to_dict()
    poisoned["resources"]["hill"]["wild_food"] = 9999
    poisoned["resources"]["grove"]["wild_food"] = 0
    poisoned["npcs"]["basim"]["beliefs"]["food:hill"] = {
        "text": "food-state:empty; observed_at=0",
        "source": "observation:hill", "received_at": 0, "confidence": 90,
    }
    assert choose_food_route(WorldState(**poisoned), "adel",
                             scarcity_enabled=True) == alternative


def test_other_persons_failure_cannot_poison_own_route(village):
    db, clock = village
    tell(db, site="grove")
    learn_local_roads(db, clock)
    other_failure = fail_history_state(db.load("village"), owner="nora")
    assert choose_food_route(other_failure, "adel",
                             scarcity_enabled=True).destination == "grove"


def test_failed_site_recovers_after_timeout_or_new_direct_sighting(village):
    db, clock = village
    tell(db, site="grove")
    learn_local_roads(db, clock)
    failed = fail_history_state(db.load("village"))
    assert choose_food_route(failed, "adel", scarcity_enabled=True) is None
    stale = failed.to_dict()
    stale["time"] = FAILED_SITE_RETRY_SECONDS - 1
    assert choose_food_route(WorldState(**stale), "adel",
                             scarcity_enabled=True) is None
    expired = failed.to_dict()
    expired["time"] = FAILED_SITE_RETRY_SECONDS
    assert choose_food_route(WorldState(**expired), "adel",
                             scarcity_enabled=True) is not None

    witnessed = failed.to_dict()
    witnessed["time"] = 200
    witnessed["npcs"]["adel"]["beliefs"]["food:grove"] = {
        "text": "food-state:present; observed_at=200",
        "source": "observation:grove", "received_at": 200, "confidence": 90,
    }
    assert choose_food_route(WorldState(**witnessed), "adel",
                             scarcity_enabled=True).destination == "grove"


def test_no_alternative_does_not_invent_food_or_route(village):
    db, clock = village
    tell(db, site="grove")
    learn_local_roads(db, clock)
    own_failure = fail_history_state(db.load("village"))
    assert choose_food_route(own_failure, "adel", scarcity_enabled=True) is None
    assert own_failure.resources["adel"]["food"] == 0


def record_refusal(db, clock, *, owner="adel", provider="basim",
                   request_id="first", choice="declined"):
    svc = NPCAssistanceService(db, clock)
    svc.request("village", owner, provider, "food", 2, request_id,
                expected_revision=db.load("village").revision)
    if choice == "declined":
        svc.respond("village", provider, request_id, accept=False,
                    command_id="decline-" + request_id,
                    expected_revision=db.load("village").revision)
    elif choice == "promise_withdrawn":
        svc.respond("village", provider, request_id, accept=True,
                    command_id="promise-" + request_id,
                    expected_revision=db.load("village").revision)
        svc.cancel("village", provider, request_id, reason="promise_withdrawn",
                   command_id="withdraw-" + request_id,
                   expected_revision=db.load("village").revision)
    elif choice == "request_withdrawn":
        svc.cancel("village", owner, request_id, reason="request_withdrawn",
                   command_id="withdraw-" + request_id,
                   expected_revision=db.load("village").revision)
    else:
        raise ValueError("unknown test result")


@pytest.mark.parametrize("choice", ["declined", "promise_withdrawn"])
def test_refused_help_selects_another_peer_after_existing_global_wait(
        village, choice):
    db, clock = village
    record_refusal(db, clock, choice=choice)
    before = db.load("village")
    assert recently_refused_by(before, "adel", "basim")
    assert choose_assistance_intent(before, "adel", "request",
                                    scarcity_enabled=True) is None
    clock.advance("village", seconds=899, command_id="reask-899",
                  expected_revision=before.revision)
    assert choose_assistance_intent(db.load("village"), "adel", "request",
                                    scarcity_enabled=True) is None
    clock.advance("village", seconds=1, command_id="reask-900",
                  expected_revision=db.load("village").revision)
    state = db.load("village")
    old = choose_assistance_intent(state, "adel", "request")
    new = choose_assistance_intent(state, "adel", "request",
                                   scarcity_enabled=True)
    assert old is not None and old.fields["provider"] == "basim"
    assert new is not None and new.fields["provider"] == "huda"
    assert state.resources["adel"]["food"] == 0
    assert state.resources["basim"]["food"] == 0


def test_requester_own_withdrawal_does_not_count_as_provider_refusal(village):
    db, clock = village
    record_refusal(db, clock, choice="request_withdrawn")
    assert not recently_refused_by(db.load("village"), "adel", "basim")
    clock.advance("village", seconds=900, command_id="withdrawal-timeout",
                  expected_revision=db.load("village").revision)
    choice = choose_assistance_intent(db.load("village"), "adel", "request",
                                      scarcity_enabled=True)
    assert choice is not None and choice.fields["provider"] == "basim"


def test_refusal_memory_expires_at_exact_boundary(village):
    db, clock = village
    record_refusal(db, clock)
    clock.advance("village", seconds=REFUSED_PROVIDER_RETRY_SECONDS - 1,
                  command_id="before-expiry",
                  expected_revision=db.load("village").revision)
    state = db.load("village")
    assert recently_refused_by(state, "adel", "basim")
    assert choose_assistance_intent(state, "adel", "request",
                                    scarcity_enabled=True).fields["provider"] == "huda"
    clock.advance("village", seconds=1, command_id="at-expiry",
                  expected_revision=db.load("village").revision)
    state = db.load("village")
    assert not recently_refused_by(state, "adel", "basim")
    assert choose_assistance_intent(state, "adel", "request",
                                    scarcity_enabled=True).fields["provider"] == "basim"


def test_real_refusal_survives_sqlite_snapshot_close_reopen_and_autonomy(tmp_path):
    path = tmp_path / "01v-reopen.sqlite"
    with SQLiteEventStore(path) as db:
        make_world(db, hunger=85)
        clock = TimeEngine(db)
        clock.open_session("village")
        record_refusal(db, clock)
        clock.advance("village", seconds=900, command_id="advance-to-900",
                      expected_revision=db.load("village").revision)
        db.snapshot("village")
        original = db.load("village").to_dict()
        assert db.verify("village").to_dict() == original

    with SQLiteEventStore(path) as db:
        clock = TimeEngine(db)
        clock.open_session("village")
        assert db.load("village").to_dict() == original
        assert db.verify("village").to_dict() == original
        outcome = option_engine(db, clock).advance(
            "village", seconds=1, command_id="new-provider",
            expected_revision=db.load("village").revision
        )
        new = outcome.state
        assert new.obligations["first"]["status"] == "declined"
        assert new.obligations["auto-help:adel:900"]["provider"] == "huda"
        assert new.resources["adel"]["food"] == 0
        assert sum(new.resources[n]["food"] for n in
                   ("adel", "basim", "huda", "nora", "salma")) == 0
        assert db.verify("village").to_dict() == new.to_dict()
        with pytest.raises(DuplicateCommand):
            option_engine(db, clock).advance(
                "village", seconds=1, command_id="new-provider",
                expected_revision=db.load("village").revision
            )


def test_event_budget_exhaustion_rolls_back_refusal_response(village):
    db, clock = village
    record_refusal(db, clock)
    clock.advance("village", seconds=900, command_id="advance-to-900",
                  expected_revision=db.load("village").revision)
    before = db.load("village").to_dict()
    count = db.db.execute(
        "SELECT count(*) FROM events WHERE world_id='village'"
    ).fetchone()[0]
    with pytest.raises(AdvanceLimitExceeded):
        option_engine(db, clock, budget=1).advance(
            "village", seconds=1, command_id="budget-refuse",
            expected_revision=db.load("village").revision
        )
    assert db.load("village").to_dict() == before
    assert db.db.execute(
        "SELECT count(*) FROM events WHERE world_id='village'"
    ).fetchone()[0] == count
    assert db.verify("village").to_dict() == before


def test_scarcity_flag_off_preserves_legacy_assistance_and_navigation(village):
    db, clock = village
    record_refusal(db, clock)
    clock.advance("village", seconds=900, command_id="reask-exact",
                  expected_revision=db.load("village").revision)
    state = db.load("village")
    assert choose_assistance_intent(state, "adel", "request").fields["provider"] == "basim"
    assert choose_assistance_intent(state, "adel", "request",
                                    scarcity_enabled=False).fields["provider"] == "basim"
    tell(db, site="grove")
    learn_local_roads(db, clock)
    original = db.load("village")
    assert choose_food_route(original, "adel") == choose_food_route(
        original, "adel", scarcity_enabled=False
    )


def test_actual_failed_forages_are_durable_no_food_appears(tmp_path):
    from test_gathering_autonomy import make_world as make_seven_world

    with SQLiteEventStore(tmp_path / "real-depletion.sqlite") as db:
        make_seven_world(db)
        clock = TimeEngine(db)
        clock.open_session("r")
        outcome = LivingWorldEngine(
            db, clock, foraging_enabled=True, knowledge_enabled=True
        ).advance("r", seconds=120, command_id="four-forage",
                  expected_revision=db.load("r").revision)
        state = outcome.state
        failed = [v for v in state.foraging_attempts.values()
                  if v["outcome"] == "depleted"]
        assert len(failed) == 2
        assert all(v["quantity"] == 0 and v["site_after"] == 0
                   for v in failed)
        for item in failed:
            reporter = item["npc_id"]
            claim = {
                "text": "food-state:present; observed_at=0",
                "source": "basim", "received_at": 0, "confidence": 60,
            }
            assert recent_personal_depletion(
                state, reporter, item["site_id"], claim
            )
        assert state.resources["grove"]["wild_food"] == 0
        assert sum(v["quantity"] for v in state.foraging_attempts.values()) == 2
        assert db.verify("r").to_dict() == state.to_dict()


def test_other_requesters_refusal_is_not_known_as_my_refusal(village):
    db, clock = village
    record_refusal(db, clock, owner="huda")
    clock.advance("village", seconds=900, command_id="wait-900",
                  expected_revision=db.load("village").revision)
    state = db.load("village")
    assert recently_refused_by(state, "huda", "basim")
    assert not recently_refused_by(state, "adel", "basim")
    intent = choose_assistance_intent(state, "adel", "request",
                                      scarcity_enabled=True)
    assert intent is not None and intent.fields["provider"] == "basim"


def test_all_refused_providers_mean_no_new_request_or_magic_food(tmp_path):
    from test_assistance import setup as make_two_people, e

    with SQLiteEventStore(tmp_path / "no-alternative.sqlite") as db:
        make_two_people(db, food_a=1, food_b=0)
        clock = TimeEngine(db)
        clock.open_session("w")
        s = db.load("w")
        db.append("w", "nora-hungry", s.revision, [
            e("NPCNeedChanged", {
                "npc_id": "nora", "need": "hunger",
                "previous": 25, "current": 85,
            }, actor="nora"),
        ], npc_authorized=True)
        svc = NPCAssistanceService(db, clock)
        svc.request("w", "nora", "basim", "food", 2, "first",
                    expected_revision=db.load("w").revision)
        svc.respond("w", "basim", "first", accept=False,
                    command_id="basim-refuses",
                    expected_revision=db.load("w").revision)
        clock.advance("w", seconds=900, command_id="global-reask",
                      expected_revision=db.load("w").revision)
        assert choose_assistance_intent(db.load("w"), "nora", "request",
                                        scarcity_enabled=True) is None
        assert db.load("w").resources["nora"]["food"] == 1
        assert db.verify("w").to_dict() == db.load("w").to_dict()


def test_refusal_then_alternative_real_delivery_is_resource_conserving(tmp_path):
    from test_assistance import setup as make_two_people, e

    with SQLiteEventStore(tmp_path / "alternative-fulfilment.sqlite") as db:
        make_two_people(db, food_a=1, food_b=0)
        s = db.load("w")
        # A separate trusted setup adds a second physically present source.
        # This is real bootstrap inventory, never created by a refusal policy.
        newcomer = [
            e("EntityCreated", {
                "id": "zara", "name": "Zara",
                "location_id": "market", "controller": "npc",
            }),
            e("NPCConfigured", {
                "npc_id": "zara", "role": "resident",
                "needs": {"fatigue": 5, "hunger": 25, "safety": 0},
                "goals": {"earn": 20, "explore": 10, "survive": 20},
            }),
        ]
        for resource, amount in (("food", 10), ("water", 0),
                                 ("labor_units", 0),
                                 ("investigation_attempts", 0)):
            newcomer.append(e("ResourceChanged", {
                "owner_id": "zara", "resource": resource,
                "previous": None, "current": amount,
                "source": "initialization",
            }))
        db.append("w", "add-provider", s.revision, newcomer, bootstrap=True)
        clock = TimeEngine(db)
        clock.open_session("w")
        db.append("w", "nora-hungry", db.load("w").revision, [
            e("NPCNeedChanged", {
                "npc_id": "nora", "need": "hunger",
                "previous": 25, "current": 85,
            }, actor="nora"),
        ], npc_authorized=True)
        svc = NPCAssistanceService(db, clock)
        svc.request("w", "nora", "basim", "food", 2, "ask-basim",
                    expected_revision=db.load("w").revision)
        svc.respond("w", "basim", "ask-basim", accept=False,
                    command_id="declined-basim",
                    expected_revision=db.load("w").revision)
        clock.advance("w", seconds=900, command_id="wait-global",
                      expected_revision=db.load("w").revision)
        state = db.load("w")
        assert choose_assistance_intent(state, "nora", "request",
                                        scarcity_enabled=False).fields["provider"] == "basim"
        intent = choose_assistance_intent(state, "nora", "request",
                                          scarcity_enabled=True)
        assert intent is not None and intent.fields["provider"] == "zara"
        before_sum = sum(state.resources[x]["food"] for x in
                         ("nora", "basim", "zara"))
        svc.request("w", "nora", "zara", "food",
                    intent.fields["quantity"], "ask-zara",
                    expected_revision=db.load("w").revision)
        svc.respond("w", "zara", "ask-zara", accept=True,
                    command_id="zara-promised",
                    expected_revision=db.load("w").revision)
        clock.advance("w", seconds=1, command_id="time-to-fulfil",
                      expected_revision=db.load("w").revision)
        done = svc.deliver("w", "zara", "ask-zara",
                           command_id="zara-delivers",
                           expected_revision=db.load("w").revision)
        assert done.status == "fulfilled"
        s = done.state
        assert s.resources["nora"]["food"] == 4
        assert s.resources["zara"]["food"] == 7
        assert s.resources["basim"]["food"] == 0
        assert sum(s.resources[x]["food"] for x in
                   ("nora", "basim", "zara")) == before_sum == 11
        assert s.obligations["ask-basim"]["status"] == "declined"
        assert s.obligations["ask-zara"]["status"] == "fulfilled"
        assert db.verify("w").to_dict() == s.to_dict()
