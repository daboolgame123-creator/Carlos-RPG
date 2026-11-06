# 03-A7c — visible injury observation contract, first implementation slice

Branch: `simulation-engine-phase-03a-visible-symptoms`
Base: `a12b8aae3f66580657cfc54c4f43a0f08a6e3f46`
Parent 03-A: **OPEN**. Task 03-A7c: **IN_PROGRESS**, not closed.

## Analysis and design
Injury records contain private severity, status and onset but do not encode
observable symptoms. Co-location alone must not disclose an injury. Consequently
the first slice implements a **read-only candidate interpreter**, not a persistent
observation or automatic disclosure mechanism.

- Visible signal vocabulary: limping, visible_bleeding, difficulty_moving, collapse.
- Inference is uncertain; no diagnosis, severity, injury ID, onset or cause.
- Both characters must exist, be present and share a location at the logical time.
- Candidate never mutates state, emits events, records knowledge, or authorizes a
  diagnosis. An arbitrary caller can supply a signal, so the candidate MUST NEVER
  be represented as a witnessed fact or sent to a language model as verified truth.
- Neither private injury data nor another NPC's beliefs are consulted.

## Character acceptance scenarios
1. Basim and injured Nora in bakery: supplied limping produces only
   `possible_mobility_problem`; no injury ID/severity disclosed.
2. Omar in square: remote observation rejected.
3. Nora without an injury record: caller-supplied signal remains a mere candidate,
   proving that this function cannot itself establish an injury.
4. Invalid signal, actor, self-observation and time rejected.
5. SQLite snapshot, reopen and event replay unchanged.

## Remaining before closing 03-A7c
A trusted runtime *symptom production* rule linked to observable behavior,
an authorized event pair and stored provenance; protection from forged
direct observations at append/replay boundaries; knowledge expiry/correction,
message propagation rules if included in scope; dual-Python complete CI on
the final code SHA. None of these are asserted complete in this slice.

No schema/rules bump: the new helper is not wired into accepted events or world
decisions. This is not a production or external-review approval.
