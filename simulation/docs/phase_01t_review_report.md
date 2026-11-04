# Phase 01-T — Engineering review before formal closure

**Status:** IMPLEMENTATION REGRESSIONS PASS; **FORMAL CLOSURE PENDING** separate independent adversarial sign-off. This report is not a closure approval.
**Repository/branch:** [Carlos-RPG](https://github.com/daboolgame123-creator/Carlos-RPG/tree/simulation-engine-phase-01t), `simulation-engine-phase-01t`.
**Baseline:** closed Phase 01-S `c35245d1904e7a6d779cafa92cbf556618247f38`, Schema 13 / Rules 17, 481 passing tests.
**Current reviewed code:** `02dd03d75cac543eb4286161e945d221fcade90d`, Schema 13 / Rules 18. This documentation commit will have its own CI run.
**Scope:** Food knowledge in per-NPC beliefs, verifiable direct observation, non-omniscient hearsay, deterministic sharing and replay; no 01-U navigation-to-known-food behavior.

## 1. Inspected requirements and implementation

- Read `ROADMAP.md`, `DEVELOPMENT_PROTOCOL.md`, `phase_01t_design.md`, `SAVE_COMPATIBILITY_POLICY.md`, and the Phase 01-S closure report.
- Compared the 01-T branch to the closed 01-S commit. Changes cover `domain.py` (Rules 18), new `knowledge.py`, `npc.py`, `living_world.py`, explicit `movement.py` observation, tests and CI. Original Carlos story files, main, and 01-U are untouched.
- Retained four-field claim contract, event-reducer provenance validation, fact-time `observed_at` separate from delivery `received_at`, opt-in knowledge flag, no remote resource reads in the sender's sharing policy, and use of `delivery_history` on the receiving NPC.
- A food claim is a belief, not a resource ledger update; a direct observation checks site, time and initialized actual stock. Hearsay does not bypass this verification or get upgraded to world truth.

## 2. Diagnosed CI failures (verified, not guessed)

| Commit/run | Evidence and root cause | Disposition |
|---|---|---|
| `0d5b24f` / [41913842445](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/41913842445) | Both Python jobs passed 530 unit tests but the 13/17 compatibility CI fixture failed with `InvalidEvent: NPC setup requires trusted bootstrap`. It also fabricated a 13/17 DB by rewriting version columns in a new-runtime DB, contrary to the approved test contract. | Replaced with a genuine 01-S binary checkout creating a 13/17 SQLite DB; verifies old DB before the rejection, then checks rows/events/snapshots unchanged. |
| `f2630a9` / [41916511877](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/41916511877) | CI passed on 3.10 and 3.13 after the genuine old-world compatibility fix (530 tests). | Verified. |
| `e187dde` / [41917042045](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/41917042045) | One original unit test inserted a prior delivery ID in the **sender's** delivery_history, although actual delivery events record IDs in the **recipient's** history. After correcting the production code this invalid fixture asserted the wrong contract. | Fixture corrected; production rule preserved. |
| `65c6c4a` / [41917217353](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/41917217353) | Both Python versions passed **537/537** tests, scenario smoke tests and old-world compatibility/parity checks. | PASS for these code regressions; not independent closure. |

## 3. Proven behavior defects corrected

1. **Forged fact age:** A `method=observation` food claim previously accepted `observed_at < current time`, while checking only current stock, allowing false historical provenance. Now requires `observed_at == state.time`. New reducer rejection/rollback probe.
2. **Nonexistent food site:** A food hearsay key for a nonexistent location could enter beliefs. Site existence is now checked for all food claims. New rollback probe.
3. **Negative observations not shared:** The sharing selector iterated only positive `known_food_sites`; `food:empty` never propagated. It now iterates valid food beliefs, including empty, without inspecting remote resource stock.
4. **Cooldown owner/error:** Sharing checked the sender's delivery history, which is not where the event reducer records deliveries. It now checks recipient history and implements the per-sender/recipient/site 600-second rate limit.
5. **One message per pair per tick:** Multiple known food sites could create multiple same-tick deliveries to the same recipient; now bounded to one pair delivery per tick.
6. **Autonomous sharing starved:** The coordinator started all idle NPC actions before attempting the sharing pass, so newly busy NPCs had no opportunity to speak. Moved the pass before actions; knowledge does not change `next_decision_at` or foraging decisions.
7. **Explicit observation gap:** `NPCMovementService.observe` recorded occupants but omitted food-memory events. New opt-in `knowledge_enabled` keeps old behavior by default and atomically emits the observation, food delivery and acknowledgement.

These repairs are limited to 01-T behavior. No new resource generation, remote omniscient planner read, world-clock activity, schema migration, or 01-U route selection was introduced.

## 3a. Adversarial review: recipient-private knowledge leak (follow-up)

**Finding AR-03 — blocker, repaired on 01-T branch:** The autonomous sender's `choose_food_sharing` was consulting `recipient["beliefs"]` and running `should_adopt` before deciding whether to speak. This reveals the recipient's unspoken knowledge to the sender's policy, violating the no-omniscience invariant.

**Remedy:** autonomous sharing now depends on sender-owned beliefs, physical co-location/availability and the sender-to-recipient communication history for cooldowns. It does **not** inspect the recipient's private belief state. The recipient's reducer independently calls `should_adopt` on acknowledgement; delivery is consumed even when the belief is not replaced. Existing reducer/adversarial acknowledgement tests remain intact. Added a regression that changes only the recipient's private belief state and asserts byte-equal sender-generated delivery+ack events.

This correction does not allow the sender to alter another NPC's thoughts or state directly; all changes still require committed domain events.

## 3b. Final 01-T code regression checkpoint

- Code commit: [`02dd03d`](https://github.com/daboolgame123-creator/Carlos-RPG/commit/02dd03d75cac543eb4286161e945d221fcade90d).
- CI: [41919258093](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/41919258093), **success** on both Python 3.10 and Python 3.13 with **537/537 passed per interpreter**, including the new recipient-private-belief noninterference regression.
- The 01-T branch is a strict descendant of the approved 01-S baseline; all changes remain limited to `simulation/` and its CI workflow. No `main` changes, story-file edits, migrations, or 01-U implementation.
- This was a critical, adversarial review **conducted by the implementing assistant**, not a separate reviewer. The protocol's independent-approval gate is still open.

## 4. Evidence and remaining gate

- Last code regression: **537 passed on Python 3.10 and 537 passed on Python 3.13**, CI [41919258093](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/41919258093), code commit `02dd03d`.
- Coverage includes save/reopen, snapshot and event replay; reject incompatible 12/16 and genuine 13/17 worlds without rewriting; flag-off parity, direct-observation checks, hearsay contradiction handling, food exhaustion, autonomous sharing bounds and OBS-2 decision timing.
- Testing is necessary but insufficient: perform a **separate independent read-only adversarial review of the latest documentation/code HEAD**, including the newly changed emission order, one-pair-per-tick strategy, fact-time/source bounds, historical compatibility, and rollback under event-budget pressure.
- **P0 save/restore guarantee remains open**. No production migration, durable-world certification, or story import is claimed.
- Keep `main` and original story records unchanged. Do **not** start 01-U. Update ROADMAP to *closed* only after separate approval and last-commit CI success.

**Verdict:** Ready to request final independent review; **01-T remains OPEN**.
