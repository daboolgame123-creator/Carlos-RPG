# Phase 01-U — Technical validation report

**Status:** TECHNICALLY_VALIDATED / EXTERNAL_REVIEW_PENDING — NOT APPROVED/CLOSED.
**Branch:** simulation-engine-phase-01u, forked from 01-T checkpoint d2a397bde95d2596592818f348d68b030f78f48a.
**Verified code commit:** 537c72dc3337265d287030cc7f2a9f95885793aa.
**CI:** [41930579158](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/41930579158) SUCCESS; **564/564 tests on Python 3.10 and 3.13**.
**Schema/Rules:** 13/18, unchanged; **P0 remains OPEN**.

## Delivered behavior

- Pure food-route planner (food_navigation.py) uses only this NPC's food:present beliefs, learned roads, private needs, and its own known food inventory. No remote deposit, foreign inventory, or foreign memory is consulted.
- Weighted shortest KNOWN path wins, then higher effective belief confidence, then stable site/path ordering; path duration is genuine simulated travel time.
- Opt-in food_navigation_enabled=False by default. When enabled, it requires navigation_enabled, knowledge_enabled and foraging_enabled. All legacy behavior is retained when disabled.
- Existing ScheduledEventCreated and NPCTravelStarted events represent actual routes and completion; the recorded reason describes subjective belief, source, age and known travel seconds, never remote stock as truth.
- Local foraging, existing explicit navigation targets, current decisions, private danger warnings, physical needs, and decision cooldown take priority. Forage at a stocked destination is a separate 120-second act, not automatic upon arrival.
- False rumors can cause wasted but legal travel. Arrival observation correctly updates the actor's personal belief to empty/present; uninitialized stock stays unknown rather than being hallucinated as empty. No teleportation or resource generation.

## Evidence and failure probes

- Added **20 cases** to the 01-T baseline of 544, for **564/564 passing** on each supported interpreter (CI link above). Tests use a five-NPC world and check unknown/finite resources, false rumors, local action precedence, private memory isolation, unseen road rejection and successfully learned two-hop routes.
- Additional tests verify danger/needs/unknown personal inventory, manual target override, exact decision-cooldown timing, event-budget atomic rollback, snapshot+SQLite reopen+full replay, duplicate command refusal, and split 50+120s versus single 170s physical outcomes.
- New CI step invokes the SAME knowledge-enabled test-world script under the frozen actual 01-T runtime (SHA d2a397b) and 01-U runtime, leaving only the 01-U flag disabled. State/event digests, revision, clock, event counts and replay agree exactly on both Python versions.
- Existing immutable 01-R and 01-S save rejection and 01-T parity checks are retained and pass; no schema/rules upgrade or migration is introduced by 01-U.

## Pending gates

- Phase 01-T and Phase 01-U **both await external independent review**. The implementing assistant's adversarial checks and green CI do not count as a separate APPROVED signature.
- Same-tick multi-hop hearsay from 01-T is an inherited policy question for independent classification; not silently changed here.
- Path weight currently measures travel seconds, not hazards, stamina debits, weather, cargo expenses or road capacities. Those require separately approved behavior.
- P0 backup/restore remains OPEN. All worlds are disposable tests; no long-term durable-world claim, automatic migration, real Carlos story import, main changes, or unreviewed public access.

**Verdict:** TECHNICALLY_VALIDATED / EXTERNAL_REVIEW_PENDING. May be a conditional development dependency under Development Protocol section J, but is **not formally closed**.
