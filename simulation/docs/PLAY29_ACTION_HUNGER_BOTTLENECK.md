# PLAY-29 — Action-completion hunger bottleneck (diagnostic)

**2026-11-08 | Independent design branch, no gameplay change.**

## Confirmed source behavior

`simulation/src/carlos_sim/actions.py::resolve_action` currently adds
**hunger on action completion** independently of the background passage
of simulated time:

| Real NPC action | Nominal hunger change at completion |
|---|---:|
| work | +10 |
| rest | +5 |
| investigate | +5 |
| wait | +5 |
| forage | +5 |

The legacy baseline `survival.py` simultaneously adds +1 hunger per
300 seconds. In the isolated Schema 38 / Rules 50 experiment, the
per-world background rate was changed to one per 3600 seconds **only
for an explicitly configured experimental world**. All action
completion costs remained unchanged.

## Crucial observation

The original three-day A/B test with six finite personal food units
per NPC reached hunger 100 for every NPC in **both** profiles, so a
test asserting unequal *final* hunger failed. This is not proof that
the persisted setting was ignored: the focused 3600-second tests
verify the default gives Nora +12 baseline points and the opt-in
world gives +1. The long-run test is now corrected to compare
genuine 6-hour hunger trajectories, preserving end-of-day starvation
as an explicit failure of food security rather than masking it.

The seven-NPC endurance world commonly logs approximately 150+ NPC
actions per day, a significant number of which may impose 5 or 10
additional hunger points on completion. **Nominal frequency is not
proof of identical completed-action counts**; inspect actual
`completed_at` and recorded `needs` deltas per character before
making a stronger production claim.

## Implementation next (strictly versioned)

1. Introduce a **separately declared, frozen, time-zero-only activity
   hunger cost policy**, e.g. legacy / reduced, with permitted values
   checked in the pure reducer and SQLite replay.
2. The current default mode MUST retain all previous +5/+10 costs.
   No ad-hoc runtime toggles, hidden clock changes, or player-accessible
   resource overrides.
3. A reduced policy must still charge authentic physical effort and
   normal elapsed-time metabolism. Ordinary waiting should not burn
   a second full ration merely because the planner emitted another
   wait action. Do not equate reduced cost with free production.
4. Compare 3-day real worlds with identical **finite** food, seed,
   farmland, tools, water, money, routes and NPCs. Track intermediate
   hunger trajectories, completed work, individual meals, real crop
   yield, and NPC rest. A good end state needs actual food and access;
   a lower hunger number alone is not a success criterion.
5. Verify deterministic event replay, stop/start, snapshot,
   default-off frozen parity, both supported Python versions and
   versioned schema/rules migration before considering integration.

**Status:** Diagnose-only. No code implementing this proposed
activity-cost policy has been merged, and none of the existing
conservation rules has been weakened.
