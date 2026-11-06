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
