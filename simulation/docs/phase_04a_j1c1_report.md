# Phase 04-A/J1c1 — explicit collection permissions (implementation report)

**Date:** 2026-11-06 Baghdad time (2026-11-05 UTC)
**Branch:** `simulation-engine-phase-04a-j1`
**Baseline:** J1b Schema26/Rules34, [CI 42121767798](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42121767798), 841/841 each Python 3.10 and 3.13.
**State:** `IMPLEMENTED / FULL-CI-VALIDATION-IN-PROGRESS / EXTERNAL_REVIEW_DEFERRED / P0 OPEN`. Do not label J1c legally complete.

## Scope

An actual original J1a beneficiary/registered site steward may issue a quantity-bounded, time-limited **recorded physical collection permission** to a physically present named NPC. The registered origin must still be the exclusively certifiable provenance for the *entire* source inventory of the commodity. No implicit title, no ownership transfer from mere sale, no automatic innocence/guilt.

Permission events:
- `PropertyPermissionGranted` records grantor, grantee, original registered origin, source, site, resource, scope `collect`, total/unused/used quantity, logical issue/expiry (max seven days), and state.
- `PropertyPermissionRevoked` requires actual issuer and recipient physically together at the registered site. No instantaneous remote revocation or fake notification.
- `PropertyTaken` now optionally references `permission_id`. The explicit trusted physical event validates the effective permission's actor/source/resource/site, expiry, unambiguous existing stock and capacity, then atomically consumes the permitted quantity. Existing takings without a cited permission remain valid physical events with `permission_basis=no_grant_recorded` — **not a theft conviction or an assertion that consent was impossible**. A cited valid permission marks `recorded_permission` and still conserves goods, witnesses, and J1b custody provenance.

Safety:
- Independent trusted `permission_authorized` capability stored with each SQLite command and verified on full replay, separate from `taking_authorized`. An active session is mandatory.
- Double-reservation of registered stock blocked at grant time, duplicate IDs/cross-user attempts blocked, and expiry/revocation/consumption cannot grant infinite access.
- Snapshot validator cross checks actual `property_takings` against grant identity, site, commodity, time, quantity and each record's used/remaining/status. In same simulation second, event revision order (replay) determines whether use precedes revocation, not timestamps alone.
- No grants shown through player-facing views or NPC omniscient state; services are internal trusted APIs, **NOT authenticated public endpoints**.
- Schema **27**, Rules **35**, world collection `property_permissions`, extended physical taking provenance and command capability; genuine J1b Schema26/Rules34 predecessor refused byte-for-byte without silent migration; no alterations to main or original narrative.

## Tests prepared

`simulation/tests/test_rights_permissions_04a_j1c1.py`: seven-person bakery, successful timed grant-backed taking, partial grant redemption, exhaustive maximum, uncited taking, impersonation, remote origin, unknown grantee, oversubscribed reservations, incomplete/mixed origin, revocation, same-tick historical usage, expiry, independent capability, stale/duplicate commands, inventory depletion, malicious detached snapshot and replay. Full historic suite and opt-in-off feature parity required.

## Unimplemented and deferred

- **J1c2:** voluntary transfer of a registered, bounded *private entitlement* and verification of the other party's acceptance; the market buyer does not automatically acquire court-enforceable title.
- **J1c3:** other permission scopes (use, hold, sell), delegation, assignment, transfer of the right itself, notice/cancellation beyond local face-to-face, and identifying an individual loaf after mixing (WORLD-GAP-010).
- **04-A/J2–J5:** court, proof standards, legal jurisdiction, hearing, restitution, warrants, fines or punishment **not implemented**.
- External independent adversarial review and production backup-recovery P0 remain OPEN; no production-world adoption or migration without their own gates.

## Technical validation

Final exact code commit SHA, CI job IDs and passed counts must be inserted only after observed successful CI for both Python 3.10 and 3.13. Earlier failure during version-update commits does not count as a validated final run.
