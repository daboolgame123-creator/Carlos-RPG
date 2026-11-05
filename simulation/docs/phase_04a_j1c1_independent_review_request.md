# Independent adversarial review request — 04-A/J1c1 collection permissions

**Code checkpoint:** `9d573b0472ecf721afa8f4672d02312af22e86ce` on `simulation-engine-phase-04a-j1`.
**Evidence:** [GitHub Actions 42127560935](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42127560935), **865/865 passed EACH Python 3.10 and 3.13**.
**Status:** `TECHNICALLY_VALIDATED / EXTERNAL_REVIEW_DEFERRED / P0 OPEN`; this document requests review and is NOT an independent sign-off.

Review exact `rights_permissions.py`, `property.py`, `domain.py`, `store.py`, new tests and schema, not just author's description. Confirm no J1c2/J1c3 or courts silently added.

## Adversarial probes to run independently

1. **Source/authority:** can a random resident, nonlocal issuer, fake market steward, absent registered origin beneficiary, player-controlled actor, or someone in transit issue/revoke for a site stock? Check actual command authorization vs a forged `event.actor_id` inside an untrusted client.
2. **Physical specificity:** source bread contains one registered loaf and one unregistered loaf, or two different original lots. Attempt to grant/consume a particular loaf; must reject unless identity is fully established, even if numeric stock is sufficient.
3. **Reservation:** issue two overlapping grants that together exceed exclusive registered stock; try expired grants, partial usage, repeated IDs, quantity bool/negative/overflow, wrong resource, unknown grantee. Rejection must preserve original stock and ledger.
4. **Transfer vs title:** a valid collection grant can be redeemed into actual physical custody but does not transfer legal title, authorize resale, or erase original entitlement/provenance. Taking without a cited grant is not an automatic conviction.
5. **Expiry:** grant at t=0 expires at t=5; valid at t=4, invalid at t=5. Large or overflow expiry and attempts to bypass by modifying event time must fail closed.
6. **Revocation and knowledge:** recorded revocation requires actual co-location and genuine identity. A grantee traveling away cannot be instantaneously notified/blocked by a remote caller via this event. A legitimate usage **earlier in the same tick** must remain valid after subsequent local revocation; later same-tick attempts must fail via immutable replay order, not timestamp-only reasoning.
7. **Permission laundering:** can a claimant cite the grant of someone else, use a different source or origin, cite a revoked grant, or grant unlimited authority through chained permissions? All invalid references must reject and never create legal rights.
8. **Atomicity and forged persistence:** a batch including grant + invalid physical taking or a failed second event should roll back fully. Tamper with `commands.permission_authorized`, or `property_permissions.used/remaining/revoked_at`, or `property_takings.permission_id`; detached `WorldState.from_dict` must refuse structural inconsistencies and full `verify()` must refuse inconsistent replay.
9. **Same-tick historical validation caution:** standalone snapshots cannot prove event ordering solely from `taken_at == revoked_at`; full replay must be authoritative. Consider adding explicit revision provenance if a future legal hearing needs time-order proof without full event-log access.
10. **World compatibility:** genuine saved-world J1b Schema26/Rules34 must refuse under Schema27/Rules35 without mutation or automatic migration; fixed older world parity and every previous module regression still passes both runtimes.
11. **Privileges/privacy:** new internal service is not a public authentication boundary; no arbitrary actor IDs or global permissions exposed to NPC/player/LLM. External authenticated identity enforcement and data projections are still missing.
12. **Scaling/capacity:** capped grants and lot-history scans must fail closed; test many grants after partial physical removal and grant expiry to ensure checks neither reserve phantom units nor violate physical stocks.
13. **P0:** do NOT approve production/live-world persistent permissions until independently demonstrated backup/restore and version migration/rejection, and a separate adversarial reviewer signs off.

Issue an actual separate test report with severity, steps, fixtures, code version, risk and fix commitments; do not label this request APPROVED.
