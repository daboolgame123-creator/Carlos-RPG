# Future Context & Dialogue Memory Contract — Carlos RPG

**Recorded:** 2026-11-05  
**Status:** ACCEPTED REQUIREMENTS / DESIGN DEFERRED / NOT IMPLEMENTED  
**Planned integration:** Phase 05-A (secure narrative adapter) and later reviewed memory/retrieval slices. This document is **not** permission to implement context memory prematurely or to bypass the P0 save/restore gate.

## The problem

A Carlos playthrough may involve hundreds of hours, thousands of world events and conversations with many NPCs. An LLM's context window is finite, and sending full chat history at every turn is slow, costly, and prone to confusion. A chat session is **not** the authoritative world save. Starting a new chat must not alter the simulation or erase durable facts.

## Non-negotiable invariants

1. **The engine and authoritative event-sourced world state are the source of truth.** Player/NPC speech, narrator prose and model-generated interpretations are *claims* or *proposals*, never automatic changes to physical facts, past events, inventory, money, identity, age, location, NPC knowledge or relationships.
2. **Narration and dialogue are outputs, not trusted state mutations.** A language model may propose interpretations or actions; the engine validates identity, permissions, preconditions, location, time, visibility and causality before any durable change.
3. **Knowledge belongs to its knower.** Context assembled for a scene must not reveal private NPC memory, secret relationships, hidden stocks, distant unseen incidents or undiscovered world facts merely because they exist in the database. Different recipients can receive different evidence and beliefs.
4. **Remember dialogue as evidence of speech, not proof of its contents.** “You stole my sword” records an accusation, not a historical theft; “old man” does not change a 23-year-old merchant's age. Distinguish speaker, audience, utterance, perceived intent (if uncertain), provenance, time and confidence.
5. **Memories and rumors are fallible.** Preserve source chains and uncertainty. An NPC may misunderstand, lie, forget, exaggerate or reject a rumor under explicit future rules; a story told twice does not become an objective fact.
6. **No player-centered reality.** NPCs continue their own lives and have memories and conflicts unrelated to Carlos. The dialogue model must not create events solely to entertain or react to the player.
7. **No fabricated continuity.** When an answer cannot be grounded in saved state or authorized evidence, do not fabricate an old conversation or agreement. Surface uncertainty naturally or request clarification where necessary.
8. **Bounded context, durable critical state.** Summaries are disposable navigation aids; they cannot replace signed/validated domain events, obligations, durable agreements, timestamps, inventory changes or the underlying event log. Summarization may omit prose but must not delete facts.

## Proposed separation of responsibilities (design target, not an implemented API)

- **Simulation engine:** governs actions, NPC autonomy, economy, causality, clock and durable world state.
- **Persistent store:** authoritative event log and current verified snapshots, with properly scoped character memory and future dialogue-related records.
- **Context Manager / Retrieval:** builds a small, purpose-scoped scene packet from authenticated player view, currently observable environment, recent relevant dialogue and authorized historical recollections. It cannot change state.
- **LLM / narrator:** understands the player's natural-language utterance and renders plausible dialogue and scene prose from that packet. No direct database writes and no authority to override engine decisions.
- **Command / result adapter:** translates *candidate* intent into explicit, engine-validated actions; rejects unrecognized/ambiguous/forged effects rather than silently inventing transactions, NPC identities or outcomes.

## Context packet requirements

A scene packet should be bounded and contain, as justified by the requesting viewpoint:

- world ID/session, logical time, scene/location and observable local participants;
- verified, viewpoint-authorized facts, separate from uncertain testimony or beliefs;
- latest conversational turns sufficient for discourse continuity;
- relevance-ranked durable recollections with original speaker, witness/viewpoint, event source, logical timestamp and uncertainty;
- current interpersonal context only where known to the speaking character;
- explicit prohibitions against inventing unprovided history and against model-side state changes.

The actual schema, retrieval algorithm, compression/token budget, embedding/index strategy and model/server integration are **undecided**. No dependency on a paid API, remote service or specific local model is approved.

## Required tests before declaring the feature implemented

1. **300+ turns / session restart:** continuous behavior across a context rollover, without losing validated persistent effects or silently replaying actions.
2. **Long absence:** Carlos returns after many in-world days; an NPC retrieves a relevant old encounter only if its memory/knowledge provenance allows it.
3. **False premise / identity:** calling a young merchant “old man” or a human baker “goblin” never rewrites their physical identity; responses vary based on personality, context and intentions.
4. **False accusation and gossip:** a theft allegation is stored as speech; any later rumor must traverse actual local contacts, elapsed time and authorized knowledge, without becoming a proven theft.
5. **Privacy and secrets:** context supplied for the player or merchant never leaks a private memory from an uninvolved NPC, even if it is relevant to the player's question.
6. **Conflicting accounts:** different NPCs can remember or retell the same incident differently, with a source chain and no omniscient correction disguised as witnessed knowledge.
7. **Persistence/replay:** verified restore/reopen produces the same authoritative world and remembered claims; resending a command does not duplicate domain effects.
8. **Context overflow/degradation:** compaction/limited tokens may reduce prose detail, not modify the world, invent critical events or fabricate agreements.
9. **NPC independence:** rumors and conversations between NPCs happen without Carlos's involvement, with no free communication across space.
10. **Injection resistance:** malicious player speech or model output cannot directly issue trusted world events, reveal hidden state or bypass actor authority.

## Future design review: decisions to make when implementation begins

- Exact canonical representation of speech acts, observations, dialogue transcripts and consequential promises.
- Which memories remain durable, which are summarized or forgotten, and how provenance is preserved.
- Whether/how full transcript archives are searchable without injecting unbounded text into prompts.
- Access-control boundaries by actor/viewpoint and prevention of accidental omniscient narrator leakage.
- Retrieval ranking, stale/conflicting evidence policies, context size, cost and local model compatibility.
- Role of the narration adapter in conversation turn management, failure fallback and user correction.
- Deterministic test seam between engine state transitions and non-deterministic language generation.
- Performance targets and P0 production save/restore certification.

**Not implemented as of recording.** Existing NPC temperament memories in 02-E record completed physical actions only; they are not yet conversational or social episodic memory. Preserve this distinction. This is a future contract and acceptance checklist, not a claim of current capability.
