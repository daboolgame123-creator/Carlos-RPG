# Simulation Development Agent Rules — Carlos RPG

Scope: `simulation/` only. These rules supplement the root `AGENTS.md`; they do not change the original interactive story.

## Mandatory sequence for EVERY development task

1. **Analyze before implementing.** Inspect the actual branch HEAD, relevant code, tests, roadmap, historical constraints and CI evidence. State the task's goal, assumptions, affected files, invariants, failure modes, security/trust boundaries and acceptance criteria. Distinguish verified facts from hypotheses.
2. **Plan small, reviewable changes.** Identify the exact implementation and regression tests required. For consequential decisions, record unresolved questions before introducing a new game rule.
3. **Implement only the analyzed scope.** Avoid speculative mechanics, silent migrations, rewriting original story files, or modifying `main` without user approval.
4. **Test, fix and review.** Run targeted tests, regression tests, replay/snapshot integrity tests, version compatibility and adversarial cases as applicable. Repair failures and rerun. Record environment, exact commit SHA and verifiable CI evidence; do not call an unexecuted test successful.
5. **Document only verified outcomes.** Update relevant phase report and roadmap status, note remaining risks and P0 blockers, and clearly distinguish independent third-party review from author self-review.
6. **Gate the next phase pragmatically.** Agree on a small, stable set of *essential* correctness and safety checks. Do not claim a gate passed when it failed; however, do not prolong a phase with expanding optional checks, marginal refinements or repeated full endurance runs. Record known noncritical limitations, close the bounded objective when those essential checks pass and the owner approves, and schedule other improvements separately.


## Owner direction — pragmatic progress without breaking the world (18 Nov 2026)

- **A believable causal world, not a perfect engine.** Prefer a simple, functioning solution with a clear world-consistent cause over technically elegant but indefinite work. Make practical tradeoffs in rules, timing, scope, acceptance depth and implementation complexity when necessary.
- **Do not get stuck in one task or phase.** Time-box investigation, identify the *actual* bottleneck, try a different small design when the current approach stalls, and deliver multiple tightly related changes together where safe. Do not start new features merely to work around a failing core loop.
- **Accept imperfect but honest outcomes.** NPCs may be hungry, unemployed, unequal or occasionally fail economically: realism does not require every individual to prosper. Distinguish emergent hardship from a broken production, transport or payment mechanism. Revisit a phase only for proven material blockers; log polish and optional improvements for later.
- **Conserve the world's causal foundations.** Do not mint money, goods or food, invent jobs/services, teleport ownership or payments, fabricate receipts, silently alter historical saves, or circumvent event-ledger trust. A compromise must still be explainable through in-world contracts, physical movement and available resources.
- **Efficient verification.** Run the smallest relevant deterministic test first; expand to checkpoints, adversarial checks and endurance only when their outcome changes the decision. Never represent incomplete or failing verification as success. Agree explicitly with the owner before relaxing an established *release-critical* criterion; do not silently lower gates.
- **Progress before perfection.** For PLAY-48 specifically, prioritize restoration of a working village economy and proof of real grain revenue, earned wages and food access; keep optional tuning outside the critical path. PLAY-49 and later phases remain separate until the owner decides to advance.

## Non-negotiable simulation boundaries

- The engine/event ledger/SQLite state, not an LLM, is authoritative.
- World state is causal, persistent and deterministic; no event is invented by narration.
- Physical custody, market sale, historical claim registration, collection permissions and *legal title* are distinct. No implicit legal ownership, adjudication or judicial enforcement.
- NPC knowledge and player perception remain scoped; a trusted in-process capability is not user authentication.
- Prefer 5–10 NPC behavioral scenarios and reproducible failure probes; use larger performance runs only when justified.
- Preserve original story files and `main`. Update only the active development branch.
