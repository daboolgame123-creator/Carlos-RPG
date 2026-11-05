# 04-A/J1c — staged property rights design and J1c1 explicit local collection permissions

**Decision:** implement J1c1 only as an engine-trusted physical collection permission, not court-recognized legal title. User approved continuing J1c on 2026-11-06 Baghdad local.
**Base:** J1b Schema26 Rules34, CI 42121767798, **841/841** passing each Python 3.10 and 3.13; branch simulation-engine-phase-04a-j1. External review deferred, P0 open.

## Hazard
H1 PropertyTaken correctly records a non-judicial physical taking with `permission_basis=no_grant_recorded` even if the world contains a verbal promise or title allegation. J1b custody traces only which registered stock moved; neither sale nor possession proves title. Automatic title transfer at any market trade would legalize an unwitting resale of a taken loaf.

## J1c1 — limited scope approved for coding
- Add `PropertyPermissionGranted` and `PropertyPermissionRevoked` with **independent trusted permission command capability, active session, durable command provenance, replay**. Only recorded original entitled person or registered market steward may issue a permission for precisely the original J1a commodity/source (one registered origin). Grantor, grantee and physical source must be at the same site when granting. Recipient and grantor must be real present NPCs.
- **Scope = collect**: bounded number of registered units authorized to be physically collected by a named recipient from the named source. Validity `[granted_at, expires_at)`; max 7 days logical time; revocation requires a local communication with the recipient (both present), not remote telepathy. No title transfer, lease or general selling rights.
- Only create a grant if the J1b origin is still *certifiably, exclusively identifiable* at the source, i.e. its known quantity equals the source's entire physical balance in that commodity. This prevents falsely granting "the registered loaf" within mixed unknown stock. Multiple simultaneous grants reserve non-overlapping portions of the exact known amount; no oversubscription.
- Extend H1 `PropertyTaken` optional `permission_id`. A recorded valid grant may be redeemed by precisely the named grantee for the exact origin/resource/source/site, before expiry and while physically present. This decrements the grant's remaining count and permanently marks the actual taking `permission_basis=recorded_permission`. A grant must never erase the physical taking, eyewitnesses, or original ownership history.
- Taking **without citing a grant** continues to be possible; it receives `permission_basis=no_grant_recorded`, which means *none cited for this event*, **not a finding of theft**. A revoked, expired, stolen, forged, remote or oversubscribed grant never enables a grant-backed taking, but may not stop a separate unpermitted physical taking under H1 constraints.
- Central validators cross-check grant usage against actual recorded physical takings, usage counts, remaining capacity, issuer identity, origin eligibility, temporal bounds and status; a forged detached snapshot must fail. Full replay is stronger than standalone snapshot validation.
- Version **Schema27/Rules35** (permissions collection, adjusted takings shape and provenance). Older real Schema26/Rules34 saved worlds rejected unchanged; NO migration; semantic opt-in-off parity. All original narrative, main, and real world state untouched.

## Separate stages deliberately NOT included in J1c1
- **J1c2:** actual, voluntary transfer of a **registered entitlement** (not guaranteed legal title), with real parties, provenance and consideration/consent; no automatic title transfer from mere sale or theft. Needs lot-identity constraints, rights accounting and legal code before court enforcement.
- **J1c3:** scope expansion to custody/use/sale, delegation and withdrawal/notification without communication teleportation; prior grants cannot create a chain of unlimited sub-grants. Full current legal title requires adopted world law, jurisdiction, independent evidence and procedure.
- **J2–J5:** courts, hearings, warrants, restitution and punishment; not authorized.
- Independent code review and P0 production save/recovery remain OPEN.

## Adversarial probes
1. Steward Adel (registered bakery) grants Basim 1 of two uniquely registered bakery bread, then Basim physically takes 1 citing it. Inventory changes as before; custody follows; recorded permission is consumed; original beneficiary does not change; not an acquittal or transfer of title.
2. Without citing the same existing grant, Basim may take 1 under H1 with `no_grant_recorded`, which cannot be treated as automatic guilt.
3. Split one grant across two physical takings by the same actor, then no third use; duplicate grant ID, stale revision and double grant beyond registered stock rejected atomically.
4. Forged permission presented by Nora, source mismatch, different resource, fake origin or mixed/unregistered stock, absent grantor or traveling recipient rejected.
5. Revocation when both parties physically together blocks further use; remote revocation rejected without changing state; expiration by logical time blocks citation even if not manually revoked.
6. Simulated unpermitted taking depletes physical source after an outstanding grant; the permission persists as historical agreement but cannot magically materialize stock on redemption.
7. Detached snapshot with fictitious used capacity, future grant, fake owner/steward, forged grant link in physical taking rejected; verified replay and backup/snapshot consistency.
8. Historical Schema26/Rules34 worlds rejected byte-for-byte without mutation and old frozen semantic comparisons unchanged; full CI both Python versions must pass.
