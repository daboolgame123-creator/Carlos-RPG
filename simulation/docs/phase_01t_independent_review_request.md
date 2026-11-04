# Phase 01-T — Independent adversarial review request

**Status:** PENDING separate reviewer. **DO NOT CLOSE 01-T OR START 01-U.**
**Target branch:** `simulation-engine-phase-01t`
**Code baseline:** `04237a6c08c4af489c46061c1adf6a4c1d5d57a8`
**Last documented code CI:** [41923020544](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/41923020544) — 542/542 tests passed on Python 3.10 and 3.13. This automated suite is not a separate human/agent reviewer approval.
**Original approved 01-S baseline:** `c35245d1904e7a6d779cafa92cbf556618247f38`
**Status of P0 backup/migration gate:** OPEN.

## Reviewer instructions

Perform a **read-only review by a reviewer other than the implementation assistant**. First confirm the actual branch head and most recent CI. Review the 01-S→01-T diff rather than relying on implementation comments, then inspect:

1. `knowledge.py`: sender only accesses sender-owned beliefs, publicly relevant co-location/availability, and sender-specific prior communication receipts. It must **never branch on the recipient's private beliefs**. Try changing only recipient beliefs: generated sender events must remain identical.
2. `npc.py`: direct observations require actual co-located NPC, actual initialized local `wild_food`, matching `food:<location>`, `observed_at == received_at == state.time`. False hearsay must remain a *belief* and must never be silently promoted to a fact.
3. `should_adopt`: verify R1–R7 including direct observation protection, stale replacement, equal-confidence tie, and acknowledgement consuming a delivery even without a belief overwrite.
4. `LivingWorldEngine`: sharing before decisions must not reschedule `next_decision_at`, change foraging priority, introduce waiting, bypass event budget, or cause knowledge-derived omniscient navigation (01-U is out of scope).
5. `movement.py`: explicit `observe(..., knowledge_enabled=True)` emits an atomic local observation and food knowledge pair without altering legacy opt-out behavior.
6. `SQLiteEventStore`: command idempotency, rollback on partial batch failure, duplicate delivery ID, pause/closed-session prohibition, snapshot/reopen/`verify()` semantic replay equality.
7. **Save compatibility:** actual 01-S (`13/17`) database built with 01-S runtime and 01-R (`12/16`) must both be rejected by 01-T (`13/18`) without any row/event/snapshot rewrite. Do not migrate them.
8. Run `python -m compileall -q src tests scenarios` and `python -m pytest -q` on supported Python versions 3.10 and 3.13; run existing seven-NPC demonstrations and **direct 01-S flag-off parity**. Test boundary timestamps (`2**63-1` accepted; `2**63` and 5,000-digit timestamps rejected), and verify the closed-session probe uses a valid event with a matching open-session control.
9. Audit ambiguous implementation corners: per-pair rate-limit across close/reopen, memory poisoning via message, sender-to-recipient location identities, per-tick sharing cap, edge cases at staleness thresholds, and one-command event budget. Independently confirm the scheduled travel-arrival hook executes for real `__npc_travel_id` payloads (including unknown/empty/present food), that `knowledge_shares` contains each delivery ID once, and that an exhausted budget **between delivery and ack** rolls the whole command back.

## Report format and gates

Submit `APPROVED` or `BLOCKED` with file/line evidence, reproducible negative probes, exact checked commit SHA, test count by Python version, and latest CI run. Classify each issue blocker/regression/future improvement, and state explicitly whether P0 remains open. If blockers exist, do not mark 01-T complete; return findings for fixes and perform a fresh review on the corrected HEAD.

Only after **separate approval** and green CI on the final commit may `phase_01t_review_report.md` and `ROADMAP.md` be updated to close 01-T; **never change main or Carlos story files** during this task.
