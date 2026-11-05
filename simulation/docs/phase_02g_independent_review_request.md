# Independent review request — Carlos RPG Phase 02-G

**Branch:** `simulation-engine-phase-02g`.  
**Do not call this APPROVED/CLOSED without an independent reviewer.**  
**Base:** genuine green Phase 02-F SHA `d46aaa04fd53f07e3fd06358f6f62efb904e7452`.  
**Status:** technical CI evidence reported separately in [phase_02g_report.md](phase_02g_report.md); P0 OPEN and disposable worlds only.

## Reviewer scope

Evaluate `simulation/src/carlos_sim/rumors.py`, `domain.py`, `living_world.py`, `store.py`, `tests/test_rumors_02g.py`, historical parity scripts and GitHub Actions CI workflow. Report exact reviewed SHA, independent findings and reproducible probes.

Questions to try **independently**, without assuming these tests are correct:

1. Forge `RumorDelivered` with an invented origin event, wrong original receiver, different subject, or another NPC's parent rumor. Confirm rejection with unchanged SQLite events/commands.
2. Re-send the same claim to the same NPC with a different ID; send two rumors on the same tick; reach maximum hops and reshare before the enforced delay.
3. Sender or receiver moves away, remains in transit, starts productive work or becomes busy: verify physical availability and that existing work commitments remain intact.
4. Contact four to seven NPCs and confirm no same-tick cascade, no secret remote observation, and no unbounded fanout or O(N²) pathological amplification.
5. Inspect two listeners with different exposure; confirm `perceived_reputation` does not become global fact, title, guilt, ownership, shop refusal or automatic sanctions.
6. Confirm player can say a false phrase without rewriting age, identity or alleged theft history, and that free-text semantic inference **is not** falsely claimed to be implemented.
7. Test an original utterance recorded with `kind='threat'` and separately with a neutral kind; check autonomous gossip's explicit bounded threat-only policy and trusted service access to other real messages.
8. Verify full SQLite snapshot/restart/replay, event hash, command idempotence, rollback after budget exhaustion, genuine frozen 02-F Schema20/Rules27 rejection unchanged, and exact OFF feature parity with genuine 02-F.
9. Review potential N²/N³ cost as rumor ledger grows; recommend profiling and bounded retention if necessary, without deleting the authoritative event log.
10. Verify P0 and other open world gaps remain visible, and this phase does not silently merge into `main` or mutate Carlos's canonical narrative.

Output **APPROVED / BLOCKED / INCONCLUSIVE** and specify exact commit evidence. If independent review is unavailable, status stays **TECHNICALLY_VALIDATED / EXTERNAL_REVIEW_DEFERRED** after successful final CI, never APPROVED.
