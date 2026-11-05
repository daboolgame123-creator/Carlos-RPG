# Independent review request — Phase 02-H1 + H2

Review the exact code SHA `ff2d9b87f91004a1155397debe8fc74b8cc38c52` and its [green CI run 42108021281](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42108021281) (787/787 each Python 3.10 / 3.13). **Do not mark APPROVED solely on CI**, do not merge into main and do not change the Carlos story.

## Adversarial questions for a separate reviewer
1. Can unauthorized/player-facing or stale-session callers create PropertyTaken, PropertyClaimFiled, or counterfeit property_sightings via a bypassing event/replay path? Are stored capabilities and batch events validated?
2. Can an offsite/traveling witness, duplicate identifier, fake NPC, spoofed actor or different clock tick fabricate an eyewitness record? Is the observation bound to the *same* taking event in atomic reducer?
3. Are sighting records private in all intended player/NPC pathways, or can global event logs be misused as omniscient semantic knowledge?
4. Can a claimant cite a taking they never saw, cite different items/sites, infer culprit from unrelated 02-G hearsay or convert a mere accusation into state mutation, guilt, sanction or restitution?
5. Can goods/currency be minted or sold twice after a taking, including with concurrent and forged revision, partial quantity and invalid source, and does rollback preserve the exact ledger?
6. Does `verify()` reproduce record provenance and `WorldState.from_dict()` reject inconsistent forged snapshots? Distinguish consistency validation from cryptographic provenance of a detached snapshot.
7. Does the authentic H1 Schema22/Rules29 saved world reject untouched and do all historical feature-disabled semantic digests match their frozen predecessor?
8. Inspect any overbroad `claim_authorized` capability and the lack of proper network authentication; identify whether P0 or authorization must block future production.
9. Verify WORLD-GAP-006/007 explicitly remain open rather than imply automatic visibility or legally determined ownership.

**Desired verdict:** APPROVED / BLOCKED with reproducible evidence and specific fixes. If BLOCKED, attach regression tests and require a green CI on repaired SHA. External review remains deferred by user; this document is a handoff, not independent approval.

## Extension — Phase 02-H3: local intake and acknowledgment

Code checkpoint for H1/H2/H3: `f102274c584f26f82d3d54e7eb42d7cad628715a`, [CI 42109843738](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42109843738), **802/802 per interpreter**, Python 3.10 and 3.13. Review this newer checkpoint for the integrated H1/H2/H3 verdict. The older H1/H2 review target remains a historical checkpoint only.

Additional independent probes:
10. Can an actor configure a new `ComplaintDeskConfigured` office after time zero or without trusted bootstrap, impersonate another desk, or appoint a nonexistent/traveling officer? Is assignment explicitly persisted and replay-verified?
11. Does intake require the actual claimant of an existing `PropertyClaimFiled`, co-located with a real on-duty desk officer? Can a second intake of the same claim or a fabricated claim be smuggled through any event batch?
12. Can an off-site, traveling, unauthorized or substituted officer acknowledge intake? Can an officer acknowledge twice, without any complaint, or after claimant departure (which should be allowed after completed intake)?
13. Can an intake or acknowledgment affect original claim `unverified` status, physical inventory or currency, guilt, incarceration, penalties, restitution, legal title or any autonomous verdict?
14. Is `complaint_authorized` independently required, tied to active sessions and stored for replay, and inaccessible through any existing player-facing command? Review outer API identity/authorization gaps separately from internal trusted service.
15. Can a malformed detached snapshot forge contradictory desks or conflicting acknowledgments? Distinguish replay proof from snapshot structural consistency.
16. Recreate a genuine H2 Schema23/Rules30 SQLite world and confirm strict read rejection with unchanged bytes under H3 Schema24/Rules31.
17. WORLD-GAP-008 still lacks officer delegation, shift scheduling, queues and inter-office referrals. Are these clearly deferred rather than silently guessed?

Formal APPROVED requires an actual separate reviewer, concrete reproducible evidence and no unresolved blockers. **P0 remains OPEN**; this handoff document is not itself a review outcome.

## Post-audit Rules32 update — review this exact checkpoint instead

**Current candidate code SHA:** `65e4dd582d8ea0a4cfbd442a8ce39e094aa5f303`, [CI 42112812532](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42112812532), **808/808 passed each on Python 3.10 and 3.13**. This is more recent than the H3 Rules31 candidate above. Rules32 still uses Schema24; genuine prior Rules31 worlds are rejected unchanged.

The internal audit discovered **REVIEW-02H-001**: a real eyewitness could cite a taking as `direct_sighting` when falsely naming someone else or claiming a different quantity. The engine now rejects such citation (the unsupported lie may still be filed as an unverified standalone claim). Independent review MUST reproduce both former loopholes, verify the repaired reducer and snapshot validator, prove rollback and verify immutable replay tamper detection. Details: [internal audit](phase_02h_internal_adversarial_audit.md).

This audit and green CI **do not constitute an independent reviewer sign-off**. Before any `APPROVED` status, independently challenge identity boundaries, capability replay, privilege leakage, absence of automatic perception, actual title vs possession and P0 production backup/recovery.
