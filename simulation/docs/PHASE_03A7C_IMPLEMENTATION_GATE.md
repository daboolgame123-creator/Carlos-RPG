# 03-A7c — Implementation gate and observation integrity (2026-11-07)

Branch: `simulation-engine-phase-03a7c-observation-contract`
Parent branch: `simulation-engine-phase-03a-treatment-integrity`
Parent phase: **03-A OPEN**.

## Analysis before implementation

Owner instruction "تابع" after the limited-observation recommendation is treated
as approval of **the principle**: only explicit, local, qualitative visible
signs, with historical provenance; no diagnosis, numeric severity or automatic
sharing. It does not authorize inventing a visual symptom from a severity
integer alone.

Existing `injuries` tracks injury ID, subject, severity, status, onset and
last_changed. These fields **do not describe a visibly observable symptom**.
A severe internal injury is not necessarily a visible limp. Mapping
`severity >= 20` to `visible_mobility_difficulty` would falsely claim
evidence the engine does not possess.

## Safe execution split

- **03-A7c-guard**: `CHAT_EXECUTABLE / READY_FOR_VERIFICATION`.
  Add negative integration checks that peer NPCs do not automatically learn
  another NPC's injury from a bootstrap ledger entry, and that reopening
  SQLite preserves the isolation. This is a security baseline, **not** feature
  implementation. Run exact-SHA full CI on Python 3.10 and 3.13.
- **03-A7c-source**: `BLOCKED_BY_DEPENDENCY / BLOCKED` until the engine
  has a trusted, deterministically verifiable source of an *actual visible
  symptom*, e.g. a recorded limp/mobility impairment due to a validated
  physical action result. Need separately bounded symptom taxonomy and
  projection from that event. Never generate a symptom solely from numeric
  injury severity or caller-supplied prose.
- **03-A7c-observe**: `BLOCKED_BY_DEPENDENCY / BLOCKED` on source.
  Trusted, explicit local observation must check observer and subject
  distinct configured NPCs, both actually present and available, local
  site and logical time, source revision/provenance; emit a receiver-scoped
  event/claim only. No automatic disclosure per tick, message propagation,
  HP changes, resource deduction or treatment.
- **03-A7c-replay**: `BLOCKED_BY_DEPENDENCY / BLOCKED` on observe.
  Negative tests for forged sign/source/location/time/actor, duplicate IDs,
  travel/busy state, invisible injuries, stale revision and partial
  transactions; positive tests with Nora, Basim, Salma, Adel and Huda,
  replay/snapshots/reopening, full parity and dual-Python CI.

## Compatibility and interfaces

Keep 03-A8a and existing event format unchanged until a verified symptom
source exists. A new persisted event or changed projection requires explicit
Schema/Rules version analysis; historic digests must not be rewritten.
NPC memory should contain only target ID, qualitative sign code, where/when
observed and trustworthy origin, with historical semantics. The injury ID,
severity, diagnosis, onset and treatment details stay private. The player
gateway must not receive that private record.

No 03-A7c closure, production readiness or independent audit is claimed
by the guard tests. Do not merge to `main` or the 04-A institution branch.


## Verified-activity observation slice (implementation candidate)

Commit `67af6c2a` introduces the pure `observed_resting_activity` projector.
It recognizes only the actual ongoing `rest` action previously accepted by
the event-sourced action reducer and a locally recorded current-tick sighting.
The result is `visible_resting`, **not a medical symptom or injury inference**.
An uninjured exhausted NPC and an injured NPC must project the same sign,
while the private injury ledger stays inaccessible in the output.

The guard does not persist any new NPC health belief, automatic disclosure or
new world event. It changes no Schema/Rules version and leaves original
`witnessed_peer_here` semantics intact. The old event-backed observation
is still explicitly scoped to the present logical time. Tests also enforce
post-snapshot SQLite reopening and invalidate the sign after time passes.

**Important:** a running rest action is only one deterministic visible
activity. It does not prove a limp, collapse, diagnosis, health condition,
cause or medical necessity. The broader 03-A7c symptom source and receiver-
scoped knowledge events remain open pending a separately justified physical
sign event. Never silently reinterpret `visible_resting` as an injury code.


## 03-A7c local scene projection — 2026-11-07

A pure, read-only `observed_local_activities(state, observer_id)` function
was added to `injury_observation.py` on code commit `461d0285`.
It returns only supported `visible_resting` entries from real ongoing
rest actions for peers listed in that observer's *same-tick* recorded
`NPCObserved` snapshot. It does not synthesize a new event or belief,
peek at the injury ledger, classify health, or transmit a rumor.

Seven-NPC test scenarios at `test_injury_local_activity_scene_03a7c.py`
prove Basim and Salma must individually observe Nora; Adel, Huda and
other non-observers learn nothing, Omar's distant location stays isolated,
and replay/snapshot/SQLite reopening preserve the factual scene projection.
The current scene loses its availability after advancing logical time.
A different NPC interpretation of a visible activity is future work,
dependent on its own evidential knowledge. Do not present a speculative
interpretation as medical fact or already persisted belief.

**Status:** ready for exact final-SHA Python 3.10 / 3.13 CI verification;
the symptom-specific source and observer-scoped historical health knowledge
remain blocked. Parent 03-A remains OPEN; P0 unchanged.


## 03-A7c conservative inference baseline — 2026-11-07

A pure `explain_visible_rest` helper returns the same explicitly
`cause_unknown` interpretation for healthy and injured actors performing
the same validated rest action. It **does not establish** a subjective
belief, health diagnosis, memory claim or fact about what motivated the
rest. Its evidence is only the observer-scoped current-tick sighting and
the running activity; a missing, distant or stale sighting returns no result.

Tests in `test_injury_observation_interpretation_03a7c.py` cover
healthy/ill indistinguishability, no hidden injury ID/severity leakage,
old sightings, invalid actors, and a replay check. The code introduces
no new WorldState fields, event types or version changes.

Real per-character *differences* in interpretation must depend on
independently obtained knowledge, a separately accepted source and
specific deterministic policy. Do not fabricate the NPC's memories or
translate ordinary resting into visible physical impairment.

**Provisional state**: `VERIFICATION_PENDING` until dual-Python CI
passes on the final SHA. The observer-specific durable health memory and
physical symptom provenance remain unimplemented; 03-A stays OPEN.


## 03-A7c observer-owned *historical activity* memory — 2026-11-07

Implementation is now present as an **opt-in behavioral evidence slice**,
not the physical injury-symptom feature. With
`NPCMovementService.observe(..., activity_enabled=True)` and an active
session, the command atomically appends the existing `NPCObserved` event
then a verified `NPCInformationDelivered` and
`NPCBeliefReceived` pair for each physically present resting peer.
The namespaced `visible-rest:<subject>:<tick>` claim is stored only in
that observer's personal NPC beliefs, with `observation:<site>` provenance.
The trusted reducer re-verifies same-tick local sighting, ongoing true
rest action, source text, identity, location, confidence and bounded
memory capacity. Passive observations and inactive sessions do not
produce the memory. The existing schema and rules versions are unchanged;
existing NPC observation invocations remain opt-out by default.

`recall_rest_activity` returns only the caller-named observer's
persisted evidence: a dated `visible_resting` fact with
`interpretation=cause_unknown`. History stays historical after
action completion. It contains **no injury ID, diagnosis, severity,
cause or treatment**; healthy exhausted and injured resting Nora create
indistinguishable observation evidence.

Verification acceptance: 2-NPC healthy/injured parity; adversarial forged
actor/source/site/sign/timestamp/recipient/confidence rejection and
transaction rollback; seven-person village (Nora, Basim, Salma, Adel,
Huda, Omar, Layla); snapshot, cross-process SQLite reopening, deterministic
replay, dual Python 3.10/3.13 CI on exact SHA. At writing,
these tests are added but **CI verification is pending**.

Separate 03-A7c *medical signs* remains blocked on an actual physical
symptom source. Ordinary visible rest cannot legally be relabeled limp,
collapse or confirmed health evidence, and must not spontaneously
trigger help or health rumors.


## Verification ledger — 2026-11-07

The initial opt-in observer-owned historical visible-rest memory slice and its
seven-NPC + persistence + forged-source regression passed the full GitHub
Actions simulation suite at exact SHA `91e6004e841dda54a18b8f517aa6bcf880933fc1`
(run `42305932829`, Python 3.10 and Python 3.13 both success).
This is a **technically tested behavioral-memory slice**, not completion of
03-A7c medical observation.

Subsequent integrity follow-up: repeated same-tick explicit sightings,
multi-tick historical events, acknowledgment without a matching delivery and
lack of automatic sharing are regression-tested at `ccb09cc0`. The activity
draft producer now skips a key already present in the observer's pending inbox,
so repeat observation does not create a competing delivery (`c82e60cf`).
The new exact pending-delivery/ack test is at `90804577`. Those latest
changes remain **VERIFICATION_PENDING until their full SHA dual-Python CI
has completed successfully**.

Existing events, version numbers and world state remain unchanged by the
follow-up. This test slice MUST NOT grant a medical source, infer motive or
create autonomous social sharing.


## Memory-capacity nonblocking observation — 2026-11-07

The resting-memory projector maintains a bounded `MAX_REST_MEMORIES=64`
per observer. Previously, when this limit was reached, a new trusted
`observe(activity_enabled=True)` could generate a delivery that the
reducer rejected, rolling back the *entire* observation. The generator now
accounts for both accepted beliefs **and pending inbox deliveries** before
drafting further memory pairs, and stops at zero remaining capacity.
The character remains able to record `NPCObserved` for the current
location even when no more resting memories fit.

The multi-tick integration regression executes 65 explicit sightings of
the same genuinely resting NPC, each at a distinct logical second,
then checks memory stays at exactly 64 without a failed 65th look.
SQL replay/verification must match; capacity overflow must not erase
prior memories, create diagnoses, or silently start a new action.
Commits: producer `61d8510a`, regression `1b7bf9af`.
**Verification pending exact SHA dual-Python CI.**


## 03-A7c observable funded care — 2026-11-07

An independent pure projector, `observed_supportive_care` (commit
`d97f39cd`), reads a *real pending, funded RecoveryStarted action*
and only presents its **external care interaction** when an available
local NPC has recorded seeing BOTH the caregiver and recipient in the
same site/tick. It deliberately hides injury IDs, severity, materials,
effectiveness and clinical diagnosis. Expired or completed treatment,
unobserved peers, missing location and unvalidated world snapshots yield
no observation. This read-only projection does NOT create a new belief,
domain event or medical sign. It is separate from the persistent
`visible-rest` behavior history.

Multi-NPC integration tests at `6f8f0813` check Adel's real care of
Nora, Basim as actual witness, Salma/Huda/Omar not learning passively,
expiration after clock time, completed treatment not being presented as
active, and unchanged replay. **Verification pending dual-Python CI**
on the exact final SHA. This remains behavioral evidence only:
a care interaction does not prove a particular wound, disease or
visible physical impairment. The separate physical symptom source is
still blocked, and 03-A remains open.
