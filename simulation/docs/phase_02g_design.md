# Phase 02-G — Local rumors and attributed reputation, first bounded slice

**Date:** 2026-11-05. **Status:** DESIGN / IMPLEMENTATION IN PROGRESS / EXTERNAL REVIEW DEFERRED.  
**Base:** green 02-F `d46aaa04fd53f07e3fd06358f6f62efb904e7452` (GitHub Actions 42100855692). P0 remains OPEN. Disposable test worlds only.

## Missing-essential-mechanics gate

Reviewed the newly mandatory roadmap open requirements WORLD-GAP-001 (safe emergency cancellation), WORLD-GAP-002 (funded wages/contracts) and WORLD-GAP-003 (housing/property). None is required for a **rumor-only** gossip slice. They remain OPEN and can become blocking before richer hazards, employment or property enforcement. Do not imply they are implemented by this work.

## Scope

An NPC can repeat **a genuine past local social message** to one co-located NPC. This records that a claim was told, not that the contents of the message are objectively true. The original message must have been genuinely received; first-hand gossip comes from the original recipient, and forwarded gossip comes from an earlier authenticated receipt. Each relay has an attributed sender, receiver, original message reference, parent delivery, time, location, hop count, and bounded confidence.

An addressed NPC may relay only what they know. Knowledge acquired in the same simulation tick is **not immediately forwarded**. Both participants must be physically present, not in transit. A locally chosen, optional autonomous gossip pass may generate at most one original report per recipient per time slice, with explicit per-speaker cooldown, suppressing explosive propagation and unbounded memory.

**Personal reputation is a subjective interpretation, not a globally correct stat.** A listener can conservatively flag that they heard a documented *threat speech-act* from someone, with confidence weakened by hops. There is no automatic market refusal, criminal conviction, relationship adjustment, actual theft, salary change or identity mutation. A caller can query only a specific NPC's own local hearsay; never reveal everybody's secret memory.

## Safety

- No arbitrary origin story, invented actor, or trust in quoted player/NPC text. Only `SocialMessageReceived` can ground a rumor.
- No change to `social_messages` and no free trust gains, coins, resources, houses or hidden map knowledge.
- No local delivery to a traveling entity and no long-distance magical gossip.
- New ledger data and event names require a deliberate Schema/Rules bump and genuine 02-F old-world rejection unchanged.
- Atomic, authorized and replayable events; invalid origin/parent/location/clock/duplicate must fail closed.
- No impression that the natural-language model can choose certified world facts: it may later narrate only what the engine authorized.
- Default feature OFF and exact old behavior parity when OFF.

## Acceptance checklist

1. Real witnessed NPC/player threat can be repeated to a different co-located NPC as attributed hearsay, without treating accusation/content as truth.
2. An unwitnessed, fabricated, self-witnessed or non-received original message is rejected.
3. Secondary relay requires a real earlier linked delivery and cannot forward in the same tick.
4. Remote parties and travelers cannot relay or receive.
5. Distinct recipients can hold distinct rumor knowledge; no omniscient global reputation.
6. Deduplicate per listener/origin and bound recipients, hop count and propagation.
7. Second-hand source chain survives snapshot, SQLite close/reopen, replay and verified backup.
8. Autonomous planner only uses source's known real messages and local participants; no same-tick cascades.
9. Frozen 02-F default-off event/semantic parity and version compatibility checks pass.
10. CI on exact HEAD Python 3.10/3.13 and independent external review separately required.

**Deferred:** hallucination-resistant arbitrary free-text semantic extraction, human-like lying/embellishment, probabilistic memory loss, culturally variable insult classification, economic refusal based on rumors, political group rumor propagation. Must be documented, prioritized and attached to a future stage if classified as essential in later review.
