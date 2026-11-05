# Phase 01-T — Response to independent OpenCode BLOCKED findings

**Verdict of original review:** BLOCKED at `d2a397bde95d2596592818f348d68b030f78f48a` (01-T). This document records an author-made remediation, **not** an independent re-review or approval.
**Remediation branch:** `simulation-engine-phase-01t-review-fix`, forked from original reviewed SHA. Last green code checkpoint `eda0419c8eb575713f276a89db2f52956a1a4707`.
**Evidence:** [CI 42007806505](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42007806505): **548/548 passing each** on Python 3.10 and Python 3.13 (4 added tests over the 544 predecessor baseline), compileall plus frozen 01-S/01-R save compatibility checks and legacy flag-off parity.

## T-1 (P1) — initial BLOCKED, fix tested, independent re-review pending
- Previously: 25 NPCs each relayed the same news during the same tick: >1000 events and permanent fail-closed availability stall. A 7-NPC suite missed the 25-NPC documented integration upper bound.
- Fixed without changing the event contract: the coordinator now **computes all sharing proposals against one frozen pre-round state**, before appending any delivery. `choose_food_sharing_round` selects **at most one delivery per (recipient, site)**; first eligible sender by lexical NPC ID wins. No sender reads private receiver belief. Each event is still a real paired `NPCInformationDelivered` / `NPCBeliefReceived` committed atomically.
- New test initializes 25 NPCs in one site with either ONE first-hand observer or ALL 25 observers, then checks exactly 24 or 25 shares, no duplicate recipient/site, command event_count <1000, progression and `verify()` replay.

## T-2 (P2) — 5000-digit historical delivery ID now safely skipped
- `choose_food_sharing` validates the numeric suffix has ASCII decimal digits, length <=19, and a signed 64-bit value **before calling `int()`**. Old noncanonical history IDs are not treated as valid cooldown ticks and cannot crash the planner.
- New integrated test adds a real reducer-authorized 5000-digit delivery ID to a recipient's durable history, then runs a sharing round and a living-world advance; these complete with a verified state.

## T-3 (policy) — explicit decision: no zero-time hearsay relay
- A hearsay belief whose `received_at` equals the current simulation tick **cannot be forwarded**; a directly witnessed observation may be sent immediately. A later tick permits ordinary propagation, subject to pair/site throttles and claim ageing. No remote truth testing or secret receiver belief scanning is added.
- The complete pre-round snapshot and per-recipient/site dedup prevent re-amplification even when multiple speakers already knew the same site.

## Remaining work and dependency gate
- The reviewed original 01-T and downstream 01-U/01-V remain **BLOCKED by inherited dependency** until an independent reviewer sees the changed code/test SHA and returns APPROVED. No equivalent approval is inferred from green CI.
- 01-U must inherit the fix and resolve reviewer U-3's exploration-vs-cooldown policy explicitly; 01-V must inherit corrected 01-U. Check all frozen-version CI parity, replay, 25-NPC and forged-ID probes for each downstream branch.
- P0 backup/restore remains OPEN; no long-lived world, auto migration, `main` change or story import is authorized.
