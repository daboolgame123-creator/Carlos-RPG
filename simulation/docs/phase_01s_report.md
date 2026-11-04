# Phase 01-S — Hunger-driven, finite autonomous local forage

**Status:** implemented; internal adversarial review completed with two confirmed fixes; **separate independent reviewer sign-off pending** (see [phase_01s_review_request.md](phase_01s_review_request.md)). 01-T must not begin before review gate is cleared.

## Base and scope

Source: Phase 01-R, commit `0770498a1f257a252a82fde5ade1c43d3a791e3f`, Schema 12 / Rules 16, 445 tests. Branch `simulation-engine-phase-01s`, no `main` merge or modification of original Carlos story.

A character can now begin a **reasoned forage action** because it is hungry and can see an initialized natural food deposit at its *current site*. A deliberate `forage` action is different from the old, opportunistic `investigate` gathering. The condition checks own hunger >=65, fatigue <=75, safety <=70 and own food exactly 0; missing stock is not zero. Remote sites and other people's private inventory are never read by this policy.

## Implementation contracts

- `foraging_enabled=False` by default in the living coordinator and manual NPC decision service; when disabled, original scoring and decision event structure are preserved.
- New `NPCDecisionRecorded(action=forage)` includes `policy=local-forage-v1`. During event projection the exact deterministic score/reason is recomputed; a trusted action capability plus existing planner authorization is required.
- `NPCActionStarted(action=forage)` schedules **120 logical seconds**. Completion charges **+12 fatigue and +5 hunger**, and `ScheduledEventFired` itself resolves the inventory effect (no separate invented instant award). This works via normal `TimeEngine` and `LivingWorldEngine`, including switching the feature flag off while a foraging action is in progress.
- The authoritative completion transfers exactly one `wild_food` from the local site to NPC `food` if any remain; otherwise the completed attempt records `depleted` with zero transfer. All completed forage actions require a historical outcome.
- The immutable `WorldState.foraging_attempts` stores actor, site, logical time, success/depletion, quantity, and before/after balances. Full validators reject absent/forged records and non-conservation. Legacy `NPCFoodGathered` stays restricted to `investigate`.

## Seven-NPC integration demonstration

`PYTHONPATH=src python scenarios/test_village/demo_foraging.py`: seven characters with varied hunger, food and location; four independently start forage in one grove with **2 units**. After 120 simulated seconds: **two successes and two recorded depleted failures**, no negative or created food, and **51 advance events**. Full event replay matches the saved state. Deterministic scheduled/ID ordering is **not yet a fairness policy**, and dynamic knowledge/travel to remote sources is out of scope (01-T/U/V).

## Validation

- CI run `41852324623`: **472/472 passing tests each** on Python 3.10 and 3.13 before the extra actual-old-world compatibility CI step and documentation commit.
- **27 new tests** compared with 01-R: bounded local knowledge, critical hunger and other competing needs, opt-in/out parity, trust/policy forgery, physical duration, scarcity/failed attempts, split-time equivalence, interruption, session freeze, atomic rollback, pure determinism, manual-time resolution, mid-action toggle, mandatory historical outcomes, snapshot/full replay and eating separation.
- CI checks old **event digests** and *legacy semantic state* digests against 01-R when forage mode is off; the full-world digest differs intentionally due to version fields and the new state collection.
- A separate CI step creates an actual Phase 01-R SQLite world, including an event and snapshot, then checks new code refuses it without erasing stored rows.
- No benchmark with 150 NPCs: correctness of 7 autonomous people and resource conservation takes priority.

## Save compatibility and security

**Schema 13 / Rules 17**. Old 12/16 SQLite worlds are intentionally refused via `UnsupportedVersion`, not silently rewritten. **No audited migration, off-file verified backup/restore or P0 closure** was implemented; only disposable test worlds were used. Capability flags are trusted local internals, not HTTP AuthN/AuthZ.

## Review and remaining limitations

Independent review has **not yet** approved this change. Requested adversarial scrutiny: provenance authorization, event replay, stale/unknown inventory, physical outcomes on both clocks, fail-safe rules-version mismatch and whether deterministic competition ordering is an acceptable Stage 01-S simplification.

**Out of scope:** knowledge of distant food, rumor memory, path planning, production/growth, skill effects, combat, fair or random resource allocation, importing Carlos story. After review, update this report and ROADMAP.md to close the stage, then plan 01-T.

## Internal adversarial review (author-review, not independent sign-off) — 2026-11-04

Evidence: [phase_01s_internal_review.md](phase_01s_internal_review.md). The original implementer performed this audit; it **does not** satisfy the separate independent reviewer gate in DEVELOPMENT_PROTOCOL.md. It does prove that the vulnerabilities below were detected through new failing regression tests, repaired and re-tested.

- **AR-01 HIGH — Nav overrides survival intent.** With both `navigation_enabled=True` and `foraging_enabled=True`, hungry NPCs could start an automatic trip even with visible natural food at the current site. Reproduced by two failing tests in run `41854606709`. Fixed in `living_world.py` by evaluating the pure local forage predicate before optional travel. Added four integration checks covering automatic routes, explicit target, fallback navigation without local food, and scheduled completion while navigation is enabled.
- **AR-02 MEDIUM — Trusted danger information ignored.** A 95-confidence danger report delivered solely to one NPC did not affect its forage choice; this broke the intended NPC-specific knowledge behavior. Reproduced by failing run `41855205489`. Fixed `foraging.py` to suppress local forage when that NPC's own `danger` belief confidence >=80. Decision reason now includes `belief_danger`; low-confidence warnings preserve forage eligibility. Added one integration and four boundary tests.
- **Final tested code before this report:** `7471938aae09197bcea1ab27dd9290b528ad5294`; run [41855607762](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/41855607762) completed **481/481 tests on Python 3.10 and Python 3.13**, with old Phase 01-R semantic parity and real old-database rejection checks.
- **No new Schema/Rules bump beyond 13/17** within this unclosed experimental phase; the 01-S event decision reason changed before a supported long-lived save contract was published. 01-R→01-S still has no approved migration.
- **Remaining design debts:** local food visibility remains a synthetic world assumption; no remote food-memory yet (01-T); deterministic competition order can favor fixed IDs (01-V); no long-lived-world P0 clearance.

**Review verdict:** the two reproduced functional defects are repaired, and all **known CI regressions are cleared**. However, approval by a *separate reviewer* remains **PENDING**, so the phase is not formally closed. Next OpenCode session should perform a read-only independent audit and write an approval or actionable blocking issues **before** beginning 01-T.
