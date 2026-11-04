# Phase 01-P — Full-world projection optimization and independent review

## What changed

Before Phase 01-P, each `apply_event` call constructed a detached world-state
dictionary, applied an event, ran all `WorldState.from_dict` validators and
then serialized/deserialized the entire world again solely to normalize
already JSON-native internal state. This made the complete living-world
simulation expensive as characters/events increased.

The new private `WorldState._from_internal_projection` path shares the
**same full validators** with public `WorldState.from_dict`, but skips the
additional whole-world JSON roundtrip *only* for a domain-reducer result
assembled from `WorldState.to_dict` and a strictly serialized/validated
`DomainEvent`. External snapshots continue through the complete portable
JSON normalization. Untrusted inputs must never use the private path.
Frozen nested containers and detached `to_dict` views remain intact.

The recursive `_freeze` operation now preserves **canonical sorted key
iteration**, matching the old JSON normalization even when a domain event
inserts keys out of order. Hash canonicalization, per-event causality, event
count, SQLite append/replay checks, capability flags, optimistic concurrency,
full rollback and snapshot integrity are unchanged.

There is **no rules or schema change**: Schema 11 / Rules 15. Experimental
databases of those versions remain compatible; no migration or story import.

## Independently verified GitHub Actions

- Final integration run:
  https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/41831460953
- Python 3.10: **419/419 passed**; Python 3.13: **419/419 passed**.
- Python compile step passed, and the same cross-version event-ledger and
  final-state digest fixture matched reviewed Phase 01-O at **10, 25 and
  50 NPCs** on both Python versions.
- New `tests/test_projection_p.py` tests enforce no extra full-world
  JSON normalization on the normalized reducer path, public invalid input
  rejection, continued unrelated world invariants, deep immutability,
  failed-event state isolation, and canonical map key order.
- Existing 01-O full replay SQL benchmark continues to run in the same CI.
- Benchmarks and semantic parity ran on separate code imports against the
  reviewed Phase 01-O branch. No tests were skipped to improve timings.

## Full-engine 60-second simulated advance

The same `bench_living_world.py` produced the same exact event counts in
both revisions. One sample per scenario and runtime, on shared GitHub
runners; setup time excluded. These are NOT production speed guarantees.

| NPCs | Advance events | Python 3.13 01-O | Python 3.13 01-P | Python 3.10 01-O | Python 3.10 01-P |
|---:|---:|---:|---:|---:|---:|
| 10 | 31 | 0.0960 s | 0.0598 s | 0.0944 s | 0.0692 s |
| 25 | 76 | 0.3928 s | 0.2487 s | 0.4232 s | 0.2860 s |
| 50 | 151 | 1.3615 s | 0.8172 s | 1.4908 s | 0.9753 s |
| 100 | 301 | 5.1005 s | 3.0082 s | 5.4902 s | 3.5862 s |
| 150 | 451 | 11.2778 s | 6.5542 s | 12.1070 s | 7.7901 s |

At 150 NPCs, 01-P is about **1.72× faster** on Python 3.13 and **1.55×**
on Python 3.10 in these single samples, with **451 events** in each. This
fixture is a deliberately simple work-oriented village; it does not measure
real narrative systems, varied relationships, combat, politics, years of
world history or 1,000 complete NPCs. No setup time is included.

## Independent review and next phase

The initial new test incorrectly assumed that direct `WorldState`
construction already had the fast normalized projection marker; the test
was corrected to begin with a public checked `from_dict` state. Separately,
review found a possible change in internal mapping iteration order. Sorted
freeze semantics plus a new regression restore parity with the previous
canonical JSON behavior. The **final** 419-test GitHub CI run passed.

The full-world immutable copy and all-domain validation still occur for
each event, and the high-level planner plus SQLite command commit each
project the event batch. That cost remains nonlinear and requires a
separately scoped optimization with stronger invariants; it is not safe
to skip validator/replay steps on the basis of these benchmarks.

**Verdict:** Phase 01-P independently verified and closed within the
isolated test-world scope. `main` and Carlos story files were untouched.
