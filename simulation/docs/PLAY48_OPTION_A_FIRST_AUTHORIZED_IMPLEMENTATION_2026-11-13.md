# PLAY-48 Option A — approved food for real work: first bounded implementation

**Owner decision:** Option A approved (2026-11-12). The owner cannot currently use OpenCode. Implementation continued using the connected GitHub repository directly.

**Status:** `OPTION_A_PRODUCTION_WAGE_PILOT / PLAY48_ECONOMIC_NO_GO / RELEASE_NO_GO`. This is NOT proof the 13-person economy is alive at 96h/168h. No merge or save migration.

## 1. Exact source and scope

- Base: `experiment/play48-final-168h-no-go-20261112` @ `a28a2c429a95dc7c2552faa4e0d92537d288dafc`, [PR #91](https://github.com/daboolgame123-creator/Carlos-RPG/pull/91).
- Work branch: `feature/play48-authorized-physical-food-for-work-20261113`.
- Draft PR: [#92](https://github.com/daboolgame123-creator/Carlos-RPG/pull/92).
- CI: [PLAY48 Option A dual interpreter](https://github.com/daboolgame123-creator/Carlos-RPG/actions/workflows/play48-first-authorized-food-for-work.yml).
- Files: new `food_for_work.py`, linked `production.py`, `domain.py`, `store.py`, `living_world.py`; opt-in signed 13-NPC bakery seed and security/physical-simulation tests.
- **Rules 62 -> 63** due to a NEW persisted economic event. Schema 45 retained (existing job receipt extension). No old save migration or Rules62 replay promised.

## 2. Contract and actual property transfer

- At **trusted time zero**, the original site-owned production recipe MUST include exactly `wage_food=1`; it cannot also have `wage_coin`. The employer/site must have an initialized food ledger. Ordinary historic recipes never acquire this automatically.
- When the REAL assigned worker's production job becomes `completed` at the original workplace, and the worker is physically present (not traveling/working elsewhere), the opt-in engine may propose one `ProductionFoodWagePaid`.
- A protected active-session production authority verifies the signed recipe, exact completed job ID, unique payment, available LOCAL site-owned FOOD, no customer-quoted bread or consigned cargo, initialized worker inventory, and a 36h per-worker food-wage cooldown.
- Reducer subtracts 1 from the physical site and adds exactly 1 to the worker's PERSONAL food. Job receipt records `site_before,site_after,worker_before,worker_after,paid_at` and is validated on every State decode and SQLite replay.
- Normal hunger consumption remains separate; payment does not reduce hunger directly. No source is minted and no remote site is queried or drained.
- If a worksite has no unpromised owned food, the completed worker remains unpaid instead of conjuring a wage. The owner must solve site financing/physical routing rather than override this.
- In opt-in test genesis only, of the **original three** opening loaves, **two stay saleable at market and one starts physically owned at bakery**. This differs transparently from the PR90 allocation; total remains three, copper twelve and people thirteen. Sign the baker's original recipe to food, run unforced autonomy.

## 3. What is NOT implemented yet

This first bounded event covers only completed on-site production jobs, NOT:
- A standing repeatedly earned food wage for real couriers' water/grain/food deliveries. Existing finite `courier_provisions` remain distinct and require their own explicit service authorization, physical payer surplus, unique proofs, and customer quote protection.
- Economic work/income for guards, explorers, merchants, smiths, repairers or residents without actual paid services.
- A real cross-site granary distribution chain; market food never teleports to field workers.
- Proof of renewable seven-day water, grain, fuel, bread and wages. One day of 12 loaves does not establish sustainable 168h production.

**Do NOT infer economic recovery from a passing test or a baker earning one loaf.**

## 4. Acceptance gates before GO

1. Dual Python3.10/3.13 exact SHA security tests pass: forged job, wrong actor, wrong amount, no authority, repeated service; physical conservation + SQLite integrity/replay under genuine 13NPC autonomy.
2. Review new Rules63 persistence policy and historical tests separately. Rules62 saves must be explicitly rejected or migrated with independently reviewed proof; do not quietly rewrite old snapshots.
3. Add owner-authorized finite **real physically delivered** food-for-service to couriers and an employment/food entitlement path for otherwise zero-income residents, without forced NPC choices.
4. Run a genuine same-physical-resource control/treatment on all thirteen through 24/48/72/96/168h with strict post72 activities, real available meals, true per-NPC hunger, food/cash provenance, no fake gifts and cross-Python validation.
5. Only an actually sustained economy may be marked `PLAY48_ECONOMIC_ACCEPTED`; otherwise `PLAY48_ECONOMIC_NO_GO` remains.

**No merge, no PLAY49 and no `PLAY48_CLOSED` yet.**
