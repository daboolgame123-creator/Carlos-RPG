# Phase 01-S — Hunger-driven, finite autonomous local forage

**Status:** **closed — implemented, tested, and independently reviewed; verdict APPROVED (2026-11-04)** (methodology, test evidence and observations OBS-1…OBS-5 in [Independent review and closure](#independent-review-and-closure--2026-11-04)). The review gate requested in [phase_01s_review_request.md](phase_01s_review_request.md) is cleared; Phase 01-T may start from this reviewed commit.

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

Independent review was requested on provenance authorization, event replay, stale/unknown inventory, physical outcomes on both clocks, fail-safe rules-version mismatch and whether deterministic competition ordering is an acceptable Stage 01-S simplification. That review has now been performed and **APPROVED** this change (see the closure section below); no blocking issues were found.

**Out of scope:** knowledge of distant food, rumor memory, path planning, production/growth, skill effects, combat, fair or random resource allocation, importing Carlos story. This report and ROADMAP.md now close the stage; 01-T is next.

## Internal adversarial review (author-review, not independent sign-off) — 2026-11-04

Evidence: [phase_01s_internal_review.md](phase_01s_internal_review.md). The original implementer performed this audit; it **does not** satisfy the separate independent reviewer gate in DEVELOPMENT_PROTOCOL.md. It does prove that the vulnerabilities below were detected through new failing regression tests, repaired and re-tested.

- **AR-01 HIGH — Nav overrides survival intent.** With both `navigation_enabled=True` and `foraging_enabled=True`, hungry NPCs could start an automatic trip even with visible natural food at the current site. Reproduced by two failing tests in run `41854606709`. Fixed in `living_world.py` by evaluating the pure local forage predicate before optional travel. Added four integration checks covering automatic routes, explicit target, fallback navigation without local food, and scheduled completion while navigation is enabled.
- **AR-02 MEDIUM — Trusted danger information ignored.** A 95-confidence danger report delivered solely to one NPC did not affect its forage choice; this broke the intended NPC-specific knowledge behavior. Reproduced by failing run `41855205489`. Fixed `foraging.py` to suppress local forage when that NPC's own `danger` belief confidence >=80. Decision reason now includes `belief_danger`; low-confidence warnings preserve forage eligibility. Added one integration and four boundary tests.
- **Final tested code before this report:** `7471938aae09197bcea1ab27dd9290b528ad5294`; run [41855607762](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/41855607762) completed **481/481 tests on Python 3.10 and Python 3.13**, with old Phase 01-R semantic parity and real old-database rejection checks.
- **No new Schema/Rules bump beyond 13/17** within this unclosed experimental phase; the 01-S event decision reason changed before a supported long-lived save contract was published. 01-R→01-S still has no approved migration.
- **Remaining design debts:** local food visibility remains a synthetic world assumption; no remote food-memory yet (01-T); deterministic competition order can favor fixed IDs (01-V); no long-lived-world P0 clearance.

**Review verdict (internal, author):** the two reproduced functional defects are repaired, and all **known CI regressions are cleared**. At the time of writing, approval by a *separate reviewer* remained **PENDING**, so the phase was not yet formally closed. That independent review has since been completed with verdict **APPROVED** — see the next section, which supersedes the pending status above.

## Independent review and closure — 2026-11-04

**Verdict: APPROVED.** A separate reviewer (OpenCode session, distinct from the original implementer) performed a read-only adversarial audit of the final reviewed commit `785c3499e91cef307e4e6861bec262267816b5fe` on `simulation-engine-phase-01s`. No blocking issues were found; five non-blocking observations (OBS-1…OBS-5) are recorded below with their target phases. No source file was modified during the review; the only changes made afterwards are documentation closure edits in this file, ROADMAP.md, decisions.md and ROADMAP_CHANGELOG.md.

**Methodology:**
1. **Baseline integrity** — verified the working snapshot is content-identical to remote HEAD `785c349` (all `simulation/` files and story files, modulo CRLF/LF line endings) via a fresh clone in a temp directory; `main` and original story files untouched.
2. **Diff inspection** — line-by-line read of the full `01r..01s` diff (`foraging.py`, `living_world.py`, `npc.py`, `actions.py`, `domain.py`, `store.py`, `time_engine.py`, `movement.py`, `gathering.py`, tests, CI workflow, docs).
3. **Local test run** — full suite **481/481 passed** (Python 3.12.14, 122 s); `compileall src tests scenarios` exit 0; `demo_foraging.py` reproduced exactly (7 NPCs, 51 advance events, 4 attempts = 2 collected + 2 depleted, `wild_food` 2→0, replay-equal).
4. **Independent probe suite** — 11 adversarial probes written from the review checklist *outside* the repository (not the shipped tests), all **PASS**: P1 forged completion while session closed, P2 out-of-order signal firing, P3 double firing, P4 action/decision mismatch, P5 decision outside session, P6 forage-vs-navigation cooldown behavior (reproduced OBS-2), P7 forged attempt history (chain forgery accepted by consistency-only `from_dict`, detected by `verify()`: "snapshot and full replay disagree"; forged `quantity=2` rejected by conservation), P8 forged site in decision reason rejected by deterministic re-derivation, P9 consumed schedule cannot re-fire.
5. **Genuine old-world rejection** — a real Phase 01-R SQLite world was created *with 01-R code* (worktree at `0770498`), then loaded with 01-S code: rejected with `UnsupportedVersion`, rows unchanged `(schema=12, rules=16, revision=1)`, 1 event and 1 snapshot intact — fail-closed, no rewrite.
6. **Cross-version parity** — `bench_event_parity --counts 7` run under both 01-R and 01-S code: `events_digest` identical (`e4414d12…`) and `legacy_semantic_digest` identical (`7d2be0d6…`); only the full `state_digest` differs (intentional: version fields + new `foraging_attempts` collection).
7. **CI** — GitHub Actions run `41856382834` on commit `785c349`: **test (3.10) = success** and **test (3.13) = success** (the single annotation is a GitHub runner notice only).

**Observations (non-blocking) and target phases:**

| ID | Severity | Finding | Target |
|---|---|---|---|
| OBS-1 | Low — save integrity | `WorldState.from_dict` accepts an internally consistent but historically forged `foraging_attempts` history (it does not cross-validate attempts against resource conservation or the event chain); provenance is guaranteed by the event log plus `verify()`, which detected a hash-consistent tampered snapshot. Same pre-existing property for all resource ledgers, not specific to 01-S. | **P0 save gate** (before first long-lived world, ROADMAP §15) and **05-D** (external snapshot import): document `from_dict` as consistency-only and add cross-validation at import boundaries. |
| OBS-2 | Low — design | With `foraging_enabled=True` + `navigation_enabled=True`, a hungry NPC inside the 60 s decision cooldown defers optional travel *and* cannot start a forage until the cooldown expires (reproduced: at t=30 neither travel nor action; forage starts at t=60; flag-off travels immediately). Consistent with AR-01 intent, but the idle gap deserves a regression test and explicit handling. | **01-U** (navigation-to-known-source) and considered now in **01-T** design: memory/navigation interaction must not strand a hungry NPC; add regression test. |
| OBS-3 | Known | Deterministic competition ordering is lexicographic: fixed IDs (adel/basim) always win the site, (nora/salma) always fail. | **01-V** fairness/competition policy (already deferred there). |
| OBS-4 | Doc note | A manual `forage` decision recorded while the flag was on can still execute through `LivingWorldEngine` after the flag is turned off (the pending decision is not re-checked against the flag). Opt-in happens at decision time; disabled-mode parity is preserved and digests prove it. | Documented here; optional hardening in **01-W** (player-gate phase). |
| OBS-5 | Optional coverage | No explicit test asserts decision-site == completion-site under navigation (deterministically enforced by `movement.py`: an NPC busy with an action cannot start travel). | Optional regression test in **01-U**. |

**Closure actions:** `phase_01s_report.md` (this file), `ROADMAP.md` (01-S → «مكتملة ومختبرة ومراجعة»), `decisions.md` and `ROADMAP_CHANGELOG.md` updated; committed and pushed **only** to `simulation-engine-phase-01s`; CI re-verified on the closure commit. **01-S is closed.** Next: branch `simulation-engine-phase-01t` from this approved commit, design review of 01-T (knowledge of food-source locations) **before** any 01-T coding.
