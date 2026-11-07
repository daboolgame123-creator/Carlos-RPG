# PLAY-21 — Food ecology: integrated NPC hunger, autonomous foraging and scarcity

Date: 2026-11-07. Status: IN_PROGRESS / CI_PENDING.
Base: PLAY-20 @ a0c091e36cb3e95ea41cd99218c8d74efec3fe91.
Branch: `simulation-engine-phase-play-21-ecology`.
Scope: disposable seven-NPC village only; no `main`, original story, schema/rules, production P0, or health/death mechanics.

## Analysis first
PLAY-20 proves two real one-hour journeys and 2 NPC meals, but its dedicated NPC hunger gateway does not enable the already-existing food-foraging, knowledge, food-route, scarcity or assistance policies. Thus hungry NPCs in PLAY-20 cannot seek wild food in that mode even though the core engine contains the capabilities. Do not claim sustainable village life or NPC starvation death.

## Implement as one independently testable batch
- **21a**: Add a new opt-in ecology bootstrap on top of the seven-NPC survival fixture, initialize missing bakery natural-food stock explicitly to zero, and retain a bootstrap-command marker. Existing worlds and their mode flags must remain unchanged. The gateway must reject mismatched ecology flags and require survival mode.
- **21b**: Enable existing local autonomous forage, learned food navigation, finite gathering, local knowledge sharing and scarcity/assistance together ONLY in the ecology fixture. Do not make NPCs omniscient, mint food, force Carlos's choices or change engine rules.
- **21c**: Run two different physically bounded player decisions (observe vs compete for square food) against seven autonomous NPCs. Collect exact NPC forage/meal/supply/replay outcomes, and compare world-conserved natural+owned+consumed food. Do not require all NPCs to eat or survive indefinitely.
- **21d**: Verify real SQLite save/resume, event-chain integrity, privacy of player handoff, correct world time, invalid mode and horizon rejection, determinism and finite stock, ideally under two Python versions.
- **21e**: Add targeted GitHub CI and run full regression. Accept technical closure only on actual matching successful CI SHA and logs. If integration breaks, fix and rerun before closing.

## Known hazards
NPC action duration is 120 logical seconds vs human forage 60 seconds; earlier player gathering can genuinely deny a later NPC. Multiple NPCs competing can fail at completion without false inventory. Automatic assistance and social events may raise the event count; 120-second waits are bounded; snapshots accelerate repeated replay without bypassing verification. No arbitrary speed-up of time, no claims about days or mortality. Keep older PLAY-20 fixture working.

## Gate
Require a witnessed real autonomous forage outcome, actual NPC meals, finite conservation, two divergent player choices, persistent same-file restart and safe player projection. Dual Python CI success is the closure condition. All external review/P0, 03-A, 03-A7c and PLAY-14g remain open.
