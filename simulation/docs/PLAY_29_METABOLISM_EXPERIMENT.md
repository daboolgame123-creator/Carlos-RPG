# PLAY-29 — Versioned per-world metabolism calibration (experimental)

**Isolated branch:** `design/play29-opt-in-metabolism-20261108`.
**Schema 38 / Rules 50**; no changes to `main`, and not accepted for
release or automatic upgrade of previous SQLite worlds.

A trusted time-zero `MetabolismPolicyConfigured` event can set
`hunger_seconds_per_point=3600`. Its absence preserves the previous
300-seconds-per-point rule. The policy is stored in each immutable WorldState,
included in every snapshot and replay. A player cannot set it, nor can
the simulation change it at runtime or generate food as a side effect.

Real NPC hunger, rather than a report-only calculation, changes during
authorized `TimeAdvanced` events in opt-in experimental worlds.
Work and rest surcharges, fatigue, meals, courier logistics, and food
conservation remain unchanged.

**Next acceptance criteria:** Tests on 3.10 and 3.13, adversarial
snapshot and provenance checks, repeatable split-step replay, 3-day real
seven-NPC endurance with 300s vs 3600s worlds, consistent rates across
restart, and an independent 37/49-to-38/50 compatibility/migration gate.
The opt-in experiment MUST NOT be merged before historical version pins
and frozen feature-off parity checks are reconciled.

**Gameplay note:** This is a calibration experiment, not permission to
erase hunger, create bread, or magically replenish water.
