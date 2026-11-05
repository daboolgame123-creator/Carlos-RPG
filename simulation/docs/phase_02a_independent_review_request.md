# Independent review request — Phase 02-A

**Review requested, NOT performed.** P0 remains **OPEN**, review DEFERRED. The author-run tests and green CI do not amount to independent approval.

**Baseline:** 01-Z `1225ae066f22bc2688a583d46e63ceda80558a07`, Schema 14 / Rules 21. **Candidate branch:** `simulation-engine-phase-02a`, Schema 15 / Rules 22.

Review `simulation/src/carlos_sim/environment.py`, its hooks in `domain.py`, `tests/test_environment_02a.py`, 7-NPC demo, frozen version checks and semantic parity. Pay attention to:
- Source-of-truth causation: every unit of increased site `wild_food` must debit an existing *known* `regrowth_reserve` unit. Validate unknown vs zero, capacity and depletion; no free growth, accidental refilling or double conversion.
- Fabricated bootstrap, actor, due-tick and generic scheduled operations: ensure only a genuine authenticated clock firing of an authorized environment configuration converts stock; attempt early, out-of-order and duplicate tick, forged schedule, cancellation and snapshot tampering.
- Time determinism: 600 seconds at once versus small steps; ties between environment and NPC action completion; due-now behavior and event budgets; expensive periods/IDs and reservation of follow-up schedules; wall-clock must not advance it.
- Physical knowledge: no NPC at a distant site should learn a replenishment just by world state changes, and a character must still perform an eligible local completed action to take wild food.
- SQLite consistency, rollback, snapshot replay, restore to a new path and genuine 01-Z 14/21 file incompatibility. Report operational risk of the still-open P0 gate separately; **no long-lived world approval**.
- Regression parity against frozen historical 7-NPC fixtures: verify the only stripped new state is empty `environment_cycles`; NPC resources/knowledge and event digests still have strict equality.

The reviewer should attach independent reproductions, their environment, Git SHA and blocker classifications. Until that happens: **TECHNICALLY_VALIDATED only when CI final SHA passes; EXTERNAL_REVIEW_DEFERRED; not APPROVED/CLOSED.**
