# Simulation Development Agent Rules — Carlos RPG

Scope: `simulation/` only. These rules supplement the root `AGENTS.md`; they do not change the original interactive story.

## Causal alternatives and efficient debugging — owner decision 2026-11-14

When a proposed fix repeatedly fails, **change the hypothesis, not the evidence**. Inspect event logs and the original NPCs, compare alternative **world-consistent** mechanisms, and implement the smallest coherent remedy **within the current open phase**. Alternative designs are explicitly allowed; repeated narrow patches without root-cause evidence are not the preferred path.

Every alternative must preserve finite physical stock, conserved seeded funds, actual work and funded wages, time and known-road travel, NPC autonomy, authentic ownership, deterministic SQLite/event replay, and existing release gates. No fictional food/copper, fabricated jobs, silent rescue, teleportation or artificially scripted success. Prefer fast deterministic failure probes first, then the relevant authentic 13-NPC long run (96/168 h for PLAY-48), then full regression CI on the final candidate. Do not lower acceptance criteria or start a new phase as a shortcut. Record the confirmed fault, rejected approach, causal alternative and measured outcome concisely.


## Mandatory sequence for EVERY development task

1. **Analyze before implementing.** Inspect the actual branch HEAD, relevant code, tests, roadmap, historical constraints and CI evidence. State the task's goal, assumptions, affected files, invariants, failure modes, security/trust boundaries and acceptance criteria. Distinguish verified facts from hypotheses.
2. **Plan small, reviewable changes.** Identify the exact implementation and regression tests required. For consequential decisions, record unresolved questions before introducing a new game rule.
3. **Implement only the analyzed scope.** Avoid speculative mechanics, silent migrations, rewriting original story files, or modifying `main` without user approval.
4. **Test, fix and review.** Run targeted tests, regression tests, replay/snapshot integrity tests, version compatibility and adversarial cases as applicable. Repair failures and rerun. Record environment, exact commit SHA and verifiable CI evidence; do not call an unexecuted test successful.
5. **Document only verified outcomes.** Update relevant phase report and roadmap status, note remaining risks and P0 blockers, and clearly distinguish independent third-party review from author self-review.
6. **Gate the next phase.** Do not call a phase complete or begin implementing the next phase until required checks and the agreed review have passed.

## Non-negotiable simulation boundaries

- The engine/event ledger/SQLite state, not an LLM, is authoritative.
- World state is causal, persistent and deterministic; no event is invented by narration.
- Physical custody, market sale, historical claim registration, collection permissions and *legal title* are distinct. No implicit legal ownership, adjudication or judicial enforcement.
- NPC knowledge and player perception remain scoped; a trusted in-process capability is not user authentication.
- Prefer 5–10 NPC behavioral scenarios and reproducible failure probes; use larger performance runs only when justified.
- Preserve original story files and `main`. Update only the active development branch.
