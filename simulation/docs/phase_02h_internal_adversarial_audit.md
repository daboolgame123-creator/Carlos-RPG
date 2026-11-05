# Phase 02-H — Internal adversarial audit (not independent approval)

Date: 2026-11-05
Branch: `simulation-engine-phase-02h`
Starting reviewed implementation: `9d6d99095f9ec84b13893002a6166a52353d96b8` (original H1/H2/H3 all green, 802 tests on Python 3.10/3.13)
Auditor: ChatGPT code inspection and added adversarial tests in the SAME development conversation; **not a separate independent reviewer**.
Status: **INTERNAL_AUDIT / FINDING_FIXED_IN_CODE / CI_PENDING_FINAL_SHA / EXTERNAL_REVIEW_DEFERRED / P0 OPEN**.

## Confirmed defect: REVIEW-02H-001 — eyewitness evidence laundering
Severity: high for future legal use; no present judicial sanctions in scope.

A claimant who actually witnessed taking `t1` by `basim` could file an `accusation` claiming `adel` was responsible, or cite quantity `100` when the recorded event involved only one unit. The prior `file_property_claim` checked event existence, site, resource and witness identity but did not require cited event's actor/quantity to match claim's stated suspect/quantity. It recorded `basis=direct_sighting`, despite immutable cited evidence directly contradicting it. This is an evidence-laundering hazard; other humans may lie, but the engine must not call the wrong assertion directly evidenced.

Remediation:
- In `property_evidence.file_property_claim`, when an existing event ID is cited, require the claim quantity to equal that recorded event's quantity, and for `accusation` require `subject_id` to equal the recorded taking actor. Other `loss`/`ownership` claims may still be unverified independently.
- Make `validate_property_evidence` enforce the same constraints on persisted snapshots and replay.
- Do **not** forbid false allegations: claims with `taking_id=None` remain permitted as `unverified_statement`, never `direct_sighting` or an automatic verdict.
- Because prior events that were accepted can now be rejected, increment **Rules 31 to 32**, retaining Schema 24; reject old Rules31 worlds without mutation and without silent migration.
- Adversarial tests: mismatch suspect, fabricated inflated quantity, self-implicating actor blaming another, falsified detached snapshot, rehashed forgery in SQLite immutable event stream, and stripped trusted capability; all should reject with unchanged state or raise integrity error.

Code changes: `simulation/src/carlos_sim/property_evidence.py`, `simulation/src/carlos_sim/domain.py`, `simulation/tests/test_property_02h2.py`, CI predecessor compatibility checks. New code checkpoint for tests: `65e4dd582d8ea0a4cfbd442a8ce39e094aa5f303`.
CI pending when this report was first drafted: https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42112812532.

## Other review observations — OPEN, not declared fixed

- **REVIEW-02H-002 / AUTH-BOUNDARY:** `NPCPropertyService`, `NPCComplaintService`, and `personal_property_evidence` accept actor/viewer IDs and privileged `WorldState` from a trusted in-process caller. This is NOT a secure authentication boundary. There is no authenticated player-to-NPC identity binding. Do not expose these APIs directly to web or LLM users. Before any public/player interface, enforce verified identity and scoped authoritative access outside the engine; add cross-user privacy probes.
- **REVIEW-02H-003 / WORLD-GAP-006:** `witnessed_by` represents trusted explicit observed witnesses, not a visibility/stealth/attention engine. A trusted caller can assign a colocated NPC as eyewitness without that NPC independently perceiving the act. No automatic witness discovery is implemented.
- **REVIEW-02H-004 / WORLD-GAP-007:** market inventory is possession and recorded source, not a definitive legal-title registry. Do not return/seize stock merely on complaint receipt or on a rumor.
- **REVIEW-02H-005 / WORLD-GAP-008:** desk staffing, replacement, jurisdiction, referral and absence queues are not implemented.
- **REVIEW-02H-006 / P0:** strict version refusal plus replay are encouraging, but full real production backup/recovery certification and adversarial independent sign-off remain OPEN. An attacker with privileged SQLite access can alter both data and stored hashes; no security property against filesystem/admin compromise is claimed.

## Acceptance gate

- Internal repair validated only when both Python versions pass the full CI against the **exact repaired code SHA**.
- `TECHNICALLY_VALIDATED` may be restored after CI, but `APPROVED`/`CLOSED` requires a genuinely separate adversarial reviewer and explicit P0 resolution as prescribed by the project's protocol.
- No judicial enforcement, false guilt, forced restitution, or unrestricted narration was introduced.
- `main` and original Carlos story files stay untouched.
