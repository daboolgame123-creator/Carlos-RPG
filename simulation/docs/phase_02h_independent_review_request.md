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
