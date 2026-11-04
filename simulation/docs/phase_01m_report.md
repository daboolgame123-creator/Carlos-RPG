# Phase 01-M — Survival needs across explicit simulated time

## Scope implemented

- Opt-in `LivingWorldEngine(..., survival_enabled=True)` updates NPC baseline **hunger** and **fatigue** as in-world time advances. Ordinary `TimeEngine` and the living-world engine with survival disabled keep their previous behavior; there is no background or wall-clock progression.
- Experimental fixed rates: **+1 hunger / 300 simulated seconds**, **+1 fatigue / 600 simulated seconds when not actively resting**. Hunger progresses during rest; fatigue's background increment pauses during a running `rest` action, whose own completion already reduces fatigue. Other work/travel/activity effects stay separate **extra effort costs**; time is not charged twice at boundaries.
- Every NPC's subinterval residues are stored in `WorldState.survival_progress` (`hunger_seconds`, `fatigue_seconds`), so single-versus-split advancement and replay have the same semantic outcome. No hidden catch-up occurs for intervals deliberately advanced while this mode was disabled.
- When survival mode is selected, **critical hunger >=90** suppresses ordinary `work` and `investigate` preference in favor of conserving energy (`rest`/`wait`), including the first decision at time zero. This does not provide food or revive anyone. Disabling the mode restores the old decision policy, even in a world with old survival residues.
- Both persistence and replay record the trusted internal `survival_authorized` capability per command. The normal untrusted clock path cannot silently enable metabolism. Simulation remains frozen while the play session is closed.

## Demonstration

`PYTHONPATH=src python scenarios/test_village/demo_survival.py` runs a disposable synthetic village. With hunger 20 and fatigue 5, after 299 seconds nothing rounds up; at time 300 hunger becomes 21, at time 600 hunger becomes 22 and fatigue becomes 6. Each stored event replays identically. No food appears.

## Tests

**379/379 tests passed locally after review** in five completed groups after the final changes:

- Core, clock, NPC decisions and action lifecycle: **134**
- Movement, navigation, social policy and review: **107**
- Aid and obligations including 01-J review: **41**
- Autonomous aid including 01-K review: **31**
- Eating/review (38) and original survival tests (22): **60**
- Post-review tests: **6**

Tests cover opt-in/off, original behavior, exact fractional boundaries, large/split advances, clamping, world restart, snapshots, audit validation, unauthorized changes, live rest and work effects, critical-hunger decisions from the first tick, toggling modes, physical aid and eating, interruption, event-budget rollback and player privacy. `python -m compileall -q src tests scenarios` passed. A combined test invocation temporarily exceeded the command time limit; the last group then completed with **60/60** on a separate rerun. Hosted GitHub CI was **not** run.

## Performance measurements — narrow and local

`PYTHONPATH=src python scenarios/test_village/bench_survival.py` measured median execution time for **one pure 600-second `TimeAdvanced` reducer operation** on the test host (three repeated runs):

| NPC count | Median reducer time |
| ---: | ---: |
| 10 | 0.00074 seconds |
| 100 | 0.00508 seconds |
| 1000 | 0.05106 seconds |

This does **not** measure SQLite initial population, command commits, full replay, NPC action generation, interactions, memory growth or multiplayer response latency. The existing projection/validation model rechecks and copies growing world state on many events. Future work must separately profile realistic 100/1000-NPC **full-engine** scenarios and optimize incremental projection and replay if necessary; the figures above are not a throughput guarantee.

## Limits and compatibility

- No hunger-related HP loss, illness, death, incapacitation, realistic digestion, day/night metabolism, independent resource production, shopping, food spoilage or debt rules in this phase. An NPC can remain at hunger 100; it will not be saved by hidden plot protection, but a later health/death system needs explicit design.
- The present fixed action completion costs remain and are explicitly treated as activity surcharges. Their game balance is provisional; advanced effort models should revisit them before claiming realism.
- The `survival_authorized` capability is a **trusted local engine flag**, not end-user authentication; never expose it to untrusted HTTP clients.
- **Schema 11 / Rules 15.** This phase adds a persisted residual map and command flag. Previously created experimental SQLite worlds require deliberate migration or new test databases; there is no silent migration.
- No changes to Carlos canonical narrative or repository `main`.

## Status

Independent review completed; ready for closure within prototype scope. Large-world performance optimization is still required.

## Phase 01-M independent review — 2026-11-04

**Issue fixed:** `NPCService.decide` previously ignored the survival-mode policy. At hunger 90 it recorded work; the living-world engine then honored this prior decision, bypassing its intended critical-hunger preference. The service now accepts `survival_enabled=True`, evaluates the same opt-in policy, and records the trusted survival capability for deterministic replay. It does not advance logical time when recording a decision. Its default remains `False`, preserving the previous API and pre-existing manual intentions.

**Verification:** six new regression tests (critical hunger, legacy default, noncritical behavior, invalid mode, snapshot/restart and no elapsed-time charge). All **379 tests** passed in four completed local batches: **162 + 107 + 41 + 69**. Python compilation and isolated village demo passed. No hosted GitHub CI was run.

**End-to-end performance:** `PYTHONPATH=src python scenarios/test_village/bench_living_world.py` runs a 60-second living-world command including NPC action events and SQLite persistence. Measured on the review host (one sample): 10 NPCs/31 events **0.139 s**, 25/76 **0.654 s**, 50/151 **2.525 s**, 100/301 **9.416 s**. At 50 NPCs, survival disabled measured **2.296 s** and enabled **2.33 s** in comparable worlds. This is a serious scaling concern in the existing complete event projection/validation pipeline, not a speed estimate for actual gameplay. The earlier 0.05-second metric measured **only one pure metabolism reducer event** for 1000 NPCs. Structural optimization should be separately reviewed before scaling. No risky event-store rewrite is performed in this phase.

**Compatibility:** schema **11**, rules **15** unchanged. No change to `main`, Carlos narrative or actual RPG world.
