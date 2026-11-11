# PLAY-48 — Owner-authorized economic recovery reopening (2026-11-11)

## Authorization and baseline
Owner explicitly authorized reopening PLAY-48 on 2026-11-11, limited to repairing the genuine 13-NPC earned-income/physical-food feedback loop and proving 96h then 168h endurance. This supersedes the *stop on further investigation* in `PLAY_48_PHASE_TERMINAL_DISPOSITION_2026-11-11.md` only for this scoped experiment. It does NOT supersede its documented failed result, nor authorize PLAY-49, main merge, release, production saves, or migration.

Branch: `feature/play48-reopened-income-food-168h-20261111`.
Baseline: `290828cef1d38e8680b4836ff52cd36828c58bdb`; tested engine source previously recorded as `e3db72d8584de1076b78ebba27cfe4c82714235a`; experimental Schema45 / Rules61.

## Root-cause hypothesis (not yet established as a fix)
At 72–96h, genuine 13-NPC economic A/B had 13/13 at hunger cap, with zero new jobs, food purchases, meals or courier deliveries. The prior physical grain→bakery→farm experiment produced two genuine delivered loaves, but the farm-owned loaves are not automatically worker-owned food or authorized wages. Personal solvency, physical reachability, labor eligibility and actual food stock must all coincide. Diagnose which first blocks the loop; do not infer that increasing food or paying an arbitrary wage resolves it.

## Work packages and acceptance
1. **Read-only causal audit:** reproduce identical genuine 13-NPC seed/weather at 0,24,48,72,96h; report per NPC personally owned food, spendable copper (excluding custody), personally known route, nearby saleable/affordable food, fatigue/hunger work guards, and real employer escrow. Capture conservation and exact event sequence.
2. **Minimum justified policy repair:** select one first proven blocker and implement smallest default-off, versioned change. Earned wages require completed service receipt, unique payout, employer-owned funds/food, and actual physical transfer. No invented NPC knowledge, market stock, cash, food, roads or travel.
3. **Adversarial checks:** no double payment, no duplicate cargo, no purchase with entrusted courier cash, no remote omniscience, no inaccessible-shop purchase, no stale/unsigned receipt, no negative stock or wallet, no legacy-save semantic change. Reopen/replay determinism.
4. **Endurance A/B:** same initial 13 NPCs and weather, intervention ON vs OFF. Report at 24/48/72/96h and daily through 168h: individual hunger, meals, jobs, deliveries, sales, real wages, site stocks, wallet/custody/escrow balances, and conserved resource/copper ledgers. Count independent economic actions *after* 72h, not merely pre-72 carryover.
5. **Release gate:** a reproducible genuine 96h AND 168h economy must show no terminal systemwide hunger/work/trade freeze; food must be physically accessible and affordable for each resident by ordinary autonomous rules, with no magic replenishment; exact-SHA targeted + full historical CI on Python3.10/3.13 and independent review. If any gate fails, record `PLAY48_REOPENED / ACCEPTANCE_NO_GO` with concrete evidence; do not relabel success.

## Stop discipline
No new professions or unrelated features, no dozens of short exploratory branches, no unverified test claims. Analyze → implement → test → document; stop at first authoritative blocker. No merge or PLAY-49 without explicit owner decision and passed gates.
