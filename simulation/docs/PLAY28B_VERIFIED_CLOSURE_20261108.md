# PLAY-28B — Verified technical closure (2026-11-08)

**Status:** `CLOSED_TECHNICALLY` — **not merged into main; not released.**

- **Exact verified source SHA:** `f33e8e350c27857257e2d25d2539f1dc02b07cbb`
- **Source branch:** `design/play28b-release-candidate-20261108`
- **Schema / Rules:** `37 / 49`
- **Acceptance**: all five independent GitHub Actions workflows passed on the same code SHA under Python **3.10** and **3.13**:
  - Full inherited suite: https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42473475793 — **1,612 passed per Python version**; frozen historical parity gates also passed.
  - Integrated finite hydrology and replay: https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42473475745
  - Historical feature-off parity: https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42473475773
  - Three-day real seven-NPC wet village: https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42473475737
  - Three-day real seven-NPC drought-vs-rain A/B: https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42473475791

## Verified behavior

1. Finite wells are configured at trusted time zero with capacity and known actual stock.
2. **Only authenticated, non-player, explicitly attested rainfall events** replenish a well. No periodic or automatic water generation; forged/duplicate/over-capacity rain fails atomically.
3. Existing physical couriers must carry well water along valid routes. Irrigation consumes actual delivered water and crops require biological growth time.
4. SQLite persists the observation authority, event provenance and snapshots; replay reproduces the exact final world. Rain cannot be smuggled into privileged bootstrap.
5. Tested both Python versions against frozen predecessor runtimes; features are opt-in and no old-world water is silently granted.
6. One- vs two-unit water A/B yielded **one** vs **two** mature crops after 3 days, and one vs two physical deliveries; both worlds reached hunger 100. **This demonstrates water helps production, not yet food self-sufficiency.**

## Scope boundaries

- No migration from old Schema 36 / Rules 48 is silently applied; unsupported versions must be rejected explicitly.
- Main branch unchanged, no externally reviewed game release, no autonomous weather model, no magic food or water, no guarantee of indefinite village survival.
- PLAY-29 investigates the independently measured bottleneck of hunger and food access on separate branches. The experimental 38/50 metabolism branch is **not part of this release**.

**Next step:** optional independent security review, explicit migration plan if old saved games need upgrading, and PLAY-29 accepted separately. Do not reopen PLAY-28B for unrelated optimizations.
