# Phase 02-G — Implementation report (provisional)

**Date:** 2026-11-05  
**Branch:** `simulation-engine-phase-02g` based on green `simulation-engine-phase-02f` SHA `d46aaa04fd53f07e3fd06358f6f62efb904e7452`.  
**Status:** IMPLEMENTED FIRST SLICE / TECHNICALLY VALIDATED AT GREEN CHECKPOINT / NEW 7-NPC PROBE CI PENDING / EXTERNAL REVIEW DEFERRED / P0 OPEN.

## Implemented scope

- Optional local gossip about **real, previously received speech**, not arbitrary inventions about actors. All original utterances are recorded `SocialMessageSent` and `SocialMessageReceived` events.
- `RumorDelivered` is a trusted session-scoped event. Persistent `rumor_deliveries` store retains original message ID, first witness or parent rumor, sender, recipient, subjective confidence, hop count, logical time, and physical site.
- A first-hop storyteller must be the *original actual listener*. Later storytellers must have received that very rumor in the past; information cannot be immediately relayed within the same tick. Direct or player-controlled creation of false source links is rejected by the reducer.
- Actors must be co-located and physically present, not traveling. The optional autonomous policy never makes a busy/producing NPC gossip. No teleportation, global omniscience, unbounded rumor flood, or magic resources.
- Recipient-specific `heard_rumors` and `perceived_reputation` reflect attributed, unproven hearsay; threats may raise a **subjective caution** score without creating guilt, criminal sanctions, market refusal, or global reputation.
- Automatic gossip is **opt-in** (`rumors_enabled=False`); autonomous gossip currently selects only actual typed **threat** utterances and is throttled. Other speech can be passed through a trusted manual service, but arbitrary free-text meaning extraction is **not** implemented.
- Version increment to Schema **21** / Rules **28** for the new persistent rumor collection and event semantics. Existing worlds must not be silently read or migrated.

## Validation / acceptance targets

Tests in `simulation/tests/test_rumors_02g.py`: witnessed local first-person gossip; cautious reputation not objective truth; no unknown origin or false witness; real two-hop chain with actual elapsed logical time; remote delivery rejection; duplicate source/recipient denial; SQLite snapshot, replay and reopen; untrusted or closed-session delivery rejection; opt-in/off checks; autonomous local rumor round; tampered snapshot rejection.

CI adds frozen **02-F** benchmark when OFF and genuine **02-F Schema20/Rules27** saved-world rejection without modifying the old database. Older historical parity and compatibility gates remain.

**Verified checkpoint:** [GitHub Actions 42102121160](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42102121160) was green on SHA `9b395101d8b5c337d9888e6cca8bebae49a561d6`: **762/762 tests pass on Python 3.10 and Python 3.13**, including the frozen 02-F feature-off semantic parity and real old-world rejection. A further adversarial seven-NPC three-hop gossip-chain test was added at code SHA `7b7deaa8f4ef17f77600332aec1a588e8d16478d`; its green verification remains pending at this exact report revision.

**Important:** This is a *provisional* report. Do not upgrade to TECHNICALLY_VALIDATED until the exact final GitHub Actions commit passes Python 3.10 and 3.13. Independent reviewer approval is separate and remains DEFERRED. Production backup P0 remains OPEN; test worlds are disposable.

## Newly identified essential follow-ups (to track in roadmap)

- **WORLD-GAP-004:** context-aware natural-language speech meaning, teasing/insult distinction, evidence vs false assertions and limited NPC-specific interpretation — candidate **05-A** narrative adapter + a future reviewed dialogue/social slice. Never let the LLM rewrite physical identity or invent old dialogue. The current `SocialMessage` kind is typed, not linguistic inference.
- **WORLD-GAP-005:** market/trade refusal based on locally known subjective reputation, personality and practical needs — candidate after **02-G and 02-C**, when local commerce decisions are extended. Refusal is not automatic, global or guaranteed.

Open `WORLD-GAP-001..003` (emergency interruption, paid work, housing ownership) remain OPEN; this phase does not implement them or block safe rumor-only tests.
