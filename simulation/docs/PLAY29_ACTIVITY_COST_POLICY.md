# PLAY-29 — Actual action hunger costs, isolated prototype

**Branch:** `design/play29-activity-hunger-policy-20261108`.
**Schema / Rules:** `39 / 51`. Not merged, not released.

An authenticated one-time `MetabolismPolicyConfigured` event at world
time 0 may set `hunger_seconds_per_point` (300 or 3600), with optional
`activity_hunger_percent` (100 or 20).

- Missing policy: preserves exact original 300 seconds/point and
  +5/+10 hunger per NPC action, even if this test is compiled.
- Explicit 3600/20 world: background hunger accrues one point per
  3600 simulated seconds; **actual completed work still charges +2**,
  and rest/wait/investigate/forage charge **+1** each, never zero.
- Action durations, fatigue, actual tool use, inventory, food consumption,
  water conservation, production and NPC scheduling are not changed.
- Both policy settings are immutable after bootstrap. Stored in
  WorldState and subject to strict type checks and SQLite event replay.
- Any old Schema 38 / Rules 50 world remains explicitly incompatible
  until a trusted migration is separately reviewed.

**Acceptance pending:** Python 3.10/3.13 focused tests, full frozen
behavior parity, all inherited tests updated for this new current
version, real multi-day seven-NPC scarcity A/B, independent review.
No claims of self-sufficiency or of the end of starvation.
