# Independent review request — Phase 02-B

**Status: REQUEST DOCUMENTED, NOT PERFORMED.** No independent approval, P0 remains OPEN.
**Baseline:** Phase 02-A `fdf6162c65d6947507d1b4e4516c17d851873c29`, Schema 15 / Rules 22.
**Candidate:** `simulation-engine-phase-02b`, Schema 16 / Rules 23.

Examine `simulation/src/carlos_sim/production.py`, its reducer/provenance integration in `domain.py` / `store.py`, and changes in `actions.py`, `movement.py`, `living_world.py`, the test files and CI, independently of the implementer's explanation.

Independent adversarial checks:
1. **Real cost:** No recipe may produce output without previously initialized input stock, output balance and physical tool, actual current location and profession. Production must debit inputs once, never draw from a remote or another entity's secret inventory, and never create bread before the scheduled due event.
2. **Scarce tools and competing workers:** A site with one oven and two bakers permits at most one simultaneous job; two ovens allow two if ingredients suffice. Test parallel command races, stale revision and same IDs. Ensure a busy baker cannot begin an action, travel or perform incompatible autonomous work while baking.
3. **Event forgery:** Try direct `ProductionStarted` without `production_authorized`, impersonating someone else's profession or actor ID, a generic invented `__production_job` schedule, premature firing and cancellation, and editing snapshot job records to invent output. The failure must be atomic with no stolen inputs.
4. **Reproducible timing:** One 90-second command versus smaller steps, time paused during process restart, pending jobs snapshotted, simultaneous same-due jobs with deterministic order, and limits on total events per advance. Full replay and SQLite integrity should match.
5. **Compatibility and provenance:** Confirm genuine 15/22 predecessor data is refused unchanged; no SQL migration, no accidental acceptance of old command tables without `production_authorized` column. Reopen and re-verify a 16/23 backup copy.
6. **Prior behavior:** Check 7-NPC hunger/foraging/social/knowledge parity with no recipe configured. Verify the new empty collections alone are excluded from old-version semantic normalization, while event counts, event digests and all NPC resources remain strictly compared. Check no new player visibility/private-data leak.
7. **Operational limits:** Current project still has P0 OPEN, no independent backup certification, no API authorization or permanent saves. Production job cancellation/refunds, tool degradation, wages, price and ownership transfer are NOT implemented; do not infer their presence.

Report tested SHA, independent environment, Python versions, reproducible test commands, blockers and regression classifications. Until independent sign-off, any successfully tested 02-B revision remains **TECHNICALLY_VALIDATED / EXTERNAL_REVIEW_DEFERRED, not APPROVED/CLOSED**.
