# Phase 01-H — Social relationships and local interactions

## Implemented

- Event-sourced, **asymmetric** NPC trust toward other entities, bounded to −100…100. The recipient’s trust may change while the sender’s view remains unchanged.
- Four deterministic, prototype-level *speech acts*: greeting, offer_help, request_help, threat. Interpretation depends on the recipient’s existing trust; an offered favor **never** creates actual help or transfers goods.
- Two auditable events: `SocialMessageSent` and `SocialMessageReceived`. The receiver alone acknowledges a pending message. The trusted `NPCSocialService.interact` submits send and reception in one atomic SQLite command.
- Both parties must be present in the **same location**, excluding in-transit travelers. Unrelated or unknown actors, fake receipts, repeat delivery, duplicate IDs and delivery while the session is closed are rejected.
- Trust and message receipt history survive snapshots and deterministic replay, and neither exposed player views nor Carlos's original story state is modified.

## Verification

`cd simulation && python -m pytest -q` → **212 passed before review; 216 passed afterward** (188 baseline + 24 Phase 01-H tests). `python -m compileall -q src tests scenarios` passed. `PYTHONPATH=src python scenarios/test_village/demo_social.py` completed.

In an isolated four-message example, Basim's trust toward Nora became **−13** after greeting, threat, then help request; Nora's trust toward Basim became **+3** after an offer of help. Trust evolves independently and outcomes are order-dependent.

Test coverage: directional trust, interpretation policy, local presence, travel, reply after arrival, player-as-sender only, refusal to automate Carlos as recipient, message forgery, double acknowledgement, command duplication, closed session, capabilities, immutable snapshots, restart, revision conflict, bounded trust, validation, atomicity and deterministic replay.

## Explicit limitations

- **Messages are initiated by an explicit trusted local service call**; Phase 01-H does *not* yet choose social partners, motivations, dialogue or conflicts automatically during the autonomous time loop.
- The categorization `kind` is a supplied speech act, not validated natural-language meaning; typed text is stored, not parsed or trusted. An offer of help is a statement, not a fulfilled obligation. No actual resources, legal consequences, promises, debts, reputation propagation or combat are simulated.
- Each interaction currently uses an instantaneous, atomic send-and-receive pair; delayed messaging requires a separately authorized workflow.
- The in-process `social_authorized` flag is not authentication; future network exposure must add identity/permission checks.
- The model uses **schema 8 / rules 10** and requires explicit migration/recreation of old experimental databases. No production Carlos data imported, no `main` merge and no hosted GitHub CI verification performed.

## Decision

This phase is an initial, testable social foundation, **not** a complete independent social agent. Review and patch any discovered issues before progressing to autonomous partner selection, social memory and resource-backed assistance.

## Post-review corrections (2026-11-03)

**Two confirmed issues were reproduced and fixed, with four regression tests:**

1. **Misplaced delayed receipt:** A pending locally spoken message could be acknowledged after both parties traveled to a different location, because receipt checked only current co-location, not the message's original local location. The reducer now requires that the receiver be in the `location_id` recorded by the original send event, as well as the existing sender/receiver co-location checks. Same-location delayed receipts still work and remain auditable.
2. **Same-tick reputation farming:** Repeating `offer_help` (or another identical speech act) from the same sender to the same recipient dozens of times without advancing simulation time produced unlimited trust gains. The reducer now refuses another message with the same sender, recipient, kind and simulated `sent_at`. Different speech act kinds at the same instant remain valid, and the same kind can be repeated after simulated time progresses. This is a **basic integrity guard**, not a complete social-influence/cooldown model.

**Verification:** local `python -m pytest -q` → **216 passed** (212 baseline plus 4 review tests), `python -m compileall -q src tests scenarios` succeeded. The four changed Python files (`social.py`, `domain.py`, `test_social.py`, `test_social_review.py`) match the exact GitHub blob SHAs of the locally tested bytes. No hosted CI run.

**Compatibility:** schema remains **8**; rules version advances from **9 to 10**. Older experimental worlds using rules v9 are intentionally rejected pending explicit migration/replay compatibility treatment. No real Carlos story state imported, no changes to `main`, and no authenticated external social API exposed.

**Open model limitations:** separate truthful speech/content verification, social time cost, physical aid, fatigue/skill consequences, NPC-initiated communication and longer-term cooldown/diminishing returns still need separate reviewed rules. An actor could still gain trust by repeating offers on successive simulated ticks; this first guard prevents same-instant duplication only.
