# Phase 01-S — Internal adversarial review and correction report

**Date:** 2026-11-04  
**Reviewed branch:** `simulation-engine-phase-01s` based on `simulation-engine-phase-01r`.  
**Reviewer type:** implementing assistant's critical follow-up, **NOT a separate independent reviewer**.  
**Disposition:** both reproduced defects corrected; 481/481 tests pass per Python version; separate reviewer sign-off still required before formally closing the phase.

## Baseline and evidence

- Pre-review version: `565c363194a99a0b99ae0abc92d0f1306163a8ea`, 472/472 tests. Core new mechanics: foraging decision, 120-second action, conservation and audited failure history.
- Latest code regression-checked: `7471938aae09197bcea1ab27dd9290b528ad5294`.
- Passing CI on latest **reviewed code before documentation update:** [run 41855607762](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/41855607762): Python 3.10 **481/481**, Python 3.13 **481/481**. The final documentation/handoff commit must be retested.
- The suite includes authentic 12/16 SQLite old-world refusal, replay/snapshot checks, integration, rollback and legacy semantic/event digest parity against 01-R.

## Finding AR-01 — HIGH — Navigation preempted urgent local forage

**Path:** `simulation/src/carlos_sim/living_world.py`, decision/orchestration loop.

**Reproduction:** Introduce a known route `grove↔square` alongside 2 visible food units at the grove. Hungry NPC has hunger 70, owned food 0. Run `LivingWorldEngine(navigation_enabled=True, foraging_enabled=True).advance(...)`. Previously the coordinator surveyed and started optional navigation **before** calling `choose_action`, and the NPC left available local food. Even a preselected route target hid the forage candidate.

**Failing tests evidence:** run [41854606709](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/41854606709), two tests failed on Python 3.10 and 3.13; prior 472 still passed.

**Repair:** commit `a7641df21231e31edc9af2e0382afa714cf98150`: call the pure local forage eligibility check before the optional travel branch, and skip travel only if a valid local hunger-driven forage opportunity exists. Preserve existing pending same-tick manual decisions and ordinary movement when no such opportunity exists.

**Regression cases:** ordinary autonomous route, explicit target, travel continues if local forage impossible, 120-second completion while navigation is enabled.

**Status:** corrected; all tests green.

## Finding AR-02 — MEDIUM — High-confidence danger belief ignored

**Path:** `simulation/src/carlos_sim/foraging.py`, `choose_local_foraging`.

**Reproduction:** Have Basim deliver `danger` warning about a predator to Adel only, confidence 95. Adel's `NPCDecisionRecorded` policy continued to choose `forage` despite the newly known risk, whereas older `_score_choice` already incorporates danger knowledge.

**Failing test evidence:** run [41855205489](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/41855205489), one failure on Python 3.13 before patch (also executed on 3.10).

**Repair:** commit `1f5685bdbee7203f45fb68cb77fc4e5a3c631cc0`. The foraging predicate reads **that NPC's own** `danger` belief only; suppresses forage at `confidence >=80`. Lower-confidence reports allow a choice. The deterministic, recomputed reason includes `belief_danger`. No other character learns the report without delivery.

**Regression cases:** action selection and physical action integration, receiver-only effect, boundary values 0/79/80/100, DB event replay.

**Status:** corrected; all tests green. This threshold is an explicit prototype policy, not a general combat risk model.

## Additional review verification

- **Causal action:** `NPCDecisionRecorded(action=forage)` requires trusted planner/action capability and exact validated `policy=local-forage-v1`; `NPCActionStarted` requires scheduled event and recent decision.
- **Finite stock:** `ScheduledEventFired` resolves both success and depletion, with one persistent attempt per completed action. No resource minting, negative balances or double completion permitted.
- **Replay and rollback:** same for standalone TimeEngine/LivingWorld, paused session rejection, logical-time split parity, event-cap rollback, immutable snapshot/full replay.
- **Knowledge:** local natural deposit only; no remote inventory scan. The "deposit visibly available" assumption is intentional and is not a complete perception/knowledge API yet.
- **Versioning:** Schema 13 / Rules 17, old 12/16 worlds rejected fail-closed without mutation, no migration; P0 remains **open**.

## Residual issues / handoff

- **NEEDS INDEPENDENT SIGN-OFF:** distinct OpenCode reviewer should inspect source and tests without relying on this report, reproduce critical safeguards, and record verdict `APPROVED` or `BLOCKED`. If blocked, fix, rerun CI and revise the report. Do not claim this audit meets the independent review policy.
- **Deferred design:** remote food memory/rumors (01-T), choice of travel to a *known* food source (01-U), reaction to repeated empty forages and fairness (01-V), more nuanced danger/character personality (02-E), production (02-B), long-lived save P0.
- **No changes permitted without separate user authorization:** `main` merge, rewriting original Carlos story, importing old long-lived saves, executing untested migrations or exposing public APIs.

**Review recommendation:** code is ready for independent audit after corrections; no currently known blocker from the tests, but formal stage closure remains conditional on separate reviewer approval.
